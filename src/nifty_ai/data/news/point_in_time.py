"""Point-in-Time News Eligibility Engine for Snapshot A and Snapshot B.

Enforces:
- Snapshot A information cutoff: strictly <= 15:30:00.000 IST on Day T
- Snapshot B information cutoff: strictly > 15:30:00.000 IST on Day T AND <= 08:50:00.000 IST on Day T+1
- Evidence Hierarchy audit: quarantines unverified or ambiguous items
- Zero look-ahead bias across midnight, weekends, and holidays
"""

from datetime import date, datetime, time, timedelta
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from nifty_ai.data.news.schema import (
    AvailabilityEvidenceLevel,
    CanonicalNewsRecord,
)
from nifty_ai.data.snapshots import SnapshotCutoff, SnapshotType

TIMEZONE_KOLKATA = ZoneInfo("Asia/Kolkata")
TIMEZONE_UTC = ZoneInfo("UTC")


def evaluate_news_point_in_time(
    record: CanonicalNewsRecord,
    snapshot_type: SnapshotType,
    reference_date: date,
    target_date: date,
) -> Tuple[bool, Optional[str]]:
    """Determine whether a news record is legitimately available for a prediction snapshot.

    Args:
        record: Canonical news item.
        snapshot_type: SNAPSHOT_1540 (Snapshot A) or SNAPSHOT_0850 (Snapshot B).
        reference_date: Preceding trading session date (Day T).
        target_date: Prediction session date (Day T+1).

    Returns:
        Tuple of (is_eligible, quarantine_or_rejection_reason).
    """
    # Rule 1: Quarantined records are strictly unusable
    if record.quarantine_flag:
        return False, f"QUARANTINED: {record.quarantine_reason}"

    # Rule 2: Evidence Level Audit
    # Level UNVERIFIED cannot prove point-in-time validity
    if record.availability_evidence_level == AvailabilityEvidenceLevel.LEVEL_UNVERIFIED:
        return False, "QUARANTINED: Unverified availability evidence level."

    # Rule 3: Level D Historical Web Audit
    if record.availability_evidence_level == AvailabilityEvidenceLevel.LEVEL_D:
        if record.published_timestamp.tzinfo is None or not record.timezone:
            return False, "QUARANTINED: Level D record missing explicit timezone."
        if not record.provenance or not record.provenance.provider:
            return False, "QUARANTINED: Level D record missing provenance metadata."
        if record.last_modified_timestamp is not None and record.last_modified_timestamp > record.availability_timestamp:
            return False, "QUARANTINED: Level D record has post-hoc revision evidence (last_modified > availability)."

    # Convert availability timestamp to Asia/Kolkata
    avail_dt = record.availability_timestamp.astimezone(TIMEZONE_KOLKATA)

    # Define snapshot window boundaries in Asia/Kolkata
    if snapshot_type == SnapshotType.SNAPSHOT_1540:
        # Snapshot A: Cutoff is strictly 15:30:00.000 IST on Session T (reference_date)
        cutoff_dt = datetime.combine(reference_date, time(15, 30, 0, 0), tzinfo=TIMEZONE_KOLKATA)

        # Usable only if availability <= 15:30:00 IST on Session T
        if avail_dt <= cutoff_dt:
            return True, None
        else:
            return False, f"EXCLUDED_SNAP_A: Availability {avail_dt.isoformat()} is after cutoff {cutoff_dt.isoformat()}"

    elif snapshot_type == SnapshotType.SNAPSHOT_0850:
        # Snapshot B: PURE OVERNIGHT WINDOW
        # Lower bound: > 15:30:00.000 IST on Session T (reference_date)
        # Upper bound: <= 08:50:00.000 IST on Session T+1 (target_date)
        start_window_dt = datetime.combine(reference_date, time(15, 30, 0, 0), tzinfo=TIMEZONE_KOLKATA)
        cutoff_dt = datetime.combine(target_date, time(8, 50, 0, 0), tzinfo=TIMEZONE_KOLKATA)

        if start_window_dt < avail_dt <= cutoff_dt:
            return True, None
        elif avail_dt <= start_window_dt:
            return False, f"EXCLUDED_SNAP_B: Item belongs to prior intraday window (avail {avail_dt.isoformat()} <= {start_window_dt.isoformat()})"
        else:
            return False, f"EXCLUDED_SNAP_B: Item arrived after Snapshot B cutoff ({avail_dt.isoformat()} > {cutoff_dt.isoformat()})"

    return False, f"UNKNOWN_SNAPSHOT_TYPE: {snapshot_type}"


def filter_news_for_snapshot(
    records: List[CanonicalNewsRecord],
    snapshot_type: SnapshotType,
    reference_date: date,
    target_date: date,
) -> Tuple[List[CanonicalNewsRecord], List[Tuple[CanonicalNewsRecord, str]]]:
    """Filter an inventory of news records for a specific snapshot cutoff.

    Returns:
        Tuple of (eligible_records, rejected_or_quarantined_records_with_reason).
    """
    eligible: List[CanonicalNewsRecord] = []
    rejected: List[Tuple[CanonicalNewsRecord, str]] = []

    for r in records:
        is_ok, reason = evaluate_news_point_in_time(
            record=r,
            snapshot_type=snapshot_type,
            reference_date=reference_date,
            target_date=target_date,
        )
        if is_ok:
            eligible.append(r)
        else:
            rejected.append((r, str(reason)))

    # Deterministic chronological sort by availability_timestamp, then news_id
    eligible.sort(key=lambda x: (x.availability_timestamp, x.news_id))
    return eligible, rejected


__all__ = [
    "TIMEZONE_KOLKATA",
    "TIMEZONE_UTC",
    "evaluate_news_point_in_time",
    "filter_news_for_snapshot",
]
