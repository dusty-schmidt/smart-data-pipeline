from datetime import datetime, timezone

from typing import Any, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger
import os
from src.storage.models import Base, BronzeLog

class BronzeStorage:
    def __init__(self, db_path: str = "sqlite:///data/pipeline.db"):
        os.makedirs("data", exist_ok=True)
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def save(self, data: Dict[str, Any], source: str) -> int:
        """
        Saves raw data to the bronze_logs table.
        Returns the ID of the inserted row.
        """
        session = self.Session()
        try:
            log_entry = BronzeLog(
                source=source,
                payload=data,
                ingested_at=datetime.now(timezone.utc)
            )
            session.add(log_entry)
            session.commit()
            
            # Refresh to get the generated ID
            session.refresh(log_entry)
            logger.info(f"Saved raw data to DB (ID: {log_entry.id})")
            
            # ALSO save to file system for easy inspection (Data Lake pattern)
            try:
                timestamp_str = log_entry.ingested_at.strftime("%Y-%m-%dT%H-%M-%S")
                filename = f"{source}_{timestamp_str}.json"
                file_path = os.path.join("data/bronze", filename)
                
                # Ensure directory exists
                os.makedirs("data/bronze", exist_ok=True)
                
                with open(file_path, "w") as f:
                    import json
                    # Use default=str to handle datetime objects
                    json.dump({"metadata": {"source": source, "id": log_entry.id, "ingested_at": str(log_entry.ingested_at)}, "payload": data}, f, indent=2, default=str)
                    
                logger.info(f"Saved raw data to file: {file_path}")
            except Exception as file_error:
                logger.error(f"Failed to save raw data to file: {file_error}")
                # Don't fail the whole operation if file write fails, DB is primary
            
            return log_entry.id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save to DB: {e}")
            raise
        finally:
            session.close()

    def get(self, log_id: int) -> Dict[str, Any]:
        """
        Retrieves a record by ID. 
        Useful for the parser to load data.
        """
        session = self.Session()
        try:
            record = session.query(BronzeLog).filter_by(id=log_id).first()
            if not record:
                raise FileNotFoundError(f"BronzeLog ID {log_id} not found")
            
            return {
                "metadata": {
                    "source": record.source,
                    "ingested_at": record.ingested_at.isoformat(),
                    "version": record.version,
                    "id": record.id
                },
                "payload": record.payload
            }
        finally:
            session.close()
