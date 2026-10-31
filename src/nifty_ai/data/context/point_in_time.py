"""Strict point-in-time filtering and availability evaluation for market context.

Evaluates whether any market context observation was strictly finalized and available
prior to or at a prediction snapshot's cutoff time.
"""

from datetime import datetime
from typing import Callable, Iterable, List, Optional
from zoneinfo import ZoneInfo

from nifty_ai.data.context.schema import ContextObservation
from nifty_ai.data.snapshots import SnapshotCutoff, SnapshotType

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def is_context_observation_available(
    observation: ContextObservation,
    cutoff: SnapshotCutoff,
) -> bool:
    """Evaluate whether an observation is point-in-time usable for a given cutoff.

    CRITICAL RULE:
    usable(obs, cutoff) <=> obs.availability_timestamp <= cutoff.cutoff_timestamp
    """
    if observation.availability_timestamp.tzinfo is None:
        raise ValueError(f"Observation for {observation.variable_name} lacks timezone awareness.")

    avail_dt = observation.availability_timestamp.astimezone(MARKET_TIMEZONE)
    cutoff_dt = cutoff.cutoff_timestamp.astimezone(MARKET_TIMEZONE)

    return avail_dt <= cutoff_dt


def filter_context_for_snapshot(
    observations: Iterable[ContextObservation],
    cutoff: SnapshotCutoff,
) -> List[ContextObservation]:
    """Filter context observations strictly adhering to the snapshot cutoff."""
    return [
        obs for obs in observations
        if is_context_observation_available(obs, cutoff)
    ]


__all__ = [
    "is_context_observation_available",
    "filter_context_for_snapshot",
]
