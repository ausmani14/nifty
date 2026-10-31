"""CLI script for auditing dataset quality and generating machine-readable diagnostics.

Usage:
    python scripts/run_data_audit.py [--file data/processed/nifty_50_daily.csv]
                                    [--output data/processed/quality_report.json]
"""

import argparse
from pathlib import Path
import sys

from nifty_ai.data import (
    DataQualityAuditor,
    compute_file_sha256,
    load_processed_market_data,
    save_quality_report,
)
from nifty_ai.utils import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NIFTY AI Historical Dataset Quality Auditor",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--file",
        type=str,
        default="data/processed/nifty_50_daily.csv",
        help="Path to processed CSV dataset to audit.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/quality_report.json",
        help="Path where machine-readable JSON quality report should be saved.",
    )
    return parser.parse_args()


def main() -> int:
    logger = setup_logger("nifty_ai.quality")
    args = parse_args()

    data_file = Path(args.file)
    output_file = Path(args.output)

    if not data_file.is_file():
        logger.error("Dataset file not found: %s", data_file)
        return 1

    logger.info("==================================================================")
    logger.info("Executing NIFTY AI Data Quality & Integrity Audit")
    logger.info("Auditing File: %s", data_file)
    logger.info("==================================================================")

    records = load_processed_market_data(data_file)
    dataset_sha256 = compute_file_sha256(data_file)

    auditor = DataQualityAuditor()
    report = auditor.audit(
        records=records,
        dataset_name=data_file.stem,
        file_path=str(data_file),
        dataset_sha256=dataset_sha256,
    )

    save_quality_report(report, output_file)

    logger.info("Audit Completed Successfully!")
    logger.info("Overall Status     : %s", report.overall_status)
    logger.info("Total Rows Audited : %d", report.row_count)
    logger.info("Date Range Covered : %s to %s", report.start_date, report.end_date)
    logger.info("Dataset SHA-256    : %s", report.dataset_sha256)
    logger.info("Audit Report Saved : %s", output_file)
    logger.info("------------------------------------------------------------------")
    logger.info("Checks Summary:")
    for check in report.checks:
        logger.info("  [%-7s] %-30s : %s", check.status, check.name, check.message)
    logger.info("------------------------------------------------------------------")
    logger.info(
        "Return Stats: Min: %.2f%% (%s) | Max: %.2f%% (%s) | Mean: %.4f%%",
        report.return_statistics.min_return * 100,
        report.return_statistics.min_return_date,
        report.return_statistics.max_return * 100,
        report.return_statistics.max_return_date,
        report.return_statistics.mean_return * 100,
    )
    logger.info(
        "Volume Stats: %d zero-volume rows (%.2f%%) | Reliability: %s",
        report.volume_audit.zero_volume_count,
        report.volume_audit.zero_volume_pct,
        report.volume_audit.reliability_assessment,
    )
    logger.info("==================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
