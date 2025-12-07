from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

class ParsingResult:
    """
    Standardized output object for all parsers.
    Matches the SilverEntity schema.
    """
    def __init__(
        self,
        source: str,
        type: str,
        external_id: str,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        status: str = "Unknown",
        name: str = "Unknown",
        labels: Dict[str, str] = None
    ):
        self.source = source
        self.type = type
        self.external_id = external_id
        self.data = data
        self.timestamp = timestamp or datetime.utcnow()
        self.status = status
        self.name = name
        self.labels = labels or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "type": self.type,
            "external_id": self.external_id,
            "data": self.data,
            "timestamp": self.timestamp,
            "status": self.status,
            "name": self.name,
            "labels": self.labels
        }

class BaseParser(ABC):
    """
    The Contract: All parsers must inherit from this.
    Input: A Raw Bronze Record (Metadata + Payload).
    Output: A list of Standardized Silver Entities.
    """
    
    @abstractmethod
    def parse(self, message: Dict[str, Any]) -> List[ParsingResult]:
        """
        Parses a single bronze record into N silver entities.
        One raw file might contain 10 games, so we return a list.
        """
        pass
