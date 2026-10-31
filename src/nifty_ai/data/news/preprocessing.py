"""Authentic News NLP Preprocessing & Daily Snapshot Feature Generation Engine.

Phase 9 Stage 4A:
- Converts authentic NSE news disclosures into canonical news representations.
- Extracts entities point-in-time, enforces 18-category canonical Phase 8 taxonomy.
- Evaluates ex-ante importance and market relevance without peeking at future price.
- Computes deterministic sentiment via LoughranMcDonaldIndianSentiment.
- Generates causal novelty via StreamingDeduplicator (7-day lookback).
- Assigns records strictly according to the verified Phase 8 PIT calendar partition:
  Snapshot A = 25,523, Snapshot B = 36,806, Total = 62,329.
- Generates authentic daily aggregates for Snapshot A and Snapshot B across all 4,653 trading days.
"""

from bisect import bisect_left
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

from nifty_ai.data.news.constituents import (
    CANONICAL_CONSTITUENTS,
    is_active_nifty_constituent,
)
from nifty_ai.data.news.datasets import (
    aggregate_snapshot_news,
    compute_information_decay,
)
from nifty_ai.data.news.deduplication import StreamingDeduplicator
from nifty_ai.data.news.nlp_engine import (
    compute_ex_ante_importance,
    evaluate_market_relevance,
    extract_entities,
    map_sectors_from_entities,
)
from nifty_ai.data.news.schema import (
    AvailabilityEvidenceLevel,
    BodyAvailabilityTier,
    CanonicalNewsRecord,
    DataStatus,
    EntityMention,
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

EXPECTED_RAW_INVENTORY_SHA = "6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3"
EXPECTED_RAW_RECORD_COUNT = 62329

# Authoritative 18-Category Event Taxonomy (17 Substantive + OTHER Fallback)
CANONICAL_PHASE8_EVENT_CATEGORIES = [
    "EARNINGS_RESULTS",
    "DIVIDEND",
    "BONUS_SPLIT",
    "RIGHTS_ISSUE",
    "BUYBACK",
    "M_AND_A",
    "CAPEX_BUSINESS_UPDATE",
    "FINANCIAL_IRREGULARITY",
    "SHAREHOLDING_CHANGE",
    "OPERATIONAL_EVENT",
    "STRATEGIC_PARTNERSHIP",
    "CREDIT_RATING_DEBT",
    "FUNDRAISING",
    "REGULATORY_LEGAL",
    "CORPORATE_ACTION",
    "MANAGEMENT_CHANGE",
    "ORDER_CONTRACT",
    "OTHER",
]

# Regex patterns for deterministic Phase 8 event classification
PHASE8_EVENT_PATTERNS: Dict[str, List[str]] = {
    "EARNINGS_RESULTS": [
        r"\bfinancial results\b", r"\bquarterly results\b", r"\baudited results\b",
        r"\bunaudited results\b", r"\bnet profit\b", r"\bq[1-4].*?(results|profit|loss)",
        r"\blimited review report\b", r"\bebitda\b", r"\bpat (jumps|falls|beats|rises|rose)",
        r"\bquarterly (financial|operating)\b", r"\bstatement of.*?(profit|loss)",
    ],
    "DIVIDEND": [
        r"\bdividend\b", r"\binterim dividend\b", r"\bfinal dividend\b",
        r"\brecommends.*?dividend\b", r"\bdeclared.*?dividend\b", r"\bbook closure for.*?dividend\b",
    ],
    "BONUS_SPLIT": [
        r"\bbonus share\b", r"\bbonus issue\b", r"\bstock split\b",
        r"\bsub-division of shares\b", r"\bsubdivision of nominal\b", r"\bconsolidation of shares\b",
    ],
    "RIGHTS_ISSUE": [
        r"\brights issue\b", r"\brights entitlement\b", r"\bletter of offer\b",
        r"\brights basis\b",
    ],
    "BUYBACK": [
        r"\bbuyback\b", r"\bbuy-back\b", r"\bextinguishment of.*?shares\b",
        r"\btender offer\b", r"\bshare buyback\b",
    ],
    "M_AND_A": [
        r"\bmerger\b", r"\bacquisition\b", r"\bacquires\b", r"\bdemerger\b",
        r"\bamalgamation\b", r"\btakeover\b", r"\bslump sale\b", r"\bscheme of arrangement\b",
        r"\bstake sale\b", r"\bdivestment\b", r"\btransfer of.*?undertaking\b",
    ],
    "CAPEX_BUSINESS_UPDATE": [
        r"\bnew plant\b", r"\bcapacity expansion\b", r"\bcommissioning\b",
        r"\bcommercial launch\b", r"\bcapex\b", r"\bincorporation of wholly owned subsidiary\b",
        r"\bgreenfield facility\b", r"\bbrownfield expansion\b", r"\bmanufacturing unit\b",
    ],
    "FINANCIAL_IRREGULARITY": [
        r"\bforensic audit\b", r"\bfraud\b", r"\baccounting irregularities\b",
        r"\baudit qualification\b", r"\bresignation of auditor.*?(dispute|qualification)",
        r"\bfinancial restatement\b",
    ],
    "SHAREHOLDING_CHANGE": [
        r"\binsider trading\b", r"\bregulation 13\(", r"\bregulation 7\(2\)",
        r"\bpromoter pledge\b", r"\brevocation of pledge\b", r"\bsast\b",
        r"\btakeover regulations\b", r"\bsubstantial acquisition\b", r"\bshareholding pattern\b",
    ],
    "OPERATIONAL_EVENT": [
        r"\bstrike\b", r"\blockout\b", r"\bplant shutdown\b", r"\btemporary suspension\b",
        r"\bfire accident\b", r"\bindustrial dispute\b", r"\boperational disruption\b",
    ],
    "STRATEGIC_PARTNERSHIP": [
        r"\bjoint venture\b", r"\bstrategic partnership\b", r"\bcommercial alliance\b",
        r"\btechnical collaboration\b", r"\bmemorandum of understanding\b", r"\bmou\b",
    ],
    "CREDIT_RATING_DEBT": [
        r"\bcredit rating\b", r"\brating assigned\b", r"\brating reaffirmed\b",
        r"\bcrisil\b", r"\bicra\b", r"\bcare rating\b", r"\bnon-convertible debenture\b",
        r"\bncd\b", r"\bcommercial paper\b", r"\bredemption of debenture\b",
    ],
    "FUNDRAISING": [
        r"\bqualified institutional placement\b", r"\bqip\b", r"\bpreferential allotment\b",
        r"\braising of funds\b", r"\bissue of securities\b", r"\bwarrants allotment\b",
        r"\bgdr\b", r"\badr\b",
    ],
    "REGULATORY_LEGAL": [
        r"\bsebi\b", r"\breserve bank of india\b", r"\brbi\b", r"\busfda\b",
        r"\bform 483\b", r"\bwarning letter\b", r"\bpenalty\b", r"\bshow cause notice\b",
        r"\bhigh court\b", r"\bsupreme court\b", r"\bnclt\b", r"\btribunal\b",
        r"\benforcement directorate\b", r"\bcompetition commission\b",
    ],
    "CORPORATE_ACTION": [
        r"\bloss of share\b", r"\bduplicate share\b", r"\bcompliance certificate\b",
        r"\bregulation 39\(3\)", r"\bregulation 7\(3\)", r"\bregulation 40\(9\)",
        r"\btrading window\b", r"\besop\b", r"\besos\b",
    ],
    "MANAGEMENT_CHANGE": [
        r"\bappointment of\b", r"\bresignation of\b", r"\bcessation of\b",
        r"\bdemise of\b", r"\bmanaging director\b", r"\bchief executive officer\b",
        r"\bceo\b", r"\bchief financial officer\b", r"\bcfo\b", r"\bcompany secretary\b",
        r"\bindependent director\b", r"\bboard reshuffle\b",
    ],
    "ORDER_CONTRACT": [
        r"\border win\b", r"\bbags order\b", r"\bsecures contract\b",
        r"\bawarded order\b", r"\bcontract worth\b", r"\bmajor order\b",
        r"\bproject award\b", r"\bsupply contract\b", r"\bcommercial agreement\b",
    ],
}

# Mapping of Phase 8 canonical categories to EventType enums for rubric scoring
PHASE8_TO_EVENT_TYPE: Dict[str, EventType] = {
    "EARNINGS_RESULTS": EventType.EARNINGS,
    "DIVIDEND": EventType.CORPORATE_ACTION,
    "BONUS_SPLIT": EventType.CORPORATE_ACTION,
    "RIGHTS_ISSUE": EventType.CORPORATE_ACTION,
    "BUYBACK": EventType.CORPORATE_ACTION,
    "M_AND_A": EventType.CORPORATE_ACTION,
    "CAPEX_BUSINESS_UPDATE": EventType.CAPEX_INVESTMENT,
    "FINANCIAL_IRREGULARITY": EventType.REGULATORY_LEGAL,
    "SHAREHOLDING_CHANGE": EventType.CORPORATE_ACTION,
    "OPERATIONAL_EVENT": EventType.CORPORATE_ACTION,
    "STRATEGIC_PARTNERSHIP": EventType.CORPORATE_ACTION,
    "CREDIT_RATING_DEBT": EventType.CREDIT_DEBT,
    "FUNDRAISING": EventType.CORPORATE_ACTION,
    "REGULATORY_LEGAL": EventType.REGULATORY_LEGAL,
    "CORPORATE_ACTION": EventType.CORPORATE_ACTION,
    "MANAGEMENT_CHANGE": EventType.MANAGEMENT_CHANGE,
    "ORDER_CONTRACT": EventType.ORDER_CONTRACT,
    "OTHER": EventType.ROUTINE_COMMENTARY,
}


def classify_phase8_events(text: str) -> Tuple[str, List[str], float]:
    """Classify disclosure text into the 18-category canonical Phase 8 taxonomy.

    Applies the waterfall precedence:
    EARNINGS_RESULTS -> DIVIDEND -> BONUS_SPLIT -> RIGHTS_ISSUE -> BUYBACK ->
    M_AND_A -> CAPEX_BUSINESS_UPDATE -> FINANCIAL_IRREGULARITY ->
    SHAREHOLDING_CHANGE -> OPERATIONAL_EVENT -> STRATEGIC_PARTNERSHIP ->
    CREDIT_RATING_DEBT -> FUNDRAISING -> REGULATORY_LEGAL -> CORPORATE_ACTION ->
    MANAGEMENT_CHANGE -> ORDER_CONTRACT -> OTHER.
    """
    text_lower = text.lower()
    matched_cats: List[Tuple[str, int]] = []

    for cat in CANONICAL_PHASE8_EVENT_CATEGORIES:
        if cat == "OTHER":
            continue
        pats = PHASE8_EVENT_PATTERNS.get(cat, [])
        matches = sum(1 for p in pats if re.search(p, text_lower))
        if matches > 0:
            matched_cats.append((cat, matches))

    if not matched_cats:
        return "OTHER", [], 0.50

    # Sort primarily by match count descending, then by waterfall order
    waterfall_order = {cat: i for i, cat in enumerate(CANONICAL_PHASE8_EVENT_CATEGORIES)}
    matched_cats.sort(key=lambda x: (-x[1], waterfall_order.get(x[0], 999)))

    primary = matched_cats[0][0]
    secondaries = [c[0] for c in matched_cats[1:4]]
    confidence = min(1.0, 0.60 + 0.10 * matched_cats[0][1])

    return primary, secondaries, round(confidence, 2)


def assign_record_pit(
    pub_dt: datetime,
    trading_dates: List[date],
    trading_dates_set: Set[date],
) -> Dict[str, Any]:
    """Assign an authentic news timestamp to prediction date T and Snapshot A or B.

    Authoritative Phase 8 Calendar Partition (verified in scratch/audit_pit_assignment.py):
    - Trading day d, clock <= 08:50:00 -> Overnight B(T_prev) into d
    - Trading day d, 08:50:00 < clock <= 15:30:00 -> Intraday A(d) into T_next
    - Trading day d, clock > 15:30:00 -> Overnight B(d) into T_next
    - Non-trading day (weekend/holiday) -> Overnight B(T_prev) into T_next
    """
    dt_ist = pub_dt.astimezone(TIMEZONE_KOLKATA)
    d = dt_ist.date()
    t = dt_ist.time()

    cutoff_0850 = time(8, 50, 0)
    cutoff_1530 = time(15, 30, 0)

    is_trading_day = d in trading_dates_set

    if is_trading_day:
        idx = bisect_left(trading_dates, d)
        if t <= cutoff_0850:
            if idx > 0:
                t_pred = trading_dates[idx - 1]
                t_next = d
                snap = "SNAPSHOT_B"
            else:
                return {"status": "OUT_OF_BOUNDS"}
        elif t <= cutoff_1530:
            t_pred = d
            t_next = trading_dates[idx + 1] if idx + 1 < len(trading_dates) else None
            snap = "SNAPSHOT_A"
        else:
            t_pred = d
            t_next = trading_dates[idx + 1] if idx + 1 < len(trading_dates) else None
            snap = "SNAPSHOT_B"
    else:
        idx = bisect_left(trading_dates, d)
        if idx == 0:
            return {"status": "OUT_OF_BOUNDS"}
        t_pred = trading_dates[idx - 1]
        t_next = trading_dates[idx] if idx < len(trading_dates) else None
        snap = "SNAPSHOT_B"

    if t_next is None:
        return {"status": "TERMINAL_DATE"}

    cutoff_time = time(15, 30, 0) if snap == "SNAPSHOT_A" else time(8, 50, 0)
    cutoff_day = t_pred if snap == "SNAPSHOT_A" else t_next
    cutoff_dt = datetime.combine(cutoff_day, cutoff_time, tzinfo=TIMEZONE_KOLKATA)

    return {
        "status": "VALID",
        "snapshot": snap,
        "prediction_date_T": t_pred,
        "target_date": t_next,
        "cutoff_timestamp": cutoff_dt,
    }


def run_authentic_news_preprocessing_pipeline(
    raw_inventory_path: Path,
    nifty_daily_path: Path,
    output_dir: Path,
) -> Dict[str, Any]:
    """Execute the complete Stage 4A preprocessing pipeline."""
    logger.info("Verifying raw authentic inventory file and hash...")
    assert raw_inventory_path.is_file(), f"Missing raw inventory: {raw_inventory_path}"

    h = hashlib.sha256()
    with open(raw_inventory_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    actual_sha = h.hexdigest()
    if actual_sha != EXPECTED_RAW_INVENTORY_SHA:
        raise ValueError(f"CRITICAL: Raw inventory SHA mismatch! Expected {EXPECTED_RAW_INVENTORY_SHA}, got {actual_sha}")

    # 1. Load official NIFTY 50 trading calendar
    df_nifty = pd.read_csv(nifty_daily_path)
    trading_dates = sorted([date.fromisoformat(d) for d in df_nifty["trading_date"].unique()])
    trading_dates_set = set(trading_dates)
    logger.info(f"Loaded {len(trading_dates)} NIFTY trading dates: {trading_dates[0]} to {trading_dates[-1]}")

    ref_dates = trading_dates[:-1]
    tgt_dates = trading_dates[1:]
    assert len(ref_dates) == 4653, f"Expected 4653 trading day pairs, got {len(ref_dates)}"

    # 2. Ingest and sort all authentic records
    logger.info("Loading and chronologically sorting 62,329 authentic records...")
    raw_records = []
    with open(raw_inventory_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw_records.append(json.loads(line))

    if len(raw_records) != EXPECTED_RAW_RECORD_COUNT:
        raise ValueError(f"Expected {EXPECTED_RAW_RECORD_COUNT} records, got {len(raw_records)}")

    # Sort deterministically by (published_timestamp, article_id)
    raw_records.sort(key=lambda r: (r["published_timestamp"], r["article_id"]))

    # 3. Deterministic NLP Preprocessing & Streaming Deduplication
    logger.info("Executing deterministic NLP preprocessing and streaming deduplication...")
    lm = LoughranMcDonaldIndianSentiment()
    dedup = StreamingDeduplicator(similarity_threshold=0.80, lookback_window_hours=168)

    canonical_records: List[CanonicalNewsRecord] = []
    records_by_snap_a: Dict[date, List[CanonicalNewsRecord]] = {d: [] for d in ref_dates}
    records_by_snap_b: Dict[date, List[CanonicalNewsRecord]] = {d: [] for d in ref_dates}

    count_a = 0
    count_b = 0
    unassigned_count = 0

    event_distribution = {cat: 0 for cat in CANONICAL_PHASE8_EVENT_CATEGORIES}
    sentiment_distribution = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
    relevance_distribution = {cat.value: 0 for cat in MarketRelevanceCategory}
    importance_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for d in raw_records:
        pub_dt = datetime.fromisoformat(d["published_timestamp"]).astimezone(TIMEZONE_KOLKATA)
        headline = d.get("headline", "").strip()
        body = d.get("summary_or_body", "").strip()
        full_text = f"{headline} — {body}" if body else headline

        # NLP Extractions
        entities = extract_entities(headline, pub_dt.date())
        sectors = map_sectors_from_entities(entities)

        primary_evt, sec_evts, evt_conf = classify_phase8_events(full_text)
        event_distribution[primary_evt] += 1

        primary_evt_enum = PHASE8_TO_EVENT_TYPE.get(primary_evt, EventType.ROUTINE_COMMENTARY)

        rel_cat, rel_score = evaluate_market_relevance(entities, primary_evt_enum, full_text)
        relevance_distribution[rel_cat.value] += 1

        imp_score, imp_comps = compute_ex_ante_importance(
            SourceAuthorityTier.TIER_1_REGULATORY,
            primary_evt_enum,
            rel_cat,
            1,
        )
        # Map importance score to 1-5 rubric
        if imp_score >= 0.80:
            imp_ord = 5
        elif imp_score >= 0.65:
            imp_ord = 4
        elif imp_score >= 0.45:
            imp_ord = 3
        elif imp_score >= 0.30:
            imp_ord = 2
        else:
            imp_ord = 1
        importance_distribution[imp_ord] += 1

        sent_res = lm.analyze(full_text)
        sentiment_distribution[sent_res.sentiment_class] += 1

        # Intermediate record for causal deduplicator
        temp_rec = CanonicalNewsRecord(
            news_id=d["article_id"],
            source=d["source"],
            source_type=SourceAuthorityTier.TIER_1_REGULATORY,
            headline=headline,
            published_timestamp=pub_dt,
            availability_timestamp=pub_dt,
            availability_evidence_level=AvailabilityEvidenceLevel.LEVEL_B,
            timezone="Asia/Kolkata",
            provenance=ProvenanceMetadata(
                provider=d["provider"],
                source_identifier=d["article_id"],
                retrieval_timestamp=pub_dt,
                source_timestamp=pub_dt,
                timezone="Asia/Kolkata",
                data_frequency=DataFrequency.MINUTE,
                tier=ProviderTier.OFFICIAL,
            ),
            lead_text=body,
            entities=entities,
            sectors=sectors,
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

        # Final record with novelty attributes
        final_rec = CanonicalNewsRecord(
            news_id=temp_rec.news_id,
            source=temp_rec.source,
            source_type=temp_rec.source_type,
            headline=temp_rec.headline,
            published_timestamp=temp_rec.published_timestamp,
            availability_timestamp=temp_rec.availability_timestamp,
            availability_evidence_level=temp_rec.availability_evidence_level,
            timezone=temp_rec.timezone,
            provenance=temp_rec.provenance,
            lead_text=temp_rec.lead_text,
            url=d.get("source_url"),
            entities=temp_rec.entities,
            sectors=temp_rec.sectors,
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
            novelty_score=nov_score,
            cluster_id=cid,
            is_novel=is_nov,
            data_type="HISTORICAL_GENUINE",
        )
        canonical_records.append(final_rec)

        # PIT Assignment
        pit_info = assign_record_pit(pub_dt, trading_dates, trading_dates_set)
        if pit_info.get("status") == "VALID":
            t_pred = pit_info["prediction_date_T"]
            snap = pit_info["snapshot"]
            if snap == "SNAPSHOT_A":
                records_by_snap_a[t_pred].append(final_rec)
                count_a += 1
            else:
                records_by_snap_b[t_pred].append(final_rec)
                count_b += 1
        else:
            unassigned_count += 1

    logger.info(f"PIT Assignment Complete: Snapshot A = {count_a}, Snapshot B = {count_b}, Unassigned = {unassigned_count}")
    if count_a != 25523 or count_b != 36806 or unassigned_count != 0:
        raise ValueError(
            f"CRITICAL PIT MISMATCH! Expected A=25,523, B=36,806, Unassigned=0. "
            f"Got A={count_a}, B={count_b}, Unassigned={unassigned_count}"
        )

    # 4. Save canonical_news_records.jsonl
    output_dir.mkdir(parents=True, exist_ok=True)
    canonical_jsonl_path = output_dir / "canonical_news_records.jsonl"
    logger.info(f"Writing {len(canonical_records)} canonical news records to {canonical_jsonl_path}...")
    with open(canonical_jsonl_path, "w", encoding="utf-8") as f:
        for r in canonical_records:
            f.write(json.dumps(r.to_dict()) + "\n")

    # 5. Build daily aggregates for Snapshot A and Snapshot B
    logger.info("Constructing authentic daily aggregates across all 4,653 trading sessions...")
    rows_a = []
    rows_b = []
    rows_delta = []

    for ref_d, tgt_d in zip(ref_dates, tgt_dates):
        recs_a = records_by_snap_a[ref_d]
        row_a = aggregate_snapshot_news(
            recs_a,
            SnapshotType.SNAPSHOT_1540,
            ref_d,
            tgt_d,
            feed_is_healthy=True,
            news_observed_on_empty=False,
        )
        rows_a.append(row_a)

        recs_b = records_by_snap_b[ref_d]
        row_b = aggregate_snapshot_news(
            recs_b,
            SnapshotType.SNAPSHOT_0850,
            ref_d,
            tgt_d,
            feed_is_healthy=True,
            news_observed_on_empty=False,
        )
        rows_b.append(row_b)

        # Diagnostic Delta
        sent_a = row_a["importance_weighted_sentiment"]
        sent_b = row_b["importance_weighted_sentiment"]
        rows_delta.append({
            "trading_date": ref_d.isoformat(),
            "target_date": tgt_d.isoformat(),
            "sentiment_a": sent_a,
            "sentiment_b": sent_b,
            "delta_b_minus_a_sentiment": round(sent_b - sent_a, 4),
            "volume_overnight_b": row_b["news_volume_total"],
        })

    df_a = pd.DataFrame(rows_a)
    df_b = pd.DataFrame(rows_b)
    df_delta = pd.DataFrame(rows_delta)

    # Invariant assertions
    assert len(df_a) == 4653, f"Expected 4653 rows in df_a, got {len(df_a)}"
    assert len(df_b) == 4653, f"Expected 4653 rows in df_b, got {len(df_b)}"
    assert not df_a.isna().any().any(), "Found NaN in Snapshot A daily dataframe!"
    assert not df_b.isna().any().any(), "Found NaN in Snapshot B daily dataframe!"

    out_a_csv = output_dir / "snapshot_a_news_daily.csv"
    out_b_csv = output_dir / "snapshot_b_news_daily.csv"
    out_delta_csv = output_dir / "diagnostic_delta_b_minus_a_news.csv"

    df_a.to_csv(out_a_csv, index=False)
    df_b.to_csv(out_b_csv, index=False)
    df_delta.to_csv(out_delta_csv, index=False)

    logger.info(f"Saved authentic Snapshot A news daily to {out_a_csv}")
    logger.info(f"Saved authentic Snapshot B news daily to {out_b_csv}")
    logger.info(f"Saved Diagnostic Delta news daily to {out_delta_csv}")

    # 6. Compute SHA-256 hashes of generated artifacts
    def compute_sha(path: Path) -> str:
        s = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                s.update(chunk)
        return s.hexdigest()

    sha_jsonl = compute_sha(canonical_jsonl_path)
    sha_a = compute_sha(out_a_csv)
    sha_b = compute_sha(out_b_csv)
    sha_delta = compute_sha(out_delta_csv)

    results = {
        "status": "STAGE_4A_COMPLETE",
        "input_record_count": len(raw_records),
        "input_sha256": actual_sha,
        "count_snapshot_a": count_a,
        "count_snapshot_b": count_b,
        "unassigned_count": unassigned_count,
        "trading_day_pairs": len(ref_dates),
        "df_a_rows": len(df_a),
        "df_b_rows": len(df_b),
        "no_news_days_a": int((df_a["news_volume_total"] == 0).sum()),
        "no_news_days_b": int((df_b["news_volume_total"] == 0).sum()),
        "event_distribution": event_distribution,
        "sentiment_distribution": sentiment_distribution,
        "relevance_distribution": relevance_distribution,
        "importance_distribution": importance_distribution,
        "sha_canonical_jsonl": sha_jsonl,
        "sha_snapshot_a_csv": sha_a,
        "sha_snapshot_b_csv": sha_b,
        "sha_diagnostic_delta_csv": sha_delta,
        "df_a_stats": df_a.describe().to_dict(),
        "df_b_stats": df_b.describe().to_dict(),
    }
    return results
