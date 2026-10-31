"""Point-in-time input capture pipeline for Phase 14 Shadow System.

Assembles and packages point-in-time 63-feature vectors adhering to the 08:50 IST cutoff.
"""

from datetime import date, datetime, time, timezone
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    FeatureVector,
    ProvenanceType,
    SourceProvenance,
)
from nifty_ai.shadow.input_validator import compute_feature_vector_hash

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def build_synthetic_feature_vector(
    session_date: str,
    feature_values: Optional[List[float]] = None,
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    cutoff_time: Optional[datetime] = None,
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
    source_id: str = "synthetic_test_provider",
) -> FeatureVector:
    """Construct a well-formed synthetic feature vector for testing and verification."""
    dt_session = datetime.strptime(session_date, "%Y-%m-%d").date()
    
    if cutoff_time is None:
        cutoff_time = datetime.combine(
            dt_session, time(8, 50, 0), tzinfo=MARKET_TIMEZONE
        )
    if observation_time is None:
        observation_time = datetime.combine(
            dt_session, time(8, 45, 0), tzinfo=MARKET_TIMEZONE
        )
    if availability_time is None:
        availability_time = datetime.combine(
            dt_session, time(8, 48, 0), tzinfo=MARKET_TIMEZONE
        )

    if feature_values is None:
        # Default deterministic test values
        feature_values = [0.001 * (i + 1) for i in range(len(CANONICAL_FEATURES_63))]

    feature_names = list(CANONICAL_FEATURES_63)
    feature_hash = compute_feature_vector_hash(feature_names, feature_values)

    provenance = SourceProvenance(
        source_id=source_id,
        observation_time=observation_time,
        availability_time=availability_time,
        ingestion_time=datetime.now(timezone.utc),
        timezone="Asia/Kolkata",
        raw_data_hash=hashlib.sha256(f"{session_date}_{source_id}".encode()).hexdigest(),
        provenance_type=provenance_type,
    )

    return FeatureVector(
        session_date=session_date,
        cutoff_time=cutoff_time,
        feature_names=feature_names,
        feature_values=feature_values,
        feature_hash=feature_hash,
        provenance=provenance,
    )


def load_feature_vector_from_json(filepath: Path) -> FeatureVector:
    """Load and deserialize a point-in-time feature vector from a JSON file."""
    import json
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    prov_data = data["provenance"]
    
    def parse_dt(s: str) -> datetime:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MARKET_TIMEZONE)
        return dt

    prov = SourceProvenance(
        source_id=prov_data["source_id"],
        observation_time=parse_dt(prov_data["observation_time"]),
        availability_time=parse_dt(prov_data["availability_time"]),
        ingestion_time=parse_dt(prov_data["ingestion_time"]),
        timezone=prov_data.get("timezone", "Asia/Kolkata"),
        raw_data_hash=prov_data.get("raw_data_hash", ""),
        provenance_type=ProvenanceType(prov_data["provenance_type"]),
        quarantine_reason=prov_data.get("quarantine_reason"),
    )

    cutoff_dt = parse_dt(data["cutoff_time"])
    feature_names = list(data["feature_names"])
    feature_values = [float(x) for x in data["feature_values"]]
    feature_hash = data.get("feature_hash") or compute_feature_vector_hash(feature_names, feature_values)

    return FeatureVector(
        session_date=data["session_date"],
        cutoff_time=cutoff_dt,
        feature_names=feature_names,
        feature_values=feature_values,
        feature_hash=feature_hash,
        provenance=prov,
    )

