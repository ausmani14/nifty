#!/usr/bin/env python3
"""Unified Daily Operations CLI Runner for NIFTY AI Cloud & Local Execution.

Handles allowlisted daily workflows:
- snapshot_b: 08:50 IST Pre-market Snapshot B feature capture & inference
- reconcile_outcomes: Post-market (15:30+ IST) realized return reconciliation
- health_check: Preflight model integrity and cryptographic ledger audit
- dry_run: Synthetic isolated end-to-end pipeline test without ledger mutation

Usage:
    python scripts/run_daily_ops.py --operation snapshot_b
    python scripts/run_daily_ops.py --operation reconcile_outcomes
    python scripts/run_daily_ops.py --operation health_check
    python scripts/run_daily_ops.py --operation dry_run
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

from nifty_ai.config import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from nifty_ai.shadow.contracts import LedgerStatus, ProvenanceType
from nifty_ai.shadow.inference import ShadowInferenceRunner
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector
from nifty_ai.shadow.input_validator import SnapshotBInputValidator
from nifty_ai.shadow.ledger import ShadowPredictionLedger
from nifty_ai.shadow.live_data import CaptureStatus, attempt_live_feature_capture, is_nse_trading_day
from nifty_ai.shadow.model_protection import assert_frozen_model_intact
from nifty_ai.shadow.reconciliation import ShadowOutcomeReconciler
from nifty_ai.shadow.website_exporter import WebsiteDataExporter

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")
ALLOWED_OPERATIONS = {"snapshot_b", "reconcile_outcomes", "health_check", "dry_run"}


def run_snapshot_b(session_date: str, input_file: str = None) -> int:
    today_ist_str = datetime.now(timezone.utc).astimezone(MARKET_TIMEZONE).strftime("%Y-%m-%d")
    if not session_date:
        session_date = today_ist_str

    print(f"[Snapshot B] Executing morning prediction workflow for session {session_date}...")
    exporter = WebsiteDataExporter()

    # Reject past sessions
    if session_date < today_ist_str:
        err = f"Cannot generate prospective prediction for past session date {session_date}. Backdating is strictly prohibited."
        print(f"      [FATAL] Prospective Rejected: {err}", file=sys.stderr)
        exporter.export_all(current_system_state="REJECTED_PAST_SESSION", latest_error=err)
        return 1

    # Reject future sessions
    if session_date > today_ist_str:
        err = f"Cannot generate prospective prediction for future session date {session_date} in advance."
        print(f"      [FATAL] Prospective Rejected: {err}", file=sys.stderr)
        exporter.export_all(current_system_state="REJECTED_FUTURE_SESSION", latest_error=err)
        return 1

    # 1. Model Integrity Guard
    try:
        report = assert_frozen_model_intact()
        print(f"      [OK] Frozen Model Verified: N*={report.n_estimators}, SHA-256={report.model_sha256[:16]}...")
    except Exception as e:
        print(f"      [FATAL] Model Protection Check Failed: {e}", file=sys.stderr)
        exporter.export_all(current_system_state="MODEL_INTEGRITY_FAILURE", latest_error=str(e))
        return 1

    # 2. Attempt Feature Capture
    in_path = Path(input_file) if input_file else None
    capture = attempt_live_feature_capture(session_date=session_date, input_file_path=in_path)
    print(f"      [Status] Data Capture Status: {capture.status.value}")

    if capture.status in (CaptureStatus.HOLIDAY, CaptureStatus.WEEKEND):
        print(f"      [Notice] Non-trading day ({capture.reason}). Skipping prediction generation.")
        exporter.export_all(current_system_state="HOLIDAY", latest_error=capture.reason)
        return 0

    if capture.status == CaptureStatus.MISSED_CUTOFF:
        print(f"      [FAIL] Missed 08:50:00 IST Cutoff ({capture.reason}).", file=sys.stderr)
        exporter.export_all(current_system_state="MISSED CUTOFF", latest_error=capture.reason)
        return 1

    if capture.status != CaptureStatus.SUCCESS or capture.feature_vector is None:
        print(f"      [CAPTURE STATUS: DATA_SOURCE_BLOCKED] {capture.reason}", file=sys.stderr)
        exporter.export_all(current_system_state="DATA_SOURCE_BLOCKED", latest_error=capture.reason)
        return 0  # Clean zero exit so workflow exports blocked status to website without claiming prediction success

    # 3. Validate Point-in-Time Vector
    validator = SnapshotBInputValidator()
    val_report = validator.validate(capture.feature_vector)
    if not val_report.is_eligible_for_inference:
        print(f"      [FAIL] Input Validation Failed: {val_report.error_messages}", file=sys.stderr)
        exporter.export_all(current_system_state="VALIDATION_FAILED", latest_error=str(val_report.error_messages))
        return 1

    # 4. Generate Inference & Record in Ledger
    ledger = ShadowPredictionLedger()
    runner = ShadowInferenceRunner()
    tip_hash = ledger.get_tip_hash()

    prediction = runner.predict(capture.feature_vector, val_report, prev_record_hash=tip_hash)
    status, rec = ledger.append_prediction(prediction)

    if status == LedgerStatus.DUPLICATE_IGNORED:
        print(f"      [IDEMPOTENT] Duplicate prediction for {session_date} safely ignored.")
    else:
        print(f"      [RECORDED] Prediction ID: {prediction.prediction_id}")
        print(f"                 Predicted T0: {prediction.predicted_return:.6f} ({prediction.predicted_return_bps:+.2f} bps)")
        print(f"                 Record Hash:  {prediction.record_hash}")

    # 5. Export Updated Website Data
    exporter.export_all(current_system_state="PREDICTION_RECORDED")
    return 0


def run_reconcile_outcomes(session_date: str, open_price: float = None, close_price: float = None, source: str = "NSE_OFFICIAL_CASH") -> int:
    print(f"[Reconciliation] Executing post-market outcome reconciliation for session {session_date}...")
    exporter = WebsiteDataExporter()

    # Model Integrity Guard
    assert_frozen_model_intact()

    reconciler = ShadowOutcomeReconciler()
    now_ist = datetime.now(MARKET_TIMEZONE)

    if open_price is None or close_price is None:
        print("      [NOTICE] Live automated daily settlement prices not supplied.")
        print("               Outcome marked RECONCILIATION PENDING until finalized prices are ingested.")
        exporter.export_all(current_system_state="RECONCILIATION PENDING", latest_error="Awaiting finalized cash Open and Close")
        return 0

    try:
        outcome = reconciler.reconcile_session(
            session_date=session_date,
            open_price=open_price,
            close_price=close_price,
            acquisition_time=now_ist,
            data_source=source,
        )
        print(f"      [RECONCILED] Outcome ID:      {outcome.outcome_id}")
        print(f"                   Realized T0:     {outcome.realized_t0:.6f} ({outcome.realized_t0_bps:+.2f} bps)")
        print(f"                   Prediction Err:  {outcome.prediction_error:.6f} ({outcome.absolute_error_bps:.2f} bps MAE)")
        print(f"                   Direction Match: {'YES' if outcome.directional_match else 'NO'}")
        exporter.export_all(current_system_state="RECONCILED")
        return 0
    except Exception as e:
        print(f"      [FAIL] Reconciliation failed: {e}", file=sys.stderr)
        exporter.export_all(current_system_state="RECONCILIATION_FAILED", latest_error=str(e))
        return 1


def run_health_check() -> int:
    print("[Health Check] Executing full preflight audit...")
    # 1. Model Check
    report = assert_frozen_model_intact()
    print(f"      [OK] Model Intact: {report.model_sha256[:16]}... (N*=43)")

    # 2. Ledger Check
    ledger = ShadowPredictionLedger()
    is_valid, issues = ledger.verify_integrity()
    if is_valid:
        print(f"      [OK] Ledger Cryptographic Chain Intact (Records: {len(ledger.get_all_records())}, Tip: {ledger.get_tip_hash()[:16]}...)")
    else:
        print(f"      [FAIL] Ledger Integrity Issues: {issues}", file=sys.stderr)
        return 1

    # 3. Website Exports
    exporter = WebsiteDataExporter()
    exporter.export_all(current_system_state="SYSTEM_HEALTHY")
    print("      [OK] Website Data Exports Up to Date")
    return 0


def run_dry_run() -> int:
    print("[Dry Run] Running isolated end-to-end simulation (temporary workspace)...")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        pred_p = tmp_path / "temp_preds.jsonl"
        out_p = tmp_path / "temp_outs.jsonl"
        web_p = tmp_path / "web_data"

        tmp_ledger = ShadowPredictionLedger(ledger_path=pred_p)
        tmp_reconciler = ShadowOutcomeReconciler(prediction_ledger=tmp_ledger, outcomes_path=out_p)
        tmp_exporter = WebsiteDataExporter(output_dir=web_p, prediction_ledger=tmp_ledger, outcome_reconciler=tmp_reconciler)

        # 1. Verify frozen model
        assert_frozen_model_intact()

        # 2. Build attested vector for isolated simulation
        test_date = "2026-11-02"
        simulated_eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
        obs_t = datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE)
        avail_t = datetime(2026, 11, 2, 8, 48, 0, tzinfo=MARKET_TIMEZONE)
        cutoff_t = datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE)

        from nifty_ai.shadow.contracts import AuthorizedOperatorKey
        from nifty_ai.shadow.crypto import (
            OperatorKeyRegistry,
            RawPayloadStore,
            generate_operator_keypair,
            create_operator_attestation,
        )
        from tests.fixtures.synthetic_inputs import build_test_prospective_feature_vector
        priv_key, pub_key = generate_operator_keypair()
        auth_key = AuthorizedOperatorKey(
            operator_id="operator_dry_run",
            key_id="ed25519_dry_run_01",
            public_key_hex=pub_key,
            valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            valid_until=datetime(2027, 1, 1, tzinfo=timezone.utc),
            is_revoked=False,
        )
        # Isolate ephemeral dry-run key in an explicit instance; never mutate default registry
        dry_run_registry = OperatorKeyRegistry([auth_key])

        dry_run_store = RawPayloadStore(base_dir=tmp_path / "raw_captures")
        vec = build_test_prospective_feature_vector(
            session_date=test_date,
            provenance_type=ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE,
            source_id="operator_verified_feed",
            payload_store=dry_run_store,
            operator_key_registry=dry_run_registry,
        )
        att = create_operator_attestation(
            feature_vector=vec,
            operator_id="operator_dry_run",
            key_id="ed25519_dry_run_01",
            private_key_hex=priv_key,
            signed_timestamp=datetime(2026, 11, 2, 8, 49, 0, tzinfo=MARKET_TIMEZONE),
        )
        from dataclasses import replace
        vec = replace(vec, provenance=replace(vec.provenance, attestation=att))

        validator = SnapshotBInputValidator(payload_store=dry_run_store)
        rep = validator.validate(
            vec,
            current_time=simulated_eval_time,
            operator_key_registry=dry_run_registry,
            payload_store=dry_run_store,
        )

        # 3. Predict & Append to temp ledger
        runner = ShadowInferenceRunner(payload_store=dry_run_store)
        pred = runner.predict(
            vec,
            rep,
            prev_record_hash=tmp_ledger.get_tip_hash(),
            operator_key_registry=dry_run_registry,
            payload_store=dry_run_store,
        )
        st, _ = tmp_ledger.append_prediction(pred)
        assert st == LedgerStatus.RECORDED

        # 4. Reconcile in temp reconciler
        out = tmp_reconciler.reconcile_session(
            session_date=test_date,
            open_price=24000.0,
            close_price=24120.0,
            acquisition_time=datetime(2026, 11, 2, 16, 0, 0, tzinfo=MARKET_TIMEZONE),
        )
        assert out.status == "RECONCILED"

        # 5. Export temp web data
        tmp_exporter.export_all()
        assert (web_p / "latest_prediction.json").exists()

        # 6. Verify real ledger was NOT touched
        real_ledger = ShadowPredictionLedger()
        assert len(real_ledger.get_all_records()) == 0

    print("      [OK] Dry Run Succeeded! Real ledger remained completely untouched (0 records).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="NIFTY AI Daily Operations Runner")
    parser.add_argument("--operation", type=str, required=True, choices=list(ALLOWED_OPERATIONS), help="Operation to execute")
    parser.add_argument("--session-date", type=str, default=None, help="Target session date (YYYY-MM-DD)")
    parser.add_argument("--input-file", type=str, default=None, help="Optional point-in-time input vector JSON")
    parser.add_argument("--open", type=float, default=None, help="Realized cash open price for reconciliation")
    parser.add_argument("--close", type=float, default=None, help="Realized cash close price for reconciliation")
    parser.add_argument("--source", type=str, default="NSE_OFFICIAL_CASH", help="Reconciliation data source")
    args = parser.parse_args()

    session_date = args.session_date or datetime.now(MARKET_TIMEZONE).strftime("%Y-%m-%d")

    if args.operation == "snapshot_b":
        return run_snapshot_b(session_date=session_date, input_file=args.input_file)
    elif args.operation == "reconcile_outcomes":
        return run_reconcile_outcomes(session_date=session_date, open_price=args.open, close_price=args.close, source=args.source)
    elif args.operation == "health_check":
        return run_health_check()
    elif args.operation == "dry_run":
        return run_dry_run()
    else:
        print(f"Unknown operation: {args.operation}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
