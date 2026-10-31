"""Snapshot and information cutoff framework for NIFTY AI.

Enforces zero look-ahead bias by guaranteeing that any data point feeding into
a model prediction was strictly finalized prior to that snapshot's cutoff time.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from typing import Callable, Iterable, List, Optional, TypeVar

try:
    from zoneinfo import ZoneInfo
    MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")
except Exception:
    MARKET_TIMEZONE = timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")

T = TypeVar("T")


class SnapshotType(str, Enum):
    """Supported prediction snapshot horizons."""
    SNAPSHOT_1540 = "SNAPSHOT_1540"  # Post-market close (Day T-1)
    SNAPSHOT_0850 = "SNAPSHOT_0850"  # Pre-market open (Day T)


@dataclass(frozen=True)
class SnapshotCutoff:
    """Information cutoff boundary specification for a prediction run."""
    snapshot_type: SnapshotType
    target_date: date
    cutoff_timestamp: datetime
    execution_timestamp: datetime
    reference_date: date

    def __post_init__(self) -> None:
        if self.cutoff_timestamp.tzinfo is None:
            raise ValueError("cutoff_timestamp must be timezone-aware.")
        if self.execution_timestamp.tzinfo is None:
            raise ValueError("execution_timestamp must be timezone-aware.")
        if self.cutoff_timestamp > self.execution_timestamp:
            raise ValueError("cutoff_timestamp cannot exceed execution_timestamp.")

    def is_valid_information(self, information_timestamp: datetime) -> bool:
        """Evaluate if an event or publication occurred prior to or at the cutoff."""
        if information_timestamp.tzinfo is None:
            raise ValueError("information_timestamp must be timezone-aware for comparison.")
        return information_timestamp <= self.cutoff_timestamp

    def filter_records(
        self,
        records: Iterable[T],
        timestamp_extractor: Callable[[T], datetime],
    ) -> List[T]:
        """Filter a collection of records strictly adhering to the information cutoff."""
        return [
            record for record in records
            if self.is_valid_information(timestamp_extractor(record))
        ]


def create_snapshot_cutoff(
    snapshot_type: SnapshotType,
    target_date: date,
    reference_date: Optional[date] = None,
) -> SnapshotCutoff:
    """Construct a validated SnapshotCutoff instance.

    Args:
        snapshot_type: SNAPSHOT_1540 or SNAPSHOT_0850.
        target_date: The trading day T for which predictions are being generated.
        reference_date: Prior trading day T-1. Required for SNAPSHOT_1540 if not same as target_date.
                        If omitted, defaults to target_date for SNAPSHOT_0850, or raises if ambiguous.
    """
    if snapshot_type == SnapshotType.SNAPSHOT_1540:
        if reference_date is None:
            # If reference_date not provided, assume target_date is prediction day T
            # and reference_date is day T-1.
            raise ValueError(
                "reference_date (Day T-1) must be explicitly provided for SNAPSHOT_1540."
            )
        cutoff_dt = datetime.combine(reference_date, time(15, 30, 0), tzinfo=MARKET_TIMEZONE)
        exec_dt = datetime.combine(reference_date, time(15, 40, 0), tzinfo=MARKET_TIMEZONE)
        return SnapshotCutoff(
            snapshot_type=snapshot_type,
            target_date=target_date,
            cutoff_timestamp=cutoff_dt,
            execution_timestamp=exec_dt,
            reference_date=reference_date,
        )

    elif snapshot_type == SnapshotType.SNAPSHOT_0850:
        ref_date = reference_date if reference_date is not None else target_date
        cutoff_dt = datetime.combine(target_date, time(8, 50, 0), tzinfo=MARKET_TIMEZONE)
        exec_dt = datetime.combine(target_date, time(8, 50, 0), tzinfo=MARKET_TIMEZONE)
        return SnapshotCutoff(
            snapshot_type=snapshot_type,
            target_date=target_date,
            cutoff_timestamp=cutoff_dt,
            execution_timestamp=exec_dt,
            reference_date=ref_date,
        )

    else:
        raise ValueError(f"Unsupported snapshot type: {snapshot_type}")


__all__ = [
    "MARKET_TIMEZONE",
    "SnapshotType",
    "SnapshotCutoff",
    "create_snapshot_cutoff",
]
