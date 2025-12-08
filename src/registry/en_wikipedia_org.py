import requests
from typing import Any, Dict, List

from bs4 import BeautifulSoup

from src.ingestion.fetcher import BaseFetcher
from src.processing.base import BaseParser, ParsingResult


class EnWikipediaOrgFetcher(BaseFetcher):
    """
    Fetcher for the Wikipedia page containing the list of S&P 500 companies.
    """

    def __init__(self) -> None:
        self.base_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        self.fetch_strategy = "http"

    def fetch(self) -> Dict[str, Any]:
        """
        Retrieves the HTML content of the target page.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the raw HTML under the key ``html``.
        """
        response = requests.get(self.base_url, timeout=30)
        response.raise_for_status()
        return {"html": response.text}


class EnWikipediaOrgParser(BaseParser):
    """
    Parser that extracts S&P 500 constituent data from the Wikipedia HTML table.
    """

    # Blueprint configuration
    _ROOT_SELECTOR = "table.wikitable.sortable tbody tr"
    _FIELD_SELECTORS = {
        "symbol": "td:nth-child(1) a",
        "security": "td:nth-child(2) a",
        "gics_sector": "td:nth-child(4)",
        "gics_sub_industry": "td:nth-child(5)",
        "headquarters_location": "td:nth-child(6)",
        "date_first_added": "td:nth-child(7)",
        "cik": "td:nth-child(8)",
        "founded": "td:nth-child(9)",
    }

    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        """
        Parses the HTML supplied by the fetcher and extracts each row as a
        ``ParsingResult``.

        Parameters
        ----------
        message : Dict[str, Any]
            The payload produced by :class:`EnWikipediaOrgFetcher`. Must contain
            an ``html`` key with the page source.

        Returns
        -------
        List[ParsingResult]
            A list where each element represents a company record extracted from
            the table.
        """
        html = message.get("html", "")
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select(self._ROOT_SELECTOR)

        results: List[ParsingResult] = []

        for row in rows:
            record: Dict[str, Any] = {}
            for field_name, selector in self._FIELD_SELECTORS.items():
                element = row.select_one(selector)
                # Use empty string when element is missing to keep schema consistent
                value = element.get_text(strip=True) if element else ""
                record[field_name] = value

            # Attach static domain labels as metadata if needed
            record["_domain_labels"] = {"topic": "Finance/Stock Market"}

            results.append(ParsingResult(data=record))

        return results