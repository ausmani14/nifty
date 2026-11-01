"""Phase 16 Provenance Authenticity and Cryptographic Trust Verification Suite.

Tests all 22 specific security and integrity scenarios required by the Phase 16 audit:
1. Missing raw payload bytes.
2. Fake descriptive payload hashes.
3. Arbitrary supplied hexadecimal hashes without retrievable artifacts.
4. Invalid/fake payload artifact references (e.g. payload_ref://).
5. Payload altered after capture (tamper-evidence).
6. Synthetic prospective vector rejection across live_data, validator, inference, ledger.
7. Synthetic source manifest provider rejection.
8. Missing authorized key registry fails closed.
9. Unknown key ID fails closed.
10. Operator ID mismatch fails closed.
11. Public key mismatch fails closed.
12. Revoked operator key fails closed.
13. Signature invalidation on modified key ID.
14. Signature invalidation on modified operator ID.
15. Signature invalidation on modified timezone.
16. Signature invalidation on modified provenance type.
17. Signature invalidation on modified staleness.
18. Signature invalidation on modified raw payload reference.
19. Valid authorized operator attestation passes all gates.
20. Exact canonical instrument mapping coverage.
21. Inference rejection after source-manifest mutation.
22. Production ledger append rejection on non-prospective provenance.
"""

from dataclasses import replace
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import pytest
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    AuthorizedOperatorKey,
    CANONICAL_CALENDAR_5,
    CANONICAL_CONTEXT_MAPPING,
    CANONICAL_FEATURES_63,
    CANONICAL_PRICE_DERIVED_40,
    FeatureVector,
    InstrumentSourceRecord,
    LedgerStatus,
    OperatorAttestation,
    ProvenanceType,
    SourceProvenance,
    ValidationStatus,
)
from nifty_ai.shadow.crypto import (
    OperatorKeyRegistry,
    RawPayloadStore,
    compute_manifest_hash,
    create_operator_attestation,
    generate_operator_keypair,
    get_default_key_registry,
    verify_attestation,
    verify_raw_payload_sha256,
)
from nifty_ai.shadow.inference import ShadowInferenceRunner
from nifty_ai.shadow.input_capture import (
    build_production_source_manifest,
    build_synthetic_feature_vector,
)
from nifty_ai.shadow.input_validator import (
    SNAPSHOT_B_CUTOFF_TIME,
    SnapshotBInputValidator,
    compute_feature_vector_hash,
)
from nifty_ai.shadow.ledger import DEFAULT_LEDGER_PATH, ShadowPredictionLedger
from nifty_ai.shadow.live_data import CaptureStatus, attempt_live_feature_capture
from tests.fixtures.synthetic_inputs import (
    build_test_prospective_feature_vector,
    build_test_source_manifest,
)

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# 1. Missing Raw Payload Bytes
# ---------------------------------------------------------------------------
def test_01_missing_raw_payload_bytes_raises_error(tmp_path: Path):
    """Missing or empty raw payload bytes in production manifest raises ValueError."""
    store = RawPayloadStore(base_dir=tmp_path / "raw")
    payloads = {"^NSEI": b"DATA"}  # Missing CALENDAR and context instruments
    metadata = {"^NSEI": {"observation_time": datetime.now(timezone.utc), "availability_time": datetime.now(timezone.utc), "ingestion_time": datetime.now(timezone.utc)}}

    with pytest.raises(ValueError, match="Production source manifest missing required raw payload bytes"):
        build_production_source_manifest(
            session_date="2026-11-02",
            instrument_payloads=payloads,
            instrument_metadata=metadata,
            payload_store=store,
        )


# ---------------------------------------------------------------------------
# 2. Fake Descriptive Payload Hashes
# ---------------------------------------------------------------------------
def test_02_fake_descriptive_payload_hashes_fail_closed(tmp_path: Path):
    """Fake descriptive strings as hashes fail validation closed."""
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    tainted = [
        replace(s, raw_payload_hash="sha256_placeholder_description_string_here_not_hex")
        if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    vec_tainted = replace(vec, provenance=replace(vec.provenance, source_manifest=tainted))

    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    rep = validator.validate(vec_tainted, current_time=eval_time)
    assert rep.status == ValidationStatus.FAILED
    assert rep.is_eligible_for_inference is False
    assert any("raw_payload_hash must be a valid 64-character hexadecimal SHA-256 hash" in err for err in rep.error_messages)


# ---------------------------------------------------------------------------
# 3. Arbitrary Supplied Hexadecimal Hashes
# ---------------------------------------------------------------------------
def test_03_arbitrary_supplied_hexadecimal_hashes_without_artifact_fail_closed(tmp_path: Path):
    """Caller-supplied 64-hex hash without retrievable artifact file fails closed."""
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    tainted = [
        replace(s, raw_payload_hash="a" * 64, raw_payload_ref=str(tmp_path / "non_existent.bin"))
        if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    vec_tainted = replace(vec, provenance=replace(vec.provenance, source_manifest=tainted))

    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    rep = validator.validate(vec_tainted, current_time=eval_time)
    assert rep.status == ValidationStatus.FAILED
    assert any("raw payload artifact verification failed" in err for err in rep.error_messages)


# ---------------------------------------------------------------------------
# 4. Invalid Payload Artifact References (Fake URI Scheme)
# ---------------------------------------------------------------------------
def test_04_fake_payload_ref_uri_scheme_fails_closed(tmp_path: Path):
    """Fake payload_ref:// URIs are rejected by artifact verification."""
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    tainted = [
        replace(s, raw_payload_ref=f"payload_ref://{s.instrument_symbol}/2026-11-02")
        if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    vec_tainted = replace(vec, provenance=replace(vec.provenance, source_manifest=tainted))

    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    rep = validator.validate(vec_tainted, current_time=eval_time)
    assert rep.status == ValidationStatus.FAILED
    assert any("Fake payload URI scheme rejected" in err for err in rep.error_messages)


# ---------------------------------------------------------------------------
# 5. Payload Altered After Capture (Tamper-Evidence)
# ---------------------------------------------------------------------------
def test_05_payload_altered_after_capture_detected(tmp_path: Path):
    """Altered raw bytes on disk cause hash mismatch and fail validation."""
    store = RawPayloadStore(base_dir=tmp_path / "raw")
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=store)
    nsei_record = next(s for s in vec.provenance.source_manifest if s.instrument_symbol == "^NSEI")

    # Tamper with the artifact file directly
    artifact_file = Path(nsei_record.raw_payload_ref)
    assert artifact_file.exists()
    artifact_file.write_bytes(artifact_file.read_bytes() + b"\nTAMPERED_MALICIOUS_ROW")

    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.status == ValidationStatus.FAILED
    assert any("Raw payload hash mismatch" in err for err in rep.error_messages)


# ---------------------------------------------------------------------------
# 6. Synthetic Prospective Vector Rejection
# ---------------------------------------------------------------------------
def test_06_synthetic_prospective_vector_fails_all_gates(tmp_path: Path):
    """Synthetic feature vector is quarantined and fails validator, runner, and ledger."""
    vec = build_synthetic_feature_vector("2026-11-02")
    assert vec.provenance.provenance_type == ProvenanceType.INVALID_OR_QUARANTINED

    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.status == ValidationStatus.FAILED
    assert rep.is_eligible_for_inference is False

    runner = ShadowInferenceRunner()
    with pytest.raises(ValueError, match="Provenance type 'invalid_or_quarantined' is not authorized"):
        runner.predict(vec, rep)

    temp_ledger = ShadowPredictionLedger(ledger_path=tmp_path / "test_ledger.jsonl")
    # Manually constructed mock prediction with quarantined provenance
    from nifty_ai.shadow.contracts import ShadowPrediction
    pred = ShadowPrediction(
        prediction_id="pred_synth",
        session_date="2026-11-02",
        target_date="2026-11-02",
        prediction_timestamp=datetime.now(timezone.utc),
        snapshot_type="SNAPSHOT_0850",
        cutoff_timestamp=datetime(2026, 11, 2, 3, 20, tzinfo=timezone.utc),
        target_id="T0",
        predicted_return=0.001,
        predicted_return_bps=10.0,
        model_name="test_model",
        model_sha256="test_hash",
        feature_hash="hash",
        feature_count=63,
        provenance_type="invalid_or_quarantined",
        research_status="RESEARCH_BASELINE_ONLY",
        trading_authorized=False,
        prev_record_hash="0" * 64,
        record_hash="record_hash",
    )
    with pytest.raises(ValueError, match="strictly rejects non-prospective provenance"):
        temp_ledger.append_prediction(pred, enforce_prospective=True)


# ---------------------------------------------------------------------------
# 7. Synthetic Source Manifest Rejection
# ---------------------------------------------------------------------------
def test_07_synthetic_source_manifest_rejected(tmp_path: Path):
    """Vector with synthetic/test provider ID in manifest is rejected."""
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    tainted = [
        replace(s, source_id="synthetic_mock_feed_provider")
        if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    vec_tainted = replace(vec, provenance=replace(vec.provenance, source_manifest=tainted))

    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    rep = validator.validate(vec_tainted, current_time=eval_time)
    assert rep.status == ValidationStatus.FAILED
    assert any("synthetic/test identifier" in err for err in rep.error_messages)


# ---------------------------------------------------------------------------
# 8. Missing Authorized Key Registry
# ---------------------------------------------------------------------------
def test_08_missing_authorized_key_registry_fails_closed(tmp_path: Path):
    """Attestation evaluated against empty OperatorKeyRegistry fails closed."""
    priv, pub = generate_operator_keypair()
    empty_registry = OperatorKeyRegistry()  # Empty!

    vec = build_test_prospective_feature_vector(
        "2026-11-02",
        provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE,
        payload_store=RawPayloadStore(tmp_path),
    )
    att = create_operator_attestation(
        feature_vector=vec,
        operator_id="operator_alpha",
        key_id="key_alpha",
        private_key_hex=priv,
        signed_timestamp=datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE),
    )
    is_valid, err = verify_attestation(vec, att, registry=empty_registry)
    assert is_valid is False
    assert "missing or empty" in err


# ---------------------------------------------------------------------------
# 9. Unknown Key ID
# ---------------------------------------------------------------------------
def test_09_unknown_key_id_fails_closed(tmp_path: Path):
    """Attestation using unregistered key_id fails closed."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([
        AuthorizedOperatorKey(
            operator_id="operator_alpha",
            key_id="authorized_key_01",
            public_key_hex=pub,
            valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    ])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(
        feature_vector=vec,
        operator_id="operator_alpha",
        key_id="unregistered_rogue_key_id",
        private_key_hex=priv,
        signed_timestamp=datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE),
    )
    is_valid, err = verify_attestation(vec, att, registry=registry)
    assert is_valid is False
    assert "Unknown key_id" in err


# ---------------------------------------------------------------------------
# 10. Operator ID Mismatch
# ---------------------------------------------------------------------------
def test_10_operator_id_mismatch_fails_closed(tmp_path: Path):
    """Key ID registered to operator A cannot be claimed by operator B."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([
        AuthorizedOperatorKey(
            operator_id="legitimate_operator_alice",
            key_id="key_shared_01",
            public_key_hex=pub,
            valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    ])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(
        feature_vector=vec,
        operator_id="impersonator_bob",
        key_id="key_shared_01",
        private_key_hex=priv,
        signed_timestamp=datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE),
    )
    is_valid, err = verify_attestation(vec, att, registry=registry)
    assert is_valid is False
    assert "Operator ID mismatch" in err


# ---------------------------------------------------------------------------
# 11. Public Key Mismatch
# ---------------------------------------------------------------------------
def test_11_public_key_mismatch_fails_closed(tmp_path: Path):
    """Attestation public key differing from registered key fails closed."""
    priv1, pub1 = generate_operator_keypair()
    priv2, pub2 = generate_operator_keypair()
    registry = OperatorKeyRegistry([
        AuthorizedOperatorKey(
            operator_id="operator_alpha",
            key_id="key_alpha",
            public_key_hex=pub1,
            valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    ])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    # Signed with priv2
    att = create_operator_attestation(
        feature_vector=vec,
        operator_id="operator_alpha",
        key_id="key_alpha",
        private_key_hex=priv2,
        signed_timestamp=datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE),
    )
    is_valid, err = verify_attestation(vec, att, registry=registry)
    assert is_valid is False
    assert "Public key mismatch" in err


# ---------------------------------------------------------------------------
# 12. Revoked Key
# ---------------------------------------------------------------------------
def test_12_revoked_key_fails_closed(tmp_path: Path):
    """Revoked key is explicitly rejected."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([
        AuthorizedOperatorKey(
            operator_id="operator_alpha",
            key_id="key_revoked",
            public_key_hex=pub,
            valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            is_revoked=True,
        )
    ])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(
        feature_vector=vec,
        operator_id="operator_alpha",
        key_id="key_revoked",
        private_key_hex=priv,
        signed_timestamp=datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE),
    )
    is_valid, err = verify_attestation(vec, att, registry=registry)
    assert is_valid is False
    assert "is revoked" in err


# ---------------------------------------------------------------------------
# 13. Signature with Modified Key ID
# ---------------------------------------------------------------------------
def test_13_signature_with_modified_key_id_fails_verification(tmp_path: Path):
    """Tampering with key_id after signing breaks cryptographic verification."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([
        AuthorizedOperatorKey("operator_alpha", "key_orig", pub, datetime(2026, 1, 1, tzinfo=timezone.utc)),
        AuthorizedOperatorKey("operator_alpha", "key_alt", pub, datetime(2026, 1, 1, tzinfo=timezone.utc)),
    ])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(vec, "operator_alpha", "key_orig", priv, datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE))
    # Mutate key_id
    tampered_att = replace(att, key_id="key_alt")
    is_valid, err = verify_attestation(vec, tampered_att, registry=registry)
    assert is_valid is False
    assert "signature verification failed" in err


# ---------------------------------------------------------------------------
# 14. Signature with Modified Operator ID
# ---------------------------------------------------------------------------
def test_14_signature_with_modified_operator_id_fails_verification(tmp_path: Path):
    """Tampering with operator_id breaks cryptographic verification."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([
        AuthorizedOperatorKey("operator_alt", "key_orig", pub, datetime(2026, 1, 1, tzinfo=timezone.utc)),
    ])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(vec, "operator_orig", "key_orig", priv, datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE))
    tampered_att = replace(att, operator_id="operator_alt")
    is_valid, err = verify_attestation(vec, tampered_att, registry=registry)
    assert is_valid is False
    assert "signature verification failed" in err


# ---------------------------------------------------------------------------
# 15. Signature with Modified Timezone
# ---------------------------------------------------------------------------
def test_15_signature_with_modified_timezone_fails_verification(tmp_path: Path):
    """Mutating timezone of a source record invalidates signature."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([AuthorizedOperatorKey("operator_alpha", "key_01", pub, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(vec, "operator_alpha", "key_01", priv, datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE))
    # Mutate timezone on one source record
    tampered_manifest = [
        replace(s, timezone="UTC") if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    tampered_vec = replace(vec, provenance=replace(vec.provenance, source_manifest=tampered_manifest))
    is_valid, err = verify_attestation(tampered_vec, att, registry=registry)
    assert is_valid is False
    assert "signature verification failed" in err


# ---------------------------------------------------------------------------
# 16. Signature with Modified Provenance Type
# ---------------------------------------------------------------------------
def test_16_signature_with_modified_provenance_type_fails_verification(tmp_path: Path):
    """Mutating provenance_type of a source record invalidates signature."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([AuthorizedOperatorKey("operator_alpha", "key_01", pub, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(vec, "operator_alpha", "key_01", priv, datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE))
    tampered_manifest = [
        replace(s, provenance_type=ProvenanceType.HISTORICAL_BACKFILL) if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    tampered_vec = replace(vec, provenance=replace(vec.provenance, source_manifest=tampered_manifest))
    is_valid, err = verify_attestation(tampered_vec, att, registry=registry)
    assert is_valid is False
    assert "signature verification failed" in err


# ---------------------------------------------------------------------------
# 17. Signature with Modified Staleness
# ---------------------------------------------------------------------------
def test_17_signature_with_modified_staleness_fails_verification(tmp_path: Path):
    """Mutating staleness_seconds of a source record invalidates signature."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([AuthorizedOperatorKey("operator_alpha", "key_01", pub, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(vec, "operator_alpha", "key_01", priv, datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE))
    tampered_manifest = [
        replace(s, staleness_seconds=3600.0) if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    tampered_vec = replace(vec, provenance=replace(vec.provenance, source_manifest=tampered_manifest))
    is_valid, err = verify_attestation(tampered_vec, att, registry=registry)
    assert is_valid is False
    assert "signature verification failed" in err


# ---------------------------------------------------------------------------
# 18. Signature with Modified Raw Payload Reference
# ---------------------------------------------------------------------------
def test_18_signature_with_modified_raw_payload_ref_fails_verification(tmp_path: Path):
    """Mutating raw_payload_ref of a source record invalidates signature."""
    priv, pub = generate_operator_keypair()
    registry = OperatorKeyRegistry([AuthorizedOperatorKey("operator_alpha", "key_01", pub, datetime(2026, 1, 1, tzinfo=timezone.utc))])
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=RawPayloadStore(tmp_path))
    att = create_operator_attestation(vec, "operator_alpha", "key_01", priv, datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE))
    tampered_manifest = [
        replace(s, raw_payload_ref="/new/tampered/path/to/payload.bin") if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    tampered_vec = replace(vec, provenance=replace(vec.provenance, source_manifest=tampered_manifest))
    is_valid, err = verify_attestation(tampered_vec, att, registry=registry)
    assert is_valid is False
    assert "signature verification failed" in err


# ---------------------------------------------------------------------------
# 19. Valid Authorized Signature Passes All Gates
# ---------------------------------------------------------------------------
def test_19_valid_authorized_signature_passes_all_gates(tmp_path: Path):
    """Authentic operator attestation with registered key passes validator, inference, ledger."""
    priv, pub = generate_operator_keypair()
    auth_key = AuthorizedOperatorKey(
        operator_id="authorized_lead_operator",
        key_id="ed25519_prod_key_01",
        public_key_hex=pub,
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
        valid_until=datetime(2027, 1, 1, tzinfo=timezone.utc),
        is_revoked=False,
    )
    reg = OperatorKeyRegistry([auth_key])
    store = RawPayloadStore(base_dir=tmp_path / "raw")

    vec_raw = build_test_prospective_feature_vector(
        session_date="2026-11-02",
        provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE,
        source_id="operator_feed",
        payload_store=store,
    )
    att = create_operator_attestation(
        feature_vector=vec_raw,
        operator_id="authorized_lead_operator",
        key_id="ed25519_prod_key_01",
        private_key_hex=priv,
        signed_timestamp=datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE),
    )
    vec = replace(vec_raw, provenance=replace(vec_raw.provenance, attestation=att))

    # Validate against registry
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    from nifty_ai.shadow.crypto import set_default_key_registry
    set_default_key_registry(reg)

    rep = validator.validate(vec, current_time=eval_time)
    assert rep.status == ValidationStatus.PASSED
    assert rep.is_eligible_for_inference is True

    # Inference runner
    runner = ShadowInferenceRunner()
    temp_ledger = ShadowPredictionLedger(ledger_path=tmp_path / "temp_ledger.jsonl")
    pred = runner.predict(vec, rep, prev_record_hash=temp_ledger.get_tip_hash())
    assert pred.manifest_hash is not None
    assert pred.raw_evidence_digest is not None

    status, rec = temp_ledger.append_prediction(pred)
    assert status == LedgerStatus.RECORDED


# ---------------------------------------------------------------------------
# 20. Exact Canonical Instrument Mapping
# ---------------------------------------------------------------------------
def test_20_exact_canonical_instrument_mapping():
    """Verify exact 63 canonical feature mapping across price, calendar, and 16 context instruments."""
    manifest = build_test_source_manifest("2026-11-02")
    assert len(manifest) == 18  # 1 price + 1 calendar + 16 context

    covered_features = []
    for s in manifest:
        covered_features.extend(s.feature_names)

    assert len(covered_features) == 63
    assert len(set(covered_features)) == 63
    assert set(covered_features) == set(CANONICAL_FEATURES_63)


# ---------------------------------------------------------------------------
# 21. Inference Rejection After Source-Manifest Mutation
# ---------------------------------------------------------------------------
def test_21_inference_rejected_after_manifest_mutation(tmp_path: Path):
    """Mutating manifest after validator passes triggers runner defense-in-depth abort."""
    store = RawPayloadStore(base_dir=tmp_path / "raw")
    vec = build_test_prospective_feature_vector("2026-11-02", payload_store=store)

    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.status == ValidationStatus.PASSED

    # Corrupt artifact reference in manifest right before inference
    tainted = [
        replace(s, raw_payload_ref=str(tmp_path / "corrupted_missing_file.bin"))
        if s.instrument_symbol == "^NSEI" else s
        for s in vec.provenance.source_manifest
    ]
    tampered_vec = replace(vec, provenance=replace(vec.provenance, source_manifest=tainted))

    runner = ShadowInferenceRunner()
    with pytest.raises(ValueError, match="Raw payload artifact verification failed"):
        runner.predict(tampered_vec, rep)


# ---------------------------------------------------------------------------
# 22. Production Ledger Append Rejection on Non-Prospective Provenance
# ---------------------------------------------------------------------------
def test_22_production_ledger_append_with_invalid_provenance_rejected(tmp_path: Path):
    """Production ledger strictly rejects HISTORICAL_BACKFILL and INVALID_OR_QUARANTINED."""
    ledger = ShadowPredictionLedger(ledger_path=tmp_path / "prod_ledger.jsonl")

    from nifty_ai.shadow.contracts import ShadowPrediction
    pred_bad = ShadowPrediction(
        prediction_id="pred_hist",
        session_date="2026-11-02",
        target_date="2026-11-02",
        prediction_timestamp=datetime(2026, 11, 2, 8, 52, 0, tzinfo=timezone.utc),
        snapshot_type="SNAPSHOT_0850",
        cutoff_timestamp=datetime(2026, 11, 2, 3, 20, 0, tzinfo=timezone.utc),
        target_id="T0",
        predicted_return=0.001,
        predicted_return_bps=10.0,
        model_name="Snapshot B T0 Full Development Production Model",
        model_sha256="test",
        feature_hash="hash",
        feature_count=63,
        provenance_type="historical_backfill",
        research_status="RESEARCH_BASELINE_ONLY",
        trading_authorized=False,
        prev_record_hash="0" * 64,
        record_hash="rec_hash",
    )
    with pytest.raises(ValueError, match="strictly rejects non-prospective provenance"):
        ledger.append_prediction(pred_bad, enforce_prospective=True)
