#!/usr/bin/env python3
"""CLI utility to verify cryptographic integrity of the Phase 14 shadow prediction ledger.

Usage:
    python scripts/verify_shadow_ledger.py
"""

import json
import sys

from nifty_ai.shadow.ledger import ShadowPredictionLedger
from nifty_ai.shadow.reconciliation import ShadowOutcomeReconciler


def main() -> int:
    print("================================================================================")
    print("NIFTY AI — PHASE 14 SHADOW LEDGER INTEGRITY AUDITOR")
    print("Governance: Cryptographic Hash Chaining Verification")
    print("================================================================================")

    ledger = ShadowPredictionLedger()
    records = ledger.get_all_records()
    print(f"Total Prediction Records: {len(records)}")

    is_valid, issues = ledger.verify_integrity()
    if is_valid:
        print("LEDGER INTEGRITY AUDIT: PASSED (Cryptographic chain intact)")
        print(f"Tip Hash: {ledger.get_tip_hash()}")
    else:
        print("LEDGER INTEGRITY AUDIT: FAILED", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    reconciler = ShadowOutcomeReconciler(prediction_ledger=ledger)
    outcomes = reconciler.get_all_outcomes()
    print(f"Total Reconciled Outcomes: {len(outcomes)}")

    metrics = reconciler.compute_forward_metrics(filter_prospective_only=True)
    print("\nForward Validation Scorecard (Prospective Live Only):")
    print(json.dumps(metrics, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
