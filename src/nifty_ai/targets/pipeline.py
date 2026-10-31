"""Pipeline orchestrator for target dataset generation in NIFTY AI.

Coordinates loading of validated processed market data, computation of next-session
returns, rolling point-in-time SIDEWAYS threshold estimation, and atomic persistence
of target datasets for Snapshot A and Snapshot B with metadata manifests.
"""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.schema import NormalizedMarketRecord
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.data.storage import compute_file_sha256, load_processed_market_data
from nifty_ai.targets.classification import ClassifiedTarget, classify_targets
from nifty_ai.targets.returns import TargetReturn, compute_next_session_returns
from nifty_ai.targets.thresholds import (
    ThresholdMethod,
    VolatilityScaledThreshold,
    compute_rolling_thresholds,
)

TARGETS_DIR = PROJECT_ROOT / "data" / "targets"


class TargetPipeline:
    """Orchestrates target computation and export for both prediction snapshots."""

    def __init__(
        self,
        threshold_method: Optional[ThresholdMethod] = None,
    ) -> None:
        self.threshold_method = threshold_method or VolatilityScaledThreshold(k=0.35, window=20)

    def run(
        self,
        input_csv_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> Tuple[Path, Path, Dict[str, Any]]:
        """Execute the end-to-end target generation pipeline.

        Args:
            input_csv_path: Path to processed market data CSV (defaults to data/processed/nifty_50_daily.csv).
            output_dir: Destination directory for target datasets (defaults to data/targets/).

        Returns:
            Tuple of (snapshot_a_csv_path, snapshot_b_csv_path, metadata_dict).
        """
        in_path = input_csv_path or (PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv")
        out_dir = output_dir or TARGETS_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        if not in_path.is_file():
            raise FileNotFoundError(f"Processed market data file not found: {in_path}")

        records: List[NormalizedMarketRecord] = load_processed_market_data(in_path)
        source_sha256 = compute_file_sha256(in_path)

        # 1. Compute regression targets (next-session returns)
        target_returns: List[TargetReturn] = compute_next_session_returns(records)

        # 2. Compute trailing daily returns up to cutoff T for rolling threshold
        dates = [r.trading_date for r in records]
        daily_returns: List[Optional[float]] = [None] * len(records)
        for i in range(1, len(records)):
            daily_returns[i] = (records[i].close / records[i - 1].close) - 1.0

        # 3. Compute rolling thresholds strictly point-in-time
        threshold_results = compute_rolling_thresholds(
            method=self.threshold_method,
            dates=dates,
            daily_returns=daily_returns,
        )

        # 4. Classify targets
        classified_targets: List[ClassifiedTarget] = classify_targets(
            target_returns=target_returns,
            threshold_results=threshold_results,
        )

        # 5. Write Snapshot A CSV (Execution: 15:40 on Day T, predicting Day T+1)
        snap_a_path = out_dir / "nifty50_targets_snapshot_a.csv"
        self._write_snapshot_a_csv(records, classified_targets, snap_a_path)
        snap_a_sha256 = compute_file_sha256(snap_a_path)

        # 6. Write Snapshot B CSV (Execution: 08:50 on Day T+1, predicting Day T+1)
        snap_b_path = out_dir / "nifty50_targets_snapshot_b.csv"
        self._write_snapshot_b_csv(records, classified_targets, snap_b_path)
        snap_b_sha256 = compute_file_sha256(snap_b_path)

        # 7. Aggregate summary metrics
        total_rows = len(classified_targets)
        classified_rows = [ct for ct in classified_targets if ct.is_classified]
        classified_count = len(classified_rows)
        warmup_count = sum(1 for ct in classified_targets if not ct.has_threshold)
        terminal_count = sum(1 for ct in classified_targets if not ct.has_target)

        up_count = sum(1 for ct in classified_rows if ct.target_direction == "UP")
        down_count = sum(1 for ct in classified_rows if ct.target_direction == "DOWN")
        sideways_count = sum(1 for ct in classified_rows if ct.target_direction == "SIDEWAYS")

        up_pct = (up_count / classified_count * 100.0) if classified_count > 0 else 0.0
        down_pct = (down_count / classified_count * 100.0) if classified_count > 0 else 0.0
        sideways_pct = (sideways_count / classified_count * 100.0) if classified_count > 0 else 0.0

        metadata: Dict[str, Any] = {
            "source_dataset": in_path.name,
            "source_sha256": source_sha256,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target_version": "1.0.0",
            "threshold_method": self.threshold_method.name,
            "threshold_parameters": self.threshold_method.parameters,
            "total_rows": total_rows,
            "classified_rows": classified_count,
            "warmup_rows_excluded": warmup_count,
            "terminal_unlabeled_rows": terminal_count,
            "start_date": records[0].trading_date.isoformat(),
            "end_date": records[-1].trading_date.isoformat(),
            "class_counts": {
                "UP": up_count,
                "DOWN": down_count,
                "SIDEWAYS": sideways_count,
            },
            "class_distribution_pct": {
                "UP": round(up_pct, 2),
                "DOWN": round(down_pct, 2),
                "SIDEWAYS": round(sideways_pct, 2),
            },
            "up_down_ratio": round(up_count / down_count, 3) if down_count > 0 else None,
            "snapshot_a_file": snap_a_path.name,
            "snapshot_a_sha256": snap_a_sha256,
            "snapshot_b_file": snap_b_path.name,
            "snapshot_b_sha256": snap_b_sha256,
        }

        meta_file = out_dir / "nifty50_targets.meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return snap_a_path, snap_b_path, metadata

    def _write_snapshot_a_csv(
        self,
        records: List[NormalizedMarketRecord],
        classified: List[ClassifiedTarget],
        path: Path,
    ) -> None:
        """Write targets aligned to Snapshot A (executed at 15:40 Day T)."""
        fieldnames = [
            "trading_date",
            "timestamp",
            "symbol",
            "close",
            "target_date",
            "target_close",
            "target_return",
            "threshold_method",
            "threshold_value",
            "target_direction",
            "snapshot_type",
            "has_target",
            "has_threshold",
            "is_classified",
            "target_version",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for rec, ct in zip(records, classified):
                writer.writerow({
                    "trading_date": ct.trading_date.isoformat(),
                    "timestamp": rec.timestamp.isoformat(),
                    "symbol": rec.symbol,
                    "close": f"{ct.close:.4f}",
                    "target_date": ct.target_date.isoformat() if ct.target_date else "",
                    "target_close": f"{ct.target_close:.4f}" if ct.target_close is not None else "",
                    "target_return": f"{ct.target_return:.6f}" if ct.target_return is not None else "",
                    "threshold_method": ct.threshold_method,
                    "threshold_value": f"{ct.threshold_value:.6f}" if ct.threshold_value is not None else "",
                    "target_direction": ct.target_direction.value if ct.target_direction else "",
                    "snapshot_type": SnapshotType.SNAPSHOT_1540.value,
                    "has_target": ct.has_target,
                    "has_threshold": ct.has_threshold,
                    "is_classified": ct.is_classified,
                    "target_version": "1.0.0",
                })

    def _write_snapshot_b_csv(
        self,
        records: List[NormalizedMarketRecord],
        classified: List[ClassifiedTarget],
        path: Path,
    ) -> None:
        """Write targets aligned to Snapshot B (executed at 08:50 on target morning).

        For target session T (which opens at 09:15):
        - Prediction execution: 08:50 on date T
        - Information cutoff: strictly 08:50 on date T
        - Latest eligible completed daily bar: session T-1
        - Target outcome: close-to-close return of session T relative to T-1
        """
        fieldnames = [
            "prediction_date",
            "feature_cutoff_session",
            "feature_close",
            "target_date",
            "target_close",
            "target_return",
            "threshold_method",
            "threshold_value",
            "target_direction",
            "snapshot_type",
            "has_target",
            "has_threshold",
            "is_classified",
            "target_version",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for rec, ct in zip(records, classified):
                # When predicting target_date at 08:50 in the morning:
                # The prediction date is target_date (or empty for terminal)
                # Feature cutoff session is trading_date (Day T-1 relative to target_date)
                pred_date = ct.target_date.isoformat() if ct.target_date else ""
                writer.writerow({
                    "prediction_date": pred_date,
                    "feature_cutoff_session": ct.trading_date.isoformat(),
                    "feature_close": f"{ct.close:.4f}",
                    "target_date": pred_date,
                    "target_close": f"{ct.target_close:.4f}" if ct.target_close is not None else "",
                    "target_return": f"{ct.target_return:.6f}" if ct.target_return is not None else "",
                    "threshold_method": ct.threshold_method,
                    "threshold_value": f"{ct.threshold_value:.6f}" if ct.threshold_value is not None else "",
                    "target_direction": ct.target_direction.value if ct.target_direction else "",
                    "snapshot_type": SnapshotType.SNAPSHOT_0850.value,
                    "has_target": ct.has_target,
                    "has_threshold": ct.has_threshold,
                    "is_classified": ct.is_classified,
                    "target_version": "1.0.0",
                })


__all__ = ["TARGETS_DIR", "TargetPipeline"]
