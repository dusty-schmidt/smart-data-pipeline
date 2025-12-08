from datetime import datetime, timezone

from src.storage.silver import SilverStorage
from loguru import logger
import sys

def test_generic_upsert():
    logger.info("Testing Silver Layer (Generic Entity) Upsert...")
    
    storage = SilverStorage()
    
    ext_id = "generic_001"
    
    # 1. First Insert (Sports Domain)
    entity_1 = {
        "source": "manual_test",
        "type": "game",
        "external_id": ext_id,
        "timestamp": datetime.now(timezone.utc),
        "status": "InProgress",
        "name": "Team A vs Team B",
        "data": {
            "home": {"name": "Team A", "score": 10},
            "away": {"name": "Team B", "score": 5}
        }
    }
    
    storage.upsert_entity(entity_1)
    logger.info("Inserted Initial Game.")
    
    # Verify 1
    stored = storage.get_entity("manual_test", "game", ext_id)
    assert stored["status"] == "InProgress"
    assert stored["data"]["home"]["score"] == 10
    
    # 2. Upsert (Update)
    entity_2 = {
        "source": "manual_test",
        "type": "game",
        "external_id": ext_id,
        "timestamp": datetime.now(timezone.utc),
        "status": "Final", # Changed
        "name": "Team A vs Team B",
        "data": {
            "home": {"name": "Team A", "score": 20}, # Changed
            "away": {"name": "Team B", "score": 15}
        }
    }
    
    storage.upsert_entity(entity_2)
    logger.info("Upserted Updated Game.")

    # Verify 2
    updated = storage.get_entity("manual_test", "game", ext_id)
    assert updated["status"] == "Final"
    assert updated["data"]["home"]["score"] == 20
    
    # 3. New Domain (Finance)
    finance_entity = {
        "source": "alpaca",
        "type": "quote",
        "external_id": "AAPL",
        "timestamp": datetime.now(timezone.utc),
        "status": "Active",
        "name": "Apple Inc.",
        "data": {
            "price": 150.25,
            "volume": 1000000
        }
    }
    storage.upsert_entity(finance_entity)
    logger.info("Inserted Finance Entity.")
    
    stock = storage.get_entity("alpaca", "quote", "AAPL")
    assert stock["data"]["price"] == 150.25

    logger.success("Verification Passed: Generic Upsert handles multiple domains.")

    logger.success("Verification Passed: Generic Upsert handles multiple domains.")

