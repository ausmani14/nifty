"""Point-in-time input capture pipeline for Phase 14 Shadow System.

Assembles and packages point-in-time 63-feature vectors adhering to the 08:50 IST cutoff.
"""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    CANONICAL_CALENDAR_5,
    CANONICAL_CONTEXT_MAPPING,
    CANONICAL_FEATURES_63,
    CANONICAL_PRICE_DERIVED_40,
    CANONICAL_TIMEZONES,
    FeatureVector,
    InstrumentSourceRecord,
    OperatorAttestation,
    ProvenanceType,
    SourceProvenance,
    TRUSTED_LIVE_PROVIDERS,
)
from nifty_ai.shadow.crypto import RawPayloadStore, compute_manifest_hash
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


def build_production_source_manifest(
    session_date: str,
    instrument_payloads: Dict[str, bytes],
    instrument_metadata: Dict[str, Dict[str, Any]],
    payload_store: Optional[RawPayloadStore] = None,
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    source_id: str = "production_market_feed",
) -> List[InstrumentSourceRecord]:
    """Construct production source provenance manifest strictly backed by real raw payload bytes.
    
    Requires authentic raw binary payloads for all 18 required instruments (^NSEI, CALENDAR,
    and the 16 canonical context instruments). Never generates placeholder hashes or dummy timestamps.
    """
    store = payload_store or RawPayloadStore()
    required_instruments = ["^NSEI", "CALENDAR"] + list(CANONICAL_CONTEXT_MAPPING.keys())

    # Check for missing payloads
    missing = [sym for sym in required_instruments if not instrument_payloads.get(sym)]
    if missing:
        raise ValueError(
            f"Production source manifest missing required raw payload bytes for {len(missing)} instruments: {missing}."
        )

    # Check for missing metadata
    missing_meta = [sym for sym in required_instruments if sym not in instrument_metadata]
    if missing_meta:
        raise ValueError(
            f"Production source manifest missing capture metadata for {len(missing_meta)} instruments: {missing_meta}."
        )

    # Authoritative cutoff for Snapshot B on session_date
    dt_session = datetime.strptime(session_date, "%Y-%m-%d").date()
    cutoff_time = datetime.combine(dt_session, time(8, 50, 0), tzinfo=MARKET_TIMEZONE)

    # Validate metadata timestamps, explicit timezones, and staleness
    for sym in required_instruments:
        meta = instrument_metadata[sym]
        obs_t = meta.get("observation_time")
        avail_t = meta.get("availability_time")
        ingest_t = meta.get("ingestion_time")

        if not obs_t or not isinstance(obs_t, datetime) or obs_t.tzinfo is None:
            raise ValueError(f"Metadata for '{sym}' observation_time must be timezone-aware datetime.")
        if not avail_t or not isinstance(avail_t, datetime) or avail_t.tzinfo is None:
            raise ValueError(f"Metadata for '{sym}' availability_time must be timezone-aware datetime.")
        if not ingest_t or not isinstance(ingest_t, datetime) or ingest_t.tzinfo is None:
            raise ValueError(f"Metadata for '{sym}' ingestion_time must be timezone-aware datetime.")
        if ingest_t < avail_t or avail_t < obs_t:
            raise ValueError(f"Metadata timestamps for '{sym}' must be chronological: observation <= availability <= ingestion.")

        # Issue 2: Explicit timezone must be provided, valid via ZoneInfo, and match canonical timezone
        if "timezone" not in meta or not meta["timezone"] or not isinstance(meta["timezone"], str):
            raise ValueError(f"Metadata for '{sym}' missing explicit timezone.")
        provided_tz = meta["timezone"].strip()
        try:
            ZoneInfo(provided_tz)
        except Exception as e:
            raise ValueError(f"Invalid timezone '{provided_tz}' for '{sym}': {e}")
        expected_tz = CANONICAL_TIMEZONES.get(sym)
        if expected_tz is None or provided_tz != expected_tz:
            raise ValueError(f"Timezone for '{sym}' must match canonical timezone '{expected_tz}', got '{provided_tz}'.")

        # Issue 3: Recompute staleness from cutoff_time and actual observation_time
        auth_staleness = (cutoff_time - obs_t).total_seconds()
        if "staleness_seconds" in meta and meta["staleness_seconds"] is not None:
            declared_staleness = float(meta["staleness_seconds"])
            if abs(declared_staleness - auth_staleness) > 1.0:
                raise ValueError(
                    f"Declared staleness {declared_staleness}s for '{sym}' does not match authoritative staleness {auth_staleness}s within 1.0s tolerance."
                )

    records: List[InstrumentSourceRecord] = []

    # 1. ^NSEI (40 price-derived features)
    nsei_bytes = instrument_payloads["^NSEI"]
    nsei_meta = instrument_metadata["^NSEI"]
    nsei_hash, nsei_ref = store.store_payload(session_date, "^NSEI", nsei_bytes)
    nsei_obs = nsei_meta["observation_time"]
    nsei_staleness = (cutoff_time - nsei_obs).total_seconds()
    records.append(
        InstrumentSourceRecord(
            source_id=f"{source_id}_nsei_cash",
            instrument_symbol="^NSEI",
            feature_family="price_derived",
            feature_names=list(CANONICAL_PRICE_DERIVED_40),
            observation_time=nsei_obs,
            availability_time=nsei_meta["availability_time"],
            ingestion_time=nsei_meta["ingestion_time"],
            timezone=nsei_meta["timezone"].strip(),
            raw_payload_hash=nsei_hash,
            provenance_type=provenance_type,
            staleness_seconds=nsei_staleness,
            raw_payload_ref=nsei_ref,
        )
    )

    # 2. CALENDAR (5 calendar features)
    cal_bytes = instrument_payloads["CALENDAR"]
    cal_meta = instrument_metadata["CALENDAR"]
    cal_hash, cal_ref = store.store_payload(session_date, "CALENDAR", cal_bytes)
    cal_obs = cal_meta["observation_time"]
    cal_staleness = (cutoff_time - cal_obs).total_seconds()
    records.append(
        InstrumentSourceRecord(
            source_id=f"{source_id}_calendar",
            instrument_symbol="CALENDAR",
            feature_family="calendar",
            feature_names=list(CANONICAL_CALENDAR_5),
            observation_time=cal_obs,
            availability_time=cal_meta["availability_time"],
            ingestion_time=cal_meta["ingestion_time"],
            timezone=cal_meta["timezone"].strip(),
            raw_payload_hash=cal_hash,
            provenance_type=provenance_type,
            staleness_seconds=cal_staleness,
            raw_payload_ref=cal_ref,
        )
    )

    # 3. Market context (16 instruments, 18 features)
    for sym, (family, feat_list) in CANONICAL_CONTEXT_MAPPING.items():
        ctx_bytes = instrument_payloads[sym]
        ctx_meta = instrument_metadata[sym]
        ctx_hash, ctx_ref = store.store_payload(session_date, sym, ctx_bytes)
        ctx_obs = ctx_meta["observation_time"]
        ctx_staleness = (cutoff_time - ctx_obs).total_seconds()
        records.append(
            InstrumentSourceRecord(
                source_id=f"{source_id}_{sym.replace('^', '').replace('=', '_')}",
                instrument_symbol=sym,
                feature_family=family,
                feature_names=list(feat_list),
                observation_time=ctx_obs,
                availability_time=ctx_meta["availability_time"],
                ingestion_time=ctx_meta["ingestion_time"],
                timezone=ctx_meta["timezone"].strip(),
                raw_payload_hash=ctx_hash,
                provenance_type=provenance_type,
                staleness_seconds=ctx_staleness,
                raw_payload_ref=ctx_ref,
            )
        )

    return records


def build_canonical_source_manifest(
    session_date: str,
    provenance_type: ProvenanceType = ProvenanceType.INVALID_OR_QUARANTINED,
    source_id: str = "canonical_source_provider",
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
    ingestion_time: Optional[datetime] = None,
    raw_payload_data: Optional[Dict[str, bytes]] = None,
    raw_payload_hashes: Optional[Dict[str, str]] = None,
    payload_store: Optional[RawPayloadStore] = None,
    cutoff_time: Optional[datetime] = None,
) -> List[InstrumentSourceRecord]:
    """Build source provenance manifest for non-prospective records.
    
    Strictly prohibits prospective provenance types (PROSPECTIVE_LIVE_CAPTURE,
    OPERATOR_ATTESTED_PROSPECTIVE). Prospective pipelines MUST use
    build_production_source_manifest with verified raw binary payloads.
    """
    if provenance_type in {
        ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
        ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE,
    }:
        raise ValueError(
            "build_canonical_source_manifest cannot be used for prospective provenance; "
            "authentic raw binary payloads and build_production_source_manifest are required."
        )

    store = payload_store or RawPayloadStore()
    dt_session = datetime.strptime(session_date, "%Y-%m-%d").date()
    cutoff_ref = cutoff_time or datetime.combine(dt_session, time(8, 50, 0), tzinfo=MARKET_TIMEZONE)
    c_calc = cutoff_ref.replace(tzinfo=MARKET_TIMEZONE) if cutoff_ref.tzinfo is None else cutoff_ref

    obs_ref = observation_time or datetime.combine(dt_session, time(8, 45, 0), tzinfo=MARKET_TIMEZONE)
    avail_ref = availability_time or datetime.combine(dt_session, time(8, 48, 0), tzinfo=MARKET_TIMEZONE)
    ingest_time = ingestion_time or (avail_ref + timedelta(minutes=1))

    records: List[InstrumentSourceRecord] = []

    def get_payload_hash_and_ref(instrument: str, concrete_content: bytes) -> Tuple[str, Optional[str]]:
        if raw_payload_data and instrument in raw_payload_data:
            data = raw_payload_data[instrument]
            h, ref = store.store_payload(session_date, instrument, data)
            return h, ref
        if raw_payload_hashes and instrument in raw_payload_hashes:
            return raw_payload_hashes[instrument], None
        h, ref = store.store_payload(session_date, instrument, concrete_content)
        return h, ref

    # 1. Price-derived feature family (40 features: ^NSEI)
    price_features = list(CANONICAL_PRICE_DERIVED_40)
    p_hash, p_ref = get_payload_hash_and_ref(
        "^NSEI",
        f"SYMBOL=^NSEI\nDATE={session_date}\nNON_PROSPECTIVE_FIXTURE_PAYLOAD\n".encode("utf-8"),
    )
    p_staleness = (c_calc - obs_ref).total_seconds()
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
            staleness_seconds=p_staleness,
            raw_payload_ref=p_ref,
        )
    )

    # 2. Calendar deterministic features (5 features: CALENDAR)
    calendar_features = list(CANONICAL_CALENDAR_5)
    cal_time = datetime.combine(dt_session, time(0, 0, 0), tzinfo=MARKET_TIMEZONE)
    cal_hash, cal_ref = get_payload_hash_and_ref(
        "CALENDAR",
        f"CALENDAR_ENGINE=NSE_TRADING_CALENDAR\nSESSION_DATE={session_date}\n".encode("utf-8"),
    )
    cal_staleness = (c_calc - cal_time).total_seconds()
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
            staleness_seconds=cal_staleness,
            raw_payload_ref=cal_ref,
        )
    )

    # 3. Market context instruments (16 instruments, 18 features)
    ctx_staleness = (c_calc - obs_ref).total_seconds()
    for sym, (family, feat_list) in CANONICAL_CONTEXT_MAPPING.items():
        ctx_hash, ctx_ref = get_payload_hash_and_ref(
            sym,
            f"INSTRUMENT={sym}\nDATE={session_date}\nNON_PROSPECTIVE_FIXTURE_PAYLOAD\n".encode("utf-8"),
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
                timezone=CANONICAL_TIMEZONES.get(sym, "UTC"),
                raw_payload_hash=ctx_hash,
                provenance_type=provenance_type,
                staleness_seconds=ctx_staleness,
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
    
    Hard-coded to INVALID_OR_QUARANTINED. Fails closed with ValueError if caller attempts
    to specify prospective provenance or impersonate a production source.
    """
    if provenance_type in {
        ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
        ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE,
    }:
        raise ValueError(
            "build_synthetic_feature_vector is strictly quarantined and cannot accept prospective provenance."
        )
    if source_id != "synthetic_fixture_provider":
        raise ValueError(
            "Synthetic feature vectors cannot impersonate production or canonical source providers."
        )

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
            cutoff_time=cutoff_time,
        )

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


def load_feature_vector_from_json(filepath: Path) -> FeatureVector:
    """Load and deserialize a point-in-time feature vector from a JSON file.
    
    Strictly requires timezone awareness for all timestamps; rejects naive datetimes,
    missing/invalid timezones, and mismatched staleness values.
    """
    import json
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    cutoff_dt = parse_iso_datetime(data["cutoff_time"], "cutoff_time")
    prov_data = data["provenance"]

    manifest = []
    for s in prov_data.get("source_manifest", []):
        sym = s["instrument_symbol"]
        if "timezone" not in s or not s["timezone"] or not isinstance(s["timezone"], str):
            raise ValueError(f"Source manifest entry for '{sym}' missing explicit timezone.")
        provided_tz = s["timezone"].strip()
        try:
            ZoneInfo(provided_tz)
        except Exception as e:
            raise ValueError(f"Invalid timezone '{provided_tz}' in source manifest for '{sym}': {e}")
        expected_tz = CANONICAL_TIMEZONES.get(sym)
        if expected_tz is not None and provided_tz != expected_tz:
            raise ValueError(f"Timezone for '{sym}' must match canonical timezone '{expected_tz}', got '{provided_tz}'.")

        s_obs = parse_iso_datetime(s["observation_time"], f"source_manifest[{sym}].observation_time")
        s_avail = parse_iso_datetime(s["availability_time"], f"source_manifest[{sym}].availability_time")
        s_ingest = parse_iso_datetime(s["ingestion_time"], f"source_manifest[{sym}].ingestion_time")

        # Authoritative staleness recomputation
        auth_staleness = (cutoff_dt - s_obs).total_seconds()
        if "staleness_seconds" in s and s["staleness_seconds"] is not None:
            declared_staleness = float(s["staleness_seconds"])
            if abs(declared_staleness - auth_staleness) > 1.0:
                raise ValueError(
                    f"Declared staleness {declared_staleness}s for '{sym}' does not match authoritative staleness {auth_staleness}s within 1.0s tolerance."
                )

        manifest.append(
            InstrumentSourceRecord(
                source_id=s["source_id"],
                instrument_symbol=sym,
                feature_family=s["feature_family"],
                feature_names=list(s["feature_names"]),
                observation_time=s_obs,
                availability_time=s_avail,
                ingestion_time=s_ingest,
                timezone=provided_tz,
                raw_payload_hash=s.get("raw_payload_hash", ""),
                provenance_type=ProvenanceType(s["provenance_type"]),
                staleness_seconds=auth_staleness,
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

    if "timezone" not in prov_data or not prov_data["timezone"] or not isinstance(prov_data["timezone"], str):
        raise ValueError("Provenance missing explicit timezone.")
    prov_tz = prov_data["timezone"].strip()
    try:
        ZoneInfo(prov_tz)
    except Exception as e:
        raise ValueError(f"Invalid timezone in provenance '{prov_tz}': {e}")

    prov = SourceProvenance(
        source_id=prov_data["source_id"],
        observation_time=parse_iso_datetime(prov_data["observation_time"], "provenance.observation_time"),
        availability_time=parse_iso_datetime(prov_data["availability_time"], "provenance.availability_time"),
        ingestion_time=parse_iso_datetime(prov_data["ingestion_time"], "provenance.ingestion_time"),
        timezone=prov_tz,
        raw_data_hash=prov_data.get("raw_data_hash", ""),
        provenance_type=ProvenanceType(prov_data["provenance_type"]),
        quarantine_reason=prov_data.get("quarantine_reason"),
        source_manifest=manifest,
        attestation=att,
    )

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
