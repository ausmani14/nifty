"""Point-in-Time live data capture and exchange calendar adapter for NIFTY AI.

Implements fail-closed capture logic, strict 08:50:00 IST cutoff evaluation,
NSE trading calendar verification, and safe error classification.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    FeatureVector,
    ProvenanceType,
    SourceProvenance,
)
from nifty_ai.shadow.input_validator import (
    SNAPSHOT_B_CUTOFF_TIME,
    compute_feature_vector_hash,
)

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")

# Official NSE Equity Trading Holidays for 2026 (YYYY-MM-DD)
NSE_HOLIDAYS_2026: Set[str] = {
    "2026-01-26",  # Republic Day
    "2026-02-17",  # Mahashivratri
    "2026-03-03",  # Holi
    "2026-03-20",  # Id-Ul-Fitr
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-27",  # Bakri Id / Eid ul-Adha
    "2026-06-26",  # Muharram
    "2026-08-15",  # Independence Day (Saturday)
    "2026-10-02",  # Mahatma Gandhi Jayanti
    "2026-10-20",  # Dussehra
    "2026-11-09",  # Diwali Balipratipada (Note: Lakshmi Puja Muhurat is Sun 2026-11-08)
    "2026-11-24",  # Guru Nanak Jayanti
    "2026-12-25",  # Christmas
}


class CaptureStatus(str, Enum):
    SUCCESS = "SUCCESS"
    DATA_SOURCE_BLOCKED = "DATA_SOURCE_BLOCKED"
    INSUFFICIENT_ELIGIBLE_FEATURES = "INSUFFICIENT_ELIGIBLE_FEATURES"
    INVALID_POINT_IN_TIME_INPUT = "INVALID_POINT_IN_TIME_INPUT"
    HOLIDAY = "HOLIDAY"
    WEEKEND = "WEEKEND"
    MISSED_CUTOFF = "MISSED_CUTOFF"
    INPUT_FILE_LOADED = "INPUT_FILE_LOADED"


@dataclass(frozen=True)
class DataCaptureResult:
    status: CaptureStatus
    session_date: str
    feature_vector: Optional[FeatureVector] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = None


def is_nse_trading_day(session_date_str: str) -> Tuple[bool, Optional[str]]:
    """Determine whether a given date is an official NSE trading day."""
    dt = datetime.strptime(session_date_str, "%Y-%m-%d").date()
    # 0 = Monday, 6 = Sunday
    if dt.weekday() == 5:
        return False, "Saturday (Weekend)"
    if dt.weekday() == 6:
        return False, "Sunday (Weekend)"
    if session_date_str in NSE_HOLIDAYS_2026:
        return False, f"Official NSE Holiday ({session_date_str})"
    return True, None


def attempt_live_feature_capture(
    session_date: str,
    input_file_path: Optional[Path] = None,
    current_time: Optional[datetime] = None,
) -> DataCaptureResult:
    """Attempt point-in-time Snapshot B feature capture with strict calendar and cutoff gates."""
    now_ist = (current_time or datetime.now(timezone.utc)).astimezone(MARKET_TIMEZONE)

    # 1. Trading Calendar Check
    is_trading, cal_reason = is_nse_trading_day(session_date)
    if not is_trading:
        status = CaptureStatus.WEEKEND if "Weekend" in (cal_reason or "") else CaptureStatus.HOLIDAY
        return DataCaptureResult(
            status=status,
            session_date=session_date,
            feature_vector=None,
            reason=cal_reason,
            metadata={"calendar_check": cal_reason},
        )

    # 2. Timing Cutoff and Backdating Check (08:50:00 Asia/Kolkata)
    today_ist_str = now_ist.strftime("%Y-%m-%d")
    cutoff_time = datetime.combine(
        datetime.strptime(session_date, "%Y-%m-%d").date(),
        SNAPSHOT_B_CUTOFF_TIME,
        tzinfo=MARKET_TIMEZONE,
    )

    # Disallow backdating: predictions cannot be generated prospectively for past sessions
    if session_date < today_ist_str and not input_file_path:
        return DataCaptureResult(
            status=CaptureStatus.MISSED_CUTOFF,
            session_date=session_date,
            feature_vector=None,
            reason=f"Cannot generate prospective prediction for past session date {session_date}. Backdating is strictly prohibited.",
            metadata={"session_date": session_date, "today_ist": today_ist_str, "cutoff_time": cutoff_time.isoformat()},
        )

    # If the capture is attempted for today after 08:50 IST, it has missed the cutoff
    if session_date == today_ist_str and now_ist.time() > SNAPSHOT_B_CUTOFF_TIME and not input_file_path:
        return DataCaptureResult(
            status=CaptureStatus.MISSED_CUTOFF,
            session_date=session_date,
            feature_vector=None,
            reason=f"Current time {now_ist.strftime('%H:%M:%S IST')} is after 08:50:00 IST cutoff.",
            metadata={"current_time": now_ist.isoformat(), "cutoff_time": cutoff_time.isoformat()},
        )

    # 3. Input File Path provided (Manual / Point-in-Time file)
    if input_file_path and input_file_path.exists():
        try:
            from nifty_ai.shadow.input_capture import load_feature_vector_from_json
            vec = load_feature_vector_from_json(input_file_path)
            return DataCaptureResult(
                status=CaptureStatus.SUCCESS,
                session_date=session_date,
                feature_vector=vec,
                reason="Loaded verified point-in-time input vector from file.",
                metadata={"source_file": str(input_file_path)},
            )
        except Exception as e:
            return DataCaptureResult(
                status=CaptureStatus.DATA_SOURCE_BLOCKED,
                session_date=session_date,
                feature_vector=None,
                reason=f"Failed to parse input file: {e}",
                metadata={"input_file": str(input_file_path)},
            )

    # 4. In the absence of an authenticated live broker/feed feed connection:
    # Fail-closed with DATA_SOURCE_BLOCKED rather than fabricating data
    return DataCaptureResult(
        status=CaptureStatus.DATA_SOURCE_BLOCKED,
        session_date=session_date,
        feature_vector=None,
        reason=(
            "Live market-data feed is not connected or provider unavailable. "
            "Under zero-fabrication governance, automated vector synthesis without verified "
            "feed is blocked. Supply verified point-in-time input via --input-file."
        ),
        metadata={"session_date": session_date, "cutoff_time": cutoff_time.isoformat()},
    )
