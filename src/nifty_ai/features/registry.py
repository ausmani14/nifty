"""Feature registry and metadata catalog for NIFTY AI.

Provides structured definitions for all price-based features, recording formulas,
lookback windows, input dependencies, and information cutoff semantics.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass(frozen=True)
class FeatureDefinition:
    """Immutable specification of an individual feature."""
    name: str
    category: str
    formula: str
    lookback_period: int
    input_columns: List[str]
    snapshot_applicability: List[str]
    description: str
    leakage_risk: str = "none"
    notes: Optional[str] = None


class FeatureRegistry:
    """Catalog of all registered features in NIFTY AI."""

    def __init__(self) -> None:
        self._features: Dict[str, FeatureDefinition] = {}

    def register(self, feature: FeatureDefinition) -> None:
        """Register a feature definition."""
        self._features[feature.name] = feature

    def get(self, name: str) -> FeatureDefinition:
        """Retrieve a feature definition by name."""
        if name not in self._features:
            raise KeyError(f"Feature '{name}' not found in registry.")
        return self._features[name]

    def list_all(self) -> List[FeatureDefinition]:
        """Return all registered feature definitions."""
        return list(self._features.values())

    def list_by_category(self, category: str) -> List[FeatureDefinition]:
        """Filter features by category."""
        return [f for f in self._features.values() if f.category == category]

    @property
    def max_lookback(self) -> int:
        """Maximum lookback window across all registered features (warm-up requirement)."""
        return max((f.lookback_period for f in self._features.values()), default=0)

    def to_dict(self) -> Dict[str, Any]:
        """Export registry as a dictionary."""
        return {
            "feature_count": len(self._features),
            "max_lookback": self.max_lookback,
            "features": {f.name: asdict(f) for f in self._features.values()},
        }

    def save_yaml(self, path: Path) -> Path:
        """Export registry to a YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, sort_keys=False, indent=2)
        return path


def build_default_feature_registry() -> FeatureRegistry:
    """Construct and populate the standard V1 baseline price feature registry."""
    registry = FeatureRegistry()

    # 1. Price Returns (Historical close-to-close returns)
    return_windows = [1, 2, 3, 5, 10, 20]
    for w in return_windows:
        registry.register(
            FeatureDefinition(
                name=f"ret_{w}d",
                category="returns",
                formula=f"(close_t / close_(t-{w})) - 1",
                lookback_period=w,
                input_columns=["close"],
                snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
                description=f"Trailing {w}-day close-to-close percentage price return.",
            )
        )

    # 2. Lagged Returns
    lag_steps = [1, 2, 3, 5, 10]
    for lag in lag_steps:
        registry.register(
            FeatureDefinition(
                name=f"ret_lag_{lag}",
                category="lags",
                formula=f"ret_1d_(t-{lag})",
                lookback_period=lag + 1,
                input_columns=["close"],
                snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
                description=f"1-day return lagged by {lag} completed trading session(s).",
            )
        )

    # 3. Simple Moving Averages (SMA) & Normalized Distance
    ma_windows = [5, 10, 20, 50, 100, 200]
    for w in ma_windows:
        registry.register(
            FeatureDefinition(
                name=f"sma_{w}",
                category="moving_averages",
                formula=f"mean(close_(t-{w}+1 : t))",
                lookback_period=w,
                input_columns=["close"],
                snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
                description=f"Trailing {w}-day simple moving average of closing price.",
            )
        )
        registry.register(
            FeatureDefinition(
                name=f"close_to_sma_{w}",
                category="moving_averages",
                formula=f"(close_t / sma_{w}) - 1",
                lookback_period=w,
                input_columns=["close"],
                snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
                description=f"Percentage distance of closing price from trailing {w}-day SMA.",
            )
        )

    # 4. Momentum Features
    mom_windows = [5, 10, 20, 60]
    for w in mom_windows:
        registry.register(
            FeatureDefinition(
                name=f"mom_{w}d",
                category="momentum",
                formula=f"close_t - close_(t-{w})",
                lookback_period=w,
                input_columns=["close"],
                snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
                description=f"Absolute price change over trailing {w} completed sessions.",
            )
        )

    # 5. Volatility Features (Standard deviation of daily returns)
    vol_windows = [5, 10, 20, 60]
    for w in vol_windows:
        registry.register(
            FeatureDefinition(
                name=f"volatility_{w}d",
                category="volatility",
                formula=f"std_dev(ret_1d_(t-{w}+1 : t))",
                lookback_period=w + 1,
                input_columns=["close"],
                snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
                description=f"Trailing {w}-day sample standard deviation of daily returns.",
            )
        )
    registry.register(
        FeatureDefinition(
            name="volatility_ann_20d",
            category="volatility",
            formula="volatility_20d * sqrt(252)",
            lookback_period=21,
            input_columns=["close"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Annualized trailing 20-day volatility assuming 252 trading sessions.",
        )
    )

    # 6. OHLC Range & Shape Features
    registry.register(
        FeatureDefinition(
            name="hl_range_pct",
            category="ohlc_shape",
            formula="(high_t - low_t) / low_t",
            lookback_period=1,
            input_columns=["high", "low"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Intraday high-low range expressed as a percentage of low.",
        )
    )
    registry.register(
        FeatureDefinition(
            name="close_pos_in_range",
            category="ohlc_shape",
            formula="(close_t - low_t) / (high_t - low_t)",
            lookback_period=1,
            input_columns=["high", "low", "close"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Close location within the daily high-low range [0.0, 1.0].",
        )
    )
    registry.register(
        FeatureDefinition(
            name="open_to_close_ret",
            category="ohlc_shape",
            formula="(close_t - open_t) / open_t",
            lookback_period=1,
            input_columns=["open", "close"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Intraday session return from session open to official close.",
        )
    )
    registry.register(
        FeatureDefinition(
            name="high_to_close_dist",
            category="ohlc_shape",
            formula="(high_t - close_t) / close_t",
            lookback_period=1,
            input_columns=["high", "close"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Normalized distance between session high and official close.",
        )
    )
    registry.register(
        FeatureDefinition(
            name="low_to_close_dist",
            category="ohlc_shape",
            formula="(close_t - low_t) / close_t",
            lookback_period=1,
            input_columns=["low", "close"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Normalized distance between official close and session low.",
        )
    )

    # 7. Trend Features
    registry.register(
        FeatureDefinition(
            name="sma_ratio_20_50",
            category="trend",
            formula="(sma_20 / sma_50) - 1",
            lookback_period=50,
            input_columns=["close"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Spread between 20-day and 50-day moving averages.",
        )
    )
    registry.register(
        FeatureDefinition(
            name="sma_ratio_50_200",
            category="trend",
            formula="(sma_50 / sma_200) - 1",
            lookback_period=200,
            input_columns=["close"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Spread between 50-day and 200-day moving averages (Golden/Death cross proxy).",
        )
    )
    registry.register(
        FeatureDefinition(
            name="trend_slope_20d",
            category="trend",
            formula="linear_regression_slope(close_(t-19:t)) / mean(close)",
            lookback_period=20,
            input_columns=["close"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Normalized linear regression slope of closing prices over trailing 20 days.",
        )
    )

    # 8. Calendar Features (Point-in-time deterministic temporal attributes)
    registry.register(
        FeatureDefinition(
            name="day_of_week",
            category="calendar",
            formula="trading_date.weekday()",
            lookback_period=0,
            input_columns=["trading_date"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Day of week integer (0=Monday, 1=Tuesday, ..., 4=Friday, 5=Saturday).",
        )
    )
    registry.register(
        FeatureDefinition(
            name="day_of_month",
            category="calendar",
            formula="trading_date.day",
            lookback_period=0,
            input_columns=["trading_date"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Day of the month integer (1 to 31).",
        )
    )
    registry.register(
        FeatureDefinition(
            name="month",
            category="calendar",
            formula="trading_date.month",
            lookback_period=0,
            input_columns=["trading_date"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Calendar month integer (1 to 12).",
        )
    )
    registry.register(
        FeatureDefinition(
            name="quarter",
            category="calendar",
            formula="(trading_date.month - 1) // 3 + 1",
            lookback_period=0,
            input_columns=["trading_date"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Calendar quarter integer (1 to 4).",
        )
    )
    registry.register(
        FeatureDefinition(
            name="is_month_end",
            category="calendar",
            formula="1 if next_calendar_day.month != current_month else 0",
            lookback_period=0,
            input_columns=["trading_date"],
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            description="Binary flag (1 or 0) indicating whether session is near the month-end expiry boundary.",
        )
    )

    return registry


default_feature_registry = build_default_feature_registry()

__all__ = [
    "FeatureDefinition",
    "FeatureRegistry",
    "build_default_feature_registry",
    "default_feature_registry",
]
