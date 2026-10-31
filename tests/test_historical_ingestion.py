"""Offline unit tests for Phase 2 historical data ingestion pipeline.

All tests utilize deterministic in-memory fixtures. No network or external API access
is performed during test suite execution.
"""

from datetime import date, datetime, time, timezone
import json
from pathlib import Path
import pytest

from nifty_ai.data import (
    MARKET_TIMEZONE,
    DataFrequency,
    HistoricalIngestionPipeline,
    MarketDataValidator,
    NormalizedMarketRecord,
    ProvenanceMetadata,
    ProviderError,
    ProviderTier,
    YahooFinanceMarketProvider,
    load_processed_market_data,
    save_processed_market_data,
    save_raw_market_data,
)

# Deterministic test fixture representing a valid Yahoo Finance chart API response
SAMPLE_VALID_CHART_JSON = json.dumps({
    "chart": {
        "result": [
            {
                "meta": {
                    "currency": "INR",
                    "symbol": "^NSEI",
                    "exchangeName": "NSI",
                    "fullExchangeName": "NSE",
                    "exchangeTimezoneName": "Asia/Kolkata",
                },
                "timestamp": [1725249300, 1725335700, 1725422100],  # Sept 2, 3, 4, 2024
                "indicators": {
                    "quote": [
                        {
                            "open": [25300.0, 25350.0, 25400.0],
                            "high": [25380.0, 25420.0, 25450.0],
                            "low": [25250.0, 25300.0, 25350.0],
                            "close": [25340.0, 25390.0, 25430.0],
                            "volume": [200000, 210000, 220000],
                        }
                    ]
                },
            }
        ],
        "error": None,
    }
})

# Test fixture with an exchange-closed holiday row containing nulls
SAMPLE_CHART_WITH_NULLS_JSON = json.dumps({
    "chart": {
        "result": [
            {
                "meta": {"symbol": "^NSEI", "exchangeTimezoneName": "Asia/Kolkata"},
                "timestamp": [1725249300, 1725335700],
                "indicators": {
                    "quote": [
                        {
                            "open": [25300.0, None],
                            "high": [25380.0, None],
                            "low": [25250.0, None],
                            "close": [25340.0, None],
                            "volume": [200000, None],
                        }
                    ]
                },
            }
        ],
        "error": None,
    }
})


def test_parse_chart_response_valid():
    """Verify parsing of valid chart JSON into NormalizedMarketRecord instances."""
    provider = YahooFinanceMarketProvider()
    retrieval_dt = datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

    records, stats = provider.parse_chart_response(
        raw_json_str=SAMPLE_VALID_CHART_JSON,
        canonical_symbol="NIFTY 50",
        retrieval_timestamp=retrieval_dt,
    )

    assert len(records) == 3
    assert stats["raw_count"] == 3
    assert stats["valid_count"] == 3
    assert stats["null_count"] == 0

    first = records[0]
    assert first.symbol == "NIFTY 50"
    assert first.open == 25300.0
    assert first.high == 25380.0
    assert first.low == 25250.0
    assert first.close == 25340.0
    assert first.volume == 200000.0
    assert first.status == "finalized"

    # Verify market close standardization (15:30:00 IST) to eliminate look-ahead bias
    assert first.timestamp == datetime.combine(first.trading_date, time(15, 30, 0), tzinfo=MARKET_TIMEZONE)
    assert first.provenance.retrieval_timestamp == retrieval_dt
    assert first.provenance.provider == "yahoo_finance"


def test_parse_chart_response_omits_null_sessions():
    """Verify that null sessions are not fabricated and are tracked in diagnostic stats."""
    provider = YahooFinanceMarketProvider()
    records, stats = provider.parse_chart_response(
        raw_json_str=SAMPLE_CHART_WITH_NULLS_JSON,
        canonical_symbol="NIFTY 50",
    )

    assert len(records) == 1
    assert stats["raw_count"] == 2
    assert stats["valid_count"] == 1
    assert stats["null_count"] == 1
    assert len(stats["null_dates"]) == 1


def test_parse_chart_response_error_handling():
    """Verify error handling on malformed JSON or API error objects."""
    provider = YahooFinanceMarketProvider()

    # 1. Malformed JSON
    with pytest.raises(ProviderError, match="Malformed JSON"):
        provider.parse_chart_response("NOT_VALID_JSON", "NIFTY 50")

    # 2. API error payload
    error_payload = json.dumps({
        "chart": {
            "result": None,
            "error": {"code": "Not Found", "description": "No data found for symbol"},
        }
    })
    with pytest.raises(ProviderError, match="Yahoo Finance API error"):
        provider.parse_chart_response(error_payload, "NIFTY 50")


def test_storage_raw_and_processed_roundtrip(tmp_path: Path):
    """Verify saving raw payload and round-trip serialization of processed CSV."""
    provider = YahooFinanceMarketProvider()
    records, _ = provider.parse_chart_response(
        raw_json_str=SAMPLE_VALID_CHART_JSON,
        canonical_symbol="NIFTY 50",
    )

    # 1. Save raw
    raw_path, raw_meta = save_raw_market_data(
        raw_content=SAMPLE_VALID_CHART_JSON,
        provider="yahoo_finance",
        symbol="NIFTY 50",
        start_date=date(2024, 9, 2),
        end_date=date(2024, 9, 4),
        destination_dir=tmp_path / "raw",
    )
    assert raw_path.is_file()
    assert (tmp_path / "raw" / f"{raw_path.name}.meta.json").is_file()
    assert "sha256" in raw_meta

    # 2. Save processed CSV
    proc_target = tmp_path / "processed" / "nifty50_daily.csv"
    saved_path, proc_meta = save_processed_market_data(
        records=records,
        output_path=proc_target,
    )
    assert saved_path.is_file()
    assert (tmp_path / "processed" / "nifty50_daily.csv.meta.json").is_file()
    assert proc_meta["row_count"] == 3

    # 3. Load processed CSV back and compare
    loaded_records = load_processed_market_data(saved_path)
    assert len(loaded_records) == 3
    for orig, loaded in zip(records, loaded_records):
        assert orig.trading_date == loaded.trading_date
        assert orig.timestamp == loaded.timestamp
        assert orig.symbol == loaded.symbol
        assert orig.open == loaded.open
        assert orig.high == loaded.high
        assert orig.low == loaded.low
        assert orig.close == loaded.close
        assert orig.volume == loaded.volume
        assert orig.provenance.provider == loaded.provenance.provider


def test_pipeline_offline_execution(tmp_path: Path):
    """Verify HistoricalIngestionPipeline workflow using an offline mocked provider."""
    class MockYahooProvider(YahooFinanceMarketProvider):
        def fetch_raw_payload(self, symbol, start_date=None, end_date=None):
            return SAMPLE_VALID_CHART_JSON, datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc)

    mock_provider = MockYahooProvider()
    pipeline = HistoricalIngestionPipeline(provider=mock_provider)

    result = pipeline.run(
        symbol="NIFTY 50",
        start_date=date(2024, 9, 2),
        end_date=date(2024, 9, 4),
        save_raw=True,
        save_processed=True,
        output_dir=tmp_path,
    )

    assert result.success is True
    assert result.record_count == 3
    assert result.processed_path is not None
    assert result.processed_path.is_file()
    assert result.validation_result is not None
    assert result.validation_result.is_valid is True


def test_invalid_date_range_validation():
    """Verify that start_date > end_date raises a ValueError without network activity."""
    provider = YahooFinanceMarketProvider()
    with pytest.raises(ValueError, match="start_date.*cannot be after end_date"):
        provider.fetch_raw_payload(
            symbol="NIFTY 50",
            start_date=date(2026, 9, 10),
            end_date=date(2026, 9, 1),
        )
