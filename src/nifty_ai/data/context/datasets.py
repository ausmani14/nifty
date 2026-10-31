"""Snapshot-specific context dataset generator and alignment engine.

Constructs:
- Snapshot A context dataset (Information cutoff: 15:30 IST on Day T, predicts T+1)
- Snapshot B context dataset (Information cutoff: 08:50 IST on Day T+1, predicts T+1)
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from nifty_ai.data.context.calendar import (
    CANONICAL_CONTEXT_SPECS,
    TIMEZONE_KOLKATA,
)
from nifty_ai.data.context.missing_data import align_and_fill_series
from nifty_ai.data.context.point_in_time import is_context_observation_available
from nifty_ai.data.context.schema import ContextObservation
from nifty_ai.data.snapshots import SnapshotCutoff, SnapshotType, create_snapshot_cutoff


@dataclass
class SnapshotContextTable:
    """Consolidated DataFrame and provenance metadata for a snapshot horizon."""
    snapshot_type: SnapshotType
    df: pd.DataFrame
    variable_names: List[str]
    metadata: Dict[str, Any]


def build_snapshot_context_dataset(
    target_dates: List[date],
    reference_dates: List[date],
    snapshot_type: SnapshotType,
    context_series_map: Dict[str, List[ContextObservation]],
) -> SnapshotContextTable:
    """Construct a point-in-time snapshot context table aligned to NIFTY trading dates.

    Args:
        target_dates: Prediction session dates (Session T+1).
        reference_dates: Preceding session dates (Session T).
        snapshot_type: SNAPSHOT_1540 (Snapshot A) or SNAPSHOT_0850 (Snapshot B).
        context_series_map: Map of variable_name to chronologically ordered ContextObservation lists.

    Returns:
        SnapshotContextTable with exact anti-leakage alignment.
    """
    rows: List[Dict[str, Any]] = []

    # Pre-index observations by variable_name and observation_date for speed
    obs_index: Dict[str, Dict[date, ContextObservation]] = {}
    for var_name, obs_list in context_series_map.items():
        obs_index[var_name] = {obs.observation_date: obs for obs in obs_list}

    # Extract all sorted dates in each series
    series_dates: Dict[str, List[date]] = {
        var: sorted(obs_index[var].keys()) for var in context_series_map
    }

    for ref_date, tgt_date in zip(reference_dates, target_dates):
        cutoff = create_snapshot_cutoff(
            snapshot_type=snapshot_type,
            target_date=tgt_date,
            reference_date=ref_date,
        )

        row_dict: Dict[str, Any] = {
            "trading_date": ref_date.isoformat(),
            "target_date": tgt_date.isoformat(),
            "cutoff_timestamp": cutoff.cutoff_timestamp.isoformat(),
            "snapshot_type": snapshot_type.value,
        }

        for var_name, spec in CANONICAL_CONTEXT_SPECS.items():
            if var_name not in obs_index:
                row_dict[f"{var_name.lower()}_close"] = np.nan
                row_dict[f"{var_name.lower()}_obs_date"] = None
                continue

            available_obs_dict = obs_index[var_name]
            all_dates = series_dates[var_name]

            # Candidate dates <= ref_date for Day T cutoff, or <= tgt_date for morning cutoff
            max_candidate_date = ref_date if snapshot_type == SnapshotType.SNAPSHOT_1540 else tgt_date
            candidates = [d for d in all_dates if d <= max_candidate_date]

            # Find latest candidate that satisfies availability_timestamp <= cutoff.cutoff_timestamp
            selected_obs: Optional[ContextObservation] = None
            for cand_date in reversed(candidates):
                candidate_obs = available_obs_dict[cand_date]
                if is_context_observation_available(candidate_obs, cutoff):
                    # Check calendar freshness (e.g. within max 5 calendar days)
                    if (ref_date - cand_date).days <= 5:
                        selected_obs = candidate_obs
                    break

            if selected_obs is not None:
                row_dict[f"{var_name.lower()}_close"] = selected_obs.close
                row_dict[f"{var_name.lower()}_obs_date"] = selected_obs.observation_date.isoformat()
            else:
                row_dict[f"{var_name.lower()}_close"] = np.nan
                row_dict[f"{var_name.lower()}_obs_date"] = None

        rows.append(row_dict)

    df = pd.DataFrame(rows)

    metadata = {
        "snapshot_type": snapshot_type.value,
        "record_count": len(df),
        "start_trading_date": reference_dates[0].isoformat() if reference_dates else None,
        "end_trading_date": reference_dates[-1].isoformat() if reference_dates else None,
        "variables_included": list(context_series_map.keys()),
    }

    return SnapshotContextTable(
        snapshot_type=snapshot_type,
        df=df,
        variable_names=list(context_series_map.keys()),
        metadata=metadata,
    )


__all__ = [
    "SnapshotContextTable",
    "build_snapshot_context_dataset",
]
