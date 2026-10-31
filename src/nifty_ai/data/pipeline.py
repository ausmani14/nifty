"""Historical data ingestion pipeline orchestrator for NIFTY AI.

Coordinates the end-to-end data ingestion workflow:
Raw Provider Fetch -> Raw Preservation -> Normalization -> Validation -> Processed Storage.
"""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from nifty_ai.data.providers.base import BaseMarketDataProvider
from nifty_ai.data.providers.registry import default_registry
from nifty_ai.data.providers.yahoo import YahooFinanceMarketProvider
from nifty_ai.data.schema import NormalizedMarketRecord
from nifty_ai.data.storage import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    save_processed_market_data,
    save_raw_market_data,
)
from nifty_ai.data.validation import MarketDataValidator, ValidationResult

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


@dataclass
class IngestionResult:
    """Result summary of a historical ingestion run."""
    success: bool
    symbol: str
    provider_name: str
    start_date: Optional[date]
    end_date: Optional[date]
    raw_path: Optional[Path]
    processed_path: Optional[Path]
    record_count: int
    raw_stats: Dict[str, Any]
    validation_result: Optional[ValidationResult]
    metadata: Dict[str, Any]


class HistoricalIngestionPipeline:
    """End-to-end ingestion pipeline for historical index market data."""

    def __init__(
        self,
        provider: Optional[BaseMarketDataProvider] = None,
        validator: Optional[MarketDataValidator] = None,
    ) -> None:
        self.provider = provider or default_registry.get_market_provider("yahoo_finance")
        self.validator = validator or MarketDataValidator()

    def run(
        self,
        symbol: str = "NIFTY 50",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        save_raw: bool = True,
        save_processed: bool = True,
        output_dir: Optional[Path] = None,
    ) -> IngestionResult:
        """Execute the ingestion workflow from remote source to validated storage."""
        # 1. Fetch raw payload and retrieval timestamp
        if not isinstance(self.provider, YahooFinanceMarketProvider):
            raise NotImplementedError(
                f"Provider {self.provider.name} does not support raw payload extraction."
            )

        raw_text, retrieval_dt = self.provider.fetch_raw_payload(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        effective_start = start_date or self.provider.EARLIEST_NIFTY_DATE
        effective_end = end_date or datetime.now(MARKET_TIMEZONE).date()

        # 2. Raw preservation
        raw_path: Optional[Path] = None
        raw_meta: Dict[str, Any] = {}
        if save_raw:
            raw_path, raw_meta = save_raw_market_data(
                raw_content=raw_text,
                provider=self.provider.name,
                symbol=symbol,
                start_date=effective_start,
                end_date=effective_end,
                retrieval_timestamp=retrieval_dt,
            )

        # 3. Provider normalization
        records, raw_stats = self.provider.parse_chart_response(
            raw_json_str=raw_text,
            canonical_symbol=symbol,
            retrieval_timestamp=retrieval_dt,
        )

        if not records:
            return IngestionResult(
                success=False,
                symbol=symbol,
                provider_name=self.provider.name,
                start_date=effective_start,
                end_date=effective_end,
                raw_path=raw_path,
                processed_path=None,
                record_count=0,
                raw_stats=raw_stats,
                validation_result=None,
                metadata={"error": "No records parsed from raw payload."},
            )

        # 4. Validation
        validation_result = self.validator.validate(records)
        if not validation_result.is_valid:
            return IngestionResult(
                success=False,
                symbol=symbol,
                provider_name=self.provider.name,
                start_date=records[0].trading_date,
                end_date=records[-1].trading_date,
                raw_path=raw_path,
                processed_path=None,
                record_count=len(records),
                raw_stats=raw_stats,
                validation_result=validation_result,
                metadata={"validation_errors": [str(e) for e in validation_result.errors]},
            )

        # 5. Processed storage
        processed_path: Optional[Path] = None
        processed_meta: Dict[str, Any] = {}
        if save_processed:
            proc_dir = output_dir or PROCESSED_DATA_DIR
            safe_sym = symbol.replace("^", "").replace(" ", "_").lower()
            target_file = proc_dir / f"{safe_sym}_daily.csv"
            processed_path, processed_meta = save_processed_market_data(
                records=records,
                output_path=target_file,
                extra_metadata={
                    "raw_file": str(raw_path.name) if raw_path else None,
                    "raw_sha256": raw_meta.get("sha256") if raw_meta else None,
                    "raw_stats": raw_stats,
                },
            )

        return IngestionResult(
            success=True,
            symbol=symbol,
            provider_name=self.provider.name,
            start_date=records[0].trading_date,
            end_date=records[-1].trading_date,
            raw_path=raw_path,
            processed_path=processed_path,
            record_count=len(records),
            raw_stats=raw_stats,
            validation_result=validation_result,
            metadata=processed_meta,
        )


__all__ = ["HistoricalIngestionPipeline", "IngestionResult"]
