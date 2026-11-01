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


# ---------------------------------------------------------------------------
# 23. RFC 8032 Standard Test Vectors Verification
# ---------------------------------------------------------------------------
def test_23_rfc8032_standard_test_vectors():
    """Verify Ed25519 signing and verification match official RFC 8032 vectors exactly."""
    from nifty_ai.shadow.crypto import derive_public_key, ed25519_sign, ed25519_verify

    # Vector 1
    sk1 = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pk1 = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    msg1 = b""
    sig1 = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )
    assert derive_public_key(sk1.hex()) == pk1.hex()
    assert ed25519_sign(msg1, sk1) == sig1
    assert ed25519_verify(msg1, sig1, pk1) is True

    # Vector 2
    sk2 = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
    pk2 = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    msg2 = bytes.fromhex("72")
    sig2 = bytes.fromhex(
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
    )
    assert derive_public_key(sk2.hex()) == pk2.hex()
    assert ed25519_sign(msg2, sk2) == sig2
    assert ed25519_verify(msg2, sig2, pk2) is True


# ---------------------------------------------------------------------------
# 24. Content-Addressed Storage Filename and Atomicity
# ---------------------------------------------------------------------------
def test_24_content_addressed_storage_filename_and_atomicity(tmp_path: Path):
    """Raw payload store writes {sym}_{sha256}.bin, exclusive atomic creation, and collision check."""
    store = RawPayloadStore(base_dir=tmp_path / "raw")
    content = b"GENUINE_MARKET_EVIDENCE_STREAM_DATA"
    h = hashlib.sha256(content).hexdigest()

    sha, ref = store.store_payload("2026-11-02", "^NSEI", content)
    assert sha == h
    assert f"NSEI_{h}.bin" in ref
    assert Path(ref).is_file() or (tmp_path / "raw" / "2026-11-02" / f"NSEI_{h}.bin").is_file()

    # Idempotent write with identical bytes succeeds
    sha2, ref2 = store.store_payload("2026-11-02", "^NSEI", content)
    assert sha2 == h
    assert ref2 == ref

    # Attempt to write different content to existing path raises ValueError
    target_file = tmp_path / "raw" / "2026-11-02" / f"NSEI_{h}.bin"
    target_file.write_bytes(b"CORRUPTED_BYTES")
    with pytest.raises(ValueError, match="Hash collision / corruption"):
        store.store_payload("2026-11-02", "^NSEI", content)


# ---------------------------------------------------------------------------
# 25. Raw Payload Store Traversal and Symlink Guards
# ---------------------------------------------------------------------------
def test_25_raw_payload_store_traversal_and_symlink_guards(tmp_path: Path):
    """Store rejects path traversal and symlinks strictly."""
    store = RawPayloadStore(base_dir=tmp_path / "raw")
    content = b"PAYLOAD_DATA"

    # Traversal in session_date is rejected by date regex
    with pytest.raises(ValueError, match="Invalid session_date format"):
        store.store_payload("../../2026-11-02", "^NSEI", content)

    # Retrieval of symlink is blocked
    normal_sha, normal_ref = store.store_payload("2026-11-02", "^NSEI", content)
    symlink_file = tmp_path / "raw" / "symlink.bin"
    try:
        symlink_file.symlink_to(Path(normal_ref).resolve())
        assert store.retrieve_payload(str(symlink_file)) is None
    except (OSError, NotImplementedError):
        pass  # On Windows without developer mode/admin rights, symlink creation may not be permitted


# ---------------------------------------------------------------------------
# 26. Raw Payload Store Date and Instrument Validation
# ---------------------------------------------------------------------------
def test_26_raw_payload_store_date_and_instrument_validation(tmp_path: Path):
    """Store validates session_date and canonical instrument allowlist."""
    store = RawPayloadStore(base_dir=tmp_path / "raw")
    content = b"SOME_DATA"

    # Invalid dates
    with pytest.raises(ValueError, match="Invalid session_date format"):
        store.store_payload("20261102", "^NSEI", content)

    with pytest.raises(ValueError, match="not a valid calendar date"):
        store.store_payload("2026-02-30", "^NSEI", content)

    # Disallowed instrument
    with pytest.raises(ValueError, match="not in canonical instrument allowlist"):
        store.store_payload("2026-11-02", "UNREGISTERED_TICKER", content)


# ---------------------------------------------------------------------------
# 27. Deterministic Canonical JSON Manifest Hash (RFC 8785)
# ---------------------------------------------------------------------------
def test_27_deterministic_canonical_json_manifest_hash():
    """Manifest hash is independent of record order and sensitive to every field."""
    from nifty_ai.shadow.crypto import compute_manifest_hash

    manifest = build_test_source_manifest("2026-11-02")
    hash_original = compute_manifest_hash(manifest)

    # Reversing the order produces the exact same hash
    reversed_manifest = list(reversed(manifest))
    hash_reversed = compute_manifest_hash(reversed_manifest)
    assert hash_original == hash_reversed

    # Modifying any field produces a different hash
    mod_staleness = [replace(manifest[0], staleness_seconds=99.0)] + list(manifest[1:])
    assert compute_manifest_hash(mod_staleness) != hash_original

    mod_tz = [replace(manifest[0], timezone="UTC")] + list(manifest[1:])
    assert compute_manifest_hash(mod_tz) != hash_original


# ---------------------------------------------------------------------------
# 28. Operator Key Registry File Loading and Isolation
# ---------------------------------------------------------------------------
def test_28_operator_key_registry_file_loading_and_isolation(tmp_path: Path):
    """OperatorKeyRegistry loads from reviewed JSON file and fails closed if empty."""
    from nifty_ai.shadow.crypto import load_operator_key_registry

    # Missing file returns empty registry
    empty_reg = load_operator_key_registry(tmp_path / "nonexistent.json")
    assert empty_reg.is_empty() is True

    # Empty array returns empty registry
    empty_json = tmp_path / "empty_keys.json"
    empty_json.write_text("[]", encoding="utf-8")
    loaded_empty = load_operator_key_registry(empty_json)
    assert loaded_empty.is_empty() is True

    # Valid config
    valid_json = tmp_path / "valid_keys.json"
    valid_data = [
        {
            "operator_id": "op_test",
            "key_id": "key_test_01",
            "public_key_hex": "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
            "valid_from": "2026-01-01T00:00:00+00:00",
            "valid_until": "2027-01-01T00:00:00+00:00",
            "is_revoked": False,
        }
    ]
    valid_json.write_text(json.dumps(valid_data), encoding="utf-8")
    loaded_valid = load_operator_key_registry(valid_json)
    assert loaded_valid.is_empty() is False
    assert loaded_valid.get_key("key_test_01") is not None


# ---------------------------------------------------------------------------
# 29. Synthetic Builders Strictly Quarantined
# ---------------------------------------------------------------------------
def test_29_synthetic_builders_strictly_quarantined():
    """Synthetic builders fail closed if prospective provenance is attempted."""
    from nifty_ai.shadow.input_capture import (
        build_canonical_source_manifest,
        build_synthetic_feature_vector,
    )

    # build_synthetic_feature_vector rejects prospective provenance
    with pytest.raises(ValueError, match="strictly quarantined"):
        build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE)

    # build_synthetic_feature_vector rejects impersonating source provider
    with pytest.raises(ValueError, match="cannot impersonate production"):
        build_synthetic_feature_vector("2026-11-02", source_id="production_live_feed")

    # build_canonical_source_manifest rejects prospective provenance
    with pytest.raises(ValueError, match="cannot be used for prospective provenance"):
        build_canonical_source_manifest("2026-11-02", provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE)


# ---------------------------------------------------------------------------
# 30. Production Manifest Validates Timezones and Chronology
# ---------------------------------------------------------------------------
def test_30_production_manifest_validates_timezones_and_chronology(tmp_path: Path):
    """Production manifest rejects invalid timezones, non-chronological timestamps, and missing fields."""
    store = RawPayloadStore(base_dir=tmp_path / "raw")

    # Construct complete payload set for 18 instruments
    required = ["^NSEI", "CALENDAR"] + list(CANONICAL_CONTEXT_MAPPING.keys())
    payloads = {sym: f"DATA_{sym}".encode("utf-8") for sym in required}

    now_utc = datetime(2026, 11, 2, 8, 48, 0, tzinfo=timezone.utc)
    metadata = {
        sym: {
            "observation_time": now_utc - timedelta(minutes=3),
            "availability_time": now_utc - timedelta(minutes=1),
            "ingestion_time": now_utc,
            "timezone": "Asia/Kolkata" if sym in {"^NSEI", "CALENDAR", "^NSEBANK", "^INDIAVIX", "IN10YT=RR", "INR=X"} else ("Europe/London" if sym in {"BZ=F", "^FTSE"} else ("Asia/Tokyo" if sym == "^N225" else ("Asia/Hong_Kong" if sym == "^HSI" else "America/New_York"))),
        }
        for sym in required
    }

    # Perfectly valid call succeeds
    records = build_production_source_manifest(
        session_date="2026-11-02",
        instrument_payloads=payloads,
        instrument_metadata=metadata,
        payload_store=store,
    )
    assert len(records) == 18

    # Wrong timezone for ^NSEI fails closed
    bad_meta = dict(metadata)
    bad_meta["^NSEI"] = dict(metadata["^NSEI"], timezone="America/New_York")
    with pytest.raises(ValueError, match="Timezone for '\\^NSEI' must match canonical timezone 'Asia/Kolkata'"):
        build_production_source_manifest(
            session_date="2026-11-02",
            instrument_payloads=payloads,
            instrument_metadata=bad_meta,
            payload_store=store,
        )

    # Inverted timestamps fail closed
    bad_time_meta = dict(metadata)
    bad_time_meta["^NSEI"] = dict(
        metadata["^NSEI"],
        observation_time=now_utc,
        availability_time=now_utc - timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="Metadata timestamps for '\\^NSEI' must be chronological"):
        build_production_source_manifest(
            session_date="2026-11-02",
            instrument_payloads=payloads,
            instrument_metadata=bad_time_meta,
            payload_store=store,
        )

