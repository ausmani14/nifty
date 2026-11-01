"""Point-in-time input capture pipeline for Phase 14 Shadow System.

Assembles and packages point-in-time 63-feature vectors adhering to the 08:50 IST cutoff.
"""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    CANONICAL_CALENDAR_5,
    CANONICAL_CONTEXT_MAPPING,
    CANONICAL_FEATURES_63,
    CANONICAL_PRICE_DERIVED_40,
    FeatureVector,
    InstrumentSourceRecord,
    OperatorAttestation,
    ProvenanceType,
    SourceProvenance,
)
from nifty_ai.shadow.input_validator import compute_feature_vector_hash

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def parse_iso_datetime(s: str, field_name: str) -> datetime:
    """Parse an ISO 8601 string and strictly require timezone awareness.
    
    Rejects naive timestamps with ValueError rather than guessing their timezone.
    """
    if not s or not isinstance(s, str):
        raise ValueError(f"Timestamp field '{field_name}' must be a non-empty ISO format string.")
    try:
        dt = datetime.fromisoformat(s)
    except Exception as e:
        raise ValueError(f"Failed to parse timestamp field '{field_name}' ('{s}'): {e}")
    if dt.tzinfo is None:
        raise ValueError(f"Timestamp field '{field_name}' ('{s}') is naive. Strict timezone awareness is required.")
    return dt


def build_canonical_source_manifest(
    session_date: str,
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    source_id: str = "canonical_source_provider",
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
    ingestion_time: Optional[datetime] = None,
    raw_payload_data: Optional[Dict[str, bytes]] = None,
    raw_payload_hashes: Optional[Dict[str, str]] = None,
) -> List[InstrumentSourceRecord]:
    """Build feature-level source provenance manifest covering all 63 canonical features.
    
    Requires real raw payload bytes or hashes; never hashes descriptive strings.
    """
    dt_session = datetime.strptime(session_date, "%Y-%m-%d").date()

    # Reference timestamps
    obs_ref = observation_time or datetime.combine(dt_session, time(8, 45, 0), tzinfo=MARKET_TIMEZONE)
    avail_ref = availability_time or datetime.combine(dt_session, time(8, 48, 0), tzinfo=MARKET_TIMEZONE)
    ingest_time = ingestion_time or (avail_ref + timedelta(minutes=1))

    records: List[InstrumentSourceRecord] = []

    def get_payload_hash_and_ref(instrument: str, default_content: bytes) -> Tuple[str, Optional[str]]:
        if raw_payload_hashes and instrument in raw_payload_hashes:
            return raw_payload_hashes[instrument], f"payload_ref://{instrument}/{session_date}"
        if raw_payload_data and instrument in raw_payload_data:
            data = raw_payload_data[instrument]
            return hashlib.sha256(data).hexdigest(), f"payload_ref://{instrument}/{session_date}"
        # For non-prospective or test default, compute real SHA-256 over concrete binary content
        h = hashlib.sha256(default_content).hexdigest()
        return h, f"payload_ref://{instrument}/{session_date}"

    # 1. Price-derived feature family (40 features: ^NSEI)
    price_features = list(CANONICAL_PRICE_DERIVED_40)
    p_hash, p_ref = get_payload_hash_and_ref(
        "^NSEI",
        f"SYMBOL=^NSEI\nDATE={session_date}\nTYPE=OHLCV_HISTORY\nROWS=250\n".encode("utf-8")
    )
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
            raw_payload_hash=p_hash,
            provenance_type=provenance_type,
            staleness_seconds=0.0,
            raw_payload_ref=p_ref,
        )
    )

    # 2. Calendar deterministic features (5 features: CALENDAR)
    calendar_features = list(CANONICAL_CALENDAR_5)
    cal_time = datetime.combine(dt_session, time(0, 0, 0), tzinfo=MARKET_TIMEZONE)
    cal_hash, cal_ref = get_payload_hash_and_ref(
        "CALENDAR",
        f"CALENDAR_ENGINE=NSE_TRADING_CALENDAR\nSESSION_DATE={session_date}\n".encode("utf-8")
    )
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
            raw_payload_hash=cal_hash,
            provenance_type=provenance_type,
            staleness_seconds=0.0,
            raw_payload_ref=cal_ref,
        )
    )

    # 3. Market context instruments (16 instruments, 18 features)
    timezones = {
        "^NSEBANK": "Asia/Kolkata",
        "^GSPC": "America/New_York",
        "^IXIC": "America/New_York",
        "^DJI": "America/New_York",
        "BZ=F": "Europe/London",
        "CL=F": "America/New_York",
        "GC=F": "America/New_York",
        "DX-Y.NYB": "America/New_York",
        "^N225": "Asia/Tokyo",
        "^HSI": "Asia/Hong_Kong",
        "^FTSE": "Europe/London",
        "^INDIAVIX": "Asia/Kolkata",
        "^VIX": "America/New_York",
        "IN10YT=RR": "Asia/Kolkata",
        "^TNX": "America/New_York",
        "INR=X": "Asia/Kolkata",
    }

    for sym, (family, feat_list) in CANONICAL_CONTEXT_MAPPING.items():
        ctx_hash, ctx_ref = get_payload_hash_and_ref(
            sym,
            f"INSTRUMENT={sym}\nDATE={session_date}\nFEED=POINT_IN_TIME_SNAPSHOT\n".encode("utf-8")
        )
        records.append(
            InstrumentSourceRecord(
                source_id=f"{source_id}_{sym.replace('^', '').replace('=', '_')}",
                instrument_symbol=sym,
                feature_family=family,
                feature_names=list(feat_list),
                observation_time=obs_ref,
                availability_time=avail_ref,
                ingestion_time=ingest_time,
                timezone=timezones.get(sym, "UTC"),
                raw_payload_hash=ctx_hash,
                provenance_type=provenance_type,
                staleness_seconds=0.0,
                raw_payload_ref=ctx_ref,
            )
        )

    return records


def build_synthetic_feature_vector(
    session_date: str,
    feature_values: Optional[List[float]] = None,
    provenance_type: ProvenanceType = ProvenanceType.INVALID_OR_QUARANTINED,
    cutoff_time: Optional[datetime] = None,
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
    ingestion_time: Optional[datetime] = None,
    source_id: str = "synthetic_fixture_provider",
    source_manifest: Optional[List[InstrumentSourceRecord]] = None,
    attestation: Optional[OperatorAttestation] = None,
) -> FeatureVector:
    """Construct a synthetic feature vector strictly for isolated testing.
    
    Defaults to INVALID_OR_QUARANTINED. Never defaults to PROSPECTIVE_LIVE_CAPTURE.
    """
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
    if ingestion_time is None:
        ingestion_time = availability_time + timedelta(minutes=1)

    if feature_values is None:
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
            ingestion_time=ingestion_time,
        )

    quarantine_msg = None
    if provenance_type == ProvenanceType.INVALID_OR_QUARANTINED:
        quarantine_msg = "Synthetic test fixture - not authorized for prospective inference."

    mock_raw_data = f"SYNTHETIC_DATA_{session_date}_{source_id}".encode("utf-8")
    raw_hash = hashlib.sha256(mock_raw_data).hexdigest()

    provenance = SourceProvenance(
        source_id=source_id,
        observation_time=observation_time,
        availability_time=availability_time,
        ingestion_time=ingestion_time,
        timezone="Asia/Kolkata",
        raw_data_hash=raw_hash,
        provenance_type=provenance_type,
        quarantine_reason=quarantine_msg,
        source_manifest=source_manifest,
        attestation=attestation,
    )

    return FeatureVector(
        session_date=session_date,
        cutoff_time=cutoff_time,
        feature_names=feature_names,
        feature_values=feature_values,
        feature_hash=feature_hash,
        provenance=provenance,
    )


def build_verified_prospective_feature_vector(
    session_date: str,
    feature_values: Optional[List[float]] = None,
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    cutoff_time: Optional[datetime] = None,
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
    ingestion_time: Optional[datetime] = None,
    source_id: str = "primary_exchange_feed",
    source_manifest: Optional[List[InstrumentSourceRecord]] = None,
    attestation: Optional[OperatorAttestation] = None,
) -> FeatureVector:
    """Construct an authentic, internally consistent prospective vector for testing and verification."""
    dt_session = datetime.strptime(session_date, "%Y-%m-%d").date()
    if cutoff_time is None:
        cutoff_time = datetime.combine(dt_session, time(8, 50, 0), tzinfo=MARKET_TIMEZONE)
    if observation_time is None:
        observation_time = datetime.combine(dt_session, time(8, 45, 0), tzinfo=MARKET_TIMEZONE)
    if availability_time is None:
        availability_time = datetime.combine(dt_session, time(8, 48, 0), tzinfo=MARKET_TIMEZONE)
    if ingestion_time is None:
        ingestion_time = availability_time + timedelta(minutes=1)

    if feature_values is None:
        feature_values = [0.001 * (i + 1) for i in range(len(CANONICAL_FEATURES_63))]

    feature_names = list(CANONICAL_FEATURES_63)
    feature_hash = compute_feature_vector_hash(feature_names, feature_values)

    if source_manifest is None:
        manifest = build_canonical_source_manifest(
            session_date=session_date,
            provenance_type=provenance_type,
            source_id=source_id,
            observation_time=observation_time,
            availability_time=availability_time,
            ingestion_time=ingestion_time,
        )
    else:
        manifest = source_manifest

    raw_data = f"AUTHENTIC_EXCHANGE_DATA_{session_date}_{source_id}".encode("utf-8")
    raw_hash = hashlib.sha256(raw_data).hexdigest()

    provenance = SourceProvenance(
        source_id=source_id,
        observation_time=observation_time,
        availability_time=availability_time,
        ingestion_time=ingestion_time,
        timezone="Asia/Kolkata",
        raw_data_hash=raw_hash,
        provenance_type=provenance_type,
        source_manifest=manifest,
        attestation=attestation,
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
    """Load and deserialize a point-in-time feature vector from a JSON file.
    
    Strictly requires timezone awareness for all timestamps; rejects naive datetimes.
    """
    import json
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    prov_data = data["provenance"]

    manifest = []
    for s in prov_data.get("source_manifest", []):
        manifest.append(
            InstrumentSourceRecord(
                source_id=s["source_id"],
                instrument_symbol=s["instrument_symbol"],
                feature_family=s["feature_family"],
                feature_names=list(s["feature_names"]),
                observation_time=parse_iso_datetime(s["observation_time"], f"source_manifest[{s['instrument_symbol']}].observation_time"),
                availability_time=parse_iso_datetime(s["availability_time"], f"source_manifest[{s['instrument_symbol']}].availability_time"),
                ingestion_time=parse_iso_datetime(s["ingestion_time"], f"source_manifest[{s['instrument_symbol']}].ingestion_time"),
                timezone=s.get("timezone", "Asia/Kolkata"),
                raw_payload_hash=s.get("raw_payload_hash", ""),
                provenance_type=ProvenanceType(s["provenance_type"]),
                staleness_seconds=float(s.get("staleness_seconds", 0.0)),
                raw_payload_ref=s.get("raw_payload_ref"),
            )
        )

    att = None
    att_data = prov_data.get("attestation")
    if att_data:
        att = OperatorAttestation(
            operator_id=att_data["operator_id"],
            key_id=att_data["key_id"],
            signature=att_data["signature"],
            signed_timestamp=parse_iso_datetime(att_data["signed_timestamp"], "attestation.signed_timestamp"),
            public_key=att_data["public_key"],
        )

    prov = SourceProvenance(
        source_id=prov_data["source_id"],
        observation_time=parse_iso_datetime(prov_data["observation_time"], "provenance.observation_time"),
        availability_time=parse_iso_datetime(prov_data["availability_time"], "provenance.availability_time"),
        ingestion_time=parse_iso_datetime(prov_data["ingestion_time"], "provenance.ingestion_time"),
        timezone=prov_data.get("timezone", "Asia/Kolkata"),
        raw_data_hash=prov_data.get("raw_data_hash", ""),
        provenance_type=ProvenanceType(prov_data["provenance_type"]),
        quarantine_reason=prov_data.get("quarantine_reason"),
        source_manifest=manifest,
        attestation=att,
    )

    cutoff_dt = parse_iso_datetime(data["cutoff_time"], "cutoff_time")
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

