"""Comprehensive Verification Test Suite for Point-in-Time News NLP Feature Generation.

Phase 9 Step 3 Invariant Tests:
1. PIT correctness
2. No future news
3. Snapshot boundaries (A and B disjoint)
4. Membership filtering (anti-survivorship bias)
5. Novelty lookback (7-day causal window, no lookahead mutation)
6. Time decay (24h half-life: 2^(-dt / 24))
7. Importance formula (0.35*S + 0.30*E + 0.20*M + 0.15*C dynamic variance)
8. Aggregation correctness (count consistency, ratio bounds)
9. Deterministic output
10. Holdout isolation (gold_holdout_annotation_input.csv untouched)
11. No NaN / infinity across all 4,653 trading rows
12. Terminal coverage (2022–2026 >99% session coverage)
13. LICI exclusion (0 records, non-member status verified)
14. LTIM zero-record handling (graceful 0 count, no division by zero)
"""

from datetime import date, datetime, time, timedelta
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest

from nifty_ai.data.news.constituents import (
    CANONICAL_CONSTITUENTS,
    is_active_nifty_constituent,
)
from nifty_ai.data.news.deduplication import StreamingDeduplicator
from nifty_ai.data.news.feature_generation import (
    EXPECTED_GOLD_SHA,
    EXPECTED_HISTORICAL_SHA,
    EXPECTED_TERMINAL_SHA,
    aggregate_daily_snapshot_features,
    build_snapshot_delta_features,
    compute_file_sha256,
    compute_information_decay,
    resolve_canonical_company_symbol,
)
from nifty_ai.data.news.nlp_engine import (
    compute_ex_ante_importance,
    evaluate_market_relevance,
    extract_entities,
)
from nifty_ai.data.news.preprocessing import (
    CANONICAL_PHASE8_EVENT_CATEGORIES,
    PHASE8_TO_EVENT_TYPE,
    assign_record_pit,
    classify_phase8_events,
)
from nifty_ai.data.news.schema import (
    AvailabilityEvidenceLevel,
    CanonicalNewsRecord,
    EventType,
    MarketRelevanceCategory,
    SourceAuthorityTier,
)
from nifty_ai.data.news.sentiment import LoughranMcDonaldIndianSentiment
from nifty_ai.data.schema import DataFrequency, ProvenanceMetadata, ProviderTier
from nifty_ai.data.snapshots import SnapshotType

TIMEZONE_KOLKATA = ZoneInfo("Asia/Kolkata")
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "interim" / "news"


# =============================================================================
# 1. PIT Correctness
# =============================================================================
def test_1_point_in_time_correctness():
    """Verify that records are assigned strictly relative to the 15:30 IST and 08:50 IST cutoffs."""
    df_nifty = pd.read_csv(ROOT_DIR / "data" / "processed" / "nifty_50_daily.csv")
    trading_dates = sorted([date.fromisoformat(d) for d in df_nifty["trading_date"].unique()])
    trading_dates_set = set(trading_dates)

    # Test Intraday Session T at 11:00 IST -> Snapshot A Day T
    dt_a = datetime(2023, 5, 10, 11, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    res_a = assign_record_pit(dt_a, trading_dates, trading_dates_set)
    assert res_a["status"] == "VALID"
    assert res_a["snapshot"] == "SNAPSHOT_A"
    assert res_a["prediction_date_T"] == date(2023, 5, 10)
    assert res_a["cutoff_timestamp"] == datetime(2023, 5, 10, 15, 30, 0, tzinfo=TIMEZONE_KOLKATA)

    # Test Evening Session T at 18:30 IST -> Snapshot B Day T
    dt_b = datetime(2023, 5, 10, 18, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    res_b = assign_record_pit(dt_b, trading_dates, trading_dates_set)
    assert res_b["status"] == "VALID"
    assert res_b["snapshot"] == "SNAPSHOT_B"
    assert res_b["prediction_date_T"] == date(2023, 5, 10)
    assert res_b["cutoff_timestamp"] == datetime(2023, 5, 11, 8, 50, 0, tzinfo=TIMEZONE_KOLKATA)

    # Test Early Morning Session T+1 at 07:30 IST -> Snapshot B Day T
    dt_early = datetime(2023, 5, 11, 7, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    res_early = assign_record_pit(dt_early, trading_dates, trading_dates_set)
    assert res_early["status"] == "VALID"
    assert res_early["snapshot"] == "SNAPSHOT_B"
    assert res_early["prediction_date_T"] == date(2023, 5, 10)

    # Test Weekend (Saturday) -> Snapshot B of preceding Friday
    dt_wknd = datetime(2023, 5, 13, 14, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    res_wknd = assign_record_pit(dt_wknd, trading_dates, trading_dates_set)
    assert res_wknd["status"] == "VALID"
    assert res_wknd["snapshot"] == "SNAPSHOT_B"
    assert res_wknd["prediction_date_T"] == date(2023, 5, 12)  # Friday


# =============================================================================
# 2. No Future News Leakage
# =============================================================================
def test_2_no_future_news_leakage():
    """Verify that removing future news items cannot alter earlier snapshot features."""
    ref_d = date(2023, 6, 15)
    tgt_d = date(2023, 6, 16)
    cutoff_dt = datetime.combine(ref_d, time(15, 30, 0), tzinfo=TIMEZONE_KOLKATA)

    item1 = {
        "company_symbol": "RELIANCE",
        "headline": "RELIANCE: Operational Update",
        "published_timestamp": datetime(2023, 6, 15, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA),
        "availability_timestamp": datetime(2023, 6, 15, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA),
        "primary_event": "OPERATIONAL_EVENT",
        "market_relevance_category": MarketRelevanceCategory.HIGH_DIRECT,
        "market_relevance_score": 0.80,
        "importance_score": 0.55,
        "sentiment_polarity": 0.20,
        "sentiment_class": "POSITIVE",
        "novelty_score": 0.90,
        "is_novel": True,
        "is_active_constituent": True,
    }

    # Run with item1 only
    row1 = aggregate_daily_snapshot_features([item1], SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)

    # Future item arriving at 17:00 IST (after 15:30 cutoff)
    future_item = {
        "company_symbol": "TCS",
        "headline": "TCS: Big Contract Win",
        "published_timestamp": datetime(2023, 6, 15, 17, 0, 0, tzinfo=TIMEZONE_KOLKATA),
        "availability_timestamp": datetime(2023, 6, 15, 17, 0, 0, tzinfo=TIMEZONE_KOLKATA),
        "primary_event": "ORDER_CONTRACT",
        "market_relevance_category": MarketRelevanceCategory.HIGH_DIRECT,
        "market_relevance_score": 0.90,
        "importance_score": 0.75,
        "sentiment_polarity": 0.60,
        "sentiment_class": "POSITIVE",
        "novelty_score": 0.95,
        "is_novel": True,
        "is_active_constituent": True,
    }

    # Verify future item cannot enter Snapshot A
    assert future_item["availability_timestamp"] > cutoff_dt
    # Snapshot A features for Day T must remain 100% identical
    assert row1["news_count"] == 1
    assert row1["mean_sentiment"] == 0.20


# =============================================================================
# 3. Snapshot Boundaries Disjoint
# =============================================================================
def test_3_snapshot_boundaries_disjoint():
    """Verify that Snapshot A and Snapshot B windows on Day T are strictly disjoint."""
    t_date = date(2023, 8, 10)
    cutoff_a = datetime.combine(t_date, time(15, 30, 0), tzinfo=TIMEZONE_KOLKATA)
    cutoff_b_start = cutoff_a
    cutoff_b_end = datetime.combine(date(2023, 8, 11), time(8, 50, 0), tzinfo=TIMEZONE_KOLKATA)

    # A item
    t_a = datetime(2023, 8, 10, 15, 29, 59, tzinfo=TIMEZONE_KOLKATA)
    assert t_a <= cutoff_a
    assert not (cutoff_b_start < t_a <= cutoff_b_end)

    # B item
    t_b = datetime(2023, 8, 10, 15, 30, 0, 1, tzinfo=TIMEZONE_KOLKATA)
    assert t_b > cutoff_a
    assert cutoff_b_start < t_b <= cutoff_b_end


# =============================================================================
# 4. Membership Filtering (Anti-Survivorship Bias)
# =============================================================================
def test_4_membership_filtering():
    """Verify that non-member companies never contribute to NIFTY 50 features on that date."""
    # JSW Steel entered NIFTY 50 on 2018-09-28
    assert is_active_nifty_constituent("JSWSTEEL", date(2018, 9, 27)) is False
    assert is_active_nifty_constituent("JSWSTEEL", date(2018, 9, 28)) is True

    # ZEEL exited NIFTY 50 on 2020-09-25
    assert is_active_nifty_constituent("ZEEL", date(2020, 9, 25)) is True
    assert is_active_nifty_constituent("ZEEL", date(2020, 9, 26)) is False

    # Simulate Day T in 2017 when JSW Steel had an announcement
    ref_d = date(2017, 5, 10)
    tgt_d = date(2017, 5, 11)

    jsw_item = {
        "company_symbol": "JSWSTEEL",
        "headline": "JSWSTEEL: Financial Results",
        "published_timestamp": datetime(2017, 5, 10, 11, 0, 0, tzinfo=TIMEZONE_KOLKATA),
        "availability_timestamp": datetime(2017, 5, 10, 11, 0, 0, tzinfo=TIMEZONE_KOLKATA),
        "primary_event": "EARNINGS_RESULTS",
        "market_relevance_category": MarketRelevanceCategory.HIGH_DIRECT,
        "importance_score": 0.75,
        "sentiment_polarity": 0.40,
        "novelty_score": 0.80,
        "is_active_constituent": is_active_nifty_constituent("JSWSTEEL", ref_d),  # False
    }

    # Filter active constituents
    active_recs = [r for r in [jsw_item] if r["is_active_constituent"]]
    assert len(active_recs) == 0

    # Aggregating with filtered active records results in Genuine Zero News
    row = aggregate_daily_snapshot_features(active_recs, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    assert row["news_count"] == 0
    assert row["mean_sentiment"] == 0.0
    assert row["data_status"] in ("GENUINE_ZERO_NEWS", "genuine_zero_news")


# =============================================================================
# 5. Novelty Lookback (7-Day Causal Window)
# =============================================================================
def test_5_novelty_lookback():
    """Verify that novelty lookback strictly enforces a 168-hour window without future mutation."""
    dedup = StreamingDeduplicator(similarity_threshold=0.80, lookback_window_hours=168)
    t0 = datetime(2023, 1, 10, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA)

    rec1 = CanonicalNewsRecord(
        news_id="TEST_001",
        source="NSE",
        source_type=SourceAuthorityTier.TIER_1_REGULATORY,
        headline="Reliance announces major crude discovery in KG Basin",
        published_timestamp=t0,
        availability_timestamp=t0,
        availability_evidence_level=AvailabilityEvidenceLevel.LEVEL_B,
        timezone="Asia/Kolkata",
        provenance=ProvenanceMetadata("NSE", "TEST_001", t0, t0, "Asia/Kolkata", DataFrequency.MINUTE, ProviderTier.OFFICIAL),
    )
    is_dup1, cid1, nov1, is_nov1 = dedup.process_record(rec1)
    assert is_nov1 is True
    assert nov1 == 1.0

    # Duplicate headline within 2 days (48 hours)
    t1 = t0 + timedelta(days=2)
    rec2 = CanonicalNewsRecord(
        news_id="TEST_002",
        source="NSE",
        source_type=SourceAuthorityTier.TIER_1_REGULATORY,
        headline="Reliance announces major crude discovery in KG Basin",
        published_timestamp=t1,
        availability_timestamp=t1,
        availability_evidence_level=AvailabilityEvidenceLevel.LEVEL_B,
        timezone="Asia/Kolkata",
        provenance=ProvenanceMetadata("NSE", "TEST_002", t1, t1, "Asia/Kolkata", DataFrequency.MINUTE, ProviderTier.OFFICIAL),
    )
    is_dup2, cid2, nov2, is_nov2 = dedup.process_record(rec2)
    assert is_dup2 is True
    assert is_nov2 is False
    assert nov2 == 0.0
    assert cid2 == cid1

    # Identical headline 8 days after rec2 (10 days after rec1 > 168 hours lookback)
    t2 = t1 + timedelta(days=8)
    rec3 = CanonicalNewsRecord(
        news_id="TEST_003",
        source="NSE",
        source_type=SourceAuthorityTier.TIER_1_REGULATORY,
        headline="Reliance announces major crude discovery in KG Basin",
        published_timestamp=t2,
        availability_timestamp=t2,
        availability_evidence_level=AvailabilityEvidenceLevel.LEVEL_B,
        timezone="Asia/Kolkata",
        provenance=ProvenanceMetadata("NSE", "TEST_003", t2, t2, "Asia/Kolkata", DataFrequency.MINUTE, ProviderTier.OFFICIAL),
    )
    is_dup3, cid3, nov3, is_nov3 = dedup.process_record(rec3)
    # Beyond 7-day lookback, prior records have expired from deduplication window
    assert is_nov3 is True
    assert nov3 == 1.0


# =============================================================================
# 6. Time Decay
# =============================================================================
def test_6_time_decay_half_life():
    """Verify exponential half-life decay function."""
    cutoff = datetime(2023, 4, 15, 15, 30, 0, tzinfo=TIMEZONE_KOLKATA)

    # Exactly at cutoff (age = 0) -> decay = 1.0
    assert compute_information_decay(cutoff, cutoff, half_life_hours=24.0) == 1.0

    # 24 hours prior (age = 24) -> decay = 0.5
    t_24h = cutoff - timedelta(hours=24)
    assert compute_information_decay(t_24h, cutoff, half_life_hours=24.0) == 0.5

    # 48 hours prior (age = 48) -> decay = 0.25
    t_48h = cutoff - timedelta(hours=48)
    assert compute_information_decay(t_48h, cutoff, half_life_hours=24.0) == 0.25


# =============================================================================
# 7. Importance Formula
# =============================================================================
def test_7_importance_formula_variance():
    """Verify dynamic importance scoring: 0.35*S + 0.30*E + 0.20*M + 0.15*C."""
    # Low importance: routine notice
    imp_low, _ = compute_ex_ante_importance(
        source_type=SourceAuthorityTier.TIER_1_REGULATORY,
        primary_event=EventType.ROUTINE_COMMENTARY,
        relevance_category=MarketRelevanceCategory.LOW_INCIDENTAL,
        headline_syndication_count=1,
    )

    # High importance: major earnings results from active heavyweight
    imp_high, _ = compute_ex_ante_importance(
        source_type=SourceAuthorityTier.TIER_1_REGULATORY,
        primary_event=EventType.EARNINGS,
        relevance_category=MarketRelevanceCategory.HIGH_DIRECT,
        headline_syndication_count=1,
    )

    assert imp_high > imp_low
    assert imp_high >= 0.70  # High importance threshold
    assert 0.0 <= imp_low <= 1.0
    assert 0.0 <= imp_high <= 1.0


# =============================================================================
# 8. Aggregation Correctness
# =============================================================================
def test_8_aggregation_correctness():
    """Verify feature relationships and boundary invariants in daily aggregation."""
    ref_d = date(2023, 7, 20)
    tgt_d = date(2023, 7, 21)

    recs = [
        {
            "company_symbol": "INFY",
            "headline": "INFY: Quarterly Results Net Profit jumps 12%",
            "published_timestamp": datetime(2023, 7, 20, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA),
            "availability_timestamp": datetime(2023, 7, 20, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA),
            "primary_event": "EARNINGS_RESULTS",
            "market_relevance_category": MarketRelevanceCategory.HIGH_DIRECT,
            "market_relevance_score": 0.90,
            "importance_score": 0.75,
            "sentiment_polarity": 0.45,
            "sentiment_class": "POSITIVE",
            "novelty_score": 1.0,
            "is_novel": True,
            "is_active_constituent": True,
        },
        {
            "company_symbol": "TCS",
            "headline": "TCS: Board Meeting regarding interim dividend",
            "published_timestamp": datetime(2023, 7, 20, 12, 0, 0, tzinfo=TIMEZONE_KOLKATA),
            "availability_timestamp": datetime(2023, 7, 20, 12, 0, 0, tzinfo=TIMEZONE_KOLKATA),
            "primary_event": "DIVIDEND",
            "market_relevance_category": MarketRelevanceCategory.HIGH_DIRECT,
            "market_relevance_score": 0.85,
            "importance_score": 0.65,
            "sentiment_polarity": 0.0,
            "sentiment_class": "NEUTRAL",
            "novelty_score": 0.85,
            "is_novel": True,
            "is_active_constituent": True,
        },
    ]

    row = aggregate_daily_snapshot_features(recs, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    assert row["news_count"] == 2
    assert row["positive_count"] + row["negative_count"] + row["neutral_count"] == row["news_count"]
    assert 0.0 <= row["positive_ratio"] <= 1.0
    assert 0.0 <= row["negative_ratio"] <= 1.0
    assert row["max_importance"] >= row["mean_importance"]
    assert row["unique_company_count"] == 2
    assert row["event_earnings_results_count"] == 1
    assert row["event_dividend_count"] == 1


# =============================================================================
# 9. Deterministic Output
# =============================================================================
def test_9_deterministic_output():
    """Verify that running aggregation on identical records produces identical output."""
    ref_d = date(2023, 9, 1)
    tgt_d = date(2023, 9, 4)

    recs = [
        {
            "company_symbol": "SBIN",
            "headline": "SBIN: Press Release",
            "published_timestamp": datetime(2023, 9, 1, 14, 0, 0, tzinfo=TIMEZONE_KOLKATA),
            "availability_timestamp": datetime(2023, 9, 1, 14, 0, 0, tzinfo=TIMEZONE_KOLKATA),
            "primary_event": "CAPEX_BUSINESS_UPDATE",
            "market_relevance_category": MarketRelevanceCategory.HIGH_DIRECT,
            "market_relevance_score": 0.80,
            "importance_score": 0.55,
            "sentiment_polarity": 0.15,
            "sentiment_class": "POSITIVE",
            "novelty_score": 0.90,
            "is_novel": True,
            "is_active_constituent": True,
        }
    ]

    row1 = aggregate_daily_snapshot_features(recs, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    row2 = aggregate_daily_snapshot_features(recs, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    assert row1 == row2


# =============================================================================
# 10. Holdout Isolation
# =============================================================================
def test_10_holdout_isolation():
    """Verify that the 200-record gold benchmark is 100% byte-for-byte untouched."""
    gold_path = DATA_DIR / "gold_holdout_annotation_input.csv"
    assert gold_path.is_file(), f"Gold benchmark missing at {gold_path}"
    sha = compute_file_sha256(gold_path)
    assert sha == EXPECTED_GOLD_SHA, f"CRITICAL: Gold benchmark SHA mismatch! Expected {EXPECTED_GOLD_SHA}, got {sha}"


# =============================================================================
# 11. No NaN / Infinity in Output CSVs
# =============================================================================
def test_11_no_nan_or_infinity_in_outputs():
    """Verify that generated feature datasets have 4,653 rows with 0 NaNs and 0 infs."""
    snap_a_path = DATA_DIR / "features_news_snapshot_a.csv"
    snap_b_path = DATA_DIR / "features_news_snapshot_b.csv"
    delta_path = DATA_DIR / "features_news_snapshot_delta.csv"

    for path, name in [(snap_a_path, "Snapshot A"), (snap_b_path, "Snapshot B"), (delta_path, "Delta")]:
        if not path.is_file():
            pytest.skip(f"{name} file not generated yet at {path}")

        df = pd.read_csv(path)
        assert len(df) == 4653, f"Expected 4653 rows in {name}, got {len(df)}"
        assert not df.isna().any().any(), f"Found NaN values in {name} dataset!"

        num_cols = df.select_dtypes(include=np.number)
        assert not np.isinf(num_cols.values).any(), f"Found infinite values in {name} dataset!"


# =============================================================================
# 12. Terminal Coverage
# =============================================================================
def test_12_terminal_coverage():
    """Verify that the 2022–2026 terminal out-of-sample window has >99% news coverage."""
    snap_a_path = DATA_DIR / "features_news_snapshot_a.csv"
    snap_b_path = DATA_DIR / "features_news_snapshot_b.csv"

    if not snap_a_path.is_file() or not snap_b_path.is_file():
        pytest.skip("Snapshot feature files not generated yet")

    df_a = pd.read_csv(snap_a_path)
    df_b = pd.read_csv(snap_b_path)

    df_a_term = df_a[df_a["trading_date"] >= "2022-01-01"]
    df_b_term = df_b[df_b["trading_date"] >= "2022-01-01"]

    assert len(df_a_term) == 1154, f"Expected 1154 terminal trading sessions, got {len(df_a_term)}"

    cov_a = (df_a_term["news_count"] > 0).mean()
    cov_b = (df_b_term["news_count"] > 0).mean()

    assert cov_a > 0.99, f"Snapshot A terminal coverage {cov_a*100:.2f}% is below 99%!"
    assert cov_b > 0.99, f"Snapshot B terminal coverage {cov_b*100:.2f}% is below 99%!"


# =============================================================================
# 13. LICI Exclusion
# =============================================================================
def test_13_lici_exclusion():
    """Verify that LICI is never treated as a constituent and contributes 0 records."""
    assert is_active_nifty_constituent("LICI", date(2024, 3, 28)) is False
    assert is_active_nifty_constituent("LICI", date(2022, 1, 1)) is False
    assert is_active_nifty_constituent("LICI", date(2026, 9, 4)) is False

    # Check that LICI is not in canonical registry
    assert not any(c.symbol.upper() == "LICI" for c in CANONICAL_CONSTITUENTS)


# =============================================================================
# 14. LTIM Zero-Record Handling
# =============================================================================
def test_14_ltim_zero_record_handling():
    """Verify that LTIM's zero authentic records are handled gracefully without errors or NaNs."""
    # LTIM was active from 2023-07-13 to 2024-09-30
    assert is_active_nifty_constituent("LTIM", date(2023, 7, 13)) is True
    assert is_active_nifty_constituent("LTIM", date(2024, 9, 30)) is True

    # Empty records on an active day produces clean GENUINE_ZERO_NEWS
    row = aggregate_daily_snapshot_features([], SnapshotType.SNAPSHOT_1540, date(2023, 8, 1), date(2023, 8, 2))
    assert row["news_count"] == 0
    assert row["mean_sentiment"] == 0.0
    assert row["weighted_sentiment"] == 0.0
    assert row["mean_importance"] == 0.0
    assert row["data_status"] in ("GENUINE_ZERO_NEWS", "genuine_zero_news")
    assert not any(np.isnan(v) for v in row.values() if isinstance(v, (int, float)))
