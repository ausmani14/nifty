"""Chronological expanding-window walk-forward validation splitter for NIFTY AI.

Implements strict temporal partitioning:
- 8 expanding-window development folds (2014 to 2021)
- Guaranteed zero lookahead: train_dates < val_dates
- Complete isolation of the final holdout partition (>= 2022-01-01)
"""

from dataclasses import dataclass
from datetime import date
from typing import Iterator, List, Tuple
import numpy as np


@dataclass(frozen=True)
class WalkForwardFold:
    """Represents a single chronological train/validation fold."""
    fold_id: int
    train_indices: np.ndarray
    val_indices: np.ndarray
    train_start_date: date
    train_end_date: date
    val_start_date: date
    val_end_date: date
    era_name: str


class WalkForwardSplitter:
    """Generates expanding-window chronological cross-validation folds strictly within development partition."""

    def __init__(
        self,
        development_end_date: date = date(2021, 12, 31),
    ) -> None:
        self.development_end_date = development_end_date

        # 8 expanding-window development validation eras (1 calendar year each)
        self.fold_definitions = [
            (1, date(2014, 1, 1), date(2014, 12, 31), "2014 General Election & Bull Market"),
            (2, date(2015, 1, 1), date(2015, 12, 31), "2015 Commodity Deflation & Consolidation"),
            (3, date(2016, 1, 1), date(2016, 12, 31), "2016 Demonetization & Volatility Shock"),
            (4, date(2017, 1, 1), date(2017, 12, 31), "2017 Low-Volatility Secular Bull"),
            (5, date(2018, 1, 1), date(2018, 12, 31), "2018 IL&FS Credit Crisis & Correction"),
            (6, date(2019, 1, 1), date(2019, 12, 31), "2019 Corporate Tax Cut & Pre-COVID Rally"),
            (7, date(2020, 1, 1), date(2020, 12, 31), "2020 COVID-19 Crash & Rapid Rebound"),
            (8, date(2021, 1, 1), date(2021, 12, 31), "2021 Post-COVID Global Liquidity Expansion"),
        ]

    def split_development(self, dates: List[date]) -> List[WalkForwardFold]:
        """Generate the 8 expanding-window folds on development observations (dates <= 2021-12-31)."""
        folds: List[WalkForwardFold] = []
        date_arr = np.array(dates)

        for fold_id, val_start, val_end, era_name in self.fold_definitions:
            train_mask = (date_arr < val_start) & (date_arr <= self.development_end_date)
            val_mask = (date_arr >= val_start) & (date_arr <= val_end)

            train_indices = np.where(train_mask)[0]
            val_indices = np.where(val_mask)[0]

            if len(train_indices) == 0 or len(val_indices) == 0:
                continue

            train_start_d = date_arr[train_indices[0]]
            train_end_d = date_arr[train_indices[-1]]
            val_start_d = date_arr[val_indices[0]]
            val_end_d = date_arr[val_indices[-1]]

            # Strict chronological assertion
            assert train_end_d < val_start_d, f"Leakage detected in Fold {fold_id}: {train_end_d} >= {val_start_d}"

            folds.append(
                WalkForwardFold(
                    fold_id=fold_id,
                    train_indices=train_indices,
                    val_indices=val_indices,
                    train_start_date=train_start_d,
                    train_end_date=train_end_d,
                    val_start_date=val_start_d,
                    val_end_date=val_end_d,
                    era_name=era_name,
                )
            )

        return folds

    def get_development_and_holdout_indices(
        self,
        dates: List[date],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Isolate development indices (<= 2021-12-31) and final holdout indices (>= 2022-01-01)."""
        date_arr = np.array(dates)
        dev_indices = np.where(date_arr <= self.development_end_date)[0]
        holdout_indices = np.where(date_arr > self.development_end_date)[0]

        assert len(dev_indices) > 0, "Development partition cannot be empty."
        assert len(holdout_indices) > 0, "Holdout partition cannot be empty."
        assert date_arr[dev_indices[-1]] < date_arr[holdout_indices[0]], "Temporal breach between dev and holdout."

        return dev_indices, holdout_indices


__all__ = ["WalkForwardFold", "WalkForwardSplitter"]
