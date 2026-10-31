"""Tests for Phase 15 Cloud Operations, Model Protection, and Live Data Capture Gates."""

from datetime import datetime, time
from pathlib import Path
import pytest
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    CANONICAL_MODEL_SHA256,
)
from nifty_ai.shadow.live_data import (
    CaptureStatus,
    attempt_live_feature_capture,
    is_nse_trading_day,
)
from nifty_ai.shadow.model_protection import (
    ModelIntegrityError,
    assert_frozen_model_intact,
    audit_frozen_model_protection,
)

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def test_frozen_model_protection_audit_passes():
    report = audit_frozen_model_protection()
    assert report.is_intact is True
    assert report.model_sha256 == CANONICAL_MODEL_SHA256
    assert report.n_estimators == 43
    assert report.feature_count == 63
    assert report.error_code is None


def test_frozen_model_protection_detects_tampering(tmp_path: Path):
    corrupt_model = tmp_path / "corrupt_model.json"
    corrupt_model.write_text('{"corrupted": true}', encoding="utf-8")

    meta_path = Path("data/interim/phase13_steps2_4/models/snapshot_b_t0_primary_model.meta.json")

    report = audit_frozen_model_protection(model_path=corrupt_model, meta_path=meta_path)
    assert report.is_intact is False
    assert report.error_code == "MODEL_INTEGRITY_FAILURE"
    assert "SHA-256 mismatch" in (report.error_message or "")

    with pytest.raises(ModelIntegrityError):
        assert_frozen_model_intact(model_path=corrupt_model, meta_path=meta_path)


def test_exchange_calendar_trading_day_verification():
    # Saturday (2026-10-31)
    is_trade, reason = is_nse_trading_day("2026-10-31")
    assert is_trade is False
    assert "Saturday" in reason

    # Sunday (2026-11-01)
    is_trade, reason = is_nse_trading_day("2026-11-01")
    assert is_trade is False
    assert "Sunday" in reason

    # Monday (2026-11-02) -> Regular trading session
    is_trade, reason = is_nse_trading_day("2026-11-02")
    assert is_trade is True
    assert reason is None

    # Official NSE Holiday (Republic Day 2026-01-26)
    is_trade, reason = is_nse_trading_day("2026-01-26")
    assert is_trade is False
    assert "Official NSE Holiday" in reason


def test_live_capture_weekend_rejection():
    # Saturday
    res = attempt_live_feature_capture("2026-10-31")
    assert res.status == CaptureStatus.WEEKEND
    assert res.feature_vector is None


def test_live_capture_holiday_rejection():
    # Republic day
    res = attempt_live_feature_capture("2026-01-26")
    assert res.status == CaptureStatus.HOLIDAY
    assert res.feature_vector is None


def test_live_capture_premature_evaluation_rejection():
    # Simulate today before 08:50:00 IST cutoff (e.g. 08:40:00 IST)
    now_early = datetime(2026, 11, 2, 8, 40, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture("2026-11-02", current_time=now_early)
    assert res.status == CaptureStatus.PREMATURE_EVALUATION
    assert res.feature_vector is None
    assert "before 08:50:00 IST" in (res.reason or "")


def test_live_capture_missed_cutoff_rejection():
    # Simulate today at 09:20 IST (after 09:15:00 IST pre-market deadline)
    now_late = datetime(2026, 11, 2, 9, 20, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture("2026-11-02", current_time=now_late)
    assert res.status == CaptureStatus.MISSED_CUTOFF
    assert res.feature_vector is None
    assert "at or after 09:15:00 IST" in (res.reason or "")


def test_live_capture_fail_closed_without_feed():
    # When evaluated in valid window [08:50, 09:15) but no feed is connected:
    now_valid_window = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture("2026-11-02", current_time=now_valid_window)
    assert res.status == CaptureStatus.DATA_SOURCE_BLOCKED
    assert res.feature_vector is None
    assert "Under zero-fabrication governance" in (res.reason or "")
