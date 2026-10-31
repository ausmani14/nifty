"""Context data layer for Indian and Global Market Variables.

This package provides point-in-time, timezone-aware market context
aligned strictly to NIFTY AI Snapshot A and Snapshot B schedules.
"""

from nifty_ai.data.context.schema import (
    ContextCategory,
    MissingPolicy,
    AvailabilityTimestampType,
    AvailabilitySpec,
    ContextObservation,
)
from nifty_ai.data.context.calendar import (
    CANONICAL_CONTEXT_SPECS,
    compute_availability_timestamp,
    TIMEZONE_KOLKATA,
    TIMEZONE_NEW_YORK,
    TIMEZONE_TOKYO,
    TIMEZONE_HONG_KONG,
    TIMEZONE_LONDON,
)
from nifty_ai.data.context.point_in_time import (
    is_context_observation_available,
    filter_context_for_snapshot,
)
from nifty_ai.data.context.normalizer import (
    ContextDataValidator,
)
from nifty_ai.data.context.missing_data import (
    align_and_fill_series,
)
from nifty_ai.data.context.features import (
    compute_series_return,
    compute_series_diff,
    compute_rolling_volatility,
)
from nifty_ai.data.context.datasets import (
    SnapshotContextTable,
    build_snapshot_context_dataset,
)

__all__ = [
    "ContextCategory",
    "MissingPolicy",
    "AvailabilityTimestampType",
    "AvailabilitySpec",
    "ContextObservation",
    "CANONICAL_CONTEXT_SPECS",
    "compute_availability_timestamp",
    "TIMEZONE_KOLKATA",
    "TIMEZONE_NEW_YORK",
    "TIMEZONE_TOKYO",
    "TIMEZONE_HONG_KONG",
    "TIMEZONE_LONDON",
    "is_context_observation_available",
    "filter_context_for_snapshot",
    "ContextDataValidator",
    "align_and_fill_series",
    "compute_series_return",
    "compute_series_diff",
    "compute_rolling_volatility",
    "SnapshotContextTable",
    "build_snapshot_context_dataset",
]
