"""
Source Health Tracking - Monitors source status for Tier 2 Autonomy

Tracks success/failure rates, manages quarantine, and provides health status.
"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from enum import Enum

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from src.storage.models import Base, SourceHealthRecord


class SourceState(Enum):
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    QUARANTINED = "QUARANTINED"
    DEAD = "DEAD"


@dataclass
class SourceHealth:
    """Health status of a data source."""
    source_name: str
    state: SourceState
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_error: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    fix_attempts_today: int = 0
    quarantine_until: Optional[datetime] = None
    
    @classmethod
    def from_record(cls, record: SourceHealthRecord) -> "SourceHealth":
        """Convert SQLAlchemy record to SourceHealth dataclass."""
        return cls(
            source_name=record.source_name,
            state=SourceState(record.state),
            last_success_at=record.last_success_at,
            last_failure_at=record.last_failure_at,
            last_error=record.last_error,
            success_count=record.success_count,
            failure_count=record.failure_count,
            consecutive_failures=record.consecutive_failures,
            fix_attempts_today=record.fix_attempts_today,
            quarantine_until=record.quarantine_until,
        )
    
    @property
    def is_healthy(self) -> bool:
        """Returns True if source is ACTIVE."""
        return self.state == SourceState.ACTIVE
    
    @property
    def needs_fix(self) -> bool:
        """Returns True if source needs repair."""
        return self.state in (SourceState.DEGRADED, SourceState.QUARANTINED)


# Circuit breaker settings
MAX_FIX_ATTEMPTS_PER_DAY = 3
QUARANTINE_THRESHOLD = 3  # consecutive failures before quarantine
DEFAULT_QUARANTINE_HOURS = 24


class HealthTracker:
    """
    Tracks health status of all data sources.
    
    Responsibilities:
    - Record successes and failures
    - Calculate health scores
    - Manage quarantine state (3-strikes rule)
    - Provide circuit breaker for fix attempts
    """
    
    def __init__(self, db_path: str = "data/pipeline.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def _get_or_create_record(self, session, source_name: str) -> SourceHealthRecord:
        """Get existing record or create new one."""
        record = session.query(SourceHealthRecord).filter(
            SourceHealthRecord.source_name == source_name
        ).first()
        
        if record is None:
            record = SourceHealthRecord(
                source_name=source_name,
                state=SourceState.ACTIVE.value,
            )
            session.add(record)
            session.flush()
        
        return record
    
    def _reset_daily_counters_if_needed(self, record: SourceHealthRecord) -> None:
        """Reset fix_attempts_today if we're in a new day."""
        now = datetime.now(timezone.utc)
        if record.fix_attempts_reset_at is None:
            record.fix_attempts_reset_at = now
            return
        
        # Reset if last reset was before today
        if record.fix_attempts_reset_at.date() < now.date():
            record.fix_attempts_today = 0
            record.fix_attempts_reset_at = now
    
    def record_success(self, source_name: str) -> None:
        """
        Record a successful scrape.
        
        Resets consecutive failures and sets state to ACTIVE.
        """
        session = self.Session()
        try:
            record = self._get_or_create_record(session, source_name)
            self._reset_daily_counters_if_needed(record)
            
            record.success_count += 1
            record.consecutive_failures = 0
            record.last_success_at = datetime.now(timezone.utc)
            record.state = SourceState.ACTIVE.value
            record.quarantine_until = None
            
            session.commit()
            logger.debug(f"[{source_name}] Success recorded")
        finally:
            session.close()
    
    def record_failure(self, source_name: str, error: str) -> SourceHealth:
        """
        Record a failed scrape.
        
        Implements 3-strikes quarantine rule:
        - 1 failure: stays ACTIVE
        - 2 failures: becomes DEGRADED
        - 3+ failures: becomes QUARANTINED
        
        Returns updated health status.
        """
        session = self.Session()
        try:
            record = self._get_or_create_record(session, source_name)
            self._reset_daily_counters_if_needed(record)
            
            record.failure_count += 1
            record.consecutive_failures += 1
            record.last_failure_at = datetime.now(timezone.utc)
            record.last_error = error[:1000] if error else None  # Truncate long errors
            
            # Apply 3-strikes rule
            if record.consecutive_failures >= QUARANTINE_THRESHOLD:
                record.state = SourceState.QUARANTINED.value
                record.quarantine_until = datetime.now(timezone.utc) + timedelta(hours=DEFAULT_QUARANTINE_HOURS)
                logger.warning(f"[{source_name}] QUARANTINED after {record.consecutive_failures} failures")
            elif record.consecutive_failures >= 2:
                record.state = SourceState.DEGRADED.value
                logger.warning(f"[{source_name}] DEGRADED ({record.consecutive_failures} failures)")
            
            session.commit()
            session.refresh(record)
            return SourceHealth.from_record(record)
        finally:
            session.close()
    
    def get_health(self, source_name: str) -> Optional[SourceHealth]:
        """Get current health status for a source."""
        session = self.Session()
        try:
            record = session.query(SourceHealthRecord).filter(
                SourceHealthRecord.source_name == source_name
            ).first()
            
            if record is None:
                return None
            
            return SourceHealth.from_record(record)
        finally:
            session.close()
    
    def quarantine(self, source_name: str, hours: int = DEFAULT_QUARANTINE_HOURS) -> None:
        """Manually put source in quarantine."""
        session = self.Session()
        try:
            record = self._get_or_create_record(session, source_name)
            record.state = SourceState.QUARANTINED.value
            record.quarantine_until = datetime.now(timezone.utc) + timedelta(hours=hours)
            session.commit()
            logger.warning(f"[{source_name}] Manually quarantined for {hours}h")
        finally:
            session.close()
    
    def is_quarantined(self, source_name: str) -> bool:
        """Check if source is currently quarantined."""
        session = self.Session()
        try:
            record = session.query(SourceHealthRecord).filter(
                SourceHealthRecord.source_name == source_name
            ).first()
            
            if record is None:
                return False
            
            if record.state != SourceState.QUARANTINED.value:
                return False
            
            # Check if quarantine has expired
            if record.quarantine_until and record.quarantine_until < datetime.now(timezone.utc):
                # Auto-release from quarantine
                record.state = SourceState.DEGRADED.value
                record.quarantine_until = None
                session.commit()
                logger.info(f"[{source_name}] Released from quarantine")
                return False
            
            return True
        finally:
            session.close()
    
    def get_degraded_sources(self) -> List[SourceHealth]:
        """Get all sources that need attention (DEGRADED or QUARANTINED)."""
        session = self.Session()
        try:
            records = session.query(SourceHealthRecord).filter(
                SourceHealthRecord.state.in_([
                    SourceState.DEGRADED.value,
                    SourceState.QUARANTINED.value
                ])
            ).all()
            return [SourceHealth.from_record(r) for r in records]
        finally:
            session.close()
    
    def get_all_sources(self) -> List[SourceHealth]:
        """Get health status of all tracked sources."""
        session = self.Session()
        try:
            records = session.query(SourceHealthRecord).order_by(
                SourceHealthRecord.source_name
            ).all()
            return [SourceHealth.from_record(r) for r in records]
        finally:
            session.close()
    
    def can_attempt_fix(self, source_name: str) -> bool:
        """
        Check if we can attempt a fix (circuit breaker).
        
        Returns False if we've exceeded MAX_FIX_ATTEMPTS_PER_DAY.
        """
        session = self.Session()
        try:
            record = self._get_or_create_record(session, source_name)
            self._reset_daily_counters_if_needed(record)
            session.commit()
            return record.fix_attempts_today < MAX_FIX_ATTEMPTS_PER_DAY
        finally:
            session.close()
    
    def record_fix_attempt(self, source_name: str) -> None:
        """Record that a fix attempt was made."""
        session = self.Session()
        try:
            record = self._get_or_create_record(session, source_name)
            self._reset_daily_counters_if_needed(record)
            record.fix_attempts_today += 1
            session.commit()
            logger.info(f"[{source_name}] Fix attempt {record.fix_attempts_today}/{MAX_FIX_ATTEMPTS_PER_DAY}")
        finally:
            session.close()
    
    def mark_dead(self, source_name: str) -> None:
        """Mark a source as permanently dead (manual intervention required)."""
        session = self.Session()
        try:
            record = self._get_or_create_record(session, source_name)
            record.state = SourceState.DEAD.value
            session.commit()
            logger.error(f"[{source_name}] Marked as DEAD")
        finally:
            session.close()
    
    def update_html_hash(self, source_name: str, html_hash: str) -> None:
        """Store the hash of the last successful HTML for diff detection."""
        session = self.Session()
        try:
            record = self._get_or_create_record(session, source_name)
            record.last_html_hash = html_hash
            session.commit()
        finally:
            session.close()
    
    def get_html_hash(self, source_name: str) -> Optional[str]:
        """Get the stored HTML hash for diff detection."""
        session = self.Session()
        try:
            record = session.query(SourceHealthRecord).filter(
                SourceHealthRecord.source_name == source_name
            ).first()
            return record.last_html_hash if record else None
        finally:
            session.close()
