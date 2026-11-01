"""Tests for Phase 14 Step 3: Frozen Model Inference Runner."""

from datetime import datetime
import pytest
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    CANONICAL_MODEL_SHA256,
    ProvenanceType,
    ValidationStatus,
)
from nifty_ai.shadow.inference import (
    ShadowInferenceRunner,
    verify_frozen_model_artifacts,
)
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector
from nifty_ai.shadow.input_validator import SnapshotBInputValidator

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def test_frozen_model_artifacts_verification():
    meta = verify_frozen_model_artifacts()
    assert meta["model_name"] == "Snapshot B T0 Full Development Production Model"
    assert meta["feature_count"] == 63
    assert meta["hyperparameters"]["n_estimators"] == 43


def test_inference_runner_initialization_and_prediction():
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = validator.validate(vec, current_time=eval_time)
    assert report.is_eligible_for_inference is True

    pred = runner.predict(vec, report, prev_record_hash="0" * 64)

    assert pred.prediction_id == "pred_2026-11-02_0850"
    assert pred.session_date == "2026-11-02"
    assert pred.target_id == "T0"
    assert pred.model_sha256 == CANONICAL_MODEL_SHA256
    assert pred.feature_count == 63
    assert pred.research_status == "RESEARCH_BASELINE_ONLY"
    assert pred.trading_authorized is False
    assert isinstance(pred.predicted_return, float)
    assert pred.predicted_return_bps == pytest.approx(pred.predicted_return * 10000.0, rel=1e-5)
    assert len(pred.record_hash) == 64


def test_inference_runner_fails_on_ineligible_input():
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    # Invalid feature vector with NaN
    vals = [0.01] * 63
    vals[0] = float("nan")
    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        feature_values=vals,
        provenance_type=ProvenanceType.HISTORICAL_BACKFILL,
    )
    report = validator.validate(vec)
    assert report.is_eligible_for_inference is False

    with pytest.raises(ValueError, match="Cannot generate prediction"):
        runner.predict(vec, report)


def test_deterministic_prediction_reproducibility():
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        feature_values=[0.005] * 63,
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = validator.validate(vec, current_time=eval_time)

    pred1 = runner.predict(vec, report, prev_record_hash="0" * 64)
    pred2 = runner.predict(vec, report, prev_record_hash="0" * 64)

    assert pred1.predicted_return == pred2.predicted_return
    assert pred1.predicted_return_bps == pred2.predicted_return_bps
