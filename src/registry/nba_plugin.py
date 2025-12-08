from typing import Dict, Any, List
from datetime import datetime, timezone

from src.processing.base import BaseParser, ParsingResult
from loguru import logger

class NBAScoreboardParser(BaseParser):
    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        payload = message.get("payload", {})
        metadata = message.get("metadata", {})
        
        scoreboard = payload.get("scoreboard", {})
        games = scoreboard.get("games", [])
        
        results = []
        for game in games:
            try:
                # Extract Core Identity
                game_id = game.get("gameId")
                home_team = game.get("homeTeam", {})
                away_team = game.get("awayTeam", {})
                
                # Construct Name
                name = f"{away_team.get('teamTricode')} @ {home_team.get('teamTricode')}"
                
                # Construct Status
                # NBA uses 1=Scheduled, 2=Live, 3=Final usually, but let's stick to text if avail
                status_text = game.get("gameStatusText", "Unknown")
                
                # Construct Data Payload (The Cleaned Version)
                data_payload = {
                    "home_score": home_team.get("score"),
                    "away_score": away_team.get("score"),
                    "period": game.get("period"),
                    "clock": game.get("gameClock"),
                }
                
                # Create Result
                result = ParsingResult(
                    source="nba",
                    type="game",
                    external_id=game_id,
                    data=data_payload,
                    status=status_text,
                    name=name,
                    timestamp=datetime.now(timezone.utc), # Ideally parse gameTimeUTC
                    labels={
                        "league": "NBA",
                        "season": "2024-25", # Could be dynamic
                        "domain": "sports"
                    }
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to parse game entry: {e}")
                continue
                
        logger.info(f"Extracted {len(results)} games from {metadata.get('source')} payload.")
        return results
