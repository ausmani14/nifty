"""Tests for Phase 14 Step 5: Outcome Reconciliation & Forward Research Reporting."""

from datetime import datetime, time
from pathlib import Path
import pytest
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    LedgerStatus,
    ProvenanceType,
)
from nifty_ai.shadow.inference import ShadowInferenceRunner
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector
from nifty_ai.shadow.input_validator import SnapshotBInputValidator
from nifty_ai.shadow.ledger import ShadowPredictionLedger
from nifty_ai.shadow.reconciliation import ShadowOutcomeReconciler

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def isolated_shadow_system(tmp_path: Path):
    pred_path = tmp_path / "preds.jsonl"
    out_path = tmp_path / "outcomes.jsonl"
    ledger = ShadowPredictionLedger(ledger_path=pred_path)
    reconciler = ShadowOutcomeReconciler(prediction_ledger=ledger, outcomes_path=out_path)
    return ledger, reconciler


def test_reconciliation_before_market_close_fails(isolated_shadow_system):
    ledger, reconciler = isolated_shadow_system
    # Attempt to reconcile at 14:00 IST (market closes at 15:30 IST)
    acq_early = datetime(2026, 11, 2, 14, 0, 0, tzinfo=MARKET_TIMEZONE)
    with pytest.raises(ValueError, match="Cannot reconcile outcome prior to market close"):
        reconciler.reconcile_session(
            session_date="2026-11-02",
            open_price=24000.0,
            close_price=24100.0,
            acquisition_time=acq_early,
        )


def test_reconcile_unpredicted_session_fails(isolated_shadow_system):
    ledger, reconciler = isolated_shadow_system
    acq_time = datetime(2026, 11, 2, 16, 0, 0, tzinfo=MARKET_TIMEZONE)
    with pytest.raises(ValueError, match="No pre-market prediction found"):
        reconciler.reconcile_session(
            session_date="2026-11-02",
            open_price=24000.0,
            close_price=24100.0,
            acquisition_time=acq_time,
        )


def test_end_to_end_reconciliation_and_metrics(isolated_shadow_system):
    ledger, reconciler = isolated_shadow_system
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    # Generate 5 prospective predictions and reconcile them
    dates = ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06"]
    mock_opens = [24000.0, 24100.0, 24050.0, 24200.0, 24150.0]
    mock_closes = [23950.0, 24150.0, 23900.0, 24250.0, 24100.0]

    for idx, s_date in enumerate(dates):
        # 1. Pre-market input capture at 08:45 IST
        vec = build_synthetic_feature_vector(
            session_date=s_date,
            provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
        )
        acq_date = datetime.strptime(s_date, "%Y-%m-%d").date()
        eval_time = datetime.combine(acq_date, time(8, 52, 0), tzinfo=MARKET_TIMEZONE)
        report = validator.validate(vec, current_time=eval_time)
        assert report.is_eligible_for_inference is True

        # 2. Pre-market prediction at 08:52 IST
        pred = runner.predict(vec, report, prev_record_hash=ledger.get_tip_hash())
        status, _ = ledger.append_prediction(pred)
        assert status == LedgerStatus.RECORDED

        # 3. Post-market outcome reconciliation at 16:00 IST
        outcome = reconciler.reconcile_session(
            session_date=s_date,
            open_price=mock_opens[idx],
            close_price=mock_closes[idx],
            acquisition_time=datetime.combine(acq_date, time(16, 0, 0), tzinfo=MARKET_TIMEZONE),
        )

        expected_t0 = (mock_closes[idx] / mock_opens[idx]) - 1.0
        assert outcome.realized_t0 == pytest.approx(expected_t0, abs=1e-8)
        assert outcome.realized_t0_bps == pytest.approx(expected_t0 * 10000.0, abs=1e-4)

    # 4. Compute forward metrics
    metrics = reconciler.compute_forward_metrics(filter_prospective_only=True)
    assert metrics["sample_size"] == 5
    assert "pearson_ic" in metrics
    assert "model_mae_bps" in metrics
    assert "zero_benchmark_mae_bps" in metrics
    assert "incremental_r2" in metrics
    assert "model_mda_pct" in metrics
    assert metrics["long_prediction_count"] + metrics["short_prediction_count"] + metrics["flat_prediction_count"] == 5


def test_prospective_filtering_excludes_quarantined_fixtures(isolated_shadow_system):
    ledger, reconciler = isolated_shadow_system
    from nifty_ai.shadow.contracts import ShadowPrediction

    # Create a quarantined fixture prediction directly on isolated test ledger
    pred = ShadowPrediction(
        prediction_id="pred_2026-11-02_0850",
        session_date="2026-11-02",
        target_date="2026-11-02",
        prediction_timestamp=datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE),
        snapshot_type="SNAPSHOT_0850",
        cutoff_timestamp=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        target_id="T0",
        predicted_return=0.001,
        predicted_return_bps=10.0,
        model_name="test_model",
        model_sha256="test_sha",
        feature_hash="hash",
        feature_count=63,
        provenance_type=ProvenanceType.INVALID_OR_QUARANTINED.value,
        research_status="RESEARCH_BASELINE_ONLY",
        trading_authorized=False,
        prev_record_hash=ledger.get_tip_hash(),
        record_hash="a" * 64,
    )
    ledger.append_prediction(pred)

    reconciler.reconcile_session(
        session_date="2026-11-02",
        open_price=24000.0,
        close_price=24100.0,
        acquisition_time=datetime(2026, 11, 2, 16, 0, 0, tzinfo=MARKET_TIMEZONE),
    )

    # When filtering prospective only, quarantined fixture must be excluded
    metrics = reconciler.compute_forward_metrics(filter_prospective_only=True)
    assert metrics["sample_size"] == 0
    assert metrics["status"] == "ZERO_QUALIFIED_PROSPECTIVE_SESSIONS"
