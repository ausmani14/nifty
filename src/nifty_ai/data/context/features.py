"""Phase 7 baseline context feature engineering transformations.

Generates limited baseline context features:
- Percentage returns (1d, 5d)
- Level changes for yields and volatility (e.g. delta India VIX, delta US 10Y)
- Yield spread and volatility ratio indicators
Strictly respects lookback boundaries and point-in-time snapshot availability.
"""

from typing import Dict, List, Optional
import numpy as np
import pandas as pd


def compute_series_return(
    values: np.ndarray,
    lookback: int = 1,
) -> np.ndarray:
    """Calculate percentage price return over lookback sessions: (P_t / P_(t-k)) - 1."""
    ret = np.full(len(values), np.nan, dtype=np.float64)
    for i in range(lookback, len(values)):
        v_curr = values[i]
        v_prev = values[i - lookback]
        if np.isfinite(v_curr) and np.isfinite(v_prev) and v_prev != 0.0:
            ret[i] = (v_curr / v_prev) - 1.0
    return ret


def compute_series_diff(
    values: np.ndarray,
    lookback: int = 1,
) -> np.ndarray:
    """Calculate level change for yields or volatility: V_t - V_(t-k)."""
    diff = np.full(len(values), np.nan, dtype=np.float64)
    for i in range(lookback, len(values)):
        v_curr = values[i]
        v_prev = values[i - lookback]
        if np.isfinite(v_curr) and np.isfinite(v_prev):
            diff[i] = v_curr - v_prev
    return diff


def compute_rolling_volatility(
    returns: np.ndarray,
    window: int = 20,
) -> np.ndarray:
    """Calculate rolling sample standard deviation of returns with zero lookahead."""
    vol = np.full(len(returns), np.nan, dtype=np.float64)
    for i in range(window - 1, len(returns)):
        sub = returns[i - window + 1 : i + 1]
        valid_sub = sub[np.isfinite(sub)]
        if len(valid_sub) >= window // 2:
            vol[i] = float(np.std(valid_sub, ddof=1))
    return vol


__all__ = [
    "compute_series_return",
    "compute_series_diff",
    "compute_rolling_volatility",
]
