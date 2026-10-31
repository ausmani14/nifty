"""CLI script for generating price-based features from processed market data.

Usage:
    python scripts/generate_features.py [--input data/processed/nifty_50_daily.csv]
                                        [--output-dir data/features]
"""

import argparse
from pathlib import Path
import sys

from nifty_ai.features import FeaturePipeline
from nifty_ai.utils import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NIFTY AI Price Feature Generation Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/processed/nifty_50_daily.csv",
        help="Path to validated processed market data CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/features",
        help="Destination directory for feature datasets and manifests.",
    )
    return parser.parse_args()


def main() -> int:
    logger = setup_logger("nifty_ai.features")
    args = parse_args()

    in_file = Path(args.input)
    out_dir = Path(args.output_dir)

    if not in_file.is_file():
        logger.error("Input market dataset not found: %s", in_file)
        return 1

    logger.info("==================================================================")
    logger.info("Executing NIFTY AI Price Feature Generation Pipeline")
    logger.info("Input Dataset : %s", in_file)
    logger.info("Output Directory: %s", out_dir)
    logger.info("==================================================================")

    pipeline = FeaturePipeline()
    try:
        full_path, clean_path, metadata = pipeline.run(
            input_csv_path=in_file,
            output_dir=out_dir,
        )
    except Exception as exc:
        logger.error("Feature generation failed: %s", exc, exc_info=True)
        return 1

    logger.info("Feature Generation Completed Successfully!")
    logger.info("Total Features Generated : %d features", metadata["feature_count"])
    logger.info("Full Dataset Path        : %s", full_path)
    logger.info("Full Dataset Rows        : %d rows (%s to %s)", metadata["full_features_rows"], metadata["start_date"], metadata["end_date"])
    logger.info("Warm-up Lookback         : %d initial rows excluded for clean matrix", metadata["warmup_rows_excluded"])
    logger.info("Clean Dataset Path       : %s", clean_path)
    logger.info("Clean Dataset Rows       : %d rows (%s to %s)", metadata["clean_features_rows"], metadata["clean_start_date"], metadata["clean_end_date"])
    logger.info("Clean Dataset SHA-256    : %s", metadata["clean_features_sha256"])
    logger.info("Volume Included          : %s (Quarantined per Phase 3 Audit)", metadata["volume_excluded"] is False)
    logger.info("==================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
