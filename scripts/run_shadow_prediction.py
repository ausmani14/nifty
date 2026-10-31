#!/usr/bin/env python3
"""CLI utility to generate and record a pre-market Phase 14 shadow prediction at 08:50 IST.

Usage:
    python scripts/run_shadow_prediction.py --session-date 2026-11-02 --synthetic-test
    python scripts/run_shadow_prediction.py --preflight-only
"""

import argparse
from datetime import datetime, timezone
import json
import sys
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import LedgerStatus, ProvenanceType
from nifty_ai.shadow.inference import ShadowInferenceRunner
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector
from nifty_ai.shadow.input_validator import SnapshotBInputValidator
from nifty_ai.shadow.ledger import ShadowPredictionLedger

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 14 Shadow Prediction Runner")
    parser.add_argument("--session-date", type=str, default=None, help="Target session date (YYYY-MM-DD)")
    parser.add_argument("--input-file", type=str, default=None, help="Path to point-in-time validated feature vector JSON file")
    parser.add_argument("--preflight-only", action="store_true", help="Perform preflight checks without executing prediction")
    parser.add_argument("--synthetic-test", action="store_true", help="Execute with a synthetic test vector (marked synthetic)")
    args = parser.parse_args()

    print("================================================================================")
    print("NIFTY AI — PHASE 14 SHADOW PREDICTION RUNNER")
    print("Governance: RESEARCH_BASELINE_ONLY | Zero Live Trading Authorization")
    print("================================================================================")

    # Preflight model verification
    print("[1/4] Authenticating frozen model artifacts...")
    try:
        runner = ShadowInferenceRunner()
        print(f"      Model authenticated: {runner.metadata.get('model_name')}")
        print(f"      Frozen trees: {runner.metadata.get('hyperparameters', {}).get('n_estimators')}")
        print(f"      Feature count: {runner.metadata.get('feature_count')}")
    except Exception as e:
        print(f"FAILED: Model preflight check failed: {e}", file=sys.stderr)
        return 1

    if args.preflight_only:
        print("Preflight checks PASSED successfully.")
        return 0

    session_date = args.session_date
    if session_date is None:
        session_date = datetime.now(MARKET_TIMEZONE).strftime("%Y-%m-%d")

    print(f"[2/4] Assembling Snapshot B input vector for session {session_date}...")
    if args.input_file:
        from pathlib import Path
        from nifty_ai.shadow.input_capture import load_feature_vector_from_json
        in_path = Path(args.input_file)
        if not in_path.exists():
            print(f"ERROR: Input file not found: {in_path}", file=sys.stderr)
            return 1
        feature_vec = load_feature_vector_from_json(in_path)
        print(f"      Loaded input vector from: {in_path}")
    elif args.synthetic_test:
        feature_vec = build_synthetic_feature_vector(
            session_date=session_date,
            provenance_type=ProvenanceType.INVALID_OR_QUARANTINED,  # Synthetic test vectors quarantined from live metrics
            source_id="synthetic_cli_test",
        )
    else:
        print("ERROR: Live market data feed not connected for real-time capture.", file=sys.stderr)
        print("Provide an input vector via --input-file <path> or use --synthetic-test.", file=sys.stderr)
        return 1

    print("[3/4] Validating Point-in-Time input vector...")
    validator = SnapshotBInputValidator()
    report = validator.validate(feature_vec)

    if not report.is_eligible_for_inference:
        print(f"VALIDATION FAILED: {report.error_messages}", file=sys.stderr)
        return 1
    print("      Validation: PASSED")

    print("[4/4] Generating frozen model prediction and updating ledger...")
    ledger = ShadowPredictionLedger()
    tip_hash = ledger.get_tip_hash()

    prediction = runner.predict(feature_vec, report, prev_record_hash=tip_hash)
    status, rec = ledger.append_prediction(prediction)

    if status == LedgerStatus.DUPLICATE_IGNORED:
        print(f"STATUS: Prediction already recorded for session {session_date} (Idempotent ignore).")
    else:
        print(f"STATUS: Successfully recorded prediction {prediction.prediction_id}")
        print(f"        Predicted T0: {prediction.predicted_return:.6f} ({prediction.predicted_return_bps:+.2f} bps)")
        print(f"        Record Hash:  {prediction.record_hash}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
