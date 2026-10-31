"""Price-based feature engineering engine for NIFTY AI.

Implements mathematically rigorous, leakage-free feature calculations using
historical OHLC prices only. Excludes quarantined volume data.
"""

from datetime import date, datetime, timedelta
import math
import statistics
from typing import Any, Dict, List, Optional, Tuple

from nifty_ai.data.schema import NormalizedMarketRecord
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.features.registry import FeatureRegistry, default_feature_registry


def linear_regression_slope(y_values: List[float]) -> float:
    """Compute ordinary least squares linear regression slope for equally spaced y values."""
    n = len(y_values)
    if n < 2:
        return 0.0
    # x = 0, 1, ..., n-1
    x_mean = (n - 1) / 2.0
    y_mean = sum(y_values) / n

    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(y_values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0
    return numerator / denominator


class PriceFeatureEngine:
    """Computes baseline price, momentum, moving average, volatility, and shape features."""

    def __init__(self, registry: Optional[FeatureRegistry] = None) -> None:
        self.registry = registry or default_feature_registry

    def compute_features(
        self,
        records: List[NormalizedMarketRecord],
        trim_warmup: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Compute all registered price features chronologically across the market records.

        Args:
            records: Chronologically sorted NormalizedMarketRecord instances.
            trim_warmup: If True, drops initial rows (indices < max_lookback) having NaNs.

        Returns:
            Tuple of (feature_rows, metadata_dict).
        """
        if not records:
            return [], {"row_count": 0, "feature_count": 0}

        closes = [r.close for r in records]
        opens = [r.open for r in records]
        highs = [r.high for r in records]
        lows = [r.low for r in records]
        dates = [r.trading_date for r in records]
        timestamps = [r.timestamp for r in records]
        n_rows = len(records)

        # 1. Precompute 1-day returns for lag and volatility calculations
        ret_1d_list: List[Optional[float]] = [None] * n_rows
        for i in range(1, n_rows):
            ret_1d_list[i] = (closes[i] / closes[i - 1]) - 1.0

        feature_rows: List[Dict[str, Any]] = []
        max_lookback = self.registry.max_lookback  # 200

        for i in range(n_rows):
            row: Dict[str, Any] = {
                "trading_date": dates[i].isoformat(),
                "timestamp": timestamps[i].isoformat(),
                "symbol": records[i].symbol,
                "close": closes[i],
            }

            # ------------------------------------------------------------------
            # A. Returns (close-to-close)
            # ------------------------------------------------------------------
            for w in [1, 2, 3, 5, 10, 20]:
                if i >= w:
                    row[f"ret_{w}d"] = (closes[i] / closes[i - w]) - 1.0
                else:
                    row[f"ret_{w}d"] = None

            # ------------------------------------------------------------------
            # B. Lagged Returns (lag 1 refers to ret_1d from day i-1)
            # ------------------------------------------------------------------
            for lag in [1, 2, 3, 5, 10]:
                if i >= lag and ret_1d_list[i - lag + 1] is not None:
                    # Note: lag 1 of ret_1d at day i is ret_1d at day i-1
                    # At index i, ret_1d is (closes[i]/closes[i-1]) - 1
                    # So lag 1 is ret_1d_list[i-1], lag 2 is ret_1d_list[i-2], etc.
                    row[f"ret_lag_{lag}"] = ret_1d_list[i - lag] if (i - lag >= 1) else None
                else:
                    row[f"ret_lag_{lag}"] = None

            # ------------------------------------------------------------------
            # C. Moving Averages & Distances
            # ------------------------------------------------------------------
            smas: Dict[int, Optional[float]] = {}
            for w in [5, 10, 20, 50, 100, 200]:
                if i >= w - 1:
                    window = closes[i - w + 1 : i + 1]
                    sma_val = sum(window) / w
                    smas[w] = sma_val
                    row[f"sma_{w}"] = sma_val
                    row[f"close_to_sma_{w}"] = (closes[i] / sma_val) - 1.0
                else:
                    smas[w] = None
                    row[f"sma_{w}"] = None
                    row[f"close_to_sma_{w}"] = None

            # ------------------------------------------------------------------
            # D. Momentum Features
            # ------------------------------------------------------------------
            for w in [5, 10, 20, 60]:
                if i >= w:
                    row[f"mom_{w}d"] = closes[i] - closes[i - w]
                else:
                    row[f"mom_{w}d"] = None

            # ------------------------------------------------------------------
            # E. Volatility Features (Standard deviation of daily returns)
            # ------------------------------------------------------------------
            for w in [5, 10, 20, 60]:
                # Need w daily return points, which requires w + 1 close prices
                if i >= w:
                    ret_window = [r for r in ret_1d_list[i - w + 1 : i + 1] if r is not None]
                    if len(ret_window) == w and w >= 2:
                        vol = statistics.stdev(ret_window)
                        row[f"volatility_{w}d"] = vol
                    else:
                        row[f"volatility_{w}d"] = None
                else:
                    row[f"volatility_{w}d"] = None

            # Annualized 20-day volatility
            vol_20 = row.get("volatility_20d")
            if vol_20 is not None:
                row["volatility_ann_20d"] = vol_20 * math.sqrt(252.0)
            else:
                row["volatility_ann_20d"] = None

            # ------------------------------------------------------------------
            # F. OHLC Range & Shape Features
            # ------------------------------------------------------------------
            h = highs[i]
            l = lows[i]
            o = opens[i]
            c = closes[i]

            row["hl_range_pct"] = (h - l) / l if l > 0 else 0.0
            row["close_pos_in_range"] = (c - l) / (h - l) if h > l else 0.5
            row["open_to_close_ret"] = (c - o) / o if o > 0 else 0.0
            row["high_to_close_dist"] = (h - c) / c if c > 0 else 0.0
            row["low_to_close_dist"] = (c - l) / c if c > 0 else 0.0

            # ------------------------------------------------------------------
            # G. Trend Features
            # ------------------------------------------------------------------
            sma20 = smas.get(20)
            sma50 = smas.get(50)
            sma200 = smas.get(200)

            if sma20 is not None and sma50 is not None and sma50 > 0:
                row["sma_ratio_20_50"] = (sma20 / sma50) - 1.0
            else:
                row["sma_ratio_20_50"] = None

            if sma50 is not None and sma200 is not None and sma200 > 0:
                row["sma_ratio_50_200"] = (sma50 / sma200) - 1.0
            else:
                row["sma_ratio_50_200"] = None

            if i >= 19:
                window_20 = closes[i - 19 : i + 1]
                mean_20 = sum(window_20) / 20.0
                slope = linear_regression_slope(window_20)
                row["trend_slope_20d"] = slope / mean_20 if mean_20 > 0 else 0.0
            else:
                row["trend_slope_20d"] = None

            # ------------------------------------------------------------------
            # H. Calendar Features
            # ------------------------------------------------------------------
            d = dates[i]
            row["day_of_week"] = d.weekday()
            row["day_of_month"] = d.day
            row["month"] = d.month
            row["quarter"] = (d.month - 1) // 3 + 1

            # Approximate month end check (last 3 calendar days of month)
            next_day = d + timedelta(days=1)
            row["is_month_end"] = 1 if next_day.month != d.month else 0

            feature_rows.append(row)

        # Handle warm-up trimming if requested
        if trim_warmup:
            clean_rows = feature_rows[max_lookback:]
            warmup_dropped = max_lookback
        else:
            clean_rows = feature_rows
            warmup_dropped = 0

        metadata = {
            "total_records_processed": n_rows,
            "warmup_lookback_required": max_lookback,
            "warmup_rows_dropped": warmup_dropped,
            "output_rows_count": len(clean_rows),
            "feature_count": len(self.registry.list_all()),
            "feature_names": [f.name for f in self.registry.list_all()],
            "volume_included": False,
        }

        return clean_rows, metadata

    def get_features_for_prediction(
        self,
        historical_records: List[NormalizedMarketRecord],
        target_prediction_date: date,
        snapshot_type: SnapshotType,
    ) -> Dict[str, Any]:
        """Extract the exact leakage-free feature vector for a specific snapshot prediction.

        Rules:
        - Snapshot A (15:40 on T-1): Uses completed daily bar of Day T-1.
        - Snapshot B (08:50 on T): Uses completed daily bar of Day T-1.
          Day T's daily bar is strictly inaccessible.
        """
        if not historical_records:
            raise ValueError("historical_records cannot be empty.")

        # Find the latest eligible completed trading day prior to or at T-1
        eligible_records = [
            r for r in historical_records
            if r.trading_date < target_prediction_date
        ]

        if not eligible_records:
            raise ValueError(
                f"No eligible completed historical records found prior to {target_prediction_date}."
            )

        features, _ = self.compute_features(eligible_records, trim_warmup=False)
        return features[-1]


__all__ = ["linear_regression_slope", "PriceFeatureEngine"]
