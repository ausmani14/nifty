"""Tests for Phase 9 Step 2E Complete Terminal Acquisition Artifact.

Verifies:
1. File existence and cryptographic SHA-256 integrity (41,371 records).
2. Preservation and byte-for-byte immutability of:
   - raw_authentic_news_holdout_2022_2026.jsonl (old Step 2 artifact)
   - raw_authentic_news_inventory.jsonl (historical 2008-2021 inventory)
   - gold_holdout_annotation_input.csv (200-record gold holdout)
3. Schema compliance and required non-null fields.
4. Timestamps strictly bounded to [2022-01-01, 2026-09-04].
5. PIT constituent membership validity (no out-of-interval leakage).
6. Zero LICI contamination.
7. Zero non-member contamination.
8. Deduplication uniqueness.
"""

from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import pytest

from nifty_ai.data.news.constituents import CANONICAL_CONSTITUENTS

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NEW_HOLDOUT_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_terminal_2022_2026_step2e.jsonl"
OLD_HOLDOUT_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_holdout_2022_2026.jsonl"
EXISTING_RAW_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_inventory.jsonl"
HOLDOUT_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "gold_holdout_annotation_input.csv"
AUDIT_JSON = PROJECT_ROOT / "data" / "interim" / "news" / "acquisition_2022_2026_step2e_audit.json"

EXPECTED_NEW_SHA = "5d5daf5ed7c844e86d45dc6a893f03b1d4f523183e29200d94b592329136f6fd"
EXPECTED_OLD_STEP2_SHA = "f2cab28eaa624d5bc8d72169798655e7fb82b6b4e68102e93179eaffcadd335e"
EXPECTED_RAW_SHA = "6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3"
EXPECTED_HOLDOUT_CSV_SHA = "0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199"
EXPECTED_RECORD_COUNT = 41371

WINDOW_START = date(2022, 1, 1)
WINDOW_END = date(2026, 9, 4)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def test_immutable_pre_existing_artifacts():
    """Verify that Step 2E acquisition did NOT mutate any existing historical artifacts."""
    assert sha256_file(EXISTING_RAW_JSONL) == EXPECTED_RAW_SHA, "Historical raw inventory modified!"
    assert sha256_file(HOLDOUT_CSV) == EXPECTED_HOLDOUT_CSV_SHA, "Gold holdout benchmark modified!"
    assert sha256_file(OLD_HOLDOUT_JSONL) == EXPECTED_OLD_STEP2_SHA, "Old Step 2 holdout artifact modified!"


def test_step2e_artifact_exists_and_count():
    """Verify Step 2E JSONL exists, has correct SHA-256 and exact record count."""
    assert NEW_HOLDOUT_JSONL.exists(), f"Missing {NEW_HOLDOUT_JSONL}"
    assert AUDIT_JSON.exists(), f"Missing {AUDIT_JSON}"
    assert sha256_file(NEW_HOLDOUT_JSONL) == EXPECTED_NEW_SHA, "SHA-256 mismatch for Step 2E artifact"

    with open(NEW_HOLDOUT_JSONL, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == EXPECTED_RECORD_COUNT, f"Expected {EXPECTED_RECORD_COUNT}, got {len(lines)}"


def test_step2e_schema_pit_and_contamination():
    """Verify schema, PIT validity, zero LICI, and zero out-of-interval leakage."""
    constituent_map = {c.symbol: c for c in CANONICAL_CONSTITUENTS}
    seen_ids = set()

    with open(NEW_HOLDOUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
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

            # Contamination checks
            sym = rec["company_or_entities"][0]
            assert sym != "LICI", "CRITICAL CONTAMINATION: LICI record found in Step 2E artifact!"
            assert sym in constituent_map, f"Unknown symbol {sym} outside CANONICAL_CONSTITUENTS!"

            # Timestamp bounds
            pub_dt = datetime.fromisoformat(rec["published_timestamp"])
            p_date = pub_dt.date()
            assert WINDOW_START <= p_date <= WINDOW_END, (
                f"Record {art_id} date {p_date} out of window [{WINDOW_START}, {WINDOW_END}]"
            )

            # PIT membership tenure bounds
            c = constituent_map[sym]
            assert p_date >= c.valid_from, f"{sym} publication {p_date} before valid_from {c.valid_from}"
            if c.valid_to is not None:
                assert p_date <= c.valid_to, f"{sym} publication {p_date} after valid_to {c.valid_to}"
