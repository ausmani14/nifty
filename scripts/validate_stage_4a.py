"""Stage 4A Validation Script.

Verifies:
1. Exactly 62,329 authentic source records processed.
2. PIT assignment matches authoritative counts: Snapshot A = 25,523, Snapshot B = 36,806, Unassigned = 0.
3. Daily feature CSVs: snapshot_a_news_daily.csv and snapshot_b_news_daily.csv each have exactly 4,653 rows.
4. No duplicate (trading_date, snapshot_type) keys.
5. Zero NaN or inf values across all feature columns.
6. Event taxonomy strictly conforms to Phase 8 canonical taxonomy (17 substantive + OTHER).
7. Terminal holdout SHA-256 is untouched and quarantined.
8. Daily news aggregates are authentic (not old 1-2 count synthetic fixture).
"""

import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_inventory.jsonl"
CANONICAL_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "canonical_news_records.jsonl"
SNAP_A_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "snapshot_a_news_daily.csv"
SNAP_B_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "snapshot_b_news_daily.csv"
HOLDOUT_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "gold_holdout_annotation_input.csv"
SUMMARY_JSON = PROJECT_ROOT / "data" / "interim" / "news" / "stage_4a_summary.json"

EXPECTED_RAW_SHA = "6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3"
EXPECTED_HOLDOUT_SHA = "0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199"

CANONICAL_TAXONOMY = {
    "EARNINGS_RESULTS", "DIVIDEND", "BONUS_SPLIT", "RIGHTS_ISSUE", "BUYBACK",
    "M_AND_A", "CAPEX_BUSINESS_UPDATE", "FINANCIAL_IRREGULARITY", "SHAREHOLDING_CHANGE",
    "OPERATIONAL_EVENT", "STRATEGIC_PARTNERSHIP", "CREDIT_RATING_DEBT", "FUNDRAISING",
    "REGULATORY_LEGAL", "CORPORATE_ACTION", "MANAGEMENT_CHANGE", "ORDER_CONTRACT", "OTHER"
}

NUMERIC_COLS = [
    "news_volume_total", "news_volume_high_importance", "high_relevance_count",
    "max_importance_score", "earnings_event_count", "macro_event_count",
    "monetary_event_count", "mean_sentiment_polarity", "sentiment_dispersion",
    "importance_weighted_sentiment", "novelty_weighted_sentiment"
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main():
    print("=== Stage 4A Forensic Validation ===")

    # 1. Source Hash & Quarantine Verification
    assert RAW_JSONL.exists(), "Raw inventory missing!"
    raw_sha = sha256_file(RAW_JSONL)
    assert raw_sha == EXPECTED_RAW_SHA, f"Raw SHA mismatch: {raw_sha}"
    print(f"1. Raw Authentic Inventory SHA-256: {raw_sha} (MATCH)")

    assert HOLDOUT_CSV.exists(), "Holdout missing!"
    holdout_sha = sha256_file(HOLDOUT_CSV)
    assert holdout_sha == EXPECTED_HOLDOUT_SHA, f"Holdout SHA mismatch: {holdout_sha}"
    print(f"2. Quarantined Terminal Holdout SHA-256: {holdout_sha} (MATCH)")

    # 2. Canonical JSONL Validation
    assert CANONICAL_JSONL.exists(), "Canonical JSONL missing!"
    total_canon = 0
    with open(CANONICAL_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            total_canon += 1
            assert r["primary_event"] in CANONICAL_TAXONOMY, f"Invalid event: {r['primary_event']}"
            assert r["sentiment_class"] in {"POSITIVE", "NEGATIVE", "NEUTRAL"}
            assert -1.0 <= r["sentiment_polarity"] <= 1.0
            assert 0.0 <= r["importance_score"] <= 1.0
            assert 0.0 <= r["novelty_score"] <= 1.0
    assert total_canon == 62329, f"Expected 62329 canonical records, got {total_canon}"
    print(f"3. Canonical JSONL Records: {total_canon} records with valid 18-taxonomy and schema bounds (MATCH)")

    # 3. Snapshot A and B CSV Validation
    df_a = pd.read_csv(SNAP_A_CSV)
    df_b = pd.read_csv(SNAP_B_CSV)

    assert len(df_a) == 4653, f"Expected 4653 rows in A, got {len(df_a)}"
    assert len(df_b) == 4653, f"Expected 4653 rows in B, got {len(df_b)}"
    print(f"4. Daily CSV Rows: Snapshot A = {len(df_a)}, Snapshot B = {len(df_b)} (MATCH)")

    # Unique dates
    assert df_a["trading_date"].nunique() == 4653, "Duplicate trading dates in Snapshot A"
    assert df_b["trading_date"].nunique() == 4653, "Duplicate trading dates in Snapshot B"
    print("5. Trading Date Keys: Strictly unique across both snapshots (MATCH)")

    # Zero NaNs or infs
    for col in NUMERIC_COLS:
        assert not df_a[col].isna().any(), f"NaN in df_a[{col}]"
        assert not np.isinf(df_a[col]).any(), f"Inf in df_a[{col}]"
        assert not df_b[col].isna().any(), f"NaN in df_b[{col}]"
        assert not np.isinf(df_b[col]).any(), f"Inf in df_b[{col}]"
        assert (df_a[col] >= 0).all() or "sentiment" in col, f"Negative values in non-sentiment col {col}"
        assert (df_b[col] >= 0).all() or "sentiment" in col, f"Negative values in non-sentiment col {col}"
    print("6. Feature Integrity: Zero NaNs, zero Infs, non-negative event/volume counts (MATCH)")

    # Summary verification
    with open(SUMMARY_JSON, "r", encoding="utf-8") as f:
        summary = json.load(f)

    assert summary["count_snapshot_a"] == 25523, f"Expected 25523, got {summary['count_snapshot_a']}"
    assert summary["count_snapshot_b"] == 36806, f"Expected 36806, got {summary['count_snapshot_b']}"
    assert summary["unassigned_count"] == 0, f"Expected 0, got {summary['unassigned_count']}"
    print(f"7. Authoritative PIT Mapping: A = {summary['count_snapshot_a']}, B = {summary['count_snapshot_b']}, Unassigned = 0 (MATCH)")

    # Check that total underlying news volume in daily aggregates matches total records
    total_vol_a = int(df_a["news_volume_total"].sum())
    total_vol_b = int(df_b["news_volume_total"].sum())
    assert total_vol_a == 25523, f"Expected volume A = 25523, got {total_vol_a}"
    assert total_vol_b == 36806, f"Expected volume B = 36806, got {total_vol_b}"
    print(f"8. Aggregate Volume Reconciliation: Sum(A) = {total_vol_a}, Sum(B) = {total_vol_b}, Total = {total_vol_a + total_vol_b} (100% RECONCILED)")

    # Synthetic fixture removal check:
    max_vol_a = df_a["news_volume_total"].max()
    max_vol_b = df_b["news_volume_total"].max()
    mean_vol_a = df_a["news_volume_total"].mean()
    assert max_vol_a > 10 and max_vol_b > 10, "Looks like synthetic fixtures!"
    print(f"9. Synthetic Fixture Removal: Max A = {max_vol_a}, Max B = {max_vol_b}, Mean A = {mean_vol_a:.2f} (AUTHENTIC VARIANCE CONFIRMED)")

    print("\nALL STAGE 4A FORENSIC CHECKS PASSED!")


if __name__ == "__main__":
    main()
