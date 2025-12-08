from typing import Any, Dict, List
import requests
from bs4 import BeautifulSoup

from src.ingestion.fetcher import BaseFetcher
from src.processing.base import BaseParser, ParsingResult


class www_scrapethissite_comFetcher(BaseFetcher):
    """
    Fetcher for www.scrapethissite.com simple country list page.
    Retrieves the page HTML using HTTP GET.
    """

    def __init__(self) -> None:
        self.base_url: str = "https://www.scrapethissite.com/pages/simple/"

    def fetch(self) -> Dict[str, Any]:
        """
        Perform an HTTP GET request to the configured base URL and return
        a dictionary containing the raw HTML payload.

        Returns
        -------
        Dict[str, Any]
            A dictionary with at least an ``html`` key holding the page content.
        """
        response = requests.get(self.base_url, timeout=30)
        response.raise_for_status()
        return {"html": response.text, "source_url": self.base_url}


class www_scrapethissite_comParser(BaseParser):
    """
    Parser for the HTML returned by ``www_scrapethissite_comFetcher``.
    Extracts country information from the table rows using the selectors
    defined in the blueprint.
    """

    # Blueprint‑derived configuration
    _root_selector: str = "table tbody tr"
    _field_selectors: Dict[str, str] = {
        "country": "td.country",
        "capital": "td.capital",
        "population": "td.population",
        "area": "td.area",
    }
    _domain_labels: Dict[str, str] = {"topic": "countries data"}

    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        """
        Parse the HTML payload and produce a list of ``ParsingResult`` objects,
        one per country row.

        Parameters
        ----------
        message : Dict[str, Any]
            Expected to contain an ``html`` key with the page source.

        Returns
        -------
        List[ParsingResult]
            Parsed records wrapped in ``ParsingResult`` instances.
        """
        html: str = message.get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select(self._root_selector)

        results: List[ParsingResult] = []

        for row in rows:
            extracted: Dict[str, Any] = {}
            for field_name, selector in self._field_selectors.items():
                element = row.select_one(selector)
                extracted[field_name] = element.get_text(strip=True) if element else None

            # Attach domain labels for downstream enrichment
            result = ParsingResult(
                data=extracted,
                labels=self._domain_labels,
                source="www_scrapethissite_com",
                raw=row,
            )
            results.append(result)

        return results