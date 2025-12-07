"""
NBA Schedule Fetcher - Example plugin using the Golden Template.
Moved from ingestion/fetcher.py to follow proper separation.
"""
from src.ingestion.fetcher import BaseFetcher


class NBAScheduleFetcher(BaseFetcher):
    """
    Fetches today's NBA scoreboard data.
    Example implementation of a concrete fetcher using the Golden Template.
    """
    def __init__(self):
        url = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
        super().__init__(url)
