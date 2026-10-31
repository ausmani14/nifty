"""Pipeline orchestrator for price feature dataset generation in NIFTY AI.

Coordinates loading of validated processed market data, execution of PriceFeatureEngine,
and atomic persistence of feature matrices with metadata manifests.
"""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.storage import (
    compute_file_sha256,
    load_processed_market_data,
)
from nifty_ai.features.engine import PriceFeatureEngine
from nifty_ai.features.registry import FeatureRegistry, default_feature_registry

FEATURES_DIR = PROJECT_ROOT / "data" / "features"


class FeaturePipeline:
    """Orchestrates the feature transformation from processed market data to feature store."""

    def __init__(
        self,
        engine: Optional[PriceFeatureEngine] = None,
        registry: Optional[FeatureRegistry] = None,
    ) -> None:
        self.registry = registry or default_feature_registry
        self.engine = engine or PriceFeatureEngine(registry=self.registry)

    def run(
        self,
        input_csv_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
    ) -> Tuple[Path, Path, Dict[str, Any]]:
        """Run feature extraction and persist both full and warm-up trimmed datasets.

        Returns:
            Tuple of (full_features_path, clean_features_path, metadata_dict).
        """
        in_path = input_csv_path or (PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv")
        out_dir = output_dir or FEATURES_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        if not in_path.is_file():
            raise FileNotFoundError(f"Processed market data file not found: {in_path}")

        records = load_processed_market_data(in_path)
        source_sha256 = compute_file_sha256(in_path)

        # Compute full feature matrix
        all_rows, meta = self.engine.compute_features(records, trim_warmup=False)

        # 1. Save full feature dataset
        full_file = out_dir / "nifty50_features.csv"
        self._write_csv(all_rows, full_file)
        full_sha256 = compute_file_sha256(full_file)

        # 2. Save warm-up trimmed clean dataset
        max_lookback = self.registry.max_lookback
        clean_rows = all_rows[max_lookback:]
        clean_file = out_dir / "nifty50_features_clean.csv"
        self._write_csv(clean_rows, clean_file)
        clean_sha256 = compute_file_sha256(clean_file)

        # 3. Create metadata manifest
        metadata: Dict[str, Any] = {
            "source_dataset": str(in_path.name),
            "source_sha256": source_sha256,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_input_records": len(records),
            "full_features_file": full_file.name,
            "full_features_rows": len(all_rows),
            "full_features_sha256": full_sha256,
            "clean_features_file": clean_file.name,
            "clean_features_rows": len(clean_rows),
            "clean_features_sha256": clean_sha256,
            "warmup_rows_excluded": max_lookback,
            "start_date": records[0].trading_date.isoformat(),
            "end_date": records[-1].trading_date.isoformat(),
            "clean_start_date": clean_rows[0]["trading_date"] if clean_rows else None,
            "clean_end_date": clean_rows[-1]["trading_date"] if clean_rows else None,
            "feature_count": meta["feature_count"],
            "feature_names": meta["feature_names"],
            "volume_excluded": True,
            "schema_version": "1.0.0",
        }

        meta_file = out_dir / "nifty50_features.meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return full_file, clean_file, metadata

    def _write_csv(self, rows: List[Dict[str, Any]], target_path: Path) -> None:
        """Write feature dictionary rows to a deterministic CSV file."""
        if not rows:
            return
        fieldnames = list(rows[0].keys())
        with open(target_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                formatted_row = {}
                for k, v in row.items():
                    if v is None:
                        formatted_row[k] = ""
                    elif isinstance(v, float):
                        formatted_row[k] = f"{v:.6f}"
                    else:
                        formatted_row[k] = str(v)
                writer.writerow(formatted_row)


__all__ = ["FEATURES_DIR", "FeaturePipeline"]
