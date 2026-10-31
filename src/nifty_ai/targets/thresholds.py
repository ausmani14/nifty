"""SIDEWAYS threshold computation models and candidate methodologies for NIFTY AI.

Provides a pluggable framework for evaluating candidate threshold methodologies:
- Method A: Volatility-scaled threshold (proportional to trailing realized volatility)
- Method B: Empirical return-distribution threshold (percentile of trailing absolute returns)
- Method C: Fixed baseline threshold (constant percentage)

All methods strictly enforce point-in-time calculation using trailing historical data
available at or before the feature cutoff, preventing future look-ahead leakage.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
import math
import statistics
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ThresholdResult:
    """Calculated threshold value for a specific trading session."""
    trading_date: date
    threshold_value: Optional[float]
    method_name: str
    parameters: Dict[str, Any]
    is_warmup: bool


class ThresholdMethod(ABC):
    """Abstract base class for SIDEWAYS threshold calculation methodologies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier name of the methodology."""
        pass

    @property
    @abstractmethod
    def min_lookback(self) -> int:
        """Minimum number of trailing return observations required."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Dictionary of configuration parameters."""
        pass

    @abstractmethod
    def compute_threshold(self, trailing_returns: List[float]) -> Optional[float]:
        """Compute threshold from trailing returns available up to prediction cutoff.

        Args:
            trailing_returns: List of trailing daily returns up to cutoff date.

        Returns:
            Positive float threshold theta, or None if lookback insufficient.
        """
        pass


class VolatilityScaledThreshold(ThresholdMethod):
    """Method A: Dynamic volatility-calibrated threshold.

    theta_T = k * stdev(trailing_returns[window])
    """

    def __init__(self, k: float = 0.35, window: int = 20) -> None:
        if k <= 0:
            raise ValueError(f"Multiplier k must be positive, got {k}")
        if window < 2:
            raise ValueError(f"Window must be >= 2 for standard deviation, got {window}")
        self._k = k
        self._window = window

    @property
    def name(self) -> str:
        return "volatility_scaled"

    @property
    def min_lookback(self) -> int:
        return self._window

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"k": self._k, "window": self._window}

    def compute_threshold(self, trailing_returns: List[float]) -> Optional[float]:
        if len(trailing_returns) < self._window:
            return None
        window_returns = trailing_returns[-self._window :]
        sigma = statistics.stdev(window_returns)
        return float(self._k * sigma)


class EmpiricalDistributionThreshold(ThresholdMethod):
    """Method B: Trailing empirical return-distribution threshold.

    Computes the p-th percentile of absolute trailing daily returns:
    theta_T = percentile_p(|trailing_returns[window]|)
    Represents the boundary of the central noise band.
    """

    def __init__(self, percentile: float = 30.0, window: int = 252) -> None:
        if not (0.0 < percentile < 100.0):
            raise ValueError(f"Percentile must be in (0, 100), got {percentile}")
        if window < 10:
            raise ValueError(f"Window must be >= 10, got {window}")
        self._percentile = percentile
        self._window = window

    @property
    def name(self) -> str:
        return "empirical_distribution"

    @property
    def min_lookback(self) -> int:
        return self._window

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"percentile": self._percentile, "window": self._window}

    def compute_threshold(self, trailing_returns: List[float]) -> Optional[float]:
        if len(trailing_returns) < self._window:
            return None
        window_returns = trailing_returns[-self._window :]
        abs_returns = sorted(abs(r) for r in window_returns)

        # Linear interpolation percentile
        n = len(abs_returns)
        k = (n - 1) * (self._percentile / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            val = abs_returns[int(k)]
        else:
            d0 = abs_returns[int(f)] * (c - k)
            d1 = abs_returns[int(c)] * (k - f)
            val = d0 + d1
        return float(val)


class FixedThreshold(ThresholdMethod):
    """Method C: Fixed percentage baseline threshold (e.g. 0.5% = 0.005)."""

    def __init__(self, value: float = 0.005) -> None:
        if value <= 0:
            raise ValueError(f"Fixed threshold must be positive, got {value}")
        self._value = value

    @property
    def name(self) -> str:
        return "fixed_baseline"

    @property
    def min_lookback(self) -> int:
        return 0

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"value": self._value}

    def compute_threshold(self, trailing_returns: List[float]) -> Optional[float]:
        return float(self._value)


def compute_rolling_thresholds(
    method: ThresholdMethod,
    dates: List[date],
    daily_returns: List[Optional[float]],
) -> List[ThresholdResult]:
    """Compute point-in-time rolling thresholds for a chronological series.

    For each index i (date T):
        Only returns at or before index i are visible.
        None returns (e.g. at index 0) are excluded.
        If available valid returns < method.min_lookback, threshold is None (warm-up).

    Args:
        method: Instance of ThresholdMethod.
        dates: List of trading dates.
        daily_returns: List of daily returns up to and including each date.

    Returns:
        List of ThresholdResult objects aligned with dates.
    """
    if len(dates) != len(daily_returns):
        raise ValueError(
            f"Mismatched lengths: dates ({len(dates)}) vs daily_returns ({len(daily_returns)})"
        )

    results: List[ThresholdResult] = []
    valid_returns_accum: List[float] = []

    for d, r in zip(dates, daily_returns):
        if r is not None and not math.isnan(r):
            valid_returns_accum.append(r)

        thresh = method.compute_threshold(valid_returns_accum)
        is_warmup = (thresh is None)
        results.append(
            ThresholdResult(
                trading_date=d,
                threshold_value=thresh,
                method_name=method.name,
                parameters=method.parameters,
                is_warmup=is_warmup,
            )
        )

    return results


__all__ = [
    "ThresholdResult",
    "ThresholdMethod",
    "VolatilityScaledThreshold",
    "EmpiricalDistributionThreshold",
    "FixedThreshold",
    "compute_rolling_thresholds",
]
