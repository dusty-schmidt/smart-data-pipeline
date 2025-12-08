from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from src.ingestion.fetcher import BaseFetcher
from src.processing.base import BaseParser, ParsingResult


class WwwScrapethissiteComFetcher(BaseFetcher):
    """Fetcher for www.scrapethissite.com simple page."""

    SOURCE_NAME = "www_scrapethissite_com"
    BASE_URL = "https://www.scrapethissite.com/pages/simple/"

    def fetch(self) -> Dict[str, Any]:
        """Retrieve the HTML content from the source."""
        response = requests.get(self.BASE_URL, timeout=30)
        response.raise_for_status()
        return {
            "source": self.SOURCE_NAME,
            "url": self.BASE_URL,
            "html": response.text,
        }


class WwwScrapethissiteComParser(BaseParser):
    """Parser that extracts country data from www.scrapethissite.com simple page."""

    SOURCE_NAME = "www_scrapethissite_com"
    ROOT_SELECTOR = "div.country"
    FIELDS = {
        "name": "h3.country-name",
        "capital": "span.capital",
        "population": "span.population",
        "area": "span.area",
    }
    DOMAIN_LABELS = {"topic": "countries data"}

    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        """Parse the HTML and return a list of ParsingResult objects."""
        html = message.get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        items = soup.select(self.ROOT_SELECTOR)

        results: List[ParsingResult] = []

        for item in items:
            record: Dict[str, Any] = {"source": self.SOURCE_NAME}
            # extract defined fields
            for field_name, selector in self.FIELDS.items():
                element = item.select_one(selector)
                record[field_name] = element.get_text(strip=True) if element else None

            # attach domain labels
            record.update(self.DOMAIN_LABELS)

            results.append(ParsingResult(data=record))

        return results