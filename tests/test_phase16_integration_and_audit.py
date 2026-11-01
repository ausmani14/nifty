"""Phase 16 Independent Verification, Integration, and Security Audit Suite.

Covers:
- Group A: Model integrity and cryptographic authentication
- Group B: Point-in-time input validation, timezones, and staleness
- Group C: Prediction ledger append-only chaining and idempotency
- Group D: Outcome reconciliation gates and price validation
- Group E: Daily operational workflows, health check, and dry run
- Group F: Website JSON contracts and multi-destination mirroring
- Group G: Zero-leakage isolated end-to-end lifecycle and genesis protection
"""

from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import tempfile
from typing import List
import pytest
from zoneinfo import ZoneInfo

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    CANONICAL_META_SHA256,
    CANONICAL_MODEL_SHA256,
    FeatureVector,
    LedgerStatus,
    ProvenanceType,
    ShadowPrediction,
    SourceProvenance,
    ValidationStatus,
)
from nifty_ai.shadow.inference import ShadowInferenceRunner
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector
from nifty_ai.shadow.input_validator import (
    SNAPSHOT_B_CUTOFF_TIME,
    SnapshotBInputValidator,
    compute_feature_vector_hash,
)
from nifty_ai.shadow.ledger import DEFAULT_LEDGER_PATH, ShadowPredictionLedger
from nifty_ai.shadow.live_data import (
    CaptureStatus,
    attempt_live_feature_capture,
    is_nse_trading_day,
)
from nifty_ai.shadow.model_protection import (
    ModelIntegrityError,
    assert_frozen_model_intact,
    audit_frozen_model_protection,
    compute_file_sha256,
)
from nifty_ai.shadow.reconciliation import (
    DEFAULT_OUTCOMES_PATH,
    ShadowOutcomeReconciler,
)
from nifty_ai.shadow.website_exporter import WebsiteDataExporter

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")
FROZEN_MODEL_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "phase13_steps2_4"
    / "models"
    / "snapshot_b_t0_primary_model.json"
)
FROZEN_META_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "phase13_steps2_4"
    / "models"
    / "snapshot_b_t0_primary_model.meta.json"
)


# ==============================================================================
# GROUP A: MODEL INTEGRITY AUDIT
# ==============================================================================

def test_group_a_model_sha256_exact_byte_match():
    """Verify frozen model binary byte-for-byte against registered SHA-256."""
    actual_hash = compute_file_sha256(FROZEN_MODEL_PATH)
    assert actual_hash == CANONICAL_MODEL_SHA256


def test_group_a_meta_sha256_exact_byte_match():
    """Verify frozen model metadata byte-for-byte against registered SHA-256."""
    actual_meta_hash = compute_file_sha256(FROZEN_META_PATH)
    assert actual_meta_hash == CANONICAL_META_SHA256


def test_group_a_model_structure_trees_and_features():
    """Verify loaded booster structure directly has N*=43 trees and 63 features."""
    import xgboost as xgb
    booster = xgb.Booster()
    booster.load_model(str(FROZEN_MODEL_PATH))
    assert len(booster.get_dump()) == 43
    assert booster.num_features() == 63


def test_group_a_model_byte_invariance_under_load():
    """Verify that loading the frozen model does not modify the file on disk."""
    hash_before = compute_file_sha256(FROZEN_MODEL_PATH)
    runner = ShadowInferenceRunner()
    hash_after = compute_file_sha256(FROZEN_MODEL_PATH)
    assert hash_before == hash_after == CANONICAL_MODEL_SHA256


def test_group_a_detects_wrong_sha(tmp_path: Path):
    """Corrupted binary triggers MODEL_INTEGRITY_FAILURE."""
    corrupt = tmp_path / "bad_model.json"
    corrupt.write_text('{"bad": 1}', encoding="utf-8")
    report = audit_frozen_model_protection(model_path=corrupt, meta_path=FROZEN_META_PATH)
    assert report.is_intact is False
    assert report.error_code == "MODEL_INTEGRITY_FAILURE"


def test_group_a_detects_wrong_tree_count(tmp_path: Path):
    """Metadata with wrong tree count triggers MODEL_INTEGRITY_FAILURE."""
    with open(FROZEN_META_PATH, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)
    meta_dict["hyperparameters"]["n_estimators"] = 42  # modified
    bad_meta = tmp_path / "bad_meta.json"
    bad_meta.write_text(json.dumps(meta_dict), encoding="utf-8")

    report = audit_frozen_model_protection(model_path=FROZEN_MODEL_PATH, meta_path=bad_meta)
    assert report.is_intact is False
    assert report.error_code == "MODEL_INTEGRITY_FAILURE"


def test_group_a_inference_defense_in_depth_rejects_malformed_features():
    """Inference runner directly rejects bad feature lists without trusting caller."""
    runner = ShadowInferenceRunner()
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE)
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = validator.validate(vec, current_time=eval_time)

    # Missing feature (62 instead of 63)
    bad_vec = FeatureVector(
        session_date="2026-11-02",
        cutoff_time=vec.cutoff_time,
        feature_names=vec.feature_names[:-1],
        feature_values=vec.feature_values[:-1],
        feature_hash="hash",
        provenance=vec.provenance,
    )
    with pytest.raises(ValueError, match="requires exactly 63 features"):
        runner.predict(bad_vec, report)

    # Shuffled feature order
    shuffled_names = list(vec.feature_names)
    shuffled_names[0], shuffled_names[1] = shuffled_names[1], shuffled_names[0]
    shuffled_vec = FeatureVector(
        session_date="2026-11-02",
        cutoff_time=vec.cutoff_time,
        feature_names=shuffled_names,
        feature_values=vec.feature_values,
        feature_hash="hash",
        provenance=vec.provenance,
    )
    with pytest.raises(ValueError, match="feature names or sequence do not match canonical"):
        runner.predict(shuffled_vec, report)


# ==============================================================================
# GROUP B: POINT-IN-TIME VALIDATION AUDIT
# ==============================================================================

def test_group_b_valid_pit_timestamp_passes():
    """Valid observation timestamp prior to 08:50 IST passes."""
    validator = SnapshotBInputValidator()
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE)
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = validator.validate(vec, current_time=eval_time)
    assert report.status == ValidationStatus.PASSED
    assert report.is_eligible_for_inference is True


def test_group_b_rejects_late_cutoff_timestamp():
    """Cutoff after 08:50:00 IST fails validation."""
    validator = SnapshotBInputValidator()
    late_cutoff = datetime(2026, 11, 2, 8, 55, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=late_cutoff,
        provenance_type=ProvenanceType.INVALID_OR_QUARANTINED,
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "CUTOFF_TIME_ENFORCEMENT" in report.failed_checks


def test_group_b_rejects_timezone_naive_timestamp():
    """Timezone-naive datetime fails validation."""
    validator = SnapshotBInputValidator()
    naive_cutoff = datetime(2026, 11, 2, 8, 50, 0)  # tzinfo=None
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=naive_cutoff,
        provenance_type=ProvenanceType.INVALID_OR_QUARANTINED,
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "TIMEZONE_AWARENESS" in report.failed_checks


def test_group_b_rejects_future_observation_timestamp():
    """Observation timestamp in the future fails validation."""
    validator = SnapshotBInputValidator()
    future_obs = datetime(2026, 11, 2, 8, 55, 0, tzinfo=MARKET_TIMEZONE)
    cutoff = datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=cutoff,
        observation_time=future_obs,
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "OBSERVATION_TIME_VALIDITY" in report.failed_checks


def test_group_b_rejects_excessively_stale_source():
    """Observation older than 7 days fails validation."""
    validator = SnapshotBInputValidator()
    session_dt = datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE)
    stale_obs = session_dt - timedelta(days=15)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=session_dt,
        observation_time=stale_obs,
        provenance_type=ProvenanceType.INVALID_OR_QUARANTINED,
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "STALE_SOURCE_DATA" in report.failed_checks


def test_group_b_rejects_non_finite_values():
    """NaN and Inf values are rejected."""
    validator = SnapshotBInputValidator()
    vals = [0.001] * 63
    vals[5] = float("nan")
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        feature_values=vals,
        provenance_type=ProvenanceType.INVALID_OR_QUARANTINED,
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "FINITE_VALUES" in report.failed_checks


# ==============================================================================
# GROUP C: PREDICTION LEDGER AUDIT
# ==============================================================================

def test_group_c_ledger_append_idempotency_and_chaining(tmp_path: Path):
    """Test append, idempotency on duplicate session, and cryptographic hash chaining."""
    ledger_file = tmp_path / "test_ledger.jsonl"
    ledger = ShadowPredictionLedger(ledger_path=ledger_file)
    assert ledger.get_tip_hash() == "0" * 64

    runner = ShadowInferenceRunner()
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE)
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = validator.validate(vec, current_time=eval_time)

    pred1 = runner.predict(vec, report, prev_record_hash=ledger.get_tip_hash())
    status, rec1 = ledger.append_prediction(pred1)
    assert status == LedgerStatus.RECORDED
    assert ledger.get_tip_hash() == pred1.record_hash

    # Duplicate prediction for same session ignored idempotently
    status_dup, rec_dup = ledger.append_prediction(pred1)
    assert status_dup == LedgerStatus.DUPLICATE_IGNORED
    assert len(ledger.get_all_records()) == 1

    # Verify integrity passes
    is_valid, issues = ledger.verify_integrity()
    assert is_valid is True


def test_group_c_ledger_detects_tampering(tmp_path: Path):
    """Tampering with a persisted record hash or content fails integrity audit."""
    ledger_file = tmp_path / "test_ledger.jsonl"
    ledger = ShadowPredictionLedger(ledger_path=ledger_file)
    runner = ShadowInferenceRunner()
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE)
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = SnapshotBInputValidator().validate(vec, current_time=eval_time)
    pred = runner.predict(vec, report, prev_record_hash=ledger.get_tip_hash())
    ledger.append_prediction(pred)

    # Tamper with file
    content = ledger_file.read_text(encoding="utf-8")
    tampered = content.replace('"T0"', '"TAMPERED_T0"')
    ledger_file.write_text(tampered, encoding="utf-8")

    is_valid, issues = ledger.verify_integrity()
    assert is_valid is False
    assert any("Record tamper detected" in iss for iss in issues)


# ==============================================================================
# GROUP D: RECONCILIATION AUDIT
# ==============================================================================

def test_group_d_reconciliation_lifecycle(tmp_path: Path):
    """Test valid outcome reconciliation, duplicate idempotency, and premature market close rejection."""
    pred_file = tmp_path / "preds.jsonl"
    out_file = tmp_path / "outs.jsonl"
    ledger = ShadowPredictionLedger(ledger_path=pred_file)
    reconciler = ShadowOutcomeReconciler(prediction_ledger=ledger, outcomes_path=out_file)

    runner = ShadowInferenceRunner()
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE)
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = SnapshotBInputValidator().validate(vec, current_time=eval_time)
    pred = runner.predict(vec, report, prev_record_hash=ledger.get_tip_hash())
    ledger.append_prediction(pred)

    # Rejection prior to 15:30 IST market close
    early_time = datetime(2026, 11, 2, 14, 0, 0, tzinfo=MARKET_TIMEZONE)
    with pytest.raises(ValueError, match="Cannot reconcile outcome prior to market close"):
        reconciler.reconcile_session(
            session_date="2026-11-02",
            open_price=24000.0,
            close_price=24120.0,
            acquisition_time=early_time,
        )

    # Valid post-market reconciliation
    valid_time = datetime(2026, 11, 2, 16, 0, 0, tzinfo=MARKET_TIMEZONE)
    out = reconciler.reconcile_session(
        session_date="2026-11-02",
        open_price=24000.0,
        close_price=24120.0,
        acquisition_time=valid_time,
    )
    assert out.status == "RECONCILED"
    assert out.realized_open == 24000.0
    assert out.realized_close == 24120.0
    assert pytest.approx(out.realized_t0, 1e-6) == 0.0050  # +50 bps

    # Idempotent repeat call
    out_repeat = reconciler.reconcile_session(
        session_date="2026-11-02",
        open_price=24000.0,
        close_price=24120.0,
        acquisition_time=valid_time,
    )
    assert out_repeat.outcome_id == out.outcome_id
    assert len(reconciler.get_all_outcomes()) == 1


def test_group_d_reconciler_rejects_invalid_prices(tmp_path: Path):
    """Reconciler rejects zero, negative, and NaN prices."""
    pred_file = tmp_path / "preds.jsonl"
    out_file = tmp_path / "outs.jsonl"
    ledger = ShadowPredictionLedger(ledger_path=pred_file)
    reconciler = ShadowOutcomeReconciler(prediction_ledger=ledger, outcomes_path=out_file)

    runner = ShadowInferenceRunner()
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE)
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = SnapshotBInputValidator().validate(vec, current_time=eval_time)
    ledger.append_prediction(runner.predict(vec, report, prev_record_hash=ledger.get_tip_hash()))

    valid_time = datetime(2026, 11, 2, 16, 0, 0, tzinfo=MARKET_TIMEZONE)
    with pytest.raises(ValueError, match="Invalid non-positive price"):
        reconciler.reconcile_session("2026-11-02", open_price=-10.0, close_price=24000.0, acquisition_time=valid_time)

    with pytest.raises(ValueError, match="NaN or infinite price"):
        reconciler.reconcile_session("2026-11-02", open_price=float("nan"), close_price=24000.0, acquisition_time=valid_time)


# ==============================================================================
# GROUP E: DAILY OPERATIONS & CAPTURE GATES
# ==============================================================================

def test_group_e_backdating_strictly_prevented():
    """Attempting prospective capture for a date in the past returns MISSED_CUTOFF."""
    past_date = "2020-01-01"
    res = attempt_live_feature_capture(session_date=past_date)
    assert res.status == CaptureStatus.MISSED_CUTOFF
    assert "Backdating is strictly prohibited" in (res.reason or "")


def test_group_e_unconnected_live_feed_fails_closed():
    """When no verified live feed is connected, system returns DATA_SOURCE_BLOCKED."""
    # Eligible trading day evaluated within [08:50, 09:15) window without input file
    future_monday = "2026-11-02"
    now_ist = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture(session_date=future_monday, current_time=now_ist)
    assert res.status == CaptureStatus.DATA_SOURCE_BLOCKED
    assert "Under zero-fabrication governance" in (res.reason or "")


# ==============================================================================
# GROUP F: WEBSITE DATA CONTRACT & MIRRORING
# ==============================================================================

def test_group_f_website_data_exporter_mirrors_to_web_data(tmp_path: Path):
    """Exporter generates all 6 standardized contracts in primary and mirror paths."""
    out_dir = tmp_path / "website_data"
    mirror_dir = tmp_path / "web" / "data"
    ledger = ShadowPredictionLedger(ledger_path=tmp_path / "preds.jsonl")
    reconciler = ShadowOutcomeReconciler(prediction_ledger=ledger, outcomes_path=tmp_path / "outs.jsonl")

    exporter = WebsiteDataExporter(
        output_dir=out_dir,
        mirror_dir=mirror_dir,
        prediction_ledger=ledger,
        outcome_reconciler=reconciler,
    )
    paths = exporter.export_all()

    contracts = [
        "latest_prediction.json",
        "prediction_history.json",
        "outcome_history.json",
        "system_status.json",
        "model_info.json",
        "performance_summary.json",
    ]

    for c in contracts:
        primary_file = out_dir / c
        mirror_file = mirror_dir / c
        assert primary_file.exists()
        assert mirror_file.exists()
        # Ensure identical content
        assert primary_file.read_text(encoding="utf-8") == mirror_file.read_text(encoding="utf-8")


# ==============================================================================
# GROUP G: ISOLATED END-TO-END LIFECYCLE & GENESIS PROTECTION
# ==============================================================================

def test_group_g_isolated_end_to_end_preserves_real_ledger():
    """Verify full end-to-end simulation in temp dir does not alter genesis production ledgers."""
    real_pred_ledger = ShadowPredictionLedger()
    real_out_reconciler = ShadowOutcomeReconciler()

    # Genesis check
    assert len(real_pred_ledger.get_all_records()) == 0
    assert len(real_out_reconciler.get_all_outcomes()) == 0

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_p = Path(tmp_dir)
        pred_p = tmp_p / "p.jsonl"
        out_p = tmp_p / "o.jsonl"
        web_p = tmp_p / "web_data"
        mir_p = tmp_p / "web" / "data"

        t_ledger = ShadowPredictionLedger(ledger_path=pred_p)
        t_reconciler = ShadowOutcomeReconciler(prediction_ledger=t_ledger, outcomes_path=out_p)
        t_exporter = WebsiteDataExporter(output_dir=web_p, mirror_dir=mir_p, prediction_ledger=t_ledger, outcome_reconciler=t_reconciler)

        # 1. Prediction
        vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE)
        eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
        rep = SnapshotBInputValidator().validate(vec, current_time=eval_time)
        pred = ShadowInferenceRunner().predict(vec, rep, prev_record_hash=t_ledger.get_tip_hash())
        t_ledger.append_prediction(pred)

        # 2. Outcome
        t_reconciler.reconcile_session(
            "2026-11-02",
            24000.0,
            24100.0,
            acquisition_time=datetime(2026, 11, 2, 16, 0, 0, tzinfo=MARKET_TIMEZONE),
        )

        # 3. Export
        t_exporter.export_all()

        assert len(t_ledger.get_all_records()) == 1
        assert len(t_reconciler.get_all_outcomes()) == 1

    # Real ledgers must STILL be at exactly zero
    assert len(real_pred_ledger.get_all_records()) == 0
    assert len(real_out_reconciler.get_all_outcomes()) == 0
    assert real_pred_ledger.get_tip_hash() == "0" * 64


def test_empty_ledger_displays_no_valid_prospective_prediction(tmp_path: Path):
    """Empty ledger exports 'NO VALID PROSPECTIVE PREDICTION' status label."""
    exporter = WebsiteDataExporter(output_dir=tmp_path / "web_data")
    p = exporter.export_latest_prediction()
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["has_prediction"] is False
    assert data["prediction_status"] == "NO VALID PROSPECTIVE PREDICTION"


def test_root_index_html_redirects_to_web():
    """Verify repository root contains index.html redirecting to web/ for Pages root publishing."""
    root_index = PROJECT_ROOT / "index.html"
    assert root_index.exists()
    content = root_index.read_text(encoding="utf-8")
    assert 'url=web/' in content
    assert 'window.location.replace("web/");' in content


def test_rejects_pre_cutoff_observation_substituting_for_0850():
    """Early cutoff time (e.g. 08:35 IST) is rejected by SnapshotBInputValidator."""
    early_cutoff = datetime(2026, 11, 2, 8, 35, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=early_cutoff,
        provenance_type=ProvenanceType.INVALID_OR_QUARANTINED,
    )
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = SnapshotBInputValidator().validate(vec, current_time=eval_time)
    assert report.status == ValidationStatus.FAILED
    assert "CUTOFF_TIME_ENFORCEMENT" in report.failed_checks
    assert any("Pre-cutoff observations cannot substitute" in err for err in report.error_messages)
