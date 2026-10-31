"""Deterministic Point-in-Time News NLP Feature Generation Engine.

Phase 9 Step 3:
- Ingests authentic historical news inventory (2008–2021, 62,329 records) and
  authentic terminal Step 2E holdout (2022–2026, 41,371 records) = 103,700 records.
- Verifies input SHA-256 hashes against locked provenance standards.
- Enforces strict point-in-time ordering and causal streaming novelty (168-hour lookback).
- Computes deterministic sentiment via LoughranMcDonaldIndianSentiment.
- Classifies multi-label events using the canonical 18-category Phase 8 taxonomy.
- Evaluates ex-ante importance and market relevance without peeking at future prices.
- Maps records strictly into:
    Snapshot A(T): (T-1 15:30:00 IST, T 15:30:00 IST]
    Snapshot B(T): (T 15:30:00 IST, T+1 08:50:00 IST]
- Enforces dynamic Point-in-Time NIFTY 50 constituent membership filtering:
  non-member companies never contribute to NIFTY daily features.
- Constructs daily feature sets for Snapshot A, Snapshot B, and Diagnostic Delta
  across all 4,653 trading sessions from 2007-09-17 through 2026-09-03.
- Guarantees zero NaN / zero infinite values across all required features.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

from nifty_ai.data.news.constituents import (
    CANONICAL_CONSTITUENTS,
    is_active_nifty_constituent,
)
from nifty_ai.data.news.deduplication import StreamingDeduplicator
from nifty_ai.data.news.nlp_engine import (
    compute_ex_ante_importance,
    evaluate_market_relevance,
    extract_entities,
    map_sectors_from_entities,
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
    DataStatus,
    EventType,
    MarketRelevanceCategory,
    SourceAuthorityTier,
)
from nifty_ai.data.news.sentiment import LoughranMcDonaldIndianSentiment
from nifty_ai.data.schema import DataFrequency, ProvenanceMetadata, ProviderTier
from nifty_ai.data.snapshots import SnapshotType

logger = logging.getLogger(__name__)

TIMEZONE_KOLKATA = ZoneInfo("Asia/Kolkata")
TIMEZONE_UTC = ZoneInfo("UTC")

EXPECTED_HISTORICAL_SHA = "6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3"
EXPECTED_HISTORICAL_COUNT = 62329

EXPECTED_TERMINAL_SHA = "5d5daf5ed7c844e86d45dc6a893f03b1d4f523183e29200d94b592329136f6fd"
EXPECTED_TERMINAL_COUNT = 41371

EXPECTED_GOLD_SHA = "0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199"


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def resolve_canonical_company_symbol(record_dict: Dict[str, Any]) -> str:
    """Extract canonical NIFTY equity symbol from raw record."""
    ents = record_dict.get("company_or_entities", [])
    sym = ents[0] if ents else record_dict.get("historical_symbol_variant", "")
    sym = str(sym).upper().strip()
    if sym == "TATAMTRDVR":
        return "TATAMOTORS"
    return sym


def compute_information_decay(
    item_availability: datetime,
    cutoff_dt: datetime,
    half_life_hours: float = 24.0,
) -> float:
    """Compute exponential decay weight based on information age at cutoff."""
    age_hours = max(0.0, (cutoff_dt - item_availability).total_seconds() / 3600.0)
    return round(float(2.0 ** (-age_hours / half_life_hours)), 4)


def aggregate_daily_snapshot_features(
    records: List[Dict[str, Any]],
    snapshot_type: SnapshotType,
    reference_date: date,
    target_date: date,
    feed_is_healthy: bool = True,
) -> Dict[str, Any]:
    """Aggregate qualifying point-in-time news records into daily snapshot features.
    
    Guarantees:
    - Exactly 0 NaNs and 0 infinite values.
    - Zero-news days cleanly default to 0 count / 0.0 values with GENUINE_ZERO_NEWS status.
    - Full coverage of volume, sentiment, importance, canonical events, novelty, and concentration.
    """
    cutoff_time = time(15, 30, 0) if snapshot_type == SnapshotType.SNAPSHOT_1540 else time(8, 50, 0)
    cutoff_day = reference_date if snapshot_type == SnapshotType.SNAPSHOT_1540 else target_date
    cutoff_dt = datetime.combine(cutoff_day, cutoff_time, tzinfo=TIMEZONE_KOLKATA)

    row: Dict[str, Any] = {
        "trading_date": reference_date.isoformat(),
        "target_date": target_date.isoformat(),
        "snapshot_type": snapshot_type.value,
        "cutoff_timestamp": cutoff_dt.isoformat(),
    }

    # Canonical event category column mapping
    event_count_keys = [f"event_{cat.lower()}_count" for cat in CANONICAL_PHASE8_EVENT_CATEGORIES]

    # Handle Genuine Zero News or Unhealthy Feed
    if not records or not feed_is_healthy:
        row["data_status"] = DataStatus.HEALTHY_OBSERVED.value if (feed_is_healthy and records) else DataStatus.GENUINE_ZERO_NEWS.value
        row["news_observed"] = False
        row["has_news_flag"] = 0

        # Volume / count
        row["news_count"] = 0
        row["news_volume_total"] = 0
        row["high_relevance_count"] = 0
        row["high_importance_count"] = 0
        row["news_volume_high_importance"] = 0
        row["unique_company_count"] = 0
        row["num_distinct_companies"] = 0
        row["unique_event_type_count"] = 0
        row["num_distinct_event_types"] = 0

        # Sentiment
        row["mean_sentiment"] = 0.0
        row["mean_sentiment_polarity"] = 0.0
        row["weighted_sentiment"] = 0.0
        row["importance_weighted_sentiment"] = 0.0
        row["novelty_weighted_sentiment"] = 0.0
        row["sentiment_dispersion"] = 0.0
        row["positive_count"] = 0
        row["negative_count"] = 0
        row["neutral_count"] = 0
        row["positive_ratio"] = 0.0
        row["negative_ratio"] = 0.0
        row["sentiment_balance"] = 0.0

        # Importance
        row["mean_importance"] = 0.0
        row["max_importance"] = 0.0
        row["max_importance_score"] = 0.0
        row["weighted_importance"] = 0.0
        row["high_importance_ratio"] = 0.0

        # Canonical events
        for k in event_count_keys:
            row[k] = 0
        row["earnings_event_count"] = 0
        row["macro_event_count"] = 0
        row["monetary_event_count"] = 0

        # Novelty
        row["mean_novelty"] = 0.0
        row["weighted_novelty"] = 0.0
        row["novel_news_count"] = 0

        # Concentration
        row["top_company_share"] = 0.0
        row["top_event_share"] = 0.0
        row["company_entropy"] = 0.0
        row["event_entropy"] = 0.0

        # Company-level aggregates
        row["company_news_count_mean"] = 0.0
        row["company_weighted_sentiment_mean"] = 0.0
        row["company_weighted_importance_mean"] = 0.0
        row["company_novelty_mean"] = 0.0

        return row

    # Normal Aggregation across eligible records
    n_records = len(records)
    row["data_status"] = DataStatus.HEALTHY_OBSERVED.value
    row["news_observed"] = True
    row["has_news_flag"] = 1

    # 1. Volume / count features
    row["news_count"] = n_records
    row["news_volume_total"] = n_records

    companies = [r["company_symbol"] for r in records]
    unique_comps = sorted(set(companies))
    row["unique_company_count"] = len(unique_comps)
    row["num_distinct_companies"] = len(unique_comps)

    events = [r["primary_event"] for r in records]
    unique_evts = sorted(set(events))
    row["unique_event_type_count"] = len(unique_evts)
    row["num_distinct_event_types"] = len(unique_evts)

    high_rel_count = sum(
        1 for r in records
        if r.get("market_relevance_category") in (MarketRelevanceCategory.HIGH_DIRECT, "HIGH_DIRECT", "high_direct")
        or r.get("market_relevance_score", 0.0) >= 0.80
    )
    high_imp_count = sum(1 for r in records if r["importance_score"] >= 0.70)
    row["high_relevance_count"] = high_rel_count
    row["high_importance_count"] = high_imp_count
    row["news_volume_high_importance"] = high_imp_count
    row["high_importance_ratio"] = round(high_imp_count / n_records, 4)

    # 2. Sentiment features
    polarities = [r["sentiment_polarity"] for r in records]
    pos_count = sum(1 for p in polarities if p > 0.05)
    neg_count = sum(1 for p in polarities if p < -0.05)
    neu_count = sum(1 for p in polarities if -0.05 <= p <= 0.05)

    row["mean_sentiment"] = round(float(np.mean(polarities)), 4)
    row["mean_sentiment_polarity"] = row["mean_sentiment"]
    row["sentiment_dispersion"] = round(float(np.std(polarities)), 4)
    row["positive_count"] = pos_count
    row["negative_count"] = neg_count
    row["neutral_count"] = neu_count
    row["positive_ratio"] = round(pos_count / n_records, 4)
    row["negative_ratio"] = round(neg_count / n_records, 4)
    row["sentiment_balance"] = round((pos_count - neg_count) / (pos_count + neg_count + 1.0), 4)

    # 3. Importance features
    importances = [r["importance_score"] for r in records]
    row["mean_importance"] = round(float(np.mean(importances)), 4)
    row["max_importance"] = round(float(np.max(importances)), 4)
    row["max_importance_score"] = row["max_importance"]

    # 4. Time decay and weights
    decays = [compute_information_decay(r["availability_timestamp"], cutoff_dt) for r in records]
    imp_weights = [max(0.01, imp * d) for imp, d in zip(importances, decays)]
    nov_weights = [max(0.01, imp * r["novelty_score"] * d) for imp, r, d in zip(importances, records, decays)]

    sum_imp_w = sum(imp_weights)
    weighted_sent = sum(p * w for p, w in zip(polarities, imp_weights)) / sum_imp_w if sum_imp_w > 0 else 0.0
    row["weighted_sentiment"] = round(float(weighted_sent), 4)
    row["importance_weighted_sentiment"] = row["weighted_sentiment"]

    sum_nov_w = sum(nov_weights)
    nov_weighted_sent = sum(p * w for p, w in zip(polarities, nov_weights)) / sum_nov_w if sum_nov_w > 0 else 0.0
    row["novelty_weighted_sentiment"] = round(float(nov_weighted_sent), 4)

    sum_decays = sum(decays)
    weighted_imp = sum(imp * d for imp, d in zip(importances, decays)) / sum_decays if sum_decays > 0 else 0.0
    row["weighted_importance"] = round(float(weighted_imp), 4)

    # 5. Canonical Event features
    evt_counter = Counter(events)
    for cat in CANONICAL_PHASE8_EVENT_CATEGORIES:
        k = f"event_{cat.lower()}_count"
        row[k] = evt_counter.get(cat, 0)

    # Legacy event counts
    _earnings_set = {"EARNINGS_RESULTS", "EARNINGS", EventType.EARNINGS.value if hasattr(EventType, "EARNINGS") else "earnings"}
    _macro_set = {"MACROECONOMIC", EventType.MACROECONOMIC.value if hasattr(EventType, "MACROECONOMIC") else "macroeconomic"}
    _monetary_set = {"MONETARY_POLICY", EventType.MONETARY_POLICY.value if hasattr(EventType, "MONETARY_POLICY") else "monetary_policy"}

    row["earnings_event_count"] = sum(
        1 for r in records
        if r["primary_event"] in _earnings_set or any(e in _earnings_set for e in r.get("secondary_events", []))
    )
    row["macro_event_count"] = sum(
        1 for r in records
        if r["primary_event"] in _macro_set or any(e in _macro_set for e in r.get("secondary_events", []))
    )
    row["monetary_event_count"] = sum(
        1 for r in records
        if r["primary_event"] in _monetary_set or any(e in _monetary_set for e in r.get("secondary_events", []))
    )

    # 6. Novelty features
    novelties = [r["novelty_score"] for r in records]
    row["mean_novelty"] = round(float(np.mean(novelties)), 4)
    weighted_nov = sum(nov * w for nov, w in zip(novelties, imp_weights)) / sum_imp_w if sum_imp_w > 0 else 0.0
    row["weighted_novelty"] = round(float(weighted_nov), 4)
    row["novel_news_count"] = sum(1 for r in records if r.get("is_novel", False) or r["novelty_score"] >= 0.80)

    # 7. Concentration & Entropy features
    comp_counter = Counter(companies)
    max_comp_cnt = max(comp_counter.values())
    row["top_company_share"] = round(float(max_comp_cnt / n_records), 4)

    max_evt_cnt = max(evt_counter.values())
    row["top_event_share"] = round(float(max_evt_cnt / n_records), 4)

    # Company normalized entropy
    if len(comp_counter) > 1:
        p_c = np.array(list(comp_counter.values()), dtype=float) / n_records
        h_c = -np.sum(p_c * np.log(p_c + 1e-12)) / np.log(len(comp_counter))
        row["company_entropy"] = round(float(h_c), 4)
    else:
        row["company_entropy"] = 0.0

    # Event normalized entropy
    if len(evt_counter) > 1:
        p_e = np.array(list(evt_counter.values()), dtype=float) / n_records
        h_e = -np.sum(p_e * np.log(p_e + 1e-12)) / np.log(len(evt_counter))
        row["event_entropy"] = round(float(h_e), 4)
    else:
        row["event_entropy"] = 0.0

    # 8. Company-level aggregations to NIFTY level
    row["company_news_count_mean"] = round(float(n_records / len(comp_counter)), 4)

    comp_to_records: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        comp_to_records[r["company_symbol"]].append(r)

    comp_sents = []
    comp_imps = []
    comp_novs = []
    for c_sym, c_recs in comp_to_records.items():
        c_pols = [r["sentiment_polarity"] for r in c_recs]
        c_imps = [r["importance_score"] for r in c_recs]
        c_novs = [r["novelty_score"] for r in c_recs]
        c_decays = [compute_information_decay(r["availability_timestamp"], cutoff_dt) for r in c_recs]
        c_weights = [max(0.01, imp * d) for imp, d in zip(c_imps, c_decays)]
        c_tot_w = sum(c_weights)

        c_w_sent = sum(p * w for p, w in zip(c_pols, c_weights)) / c_tot_w if c_tot_w > 0 else 0.0
        c_w_imp = sum(imp * d for imp, d in zip(c_imps, c_decays)) / sum(c_decays) if sum(c_decays) > 0 else 0.0
        comp_sents.append(c_w_sent)
        comp_imps.append(c_w_imp)
        comp_novs.append(float(np.mean(c_novs)))

    row["company_weighted_sentiment_mean"] = round(float(np.mean(comp_sents)), 4)
    row["company_weighted_importance_mean"] = round(float(np.mean(comp_imps)), 4)
    row["company_novelty_mean"] = round(float(np.mean(comp_novs)), 4)

    return row


def build_snapshot_delta_features(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
) -> pd.DataFrame:
    """Build diagnostic Snapshot Delta (B - A) features.
    
    Diagnostic only. Strictly isolated from primary Model 2 input feature vectors.
    """
    assert len(df_a) == len(df_b), "Snapshot A and B row count mismatch!"

    rows_delta = []
    for idx in range(len(df_a)):
        row_a = df_a.iloc[idx]
        row_b = df_b.iloc[idx]

        assert row_a["trading_date"] == row_b["trading_date"], "Date alignment error in delta calculation!"
        assert row_a["target_date"] == row_b["target_date"], "Target date alignment error in delta calculation!"

        t_date = row_a["trading_date"]
        tgt_date = row_a["target_date"]

        cnt_a = int(row_a["news_count"])
        cnt_b = int(row_b["news_count"])
        delta_cnt = cnt_b - cnt_a

        sent_a = float(row_a["weighted_sentiment"])
        sent_b = float(row_b["weighted_sentiment"])
        delta_sent = round(sent_b - sent_a, 4)

        mean_sent_a = float(row_a["mean_sentiment"])
        mean_sent_b = float(row_b["mean_sentiment"])
        delta_mean_sent = round(mean_sent_b - mean_sent_a, 4)

        imp_a = float(row_a["mean_importance"])
        imp_b = float(row_b["mean_importance"])
        delta_imp = round(imp_b - imp_a, 4)

        high_imp_a = int(row_a["high_importance_count"])
        high_imp_b = int(row_b["high_importance_count"])
        delta_high_imp = high_imp_b - high_imp_a

        nov_a = float(row_a["mean_novelty"])
        nov_b = float(row_b["mean_novelty"])
        delta_nov = round(nov_b - nov_a, 4)

        pos_a = int(row_a["positive_count"])
        pos_b = int(row_b["positive_count"])
        delta_pos = pos_b - pos_a

        neg_a = int(row_a["negative_count"])
        neg_b = int(row_b["negative_count"])
        delta_neg = neg_b - neg_a

        rows_delta.append({
            "trading_date": t_date,
            "target_date": tgt_date,
            "cutoff_timestamp_a": row_a["cutoff_timestamp"],
            "cutoff_timestamp_b": row_b["cutoff_timestamp"],
            "news_count_a": cnt_a,
            "news_count_b": cnt_b,
            "delta_news_count": delta_cnt,
            "mean_sentiment_a": mean_sent_a,
            "mean_sentiment_b": mean_sent_b,
            "delta_mean_sentiment": delta_mean_sent,
            "weighted_sentiment_a": sent_a,
            "weighted_sentiment_b": sent_b,
            "delta_b_minus_a_sentiment": delta_sent,
            "mean_importance_a": imp_a,
            "mean_importance_b": imp_b,
            "delta_mean_importance": delta_imp,
            "high_importance_count_a": high_imp_a,
            "high_importance_count_b": high_imp_b,
            "delta_high_importance_count": delta_high_imp,
            "mean_novelty_a": nov_a,
            "mean_novelty_b": nov_b,
            "delta_mean_novelty": delta_nov,
            "positive_count_a": pos_a,
            "positive_count_b": pos_b,
            "delta_positive_count": delta_pos,
            "negative_count_a": neg_a,
            "negative_count_b": neg_b,
            "delta_negative_count": delta_neg,
        })

    return pd.DataFrame(rows_delta)


def run_point_in_time_news_feature_pipeline(
    historical_inventory_path: Path,
    terminal_holdout_path: Path,
    nifty_daily_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """Execute the complete Phase 9 Step 3 Point-in-Time News NLP feature pipeline."""
    # 1. Forensic Hash Audit of Inputs
    logger.info("Verifying cryptographic hashes of input raw news datasets...")
    hist_sha = compute_file_sha256(historical_inventory_path)
    if hist_sha != EXPECTED_HISTORICAL_SHA:
        raise ValueError(f"Historical inventory SHA mismatch! Expected {EXPECTED_HISTORICAL_SHA}, got {hist_sha}")

    term_sha = compute_file_sha256(terminal_holdout_path)
    if term_sha != EXPECTED_TERMINAL_SHA:
        raise ValueError(f"Terminal holdout SHA mismatch! Expected {EXPECTED_TERMINAL_SHA}, got {term_sha}")

    # Verify Gold benchmark is isolated
    gold_path = historical_inventory_path.parent / "gold_holdout_annotation_input.csv"
    if gold_path.is_file():
        gold_sha = compute_file_sha256(gold_path)
        assert gold_sha == EXPECTED_GOLD_SHA, f"Gold benchmark altered! Expected {EXPECTED_GOLD_SHA}, got {gold_sha}"
        logger.info("Verified gold benchmark isolation: 100% UNTOUCHED.")

    # 2. Master Trading Calendar
    logger.info("Loading master trading calendar...")
    df_nifty = pd.read_csv(nifty_daily_path)
    trading_dates = sorted([date.fromisoformat(d) for d in df_nifty["trading_date"].unique()])
    trading_dates_set = set(trading_dates)
    ref_dates = trading_dates[:-1]
    tgt_dates = trading_dates[1:]
    assert len(ref_dates) == 4653, f"Expected 4653 trading day pairs, got {len(ref_dates)}"

    # 3. Ingest All 103,700 Authentic Records
    logger.info("Ingesting 62,329 historical + 41,371 terminal authentic records (103,700 total)...")
    all_raw_records = []
    
    # Read historical
    with open(historical_inventory_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_raw_records.append(json.loads(line))
    n_hist = len(all_raw_records)
    assert n_hist == EXPECTED_HISTORICAL_COUNT, f"Expected {EXPECTED_HISTORICAL_COUNT} historical records, got {n_hist}"

    # Read terminal Step 2E
    with open(terminal_holdout_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_raw_records.append(json.loads(line))
    n_total = len(all_raw_records)
    n_term = n_total - n_hist
    assert n_term == EXPECTED_TERMINAL_COUNT, f"Expected {EXPECTED_TERMINAL_COUNT} terminal records, got {n_term}"
    assert n_total == 103700, f"Expected 103,700 combined records, got {n_total}"

    # 4. Deterministic Chronological Sort
    logger.info("Sorting all 103,700 records deterministically by (published_timestamp, article_id)...")
    all_raw_records.sort(key=lambda r: (r["published_timestamp"], r["article_id"]))

    # 5. Causal Streaming NLP & Deduplication
    logger.info("Executing causal streaming NLP and deduplication across 103,700 records...")
    lm = LoughranMcDonaldIndianSentiment()
    dedup = StreamingDeduplicator(similarity_threshold=0.80, lookback_window_hours=168)

    records_by_snap_a: Dict[date, List[Dict[str, Any]]] = {d: [] for d in ref_dates}
    records_by_snap_b: Dict[date, List[Dict[str, Any]]] = {d: [] for d in ref_dates}

    count_a_total = 0
    count_b_total = 0
    count_a_active = 0
    count_b_active = 0
    unassigned_count = 0
    filtered_inactive_count = 0

    event_counts = {cat: 0 for cat in CANONICAL_PHASE8_EVENT_CATEGORIES}

    for d in all_raw_records:
        pub_dt = datetime.fromisoformat(d["published_timestamp"]).astimezone(TIMEZONE_KOLKATA)
        headline = d.get("headline", "").strip()
        body = d.get("summary_or_body", "").strip()
        full_text = f"{headline} — {body}" if body else headline
        article_id = d["article_id"]
        source = d.get("source", "NSE_OFFICIAL_DISCLOSURE")
        provider = d.get("provider", "NSE_PUBLIC_ANNOUNCEMENTS_API")

        # Entity Extraction & Resolution
        company_symbol = resolve_canonical_company_symbol(d)
        entities = extract_entities(headline, pub_dt.date())

        # Canonical Phase 8 Event Classification
        primary_evt, sec_evts, evt_conf = classify_phase8_events(full_text)
        event_counts[primary_evt] += 1
        primary_evt_enum = PHASE8_TO_EVENT_TYPE.get(primary_evt, EventType.ROUTINE_COMMENTARY)

        # Market Relevance & Ex-Ante Importance
        rel_cat, rel_score = evaluate_market_relevance(entities, primary_evt_enum, full_text)
        imp_score, imp_comps = compute_ex_ante_importance(
            SourceAuthorityTier.TIER_1_REGULATORY,
            primary_evt_enum,
            rel_cat,
            1,
        )

        # Sentiment Analysis
        sent_res = lm.analyze(full_text)

        # Intermediate record for streaming deduplicator
        temp_rec = CanonicalNewsRecord(
            news_id=article_id,
            source=source,
            source_type=SourceAuthorityTier.TIER_1_REGULATORY,
            headline=headline,
            published_timestamp=pub_dt,
            availability_timestamp=pub_dt,
            availability_evidence_level=AvailabilityEvidenceLevel.LEVEL_B,
            timezone="Asia/Kolkata",
            provenance=ProvenanceMetadata(
                provider=provider,
                source_identifier=article_id,
                retrieval_timestamp=pub_dt,
                source_timestamp=pub_dt,
                timezone="Asia/Kolkata",
                data_frequency=DataFrequency.MINUTE,
                tier=ProviderTier.OFFICIAL,
            ),
            lead_text=body,
            entities=entities,
            sectors=[],
            primary_event=primary_evt,
            secondary_events=sec_evts,
            event_confidence=evt_conf,
            market_relevance_category=rel_cat,
            market_relevance_score=rel_score,
            importance_score=imp_score,
            importance_components=imp_comps,
            sentiment_polarity=sent_res.polarity,
            sentiment_confidence=sent_res.confidence,
            sentiment_class=sent_res.sentiment_class,
            sentiment_model_id=sent_res.model_name,
            data_type="HISTORICAL_GENUINE",
        )

        is_dup, cid, nov_score, is_nov = dedup.process_record(temp_rec)

        # PIT Calendar Assignment
        pit_info = assign_record_pit(pub_dt, trading_dates, trading_dates_set)
        if pit_info.get("status") != "VALID":
            unassigned_count += 1
            continue

        t_pred = pit_info["prediction_date_T"]
        snap = pit_info["snapshot"]

        # Membership Filtering: Company must be active constituent at Session T
        is_active = is_active_nifty_constituent(company_symbol, t_pred)

        record_payload = {
            "article_id": article_id,
            "company_symbol": company_symbol,
            "headline": headline,
            "published_timestamp": pub_dt,
            "availability_timestamp": pub_dt,
            "primary_event": primary_evt,
            "secondary_events": sec_evts,
            "market_relevance_category": rel_cat,
            "market_relevance_score": rel_score,
            "importance_score": imp_score,
            "sentiment_polarity": sent_res.polarity,
            "sentiment_class": sent_res.sentiment_class,
            "novelty_score": nov_score,
            "cluster_id": cid,
            "is_novel": is_nov,
            "is_active_constituent": is_active,
        }

        if snap == "SNAPSHOT_A":
            count_a_total += 1
            if is_active:
                records_by_snap_a[t_pred].append(record_payload)
                count_a_active += 1
            else:
                filtered_inactive_count += 1
        else:
            count_b_total += 1
            if is_active:
                records_by_snap_b[t_pred].append(record_payload)
                count_b_active += 1
            else:
                filtered_inactive_count += 1

    logger.info(
        f"Processing Complete: Snapshot A (Active={count_a_active}, Total={count_a_total}), "
        f"Snapshot B (Active={count_b_active}, Total={count_b_total}), "
        f"Filtered Inactive={filtered_inactive_count}, Unassigned={unassigned_count}"
    )
    assert count_a_total + count_b_total + unassigned_count == 103700, "Record balance invariant violated!"

    # 6. Daily Feature Construction Across All 4,653 Sessions
    logger.info("Constructing daily Snapshot A and Snapshot B features across all 4,653 trading days...")
    rows_a = []
    rows_b = []

    for ref_d, tgt_d in zip(ref_dates, tgt_dates):
        recs_a = records_by_snap_a[ref_d]
        row_a = aggregate_daily_snapshot_features(
            records=recs_a,
            snapshot_type=SnapshotType.SNAPSHOT_1540,
            reference_date=ref_d,
            target_date=tgt_d,
            feed_is_healthy=True,
        )
        rows_a.append(row_a)

        recs_b = records_by_snap_b[ref_d]
        row_b = aggregate_daily_snapshot_features(
            records=recs_b,
            snapshot_type=SnapshotType.SNAPSHOT_0850,
            reference_date=ref_d,
            target_date=tgt_d,
            feed_is_healthy=True,
        )
        rows_b.append(row_b)

    df_a = pd.DataFrame(rows_a)
    df_b = pd.DataFrame(rows_b)
    df_delta = build_snapshot_delta_features(df_a, df_b)

    # Invariant Sanity Validations
    assert len(df_a) == 4653, f"Expected 4653 rows in df_a, got {len(df_a)}"
    assert len(df_b) == 4653, f"Expected 4653 rows in df_b, got {len(df_b)}"
    assert len(df_delta) == 4653, f"Expected 4653 rows in df_delta, got {len(df_delta)}"

    # Check for NaN / Inf
    assert not df_a.isna().any().any(), "Found NaN in Snapshot A daily dataframe!"
    assert not df_b.isna().any().any(), "Found NaN in Snapshot B daily dataframe!"
    assert not df_delta.isna().any().any(), "Found NaN in Diagnostic Delta dataframe!"

    num_cols_a = df_a.select_dtypes(include=np.number)
    num_cols_b = df_b.select_dtypes(include=np.number)
    num_cols_delta = df_delta.select_dtypes(include=np.number)

    assert not np.isinf(num_cols_a.values).any(), "Found infinity in Snapshot A features!"
    assert not np.isinf(num_cols_b.values).any(), "Found infinity in Snapshot B features!"
    assert not np.isinf(num_cols_delta.values).any(), "Found infinity in Snapshot Delta features!"

    # 7. Write Feature Artifacts
    output_dir.mkdir(parents=True, exist_ok=True)
    out_a_path = output_dir / "features_news_snapshot_a.csv"
    out_b_path = output_dir / "features_news_snapshot_b.csv"
    out_delta_path = output_dir / "features_news_snapshot_delta.csv"

    logger.info(f"Writing Snapshot A features to {out_a_path}...")
    df_a.to_csv(out_a_path, index=False)

    logger.info(f"Writing Snapshot B features to {out_b_path}...")
    df_b.to_csv(out_b_path, index=False)

    logger.info(f"Writing Diagnostic Delta features to {out_delta_path}...")
    df_delta.to_csv(out_delta_path, index=False)

    # Compute Output Checksums
    sha_a = compute_file_sha256(out_a_path)
    sha_b = compute_file_sha256(out_b_path)
    sha_delta = compute_file_sha256(out_delta_path)

    logger.info(f"Snapshot A SHA-256: {sha_a}")
    logger.info(f"Snapshot B SHA-256: {sha_b}")
    logger.info(f"Snapshot Delta SHA-256: {sha_delta}")

    return {
        "df_a": df_a,
        "df_b": df_b,
        "df_delta": df_delta,
        "sha_a": sha_a,
        "sha_b": sha_b,
        "sha_delta": sha_delta,
        "count_a_active": count_a_active,
        "count_b_active": count_b_active,
        "count_a_total": count_a_total,
        "count_b_total": count_b_total,
        "filtered_inactive_count": filtered_inactive_count,
        "unassigned_count": unassigned_count,
    }


__all__ = [
    "EXPECTED_HISTORICAL_SHA",
    "EXPECTED_HISTORICAL_COUNT",
    "EXPECTED_TERMINAL_SHA",
    "EXPECTED_TERMINAL_COUNT",
    "EXPECTED_GOLD_SHA",
    "resolve_canonical_company_symbol",
    "compute_information_decay",
    "aggregate_daily_snapshot_features",
    "build_snapshot_delta_features",
    "run_point_in_time_news_feature_pipeline",
]
