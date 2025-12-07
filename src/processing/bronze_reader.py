from typing import Dict, Any, Union
from loguru import logger
from src.storage.bronze import BronzeStorage

class SimpleParser:
    def __init__(self, storage: BronzeStorage):
        self.storage = storage

    def parse(self, local_id: Union[int, str]) -> Dict[str, Any]:
        """
        Reads a raw record from the bronze layer (by ID) and extracts payload.
        """
        logger.info(f"Parsing Record ID: {local_id}")
        
        # Load from DB instead of file
        # Handle string input just in case
        record_id = int(local_id)
        data = self.storage.get(record_id)
        
        payload = data.get("payload", {})
        metadata = data.get("metadata", {})
        
        logger.info(f"Successfully loaded data from source: {metadata.get('source')}")
        
        # Basic validation/extraction
        return {
            "title": payload.get("title", "Unknown"),
            # For NBA data, it's a different structure, let's look for a game date
            "first_game_date": payload.get("scoreboard", {}).get("gameDate", "Unknown (Complex Structure)"),
            "ingested_at": metadata.get("ingested_at")
        }
