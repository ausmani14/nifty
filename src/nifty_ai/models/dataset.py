"""Dataset loading, temporal alignment, and supervised matrix generation for NIFTY AI.

Joins Phase 4 price features with Phase 5 targets strictly point-in-time, respecting
the canonical Snapshot A and Snapshot B semantics and isolating the terminal unlabeled session.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from nifty_ai.data.snapshots import SnapshotType

CLASS_MAP: Dict[str, int] = {"DOWN": 0, "SIDEWAYS": 1, "UP": 2}
INV_CLASS_MAP: Dict[int, str] = {0: "DOWN", 1: "SIDEWAYS", 2: "UP"}

# All 45 registered feature names from Phase 4
EXPECTED_FEATURE_NAMES: List[str] = [
    "ret_1d", "ret_2d", "ret_3d", "ret_5d", "ret_10d", "ret_20d",
    "ret_lag_1", "ret_lag_2", "ret_lag_3", "ret_lag_5", "ret_lag_10",
    "sma_5", "close_to_sma_5", "sma_10", "close_to_sma_10",
    "sma_20", "close_to_sma_20", "sma_50", "close_to_sma_50",
    "sma_100", "close_to_sma_100", "sma_200", "close_to_sma_200",
    "mom_5d", "mom_10d", "mom_20d", "mom_60d",
    "volatility_5d", "volatility_10d", "volatility_20d", "volatility_60d",
    "volatility_ann_20d", "hl_range_pct", "close_pos_in_range",
    "open_to_close_ret", "high_to_close_dist", "low_to_close_dist",
    "sma_ratio_20_50", "sma_ratio_50_200", "trend_slope_20d",
    "day_of_week", "day_of_month", "month", "quarter", "is_month_end",
]


@dataclass
class AlignedDataset:
    """Supervised training dataset with exact temporal alignment between features and targets."""
    X: np.ndarray                    # N x 45 feature matrix (float64)
    y_class: np.ndarray              # N length integer array (0: DOWN, 1: SIDEWAYS, 2: UP)
    y_reg: np.ndarray                # N length continuous target_return array (float64)
    dates: List[date]                # N length feature cutoff dates (Session T)
    target_dates: List[date]         # N length prediction target dates (Session T+1)
    close_prices: np.ndarray         # N length reference close prices (Close_T)
    feature_names: List[str]         # Exactly ordered feature names
    snapshot_type: SnapshotType
    inference_X: Optional[np.ndarray] = None          # 1 x 45 matrix for terminal session
    inference_date: Optional[date] = None            # Terminal feature cutoff date (2026-09-04)
    inference_close: Optional[float] = None          # Terminal close price


def load_aligned_dataset(
    features_csv_path: Path,
    targets_csv_path: Path,
    snapshot_type: SnapshotType = SnapshotType.SNAPSHOT_1540,
) -> AlignedDataset:
    """Load, align, and construct supervised feature matrix X and target vectors y.

    Canonical Alignment Contracts:
    - Snapshot A (15:40 on Session T):
      Features at Session T predict outcomes of Session T+1.
      Join key: features.trading_date == targets.trading_date (Session T).
    - Snapshot B (08:50 on Session T+1):
      Features finalized at Session T predict outcomes of Session T+1.
      Join key: features.trading_date == targets.feature_cutoff_session (Session T).

    Args:
        features_csv_path: Path to nifty50_features_clean.csv.
        targets_csv_path: Path to nifty50_targets_snapshot_a.csv or snapshot_b.csv.
        snapshot_type: SnapshotType.SNAPSHOT_1540 or SnapshotType.SNAPSHOT_0850.

    Returns:
        AlignedDataset instance containing verified numpy arrays.
    """
    if not features_csv_path.is_file():
        raise FileNotFoundError(f"Features file not found: {features_csv_path}")
    if not targets_csv_path.is_file():
        raise FileNotFoundError(f"Targets file not found: {targets_csv_path}")

    feat_df = pd.read_csv(features_csv_path)
    targ_df = pd.read_csv(targets_csv_path)

    # Verify all expected 45 features are present
    missing_cols = [c for c in EXPECTED_FEATURE_NAMES if c not in feat_df.columns]
    if missing_cols:
        raise ValueError(f"Features file is missing expected columns: {missing_cols}")

    if snapshot_type == SnapshotType.SNAPSHOT_1540:
        # Snapshot A: join on trading_date
        merged = pd.merge(
            feat_df,
            targ_df,
            on="trading_date",
            suffixes=("", "_target"),
            how="inner",
        )
        cutoff_date_col = "trading_date"
        target_date_col = "target_date"
        ref_close_col = "close"
    elif snapshot_type == SnapshotType.SNAPSHOT_0850:
        # Snapshot B: join features.trading_date == targets.feature_cutoff_session
        merged = pd.merge(
            feat_df,
            targ_df,
            left_on="trading_date",
            right_on="feature_cutoff_session",
            suffixes=("", "_target"),
            how="inner",
        )
        cutoff_date_col = "trading_date"
        target_date_col = "target_date"
        ref_close_col = "close"
    else:
        raise ValueError(f"Unsupported snapshot type: {snapshot_type}")

    # Chronological sort assurance
    merged["cutoff_dt"] = pd.to_datetime(merged[cutoff_date_col])
    merged = merged.sort_values("cutoff_dt").reset_index(drop=True)

    # Separate terminal unclassified row (has_target == False or is_classified == False)
    supervised_mask = (
        (merged["has_target"] == True) &
        (merged["has_threshold"] == True) &
        (merged["is_classified"] == True) &
        (merged["target_direction"].isin(CLASS_MAP.keys()))
    )

    sup_df = merged[supervised_mask].copy().reset_index(drop=True)
    inf_df = merged[~supervised_mask].copy().reset_index(drop=True)

    # Feature matrix X (float64)
    X = sup_df[EXPECTED_FEATURE_NAMES].values.astype(np.float64)
    if np.isnan(X).any():
        raise ValueError("Detected unexpected NaN values in supervised feature matrix X.")

    # Target class vector y_class (int64 in {0, 1, 2})
    y_class = sup_df["target_direction"].map(CLASS_MAP).values.astype(np.int64)

    # Target regression vector y_reg (float64)
    y_reg = sup_df["target_return"].values.astype(np.float64)

    # Metadata series
    dates = [d.date() for d in sup_df["cutoff_dt"]]
    target_dates = [date.fromisoformat(str(d)) for d in sup_df[target_date_col]]
    close_prices = sup_df[ref_close_col].values.astype(np.float64)

    # Terminal inference row
    inference_X = None
    inference_date = None
    inference_close = None
    if not inf_df.empty:
        terminal_row = inf_df.iloc[-1]
        inference_X = terminal_row[EXPECTED_FEATURE_NAMES].values.reshape(1, -1).astype(np.float64)
        inference_date = date.fromisoformat(str(terminal_row[cutoff_date_col]))
        inference_close = float(terminal_row[ref_close_col])

    return AlignedDataset(
        X=X,
        y_class=y_class,
        y_reg=y_reg,
        dates=dates,
        target_dates=target_dates,
        close_prices=close_prices,
        feature_names=EXPECTED_FEATURE_NAMES,
        snapshot_type=snapshot_type,
        inference_X=inference_X,
        inference_date=inference_date,
        inference_close=inference_close,
    )


__all__ = [
    "CLASS_MAP",
    "INV_CLASS_MAP",
    "EXPECTED_FEATURE_NAMES",
    "AlignedDataset",
    "load_aligned_dataset",
]
