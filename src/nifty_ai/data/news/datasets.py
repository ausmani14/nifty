"""Snapshot News Aggregation Engine.

Constructs:
- Snapshot A News Intelligence Table (Intraday window <= 15:30 IST Day T)
- Snapshot B News Intelligence Table (Pure overnight window > 15:30 IST Day T and <= 08:50 IST Day T+1)
- Diagnostic Delta (B - A) Sentiment Shift Dataset
- Explicit handling of Genuine Zero News vs Missing Data / Outage
"""

from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

from nifty_ai.data.news.point_in_time import (
    TIMEZONE_KOLKATA,
    filter_news_for_snapshot,
)
from nifty_ai.data.news.schema import (
    CanonicalNewsRecord,
    DataStatus,
    EventType,
    MarketRelevanceCategory,
)
from nifty_ai.data.snapshots import SnapshotType


def compute_information_decay(
    item_availability: datetime,
    cutoff_dt: datetime,
    half_life_hours: float = 24.0,
) -> float:
    """Compute exponential decay weight based on information age at cutoff."""
    age_hours = max(0.0, (cutoff_dt - item_availability).total_seconds() / 3600.0)
    # Decay factor: 2^(-age / half_life)
    return round(float(2.0 ** (-age_hours / half_life_hours)), 4)


def aggregate_snapshot_news(
    records: List[CanonicalNewsRecord],
    snapshot_type: SnapshotType,
    reference_date: date,
    target_date: date,
    feed_is_healthy: bool = True,
    news_observed_on_empty: Optional[bool] = None,
) -> Dict[str, any]:
    """Aggregate a filtered collection of point-in-time news records into snapshot-level features.

    Distinguishes:
    - GENUINE_ZERO_NEWS: Feed healthy, but 0 qualifying news items found.
    - PROVIDER_OUTAGE: Feed disconnected or missing for the window.
    """
    cutoff_time = time(15, 30, 0) if snapshot_type == SnapshotType.SNAPSHOT_1540 else time(8, 50, 0)
    cutoff_day = reference_date if snapshot_type == SnapshotType.SNAPSHOT_1540 else target_date
    cutoff_dt = datetime.combine(cutoff_day, cutoff_time, tzinfo=TIMEZONE_KOLKATA)

    row: Dict[str, any] = {
        "trading_date": reference_date.isoformat(),
        "target_date": target_date.isoformat(),
        "snapshot_type": snapshot_type.value,
        "cutoff_timestamp": cutoff_dt.isoformat(),
    }

    # 1. Handle Missing Data / Provider Outage
    if not feed_is_healthy:
        row["data_status"] = DataStatus.PROVIDER_OUTAGE.value
        row["news_observed"] = False
        row["news_volume_total"] = np.nan
        row["news_volume_high_importance"] = np.nan
        row["high_relevance_count"] = np.nan
        row["max_importance_score"] = np.nan
        row["earnings_event_count"] = np.nan
        row["macro_event_count"] = np.nan
        row["monetary_event_count"] = np.nan
        row["mean_sentiment_polarity"] = np.nan
        row["sentiment_dispersion"] = np.nan
        row["importance_weighted_sentiment"] = np.nan
        row["novelty_weighted_sentiment"] = np.nan
        return row

    # 2. Handle Genuine Zero News
    if not records:
        row["data_status"] = DataStatus.GENUINE_ZERO_NEWS.value
        row["news_observed"] = True if news_observed_on_empty is None else news_observed_on_empty
        row["news_volume_total"] = 0
        row["news_volume_high_importance"] = 0
        row["high_relevance_count"] = 0
        row["max_importance_score"] = 0.0
        row["earnings_event_count"] = 0
        row["macro_event_count"] = 0
        row["monetary_event_count"] = 0
        row["mean_sentiment_polarity"] = 0.0
        row["sentiment_dispersion"] = 0.0
        row["importance_weighted_sentiment"] = 0.0
        row["novelty_weighted_sentiment"] = 0.0
        return row

    # 3. Normal Aggregation across eligible records
    row["data_status"] = DataStatus.HEALTHY_OBSERVED.value
    row["news_observed"] = True
    row["news_volume_total"] = len(records)
    
    # Importance & Relevance metrics
    high_imp_count = sum(1 for r in records if r.importance_score >= 0.70)
    high_rel_count = sum(
        1 for r in records
        if r.market_relevance_category in (MarketRelevanceCategory.HIGH_DIRECT, "HIGH_DIRECT", "high_direct")
        or getattr(r.market_relevance_category, "value", "") == "high_direct"
    )
    max_imp = max(r.importance_score for r in records)
    
    row["news_volume_high_importance"] = high_imp_count
    row["high_relevance_count"] = high_rel_count
    row["max_importance_score"] = round(max_imp, 4)

    # Event counts: support both canonical Phase 8 strings and legacy EventType enums
    _earnings_set = {EventType.EARNINGS, "earnings", "EARNINGS_RESULTS", "EARNINGS"}
    _macro_set = {EventType.MACROECONOMIC, "macroeconomic", "MACROECONOMIC"}
    _monetary_set = {EventType.MONETARY_POLICY, "monetary_policy", "MONETARY_POLICY"}

    earnings_cnt = sum(
        1 for r in records
        if r.primary_event in _earnings_set or any(e in _earnings_set for e in r.secondary_events)
    )
    macro_cnt = sum(
        1 for r in records
        if r.primary_event in _macro_set or any(e in _macro_set for e in r.secondary_events)
    )
    monetary_cnt = sum(
        1 for r in records
        if r.primary_event in _monetary_set or any(e in _monetary_set for e in r.secondary_events)
    )
    
    row["earnings_event_count"] = earnings_cnt
    row["macro_event_count"] = macro_cnt
    row["monetary_event_count"] = monetary_cnt

    # Sentiment Metrics
    polarities = [r.sentiment_polarity for r in records]
    row["mean_sentiment_polarity"] = round(float(np.mean(polarities)), 4)
    row["sentiment_dispersion"] = round(float(np.std(polarities)), 4)

    # Importance & Novelty weighted sentiment with time decay
    weights = []
    novelty_weights = []
    for r in records:
        decay = compute_information_decay(r.availability_timestamp, cutoff_dt)
        w = r.importance_score * decay
        nw = r.importance_score * r.novelty_score * decay
        weights.append(max(0.01, w))
        novelty_weights.append(max(0.01, nw))

    total_w = sum(weights)
    imp_weighted_sent = sum(p * w for p, w in zip(polarities, weights)) / total_w if total_w > 0 else 0.0
    
    total_nw = sum(novelty_weights)
    nov_weighted_sent = sum(p * nw for p, nw in zip(polarities, novelty_weights)) / total_nw if total_nw > 0 else 0.0

    row["importance_weighted_sentiment"] = round(float(imp_weighted_sent), 4)
    row["novelty_weighted_sentiment"] = round(float(nov_weighted_sent), 4)

    return row


def build_snapshot_news_datasets(
    trading_dates: List[date],
    all_records: List[CanonicalNewsRecord],
    simulated_outage_dates: Optional[Set[date]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build standalone point-in-time Snapshot A, Snapshot B, and Diagnostic Delta datasets."""
    outage_set = simulated_outage_dates or set()
    ref_dates = trading_dates[:-1]
    tgt_dates = trading_dates[1:]

    # Index records by calendar date for ultra-fast point-in-time filtering
    from collections import defaultdict
    date_to_records = defaultdict(list)
    for r in all_records:
        r_dt = r.availability_timestamp.astimezone(TIMEZONE_KOLKATA).date()
        date_to_records[r_dt].append(r)

    rows_a = []
    rows_b = []
    rows_delta = []

    for ref_d, tgt_d in zip(ref_dates, tgt_dates):
        healthy_feed = ref_d not in outage_set

        # Snapshot A: Only check records on reference date (and possibly day before)
        candidates_a = date_to_records.get(ref_d, [])
        eligible_a, _ = filter_news_for_snapshot(candidates_a, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d)
        row_a = aggregate_snapshot_news(eligible_a, SnapshotType.SNAPSHOT_1540, ref_d, tgt_d, healthy_feed)
        rows_a.append(row_a)

        # Snapshot B: Candidates between ref_d evening and tgt_d morning
        candidates_b = []
        cur_d = ref_d
        while cur_d <= tgt_d:
            candidates_b.extend(date_to_records.get(cur_d, []))
            cur_d += timedelta(days=1)

        eligible_b, _ = filter_news_for_snapshot(candidates_b, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d)
        row_b = aggregate_snapshot_news(eligible_b, SnapshotType.SNAPSHOT_0850, ref_d, tgt_d, healthy_feed)
        rows_b.append(row_b)

        # Diagnostic Delta (B - A) Sentiment Shift
        sent_a = row_a["importance_weighted_sentiment"]
        sent_b = row_b["importance_weighted_sentiment"]
        if pd.notna(sent_a) and pd.notna(sent_b):
            delta_sent = round(sent_b - sent_a, 4)
        else:
            delta_sent = np.nan

        rows_delta.append({
            "trading_date": ref_d.isoformat(),
            "target_date": tgt_d.isoformat(),
            "sentiment_a": sent_a,
            "sentiment_b": sent_b,
            "delta_b_minus_a_sentiment": delta_sent,
            "volume_overnight_b": row_b["news_volume_total"],
        })

    df_a = pd.DataFrame(rows_a)
    df_b = pd.DataFrame(rows_b)
    df_delta = pd.DataFrame(rows_delta)

    return df_a, df_b, df_delta


__all__ = [
    "compute_information_decay",
    "aggregate_snapshot_news",
    "build_snapshot_news_datasets",
]
