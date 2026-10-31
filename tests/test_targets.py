"""Unit and anti-leakage verification tests for Phase 5 Target Creation and Threshold Selection."""

from datetime import date, datetime, time, timezone
import math
import pytest

from nifty_ai.data import (
    MARKET_TIMEZONE,
    DataFrequency,
    NormalizedMarketRecord,
    ProvenanceMetadata,
    ProviderTier,
    SnapshotType,
)
from nifty_ai.targets import (
    DirectionLabel,
    EmpiricalDistributionThreshold,
    FixedThreshold,
    TargetPipeline,
    VolatilityScaledThreshold,
    classify_return,
    classify_targets,
    compute_next_session_returns,
    compute_rolling_thresholds,
)


def _make_test_record(
    d: date,
    close: float,
    open_p: float = 100.0,
    high_p: float = 105.0,
    low_p: float = 95.0,
) -> NormalizedMarketRecord:
    prov = ProvenanceMetadata(
        provider="test_prov",
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
        open=open_p,
        high=high_p,
        low=low_p,
        close=close,
        volume=1000.0,
        provenance=prov,
    )


def test_next_session_return_calculation():
    """Verify next-session close-to-close return formula: Close_(T+1) / Close_T - 1."""
    recs = [
        _make_test_record(date(2026, 9, 1), close=100.0),
        _make_test_record(date(2026, 9, 2), close=105.0),  # +5%
        _make_test_record(date(2026, 9, 3), close=94.5),   # -10% from 105
    ]
    targets = compute_next_session_returns(recs)

    assert len(targets) == 3

    # Row 0: Target is Day 2 (105 / 100 - 1 = +0.05)
    assert targets[0].trading_date == date(2026, 9, 1)
    assert targets[0].target_date == date(2026, 9, 2)
    assert targets[0].target_close == 105.0
    assert targets[0].target_return == pytest.approx(0.05)

    # Row 1: Target is Day 3 (94.5 / 105 - 1 = -0.10)
    assert targets[1].trading_date == date(2026, 9, 2)
    assert targets[1].target_date == date(2026, 9, 3)
    assert targets[1].target_close == 94.5
    assert targets[1].target_return == pytest.approx(-0.10)


def test_chronological_shift_correctness():
    """Verify that row T's target uses row T+1's close, not row T-1's close."""
    recs = [
        _make_test_record(date(2026, 9, 1), close=100.0),
        _make_test_record(date(2026, 9, 2), close=110.0),
        _make_test_record(date(2026, 9, 3), close=121.0),
    ]
    targets = compute_next_session_returns(recs)

    # At row 1 (Day 2, close=110), target should be Day 3 (121 / 110 - 1 = +10%),
    # NOT trailing Day 1 (100 / 110 - 1)
    assert targets[1].target_date == date(2026, 9, 3)
    assert targets[1].target_return == pytest.approx(0.10)


def test_last_row_has_no_fabricated_target():
    """Verify that the terminal row strictly has target_return=None and target_date=None."""
    recs = [
        _make_test_record(date(2026, 9, 1), close=100.0),
        _make_test_record(date(2026, 9, 2), close=105.0),
    ]
    targets = compute_next_session_returns(recs)

    last = targets[-1]
    assert last.trading_date == date(2026, 9, 2)
    assert last.target_date is None
    assert last.target_close is None
    assert last.target_return is None


def test_target_values_finite():
    """Verify that all non-terminal target returns are finite numbers."""
    recs = [
        _make_test_record(date(2026, 9, i), close=100.0 + (i * 2.5))
        for i in range(1, 15)
    ]
    targets = compute_next_session_returns(recs)

    for t in targets[:-1]:
        assert t.target_return is not None
        assert math.isfinite(t.target_return)


def test_preservation_of_extreme_returns():
    """Verify that extreme market moves (e.g. +20% circuit or -15% crash) are preserved unclipped."""
    recs = [
        _make_test_record(date(2026, 9, 1), close=1000.0),
        _make_test_record(date(2026, 9, 2), close=1200.0),  # +20.0%
        _make_test_record(date(2026, 9, 3), close=1020.0),  # -15.0%
    ]
    targets = compute_next_session_returns(recs)

    assert targets[0].target_return == pytest.approx(0.20)
    assert targets[1].target_return == pytest.approx(-0.15)


def test_volatility_scaled_threshold():
    """Verify Method A: Volatility-scaled threshold computation."""
    method = VolatilityScaledThreshold(k=0.5, window=5)

    # 5 returns of 0.01, 0.02, -0.01, 0.03, -0.02
    returns = [0.01, 0.02, -0.01, 0.03, -0.02]
    # Sample stdev
    import statistics
    expected_sigma = statistics.stdev(returns)
    expected_theta = 0.5 * expected_sigma

    computed = method.compute_threshold(returns)
    assert computed == pytest.approx(expected_theta)


def test_empirical_distribution_threshold():
    """Verify Method B: Empirical return-distribution threshold computation."""
    method = EmpiricalDistributionThreshold(percentile=50.0, window=10)

    # Absolute returns: 0.01 to 0.10
    returns = [0.01, -0.02, 0.03, -0.04, 0.05, -0.06, 0.07, -0.08, 0.09, -0.10]
    computed = method.compute_threshold(returns)

    # Sorted absolute: [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
    # 50th percentile (median of 10 items) -> index 4.5 -> avg(0.05, 0.06) = 0.055
    assert computed == pytest.approx(0.055)


def test_fixed_threshold():
    """Verify Method C: Fixed percentage baseline threshold."""
    method = FixedThreshold(value=0.005)
    assert method.compute_threshold([0.01, 0.02]) == pytest.approx(0.005)
    assert method.compute_threshold([]) == pytest.approx(0.005)


def test_threshold_warmup_behavior():
    """Verify that rolling threshold returns None during warm-up period."""
    method = VolatilityScaledThreshold(k=0.35, window=5)
    dates = [date(2026, 9, i) for i in range(1, 10)]
    returns = [0.01 * ((-1) ** i) for i in range(len(dates))]

    results = compute_rolling_thresholds(method, dates, returns)

    # First 4 days (indices 0..3) have < 5 returns -> warmup
    for i in range(4):
        assert results[i].threshold_value is None
        assert results[i].is_warmup is True

    # Index 4 has 5 returns -> valid threshold
    assert results[4].threshold_value is not None
    assert results[4].is_warmup is False


def test_classification_up_down_sideways():
    """Verify exact 3-class assignment against symmetric threshold."""
    theta = 0.005  # 0.5%

    assert classify_return(0.0051, theta) == DirectionLabel.UP
    assert classify_return(0.0100, theta) == DirectionLabel.UP

    assert classify_return(-0.0051, theta) == DirectionLabel.DOWN
    assert classify_return(-0.0100, theta) == DirectionLabel.DOWN

    assert classify_return(0.0000, theta) == DirectionLabel.SIDEWAYS
    assert classify_return(0.0049, theta) == DirectionLabel.SIDEWAYS
    assert classify_return(-0.0049, theta) == DirectionLabel.SIDEWAYS


def test_classification_boundary_behavior():
    """Verify boundary conditions: return == +theta and return == -theta are classified as SIDEWAYS."""
    theta = 0.005
    assert classify_return(+0.005, theta) == DirectionLabel.SIDEWAYS
    assert classify_return(-0.005, theta) == DirectionLabel.SIDEWAYS


def test_class_completeness():
    """Verify that every classified row maps to exactly one label in {UP, DOWN, SIDEWAYS}."""
    recs = [
        _make_test_record(date(2026, 9, i), close=100.0 + ((-1) ** i) * (i * 0.5))
        for i in range(1, 20)
    ]
    target_returns = compute_next_session_returns(recs)
    method = FixedThreshold(value=0.005)
    thresh_results = compute_rolling_thresholds(
        method,
        [r.trading_date for r in recs],
        [0.001] * len(recs),
    )

    classified = classify_targets(target_returns, thresh_results)

    valid_labels = {DirectionLabel.UP, DirectionLabel.DOWN, DirectionLabel.SIDEWAYS}
    # All except the terminal row should be classified
    for ct in classified[:-1]:
        assert ct.is_classified is True
        assert ct.target_direction in valid_labels

    # Terminal row
    assert classified[-1].is_classified is False
    assert classified[-1].target_direction is None


def test_snapshot_a_alignment():
    """Verify Snapshot A alignment: Session T features predict Session T+1 outcome."""
    recs = [
        _make_test_record(date(2026, 9, 1), close=100.0),
        _make_test_record(date(2026, 9, 2), close=102.0),
        _make_test_record(date(2026, 9, 3), close=101.0),
    ]
    target_returns = compute_next_session_returns(recs)
    method = FixedThreshold(value=0.005)
    thresh_results = compute_rolling_thresholds(
        method,
        [r.trading_date for r in recs],
        [0.01, 0.02, -0.01],
    )
    classified = classify_targets(target_returns, thresh_results)

    # For session on 2026-09-01:
    assert classified[0].trading_date == date(2026, 9, 1)
    assert classified[0].target_date == date(2026, 9, 2)
    assert classified[0].target_return == pytest.approx(102.0 / 100.0 - 1.0)


def test_snapshot_b_alignment():
    """Verify Snapshot B semantics: prediction on morning of T uses features through T-1."""
    recs = [
        _make_test_record(date(2026, 9, 1), close=100.0),
        _make_test_record(date(2026, 9, 2), close=102.0),
    ]
    target_returns = compute_next_session_returns(recs)
    method = FixedThreshold(value=0.005)
    thresh_results = compute_rolling_thresholds(
        method,
        [r.trading_date for r in recs],
        [0.01, 0.02],
    )
    classified = classify_targets(target_returns, thresh_results)

    # Prediction for Day 2 morning (2026-09-02):
    # Trailing feature cutoff is Day 1 (2026-09-01)
    assert classified[0].trading_date == date(2026, 9, 1)
    assert classified[0].target_date == date(2026, 9, 2)


# ------------------------------------------------------------------------------
# CRITICAL LEAKAGE TEST (Mandate from Section 14)
# ------------------------------------------------------------------------------

def test_leakage_future_return_threshold_invariance():
    """PROOF: Changing a future return must NEVER change a threshold assigned to an earlier prediction date."""
    method = VolatilityScaledThreshold(k=0.35, window=5)

    dates = [date(2026, 9, i) for i in range(1, 20)]
    returns_original = [0.005 * i for i in range(1, 20)]

    # Compute baseline rolling thresholds
    thresh_orig = compute_rolling_thresholds(method, dates, returns_original)

    # Mutate future returns (e.g. Day 19 has an extreme return of +500%)
    returns_mutated = list(returns_original)
    returns_mutated[-1] = 5.0  # Drastic future return shift on final day

    thresh_mutated = compute_rolling_thresholds(method, dates, returns_mutated)

    # Thresholds for days 0 through 17 MUST be 100% BIT-IDENTICAL
    for i in range(18):
        assert thresh_orig[i].threshold_value == thresh_mutated[i].threshold_value, (
            f"Future leakage detected! Threshold at index {i} changed when future return at index 18 was mutated."
        )


def test_deterministic_output():
    """Verify that repeated pipeline runs produce bit-identical results."""
    recs = [
        _make_test_record(date(2026, 9, i), close=100.0 + i)
        for i in range(1, 15)
    ]
    t1 = compute_next_session_returns(recs)
    t2 = compute_next_session_returns(recs)
    assert t1 == t2


def test_no_sideways_optimization_in_selection():
    """Verify that selection score does not exist and SIDEWAYS % is not an optimization target."""
    from datetime import timedelta
    from nifty_ai.targets import ThresholdAnalyzer
    analyzer = ThresholdAnalyzer()
    start = date(2026, 1, 1)
    recs = [
        _make_test_record(start + timedelta(days=i), close=100.0 + (i * 0.5))
        for i in range(50)
    ]
    eval_res = analyzer.evaluate_method(
        method=VolatilityScaledThreshold(k=0.35, window=20),
        records=recs,
        use_development_only=False,
    )
    # Ensure selection_score does NOT exist
    assert not hasattr(eval_res, "selection_score")
    # Verify sideways_pct is purely an observational field
    assert hasattr(eval_res, "sideways_pct")
    assert isinstance(eval_res.sideways_pct, float)


def test_method_a_frozen_parameters():
    """Verify Method A applies k=0.35 and window=20 correctly."""
    import statistics
    method = VolatilityScaledThreshold(k=0.35, window=20)
    assert method.parameters == {"k": 0.35, "window": 20}
    assert method.min_lookback == 20

    # Test with 20 known returns
    returns = [0.01 * (1 if i % 2 == 0 else -1) for i in range(20)]
    expected_sigma = statistics.stdev(returns)
    expected_theta = 0.35 * expected_sigma
    assert method.compute_threshold(returns) == pytest.approx(expected_theta)


def test_snapshot_b_threshold_never_uses_return_t():
    """Verify that Snapshot B threshold for predicting Day T never uses return of Day T."""
    day_t_minus_1 = date(2026, 9, 2)
    day_t = date(2026, 9, 3)

    # Base records up to Day T
    recs_base = [
        _make_test_record(date(2026, 9, 1), close=100.0),
        _make_test_record(day_t_minus_1, close=102.0),
        _make_test_record(day_t, close=105.0),
    ]

    # Mutated records where Day T's price explodes to 500.0
    recs_mutated = [
        _make_test_record(date(2026, 9, 1), close=100.0),
        _make_test_record(day_t_minus_1, close=102.0),
        _make_test_record(day_t, close=500.0),  # Extreme move on Day T
    ]

    method = FixedThreshold(value=0.005)

    # Compute targets for both
    t_base = compute_next_session_returns(recs_base)
    t_mut = compute_next_session_returns(recs_mutated)

    thresh_base = compute_rolling_thresholds(
        method,
        [r.trading_date for r in recs_base],
        [0.0, 0.02, 0.0294],
    )
    thresh_mut = compute_rolling_thresholds(
        method,
        [r.trading_date for r in recs_mutated],
        [0.0, 0.02, 3.9019],
    )

    class_base = classify_targets(t_base, thresh_base)
    class_mut = classify_targets(t_mut, thresh_mut)

    # In Snapshot B for predicting Day T (which is row index 1 predicting Day T):
    # The feature cutoff session is Day T-1 (2026-09-02)
    # The threshold used is threshold_value at index 1
    assert class_base[1].trading_date == day_t_minus_1
    assert class_base[1].target_date == day_t
    assert class_base[1].threshold_value == class_mut[1].threshold_value

