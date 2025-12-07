from src.ingestion.fetcher import NBAScheduleFetcher, BaseFetcher
from src.storage.bronze import BronzeStorage
from src.processing.parser import SimpleParser
from loguru import logger
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def main():
    logger.info("Starting Pipeline (Mode: SQLite-Backed)...")

    try:
        # Initialize Shared Storage
        storage = BronzeStorage()

        # Step 1: Ingestion
        logger.info("Initializing Fetcher...")
        fetcher = NBAScheduleFetcher()
        
        try:
            raw_data = fetcher.fetch()
            source_name = "nba_scoreboard"
            logger.info("Successfully fetched NBA Scoreboard data")
        except Exception as e:
            logger.warning(f"NBA fetch failed ({e}), falling back to dummy...")
            fetcher = BaseFetcher("https://jsonplaceholder.typicode.com/todos/1")
            raw_data = fetcher.fetch()
            source_name = "fallback_source"

        # Step 2: Bronze Storage (DB)
        # Returns an Integer ID, not a file path
        record_id = storage.save(raw_data, source_name)

        # Step 3: Processing (DB)
        parser = SimpleParser(storage)
        result = parser.parse(record_id)

        logger.success(f"Pipeline complete! Processed Record ID: {record_id}")
        logger.info(f"Parsed Result: {result}")
    
    except Exception as e:
        logger.exception("Pipeline execution failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
