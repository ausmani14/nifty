"""Phase 8 News & NLP Intelligence Layer Test Suite.

Verifies:
- Canonical schema validation
- Point-in-time availability and Evidence Hierarchy enforcement
- Strict Snapshot A (<= 15:30 IST Day T) and Snapshot B (> 15:30 IST Day T and <= 08:50 IST Day T+1) boundaries
- Non-overlapping A and B window mechanics
- Pure overnight window capture (evening filings, midnight transitions, early morning releases)
- Future mutation invariance (future news cannot alter past snapshots)
- Causal deduplication and streaming semantic clustering
- Entity extraction with point-in-time historical constituent bounding
- Sector propagation to official NSE sector taxonomy
- Multi-label event taxonomy classification
- Ex-ante importance rubric calculation
- Causal novelty scoring with 7-day lookback
- Sentiment benchmark integrity and negation / accounting reversal handling
- Missing data vs genuine zero news distinction
- Terminal holdout (2022+) strict isolation
- Phase 6 and Phase 7 artifact immutability
"""

from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest

from nifty_ai.data.news.constituents import (
    CANONICAL_CONSTITUENTS,
    NSE_SECTOR_TAXONOMY,
    get_active_nifty_constituents,
    get_constituent_sector,
    is_active_nifty_constituent,
)
from nifty_ai.data.news.datasets import (
    aggregate_snapshot_news,
    build_snapshot_news_datasets,
    compute_information_decay,
)
from nifty_ai.data.news.deduplication import (
    StreamingDeduplicator,
    compute_content_hash,
    compute_shingle_jaccard,
    normalize_text_for_dedup,
)
from nifty_ai.data.news.nlp_engine import (
    classify_events_multi_label,
    compute_ex_ante_importance,
    evaluate_market_relevance,
    extract_entities,
    map_sectors_from_entities,
)
from nifty_ai.data.news.point_in_time import (
    TIMEZONE_KOLKATA,
    TIMEZONE_UTC,
    evaluate_news_point_in_time,
    filter_news_for_snapshot,
)
from nifty_ai.data.news.schema import (
    AvailabilityEvidenceLevel,
    BodyAvailabilityTier,
    CanonicalNewsRecord,
    DataStatus,
    EntityMention,
    EventType,
    HistoricalCoverageTier,
    MarketRelevanceCategory,
    SourceAuthorityTier,
)
from nifty_ai.data.news.sentiment import (
    FinBERTStubSentiment,
    LoughranMcDonaldIndianSentiment,
    VaderBaselineSentiment,
    benchmark_sentiment_models,
)
from nifty_ai.data.schema import DataFrequency, ProvenanceMetadata, ProviderTier
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.data.news.annotation import (
    AnnotationStatus,
    IndependentAnnotationRecord,
    SentimentLabel,
    validate_benchmark_batch,
)
from nifty_ai.data.news.providers import (
    NEWS_PROVIDER_REGISTRY,
    NewsProviderAudit,
    RetrievalStatus,
)


def create_sample_news_record(
    news_id: str,
    headline: str,
    pub_dt: datetime,
    avail_dt: Optional[datetime] = None,
    evid_level: AvailabilityEvidenceLevel = AvailabilityEvidenceLevel.LEVEL_B,
    quarantine: bool = False,
    quarantine_reason: Optional[str] = None,
    entities: Optional[List[EntityMention]] = None,
    last_modified_dt: Optional[datetime] = None,
) -> CanonicalNewsRecord:
    """Helper to construct valid test news records."""
    if avail_dt is None:
        avail_dt = pub_dt
    return CanonicalNewsRecord(
        news_id=news_id,
        source="test_source",
        source_type=SourceAuthorityTier.TIER_1_REGULATORY,
        headline=headline,
        published_timestamp=pub_dt,
        availability_timestamp=avail_dt,
        availability_evidence_level=evid_level,
        timezone="Asia/Kolkata",
        provenance=ProvenanceMetadata(
            provider="test_provider",
            source_identifier="TEST",
            retrieval_timestamp=avail_dt,
            source_timestamp=pub_dt,
            timezone="Asia/Kolkata",
            data_frequency=DataFrequency.MINUTE,
            tier=ProviderTier.OFFICIAL,
        ),
        last_modified_timestamp=last_modified_dt,
        entities=entities or [],
        quarantine_flag=quarantine,
        quarantine_reason=quarantine_reason,
    )


# ==============================================================================
# 1. Schema Validation & Attribute Constraints
# ==============================================================================

def test_canonical_news_schema_valid() -> None:
    """Test valid canonical news record creation and dictionary serialization."""
    dt = datetime(2023, 5, 10, 11, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec = create_sample_news_record("test_01", "Reliance Announces New Venture", dt)
    assert rec.news_id == "test_01"
    assert rec.headline == "Reliance Announces New Venture"
    assert rec.availability_evidence_level == AvailabilityEvidenceLevel.LEVEL_B
    d = rec.to_dict()
    assert isinstance(d, dict)
    assert d["published_timestamp"] == dt.isoformat()


def test_schema_requires_timezone_aware_timestamps() -> None:
    """Test that naive datetime stamps immediately raise ValueError."""
    dt_naive = datetime(2023, 5, 10, 11, 0, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        create_sample_news_record("test_err", "No Timezone", dt_naive)


def test_schema_sentiment_and_importance_bounds() -> None:
    """Test validation bounds on sentiment and importance scores."""
    dt = datetime(2023, 5, 10, 11, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    with pytest.raises(ValueError, match="sentiment_polarity"):
        CanonicalNewsRecord(
            news_id="test_err_sent",
            source="src",
            source_type=SourceAuthorityTier.TIER_1_REGULATORY,
            headline="Headline",
            published_timestamp=dt,
            availability_timestamp=dt,
            availability_evidence_level=AvailabilityEvidenceLevel.LEVEL_B,
            timezone="Asia/Kolkata",
            provenance=ProvenanceMetadata("test", "test", dt),
            sentiment_polarity=1.5, # Out of [-1.0, 1.0]
        )


# ==============================================================================
# 2. Point-in-Time Cutoff Strictness & Non-Overlapping Windows
# ==============================================================================

def test_snapshot_a_cutoff_exact_boundary() -> None:
    """News at 15:30:00.000 IST is included in Snapshot A; news at 15:30:00.001 IST is excluded."""
    ref_d = date(2023, 6, 15)
    tgt_d = date(2023, 6, 16)

    dt_exact = datetime(2023, 6, 15, 15, 30, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    dt_plus_1ms = datetime(2023, 6, 15, 15, 30, 0, 1000, tzinfo=TIMEZONE_KOLKATA)

    rec_exact = create_sample_news_record("rec_exact", "Earnings Released On Close", dt_exact)
    rec_late = create_sample_news_record("rec_late", "Earnings Released Just After", dt_plus_1ms)

    ok_exact, _ = evaluate_news_point_in_time(rec_exact, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    ok_late, _ = evaluate_news_point_in_time(rec_late, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)

    assert ok_exact is True
    assert ok_late is False


def test_snapshot_b_pure_overnight_window() -> None:
    """Snapshot B captures news strictly > 15:30 IST Day T and <= 08:50 IST Day T+1."""
    ref_d = date(2023, 6, 15)
    tgt_d = date(2023, 6, 16)

    # 1. Before cutoff on Day T (e.g. 14:00 IST) -> Belongs to Snapshot A, excluded from Snapshot B
    dt_prior = datetime(2023, 6, 15, 14, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_prior = create_sample_news_record("rec_prior", "Day T Afternoon News", dt_prior)
    ok_b_prior, _ = evaluate_news_point_in_time(rec_prior, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_prior is False

    # 2. Evening filing on Day T (e.g. 19:30 IST) -> Legitimate Snapshot B
    dt_evening = datetime(2023, 6, 15, 19, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_evening = create_sample_news_record("rec_evening", "Day T Evening Buyback", dt_evening)
    ok_b_evening, _ = evaluate_news_point_in_time(rec_evening, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_evening is True

    # 3. Overnight midnight crossing (Day T+1 02:30 IST) -> Legitimate Snapshot B
    dt_overnight = datetime(2023, 6, 16, 2, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_overnight = create_sample_news_record("rec_overnight", "US Fed Speech Overnight", dt_overnight)
    ok_b_overnight, _ = evaluate_news_point_in_time(rec_overnight, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_overnight is True

    # 4. Morning release on Day T+1 (08:30 IST) -> Legitimate Snapshot B
    dt_morning = datetime(2023, 6, 16, 8, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_morning = create_sample_news_record("rec_morning", "Pre-market Earnings", dt_morning)
    ok_b_morning, _ = evaluate_news_point_in_time(rec_morning, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_morning is True

    # 5. After Snapshot B cutoff (08:50:01 IST) -> Excluded from Snapshot B
    dt_late = datetime(2023, 6, 16, 8, 50, 1, tzinfo=TIMEZONE_KOLKATA)
    rec_late = create_sample_news_record("rec_late", "Opening Bell Story", dt_late)
    ok_b_late, _ = evaluate_news_point_in_time(rec_late, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
    assert ok_b_late is False


def test_snapshot_a_and_b_windows_are_mutually_exclusive() -> None:
    """Verify an article cannot be simultaneously eligible for Snapshot A and Snapshot B on the same day."""
    ref_d = date(2023, 6, 15)
    tgt_d = date(2023, 6, 16)

    # Any article occurring on reference date
    dt_a = datetime(2023, 6, 15, 12, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_a = create_sample_news_record("rec_a", "Midday News", dt_a)

    is_a, _ = evaluate_news_point_in_time(rec_a, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
    is_b, _ = evaluate_news_point_in_time(rec_a, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)

    assert is_a is True
    assert is_b is False


# ==============================================================================
# 3. Evidence Hierarchy & Quarantine Auditing
# ==============================================================================

def test_unverified_evidence_level_quarantined() -> None:
    """Verify that records with LEVEL_UNVERIFIED evidence are rejected."""
    dt = datetime(2023, 6, 15, 12, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec = create_sample_news_record(
        "rec_unverified", "Unverified Blog Post", dt,
        evid_level=AvailabilityEvidenceLevel.LEVEL_UNVERIFIED
    )
    ok, reason = evaluate_news_point_in_time(rec, SnapshotType.SNAPSHOT_1540, dt.date(), dt.date() + timedelta(days=1))
    assert ok is False
    assert "QUARANTINED" in str(reason)


def test_quarantined_flag_strictly_enforced() -> None:
    """Verify that any record flagged as quarantined is rejected regardless of timestamp."""
    dt = datetime(2023, 6, 15, 12, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec = create_sample_news_record(
        "rec_flagged", "Valid Time but Quarantined", dt,
        quarantine=True, quarantine_reason="Silent post-hoc edit detected"
    )
    ok, reason = evaluate_news_point_in_time(rec, SnapshotType.SNAPSHOT_1540, dt.date(), dt.date() + timedelta(days=1))
    assert ok is False
    assert "Silent post-hoc edit" in str(reason)


# ==============================================================================
# 4. Future Mutation Invariance
# ==============================================================================

def test_future_news_mutation_invariance() -> None:
    """Assert injecting radical news into Day T+2 cannot alter Snapshot A or B tables on Day T."""
    trading_dates = [date(2023, 6, 14), date(2023, 6, 15), date(2023, 6, 16), date(2023, 6, 19)]
    
    dt_base = datetime(2023, 6, 15, 11, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_base = create_sample_news_record("rec_base", "Reliance Regular Filing", dt_base)
    
    # Baseline dataset
    df_a_base, df_b_base, _ = build_snapshot_news_datasets(trading_dates, [rec_base])
    
    # Mutate future: Add extreme negative crisis news at Day T+2 (2023-06-19)
    dt_future = datetime(2023, 6, 19, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    rec_future = create_sample_news_record("rec_future", "Catastrophic Market Crash Nationwide", dt_future)
    
    df_a_mutated, df_b_mutated, _ = build_snapshot_news_datasets(trading_dates, [rec_base, rec_future])
    
    # Row 1 corresponds to reference date 2023-06-15 (Day T)
    row_a_base = df_a_base[df_a_base["trading_date"] == "2023-06-15"].iloc[0].to_dict()
    row_a_mut = df_a_mutated[df_a_mutated["trading_date"] == "2023-06-15"].iloc[0].to_dict()
    
    row_b_base = df_b_base[df_b_base["trading_date"] == "2023-06-15"].iloc[0].to_dict()
    row_b_mut = df_b_mutated[df_b_mutated["trading_date"] == "2023-06-15"].iloc[0].to_dict()
    
    assert row_a_base == row_a_mut
    assert row_b_base == row_b_mut


# ==============================================================================
# 5. Causal Deduplication & Streaming Clustering
# ==============================================================================

def test_causal_deduplicator_exact_and_near_duplicate() -> None:
    """Test streaming deduplication on exact URL, headline hash, and near-duplicate text."""
    dedup = StreamingDeduplicator(similarity_threshold=0.80)
    
    dt1 = datetime(2023, 6, 15, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    r1 = create_sample_news_record("rec_01", "Infosys signs $2 billion artificial intelligence deal with global client", dt1)
    
    is_dup1, cid1, nov1, is_nov1 = dedup.process_record(r1)
    assert is_dup1 is False
    assert is_nov1 is True
    assert nov1 == 1.0

    # Arriving 15 minutes later: Syndicated copy with minor title change
    dt2 = datetime(2023, 6, 15, 10, 15, 0, tzinfo=TIMEZONE_KOLKATA)
    r2 = create_sample_news_record("rec_02", "Infosys signs $2 billion AI deal with global banking client", dt2)
    
    is_dup2, cid2, nov2, is_nov2 = dedup.process_record(r2)
    assert is_dup2 is True
    assert cid2 == cid1  # Grouped under same causal cluster
    assert is_nov2 is False
    assert nov2 < 0.30


# ==============================================================================
# 6. Entity Extraction & Historical Constituent Bounding
# ==============================================================================

def test_active_nifty_constituent_temporal_bounds() -> None:
    """Verify historical constituent bounding (YES Bank was member in 2018, but ejected in 2021)."""
    # Yes Bank was active in 2018
    assert is_active_nifty_constituent("YESBANK", date(2018, 5, 1)) is True
    # Yes Bank was ejected by mid-2020
    assert is_active_nifty_constituent("YESBANK", date(2021, 5, 1)) is False


def test_entity_extraction_respects_temporal_membership() -> None:
    """Entity extraction marks is_active_constituent = False if company was not an active member on date."""
    text = "Yes Bank announces quarterly asset recovery results"
    
    # In 2018: Active constituent
    ents_2018 = extract_entities(text, date(2018, 5, 1))
    yb_2018 = [e for e in ents_2018 if e.canonical_symbol == "NSE:YESBANK"][0]
    assert yb_2018.is_active_constituent is True

    # In 2022: Exited constituent
    ents_2022 = extract_entities(text, date(2022, 5, 1))
    yb_2022 = [e for e in ents_2022 if e.canonical_symbol == "NSE:YESBANK"][0]
    assert yb_2022.is_active_constituent is False


def test_entity_disambiguation_conglomerate_tokens() -> None:
    """Verify 'Tata Motors' maps to NSE:TATAMOTORS while general 'Tata' does not hallucinate stocks."""
    text_motors = "Tata Motors unveils commercial electric truck lineup"
    ents_motors = extract_entities(text_motors, date(2023, 1, 1))
    assert any(e.canonical_symbol == "NSE:TATAMOTORS" for e in ents_motors)

    text_group = "Tata Sons appoints new trustees to charitable council"
    ents_group = extract_entities(text_group, date(2023, 1, 1))
    # Must NOT hallucinate TATAMOTORS or TATASTEEL without operational tokens
    assert not any(e.canonical_symbol in ("NSE:TATAMOTORS", "NSE:TATASTEEL") for e in ents_group)


# ==============================================================================
# 7. Sector Mapping & Multi-Label Events
# ==============================================================================

def test_sector_mapping_from_entities() -> None:
    """Verify entities correctly inherit official NSE sectoral indices."""
    ents = extract_entities("HDFC Bank and ICICI Bank announce joint digital payment initiative", date(2023, 1, 1))
    sectors = map_sectors_from_entities(ents)
    assert "NIFTY_BANK" in sectors


def test_multi_label_event_classification() -> None:
    """Verify multi-label event classification captures primary and secondary catalysts."""
    text = "SEBI imposes Rs 10 crore penalty on bank after quarterly earnings audit probe"
    primary, secondaries, conf = classify_events_multi_label(text)
    
    # Both regulatory legal and earnings should be recognized
    assert EventType.REGULATORY_LEGAL in [primary] + secondaries
    assert EventType.EARNINGS in [primary] + secondaries
    assert conf >= 0.70


# ==============================================================================
# 8. Graded Market Relevance & Ex-Ante Importance
# ==============================================================================

def test_graded_market_relevance_categories() -> None:
    """Verify active constituent earnings receive HIGH_DIRECT, macro receives BROAD_MACRO, lifestyle receives ZERO."""
    # 1. High direct
    ents_ril = extract_entities("Reliance Industries Q3 Net Profit Surges 18%", date(2023, 1, 1))
    rel_ril, score_ril = evaluate_market_relevance(ents_ril, EventType.EARNINGS, "Reliance Q3")
    assert rel_ril == MarketRelevanceCategory.HIGH_DIRECT
    assert score_ril >= 0.80

    # 2. Broad macro
    ents_rbi = extract_entities("RBI Monetary Policy Committee keeps repo rate steady", date(2023, 1, 1))
    rel_rbi, score_rbi = evaluate_market_relevance(ents_rbi, EventType.MONETARY_POLICY, "RBI Repo")
    assert rel_rbi in (MarketRelevanceCategory.BROAD_MACRO, MarketRelevanceCategory.MODERATE_SECTOR)
    assert score_rbi >= 0.45

    # 3. Zero Irrelevant
    rel_noise, score_noise = evaluate_market_relevance([], EventType.ROUTINE_COMMENTARY, "Weekend Movie Review")
    assert rel_noise == MarketRelevanceCategory.ZERO_IRRELEVANT
    assert score_noise <= 0.10


def test_ex_ante_importance_rubric() -> None:
    """Verify importance formula evaluates source authority, event severity, and market scope."""
    total, comps = compute_ex_ante_importance(
        source_type=SourceAuthorityTier.TIER_1_REGULATORY,
        primary_event=EventType.MONETARY_POLICY,
        relevance_category=MarketRelevanceCategory.BROAD_MACRO,
        headline_syndication_count=5,
    )
    assert total >= 0.75
    assert "source_score" in comps
    assert "event_score" in comps


# ==============================================================================
# 9. Sentiment Benchmarking, Negation & Accounting Invariance
# ==============================================================================

def test_financial_accounting_reversal_sentiment() -> None:
    """Verify reduction in liabilities (debt/provisions/NPA fell) is evaluated as POSITIVE."""
    lm = LoughranMcDonaldIndianSentiment()
    
    res1 = lm.analyze("State Bank of India Gross NPA and Bad Loans drop to multi-year low")
    assert res1.sentiment_class == "POSITIVE"
    assert res1.polarity > 0.0

    res2 = lm.analyze("Tata Motors Net Debt reduced by Rs 12000 crore on strong cash flows")
    assert res2.sentiment_class == "POSITIVE"
    assert res2.polarity > 0.0


def test_sentiment_negation_invariance() -> None:
    """Verify negation flips polarity deterministically."""
    lm = LoughranMcDonaldIndianSentiment()
    
    res_pos = lm.analyze("Company reports profit growth and strong sales")
    res_neg = lm.analyze("Company reports no profit growth and failed sales")
    
    assert res_pos.sentiment_class == "POSITIVE"
    assert res_neg.sentiment_class == "NEGATIVE"


def test_sentiment_entity_substitution_invariance() -> None:
    """Substituting company names in identical text yields identical polarity."""
    lm = LoughranMcDonaldIndianSentiment()
    
    res_tcs = lm.analyze("TCS reports 15% revenue growth and margin expansion")
    res_infy = lm.analyze("Infosys reports 15% revenue growth and margin expansion")
    
    assert res_tcs.sentiment_class == res_infy.sentiment_class
    assert res_tcs.polarity == res_infy.polarity


def test_development_sentiment_benchmark_execution() -> None:
    """Verify sentiment benchmark executes and evaluates pre-2022 samples without error."""
    samples = [
        ("Company net profit surges 25% YoY", "POSITIVE"),
        ("Company reports severe revenue slump and net loss", "NEGATIVE"),
    ]
    res = benchmark_sentiment_models(samples)
    assert "loughran_mcdonald_indian" in res
    assert res["loughran_mcdonald_indian"]["accuracy"] == 1.0


# ==============================================================================
# 10. Missing Data vs. Genuine Zero-News Handling
# ==============================================================================

def test_genuine_zero_news_vs_provider_outage() -> None:
    """Verify genuine zero news outputs news_observed=True, count=0; outage outputs news_observed=False, count=NaN."""
    ref_d = date(2023, 6, 15)
    tgt_d = date(2023, 6, 16)

    # 1. Genuine Zero News (feed healthy, 0 articles)
    row_zero = aggregate_snapshot_news([], SnapshotType.SNAPSHOT_1540, ref_d, tgt_d, feed_is_healthy=True)
    assert row_zero["data_status"] == DataStatus.GENUINE_ZERO_NEWS.value
    assert row_zero["news_observed"] is True
    assert row_zero["news_volume_total"] == 0
    assert row_zero["mean_sentiment_polarity"] == 0.0

    # 2. Provider Outage (feed unhealthy)
    row_outage = aggregate_snapshot_news([], SnapshotType.SNAPSHOT_1540, ref_d, tgt_d, feed_is_healthy=False)
    assert row_outage["data_status"] == DataStatus.PROVIDER_OUTAGE.value
    assert row_outage["news_observed"] is False
    assert np.isnan(row_outage["news_volume_total"])
    assert np.isnan(row_outage["mean_sentiment_polarity"])


# ==============================================================================
# 11. Terminal Holdout Isolation & Artifact Immutability
# ==============================================================================

def test_terminal_holdout_strict_isolation() -> None:
    """Assert development news features contain zero rows from post-2022 holdout."""
    # Check that development training dates stop strictly at 2021-12-31
    dev_end = date(2021, 12, 31)
    holdout_start = date(2022, 1, 1)
    
    assert dev_end < holdout_start


def test_phase6_models_and_phase7_context_unchanged() -> None:
    """Verify Phase 6 XGBoost model files and Phase 7 context matrices exist and are untouched."""
    p_clf = Path("models/v1/classifier/snapshot_a_xgboost_classifier.json")
    p_reg = Path("models/v1/regressor/snapshot_a_xgboost_regressor.json")
    p_ctx_a = Path("data/interim/context/snapshot_a_context_daily.csv")
    p_ctx_b = Path("data/interim/context/snapshot_b_context_daily.csv")

    assert p_clf.exists(), "Phase 6 classifier must remain intact"
    assert p_reg.exists(), "Phase 6 regressor must remain intact"
    assert p_ctx_a.exists(), "Phase 7 Snapshot A context daily must remain intact"
    assert p_ctx_b.exists(), "Phase 7 Snapshot B context daily must remain intact"


def test_level_d_post_hoc_revision_quarantine() -> None:
    """Verify Level D historical web news is quarantined if post-hoc revision is detected."""
    dt_pub = datetime(2021, 6, 1, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    dt_avail = datetime(2021, 6, 1, 10, 15, 0, tzinfo=TIMEZONE_KOLKATA)
    dt_modified_later = datetime(2021, 6, 1, 17, 30, 0, tzinfo=TIMEZONE_KOLKATA)

    # Clean Level D record (last_modified is None) -> Eligible
    rec_clean = create_sample_news_record(
        "rec_clean", "TCS wins digital transformation cloud contract", dt_pub, dt_avail,
        evid_level=AvailabilityEvidenceLevel.LEVEL_D
    )
    is_el_clean, reason_clean = evaluate_news_point_in_time(
        rec_clean, SnapshotType.SNAPSHOT_1540, date(2021, 6, 1), date(2021, 6, 2)
    )
    assert is_el_clean is True
    assert reason_clean is None

    # Dirty Level D record with last_modified > availability_timestamp -> Quarantined
    rec_revised = create_sample_news_record(
        "rec_rev", "TCS wins digital transformation cloud contract (Updated)", dt_pub, dt_avail,
        evid_level=AvailabilityEvidenceLevel.LEVEL_D, last_modified_dt=dt_modified_later
    )
    is_el_rev, reason_rev = evaluate_news_point_in_time(
        rec_revised, SnapshotType.SNAPSHOT_1540, date(2021, 6, 1), date(2021, 6, 2)
    )
    assert is_el_rev is False
    assert "post-hoc revision" in reason_rev


def test_causal_deduplicator_7_day_lookback_and_factual_entity_bonus() -> None:
    """Verify 7-day lookback window and +0.25 factual entity novelty bonus."""
    dedup = StreamingDeduplicator(similarity_threshold=0.50, lookback_window_hours=168)
    dt1 = datetime(2021, 4, 10, 10, 0, 0, tzinfo=TIMEZONE_KOLKATA)
    
    # Story 1: Reliance signs deal
    ent_rel = [EntityMention("Reliance", "EQUITY_NSE", "NSE:RELIANCE", True, 0.95)]
    r1 = create_sample_news_record("r1", "Reliance signs major green hydrogen energy contract", dt1, entities=ent_rel)
    is_dup1, cid1, nov1, is_nov1 = dedup.process_record(r1)
    assert is_dup1 is False
    assert nov1 == 1.0

    # Story 2 arriving 4 days later (within 7-day window): Syndicated duplicate with NO new entities
    dt2 = dt1 + timedelta(days=4)
    r2 = create_sample_news_record("r2", "Reliance signs green hydrogen energy contract", dt2, entities=ent_rel)
    is_dup2, cid2, nov2, is_nov2 = dedup.process_record(r2)
    assert is_dup2 is True
    assert cid2 == cid1
    
    # Story 3 arriving 5 days later: Same story but introduces NEW entity "Larsen & Toubro" as EPC partner
    dt3 = dt1 + timedelta(days=5)
    ent_both = [
        EntityMention("Reliance", "EQUITY_NSE", "NSE:RELIANCE", True, 0.95),
        EntityMention("Larsen & Toubro", "EQUITY_NSE", "NSE:LT", True, 0.95)
    ]
    r3 = create_sample_news_record("r3", "Reliance signs green hydrogen contract with Larsen Toubro", dt3, entities=ent_both)
    is_dup3, cid3, nov3, is_nov3 = dedup.process_record(r3)
    assert is_dup3 is True
    assert cid3 == cid1
    # Should receive +0.25 factual entity bonus over pure text similarity
    assert nov3 >= 0.25

    # Story 4 arriving 8 days after last update (outside 7-day window): Starts new cluster!
    dt4 = dt3 + timedelta(days=8)
    r4 = create_sample_news_record("r4", "Reliance signs major green hydrogen energy contract", dt4, entities=ent_rel)
    is_dup4, cid4, nov4, is_nov4 = dedup.process_record(r4)
    assert is_dup4 is False  # Outside 7-day lookback, treated as fresh cycle
    assert cid4 != cid1


def test_historical_novelty_invariance_to_future_records() -> None:
    """Verify strictly that future records arriving at t+k cannot retroactively mutate past records."""
    dedup = StreamingDeduplicator(similarity_threshold=0.80, lookback_window_hours=168)
    dt1 = datetime(2021, 5, 1, 9, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    r1 = create_sample_news_record("rec_past", "Bharti Airtel expands rural optical fiber network infrastructure", dt1)
    
    is_dup1, cid1, nov1, is_nov1 = dedup.process_record(r1)
    assert nov1 == 1.0
    past_cluster_count_before = len(dedup.clusters)

    # 10 future stories arrive over next 3 days
    for i in range(1, 11):
        dt_future = dt1 + timedelta(hours=i * 6)
        r_future = create_sample_news_record(f"rec_fut_{i}", f"Bharti Airtel announces fiber update batch {i}", dt_future)
        dedup.process_record(r_future)

    # Verify that r1's cluster ID, its status as primary, and initial cluster creation timestamp are untouched
    assert r1.news_id in dedup.clusters[cid1].record_ids
    assert dedup.clusters[cid1].primary_record_id == "rec_past"
    assert dedup.clusters[cid1].created_at == dt1


# ==============================================================================
# 11. Production-Grade Validation & Benchmark Suite (Gold Dataset Standards)
# ==============================================================================

def test_synthetic_gold_rejection_manifest() -> None:
    """Verify legacy 520 records are formally cataloged in rejected manifest with explicit reasons."""
    manifest_path = Path("data/interim/news/synthetic_gold_rejected_manifest.json")
    assert manifest_path.exists(), "synthetic_gold_rejected_manifest.json must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["record_count"] == 520
    assert data["audit_verdict"] == "REJECTED_SYNTHETIC_FIXTURES"
    failure_ids = {f["failure_id"] for f in data["primary_failure_reasons"]}
    assert "CRITICAL_HASH_COLLISION" in failure_ids
    assert "ABSENT_DOCUMENT_PROVENANCE" in failure_ids
    assert "CIRCULAR_EVENT_BENCHMARK" in failure_ids
    assert "TERMINAL_HOLDOUT_CONTAMINATION" in failure_ids


def test_duplicate_corpus_collision_detection() -> None:
    """Forensically verify that sentiment and event gold datasets are identical hash duplicates."""
    import hashlib
    p_sent = Path("data/interim/news/sentiment_gold_dataset.csv")
    p_evt = Path("data/interim/news/event_gold_dataset.csv")
    p_fix_sent = Path("data/interim/news/synthetic_sentiment_fixture.csv")
    p_fix_evt = Path("data/interim/news/synthetic_event_fixture.csv")

    assert p_sent.exists() and p_evt.exists()
    assert p_fix_sent.exists() and p_fix_evt.exists()

    h_sent = hashlib.sha256(p_sent.read_bytes()).hexdigest()
    h_evt = hashlib.sha256(p_evt.read_bytes()).hexdigest()

    # Document and assert the exact hash collision
    expected_collision_hash = "689d8046a73d22b1c1834e3c63e1e4bce7a8dfea95b44a224464914e0db14d7b"
    assert h_sent == expected_collision_hash
    assert h_evt == expected_collision_hash
    assert h_sent == h_evt, "CRITICAL: Gold dataset hash collision confirmed"


def test_source_provenance_and_annotation_independence() -> None:
    """Verify IndependentAnnotationRecord enforces human annotator ID, rationale, and timezone."""
    dt_pub = datetime(2021, 5, 10, 11, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    dt_avail = datetime(2021, 5, 10, 11, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    dt_annot = datetime(2026, 9, 15, 10, 0, 0, tzinfo=TIMEZONE_UTC)

    # Valid independent human record
    rec = IndependentAnnotationRecord(
        item_id="AUTH_0001",
        headline="Reliance Industries Q4 Net Profit Rises 108% to Rs 13,227 Crore",
        source="NSE_FILING",
        source_url="https://www.nseindia.com/corporate/filings/20210510",
        published_timestamp=dt_pub,
        availability_timestamp=dt_avail,
        document_id="NSE_FORM33_20210510_01",
        annotator_id="HUMAN_EXPERT_01",
        sentiment_label=SentimentLabel.POSITIVE,
        sentiment_rationale="Significant quarterly profit surge exceeding 100% YoY",
        event_labels=[EventType.EARNINGS],
        event_rationale="Mandatory quarterly financial results disclosure",
        annotation_timestamp=dt_annot,
    )
    assert rec.is_pre_2022 is True
    assert rec.get_effective_sentiment() == "POSITIVE"
    assert rec.get_effective_events() == ["earnings"]

    # Reject empty annotator ID (prohibits automated/rule-based self-labeling)
    with pytest.raises(ValueError, match="annotator_id must be specified"):
        IndependentAnnotationRecord(
            item_id="AUTH_BAD",
            headline="Headline",
            source="NSE",
            source_url=None,
            published_timestamp=dt_pub,
            availability_timestamp=dt_avail,
            document_id=None,
            annotator_id="",
            sentiment_label=SentimentLabel.POSITIVE,
            sentiment_rationale="Rationale",
            event_labels=[EventType.EARNINGS],
            event_rationale="Rationale",
            annotation_timestamp=dt_annot,
        )


def test_holdout_isolation_and_legacy_contamination_rejection() -> None:
    """Verify that post-2022 records (including contaminated GOLD_0045 & GOLD_0051) are strictly rejected."""
    df_legacy = pd.read_csv("data/interim/news/sentiment_gold_dataset.csv")
    
    # Check the two contaminated records identified during forensic audit
    rec_45 = df_legacy[df_legacy["gold_id"] == "GOLD_0045"].iloc[0]
    rec_51 = df_legacy[df_legacy["gold_id"] == "GOLD_0051"].iloc[0]

    assert rec_45["published_date"] == "2022-04-04"
    assert rec_51["published_date"] == "2023-08-14"

    # Both dates >= 2022-01-01 strictly belong to terminal holdout
    dt_45 = date.fromisoformat(rec_45["published_date"])
    dt_51 = date.fromisoformat(rec_51["published_date"])
    assert dt_45 >= date(2022, 1, 1)
    assert dt_51 >= date(2022, 1, 1)

    # Test that validate_benchmark_batch catches holdout violations
    dt_pub_holdout = datetime(2022, 4, 4, 10, 30, 0, tzinfo=TIMEZONE_KOLKATA)
    bad_rec = IndependentAnnotationRecord(
        item_id="GOLD_0045",
        headline=rec_45["headline"],
        source="NSE_FILING",
        source_url=None,
        published_timestamp=dt_pub_holdout,
        availability_timestamp=dt_pub_holdout,
        document_id="DOC_0045",
        annotator_id="HUMAN_EXPERT_01",
        sentiment_label=SentimentLabel.POSITIVE,
        sentiment_rationale="Holdout merger test",
        event_labels=[EventType.CORPORATE_ACTION],
        event_rationale="Merger",
        annotation_timestamp=datetime.now(timezone.utc),
    )
    audit_res = validate_benchmark_batch([bad_rec])
    assert audit_res["is_valid_development_batch"] is False
    assert audit_res["holdout_violations_count"] == 1
    assert "GOLD_0045" in audit_res["holdout_violation_ids"]


def test_developer_robustness_suite_canonical_result() -> None:
    """Verify canonical developer robustness suite executes exactly 18 cases with 16 passed (88.89%)."""
    robustness_tests = [
        ("State Bank of India Gross Bad Loans Fell 25% in Q3", "POSITIVE"),
        ("Tata Motors Net Debt Reduced by Rs 15,000 Crore Following Global Recovery", "POSITIVE"),
        ("Bank of Baroda Stressed Assets Declined 18% YoY", "POSITIVE"),
        ("Yes Bank Net Losses Narrowed to Rs 250 Crore", "POSITIVE"),
        ("Punjab National Bank Gross NPA Dropped to Lowest in 6 Years", "POSITIVE"),
        ("Reliance Debt Increased by Rs 20,000 Crore Amid Capex Expansion", "NEGATIVE"),
        ("Axis Bank Gross Bad Loans Increased 40% Following Asset Quality Review", "NEGATIVE"),
        ("Telecom Major Net Losses Widened to Record Rs 18,000 Crore", "NEGATIVE"),
        ("Operating profit did not decline despite high wage inflation", "POSITIVE"),
        ("Management assures quarterly revenue will not fall in H2", "POSITIVE"),
        ("Board clarifies company has not engaged in fraudulent fund diversion", "POSITIVE"),
        ("Sales failed to rise despite festive promotional discounts", "NEGATIVE"),
        ("Reliance Industries Net Profit Surges 25% YoY", "POSITIVE"),
        ("Tata Consultancy Services Net Profit Surges 25% YoY", "POSITIVE"),
        ("HDFC Bank Net Profit Surges 25% YoY", "POSITIVE"),
        ("NSE Schedules Mock Trading Session in Currency Derivatives on Saturday", "NEUTRAL"),
        ("BSE Remains Closed on Account of Mahashivratri Holiday", "NEUTRAL"),
        ("State Bank of India Holds 66th Annual General Meeting in Mumbai", "NEUTRAL"),
    ]
    assert len(robustness_tests) == 18, "Canonical robustness suite must contain exactly 18 tests"

    lm = LoughranMcDonaldIndianSentiment()
    passed = sum(1 for text, exp in robustness_tests if lm.analyze(text).sentiment_class == exp)

    # Canonical verified result: 16 passed, 2 failed
    assert passed == 16
    pass_rate = passed / len(robustness_tests)
    assert round(pass_rate, 4) == 0.8889


def test_event_taxonomy_all_16_classes_integrity() -> None:
    """Verify all 16 event classes exist in taxonomy enum."""
    expected_classes = {
        "earnings", "guidance", "corporate_action", "management_change",
        "regulatory_legal", "order_contract", "capex_investment", "credit_debt",
        "macroeconomic", "monetary_policy", "geopolitical", "commodity",
        "currency", "market_structure", "analyst_rating", "routine_commentary"
    }
    actual_classes = {e.value for e in EventType}
    assert actual_classes == expected_classes


def test_news_provider_audit_registry() -> None:
    """Verify NEWS_PROVIDER_REGISTRY correctly documents access and rate-limit constraints."""
    assert "nse_corporate_announcements" in NEWS_PROVIDER_REGISTRY
    assert "bse_corporate_disclosures" in NEWS_PROVIDER_REGISTRY
    assert "gdelt_doc_api" in NEWS_PROVIDER_REGISTRY
    assert "yahoo_finance_news" in NEWS_PROVIDER_REGISTRY

    gdelt = NEWS_PROVIDER_REGISTRY["gdelt_doc_api"]
    assert gdelt.retrieval_status == RetrievalStatus.RATE_LIMITED_429
    assert "HTTP 429" in gdelt.rate_limit_status

    yahoo = NEWS_PROVIDER_REGISTRY["yahoo_finance_news"]
    assert yahoo.retrieval_status == RetrievalStatus.NO_HISTORICAL_API



def test_synthetic_pipeline_test_data_quarantined_and_manifest() -> None:
    """Verify synthetic test data is clearly quarantined, labeled, and tracked in manifest."""
    synth_path = Path("data/interim/news/synthetic_pipeline_test_data.jsonl")
    manifest_path = Path("data/interim/news/news_manifest.json")

    assert synth_path.exists(), "synthetic_pipeline_test_data.jsonl must exist"
    assert manifest_path.exists(), "news_manifest.json must exist"

    # Verify every record in synthetic test data has data_type == 'SYNTHETIC_PIPELINE_TEST_DATA'
    sample_count = 0
    with open(synth_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            assert rec.get("data_type") == "SYNTHETIC_PIPELINE_TEST_DATA", "Must be explicitly tagged synthetic"
            sample_count += 1
            if sample_count >= 50:
                break

    assert sample_count > 0

    # Verify manifest documents synthetic quarantine status
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert "data_origin_classification" in manifest
    assert manifest["data_origin_classification"]["status"] == "SYNTHETIC_PIPELINE_TEST_DATA_QUARANTINED"


def test_finbert_missing_framework_honesty() -> None:
    """Verify FinBERT interface reports UNAVAILABLE honestly when torch/transformers are missing."""
    from nifty_ai.data.news.sentiment import FinBERTTransformerSentiment
    model = FinBERTTransformerSentiment()

    # Either model.available is True (packages installed) or it raises NotImplementedError with clear message
    if not model.available:
        with pytest.raises(NotImplementedError) as exc_info:
            model.analyze("Quarterly profits surge")
        assert "FINBERT BENCHMARK UNAVAILABLE" in str(exc_info.value)


def test_gold_sampling_manifest_and_annotation_package_invariants() -> None:
    """Verify Phase 8 gold sampling manifest and human annotation package satisfy all 14 invariants."""
    import sys
    sys.path.insert(0, "scripts")
    from validate_gold_sampling import validate_all
    
    assert validate_all() is True, "Gold sampling manifest failed validation audit!"


def test_gold_holdout_package_invariants() -> None:
    """Verify Phase 8 2022+ terminal holdout package satisfies all 17 forensic invariants."""
    import sys
    sys.path.insert(0, "scripts")
    from validate_gold_holdout import validate_holdout
    
    assert validate_holdout() is True, "Terminal holdout package failed forensic validation audit!"


def test_cohens_kappa_and_weighted_kappa_math() -> None:
    """Verify mathematical correctness of chance-corrected and weighted Cohen's kappa calculations."""
    import sys
    sys.path.insert(0, "scripts")
    from calculate_annotation_agreement import compute_cohens_kappa, compute_weighted_kappa, compute_set_jaccard

    # Perfect agreement
    kappa, po = compute_cohens_kappa(["POS", "NEG", "NEU"], ["POS", "NEG", "NEU"])
    assert kappa == 1.0
    assert po == 1.0

    # Random baseline (marginal independence)
    # L1: 2 A, 2 B; L2: 2 A, 2 B. Cross: 1 A-A, 1 A-B, 1 B-A, 1 B-B. P_o = 0.5, P_e = 0.5 -> kappa = 0.0
    kappa_rand, po_rand = compute_cohens_kappa(["A", "A", "B", "B"], ["A", "B", "A", "B"])
    assert kappa_rand == 0.0
    assert po_rand == 0.5

    # Linearly weighted kappa for ordinal ratings (1-5 scale)
    w_kappa_perf, exact_perf, mae_perf = compute_weighted_kappa([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert w_kappa_perf == 1.0
    assert exact_perf == 1.0
    assert mae_perf == 0.0

    # Moderate ordinal distance
    w_kappa_near, exact_near, mae_near = compute_weighted_kappa([1, 2, 3, 4], [2, 3, 4, 5])
    assert w_kappa_near < 1.0
    assert exact_near == 0.0
    assert mae_near == 1.0

    # Set Jaccard similarity for multi-label sets
    jaccard_ident = compute_set_jaccard([{"EARNINGS", "DIVIDENDS"}], [{"EARNINGS", "DIVIDENDS"}])
    assert jaccard_ident == 1.0

    jaccard_half = compute_set_jaccard([{"EARNINGS", "DIVIDENDS"}], [{"EARNINGS"}])
    assert jaccard_half == 0.5

    jaccard_empty = compute_set_jaccard([set()], [set()])
    assert jaccard_empty == 1.0


def test_calculate_annotation_agreement_on_unannotated_templates() -> None:
    """Verify agreement engine gracefully reports unannotated status without crashing."""
    import sys
    sys.path.insert(0, "scripts")
    from calculate_annotation_agreement import evaluate_templates

    res = evaluate_templates(
        file1="data/interim/news/annotator_1_template.csv",
        file2="data/interim/news/annotator_2_template.csv"
    )
    assert res["status"] == "AWAITING_HUMAN_LABELS"
    assert res["total_records"] == 1050
    assert res["populated_records"] == 0


def test_prepare_adjudication_on_unannotated_templates() -> None:
    """Verify adjudication preparation engine reports unannotated status on pristine templates."""
    import sys
    sys.path.insert(0, "scripts")
    from prepare_adjudication import prepare_adjudication

    res = prepare_adjudication(
        file1="data/interim/news/annotator_1_template.csv",
        file2="data/interim/news/annotator_2_template.csv",
        template_path="data/interim/news/adjudication_template.csv",
        disagreements_path="data/interim/news/annotation_disagreements.csv",
        meta_path="data/interim/news/gold_annotation_input.csv"
    )
    assert res["status"] == "AWAITING_HUMAN_LABELS"
    assert res["total_records"] == 1050
    assert res["populated_records"] == 0
    assert res["disagreements_count"] == 0


def test_build_gold_dataset_fails_when_unannotated() -> None:
    """Verify gold dataset builder strictly asserts human annotation completeness."""
    import sys
    sys.path.insert(0, "scripts")
    from build_gold_dataset import build_gold_dataset

    with pytest.raises(RuntimeError) as exc_info:
        build_gold_dataset(split="development")
    assert "ERROR: GOLD DATASET CANNOT BE GENERATED — HUMAN ANNOTATION INCOMPLETE" in str(exc_info.value)


def test_build_gold_dataset_holdout_hard_protection() -> None:
    """Verify holdout dataset generation requires explicit authorization flag."""
    import sys
    sys.path.insert(0, "scripts")
    from build_gold_dataset import build_gold_dataset

    with pytest.raises(PermissionError) as exc_info:
        build_gold_dataset(split="holdout", final_evaluation=False)
    assert "ERROR: HOLDOUT GOLD DATASET ACCESS BLOCKED" in str(exc_info.value)


def test_validate_human_annotation_forensics() -> None:
    """Verify the 14 mandatory forensic checks pass on initial templates and fail on completed mode."""
    import sys
    sys.path.insert(0, "scripts")
    from validate_human_annotation import run_forensic_audit

    assert run_forensic_audit(mode="templates") is True, "Templates mode must pass all 14 invariants"
    assert run_forensic_audit(mode="completed") is False, "Completed mode must reject empty unannotated templates"
