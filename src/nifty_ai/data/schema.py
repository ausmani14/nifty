"""Normalized data schemas and provenance models for NIFTY AI.

Defines standardized data representations across market, macro, and news pillars,
ensuring strict provenance tracking, timezone awareness, and provider decoupling.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ProviderStatus(str, Enum):
    """Lifecycle status of a data provider integration."""
    PLANNED = "planned"
    DEVELOPMENT = "development"
    REFERENCE = "reference"
    PRODUCTION = "production"


class ProviderTier(str, Enum):
    """Categorization tier distinguishing free, official, and professional sources."""
    FREE = "free"
    PROFESSIONAL = "professional"
    OFFICIAL = "official"


class DataFrequency(str, Enum):
    """Granularity of the recorded market or macro data."""
    TICK = "tick"
    MINUTE = "minute"
    HOURLY = "hourly"
    DAILY = "daily"


@dataclass(frozen=True)
class ProvenanceMetadata:
    """Immutable provenance record tracking data lineage and auditability."""
    provider: str
    source_identifier: str
    retrieval_timestamp: datetime
    source_timestamp: Optional[datetime] = None
    timezone: str = "Asia/Kolkata"
    data_frequency: DataFrequency = DataFrequency.DAILY
    dataset_version: Optional[str] = None
    tier: ProviderTier = ProviderTier.FREE
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider:
            raise ValueError("Provenance provider must not be empty.")
        if not self.source_identifier:
            raise ValueError("Provenance source_identifier must not be empty.")
        if self.retrieval_timestamp.tzinfo is None:
            raise ValueError("retrieval_timestamp must be timezone-aware.")
        if self.source_timestamp is not None and self.source_timestamp.tzinfo is None:
            raise ValueError("source_timestamp must be timezone-aware when provided.")


@dataclass(frozen=True)
class NormalizedMarketRecord:
    """Standardized bar record for equity index and security prices."""
    timestamp: datetime
    trading_date: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    provenance: ProvenanceMetadata
    volume: Optional[float] = None
    is_adjusted: bool = False
    adjustment_factor: Optional[float] = None
    status: str = "finalized"

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("Market record timestamp must be timezone-aware.")
        if not self.symbol:
            raise ValueError("Symbol must not be empty.")


@dataclass(frozen=True)
class NormalizedMacroRecord:
    """Standardized observation for macroeconomic and global indicators."""
    timestamp: datetime
    indicator_name: str
    value: float
    provenance: ProvenanceMetadata
    effective_date: Optional[date] = None
    unit: Optional[str] = None

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("Macro record timestamp must be timezone-aware.")
        if not self.indicator_name:
            raise ValueError("Indicator name must not be empty.")


@dataclass(frozen=True)
class NormalizedNewsRecord:
    """Standardized representation for financial news and economic intelligence."""
    article_id: str
    headline: str
    publication_timestamp: datetime
    provenance: ProvenanceMetadata
    summary: Optional[str] = None
    body: Optional[str] = None
    url: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    sector: Optional[str] = None
    sentiment_score: Optional[float] = None
    event_type: Optional[str] = None
    importance: int = 1
    novelty_score: Optional[float] = None

    def __post_init__(self) -> None:
        if self.publication_timestamp.tzinfo is None:
            raise ValueError("News publication_timestamp must be timezone-aware.")
        if not self.headline:
            raise ValueError("News headline must not be empty.")
        if self.sentiment_score is not None and not (-1.0 <= self.sentiment_score <= 1.0):
            raise ValueError("sentiment_score must fall between -1.0 and +1.0.")
        if not (1 <= self.importance <= 5):
            raise ValueError("importance must be on a scale of 1 to 5.")


__all__ = [
    "ProviderStatus",
    "ProviderTier",
    "DataFrequency",
    "ProvenanceMetadata",
    "NormalizedMarketRecord",
    "NormalizedMacroRecord",
    "NormalizedNewsRecord",
]
