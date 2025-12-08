from datetime import datetime, timezone
from typing import Dict, Any, List
from src.processing.base import BaseParser, ParsingResult
from src.storage.silver import SilverStorage
from loguru import logger
import sys

class MockParser(BaseParser):
    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        """Mock parsing logic similar to the old NBA one but generic."""
        payload = message.get("payload", {})
        results = []
        for item in payload.get("items", []):
             results.append(ParsingResult(
                 source="test_source",
                 type="test_item",
                 external_id=item["id"],
                 data=item,
                 status=item.get("status", "Unknown"),
                 name=item.get("name", "Unknown"),
                 labels={"domain": "test"}
             ))
        return results

def test_parser_flow():
    logger.info("Testing Parser -> Storage Flow...")
    
    # 1. Mock Input
    raw_bronze_record = {
        "metadata": {"source": "test_source", "ingested_at": "2025-12-06T..."},
        "payload": {
            "items": [
                {"id": "001", "name": "Item 1", "status": "Active", "value": 100},
                {"id": "002", "name": "Item 2", "status": "Inactive", "value": 50}
            ]
        }
    }
    
    # 2. Transform (Parser)
    parser = MockParser()
    results = parser.parse(raw_bronze_record)
    
    assert len(results) == 2
    logger.info(f"Parser produced {len(results)} entities.")
    
    # 3. Load (Silver Storage)
    storage = SilverStorage() # connection to sqlite
    
    for item in results:
        # Convert ParsingResult to generic dict for storage
        entity_dict = item.to_dict()
        
        # Save
        db_id = storage.upsert_entity(entity_dict)
        logger.info(f"Saved Entity {item.name} -> ID: {db_id}")
        
    # 4. Verify in DB
    stored_item = storage.get_entity("test_source", "test_item", "001")
    assert stored_item["status"] == "Active"
    assert stored_item["data"]["value"] == 100
    assert stored_item["labels"]["domain"] == "test"
    
    logger.success("Verification Passed: Full Pipeline (Dict -> Parser -> Object -> DB).")

    logger.success("Verification Passed: Full Pipeline (Dict -> Parser -> Object -> DB).")

