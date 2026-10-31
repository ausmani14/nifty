"""Exchange calendar schedules and canonical availability specifications.

Defines native closing times, timezones, and availability lag rules for
Indian, US, Asian, and European market variables.
"""

from datetime import date, datetime, time, timedelta
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from nifty_ai.data.context.schema import (
    AvailabilitySpec,
    AvailabilityTimestampType,
    ContextCategory,
    MissingPolicy,
)
from nifty_ai.data.schema import ProviderTier

TIMEZONE_KOLKATA = ZoneInfo("Asia/Kolkata")
TIMEZONE_NEW_YORK = ZoneInfo("America/New_York")
TIMEZONE_TOKYO = ZoneInfo("Asia/Tokyo")
TIMEZONE_HONG_KONG = ZoneInfo("Asia/Hong_Kong")
TIMEZONE_LONDON = ZoneInfo("Europe/London")

# Canonical Registry of Context Specifications
#
# PROVENANCE POLICY (Phase 7 Correction):
# All 16 variables are classified as `assumed_schedule` because Yahoo Finance
# (free tier) does not provide historical publication timestamps. We cannot
# empirically verify when Yahoo made any data point available. The availability
# timestamp is computed as instrument_close_time + lag_minutes_to_availability,
# used as a conservative proxy for provider publication.
#
CANONICAL_CONTEXT_SPECS: Dict[str, AvailabilitySpec] = {
    # ──────────────────────────────────────────────────────────────────────────
    # 1. Domestic Indian Variables
    # ──────────────────────────────────────────────────────────────────────────
    "INDIA_VIX": AvailabilitySpec(
        variable_name="INDIA_VIX",
        instrument="^INDIAVIX",
        category=ContextCategory.DOMESTIC_VOLATILITY,
        native_timezone="Asia/Kolkata",
        market_close_time=time(15, 30, 0),
        lag_minutes_to_availability=0,
        missing_policy=MissingPolicy.NO_FILL,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "NSE India VIX implied volatility index. Instrument finalizes at 15:30 IST "
            "(NSE official equity market close)."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. No historical Yahoo publication "
            "timestamp available. Instrument finalization time (15:30 IST) used as "
            "conservative proxy for provider availability."
        ),
        provider_availability_observed=False,
        snapshot_a_eligibility_note=(
            "Snapshot A eligibility is based on an explicit conservative modeling "
            "assumption that the provider value is available at instrument finalization "
            "(15:30 IST). Historical Yahoo publication time is unavailable and therefore "
            "this boundary condition is not empirically verified. Instrument finalization "
            "coincides exactly with the Snapshot A cutoff (15:30 IST), making this a "
            "boundary case. For production/direct NSE provider, replace with a documented "
            "provider-specific availability timestamp."
        ),
        notes=(
            "NSE India implied volatility index calculated on Nifty 50 options. "
            "Instrument close: 15:30 IST. Provider: Yahoo Finance (^INDIAVIX). "
            "Provider availability: unknown (assumed at instrument close)."
        ),
    ),
    "NIFTY_BANK": AvailabilitySpec(
        variable_name="NIFTY_BANK",
        instrument="^NSEBANK",
        category=ContextCategory.DOMESTIC_EQUITY,
        native_timezone="Asia/Kolkata",
        market_close_time=time(15, 30, 0),
        lag_minutes_to_availability=0,
        missing_policy=MissingPolicy.NO_FILL,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "NSE Bank Nifty sector index (top 12 banking stocks). Instrument finalizes "
            "at 15:30 IST (NSE official equity market close)."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. No historical Yahoo publication "
            "timestamp available. Instrument finalization time (15:30 IST) used as "
            "conservative proxy for provider availability."
        ),
        provider_availability_observed=False,
        snapshot_a_eligibility_note=(
            "Snapshot A eligibility is based on an explicit conservative modeling "
            "assumption that the provider value is available at instrument finalization "
            "(15:30 IST). Historical Yahoo publication time is unavailable and therefore "
            "this boundary condition is not empirically verified. Instrument finalization "
            "coincides exactly with the Snapshot A cutoff (15:30 IST), making this a "
            "boundary case. For production/direct NSE provider, replace with a documented "
            "provider-specific availability timestamp."
        ),
        notes=(
            "NSE Bank Nifty sector index. Instrument close: 15:30 IST. "
            "Provider: Yahoo Finance (^NSEBANK). "
            "Provider availability: unknown (assumed at instrument close)."
        ),
    ),
    "USD_INR": AvailabilitySpec(
        variable_name="USD_INR",
        instrument="USDINR=X",
        category=ContextCategory.DOMESTIC_FX,
        native_timezone="Asia/Kolkata",
        market_close_time=time(15, 30, 0),
        lag_minutes_to_availability=0,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "USDINR=X on Yahoo represents OTC/interbank spot FX aggregation, NOT the "
            "RBI reference rate (FBIL publishes around 13:30 IST). Domestic interbank "
            "spot market operates ~9:00-15:30 IST. NSE currency derivatives close 17:00 IST. "
            "Yahoo daily bar aligned to approximate interbank close ~15:30 IST."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. Yahoo USDINR=X semantics differ from "
            "RBI/FBIL reference rate. No historical Yahoo publication timestamp available. "
            "Interbank close ~15:30 IST used as conservative proxy."
        ),
        provider_availability_observed=False,
        snapshot_a_eligibility_note=(
            "Snapshot A eligibility is based on an explicit conservative modeling "
            "assumption that the provider value is available at interbank close (~15:30 IST). "
            "Historical Yahoo publication time is unavailable and therefore this boundary "
            "condition is not empirically verified. Same boundary case as INDIA_VIX/NIFTY_BANK."
        ),
        notes=(
            "USD/INR spot exchange rate (OTC/interbank aggregation via Yahoo, NOT RBI "
            "reference rate). Instrument close: ~15:30 IST. Provider: Yahoo Finance "
            "(USDINR=X). Provider availability: unknown (assumed at interbank close)."
        ),
    ),
    "INDIA_10Y_YIELD": AvailabilitySpec(
        variable_name="INDIA_10Y_YIELD",
        instrument="IN10Y=RR",
        category=ContextCategory.DOMESTIC_RATES,
        native_timezone="Asia/Kolkata",
        market_close_time=time(16, 30, 0),
        lag_minutes_to_availability=15,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "India 10-Year Benchmark Sovereign Bond Yield (CCIL/NDS-OM platform). "
            "NDS-OM trading closes at 17:00 IST; CCIL settlement/valuation around 16:30 IST."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. No historical Yahoo publication "
            "timestamp available. Instrument close 16:30 IST + 15 min buffer = 16:45 IST "
            "used as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "India 10-Year Benchmark Sovereign Bond Yield (CCIL/NDS-OM). "
            "Instrument close: 16:30 IST + 15m assumed buffer = 16:45 IST. "
            "Provider: Yahoo Finance (IN10Y=RR). "
            "Provider availability: unknown (assumed at instrument close + buffer)."
        ),
    ),

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Global US Variables
    # ──────────────────────────────────────────────────────────────────────────
    "SP500": AvailabilitySpec(
        variable_name="SP500",
        instrument="^GSPC",
        category=ContextCategory.GLOBAL_EQUITY,
        native_timezone="America/New_York",
        market_close_time=time(16, 0, 0),
        lag_minutes_to_availability=30,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "S&P 500 Index (NYSE/NASDAQ composite). Regular session close: 16:00 EST/EDT. "
            "Closing cross/auction finalizes by ~16:05-16:10."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. No historical Yahoo publication "
            "timestamp available. Instrument close 16:00 + 30 min buffer used as "
            "conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "S&P 500 Index US large-cap benchmark. Instrument close: 16:00 EST/EDT "
            "+ 30m assumed buffer. Provider: Yahoo Finance (^GSPC). "
            "Provider availability: unknown (assumed at instrument close + buffer)."
        ),
    ),
    "NASDAQ": AvailabilitySpec(
        variable_name="NASDAQ",
        instrument="^IXIC",
        category=ContextCategory.GLOBAL_EQUITY,
        native_timezone="America/New_York",
        market_close_time=time(16, 0, 0),
        lag_minutes_to_availability=30,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "Nasdaq Composite Index. Regular session close: 16:00 EST/EDT. "
            "Closing cross finalizes by ~16:05-16:10."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. No historical Yahoo publication "
            "timestamp available. Instrument close 16:00 + 30 min buffer used as "
            "conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "Nasdaq Composite US benchmark. Instrument close: 16:00 EST/EDT "
            "+ 30m assumed buffer. Provider: Yahoo Finance (^IXIC). "
            "Provider availability: unknown (assumed at instrument close + buffer)."
        ),
    ),
    "DOW_JONES": AvailabilitySpec(
        variable_name="DOW_JONES",
        instrument="^DJI",
        category=ContextCategory.GLOBAL_EQUITY,
        native_timezone="America/New_York",
        market_close_time=time(16, 0, 0),
        lag_minutes_to_availability=30,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "Dow Jones Industrial Average (30 large-cap US stocks). "
            "Regular session close: 16:00 EST/EDT."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. No historical Yahoo publication "
            "timestamp available. Instrument close 16:00 + 30 min buffer used as "
            "conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "Dow Jones Industrial Average. Instrument close: 16:00 EST/EDT "
            "+ 30m assumed buffer. Provider: Yahoo Finance (^DJI). "
            "Provider availability: unknown (assumed at instrument close + buffer)."
        ),
    ),
    "US_VIX": AvailabilitySpec(
        variable_name="US_VIX",
        instrument="^VIX",
        category=ContextCategory.GLOBAL_VOLATILITY,
        native_timezone="America/New_York",
        market_close_time=time(16, 15, 0),
        lag_minutes_to_availability=15,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "CBOE Volatility Index. SPX options trading closes at 16:15 EST/EDT. "
            "Official VIX settlement value published by CBOE around 16:30 EST/EDT."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. CBOE publishes official VIX "
            "settlement, but Yahoo's publication timing is unknown. "
            "Instrument close 16:15 + 15 min buffer used as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "CBOE Volatility Index (VIX). Instrument close: 16:15 EST/EDT "
            "+ 15m assumed buffer. Provider: Yahoo Finance (^VIX). "
            "Provider availability: unknown (assumed at instrument close + buffer). "
            "Note: CBOE publishes official settlement ~16:30, but Yahoo publication "
            "timing is unverified."
        ),
    ),
    "US_10Y_YIELD": AvailabilitySpec(
        variable_name="US_10Y_YIELD",
        instrument="^TNX",
        category=ContextCategory.GLOBAL_RATES,
        native_timezone="America/New_York",
        market_close_time=time(15, 0, 0),
        lag_minutes_to_availability=30,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "^TNX is the CBOE 10-Year Treasury Note Yield INDEX — not a directly traded "
            "cash Treasury security. Quotation: yield × 10 (e.g., 42.50 = 4.250%). "
            "Derived from CME 10-year T-Note futures pricing, not directly from the "
            "cash bond market (which trades 7:00-17:00 EST). CBOE equity hours: "
            "9:30-16:00 EST, but ^TNX daily bar typically aligned to ~15:00 EST."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. ^TNX is a CBOE-computed yield "
            "index, not a cash Treasury yield. No historical Yahoo publication "
            "timestamp available. Bar close ~15:00 EST + 30 min buffer used as "
            "conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "CBOE 10-Year Treasury Note Yield INDEX (^TNX). Quotation: yield × 10. "
            "Derived from CME T-Note futures, not identical to cash Treasury yield. "
            "Instrument close: ~15:00 EST/EDT + 30m assumed buffer. "
            "Provider: Yahoo Finance (^TNX). "
            "Provider availability: unknown (assumed at instrument close + buffer)."
        ),
    ),
    "BRENT_CRUDE": AvailabilitySpec(
        variable_name="BRENT_CRUDE",
        instrument="BZ=F",
        category=ContextCategory.GLOBAL_COMMODITIES,
        native_timezone="America/New_York",
        market_close_time=time(17, 0, 0),
        lag_minutes_to_availability=30,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "ICE Brent Crude Oil continuous contract (BZ=F). Electronic session close: "
            "17:00 EST. Official daily settlement price determined around 14:30 EST "
            "(pit/settlement window). Yahoo daily bar close is NOT identical to the "
            "official exchange settlement price. BZ=F is a continuous front-month "
            "contract constructed by Yahoo with unspecified rollover methodology."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. Daily bar close ≠ official ICE "
            "settlement price. No historical Yahoo publication timestamp available. "
            "Electronic session close 17:00 + 30 min buffer used as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "ICE Brent Crude Oil continuous contract. Electronic close: 17:00 EST; "
            "official settlement: ~14:30 EST. Yahoo daily bar close ≠ settlement price. "
            "Continuous contract rollover methodology unspecified by Yahoo. "
            "+ 30m assumed buffer. Provider availability: unknown."
        ),
    ),
    "WTI_CRUDE": AvailabilitySpec(
        variable_name="WTI_CRUDE",
        instrument="CL=F",
        category=ContextCategory.GLOBAL_COMMODITIES,
        native_timezone="America/New_York",
        market_close_time=time(17, 0, 0),
        lag_minutes_to_availability=30,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "NYMEX WTI Light Sweet Crude Oil continuous contract (CL=F). Electronic "
            "session close: 17:00 EST. Official daily settlement price at 14:30 EST. "
            "Yahoo daily bar close is NOT identical to the official exchange settlement "
            "price. CL=F is a continuous front-month contract constructed by Yahoo with "
            "unspecified rollover methodology."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. Daily bar close ≠ official NYMEX "
            "settlement price. No historical Yahoo publication timestamp available. "
            "Electronic session close 17:00 + 30 min buffer used as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "NYMEX WTI Crude Oil continuous contract. Electronic close: 17:00 EST; "
            "official settlement: 14:30 EST. Yahoo daily bar close ≠ settlement price. "
            "Continuous contract rollover methodology unspecified by Yahoo. "
            "+ 30m assumed buffer. Provider availability: unknown."
        ),
    ),
    "GOLD": AvailabilitySpec(
        variable_name="GOLD",
        instrument="GC=F",
        category=ContextCategory.GLOBAL_COMMODITIES,
        native_timezone="America/New_York",
        market_close_time=time(17, 0, 0),
        lag_minutes_to_availability=30,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "COMEX Gold Futures continuous contract (GC=F). Electronic session close: "
            "17:00 EST. Official daily settlement price at 13:30 EST. Yahoo daily bar "
            "close is NOT identical to the official exchange settlement price. GC=F is "
            "a continuous front-month contract constructed by Yahoo with unspecified "
            "rollover methodology."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. Daily bar close ≠ official COMEX "
            "settlement price. No historical Yahoo publication timestamp available. "
            "Electronic session close 17:00 + 30 min buffer used as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "COMEX Gold continuous contract. Electronic close: 17:00 EST; "
            "official settlement: 13:30 EST. Yahoo daily bar close ≠ settlement price. "
            "Continuous contract rollover methodology unspecified by Yahoo. "
            "+ 30m assumed buffer. Provider availability: unknown."
        ),
    ),
    "DXY": AvailabilitySpec(
        variable_name="DXY",
        instrument="DX-Y.NYB",
        category=ContextCategory.GLOBAL_FX,
        native_timezone="America/New_York",
        market_close_time=time(17, 0, 0),
        lag_minutes_to_availability=30,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "US Dollar Index on ICE Futures US (DX-Y.NYB). Electronic session close: "
            "17:00 EST. Represents trade-weighted USD vs basket of 6 currencies."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. No historical Yahoo publication "
            "timestamp available. Electronic session close 17:00 + 30 min buffer used "
            "as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "US Dollar Index (ICE Futures US). Electronic close: 17:00 EST "
            "+ 30m assumed buffer. Provider: Yahoo Finance (DX-Y.NYB). "
            "Provider availability: unknown (assumed at session close + buffer)."
        ),
    ),

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Major Asian Benchmarks
    # ──────────────────────────────────────────────────────────────────────────
    "NIKKEI_225": AvailabilitySpec(
        variable_name="NIKKEI_225",
        instrument="^N225",
        category=ContextCategory.GLOBAL_EQUITY,
        native_timezone="Asia/Tokyo",
        market_close_time=time(15, 0, 0),
        lag_minutes_to_availability=15,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "Nikkei 225 (Tokyo Stock Exchange). Afternoon session close: 15:00 JST "
            "(= 11:30 IST). Closing auction finalizes by ~15:05 JST."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. TSE publishes official close, "
            "but Yahoo's publication timing is unknown. Instrument close 15:00 JST "
            "+ 15 min buffer used as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "Nikkei 225 (TSE). Instrument close: 15:00 JST + 15m assumed buffer "
            "= 11:45 IST. Provider: Yahoo Finance (^N225). "
            "Provider availability: unknown (assumed at instrument close + buffer)."
        ),
    ),
    "HANG_SENG": AvailabilitySpec(
        variable_name="HANG_SENG",
        instrument="^HSI",
        category=ContextCategory.GLOBAL_EQUITY,
        native_timezone="Asia/Hong_Kong",
        market_close_time=time(16, 0, 0),
        lag_minutes_to_availability=15,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "Hang Seng Index (HKEX). Afternoon session close: 16:00 HKT (= 13:30 IST). "
            "Closing auction period ends ~16:08-16:10 HKT."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. HKEX publishes official close, "
            "but Yahoo's publication timing is unknown. Instrument close 16:00 HKT "
            "+ 15 min buffer used as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "Hang Seng Index (HKEX). Instrument close: 16:00 HKT + 15m assumed buffer "
            "= 13:45 IST. Provider: Yahoo Finance (^HSI). "
            "Provider availability: unknown (assumed at instrument close + buffer)."
        ),
    ),
    "FTSE_100": AvailabilitySpec(
        variable_name="FTSE_100",
        instrument="^FTSE",
        category=ContextCategory.GLOBAL_EQUITY,
        native_timezone="Europe/London",
        market_close_time=time(16, 30, 0),
        lag_minutes_to_availability=15,
        missing_policy=MissingPolicy.FORWARD_FILL_CALENDAR,
        provider_tier=ProviderTier.FREE,
        availability_timestamp_type=AvailabilityTimestampType.ASSUMED_SCHEDULE,
        instrument_timestamp_description=(
            "FTSE 100 Index (London Stock Exchange). Regular session close: 16:30 "
            "GMT/BST (= 21:00/22:00 IST). Closing auction finalizes by ~16:35."
        ),
        provider_availability_basis=(
            "Yahoo Finance daily bar timestamp only. LSE publishes official close, "
            "but Yahoo's publication timing is unknown. Instrument close 16:30 "
            "GMT/BST + 15 min buffer used as conservative proxy."
        ),
        provider_availability_observed=False,
        notes=(
            "FTSE 100 Index (LSE). Instrument close: 16:30 GMT/BST + 15m assumed buffer. "
            "Provider: Yahoo Finance (^FTSE). "
            "Provider availability: unknown (assumed at instrument close + buffer)."
        ),
    ),
}


def compute_availability_timestamp(
    observation_date: date,
    spec: AvailabilitySpec,
) -> datetime:
    """Calculate the precise availability timestamp in UTC and Asia/Kolkata for a market session.

    Handles Daylight Saving Time (DST) automatically via native zoneinfo.
    """
    tz = ZoneInfo(spec.native_timezone)
    local_dt = datetime.combine(observation_date, spec.market_close_time, tzinfo=tz)
    avail_local = local_dt + timedelta(minutes=spec.lag_minutes_to_availability)
    # Convert directly to Asia/Kolkata
    return avail_local.astimezone(TIMEZONE_KOLKATA)


__all__ = [
    "TIMEZONE_KOLKATA",
    "TIMEZONE_NEW_YORK",
    "TIMEZONE_TOKYO",
    "TIMEZONE_HONG_KONG",
    "TIMEZONE_LONDON",
    "CANONICAL_CONTEXT_SPECS",
    "compute_availability_timestamp",
]
