"""CLI script for historical index market data ingestion in NIFTY AI.

Usage:
    python scripts/ingest_historical_data.py [--provider yahoo_finance] [--symbol "NIFTY 50"]
                                            [--start-date 2007-09-17] [--end-date 2026-09-04]
                                            [--output-dir data/processed]
"""

import argparse
from datetime import date
from pathlib import Path
import sys

from nifty_ai.data import (
    HistoricalIngestionPipeline,
    default_registry,
)
from nifty_ai.utils import setup_logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NIFTY AI Historical Market Data Ingestion Tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="yahoo_finance",
        help="Target data provider identifier (must be registered in ProviderRegistry)",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="NIFTY 50",
        help="Target index or equity symbol",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Historical window start date (YYYY-MM-DD). Defaults to provider earliest date.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Historical window end date (YYYY-MM-DD). Defaults to current date.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Custom destination directory for processed files.",
    )
    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="Disable persisting raw source payload to data/raw/.",
    )
    return parser.parse_args()


def main() -> int:
    logger = setup_logger("nifty_ai.ingest")
    args = parse_args()

    start_d: Optional[date] = None
    end_d: Optional[date] = None

    if args.start_date:
        try:
            start_d = date.fromisoformat(args.start_date)
        except ValueError:
            logger.error("Invalid --start-date format. Expected YYYY-MM-DD.")
            return 1

    if args.end_date:
        try:
            end_d = date.fromisoformat(args.end_date)
        except ValueError:
            logger.error("Invalid --end-date format. Expected YYYY-MM-DD.")
            return 1

    out_dir = Path(args.output_dir) if args.output_dir else None

    logger.info("==================================================================")
    logger.info("Starting NIFTY AI Historical Ingestion Pipeline")
    logger.info("Provider: %s | Symbol: %s", args.provider, args.symbol)
    logger.info("Start: %s | End: %s", start_d or "Earliest", end_d or "Latest")
    logger.info("==================================================================")

    try:
        provider = default_registry.get_market_provider(args.provider)
    except KeyError as exc:
        logger.error("Provider resolution error: %s", exc)
        return 1

    pipeline = HistoricalIngestionPipeline(provider=provider)

    try:
        result = pipeline.run(
            symbol=args.symbol,
            start_date=start_d,
            end_date=end_d,
            save_raw=not args.no_raw,
            save_processed=True,
            output_dir=out_dir,
        )
    except Exception as exc:
        logger.error("Ingestion failed with exception: %s", exc, exc_info=True)
        return 1

    if not result.success:
        logger.error("Ingestion pipeline failed.")
        if result.validation_result and not result.validation_result.is_valid:
            logger.error(
                "Validation issues encountered (%d errors):",
                result.validation_result.error_count,
            )
            for err in result.validation_result.errors[:10]:
                logger.error("  - [%s] %s", err.rule_name, err.message)
        return 1

    logger.info("Ingestion completed successfully!")
    logger.info("Record Count       : %d daily bars", result.record_count)
    logger.info("Date Range Covered : %s to %s", result.start_date, result.end_date)
    if result.raw_path:
        logger.info("Raw Payload Saved  : %s", result.raw_path)
    if result.processed_path:
        logger.info("Processed Dataset  : %s", result.processed_path)
        logger.info("Dataset SHA-256    : %s", result.metadata.get("sha256"))
    logger.info(
        "Raw Null Sessions  : %d omitted (documented in raw metadata)",
        result.raw_stats.get("null_count", 0),
    )
    logger.info("==================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
