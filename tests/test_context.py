"""Test Suite for Phase 7 Market Context Data Layer.

Validates point-in-time publication schedules, timezone awareness, DST handling,
absence of forward-looking leakage, Snapshot A vs B information contracts,
holdout isolation, and missing data policies.
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest

from nifty_ai.data.context.calendar import (
    CANONICAL_CONTEXT_SPECS,
    TIMEZONE_KOLKATA,
    TIMEZONE_NEW_YORK,
    TIMEZONE_TOKYO,
    compute_availability_timestamp,
)
from nifty_ai.data.context.datasets import (
    SnapshotContextTable,
    build_snapshot_context_dataset,
)
from nifty_ai.data.context.features import (
    compute_rolling_volatility,
    compute_series_diff,
    compute_series_return,
)
from nifty_ai.data.context.missing_data import (
    FillDiagnostics,
    align_and_fill_series,
    align_and_fill_series_with_diagnostics,
)
from nifty_ai.data.context.normalizer import ContextDataValidator
from nifty_ai.data.context.point_in_time import (
    filter_context_for_snapshot,
    is_context_observation_available,
)
from nifty_ai.data.context.schema import (
    AvailabilitySpec,
    AvailabilityTimestampType,
    ContextCategory,
    ContextObservation,
    MissingPolicy,
)
from nifty_ai.data.schema import DataFrequency, ProvenanceMetadata, ProviderTier
from nifty_ai.data.snapshots import SnapshotType, create_snapshot_cutoff


def create_sample_observation(
    variable_name: str,
    obs_date: date,
    close_price: float,
    native_timezone: str = "America/New_York",
    market_close_time: time = time(16, 0, 0),
    lag_minutes: int = 30,
) -> ContextObservation:
    """Helper to generate a validated ContextObservation."""
    tz = ZoneInfo(native_timezone)
    obs_dt = datetime.combine(obs_date, market_close_time, tzinfo=tz)

    spec = AvailabilitySpec(
        variable_name=variable_name,
        instrument=f"^{variable_name}",
        category=ContextCategory.GLOBAL_EQUITY,
        native_timezone=native_timezone,
        market_close_time=market_close_time,
        lag_minutes_to_availability=lag_minutes,
    )
    avail_dt = compute_availability_timestamp(obs_date, spec)

    prov = ProvenanceMetadata(
        provider="test_mock",
        source_identifier=spec.instrument,
        retrieval_timestamp=datetime.now(timezone.utc),
        source_timestamp=obs_dt,
        timezone=native_timezone,
        data_frequency=DataFrequency.DAILY,
        tier=ProviderTier.FREE,
    )

    return ContextObservation(
        variable_name=variable_name,
        instrument=spec.instrument,
        observation_date=obs_date,
        observation_timestamp=obs_dt,
        availability_timestamp=avail_dt,
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=1000.0,
        provenance=prov,
    )


# TEST 1: Publication Time Cutoff Strictness
def test_publication_time_cutoff_strictness() -> None:
    """Ensure an observation is strictly NOT available if its availability timestamp is after cutoff."""
    ref_date = date(2023, 6, 15)  # Session T
    tgt_date = date(2023, 6, 16)  # Session T+1

    # Snapshot A cutoff is 15:30 IST on Session T
    cutoff_a = create_snapshot_cutoff(SnapshotType.SNAPSHOT_1540, tgt_date, ref_date)

    # India VIX closes at 15:30 IST on Day T -> available at 15:30 IST
    india_vix_obs = create_sample_observation(
        "INDIA_VIX",
        ref_date,
        15.5,
        native_timezone="Asia/Kolkata",
        market_close_time=time(15, 30, 0),
        lag_minutes=0,
    )
    assert is_context_observation_available(india_vix_obs, cutoff_a) is True

    # S&P 500 on Day T closes at 16:00 EDT -> available at 02:00 IST on Day T+1
    sp500_t_obs = create_sample_observation(
        "SP500",
        ref_date,
        4400.0,
        native_timezone="America/New_York",
        market_close_time=time(16, 0, 0),
        lag_minutes=30,
    )
    # Must NOT be available for Snapshot A on Day T
    assert is_context_observation_available(sp500_t_obs, cutoff_a) is False


# TEST 2: Snapshot A vs B US Market Divergence
def test_snapshot_a_vs_b_us_divergence() -> None:
    """Snapshot A must only see US Day T-1; Snapshot B legitimately sees US Day T."""
    day_t_minus_1 = date(2023, 6, 14)
    day_t = date(2023, 6, 15)
    day_t_plus_1 = date(2023, 6, 16)

    obs_t_minus_1 = create_sample_observation("SP500", day_t_minus_1, 4350.0)
    obs_t = create_sample_observation("SP500", day_t, 4400.0)

    context_map = {"SP500": [obs_t_minus_1, obs_t]}

    # Snapshot A (Cutoff 15:30 IST on Day T)
    table_a = build_snapshot_context_dataset(
        target_dates=[day_t_plus_1],
        reference_dates=[day_t],
        snapshot_type=SnapshotType.SNAPSHOT_1540,
        context_series_map=context_map,
    )
    df_a = table_a.df
    # In Snapshot A, SP500 close MUST be from day_t_minus_1 (4350.0)
    assert df_a.iloc[0]["sp500_obs_date"] == day_t_minus_1.isoformat()
    assert df_a.iloc[0]["sp500_close"] == 4350.0

    # Snapshot B (Cutoff 08:50 IST on Day T+1)
    table_b = build_snapshot_context_dataset(
        target_dates=[day_t_plus_1],
        reference_dates=[day_t],
        snapshot_type=SnapshotType.SNAPSHOT_0850,
        context_series_map=context_map,
    )
    df_b = table_b.df
    # In Snapshot B, SP500 close MUST be from completed overnight Day T (4400.0)
    assert df_b.iloc[0]["sp500_obs_date"] == day_t.isoformat()
    assert df_b.iloc[0]["sp500_close"] == 4400.0


# TEST 3: Future Mutation Invariance
def test_future_mutation_invariance() -> None:
    """Historical context dataset rows up to time T must NOT change when future observations are appended."""
    d1 = date(2023, 6, 12)
    d2 = date(2023, 6, 13)
    d3 = date(2023, 6, 14)
    d4 = date(2023, 6, 15)

    base_obs = [
        create_sample_observation("SP500", d1, 4200.0),
        create_sample_observation("SP500", d2, 4220.0),
    ]

    table_base = build_snapshot_context_dataset(
        target_dates=[d2, d3],
        reference_dates=[d1, d2],
        snapshot_type=SnapshotType.SNAPSHOT_1540,
        context_series_map={"SP500": base_obs},
    )
    df_base = table_base.df.copy()

    # Append future observations (d3, d4) with extreme / radical values
    mutated_obs = base_obs + [
        create_sample_observation("SP500", d3, 99999.0),
        create_sample_observation("SP500", d4, 1.0),
    ]

    table_extended = build_snapshot_context_dataset(
        target_dates=[d2, d3],
        reference_dates=[d1, d2],
        snapshot_type=SnapshotType.SNAPSHOT_1540,
        context_series_map={"SP500": mutated_obs},
    )
    df_extended = table_extended.df.copy()

    # Base rows must be bitwise identical
    pd.testing.assert_frame_equal(df_base, df_extended)


# TEST 4: Timezone and DST Handling
def test_timezone_and_dst_handling() -> None:
    """US market close at 16:00 local EDT vs EST translates to different IST times across DST transitions."""
    spec = CANONICAL_CONTEXT_SPECS["SP500"]

    # Summer: EDT (UTC-4)
    summer_date = date(2023, 7, 15)
    avail_summer = compute_availability_timestamp(summer_date, spec)
    # 16:00 EDT + 30 min = 16:30 EDT = 20:30 UTC = 02:00 IST (next day)
    assert avail_summer.astimezone(TIMEZONE_KOLKATA).hour == 2
    assert avail_summer.astimezone(TIMEZONE_KOLKATA).minute == 0
    assert avail_summer.astimezone(TIMEZONE_KOLKATA).day == 16

    # Winter: EST (UTC-5)
    winter_date = date(2023, 1, 15)
    avail_winter = compute_availability_timestamp(winter_date, spec)
    # 16:00 EST + 30 min = 16:30 EST = 21:30 UTC = 03:00 IST (next day)
    assert avail_winter.astimezone(TIMEZONE_KOLKATA).hour == 3
    assert avail_winter.astimezone(TIMEZONE_KOLKATA).minute == 0
    assert avail_winter.astimezone(TIMEZONE_KOLKATA).day == 16


# TEST 5: Holiday Calendar and Missing Data Alignment
def test_holiday_calendar_isolation_and_missing_policy() -> None:
    """Missing observations across exchange holidays must obey forward-fill limit and never backfill."""
    d_fri = date(2023, 6, 9)
    d_mon = date(2023, 6, 12)  # Weekend gap = 3 days
    d_thu = date(2023, 6, 15)  # Extended gap = 6 days (> 5 day limit)

    obs_fri = create_sample_observation("US_10Y_YIELD", d_fri, 3.75)
    date_to_obs = {d_fri: obs_fri}

    # Weekend forward fill (3 days <= 5 days) -> should fill
    filled_mon = align_and_fill_series(
        dates=[d_mon],
        date_to_obs=date_to_obs,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        max_fill_days=5,
    )
    assert filled_mon[0] is not None
    assert filled_mon[0].close == 3.75

    # Excessive gap (6 days > 5 days) -> should expire to None
    filled_thu = align_and_fill_series(
        dates=[d_thu],
        date_to_obs=date_to_obs,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        max_fill_days=5,
    )
    assert filled_thu[0] is None

    # NO_FILL policy -> must strictly never fill
    no_fill_mon = align_and_fill_series(
        dates=[d_mon],
        date_to_obs=date_to_obs,
        missing_policy=MissingPolicy.NO_FILL,
    )
    assert no_fill_mon[0] is None


# TEST 6: Terminal Holdout Isolation
def test_terminal_holdout_isolation() -> None:
    """Context datasets must cleanly partition into development and holdout without cross-period leakage."""
    holdout_start = date(2022, 1, 1)

    # Generate a series spanning 2021 to 2022
    dates = [
        date(2021, 12, 30),
        date(2021, 12, 31),
        date(2022, 1, 3),
        date(2022, 1, 4),
    ]
    obs_list = [create_sample_observation("INDIA_VIX", d, 16.0 + i) for i, d in enumerate(dates)]

    # Development table only up to 2021-12-31
    dev_ref_dates = [dates[0]]
    dev_tgt_dates = [dates[1]]

    table_dev = build_snapshot_context_dataset(
        target_dates=dev_tgt_dates,
        reference_dates=dev_ref_dates,
        snapshot_type=SnapshotType.SNAPSHOT_1540,
        context_series_map={"INDIA_VIX": obs_list},
    )
    df_dev = table_dev.df

    # Any cutoff in development partition must have cutoff timestamp strictly before 2022-01-01
    for cutoff_str in df_dev["cutoff_timestamp"]:
        cutoff_dt = datetime.fromisoformat(cutoff_str)
        assert cutoff_dt.date() < holdout_start


# TEST 7: Rolling Feature Lookback Bounds
def test_no_future_rolling_statistics() -> None:
    """Rolling return and volatility features must not incorporate any future index data."""
    prices = np.array([100.0, 102.0, 101.0, 105.0, 107.0, 110.0], dtype=np.float64)

    # 1-day returns
    returns = compute_series_return(prices, lookback=1)
    assert np.isnan(returns[0])
    assert pytest.approx(returns[1], rel=1e-4) == (102.0 / 100.0) - 1.0

    # Changing future element price[5] from 110.0 to 999.0 must NOT alter returns[0..4]
    mutated_prices = prices.copy()
    mutated_prices[5] = 999.0
    mutated_returns = compute_series_return(mutated_prices, lookback=1)

    np.testing.assert_array_equal(returns[:5], mutated_returns[:5])

    # Rolling volatility calculation
    vol = compute_rolling_volatility(returns, window=3)
    mutated_vol = compute_rolling_volatility(mutated_returns, window=3)
    # Volatility at index 3 and 4 must remain identical
    assert pytest.approx(vol[3], rel=1e-5) == mutated_vol[3]
    assert pytest.approx(vol[4], rel=1e-5) == mutated_vol[4]


# TEST 8: All 16 Canonical Variables Inventory and Column Integrity
def test_all_16_canonical_variables_exist() -> None:
    """Verify all 16 expected variables exist in registry and generated datasets."""
    expected_16 = [
        "INDIA_VIX",
        "NIFTY_BANK",
        "USD_INR",
        "INDIA_10Y_YIELD",
        "SP500",
        "NASDAQ",
        "DOW_JONES",
        "US_VIX",
        "US_10Y_YIELD",
        "BRENT_CRUDE",
        "WTI_CRUDE",
        "GOLD",
        "DXY",
        "NIKKEI_225",
        "HANG_SENG",
        "FTSE_100",
    ]
    assert len(CANONICAL_CONTEXT_SPECS) == 16
    for var in expected_16:
        assert var in CANONICAL_CONTEXT_SPECS
        spec = CANONICAL_CONTEXT_SPECS[var]
        assert spec.variable_name == var
        assert spec.instrument is not None
        assert spec.native_timezone in [
            "Asia/Kolkata",
            "America/New_York",
            "Asia/Tokyo",
            "Asia/Hong_Kong",
            "Europe/London",
        ]
        assert spec.missing_policy in [MissingPolicy.NO_FILL, MissingPolicy.FORWARD_FILL_CALENDAR]
        assert spec.availability_timestamp_type == AvailabilityTimestampType.ASSUMED_SCHEDULE

    # Verify columns in generated interim CSVs
    import pandas as pd
    df_a = pd.read_csv("data/interim/context/snapshot_a_context_daily.csv")
    df_b = pd.read_csv("data/interim/context/snapshot_b_context_daily.csv")
    for var in expected_16:
        col_close = f"{var.lower()}_close"
        col_obs = f"{var.lower()}_obs_date"
        assert col_close in df_a.columns
        assert col_obs in df_a.columns
        assert col_close in df_b.columns
        assert col_obs in df_b.columns


# TEST 9: All 16 Variables Are Classified As Assumed Schedule
def test_availability_timestamp_type_semantics() -> None:
    """Verify ALL 16 variables are strictly classified as ASSUMED_SCHEDULE.
    
    Because Yahoo Finance (free tier) does not provide historical publication timestamps,
    no variable can claim DOCUMENTED_SCHEDULE for historical provider availability.
    """
    for var_name, spec in CANONICAL_CONTEXT_SPECS.items():
        assert (
            spec.availability_timestamp_type == AvailabilityTimestampType.ASSUMED_SCHEDULE
        ), f"Variable {var_name} must be ASSUMED_SCHEDULE, got {spec.availability_timestamp_type}"
        assert spec.provider_availability_observed is False, (
            f"Variable {var_name} must have provider_availability_observed=False"
        )


# TEST 10: Source-Specific Semantics (^TNX, USDINR=X, Futures)
def test_source_specific_instrument_semantics() -> None:
    """Verify specific financial semantics of unique instruments."""
    # ^TNX represents 10x 10-Year yield (e.g. 42.50 = 4.250%)
    tnx_spec = CANONICAL_CONTEXT_SPECS["US_10Y_YIELD"]
    assert "yield × 10" in tnx_spec.notes or "yield * 10" in tnx_spec.notes or "10x" in tnx_spec.notes.lower()

    # USDINR=X is spot FX
    usdinr_spec = CANONICAL_CONTEXT_SPECS["USD_INR"]
    assert usdinr_spec.instrument == "USDINR=X"
    assert usdinr_spec.native_timezone == "Asia/Kolkata"

    # Commodity futures (Brent, WTI, Gold)
    for comm in ["BRENT_CRUDE", "WTI_CRUDE", "GOLD"]:
        spec = CANONICAL_CONTEXT_SPECS[comm]
        assert spec.category == ContextCategory.GLOBAL_COMMODITIES
        assert spec.native_timezone == "America/New_York"
        assert spec.market_close_time == time(17, 0, 0)


# TEST 11: Cutoff Edge Case Behavior (15:30 IST and 08:50 IST)
def test_cutoff_exact_boundary_edge_cases() -> None:
    """Verify observations matching cutoff to the exact second are accepted, 1 second later rejected."""
    d = date(2023, 6, 15)
    cutoff_dt = datetime(2023, 6, 15, 15, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    cutoff = create_snapshot_cutoff(SnapshotType.SNAPSHOT_1540, date(2023, 6, 16), d)

    # Exact match: 15:30:00 -> Usable
    obs_exact = ContextObservation(
        variable_name="TEST_VAR",
        instrument="TEST",
        observation_date=d,
        observation_timestamp=cutoff_dt,
        availability_timestamp=cutoff_dt,
        open=100.0,
        high=100.0,
        low=100.0,
        close=100.0,
        volume=100.0,
        provenance=ProvenanceMetadata(
            provider="test",
            source_identifier="TEST",
            retrieval_timestamp=cutoff_dt,
            source_timestamp=cutoff_dt,
            timezone="Asia/Kolkata",
        ),
        availability_timestamp_type=AvailabilityTimestampType.DOCUMENTED_SCHEDULE,
    )
    assert is_context_observation_available(obs_exact, cutoff) is True

    # 1 second late: 15:30:01 -> Excluded
    cutoff_plus_1s = cutoff_dt + timedelta(seconds=1)
    obs_late = ContextObservation(
        variable_name="TEST_VAR",
        instrument="TEST",
        observation_date=d,
        observation_timestamp=cutoff_dt,
        availability_timestamp=cutoff_plus_1s,
        open=100.0,
        high=100.0,
        low=100.0,
        close=100.0,
        volume=100.0,
        provenance=ProvenanceMetadata(
            provider="test",
            source_identifier="TEST",
            retrieval_timestamp=cutoff_plus_1s,
            source_timestamp=cutoff_dt,
            timezone="Asia/Kolkata",
        ),
        availability_timestamp_type=AvailabilityTimestampType.DOCUMENTED_SCHEDULE,
    )
    assert is_context_observation_available(obs_late, cutoff) is False


# TEST 12: Friday to Monday Forward Fill Across Calendar
def test_friday_to_monday_forward_fill() -> None:
    """Verify weekend transition Friday -> Monday forward fill maintains source timestamps."""
    d_fri = date(2023, 6, 9)
    d_sat = date(2023, 6, 10)
    d_sun = date(2023, 6, 11)
    d_mon = date(2023, 6, 12)

    obs_fri = create_sample_observation("SP500", d_fri, 4300.0)
    date_to_obs = {d_fri: obs_fri}

    filled = align_and_fill_series(
        dates=[d_fri, d_mon],
        date_to_obs=date_to_obs,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        max_fill_days=5,
    )
    # Friday has original observation
    assert filled[0] is not None
    assert filled[0].observation_date == d_fri
    assert filled[0].close == 4300.0

    # Monday receives Friday observation with original provenance preserved
    assert filled[1] is not None
    assert filled[1].observation_date == d_fri
    assert filled[1].close == 4300.0


# TEST 13: US Holiday vs Indian Trading Day Alignment
def test_us_holiday_with_indian_trading_day() -> None:
    """On a US holiday (e.g. July 4), Snapshot B uses prior available US session without forward leakage."""
    d_july3 = date(2023, 7, 3)
    d_july4 = date(2023, 7, 4)  # US Market closed (Independence Day)
    d_july5 = date(2023, 7, 5)

    obs_july3 = create_sample_observation("SP500", d_july3, 4450.0)
    # No observation for July 4 in context series
    context_map = {"SP500": [obs_july3]}

    # Indian trading on July 5: predicting July 6 in Snapshot B
    table_b = build_snapshot_context_dataset(
        target_dates=[d_july5],
        reference_dates=[d_july4],
        snapshot_type=SnapshotType.SNAPSHOT_0850,
        context_series_map=context_map,
    )
    df_b = table_b.df
    # On July 4 reference date, SP500 must forward-fill July 3 close (4450.0)
    assert df_b.iloc[0]["sp500_close"] == 4450.0
    assert df_b.iloc[0]["sp500_obs_date"] == d_july3.isoformat()


# TEST 14: All 16 Variables Are Assumed Schedule (Universal Invariant)
def test_all_variables_are_assumed_schedule() -> None:
    """Explicitly verify that 100% of canonical context variables are ASSUMED_SCHEDULE."""
    assert len(CANONICAL_CONTEXT_SPECS) == 16
    for name, spec in CANONICAL_CONTEXT_SPECS.items():
        assert spec.availability_timestamp_type == AvailabilityTimestampType.ASSUMED_SCHEDULE, (
            f"{name} must be ASSUMED_SCHEDULE"
        )
        assert spec.provider_availability_observed is False, (
            f"{name} must have provider_availability_observed=False"
        )


# TEST 15: Availability Spec Provenance Fields Populated
def test_availability_spec_provenance_fields() -> None:
    """Verify every variable has non-empty instrument and provider provenance descriptions."""
    for name, spec in CANONICAL_CONTEXT_SPECS.items():
        assert spec.instrument_timestamp_description != "", (
            f"{name} missing instrument_timestamp_description"
        )
        assert spec.provider_availability_basis != "", (
            f"{name} missing provider_availability_basis"
        )
        assert spec.provider_tier == ProviderTier.FREE


# TEST 16: USD_INR Provenance Semantics (OTC / Interbank Separation)
def test_usdinr_provenance_semantics() -> None:
    """Verify USD_INR notes explicitly distinguish OTC/interbank spot from RBI reference rate."""
    spec = CANONICAL_CONTEXT_SPECS["USD_INR"]
    assert "RBI" in spec.instrument_timestamp_description
    assert "OTC/interbank" in spec.instrument_timestamp_description
    assert spec.availability_timestamp_type == AvailabilityTimestampType.ASSUMED_SCHEDULE
    assert spec.snapshot_a_eligibility_note is not None
    assert "conservative modeling assumption" in spec.snapshot_a_eligibility_note


# TEST 17: INDIA_VIX and NIFTY_BANK Boundary Eligibility Documentation
def test_vix_and_nifty_bank_boundary_documentation() -> None:
    """Verify INDIA_VIX and NIFTY_BANK document Snapshot A eligibility as assumption-dependent."""
    for var in ["INDIA_VIX", "NIFTY_BANK"]:
        spec = CANONICAL_CONTEXT_SPECS[var]
        assert spec.snapshot_a_eligibility_note is not None
        assert "explicit conservative modeling assumption" in spec.snapshot_a_eligibility_note
        assert "not empirically verified" in spec.snapshot_a_eligibility_note
        assert spec.market_close_time == time(15, 30, 0)
        assert spec.availability_timestamp_type == AvailabilityTimestampType.ASSUMED_SCHEDULE


# TEST 18: ^TNX Yield Index Semantics (Yield * 10, CBOE Index)
def test_tnx_yield_index_semantics() -> None:
    """Verify ^TNX notes document that it is a CBOE yield index, quoted as yield x 10."""
    spec = CANONICAL_CONTEXT_SPECS["US_10Y_YIELD"]
    assert spec.instrument == "^TNX"
    assert "INDEX" in spec.instrument_timestamp_description
    assert "yield × 10" in spec.instrument_timestamp_description or "yield * 10" in spec.instrument_timestamp_description
    assert "cash Treasury" in spec.instrument_timestamp_description


# TEST 19: Commodity Continuous Contract Semantics
def test_commodity_continuous_contract_semantics() -> None:
    """Verify commodity continuous contracts document settlement vs electronic session distinction."""
    for comm in ["BRENT_CRUDE", "WTI_CRUDE", "GOLD"]:
        spec = CANONICAL_CONTEXT_SPECS[comm]
        desc = spec.instrument_timestamp_description
        assert "continuous" in desc.lower()
        assert "settlement" in desc.lower()
        assert "NOT identical" in desc or "not identical" in desc.lower()


# TEST 20: Target-Session Fill Aging Diagnostics
def test_target_session_fill_diagnostics() -> None:
    """Verify align_and_fill_series_with_diagnostics computes both calendar and session aging."""
    d_fri = date(2023, 6, 9)
    d_mon = date(2023, 6, 12)  # Weekend: 3 calendar days, 1 NIFTY session
    d_wed = date(2023, 6, 14)  # 5 calendar days, 3 NIFTY sessions

    nifty_sessions = {date(2023, 6, 9), date(2023, 6, 12), date(2023, 6, 13), date(2023, 6, 14)}

    obs_fri = create_sample_observation("SP500", d_fri, 4300.0)
    date_to_obs = {d_fri: obs_fri}

    filled, diag = align_and_fill_series_with_diagnostics(
        dates=[d_mon, d_wed],
        date_to_obs=date_to_obs,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        max_fill_days=5,
        nifty_trading_dates=nifty_sessions,
    )

    assert len(filled) == 2
    assert diag.total_requested == 2
    assert diag.filled_rows == 2
    assert diag.same_day_matches == 0
    assert diag.max_calendar_fill_days == 5
    assert diag.max_target_session_fill_days == 3  # (June 12, 13, 14)


# TEST 21: Phase 6 Calibration Wording In MODEL_METHODOLOGY.md
def test_phase6_calibration_wording_integrity() -> None:
    """Verify MODEL_METHODOLOGY.md does not claim the classifier was accepted as Platt-calibrated."""
    from pathlib import Path
    doc_path = Path("docs/MODEL_METHODOLOGY.md")
    assert doc_path.exists()
    content = doc_path.read_text(encoding="utf-8")

    # Must state raw tree probabilities remain primary
    assert "raw tree probabilities remain primary" in content
    # Must explicitly state calibration worsened performance
    assert "calibration worsened" in content
