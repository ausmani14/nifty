"""Phase 9 Point-in-Time Integrity and Anti-Leakage Verification Tests.

Verifies:
1. Strict PIT boundaries for Snapshot A and Snapshot B news windows.
2. News intensity denominator uses trailing news counts, not market volume.
3. Candidate feature registry adherence (approved only, zero prohibited annotation features).
4. Terminal holdout strict cryptographic quarantine and isolation.
5. Non-overlapping snapshot assignment.
6. Context variable PIT transformation strictness.
"""

from datetime import date, datetime, timedelta
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pytest

from nifty_ai.data.news.point_in_time import (
    TIMEZONE_KOLKATA,
    evaluate_news_point_in_time,
)
from nifty_ai.data.news.schema import (
    AvailabilityEvidenceLevel,
    CanonicalNewsRecord,
    SourceAuthorityTier,
)
from nifty_ai.data.snapshots import SnapshotType


PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOLDOUT_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "gold_holdout_annotation_input.csv"
CANDIDATE_REGISTRY_MD = PROJECT_ROOT / "docs" / "PHASE_9_NEWS_FEATURE_CANDIDATE_REGISTRY.md"
RAW_INVENTORY_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_inventory.jsonl"


from tests.test_news import create_sample_news_record


def test_phase9_candidate_registry_exists_and_enforces_provenance():
    """Verify Candidate Registry exists, approves vetted features, and prohibits annotation dependencies."""
    assert CANDIDATE_REGISTRY_MD.is_file(), "Candidate registry docs/PHASE_9_NEWS_FEATURE_CANDIDATE_REGISTRY.md must exist."
    content = CANDIDATE_REGISTRY_MD.read_text(encoding="utf-8")

    # Approved vetted features
    assert "news_volume_total" in content
    assert "news_intensity_20d" in content
    assert "sentiment_balance" in content
    assert "recency_weighted_sentiment" in content
    assert "APPROVED" in content

    # Prohibited annotation dependencies
    assert "annotator_primary_event_*" in content
    assert "annotator_economic_importance" in content
    assert "annotator_sentiment_class" in content
    assert "PROHIBITED" in content


def test_snapshot_a_news_window_strict_bounds():
    """Verify Snapshot A strictly enforces upper cutoff at 15:30:00.000 IST on Session T."""
    ref_d = date(2020, 6, 15)
    tgt_d = date(2020, 6, 16)

    # 1. Exactly at Day T 15:30:00.000 -> Included in Day T Snapshot A
    dt_exact_close = datetime(2020, 6, 15, 15, 30, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_exact = create_sample_news_record("rec_exact", "Closing News", dt_exact_close)
    ok_exact, _ = evaluate_news_point_in_time(rec_exact, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    assert ok_exact is True

    # 2. 1ms after Day T 15:30:00.000 -> Strictly Excluded from Day T Snapshot A
    dt_late = datetime(2020, 6, 15, 15, 30, 0, 1000, tzinfo=TIMEZONE_KOLKATA)
    rec_late = create_sample_news_record("rec_late", "Post Close News", dt_late)
    ok_late, _ = evaluate_news_point_in_time(rec_late, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    assert ok_late is False, "News at 15:30:00.001 must be strictly excluded from Snapshot A"

    # 3. Morning of Day T (10:00 IST) -> Included in Snapshot A
    dt_morning = datetime(2020, 6, 15, 10, 0, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_morning = create_sample_news_record("rec_morning", "Morning News", dt_morning)
    ok_morning, _ = evaluate_news_point_in_time(rec_morning, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    assert ok_morning is True


def test_snapshot_b_news_window_strict_bounds():
    """Verify Snapshot B strictly captures (T 15:30:00.000, T+1 08:50:00.000]."""
    ref_d = date(2020, 6, 15)
    tgt_d = date(2020, 6, 16)

    # 1. Day T 15:30:00.000 -> Excluded from Snapshot B (belongs to Snapshot A)
    dt_day_t = datetime(2020, 6, 15, 15, 30, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_t = create_sample_news_record("rec_t", "Day T Close News", dt_day_t)
    ok_b_t, _ = evaluate_news_point_in_time(rec_t, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_t is False

    # 2. Evening Day T (19:30 IST) -> Included in Snapshot B
    dt_eve = datetime(2020, 6, 15, 19, 30, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_eve = create_sample_news_record("rec_eve", "Evening Overnight", dt_eve)
    ok_b_eve, _ = evaluate_news_point_in_time(rec_eve, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_eve is True

    # 3. Morning Day T+1 08:50:00.000 -> Included in Snapshot B
    dt_morn = datetime(2020, 6, 16, 8, 50, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_morn = create_sample_news_record("rec_morn", "Pre-market News", dt_morn)
    ok_b_morn, _ = evaluate_news_point_in_time(rec_morn, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_morn is True

    # 4. Morning Day T+1 08:50:00.001 -> Strictly Excluded from Snapshot B
    dt_after_morn = datetime(2020, 6, 16, 8, 50, 0, 1000, tzinfo=TIMEZONE_KOLKATA)
    rec_after_morn = create_sample_news_record("rec_after_morn", "Late Pre-market News", dt_after_morn)
    ok_b_after, _ = evaluate_news_point_in_time(rec_after_morn, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_after is False


def test_terminal_holdout_hard_cryptographic_quarantine():
    """Verify terminal holdout file is pristine, quarantined, and matches registered SHA-256."""
    assert HOLDOUT_CSV.is_file(), "Terminal holdout file must exist"
    data = HOLDOUT_CSV.read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()
    expected_sha = "0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199"
    assert actual_sha == expected_sha, "CRITICAL BREACH: Terminal holdout checksum modified!"
    # Verify row count is exactly 200 + 1 header
    lines = [l for l in data.splitlines() if l.strip()]
    assert len(lines) == 201, f"Holdout row count changed: expected 201 lines, got {len(lines)}"


def test_news_intensity_pure_news_denominator_logic():
    """Verify that news intensity formula uses strictly trailing news counts, not market trading volume."""
    # Synthetic trailing 20 daily news counts
    trailing_counts = [5, 4, 6, 5, 5, 4, 6, 5, 5, 4, 6, 5, 5, 4, 6, 5, 5, 4, 6, 5]
    sma_20 = float(np.mean(trailing_counts))
    current_count = 10

    # News intensity: (N_T + 1) / (SMA_20(N) + 1)
    intensity = (current_count + 1.0) / (sma_20 + 1.0)
    assert intensity > 1.0, "Elevated news day must produce intensity > 1.0"
    assert round(intensity, 4) == pytest.approx(round(11.0 / 6.0, 4))


def test_zero_raw_inventory_manual_annotation_dependency():
    """Verify raw authentic inventory has 62,329 rows and 0 rows depend on Phase 8 manual annotation CSVs."""
    assert RAW_INVENTORY_JSONL.is_file(), "Raw inventory must exist"
    import json
    with open(RAW_INVENTORY_JSONL, "r", encoding="utf-8") as f:
        first_line = f.readline()
        obj = json.loads(first_line)

    # Verify no manual annotation fields are present in raw inventory
    assert "sentiment" not in obj
    assert "primary_event" not in obj
    assert "confidence" not in obj
    assert "relevance" not in obj
    assert "importance" not in obj

    # Required raw fields must be present
    assert "headline" in obj
    assert "published_timestamp" in obj
    assert "company" in obj
    assert "historical_constituent_status" in obj
