#!/usr/bin/env python3
"""CLI utility to reconcile realized session outcomes (Open and Close) after market close.

Usage:
    python scripts/reconcile_shadow_outcomes.py --session-date 2026-11-02 --open 24200.0 --close 24150.0
"""

import argparse
from datetime import datetime, timezone
import json
import sys
from zoneinfo import ZoneInfo

from nifty_ai.shadow.reconciliation import ShadowOutcomeReconciler

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 14 Shadow Outcome Reconciler")
    parser.add_argument("--session-date", type=str, required=True, help="Session date (YYYY-MM-DD)")
    parser.add_argument("--open", type=float, required=True, help="Realized session open price")
    parser.add_argument("--close", type=float, required=True, help="Realized session close price")
    parser.add_argument("--source", type=str, default="NSE_OFFICIAL_CASH", help="Data source identity")
    args = parser.parse_args()

    print("================================================================================")
    print("NIFTY AI — PHASE 14 SHADOW OUTCOME RECONCILER")
    print("Governance: RESEARCH_BASELINE_ONLY | Post-Market Target Realization")
    print("================================================================================")

    reconciler = ShadowOutcomeReconciler()
    now_ist = datetime.now(MARKET_TIMEZONE)

    try:
        outcome = reconciler.reconcile_session(
            session_date=args.session_date,
            open_price=args.open,
            close_price=args.close,
            acquisition_time=now_ist,
            data_source=args.source,
        )
        print(f"STATUS: Successfully reconciled outcome for session {args.session_date}")
        print(f"        Realized T0:     {outcome.realized_t0:.6f} ({outcome.realized_t0_bps:+.2f} bps)")
        print(f"        Prediction Err:  {outcome.prediction_error:.6f} ({outcome.absolute_error_bps:.2f} bps MAE)")
        print(f"        Direction Match: {'YES' if outcome.directional_match else 'NO'}")
        print(f"        Outcome Hash:    {outcome.record_hash}")
        return 0
    except Exception as e:
        print(f"RECONCILIATION FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
