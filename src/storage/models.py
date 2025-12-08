from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# =============================================================================
# Tier 2: Orchestration Tables
# =============================================================================

class TaskRecord(Base):
    """Persistent task queue entry for orchestration."""
    __tablename__ = 'task_queue'
    
    id = Column(Integer, primary_key=True)
    task_type = Column(String, index=True)      # ADD_SOURCE, FIX_SOURCE, REFRESH_SOURCE
    target = Column(String, index=True)         # URL or source_name
    state = Column(String, index=True, default='PENDING')  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    priority = Column(Integer, default=5)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)


class SourceHealthRecord(Base):
    """Health tracking for data sources."""
    __tablename__ = 'source_health'
    
    id = Column(Integer, primary_key=True)
    source_name = Column(String, unique=True, index=True)
    state = Column(String, default='ACTIVE', index=True)  # ACTIVE, DEGRADED, QUARANTINED, DEAD
    last_success_at = Column(DateTime, nullable=True)
    last_failure_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    fix_attempts_today = Column(Integer, default=0)
    fix_attempts_reset_at = Column(DateTime, nullable=True)
    quarantine_until = Column(DateTime, nullable=True)
    # For HTML diff detection
    last_html_hash = Column(String, nullable=True)


class FixHistoryRecord(Base):
    """History of fix attempts for auditing."""
    __tablename__ = 'fix_history'
    
    id = Column(Integer, primary_key=True)
    source_name = Column(String, index=True)
    error_type = Column(String)
    error_message = Column(Text, nullable=True)
    root_cause = Column(Text, nullable=True)
    patch_applied = Column(Text, nullable=True)  # Code diff or description
    success = Column(Boolean)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# =============================================================================
# Tier 0: Storage Tables
# =============================================================================

class BronzeLog(Base):
    __tablename__ = 'bronze_logs'
    
    id = Column(Integer, primary_key=True)
    source = Column(String, index=True)
    ingested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    version = Column(String, default="1.0")
    payload = Column(JSON)
    
    @property
    def file_path(self):
        return str(self.id)

class SilverEntity(Base):
    """
    A domain-agnostic representation of a refined data object.
    Could be a Game, a Stock Ticker, a Weather Report, or a User.
    """
    __tablename__ = 'silver_entities'
    __table_args__ = (
        # Ensure we don't have duplicates for the same external item from the same source
        UniqueConstraint('source', 'type', 'external_id', name='uq_source_type_extid'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core Identity
    source = Column(String, index=True)     # e.g. "nba", "alpaca_finance"
    type = Column(String, index=True)       # e.g. "game", "quote", "news"
    external_id = Column(String, index=True) # The ID in the remote system
    
    # Common Metadata (elevated for querying)
    timestamp = Column(DateTime, index=True, nullable=True) # Event time, Publication time, etc.
    status = Column(String, index=True, nullable=True)      # Active, Final, Closed, Published
    name = Column(String, nullable=True)                    # Display name / Headline
    
    # Domain Tagging
    labels = Column(JSON, default=dict)                     # Flexible Metadata (e.g. {domain: sports})

    # Domain Specifics (The content)
    data = Column(JSON) # Structured, cleaned data (e.g. scores, teams, prices)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
