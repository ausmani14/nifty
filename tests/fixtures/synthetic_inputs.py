"""Test-only fixture helpers for isolated unit and integration testing.

These fixtures are strictly restricted to tests/ and must NEVER be imported or executed
in production pipelines.
"""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    AuthorizedOperatorKey,
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
from nifty_ai.shadow.crypto import (
    DEFAULT_RAW_CAPTURE_DIR,
    OperatorKeyRegistry,
    RawPayloadStore,
    compute_manifest_hash,
    create_operator_attestation,
    generate_operator_keypair,
    get_default_key_registry,
)
from nifty_ai.shadow.input_validator import compute_feature_vector_hash

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")
TEST_PAYLOAD_DIR = DEFAULT_RAW_CAPTURE_DIR


def build_test_source_manifest(
    session_date: str,
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    source_id: str = "canonical_source_provider",
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
    ingestion_time: Optional[datetime] = None,
    payload_store: Optional[RawPayloadStore] = None,
    cutoff_time: Optional[datetime] = None,
) -> List[InstrumentSourceRecord]:
    """Build a complete, authentic 18-record source manifest backed by real payload files."""
    dt_session = datetime.strptime(session_date, "%Y-%m-%d").date()
    cutoff_ref = cutoff_time or datetime.combine(dt_session, time(8, 50, 0), tzinfo=MARKET_TIMEZONE)
    # Ensure timezone alignment for staleness computation even if naive cutoff passed for testing
    c_calc = cutoff_ref.replace(tzinfo=MARKET_TIMEZONE) if cutoff_ref.tzinfo is None else cutoff_ref

    obs_ref = observation_time or datetime.combine(dt_session, time(8, 45, 0), tzinfo=MARKET_TIMEZONE)
    avail_ref = availability_time or datetime.combine(dt_session, time(8, 48, 0), tzinfo=MARKET_TIMEZONE)
    ingest_time = ingestion_time or (avail_ref + timedelta(minutes=1))

    store = payload_store or RawPayloadStore(base_dir=TEST_PAYLOAD_DIR)
    records: List[InstrumentSourceRecord] = []

    # 1. ^NSEI cash history (40 price-derived features)
    nsei_payload = f"EXCHANGE=NSE\nSYMBOL=^NSEI\nSESSION={session_date}\nOHLCV_HISTORY_ROWS=250\n".encode("utf-8")
    nsei_hash, nsei_ref = store.store_payload(session_date, "^NSEI", nsei_payload)
    nsei_staleness = (c_calc - obs_ref).total_seconds()
    records.append(
        InstrumentSourceRecord(
            source_id=f"{source_id}_nsei_cash",
            instrument_symbol="^NSEI",
            feature_family="price_derived",
            feature_names=list(CANONICAL_PRICE_DERIVED_40),
            observation_time=obs_ref,
            availability_time=avail_ref,
            ingestion_time=ingest_time,
            timezone="Asia/Kolkata",
            raw_payload_hash=nsei_hash,
            provenance_type=provenance_type,
            staleness_seconds=nsei_staleness,
            raw_payload_ref=nsei_ref,
        )
    )

    # 2. CALENDAR (5 calendar features)
    cal_payload = f"CALENDAR_ENGINE=NSE_TRADING_CALENDAR\nSESSION_DATE={session_date}\n".encode("utf-8")
    cal_hash, cal_ref = store.store_payload(session_date, "CALENDAR", cal_payload)
    cal_time = datetime.combine(dt_session, time(0, 0, 0), tzinfo=MARKET_TIMEZONE)
    cal_staleness = (c_calc - cal_time).total_seconds()
    records.append(
        InstrumentSourceRecord(
            source_id=f"{source_id}_calendar",
            instrument_symbol="CALENDAR",
            feature_family="calendar",
            feature_names=list(CANONICAL_CALENDAR_5),
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

    # 3. Market context (16 instruments, 18 features)
    from nifty_ai.shadow.contracts import CANONICAL_TIMEZONES

    for sym, (family, feat_list) in CANONICAL_CONTEXT_MAPPING.items():
        ctx_payload = f"EXCHANGE_DATA\nINSTRUMENT={sym}\nSESSION={session_date}\nSTATUS=FINAL\n".encode("utf-8")
        ctx_hash, ctx_ref = store.store_payload(session_date, sym, ctx_payload)
        ctx_staleness = (c_calc - obs_ref).total_seconds()
        records.append(
            InstrumentSourceRecord(
                source_id=f"{source_id}_{sym.replace('^', '').replace('=', '_')}",
                instrument_symbol=sym,
                feature_family=family,
                feature_names=list(feat_list),
                observation_time=obs_ref,
                availability_time=avail_ref,
                ingestion_time=ingest_time,
                timezone=CANONICAL_TIMEZONES[sym],
                raw_payload_hash=ctx_hash,
                provenance_type=provenance_type,
                staleness_seconds=ctx_staleness,
                raw_payload_ref=ctx_ref,
            )
        )

    return records


def build_test_prospective_feature_vector(
    session_date: str,
    provenance_type: ProvenanceType = ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    source_id: str = "canonical_source_provider",
    source_manifest: Optional[List[InstrumentSourceRecord]] = None,
    attestation: Optional[OperatorAttestation] = None,
    payload_store: Optional[RawPayloadStore] = None,
    operator_key_registry: Optional[OperatorKeyRegistry] = None,
    cutoff_time: Optional[datetime] = None,
    observation_time: Optional[datetime] = None,
    availability_time: Optional[datetime] = None,
    ingestion_time: Optional[datetime] = None,
    feature_values: Optional[List[float]] = None,
) -> FeatureVector:
    """Build a valid test-fixture feature vector strictly for automated integration testing."""
    dt_session = datetime.strptime(session_date, "%Y-%m-%d").date()
    cutoff_time = cutoff_time or datetime.combine(dt_session, time(8, 50, 0), tzinfo=MARKET_TIMEZONE)
    observation_time = observation_time or datetime.combine(dt_session, time(8, 45, 0), tzinfo=MARKET_TIMEZONE)
    availability_time = availability_time or datetime.combine(dt_session, time(8, 48, 0), tzinfo=MARKET_TIMEZONE)
    ingestion_time = ingestion_time or (availability_time + timedelta(minutes=1))

    store = payload_store or RawPayloadStore(base_dir=TEST_PAYLOAD_DIR)

    feature_names = list(CANONICAL_FEATURES_63)
    if feature_values is None:
        computed_values: List[float] = []
        for i, name in enumerate(feature_names):
            val = 0.0001 * ((i % 17) - 8)
            if "sma" in name:
                val = 24000.0 + i * 10.0
            elif "vix" in name:
                val = 14.5 + (i % 5) * 0.2
            elif name in {"day_of_week", "day_of_month", "month", "quarter"}:
                val = float((i % 7) + 1)
            computed_values.append(float(val))
        feature_values = computed_values

    feature_hash = compute_feature_vector_hash(feature_names, feature_values)

    if source_manifest is None:
        manifest = build_test_source_manifest(
            session_date,
            provenance_type=provenance_type,
            source_id=source_id,
            observation_time=observation_time,
            availability_time=availability_time,
            ingestion_time=ingestion_time,
            payload_store=store,
            cutoff_time=cutoff_time,
        )
    else:
        manifest = source_manifest

    # If OPERATOR_ATTESTED_PROSPECTIVE and no attestation given, generate a valid keypair and sign
    final_attestation = attestation
    if provenance_type == ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE and final_attestation is None:
        priv_hex, pub_hex = generate_operator_keypair()
        key_id = f"test_key_{session_date}"
        operator_id = "test_authorized_operator"
        auth_key = AuthorizedOperatorKey(
            operator_id=operator_id,
            key_id=key_id,
            public_key_hex=pub_hex,
            valid_from=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            valid_until=datetime(2027, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            is_revoked=False,
        )
        reg = operator_key_registry or get_default_key_registry()
        reg.register_key(auth_key)

        # Temporary feature vector to sign
        prov_temp = SourceProvenance(
            source_id=source_id,
            observation_time=observation_time,
            availability_time=availability_time,
            ingestion_time=ingestion_time,
            timezone="Asia/Kolkata",
            raw_data_hash=hashlib.sha256(b"TEST_MARKET_EVIDENCE").hexdigest(),
            provenance_type=provenance_type,
            source_manifest=manifest,
        )
        vec_temp = FeatureVector(
            session_date=session_date,
            cutoff_time=cutoff_time,
            feature_names=feature_names,
            feature_values=feature_values,
            feature_hash=feature_hash,
            provenance=prov_temp,
        )
        final_attestation = create_operator_attestation(
            feature_vector=vec_temp,
            operator_id=operator_id,
            key_id=key_id,
            private_key_hex=priv_hex,
            signed_timestamp=availability_time,
        )

    evidence_digest = RawPayloadStore.compute_evidence_digest(manifest) if manifest else hashlib.sha256(b"TEST").hexdigest()

    provenance = SourceProvenance(
        source_id=source_id,
        observation_time=observation_time,
        availability_time=availability_time,
        ingestion_time=ingestion_time,
        timezone="Asia/Kolkata",
        raw_data_hash=evidence_digest,
        provenance_type=provenance_type,
        source_manifest=manifest,
        attestation=final_attestation,
    )

    return FeatureVector(
        session_date=session_date,
        cutoff_time=cutoff_time,
        feature_names=feature_names,
        feature_values=feature_values,
        feature_hash=feature_hash,
        provenance=provenance,
    )


# Backward-compatible alias for existing tests
build_verified_prospective_feature_vector = build_test_prospective_feature_vector
