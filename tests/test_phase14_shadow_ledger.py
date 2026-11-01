"""Tests for Phase 14 Step 4: Immutable Prospective Prediction Ledger."""

from datetime import datetime, time
import json
from pathlib import Path
import pytest
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import LedgerStatus, ProvenanceType
from nifty_ai.shadow.inference import ShadowInferenceRunner
from nifty_ai.shadow.input_capture import (
    build_synthetic_feature_vector,
    build_verified_prospective_feature_vector,
)
from nifty_ai.shadow.input_validator import SnapshotBInputValidator
from nifty_ai.shadow.ledger import GENESIS_HASH, ShadowPredictionLedger

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def temp_ledger(tmp_path: Path) -> ShadowPredictionLedger:
    ledger_path = tmp_path / "test_predictions_ledger.jsonl"
    return ShadowPredictionLedger(ledger_path=ledger_path)


def test_empty_ledger_integrity(temp_ledger: ShadowPredictionLedger):
    assert temp_ledger.get_tip_hash() == GENESIS_HASH
    is_valid, issues = temp_ledger.verify_integrity()
    assert is_valid is True


def test_append_single_prediction_and_chaining(temp_ledger: ShadowPredictionLedger):
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    vec = build_verified_prospective_feature_vector(
        session_date="2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = validator.validate(vec, current_time=eval_time)
    pred1 = runner.predict(vec, report, prev_record_hash=temp_ledger.get_tip_hash())

    status, rec = temp_ledger.append_prediction(pred1)
    assert status == LedgerStatus.RECORDED
    assert temp_ledger.get_tip_hash() == pred1.record_hash

    # Verify integrity
    is_valid, issues = temp_ledger.verify_integrity()
    assert is_valid is True
    assert len(issues) == 0


def test_duplicate_prediction_idempotency(temp_ledger: ShadowPredictionLedger):
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    vec = build_verified_prospective_feature_vector(
        session_date="2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = validator.validate(vec, current_time=eval_time)
    pred1 = runner.predict(vec, report, prev_record_hash=temp_ledger.get_tip_hash())

    status1, _ = temp_ledger.append_prediction(pred1)
    assert status1 == LedgerStatus.RECORDED

    # Attempt to append duplicate for same session
    status2, existing = temp_ledger.append_prediction(pred1)
    assert status2 == LedgerStatus.DUPLICATE_IGNORED
    assert existing["prediction_id"] == pred1.prediction_id
    assert len(temp_ledger.get_all_records()) == 1


def test_chain_verification_detects_tampering(temp_ledger: ShadowPredictionLedger):
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    # Add 2 predictions
    for s_date in ["2026-11-02", "2026-11-03"]:
        vec = build_verified_prospective_feature_vector(
            session_date=s_date,
            provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
        )
        s_dt = datetime.strptime(s_date, "%Y-%m-%d").date()
        eval_time = datetime.combine(s_dt, time(8, 52, 0), tzinfo=MARKET_TIMEZONE)
        report = validator.validate(vec, current_time=eval_time)
        pred = runner.predict(vec, report, prev_record_hash=temp_ledger.get_tip_hash())
        temp_ledger.append_prediction(pred)

    assert len(temp_ledger.get_all_records()) == 2
    is_valid, _ = temp_ledger.verify_integrity()
    assert is_valid is True

    # Tamper with record 0 on disk
    records = temp_ledger.get_all_records()
    records[0]["predicted_return"] = 0.9999
    with open(temp_ledger.ledger_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    # Integrity verification must catch tampering
    is_valid_after, issues = temp_ledger.verify_integrity()
    assert is_valid_after is False
    assert any("Record tamper detected" in issue for issue in issues)
