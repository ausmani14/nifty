"""Schema definitions for Phase 7 market context data layer.

Defines standardized data representations for Indian and global market context variables,
ensuring strict observation vs. availability timestamping, provenance, and timezone tracking.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from nifty_ai.data.schema import DataFrequency, ProvenanceMetadata, ProviderTier


class ContextCategory(str, Enum):
    """Categorization of context variables."""
    DOMESTIC_EQUITY = "domestic_equity"
    DOMESTIC_VOLATILITY = "domestic_volatility"
    DOMESTIC_FX = "domestic_fx"
    DOMESTIC_RATES = "domestic_rates"
    GLOBAL_EQUITY = "global_equity"
    GLOBAL_VOLATILITY = "global_volatility"
    GLOBAL_RATES = "global_rates"
    GLOBAL_COMMODITIES = "global_commodities"
    GLOBAL_FX = "global_fx"


class MissingPolicy(str, Enum):
    """Policy for handling missing observations in point-in-time joins."""
    NO_FILL = "no_fill"
    FORWARD_FILL_1D = "forward_fill_1d"
    FORWARD_FILL_CALENDAR = "forward_fill_calendar"
    QUARANTINE = "quarantine"


class AvailabilityTimestampType(str, Enum):
    """Provenance classification of availability timestamps."""
    OBSERVED = "observed"
    DOCUMENTED_SCHEDULE = "documented_schedule"
    ASSUMED_SCHEDULE = "assumed_schedule"
    RETRIEVAL_TIME = "retrieval_time"


@dataclass(frozen=True)
class AvailabilitySpec:
    """Explicit schedule definition for when a market variable becomes legitimately available.

    Provenance fields explicitly separate:
    - instrument_timestamp_description: when the exchange/index finalizes the value
    - provider_availability_basis: how we estimate when the provider (Yahoo Finance) publishes the value
    - provider_availability_observed: whether we have empirical proof of provider publication timing
    - snapshot_a_eligibility_note: documents assumption-dependent boundary cases for Snapshot A
    """
    variable_name: str
    instrument: str
    category: ContextCategory
    native_timezone: str
    market_close_time: time
    lag_minutes_to_availability: int = 0
    missing_policy: MissingPolicy = MissingPolicy.FORWARD_FILL_CALENDAR
    provider_tier: ProviderTier = ProviderTier.FREE
    availability_timestamp_type: AvailabilityTimestampType = AvailabilityTimestampType.ASSUMED_SCHEDULE
    instrument_timestamp_description: str = ""
    provider_availability_basis: str = ""
    provider_availability_observed: bool = False
    snapshot_a_eligibility_note: Optional[str] = None
    notes: Optional[str] = None


@dataclass(frozen=True)
class ContextObservation:
    """A single normalized point-in-time observation of a market context variable."""
    variable_name: str
    instrument: str
    observation_date: date
    observation_timestamp: datetime
    availability_timestamp: datetime
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: float
    volume: Optional[float]
    provenance: ProvenanceMetadata
    availability_timestamp_type: AvailabilityTimestampType = AvailabilityTimestampType.ASSUMED_SCHEDULE

    def __post_init__(self) -> None:
        if self.observation_timestamp.tzinfo is None:
            raise ValueError("observation_timestamp must be timezone-aware.")
        if self.availability_timestamp.tzinfo is None:
            raise ValueError("availability_timestamp must be timezone-aware.")
        if self.observation_timestamp > self.availability_timestamp:
            raise ValueError("observation_timestamp cannot occur after availability_timestamp.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_name": self.variable_name,
            "instrument": self.instrument,
            "observation_date": self.observation_date.isoformat(),
            "observation_timestamp": self.observation_timestamp.isoformat(),
            "availability_timestamp": self.availability_timestamp.isoformat(),
            "availability_timestamp_type": self.availability_timestamp_type.value,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "provider": self.provenance.provider,
            "source_identifier": self.provenance.source_identifier,
        }


__all__ = [
    "ContextCategory",
    "MissingPolicy",
    "AvailabilityTimestampType",
    "AvailabilitySpec",
    "ContextObservation",
]
