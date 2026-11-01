"""Point-in-time input capture pipeline for Phase 14 Shadow System.

Assembles and packages point-in-time 63-feature vectors adhering to the 08:50 IST cutoff.
"""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    FeatureVector,
    InstrumentSourceRecord,
    ProvenanceType,
    SourceProvenance,
)
from nifty_ai.shadow.input_validator import compute_feature_vector_hash

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def build_canonical_source_manifest(
    session_date: str,
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    source_id: str = "canonical_source_provider",
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
) -> List[InstrumentSourceRecord]:
    """Build feature-level source provenance manifest covering all 63 canonical features."""
    dt_session = datetime.strptime(session_date, "%Y-%m-%d").date()
    ingest_time = datetime.now(timezone.utc)

    # Reference timestamps
    obs_ref = observation_time or datetime.combine(dt_session, time(8, 45, 0), tzinfo=MARKET_TIMEZONE)
    avail_ref = availability_time or datetime.combine(dt_session, time(8, 48, 0), tzinfo=MARKET_TIMEZONE)

    records: List[InstrumentSourceRecord] = []

    # 1. Price-derived feature family (40 features: indices 0..39)
    price_features = list(CANONICAL_FEATURES_63[:40])
    records.append(
        InstrumentSourceRecord(
            source_id=f"{source_id}_nsei_cash",
            instrument_symbol="^NSEI",
            feature_family="price_derived",
            feature_names=price_features,
            observation_time=obs_ref,
            availability_time=avail_ref,
            ingestion_time=ingest_time,
            timezone="Asia/Kolkata",
            raw_payload_hash=hashlib.sha256(f"{session_date}_^NSEI_price_derived".encode()).hexdigest(),
            provenance_type=provenance_type,
            staleness_seconds=0.0,
        )
    )

    # 2. Calendar deterministic features (5 features: indices 40..44)
    calendar_features = list(CANONICAL_FEATURES_63[40:45])
    cal_time = datetime.combine(dt_session, time(0, 0, 0), tzinfo=MARKET_TIMEZONE)
    records.append(
        InstrumentSourceRecord(
            source_id=f"{source_id}_calendar",
            instrument_symbol="CALENDAR",
            feature_family="calendar",
            feature_names=calendar_features,
            observation_time=cal_time,
            availability_time=cal_time,
            ingestion_time=ingest_time,
            timezone="Asia/Kolkata",
            raw_payload_hash=hashlib.sha256(f"{session_date}_CALENDAR".encode()).hexdigest(),
            provenance_type=provenance_type,
            staleness_seconds=0.0,
        )
    )

    # 3. Market context instruments (18 features: indices 45..62)
    context_mappings = [
        ("^NSEBANK", "market_context", ["ctx_ret_1d_nifty_bank"], "Asia/Kolkata"),
        ("^GSPC", "market_context", ["ctx_ret_1d_sp500"], "America/New_York"),
        ("^IXIC", "market_context", ["ctx_ret_1d_nasdaq"], "America/New_York"),
        ("^DJI", "market_context", ["ctx_ret_1d_dow_jones"], "America/New_York"),
        ("BZ=F", "market_context", ["ctx_ret_1d_brent_crude"], "Europe/London"),
        ("CL=F", "market_context", ["ctx_ret_1d_wti_crude"], "America/New_York"),
        ("GC=F", "market_context", ["ctx_ret_1d_gold"], "America/New_York"),
        ("DX-Y.NYB", "market_context", ["ctx_ret_1d_dxy"], "America/New_York"),
        ("^N225", "market_context", ["ctx_ret_1d_nikkei_225"], "Asia/Tokyo"),
        ("^HSI", "market_context", ["ctx_ret_1d_hang_seng"], "Asia/Hong_Kong"),
        ("^FTSE", "market_context", ["ctx_ret_1d_ftse_100"], "Europe/London"),
        ("^INDIAVIX", "market_context", ["ctx_diff_1d_india_vix", "ctx_level_india_vix"], "Asia/Kolkata"),
        ("^VIX", "market_context", ["ctx_diff_1d_us_vix", "ctx_level_us_vix"], "America/New_York"),
        ("IN10YT=RR", "market_context", ["ctx_diff_1d_india_10y_yield"], "Asia/Kolkata"),
        ("^TNX", "market_context", ["ctx_diff_1d_us_10y_yield"], "America/New_York"),
        ("INR=X", "market_context", ["ctx_diff_1d_usd_inr"], "Asia/Kolkata"),
    ]

    for sym, family, feat_list, tz_name in context_mappings:
        records.append(
            InstrumentSourceRecord(
                source_id=f"{source_id}_{sym.replace('^', '').replace('=', '_')}",
                instrument_symbol=sym,
                feature_family=family,
                feature_names=feat_list,
                observation_time=obs_ref,
                availability_time=avail_ref,
                ingestion_time=ingest_time,
                timezone=tz_name,
                raw_payload_hash=hashlib.sha256(f"{session_date}_{sym}".encode()).hexdigest(),
                provenance_type=provenance_type,
                staleness_seconds=0.0,
            )
        )

    return records


def build_synthetic_feature_vector(
    session_date: str,
    feature_values: Optional[List[float]] = None,
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    cutoff_time: Optional[datetime] = None,
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
    source_id: str = "synthetic_test_provider",
    source_manifest: Optional[List[InstrumentSourceRecord]] = None,
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

    if source_manifest is None:
        source_manifest = build_canonical_source_manifest(
            session_date=session_date,
            provenance_type=provenance_type,
            source_id=source_id,
            observation_time=observation_time,
            availability_time=availability_time,
        )

    provenance = SourceProvenance(
        source_id=source_id,
        observation_time=observation_time,
        availability_time=availability_time,
        ingestion_time=datetime.now(timezone.utc),
        timezone="Asia/Kolkata",
        raw_data_hash=hashlib.sha256(f"{session_date}_{source_id}".encode()).hexdigest(),
        provenance_type=provenance_type,
        source_manifest=source_manifest,
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

    manifest = []
    for s in prov_data.get("source_manifest", []):
        manifest.append(
            InstrumentSourceRecord(
                source_id=s["source_id"],
                instrument_symbol=s["instrument_symbol"],
                feature_family=s["feature_family"],
                feature_names=list(s["feature_names"]),
                observation_time=parse_dt(s["observation_time"]),
                availability_time=parse_dt(s["availability_time"]),
                ingestion_time=parse_dt(s["ingestion_time"]),
                timezone=s.get("timezone", "Asia/Kolkata"),
                raw_payload_hash=s.get("raw_payload_hash", ""),
                provenance_type=ProvenanceType(s["provenance_type"]),
                staleness_seconds=float(s.get("staleness_seconds", 0.0)),
            )
        )

    prov = SourceProvenance(
        source_id=prov_data["source_id"],
        observation_time=parse_dt(prov_data["observation_time"]),
        availability_time=parse_dt(prov_data["availability_time"]),
        ingestion_time=parse_dt(prov_data["ingestion_time"]),
        timezone=prov_data.get("timezone", "Asia/Kolkata"),
        raw_data_hash=prov_data.get("raw_data_hash", ""),
        provenance_type=ProvenanceType(prov_data["provenance_type"]),
        quarantine_reason=prov_data.get("quarantine_reason"),
        source_manifest=manifest,
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

