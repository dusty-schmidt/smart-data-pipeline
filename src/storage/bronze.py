from datetime import datetime
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
                ingested_at=datetime.utcnow()
            )
            session.add(log_entry)
            session.commit()
            
            # Refresh to get the generated ID
            session.refresh(log_entry)
            logger.info(f"Saved raw data to DB (ID: {log_entry.id})")
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
