from datetime import datetime
from src.processing.nba import NBAScoreboardParser
from src.storage.silver import SilverStorage
from loguru import logger
import sys

def test_parser_flow():
    logger.info("Testing Parser -> Storage Flow...")
    
    # 1. Mock Input (Raw Bronze Data)
    raw_bronze_record = {
        "metadata": {"source": "nba_scoreboard", "ingested_at": "2025-12-06T..."},
        "payload": {
            "scoreboard": {
                "gameDate": "2025-12-06",
                "games": [
                    {
                        "gameId": "0022300001",
                        "gameStatusText": "Final",
                        "homeTeam": {"teamTricode": "LAL", "score": 110},
                        "awayTeam": {"teamTricode": "BOS", "score": 105},
                        "period": 4,
                        "gameClock": "00:00"
                    },
                    {
                         "gameId": "0022300002",
                        "gameStatusText": "Q2",
                        "homeTeam": {"teamTricode": "NYK", "score": 45},
                        "awayTeam": {"teamTricode": "MIA", "score": 42},
                         "period": 2,
                        "gameClock": "05:30"
                    }
                ]
            }
        }
    }
    
    # 2. Transform (Parser)
    parser = NBAScoreboardParser()
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
    stored_game = storage.get_entity("nba", "game", "0022300001")
    assert stored_game["status"] == "Final"
    assert stored_game["data"]["home_score"] == 110
    assert stored_game["labels"]["league"] == "NBA"
    
    logger.success("Verification Passed: Full Pipeline (Dict -> Parser -> Object -> DB).")

if __name__ == "__main__":
    try:
        test_parser_flow()
    except Exception as e:
        logger.exception("Test Failed")
        sys.exit(1)
