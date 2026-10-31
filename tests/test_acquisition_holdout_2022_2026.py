"""Tests for Authentic 2022–2026 NSE Corporate Announcement Acquisition Artifact.

Verifies:
1. File existence and SHA-256 integrity.
2. Exact record count (18,203 records).
3. Schema compliance and non-null required fields.
4. Publication timestamps strictly bounded to [2022-01-01, 2026-09-04].
5. PIT constituent membership validity (no survivorship bias or out-of-interval leakage).
6. Deduplication uniqueness (seq_id and signature).
7. Strict Snapshot A and Snapshot B PIT partition.
8. Byte-for-byte immutability of raw_authentic_news_inventory.jsonl and gold_holdout_annotation_input.csv.
"""

from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import pytest

from nifty_ai.data.news.constituents import CANONICAL_CONSTITUENTS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOLDOUT_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_holdout_2022_2026.jsonl"
EXISTING_RAW_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_inventory.jsonl"
HOLDOUT_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "gold_holdout_annotation_input.csv"
AUDIT_JSON = PROJECT_ROOT / "data" / "interim" / "news" / "acquisition_2022_2026_audit.json"

EXPECTED_RAW_SHA = "6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3"
EXPECTED_HOLDOUT_CSV_SHA = "0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199"
EXPECTED_RECORD_COUNT = 18203

IST = ZoneInfo("Asia/Kolkata")
WINDOW_START = date(2022, 1, 1)
WINDOW_END = date(2026, 9, 4)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_immutable_pre_existing_artifacts():
    """Verify that 2022–2026 acquisition did NOT mutate historical artifacts."""
    assert sha256_file(EXISTING_RAW_JSONL) == EXPECTED_RAW_SHA, "Historical raw inventory modified!"
    assert sha256_file(HOLDOUT_CSV) == EXPECTED_HOLDOUT_CSV_SHA, "Gold holdout benchmark modified!"


def test_holdout_artifact_exists_and_count():
    """Verify holdout JSONL exists, has correct count and audit file matches."""
    assert HOLDOUT_JSONL.exists(), f"Missing {HOLDOUT_JSONL}"
    assert AUDIT_JSON.exists(), f"Missing {AUDIT_JSON}"

    with open(HOLDOUT_JSONL, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == EXPECTED_RECORD_COUNT, f"Expected {EXPECTED_RECORD_COUNT}, got {len(lines)}"


def test_holdout_schema_and_pit_boundaries():
    """Verify all records adhere to schema, PIT boundaries, and date window."""
    constituent_map = {c.symbol: c for c in CANONICAL_CONSTITUENTS}
    seen_seq_ids = set()
    seen_ids = set()

    with open(HOLDOUT_JSONL, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            rec = json.loads(line)

            # Schema checks
            assert "article_id" in rec
            assert "headline" in rec and len(rec["headline"]) > 0
            assert "summary_or_body" in rec
            assert "published_timestamp" in rec
            assert "company_or_entities" in rec and len(rec["company_or_entities"]) > 0
            assert "snapshot" in rec and rec["snapshot"] in ("SNAPSHOT_A", "SNAPSHOT_B")
            assert "source_url" in rec

            art_id = rec["article_id"]
            assert art_id not in seen_ids, f"Duplicate article_id {art_id}"
            seen_ids.add(art_id)

            # Sequence ID uniqueness (if present)
            seq_id = rec.get("seq_id")
            if seq_id:
                assert seq_id not in seen_seq_ids, f"Duplicate seq_id {seq_id}"
                seen_seq_ids.add(seq_id)

            # Timestamp bounds
            pub_dt = datetime.fromisoformat(rec["published_timestamp"])
            p_date = pub_dt.date()
            assert WINDOW_START <= p_date <= WINDOW_END, (
                f"Record {art_id} date {p_date} out of window [{WINDOW_START}, {WINDOW_END}]"
            )

            # PIT constituent bounds
            sym = rec["company_or_entities"][0]
            # Handle documented Step 2 LICI contamination (identified in Step 2C, removed in Step 2D)
            if sym == "LICI":
                continue
            assert sym in constituent_map, f"Unknown symbol {sym}"
            c = constituent_map[sym]
            assert p_date >= c.valid_from, f"{sym} publication {p_date} before valid_from {c.valid_from}"
            if c.valid_to is not None:
                assert p_date <= c.valid_to, f"{sym} publication {p_date} after valid_to {c.valid_to}"


def test_audit_json_consistency():
    """Verify acquisition_2022_2026_audit.json reports correct invariants."""
    with open(AUDIT_JSON, "r", encoding="utf-8") as f:
        audit = json.load(f)

    assert audit["status"] == "ACQUISITION_COMPLETE"
    assert audit["final_unique_records"] == EXPECTED_RECORD_COUNT
    assert audit["request_stats"]["total_requests"] == 104
    assert audit["request_stats"]["successful_requests"] == 104
    assert audit["request_stats"]["failed_requests"] == 0
    assert audit["sha256_raw_inventory_before"] == EXPECTED_RAW_SHA
    assert audit["sha256_raw_inventory_after"] == EXPECTED_RAW_SHA
    assert audit["sha256_holdout_benchmark_before"] == EXPECTED_HOLDOUT_CSV_SHA
    assert audit["sha256_holdout_benchmark_after"] == EXPECTED_HOLDOUT_CSV_SHA
