"""Unit tests for Phase 1 Data Source Architecture."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo
import pytest

from nifty_ai.config import get_providers_config
from nifty_ai.data import (
    MARKET_TIMEZONE,
    BaseMarketDataProvider,
    DataFrequency,
    MarketDataValidator,
    NormalizedMacroRecord,
    NormalizedMarketRecord,
    NormalizedNewsRecord,
    ProvenanceMetadata,
    ProviderNotAvailableError,
    ProviderRegistry,
    ProviderStatus,
    ProviderTier,
    SnapshotCutoff,
    SnapshotType,
    ValidationSeverity,
    create_snapshot_cutoff,
    default_registry,
)


def _make_sample_provenance() -> ProvenanceMetadata:
    return ProvenanceMetadata(
        provider="test_provider",
        source_identifier="TEST_SYMBOL",
        retrieval_timestamp=datetime(2026, 9, 4, 16, 0, 0, tzinfo=timezone.utc),
        timezone="Asia/Kolkata",
        data_frequency=DataFrequency.DAILY,
        tier=ProviderTier.FREE,
    )


def test_provenance_and_market_schema():
    """Verify NormalizedMarketRecord creation and validation checks."""
    provenance = _make_sample_provenance()
    record_dt = datetime(2026, 9, 4, 15, 30, 0, tzinfo=MARKET_TIMEZONE)

    record = NormalizedMarketRecord(
        timestamp=record_dt,
        trading_date=date(2026, 9, 4),
        symbol="NIFTY 50",
        open=24500.0,
        high=24600.0,
        low=24450.0,
        close=24580.0,
        volume=150000.0,
        provenance=provenance,
    )

    assert record.symbol == "NIFTY 50"
    assert record.close == 24580.0
    assert record.provenance.provider == "test_provider"
    assert record.status == "finalized"

    # Dataclass should be frozen
    with pytest.raises(Exception):
        record.close = 25000.0  # type: ignore


def test_schema_requires_timezone_awareness():
    """Verify that naive timestamps are rejected during initialization."""
    provenance = _make_sample_provenance()
    naive_dt = datetime(2026, 9, 4, 15, 30, 0)  # No tzinfo

    with pytest.raises(ValueError, match="timezone-aware"):
        NormalizedMarketRecord(
            timestamp=naive_dt,
            trading_date=date(2026, 9, 4),
            symbol="NIFTY 50",
            open=24500.0,
            high=24600.0,
            low=24450.0,
            close=24580.0,
            provenance=provenance,
        )


def test_macro_and_news_schema():
    """Verify NormalizedMacroRecord and NormalizedNewsRecord initialization and bounds."""
    provenance = _make_sample_provenance()
    ts = datetime(2026, 9, 4, 15, 30, 0, tzinfo=MARKET_TIMEZONE)

    macro_rec = NormalizedMacroRecord(
        timestamp=ts,
        indicator_name="INDIA_VIX",
        value=14.25,
        provenance=provenance,
        unit="index_points",
    )
    assert macro_rec.indicator_name == "INDIA_VIX"
    assert macro_rec.value == 14.25

    news_rec = NormalizedNewsRecord(
        article_id="art_001",
        headline="RBI keeps repo rate unchanged at 6.5%",
        publication_timestamp=datetime(2026, 9, 4, 10, 0, 0, tzinfo=MARKET_TIMEZONE),
        provenance=provenance,
        entities=["RBI"],
        sentiment_score=0.25,
        importance=4,
    )
    assert news_rec.article_id == "art_001"
    assert news_rec.sentiment_score == 0.25

    # Invalid sentiment score > 1.0
    with pytest.raises(ValueError, match="sentiment_score"):
        NormalizedNewsRecord(
            article_id="art_002",
            headline="Headline",
            publication_timestamp=ts,
            provenance=provenance,
            sentiment_score=1.5,
        )


def test_snapshot_cutoffs_and_temporal_filtering():
    """Verify snapshot cutoff generation and information cutoff enforcement."""
    target_date = date(2026, 9, 5)
    reference_date = date(2026, 9, 4)

    # 1. Snapshot A (15:40 IST execution, 15:30 IST cutoff on reference_date)
    cutoff_a = create_snapshot_cutoff(
        snapshot_type=SnapshotType.SNAPSHOT_1540,
        target_date=target_date,
        reference_date=reference_date,
    )
    assert cutoff_a.cutoff_timestamp == datetime(2026, 9, 4, 15, 30, 0, tzinfo=MARKET_TIMEZONE)
    assert cutoff_a.execution_timestamp == datetime(2026, 9, 4, 15, 40, 0, tzinfo=MARKET_TIMEZONE)

    # 2. Snapshot B (08:50 IST execution, 08:50 IST cutoff on target_date)
    cutoff_b = create_snapshot_cutoff(
        snapshot_type=SnapshotType.SNAPSHOT_0850,
        target_date=target_date,
    )
    assert cutoff_b.cutoff_timestamp == datetime(2026, 9, 5, 8, 50, 0, tzinfo=MARKET_TIMEZONE)
    assert cutoff_b.execution_timestamp == datetime(2026, 9, 5, 8, 50, 0, tzinfo=MARKET_TIMEZONE)

    # Test filtering logic for Snapshot A
    event_valid = datetime(2026, 9, 4, 15, 29, 0, tzinfo=MARKET_TIMEZONE)
    event_at_cutoff = datetime(2026, 9, 4, 15, 30, 0, tzinfo=MARKET_TIMEZONE)
    event_future = datetime(2026, 9, 4, 15, 31, 0, tzinfo=MARKET_TIMEZONE)

    assert cutoff_a.is_valid_information(event_valid) is True
    assert cutoff_a.is_valid_information(event_at_cutoff) is True
    assert cutoff_a.is_valid_information(event_future) is False

    timestamps = [event_valid, event_at_cutoff, event_future]
    filtered = cutoff_a.filter_records(timestamps, lambda t: t)
    assert filtered == [event_valid, event_at_cutoff]


def test_provider_registry_and_stubs():
    """Verify provider registration, tiering, status, and stub safety."""
    # Verify default registry contents
    nse = default_registry.get_market_provider("nse_official")
    assert nse.tier == ProviderTier.OFFICIAL
    assert nse.status == ProviderStatus.REFERENCE
    assert "NIFTY 50" in nse.get_supported_symbols()

    yf = default_registry.get_market_provider("yahoo_finance")
    assert yf.tier == ProviderTier.FREE
    assert yf.status == ProviderStatus.DEVELOPMENT

    # Calling fetch on reference stub must cleanly raise ProviderNotAvailableError
    with pytest.raises(ProviderNotAvailableError):
        nse.fetch_daily_ohlcv("NIFTY 50", date(2026, 1, 1), date(2026, 1, 10))

    # Yahoo Finance development provider is active in Phase 2
    assert yf.is_available() is True
    assert "^NSEI" in yf.get_supported_symbols()

    # Custom provider registration
    class MockProvider(BaseMarketDataProvider):
        def __init__(self):
            super().__init__("mock_p", ProviderTier.FREE, ProviderStatus.DEVELOPMENT)

        def is_available(self):
            return True

        def get_supported_symbols(self):
            return ["TEST"]

        def fetch_daily_ohlcv(self, symbol, start_date, end_date):
            return []

    custom_registry = ProviderRegistry()
    mock_p = MockProvider()
    custom_registry.register_market_provider(mock_p)
    assert custom_registry.get_market_provider("mock_p") == mock_p

    with pytest.raises(KeyError):
        custom_registry.get_market_provider("unknown_provider")


def test_market_data_validator_valid_and_invalid():
    """Verify MarketDataValidator checks for OHLC boundaries, positivity, and duplicates."""
    provenance = _make_sample_provenance()
    validator = MarketDataValidator()

    # Valid series
    rec1 = NormalizedMarketRecord(
        timestamp=datetime(2026, 9, 3, 15, 30, 0, tzinfo=MARKET_TIMEZONE),
        trading_date=date(2026, 9, 3),
        symbol="NIFTY 50",
        open=24400.0,
        high=24550.0,
        low=24380.0,
        close=24500.0,
        provenance=provenance,
    )
    rec2 = NormalizedMarketRecord(
        timestamp=datetime(2026, 9, 4, 15, 30, 0, tzinfo=MARKET_TIMEZONE),
        trading_date=date(2026, 9, 4),
        symbol="NIFTY 50",
        open=24500.0,
        high=24620.0,
        low=24470.0,
        close=24600.0,
        provenance=provenance,
    )

    valid_result = validator.validate([rec1, rec2])
    assert valid_result.is_valid is True
    assert valid_result.error_count == 0

    # Inverted High < Low
    bad_rec_inverted = NormalizedMarketRecord(
        timestamp=datetime(2026, 9, 5, 15, 30, 0, tzinfo=MARKET_TIMEZONE),
        trading_date=date(2026, 9, 5),
        symbol="NIFTY 50",
        open=24500.0,
        high=24400.0,  # High less than Low
        low=24600.0,
        close=24500.0,
        provenance=provenance,
    )
    inv_result = validator.validate([bad_rec_inverted])
    assert inv_result.is_valid is False
    assert any(i.rule_name == "HIGH_GTE_LOW" for i in inv_result.errors)

    # Duplicate timestamp
    dup_result = validator.validate([rec1, rec1])
    assert dup_result.is_valid is False
    assert any(i.rule_name == "DUPLICATE_TIMESTAMP" for i in dup_result.errors)

    # Out of order
    out_of_order_result = validator.validate([rec2, rec1])
    assert out_of_order_result.is_valid is False
    assert any(i.rule_name == "CHRONOLOGICAL_ORDER" for i in out_of_order_result.errors)


def test_providers_yaml_configuration():
    """Verify loading of configs/providers.yaml without any secrets."""
    config = get_providers_config()
    assert "providers" in config
    providers = config["providers"]
    assert "market_data" in providers
    assert "macro_data" in providers
    assert "news_data" in providers

    market_data = providers["market_data"]
    assert market_data["active_provider"] == "yahoo_finance"
    assert "nse_official" in market_data["available"]
    assert "yahoo_finance" in market_data["available"]

    # Verify no raw secret values are present in the config
    config_str = str(config)
    for forbidden in ["password", "secret_key", "sk-", "ghp_"]:
        assert forbidden not in config_str.lower()


def test_provenance_validation_edge_cases():
    """Verify input validation rules on ProvenanceMetadata."""
    now_utc = datetime.now(timezone.utc)

    # Empty provider
    with pytest.raises(ValueError, match="provider must not be empty"):
        ProvenanceMetadata(
            provider="",
            source_identifier="SYM",
            retrieval_timestamp=now_utc,
        )

    # Empty source identifier
    with pytest.raises(ValueError, match="source_identifier must not be empty"):
        ProvenanceMetadata(
            provider="test",
            source_identifier="",
            retrieval_timestamp=now_utc,
        )

    # Naive retrieval timestamp
    with pytest.raises(ValueError, match="retrieval_timestamp must be timezone-aware"):
        ProvenanceMetadata(
            provider="test",
            source_identifier="SYM",
            retrieval_timestamp=datetime.now(),
        )

    # Naive source timestamp
    with pytest.raises(ValueError, match="source_timestamp must be timezone-aware"):
        ProvenanceMetadata(
            provider="test",
            source_identifier="SYM",
            retrieval_timestamp=now_utc,
            source_timestamp=datetime.now(),
        )


def test_schema_string_and_range_validations():
    """Verify schema bounds on market, macro, and news records."""
    provenance = _make_sample_provenance()
    ts = datetime(2026, 9, 4, 15, 30, 0, tzinfo=MARKET_TIMEZONE)

    # Empty symbol in market record
    with pytest.raises(ValueError, match="Symbol must not be empty"):
        NormalizedMarketRecord(
            timestamp=ts,
            trading_date=date(2026, 9, 4),
            symbol="",
            open=100.0,
            high=110.0,
            low=90.0,
            close=105.0,
            provenance=provenance,
        )

    # Empty indicator in macro record
    with pytest.raises(ValueError, match="Indicator name must not be empty"):
        NormalizedMacroRecord(
            timestamp=ts,
            indicator_name="",
            value=10.0,
            provenance=provenance,
        )

    # Empty headline in news record
    with pytest.raises(ValueError, match="News headline must not be empty"):
        NormalizedNewsRecord(
            article_id="1",
            headline="",
            publication_timestamp=ts,
            provenance=provenance,
        )

    # Importance out of range
    with pytest.raises(ValueError, match="importance must be on a scale of 1 to 5"):
        NormalizedNewsRecord(
            article_id="1",
            headline="Test",
            publication_timestamp=ts,
            provenance=provenance,
            importance=6,
        )


def test_snapshot_cutoff_validations():
    """Verify SnapshotCutoff input constraints."""
    target = date(2026, 9, 5)

    # SNAPSHOT_1540 requires reference_date
    with pytest.raises(ValueError, match="reference_date.*must be explicitly provided"):
        create_snapshot_cutoff(
            snapshot_type=SnapshotType.SNAPSHOT_1540,
            target_date=target,
            reference_date=None,
        )

    # Invalid timestamp comparison with naive datetime
    cutoff = create_snapshot_cutoff(
        snapshot_type=SnapshotType.SNAPSHOT_0850,
        target_date=target,
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        cutoff.is_valid_information(datetime(2026, 9, 5, 8, 0, 0))  # naive


def test_market_data_validator_comprehensive():
    """Verify detailed validation rules for prices, bounds, and volumes."""
    provenance = _make_sample_provenance()
    validator = MarketDataValidator()

    ts = datetime(2026, 9, 4, 15, 30, 0, tzinfo=MARKET_TIMEZONE)

    # 1. Non-positive price
    rec_zero_price = NormalizedMarketRecord(
        timestamp=ts,
        trading_date=date(2026, 9, 4),
        symbol="NIFTY 50",
        open=0.0,  # zero
        high=100.0,
        low=0.0,
        close=50.0,
        provenance=provenance,
    )
    res1 = validator.validate([rec_zero_price])
    assert any(i.rule_name == "POSITIVE_PRICE" for i in res1.errors)

    # 2. Open outside [Low, High]
    rec_bad_open = NormalizedMarketRecord(
        timestamp=ts,
        trading_date=date(2026, 9, 4),
        symbol="NIFTY 50",
        open=110.0,  # Open > High
        high=100.0,
        low=50.0,
        close=75.0,
        provenance=provenance,
    )
    res2 = validator.validate([rec_bad_open])
    assert any(i.rule_name == "OPEN_WITHIN_RANGE" for i in res2.errors)

    # 3. Close outside [Low, High]
    rec_bad_close = NormalizedMarketRecord(
        timestamp=ts,
        trading_date=date(2026, 9, 4),
        symbol="NIFTY 50",
        open=75.0,
        high=100.0,
        low=50.0,
        close=40.0,  # Close < Low
        provenance=provenance,
    )
    res3 = validator.validate([rec_bad_close])
    assert any(i.rule_name == "CLOSE_WITHIN_RANGE" for i in res3.errors)

    # 4. Negative volume
    rec_neg_vol = NormalizedMarketRecord(
        timestamp=ts,
        trading_date=date(2026, 9, 4),
        symbol="NIFTY 50",
        open=75.0,
        high=100.0,
        low=50.0,
        close=80.0,
        volume=-500.0,
        provenance=provenance,
    )
    res4 = validator.validate([rec_neg_vol])
    assert any(i.rule_name == "NON_NEGATIVE_VOLUME" for i in res4.errors)

    # 5. Empty records list returns valid
    assert validator.validate([]).is_valid is True

