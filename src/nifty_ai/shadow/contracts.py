"""Data contracts, schemas, and provenance specifications for Phase 14 Shadow System.

Enforces zero lookahead, point-in-time constraints, immutable schemas, and 
tamper-evident provenance.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")

# Exact registered 63 features matching Snapshot B T0 Primary Model
CANONICAL_PRICE_FEATURES_45: tuple[str, ...] = (
    "ret_1d", "ret_2d", "ret_3d", "ret_5d", "ret_10d", "ret_20d",
    "ret_lag_1", "ret_lag_2", "ret_lag_3", "ret_lag_5", "ret_lag_10",
    "sma_5", "close_to_sma_5", "sma_10", "close_to_sma_10",
    "sma_20", "close_to_sma_20", "sma_50", "close_to_sma_50",
    "sma_100", "close_to_sma_100", "sma_200", "close_to_sma_200",
    "mom_5d", "mom_10d", "mom_20d", "mom_60d",
    "volatility_5d", "volatility_10d", "volatility_20d", "volatility_60d",
    "volatility_ann_20d", "hl_range_pct", "close_pos_in_range",
    "open_to_close_ret", "high_to_close_dist", "low_to_close_dist",
    "sma_ratio_20_50", "sma_ratio_50_200", "trend_slope_20d",
    "day_of_week", "day_of_month", "month", "quarter", "is_month_end"
)

# Canonical partitions: 40 price-derived + 5 deterministic calendar
CANONICAL_PRICE_DERIVED_40: tuple[str, ...] = CANONICAL_PRICE_FEATURES_45[:40]
CANONICAL_CALENDAR_5: tuple[str, ...] = CANONICAL_PRICE_FEATURES_45[40:45]

CANONICAL_CONTEXT_FEATURES_18: tuple[str, ...] = (
    "ctx_ret_1d_nifty_bank", "ctx_ret_1d_sp500", "ctx_ret_1d_nasdaq",
    "ctx_ret_1d_dow_jones", "ctx_ret_1d_brent_crude", "ctx_ret_1d_wti_crude",
    "ctx_ret_1d_gold", "ctx_ret_1d_dxy", "ctx_ret_1d_nikkei_225",
    "ctx_ret_1d_hang_seng", "ctx_ret_1d_ftse_100", "ctx_diff_1d_india_vix",
    "ctx_diff_1d_us_vix", "ctx_diff_1d_india_10y_yield",
    "ctx_diff_1d_us_10y_yield", "ctx_diff_1d_usd_inr",
    "ctx_level_india_vix", "ctx_level_us_vix"
)

# Canonical source mappings for market context (16 instruments, 18 features)
CANONICAL_CONTEXT_MAPPING: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "^NSEBANK": ("market_context", ("ctx_ret_1d_nifty_bank",)),
    "^GSPC": ("market_context", ("ctx_ret_1d_sp500",)),
    "^IXIC": ("market_context", ("ctx_ret_1d_nasdaq",)),
    "^DJI": ("market_context", ("ctx_ret_1d_dow_jones",)),
    "BZ=F": ("market_context", ("ctx_ret_1d_brent_crude",)),
    "CL=F": ("market_context", ("ctx_ret_1d_wti_crude",)),
    "GC=F": ("market_context", ("ctx_ret_1d_gold",)),
    "DX-Y.NYB": ("market_context", ("ctx_ret_1d_dxy",)),
    "^N225": ("market_context", ("ctx_ret_1d_nikkei_225",)),
    "^HSI": ("market_context", ("ctx_ret_1d_hang_seng",)),
    "^FTSE": ("market_context", ("ctx_ret_1d_ftse_100",)),
    "^INDIAVIX": ("market_context", ("ctx_diff_1d_india_vix", "ctx_level_india_vix")),
    "^VIX": ("market_context", ("ctx_diff_1d_us_vix", "ctx_level_us_vix")),
    "IN10YT=RR": ("market_context", ("ctx_diff_1d_india_10y_yield",)),
    "^TNX": ("market_context", ("ctx_diff_1d_us_10y_yield",)),
    "INR=X": ("market_context", ("ctx_diff_1d_usd_inr",)),
}

CANONICAL_FEATURES_63: tuple[str, ...] = CANONICAL_PRICE_FEATURES_45 + CANONICAL_CONTEXT_FEATURES_18

# Canonical native timezone per required instrument (18 canonical instruments)
CANONICAL_TIMEZONES: Dict[str, str] = {
    "^NSEI": "Asia/Kolkata",
    "CALENDAR": "Asia/Kolkata",
    "^NSEBANK": "Asia/Kolkata",
    "^INDIAVIX": "Asia/Kolkata",
    "IN10YT=RR": "Asia/Kolkata",
    "INR=X": "Asia/Kolkata",
    "^GSPC": "America/New_York",
    "^IXIC": "America/New_York",
    "^DJI": "America/New_York",
    "CL=F": "America/New_York",
    "GC=F": "America/New_York",
    "DX-Y.NYB": "America/New_York",
    "^VIX": "America/New_York",
    "^TNX": "America/New_York",
    "BZ=F": "Europe/London",
    "^FTSE": "Europe/London",
    "^N225": "Asia/Tokyo",
    "^HSI": "Asia/Hong_Kong",
}

# Explicit trusted live providers permitted for PROSPECTIVE_LIVE_CAPTURE
TRUSTED_LIVE_PROVIDERS: set[str] = {
    "nse_official_direct_feed",
    "authorized_exchange_adapter",
    "canonical_source_provider",
    "production_market_feed",
}

# Evidence retention indicator when durable cloud storage is not attached
EVIDENCE_RETENTION_BLOCKED: str = "EVIDENCE_RETENTION_BLOCKED"

CANONICAL_MODEL_SHA256: str = "981bbc806160090e339093686c61b660368427860451d9720824720dd031c5df"
CANONICAL_META_SHA256: str = "d64fee485721cc4e2596e8fd10039d9ea2a7e41ce84b90e19b6bd994ea5d7f33"

# Canonical activation boundary timestamp (Phase 14 Protocol Freeze)
ACTIVATION_BOUNDARY_UTC: datetime = datetime(2026, 10, 31, 14, 47, 0, tzinfo=timezone.utc)


class ProvenanceType(str, Enum):
    PROSPECTIVE_LIVE_CAPTURE = "prospective_live_capture"
    OPERATOR_ATTESTED_PROSPECTIVE = "operator_attested_prospective"
    HISTORICAL_BACKFILL = "historical_backfill"
    RETROSPECTIVE_REFERENCE = "retrospective_reference"
    INVALID_OR_QUARANTINED = "invalid_or_quarantined"


class ValidationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


class LedgerStatus(str, Enum):
    RECORDED = "RECORDED"
    DUPLICATE_IGNORED = "DUPLICATE_IGNORED"
    SUPERSEDED = "SUPERSEDED"


OPERATOR_ATTESTATION_PROTOCOL_VERSION: str = "NIFTY_AI_OPERATOR_ATTESTATION_V2"


@dataclass(frozen=True)
class AuthorizedOperatorKey:
    operator_id: str
    key_id: str
    public_key_hex: str
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_revoked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "key_id": self.key_id,
            "public_key_hex": self.public_key_hex,
            "valid_from": self.valid_from.isoformat(),
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "is_revoked": self.is_revoked,
        }


@dataclass(frozen=True)
class OperatorAttestation:
    operator_id: str
    key_id: str
    signature: str
    signed_timestamp: datetime
    public_key: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "key_id": self.key_id,
            "signature": self.signature,
            "signed_timestamp": self.signed_timestamp.isoformat(),
            "public_key": self.public_key,
        }


@dataclass(frozen=True)
class InstrumentSourceRecord:
    source_id: str
    instrument_symbol: str
    feature_family: str
    feature_names: List[str]
    observation_time: datetime
    availability_time: datetime
    ingestion_time: datetime
    timezone: str = "Asia/Kolkata"
    raw_payload_hash: str = ""
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE
    staleness_seconds: float = 0.0
    raw_payload_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "instrument_symbol": self.instrument_symbol,
            "feature_family": self.feature_family,
            "feature_names": list(self.feature_names),
            "observation_time": self.observation_time.isoformat(),
            "availability_time": self.availability_time.isoformat(),
            "ingestion_time": self.ingestion_time.isoformat(),
            "timezone": self.timezone,
            "raw_payload_hash": self.raw_payload_hash,
            "provenance_type": self.provenance_type.value,
            "staleness_seconds": self.staleness_seconds,
            "raw_payload_ref": self.raw_payload_ref,
        }


@dataclass(frozen=True)
class SourceProvenance:
    source_id: str
    observation_time: datetime
    availability_time: datetime
    ingestion_time: datetime
    timezone: str = "Asia/Kolkata"
    raw_data_hash: str = ""
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE
    quarantine_reason: Optional[str] = None
    source_manifest: List[InstrumentSourceRecord] = field(default_factory=list)
    attestation: Optional[OperatorAttestation] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "observation_time": self.observation_time.isoformat(),
            "availability_time": self.availability_time.isoformat(),
            "ingestion_time": self.ingestion_time.isoformat(),
            "timezone": self.timezone,
            "raw_data_hash": self.raw_data_hash,
            "provenance_type": self.provenance_type.value,
            "quarantine_reason": self.quarantine_reason,
            "source_manifest": [s.to_dict() for s in self.source_manifest],
            "attestation": self.attestation.to_dict() if self.attestation else None,
        }


@dataclass(frozen=True)
class FeatureVector:
    session_date: str  # YYYY-MM-DD
    cutoff_time: datetime
    feature_names: List[str]
    feature_values: List[float]
    feature_hash: str
    provenance: SourceProvenance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_date": self.session_date,
            "cutoff_time": self.cutoff_time.isoformat(),
            "feature_names": self.feature_names,
            "feature_values": self.feature_values,
            "feature_hash": self.feature_hash,
            "provenance": self.provenance.to_dict(),
        }


@dataclass
class ValidationReport:
    validation_id: str
    session_date: str
    evaluated_at: datetime
    status: ValidationStatus
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    is_eligible_for_inference: bool = False
    feature_vector_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "session_date": self.session_date,
            "evaluated_at": self.evaluated_at.isoformat(),
            "status": self.status.value,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "error_messages": self.error_messages,
            "is_eligible_for_inference": self.is_eligible_for_inference,
            "feature_vector_hash": self.feature_vector_hash,
        }


@dataclass(frozen=True)
class ShadowPrediction:
    prediction_id: str
    session_date: str
    target_date: str
    prediction_timestamp: datetime
    snapshot_type: str
    cutoff_timestamp: datetime
    target_id: str
    predicted_return: float
    predicted_return_bps: float
    model_name: str
    model_sha256: str
    feature_hash: str
    feature_count: int
    provenance_type: str
    research_status: str
    trading_authorized: bool
    prev_record_hash: str
    record_hash: str
    manifest_hash: Optional[str] = None
    raw_evidence_digest: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "session_date": self.session_date,
            "target_date": self.target_date,
            "prediction_timestamp": self.prediction_timestamp.isoformat(),
            "snapshot_type": self.snapshot_type,
            "cutoff_timestamp": self.cutoff_timestamp.isoformat(),
            "target_id": self.target_id,
            "predicted_return": self.predicted_return,
            "predicted_return_bps": self.predicted_return_bps,
            "model_name": self.model_name,
            "model_sha256": self.model_sha256,
            "feature_hash": self.feature_hash,
            "feature_count": self.feature_count,
            "provenance_type": self.provenance_type,
            "research_status": self.research_status,
            "trading_authorized": self.trading_authorized,
            "prev_record_hash": self.prev_record_hash,
            "record_hash": self.record_hash,
            "manifest_hash": self.manifest_hash,
            "raw_evidence_digest": self.raw_evidence_digest,
        }


@dataclass(frozen=True)
class RealizedOutcome:
    outcome_id: str
    prediction_id: str
    session_date: str
    realized_open: float
    realized_close: float
    realized_t0: float
    realized_t0_bps: float
    prediction_error: float
    absolute_error_bps: float
    directional_match: bool
    acquisition_timestamp: datetime
    data_source: str
    status: str
    record_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "prediction_id": self.prediction_id,
            "session_date": self.session_date,
            "realized_open": self.realized_open,
            "realized_close": self.realized_close,
            "realized_t0": self.realized_t0,
            "realized_t0_bps": self.realized_t0_bps,
            "prediction_error": self.prediction_error,
            "absolute_error_bps": self.absolute_error_bps,
            "directional_match": self.directional_match,
            "acquisition_timestamp": self.acquisition_timestamp.isoformat(),
            "data_source": self.data_source,
            "status": self.status,
            "record_hash": self.record_hash,
        }
