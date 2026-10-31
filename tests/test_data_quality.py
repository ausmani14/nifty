"""Offline unit tests for DataQualityAuditor and Phase 3 validation rules.

All tests utilize synthetic in-memory fixtures. No network access or live data is used.
"""

from datetime import date, datetime, time, timezone
import json
from pathlib import Path
import pytest

from nifty_ai.data import (
    MARKET_TIMEZONE,
    CalendarGapItem,
    DataFrequency,
    DataQualityAuditor,
    DataQualityReport,
    NormalizedMarketRecord,
    ProvenanceMetadata,
    ProviderTier,
    load_processed_market_data,
    save_quality_report,
)


def _make_record(
    d: date,
    o: float = 100.0,
    h: float = 105.0,
    l: float = 95.0,
    c: float = 102.0,
    v: float = 1000.0,
    tz=MARKET_TIMEZONE,
) -> NormalizedMarketRecord:
    prov = ProvenanceMetadata(
        provider="test_provider",
        source_identifier="TEST_SYM",
        retrieval_timestamp=datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc),
        timezone="Asia/Kolkata",
        data_frequency=DataFrequency.DAILY,
        tier=ProviderTier.FREE,
    )
    ts = datetime.combine(d, time(15, 30, 0), tzinfo=tz)
    return NormalizedMarketRecord(
        timestamp=ts,
        trading_date=d,
        symbol="NIFTY 50",
        open=o,
        high=h,
        low=l,
        close=c,
        volume=v,
        provenance=prov,
    )


def test_audit_structural_checks():
    """Verify detection of duplicate dates, duplicate timestamps, and out-of-order records."""
    auditor = DataQualityAuditor()

    # 1. Valid sequence
    recs_valid = [
        _make_record(date(2026, 9, 1)),
        _make_record(date(2026, 9, 2)),
        _make_record(date(2026, 9, 3)),
    ]
    report_valid = auditor.audit(recs_valid)
    assert report_valid.overall_status == "PASS"
    assert all(c.status == "PASS" for c in report_valid.checks)

    # 2. Duplicate dates
    recs_dup = [
        _make_record(date(2026, 9, 1)),
        _make_record(date(2026, 9, 1)),
    ]
    report_dup = auditor.audit(recs_dup)
    assert report_dup.overall_status == "FAIL"
    dup_check = next(c for c in report_dup.checks if c.name == "DUPLICATE_DATES")
    assert dup_check.status == "FAIL"

    # 3. Unordered records
    recs_unordered = [
        _make_record(date(2026, 9, 2)),
        _make_record(date(2026, 9, 1)),
    ]
    report_unordered = auditor.audit(recs_unordered)
    assert report_unordered.overall_status == "FAIL"
    order_check = next(c for c in report_dup.checks if c.name == "CHRONOLOGICAL_ORDER")
    assert order_check.status == "FAIL"


def test_audit_ohlc_checks():
    """Verify validation of non-positive prices, range violations, and flat bars."""
    auditor = DataQualityAuditor()

    # 1. Non-positive price
    rec_neg = _make_record(date(2026, 9, 1), o=-10.0, l=-15.0)
    report_neg = auditor.audit([rec_neg])
    assert report_neg.overall_status == "FAIL"
    neg_check = next(c for c in report_neg.checks if c.name == "POSITIVE_PRICES")
    assert neg_check.status == "FAIL"

    # 2. Inverted bounds (High < Low)
    rec_inv = _make_record(date(2026, 9, 1), h=90.0, l=100.0)
    report_inv = auditor.audit([rec_inv])
    assert report_inv.overall_status == "FAIL"
    bounds_check = next(c for c in report_inv.checks if c.name == "OHLC_BOUNDS")
    assert bounds_check.status == "FAIL"

    # 3. Flat bar (Open == High == Low == Close) triggers WARNING
    rec_flat = _make_record(date(2026, 9, 1), o=100.0, h=100.0, l=100.0, c=100.0)
    report_flat = auditor.audit([rec_flat])
    flat_check = next(c for c in report_flat.checks if c.name == "FLAT_BARS")
    assert flat_check.status == "WARNING"


def test_audit_calendar_gap_checks():
    """Verify identification of weekend sessions and extended multi-day gaps."""
    auditor = DataQualityAuditor(large_gap_threshold_days=4)

    # Saturday trading session
    sat_date = date(2025, 2, 1)  # Saturday
    rec_sat = _make_record(sat_date)
    report_sat = auditor.audit([rec_sat])
    wknd_check = next(c for c in report_sat.checks if c.name == "WEEKEND_SESSIONS")
    assert wknd_check.status == "WARNING"
    assert len(wknd_check.details["weekend_sessions"]) == 1

    # Large calendar gap > 4 days (e.g., 6 days between sessions)
    rec1 = _make_record(date(2026, 9, 1))
    rec2 = _make_record(date(2026, 9, 7))  # 6-day gap
    report_gap = auditor.audit([rec1, rec2])
    gap_check = next(c for c in report_gap.checks if c.name == "EXTENDED_CALENDAR_GAPS")
    assert gap_check.status == "WARNING"
    assert report_gap.calendar_gaps[0].calendar_days == 6
    assert report_gap.calendar_gaps[0].category == "EXTENDED_HOLIDAY"


def test_audit_extreme_return_detection():
    """Verify detection and statistical reporting of extreme price return anomalies."""
    auditor = DataQualityAuditor(extreme_return_threshold=0.05, severe_return_threshold=0.10)

    # Session 1: Close = 100. Session 2: Close = 115 (+15% return)
    rec1 = _make_record(date(2026, 9, 1), c=100.0)
    rec2 = _make_record(date(2026, 9, 2), c=115.0)
    report = auditor.audit([rec1, rec2])

    ret_check = next(c for c in report.checks if c.name == "EXTREME_RETURN_ANOMALIES")
    assert ret_check.status == "WARNING"
    assert report.return_statistics.max_return == pytest.approx(0.15)
    assert len(report.return_statistics.extreme_positive_returns) == 1
    assert report.return_statistics.extreme_positive_returns[0]["return_pct"] == 15.0


def test_audit_volume_fidelity_checks():
    """Verify zero-volume detection and reliability classification."""
    auditor = DataQualityAuditor()

    # Series with 50% zero volume
    rec1 = _make_record(date(2026, 9, 1), v=0.0)
    rec2 = _make_record(date(2026, 9, 2), v=1000.0)
    report = auditor.audit([rec1, rec2])

    vol_check = next(c for c in report.checks if c.name == "VOLUME_INTEGRITY")
    assert vol_check.status == "WARNING"
    assert report.volume_audit.zero_volume_count == 1
    assert report.volume_audit.zero_volume_pct == 50.0
    assert report.volume_audit.reliability_assessment == "UNRELIABLE"


def test_quality_report_json_serialization(tmp_path: Path):
    """Verify deterministic JSON serialization and presence of required audit fields."""
    auditor = DataQualityAuditor()
    recs = [
        _make_record(date(2026, 9, 1), c=100.0),
        _make_record(date(2026, 9, 2), c=102.0),
    ]
    report = auditor.audit(recs, dataset_sha256="test_sha_12345")

    target_json = tmp_path / "quality_report.json"
    saved_path = save_quality_report(report, target_json)

    assert saved_path.is_file()
    with open(saved_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["dataset_sha256"] == "test_sha_12345"
    assert data["row_count"] == 2
    assert "checks" in data
    assert "return_statistics" in data
    assert "volume_audit" in data
    assert "calendar_gaps" in data
    assert "findings_summary" in data
