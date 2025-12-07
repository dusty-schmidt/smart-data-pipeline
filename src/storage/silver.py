from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage.models import Base, SilverEntity
from typing import Dict, Any
from loguru import logger
import os

class SilverStorage:
    def __init__(self, db_path: str = "sqlite:///data/pipeline.db"):
        os.makedirs("data", exist_ok=True)
        self.engine = create_engine(db_path)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def upsert_entity(self, entity_data: Dict[str, Any]) -> int:
        """
        Generic Upsert for any specialized entity.
        
        Expected format:
        {
            "source": "nba",
            "type": "game",
            "external_id": "game_123", # Provider ID
            "timestamp": datetime_obj,
            "status": "Final",
            "name": "Lakers vs Celtics",
            "data": { ...any dict content... }
        }
        """
        session = self.Session()
        try:
            # Composite key for identity
            source = entity_data["source"]
            obj_type = entity_data["type"]
            ext_id = entity_data["external_id"]

            entity = session.query(SilverEntity).filter_by(
                source=source,
                type=obj_type,
                external_id=ext_id
            ).first()

            if entity:
                # UPDATE
                logger.debug(f"Updating entity: {source}/{obj_type}/{ext_id}")
                entity.timestamp = entity_data.get("timestamp", entity.timestamp)
                entity.status = entity_data.get("status", entity.status)
                entity.name = entity_data.get("name", entity.name)
                entity.data = entity_data.get("data", entity.data)
                if "labels" in entity_data:
                    entity.labels = entity_data["labels"]
            else:
                # INSERT
                logger.info(f"Creating entity: {source}/{obj_type}/{ext_id}")
                entity = SilverEntity(
                    source=source,
                    type=obj_type,
                    external_id=ext_id,
                    timestamp=entity_data.get("timestamp"),
                    status=entity_data.get("status"),
                    name=entity_data.get("name"),
                    labels=entity_data.get("labels", {}),
                    data=entity_data.get("data")
                )
                session.add(entity)

            session.commit()
            return entity.id

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to upsert entity {entity_data.get('external_id')}: {e}")
            raise
        finally:
            session.close()

    def get_entity(self, source: str, obj_type: str, external_id: str) -> Dict[str, Any]:
        """Helper to retrieve agnostic entities"""
        session = self.Session()
        try:
            entity = session.query(SilverEntity).filter_by(
                source=source, 
                type=obj_type, 
                external_id=external_id
            ).first()
            
            if not entity:
                return None
            
            return {
                "id": entity.id,
                "external_id": entity.external_id,
                "name": entity.name,
                "status": entity.status,
                "labels": entity.labels,
                "data": entity.data
            }
        finally:
            session.close()
