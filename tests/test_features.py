"""Offline unit and leakage prevention tests for Phase 4 price feature engineering."""

from datetime import date, datetime, time, timezone
import math
from pathlib import Path
import pytest

from nifty_ai.data import (
    MARKET_TIMEZONE,
    DataFrequency,
    NormalizedMarketRecord,
    ProvenanceMetadata,
    ProviderTier,
    SnapshotType,
)
from nifty_ai.features import (
    FeaturePipeline,
    PriceFeatureEngine,
    default_feature_registry,
    linear_regression_slope,
)


def _make_sample_record(
    d: date,
    o: float = 100.0,
    h: float = 105.0,
    l: float = 95.0,
    c: float = 102.0,
) -> NormalizedMarketRecord:
    prov = ProvenanceMetadata(
        provider="test_source",
        source_identifier="NIFTY 50",
        retrieval_timestamp=datetime(2026, 9, 6, 12, 0, 0, tzinfo=timezone.utc),
        timezone="Asia/Kolkata",
        data_frequency=DataFrequency.DAILY,
        tier=ProviderTier.FREE,
    )
    ts = datetime.combine(d, time(15, 30, 0), tzinfo=MARKET_TIMEZONE)
    return NormalizedMarketRecord(
        timestamp=ts,
        trading_date=d,
        symbol="NIFTY 50",
        open=o,
        high=h,
        low=l,
        close=c,
        volume=10000.0,  # Present in record, but must be ignored by engine
        provenance=prov,
    )


def test_feature_registry_structure():
    """Verify registry categories, completeness, and max lookback requirements."""
    categories = {f.category for f in default_feature_registry.list_all()}
    expected_cats = {
        "returns",
        "lags",
        "moving_averages",
        "momentum",
        "volatility",
        "ohlc_shape",
        "trend",
        "calendar",
    }
    assert expected_cats.issubset(categories)
    assert default_feature_registry.max_lookback == 200
    assert len(default_feature_registry.list_all()) >= 40


def test_return_and_lag_calculations():
    """Verify accuracy of returns and lag computations against manual calculations."""
    engine = PriceFeatureEngine()

    # Day 0: 100, Day 1: 105 (+5%), Day 2: 110.25 (+5%), Day 3: 115.7625 (+5%)
    recs = [
        _make_sample_record(date(2026, 9, 1), c=100.0),
        _make_sample_record(date(2026, 9, 2), c=105.0),
        _make_sample_record(date(2026, 9, 3), c=110.25),
        _make_sample_record(date(2026, 9, 4), c=115.7625),
    ]

    features, _ = engine.compute_features(recs, trim_warmup=False)

    # Day 0: lookback 1 not available
    assert features[0]["ret_1d"] is None

    # Day 1: (105 / 100) - 1 = 0.05
    assert features[1]["ret_1d"] == pytest.approx(0.05)

    # Day 2: (110.25 / 100) - 1 = 0.1025 for 2d return
    assert features[2]["ret_2d"] == pytest.approx(0.1025)

    # Day 2: lag 1 should be Day 1's 1d return (0.05)
    assert features[2]["ret_lag_1"] == pytest.approx(0.05)


def test_moving_averages_and_distances():
    """Verify moving average and normalized distance calculations."""
    engine = PriceFeatureEngine()
    recs = [
        _make_sample_record(date(2026, 9, i), c=float(i * 10))
        for i in range(1, 11)  # closes: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
    ]

    features, _ = engine.compute_features(recs, trim_warmup=False)

    # sma_5 at index 4 (values: 10, 20, 30, 40, 50) -> mean = 30.0
    assert features[4]["sma_5"] == pytest.approx(30.0)
    # close_to_sma_5 at index 4 -> (50 / 30) - 1
    assert features[4]["close_to_sma_5"] == pytest.approx((50.0 / 30.0) - 1.0)


def test_momentum_and_volatility():
    """Verify momentum differences and rolling volatility formulas."""
    engine = PriceFeatureEngine()
    # 6 bars: closes 100 to 110 in steps of 2
    recs = [
        _make_sample_record(date(2026, 9, i), c=100.0 + (i * 2))
        for i in range(1, 7)
    ]

    features, _ = engine.compute_features(recs, trim_warmup=False)

    # mom_5d at index 5 -> closes[5] - closes[0] = 112 - 102 = 10.0
    assert features[5]["mom_5d"] == pytest.approx(10.0)

    # volatility_5d at index 5 should exist
    assert features[5]["volatility_5d"] is not None


def test_ohlc_range_and_shape_features():
    """Verify high-low range, position in range, and open-to-close returns."""
    engine = PriceFeatureEngine()
    rec = _make_sample_record(
        date(2026, 9, 1),
        o=100.0,
        h=110.0,
        l=90.0,
        c=105.0,
    )
    features, _ = engine.compute_features([rec], trim_warmup=False)
    row = features[0]

    # hl_range_pct: (110 - 90) / 90 = 20 / 90
    assert row["hl_range_pct"] == pytest.approx(20.0 / 90.0)
    # close_pos_in_range: (105 - 90) / (110 - 90) = 15 / 20 = 0.75
    assert row["close_pos_in_range"] == pytest.approx(0.75)
    # open_to_close_ret: (105 - 100) / 100 = 0.05
    assert row["open_to_close_ret"] == pytest.approx(0.05)


def test_calendar_features():
    """Verify deterministic extraction of day_of_week, month, quarter."""
    engine = PriceFeatureEngine()
    # 2026-09-04 is a Friday (weekday = 4)
    rec = _make_sample_record(date(2026, 9, 4))
    features, _ = engine.compute_features([rec], trim_warmup=False)
    row = features[0]

    assert row["day_of_week"] == 4
    assert row["month"] == 9
    assert row["quarter"] == 3
    assert row["day_of_month"] == 4


# ------------------------------------------------------------------------------
# LEAKAGE TESTS (Critical Mandate)
# ------------------------------------------------------------------------------

def test_leakage_future_mutation_invariance():
    """Proof 1: Modifying a future row must NEVER alter features for prior rows."""
    engine = PriceFeatureEngine()

    base_recs = [
        _make_sample_record(date(2026, 9, i), c=100.0 + i)
        for i in range(1, 30)
    ]

    # Run feature extraction on original records
    features_orig, _ = engine.compute_features(base_recs, trim_warmup=False)

    # Clone records and drastically mutate row 28 (the final row)
    mutated_recs = [
        _make_sample_record(date(2026, 9, i), c=100.0 + i)
        for i in range(1, 30)
    ]
    mutated_recs[-1] = _make_sample_record(
        date(2026, 9, 29),
        o=99999.0,
        h=999999.0,
        l=1.0,
        c=55555.0,  # Drastic future price shift
    )

    features_mutated, _ = engine.compute_features(mutated_recs, trim_warmup=False)

    # Rows 0 through 27 must remain 100% BIT-IDENTICAL
    for idx in range(28):
        assert features_orig[idx] == features_mutated[idx], (
            f"Leakage detected at historical row {idx} when future row 28 was modified!"
        )


def test_leakage_snapshot_b_never_uses_current_day():
    """Proof 2: Snapshot B (08:50 Day T) strictly uses Day T-1 and cannot access Day T."""
    engine = PriceFeatureEngine()

    day_t_minus_1 = date(2026, 9, 3)
    day_t = date(2026, 9, 4)

    recs_without_day_t = [
        _make_sample_record(date(2026, 9, 1), c=100.0),
        _make_sample_record(date(2026, 9, 2), c=102.0),
        _make_sample_record(day_t_minus_1, c=104.0),
    ]

    recs_with_day_t = [
        _make_sample_record(date(2026, 9, 1), c=100.0),
        _make_sample_record(date(2026, 9, 2), c=102.0),
        _make_sample_record(day_t_minus_1, c=104.0),
        _make_sample_record(day_t, c=500.0),  # Day T future session
    ]

    # Extract feature vector for predicting Day T at Snapshot B
    feature_vec_1 = engine.get_features_for_prediction(
        historical_records=recs_without_day_t,
        target_prediction_date=day_t,
        snapshot_type=SnapshotType.SNAPSHOT_0850,
    )

    feature_vec_2 = engine.get_features_for_prediction(
        historical_records=recs_with_day_t,
        target_prediction_date=day_t,
        snapshot_type=SnapshotType.SNAPSHOT_0850,
    )

    # Even though recs_with_day_t contained Day T, the engine strictly filtered it out
    assert feature_vec_1["trading_date"] == "2026-09-03"
    assert feature_vec_2["trading_date"] == "2026-09-03"
    assert feature_vec_1 == feature_vec_2


def test_volume_exclusion_invariance():
    """Proof 3: Quarantined volume field is completely excluded from feature generation."""
    engine = PriceFeatureEngine()

    rec_v1 = _make_sample_record(date(2026, 9, 1), c=100.0)
    rec_v2 = _make_sample_record(date(2026, 9, 1), c=100.0)
    # Alter volume by 10,000,000
    rec_v2 = NormalizedMarketRecord(
        timestamp=rec_v2.timestamp,
        trading_date=rec_v2.trading_date,
        symbol=rec_v2.symbol,
        open=rec_v2.open,
        high=rec_v2.high,
        low=rec_v2.low,
        close=rec_v2.close,
        volume=99999999.0,  # Mutated volume
        provenance=rec_v2.provenance,
    )

    f1, _ = engine.compute_features([rec_v1], trim_warmup=False)
    f2, _ = engine.compute_features([rec_v2], trim_warmup=False)

    # Features must be identical regardless of volume
    assert f1 == f2
    # Verify no volume columns in feature output
    for col in f1[0].keys():
        assert "volume" not in col.lower()
        assert "vwap" not in col.lower()
        assert "obv" not in col.lower()
        assert "mfi" not in col.lower()


def test_determinism():
    """Proof 4: Feature computation is 100% deterministic across repeated runs."""
    engine = PriceFeatureEngine()
    recs = [
        _make_sample_record(date(2026, 9, i), c=100.0 + (i * 1.5))
        for i in range(1, 25)
    ]
    f_run1, _ = engine.compute_features(recs)
    f_run2, _ = engine.compute_features(recs)
    assert f_run1 == f_run2
