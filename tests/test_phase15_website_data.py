"""Tests for Phase 15 Website Data Exporter and Static Contracts."""

from datetime import datetime
import json
from pathlib import Path
import pytest
from zoneinfo import ZoneInfo

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")

from nifty_ai.shadow.contracts import (
    CANONICAL_MODEL_SHA256,
    LedgerStatus,
    ProvenanceType,
)
from nifty_ai.shadow.inference import ShadowInferenceRunner
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector
from nifty_ai.shadow.input_validator import SnapshotBInputValidator
from nifty_ai.shadow.ledger import ShadowPredictionLedger
from nifty_ai.shadow.reconciliation import ShadowOutcomeReconciler
from nifty_ai.shadow.website_exporter import WebsiteDataExporter


@pytest.fixture
def isolated_exporter(tmp_path: Path):
    web_dir = tmp_path / "web_data"
    pred_path = tmp_path / "preds.jsonl"
    out_path = tmp_path / "outs.jsonl"

    pred_ledger = ShadowPredictionLedger(ledger_path=pred_path)
    reconciler = ShadowOutcomeReconciler(prediction_ledger=pred_ledger, outcomes_path=out_path)
    exporter = WebsiteDataExporter(output_dir=web_dir, prediction_ledger=pred_ledger, outcome_reconciler=reconciler)
    return exporter, pred_ledger, reconciler, web_dir


def test_empty_ledger_website_exports(isolated_exporter):
    exporter, pred_ledger, reconciler, web_dir = isolated_exporter
    paths = exporter.export_all()

    assert len(paths) == 6
    for name, p in paths.items():
        assert p.exists(), f"File {name} does not exist: {p}"

    # Verify latest_prediction.json when empty
    with open(paths["latest_prediction"], "r", encoding="utf-8") as f:
        lp = json.load(f)
    assert lp["has_prediction"] is False
    assert lp["prediction_status"] == "NO VALID PROSPECTIVE PREDICTION"
    assert lp["model_sha256"] == CANONICAL_MODEL_SHA256

    # Verify system_status.json
    with open(paths["system_status"], "r", encoding="utf-8") as f:
        ss = json.load(f)
    assert ss["model_integrity"]["is_intact"] is True
    assert ss["ledger_integrity"]["prediction_count"] == 0
    assert ss["ledger_integrity"]["outcome_count"] == 0

    # Verify model_info.json
    with open(paths["model_info"], "r", encoding="utf-8") as f:
        mi = json.load(f)
    assert mi["model_classification"] == "RESEARCH BASELINE ONLY"
    assert mi["live_trading_authorized"] is False
    assert mi["frozen_tree_count"] == 43
    assert mi["total_feature_count"] == 63


def test_populated_ledger_website_exports(isolated_exporter):
    exporter, pred_ledger, reconciler, web_dir = isolated_exporter
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    # 1. Add mock prediction
    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE,
    )
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    rep = validator.validate(vec, current_time=eval_time)
    pred = runner.predict(vec, rep, prev_record_hash=pred_ledger.get_tip_hash())
    pred_ledger.append_prediction(pred)

    # Export before outcome
    exporter.export_all()
    with open(web_dir / "latest_prediction.json", "r", encoding="utf-8") as f:
        lp1 = json.load(f)
    assert lp1["has_prediction"] is True
    assert lp1["prediction_status"] == "VALID"
    assert lp1["outcome_status"] == "RECONCILIATION PENDING"

    # 2. Add mock outcome
    reconciler.reconcile_session(
        session_date="2026-11-02",
        open_price=24000.0,
        close_price=24150.0,
        acquisition_time=vec.cutoff_time.replace(hour=16),
    )

    # Export after outcome
    exporter.export_all()
    with open(web_dir / "latest_prediction.json", "r", encoding="utf-8") as f:
        lp2 = json.load(f)
    assert lp2["has_prediction"] is True
    assert lp2["outcome_status"] == "RECONCILED"
    assert lp2["realized_outcome"]["realized_open"] == 24000.0
    assert lp2["realized_outcome"]["realized_close"] == 24150.0

    with open(web_dir / "outcome_history.json", "r", encoding="utf-8") as f:
        oh = json.load(f)
    assert oh["total_count"] == 1
