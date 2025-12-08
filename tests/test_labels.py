from datetime import datetime, timezone

from src.storage.silver import SilverStorage
from loguru import logger
import sys

def test_labels():
    logger.info("Testing Silver Layer Custom Labels...")
    
    storage = SilverStorage()
    
    ext_id = "labeled_001"
    
    # 1. Insert with Labels
    entity_1 = {
        "source": "manual_test",
        "type": "game",
        "external_id": ext_id,
        "timestamp": datetime.now(timezone.utc),
        "status": "Scheduled",
        "name": "Labeled Game",
        "labels": {"domain": "sports", "league": "nba"},
        "data": {}
    }
    
    storage.upsert_entity(entity_1)
    
    # Verify 1
    stored = storage.get_entity("manual_test", "game", ext_id)
    logger.info(f"Retrieved Labels: {stored['labels']}")
    assert stored["labels"]["league"] == "nba"
    
    # 2. Update Labels (Replace)
    entity_2 = {
        "source": "manual_test",
        "type": "game",
        "external_id": ext_id,
        "labels": {"domain": "sports", "league": "nba", "season": "2025"}, # Added season
        "data": {}
    }
    
    storage.upsert_entity(entity_2)
    
    # Verify 2
    updated = storage.get_entity("manual_test", "game", ext_id)
    assert updated["labels"]["season"] == "2025"
    logger.success("Verification Passed: Labels are persisted and updated.")

if __name__ == "__main__":
    try:
        test_labels()
    except Exception as e:
        logger.exception("Test Failed")
        sys.exit(1)
