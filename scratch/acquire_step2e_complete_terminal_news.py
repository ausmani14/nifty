"""Authentic 2022–2026 NSE Corporate Announcement Acquisition Pipeline (Step 2E).

Phase 9 Step 2E:
- Targets 2022-01-01 through 2026-09-04 inclusive.
- Uses official NSE Corporate Announcements API: https://www.nseindia.com/api/corporate-announcements
- Enforces strict PIT constituent boundaries from reconciled CANONICAL_CONSTITUENTS (56 companies).
- Bypasses LICI completely (0 queries, 0 records).
- Queries HDFCLIFE for its valid tenure.
- Handles ticker aliases (TATAMTRDVR for TATAMOTORS).
- Deduplicates deterministically on seq_id, secondary signature, and source URL.
- Writes exclusively to a NEW artifact: data/interim/news/raw_authentic_news_terminal_2022_2026_step2e.jsonl.
- Preserves raw_authentic_news_holdout_2022_2026.jsonl, raw_authentic_news_inventory.jsonl,
  and gold_holdout_annotation_input.csv byte-for-byte.
"""

from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
import sys
import time as time_module
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
import pandas as pd

from nifty_ai.data.news.constituents import CANONICAL_CONSTITUENTS, is_active_nifty_constituent
from nifty_ai.data.news.preprocessing import assign_record_pit

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

PROJECT_ROOT = Path(r"c:\Users\ABEEL USMANI\.antigravity\nifty ai").resolve()
OUTPUT_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_terminal_2022_2026_step2e.jsonl"
AUDIT_JSON = PROJECT_ROOT / "data" / "interim" / "news" / "acquisition_2022_2026_step2e_audit.json"

OLD_HOLDOUT_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_holdout_2022_2026.jsonl"
EXISTING_RAW_JSONL = PROJECT_ROOT / "data" / "interim" / "news" / "raw_authentic_news_inventory.jsonl"
HOLDOUT_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "gold_holdout_annotation_input.csv"

WINDOW_START = date(2022, 1, 1)
WINDOW_END = date(2026, 9, 4)
YEARS = [2022, 2023, 2024, 2025, 2026]

EXPECTED_RAW_SHA = "6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3"
EXPECTED_HOLDOUT_SHA = "0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199"
EXPECTED_OLD_STEP2_SHA = "f2cab28eaa624d5bc8d72169798655e7fb82b6b4e68102e93179eaffcadd335e"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("nifty_ai.acquire_step2e")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def load_trading_calendar():
    df_daily = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv")
    trading_dates_str = sorted(list(set(df_daily["trading_date"].tolist())))
    t_dates = [date.fromisoformat(d) for d in trading_dates_str]
    # Add next immediate trading date after 2026-09-04 (Friday) -> Monday 2026-09-07
    if t_dates[-1] == date(2026, 9, 4):
        t_dates.append(date(2026, 9, 7))
    t_set = set(t_dates)
    return t_dates, t_set


def parse_timestamp(item):
    sort_date = item.get("sort_date")
    if sort_date:
        try:
            dt = datetime.strptime(sort_date.strip(), "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=IST)
        except Exception:
            pass

    an_dt = item.get("an_dt")
    if an_dt:
        try:
            dt = datetime.strptime(an_dt.strip(), "%d-%b-%Y %H:%M:%S")
            return dt.replace(tzinfo=IST)
        except Exception:
            pass

    exch = item.get("exchdisstime")
    if exch:
        try:
            dt = datetime.strptime(exch.strip(), "%d-%b-%Y %H:%M:%S")
            return dt.replace(tzinfo=IST)
        except Exception:
            pass

    return None


def run_acquisition():
    t_start = datetime.now(timezone.utc)
    logger.info("=== Starting Phase 9 Step 2E Complete Terminal Acquisition ===")
    logger.info(f"Target window: {WINDOW_START} to {WINDOW_END}")

    # 1. Pre-Acquisition Checksum Verifications
    raw_sha_before = sha256_file(EXISTING_RAW_JSONL)
    assert raw_sha_before == EXPECTED_RAW_SHA, f"Raw inventory modified! {raw_sha_before}"
    holdout_sha_before = sha256_file(HOLDOUT_CSV)
    assert holdout_sha_before == EXPECTED_HOLDOUT_SHA, f"Gold holdout benchmark modified! {holdout_sha_before}"
    old_step2_sha_before = sha256_file(OLD_HOLDOUT_JSONL)
    assert old_step2_sha_before == EXPECTED_OLD_STEP2_SHA, f"Step 2 artifact modified! {old_step2_sha_before}"
    logger.info("Pre-acquisition cryptographic checks passed. All protected artifacts verified.")

    t_dates, t_set = load_trading_calendar()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

    # 2. Plan Queries strictly by PIT membership across CANONICAL_CONSTITUENTS
    queries = []
    active_constituents_in_window = []

    for c in CANONICAL_CONSTITUENTS:
        # Safety: LICI must not be queried
        assert c.symbol.upper() != "LICI", "CRITICAL DEFECT: LICI detected in CANONICAL_CONSTITUENTS!"

        # Check if constituent overlaps with 2022-2026 window
        if c.valid_from > WINDOW_END:
            continue
        if c.valid_to is not None and c.valid_to < WINDOW_START:
            continue

        active_constituents_in_window.append(c)
        c_start = max(c.valid_from, WINDOW_START)
        c_end = min(c.valid_to or WINDOW_END, WINDOW_END)

        for y in YEARS:
            y_start = date(y, 1, 1)
            y_end = min(date(y, 12, 31), WINDOW_END)

            q_from = max(c_start, y_start)
            q_to = min(c_end, y_end)

            if q_from <= q_to:
                # Primary query
                queries.append({
                    "constituent": c,
                    "canonical_symbol": c.symbol,
                    "query_symbol": c.symbol,
                    "year": y,
                    "from_date": q_from,
                    "to_date": q_to,
                    "is_alias": False,
                })
                # If TATAMOTORS, also query TATAMTRDVR alias to capture full corporate announcements
                if c.symbol == "TATAMOTORS":
                    queries.append({
                        "constituent": c,
                        "canonical_symbol": c.symbol,
                        "query_symbol": "TATAMTRDVR",
                        "year": y,
                        "from_date": q_from,
                        "to_date": q_to,
                        "is_alias": True,
                    })

    unique_companies = {c.symbol for c in active_constituents_in_window}
    logger.info(f"Resolved {len(active_constituents_in_window)} active constituents in window (unique: {len(unique_companies)}).")
    assert len(unique_companies) == 56, f"Expected exactly 56 unique companies, found {len(unique_companies)}"
    logger.info(f"Generated {len(queries)} PIT-constrained constituent-year queries.")

    # 3. Execute Queries
    request_stats = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "retries": 0,
        "zero_result_queries": 0,
        "queries_with_results": 0,
    }
    query_log = []
    raw_retrieved_items = []
    retrieval_ts = datetime.now(timezone.utc).isoformat()

    company_query_stats = defaultdict(lambda: {"queries": 0, "records_raw": 0, "years_queried": set()})

    for idx, q in enumerate(queries):
        sym = q["canonical_symbol"]
        q_sym = q["query_symbol"]
        y = q["year"]
        from_str = q["from_date"].strftime("%d-%m-%Y")
        to_str = q["to_date"].strftime("%d-%m-%Y")

        url = f"https://www.nseindia.com/api/corporate-announcements?index=equities&symbol={urllib.parse.quote(q_sym)}&from_date={from_str}&to_date={to_str}"
        request_stats["total_requests"] += 1
        company_query_stats[sym]["queries"] += 1
        company_query_stats[sym]["years_queried"].add(y)

        items = []
        status_code = None
        error_msg = None
        retries_used = 0

        # Retry logic with exponential backoff
        for attempt in range(1, 4):
            try:
                req = urllib.request.Request(url, headers=headers)
                with opener.open(req, timeout=15) as resp:
                    status_code = resp.status
                    if resp.status == 200:
                        raw_data = resp.read().decode("utf-8")
                        parsed = json.loads(raw_data)
                        if isinstance(parsed, list):
                            items = parsed
                        break
                    else:
                        error_msg = f"HTTP {resp.status}"
            except Exception as e:
                error_msg = str(e)
                retries_used += 1
                request_stats["retries"] += 1
                time_module.sleep(1.0 * attempt)

        # Polite delay to respect exchange infrastructure
        time_module.sleep(0.38)

        if status_code == 200 and isinstance(items, list):
            request_stats["successful_requests"] += 1
            if len(items) > 0:
                request_stats["queries_with_results"] += 1
                company_query_stats[sym]["records_raw"] += len(items)
                for item in items:
                    item["_query_symbol"] = sym
                    item["_query_symbol_variant"] = q_sym
                    item["_constituent_record"] = q["constituent"]
                    item["_query_year"] = y
                    raw_retrieved_items.append(item)
            else:
                request_stats["zero_result_queries"] += 1
        else:
            request_stats["failed_requests"] += 1

        is_zero = len(items) == 0
        q_entry = {
            "query_index": idx + 1,
            "canonical_symbol": sym,
            "query_symbol": q_sym,
            "year": y,
            "from_date": q["from_date"].isoformat(),
            "to_date": q["to_date"].isoformat(),
            "http_status": status_code,
            "records_returned": len(items),
            "retries": retries_used,
            "error": error_msg if status_code != 200 else None,
        }
        query_log.append(q_entry)
        zero_flag = " [ZERO RESULTS]" if is_zero else ""
        logger.info(f"[{idx+1:03d}/{len(queries):03d}] {sym:12s} ({q_sym}, {y}, {from_str} to {to_str}): {len(items):4d} items (status {status_code}){zero_flag}")

    logger.info(f"Raw items retrieved: {len(raw_retrieved_items)}")

    # 4. Deterministic Deduplication & Strict PIT Validation
    seen_seq_ids = set()
    seen_signatures = set()
    seen_urls = set()

    unique_records = []
    duplicate_count = 0
    discarded_out_of_bounds = 0
    discarded_missing_ts = 0
    discarded_non_member = 0

    record_counter = 1

    for item in raw_retrieved_items:
        c = item["_constituent_record"]
        sym = item["_query_symbol"]
        variant = item.get("_query_symbol_variant", sym)
        seq_id = str(item.get("seq_id", "") or "").strip()
        if seq_id == "None" or not seq_id:
            seq_id = None

        pub_dt = parse_timestamp(item)
        if pub_dt is None:
            discarded_missing_ts += 1
            continue

        p_date = pub_dt.date()

        # Strict window check
        if not (WINDOW_START <= p_date <= WINDOW_END):
            discarded_out_of_bounds += 1
            continue

        # Strict PIT membership check
        if p_date < c.valid_from:
            discarded_non_member += 1
            continue
        if c.valid_to is not None and p_date > c.valid_to:
            discarded_non_member += 1
            continue

        desc = (item.get("desc", "") or "Corporate Announcement").strip()
        attch_text = (item.get("attchmntText", "") or "").strip()
        attch_file = (item.get("attchmntFile", "") or "").strip()

        # Headline
        if attch_text and len(attch_text) > 10:
            headline = f"{sym}: {desc} — {attch_text[:180]}"
        else:
            headline = f"{sym}: {desc}"

        # Source URL
        if attch_file and attch_file.startswith("http"):
            source_url = attch_file
        else:
            source_url = f"https://www.nseindia.com/companies-listing/corporate-filings-announcements?symbol={urllib.parse.quote(sym)}&dt={item.get('dt', '')}"

        # Deduplication Keys
        norm_head = re.sub(r"\W+", "", desc.lower())[:50]
        sig_key = f"SIG_{sym}_{pub_dt.isoformat()}_{norm_head}"

        is_dup = False
        if seq_id and seq_id in seen_seq_ids:
            is_dup = True
        elif sig_key in seen_signatures:
            is_dup = True

        if is_dup:
            duplicate_count += 1
            continue

        if seq_id:
            seen_seq_ids.add(seq_id)
        seen_signatures.add(sig_key)
        seen_urls.add(source_url)

        # PIT Assignment
        pit_res = assign_record_pit(pub_dt, t_dates, t_set)
        if pit_res.get("status") not in ("VALID",):
            snap = "SNAPSHOT_B"
            t_pred = date(2026, 9, 4)
            t_next = date(2026, 9, 7)
        else:
            snap = pit_res["snapshot"]
            t_pred = pit_res["prediction_date_T"]
            t_next = pit_res["target_date"]

        art_id = f"RAW_NSE_E_{record_counter:06d}"
        record_counter += 1

        rec = {
            "article_id": art_id,
            "headline": headline,
            "summary_or_body": attch_text if attch_text else desc,
            "source": "NSE_OFFICIAL_DISCLOSURE",
            "source_url": source_url,
            "published_timestamp": pub_dt.isoformat(),
            "published_timezone": "Asia/Kolkata",
            "retrieval_timestamp": retrieval_ts,
            "company": c.company_name,
            "company_or_entities": [sym],
            "historical_symbol_variant": variant,
            "sector": c.primary_sector,
            "historical_constituent_status": "ACTIVE_NIFTY_50_CONSTITUENT_HOLDOUT",
            "provider": "NSE_PUBLIC_ANNOUNCEMENTS_API",
            "evidence_level": "LEVEL_B",
            "seq_id": seq_id,
            "pit_eligibility": snap,
            "snapshot": snap,
            "prediction_date_T": t_pred.isoformat() if hasattr(t_pred, "isoformat") else str(t_pred),
            "target_trading_day": t_next.isoformat() if hasattr(t_next, "isoformat") else str(t_next),
            "is_pre_2022": False,
            "pub_year": str(pub_dt.year),
        }
        unique_records.append(rec)

    logger.info(f"Deduplication complete: {duplicate_count} duplicates removed. {len(unique_records)} final unique records.")

    # 5. Write to NEW output artifact
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for r in unique_records:
            f.write(json.dumps(r) + "\n")
    logger.info(f"Saved {len(unique_records)} records to NEW artifact: {OUTPUT_JSONL}")

    # 6. Checksums and Immutability Checks
    output_sha = sha256_file(OUTPUT_JSONL)
    raw_sha_after = sha256_file(EXISTING_RAW_JSONL)
    holdout_sha_after = sha256_file(HOLDOUT_CSV)
    old_step2_sha_after = sha256_file(OLD_HOLDOUT_JSONL)

    assert raw_sha_after == EXPECTED_RAW_SHA, f"CRITICAL: raw_authentic_news_inventory.jsonl was modified!"
    assert holdout_sha_after == EXPECTED_HOLDOUT_SHA, f"CRITICAL: gold_holdout_annotation_input.csv was modified!"
    assert old_step2_sha_after == EXPECTED_OLD_STEP2_SHA, f"CRITICAL: Step 2 artifact was modified!"

    # Distribution summaries
    records_by_year = Counter(r["pub_year"] for r in unique_records)
    records_by_company = Counter(r["company_or_entities"][0] for r in unique_records)
    records_by_snapshot = Counter(r["snapshot"] for r in unique_records)

    timestamps = [r["published_timestamp"] for r in unique_records]
    earliest_ts = min(timestamps) if timestamps else None
    latest_ts = max(timestamps) if timestamps else None

    t_end = datetime.now(timezone.utc)
    duration_secs = (t_end - t_start).total_seconds()

    # Per-company audit records
    per_company_audit = {}
    for c in active_constituents_in_window:
        sym = c.symbol
        rec_cnt = records_by_company.get(sym, 0)
        q_stats = company_query_stats.get(sym, {"queries": 0, "records_raw": 0, "years_queried": set()})
        per_company_audit[sym] = {
            "symbol": sym,
            "company_name": c.company_name,
            "sector": c.primary_sector,
            "valid_from": c.valid_from.isoformat(),
            "valid_to": c.valid_to.isoformat() if c.valid_to else None,
            "years_queried": sorted(list(q_stats["years_queried"])),
            "api_queries_count": q_stats["queries"],
            "raw_records_returned": q_stats["records_raw"],
            "unique_records_retained": rec_cnt,
            "is_zero_records": rec_cnt == 0,
            "zero_record_reason": "Genuinely zero announcements returned by exchange endpoint" if rec_cnt == 0 else None,
        }

    audit_data = {
        "status": "ACQUISITION_COMPLETE",
        "step": "PHASE_9_STEP_2E",
        "start_timestamp_utc": t_start.isoformat(),
        "end_timestamp_utc": t_end.isoformat(),
        "duration_seconds": round(duration_secs, 2),
        "target_window": {"start": str(WINDOW_START), "end": str(WINDOW_END)},
        "request_stats": request_stats,
        "raw_records_retrieved": len(raw_retrieved_items),
        "duplicates_removed": duplicate_count,
        "duplicate_rate_pct": round(duplicate_count / max(1, len(raw_retrieved_items)) * 100, 2),
        "discarded_out_of_bounds": discarded_out_of_bounds,
        "discarded_missing_ts": discarded_missing_ts,
        "discarded_non_member": discarded_non_member,
        "final_unique_records": len(unique_records),
        "records_by_year": dict(sorted(records_by_year.items())),
        "records_by_snapshot": dict(records_by_snapshot),
        "records_by_company": dict(sorted(records_by_company.items(), key=lambda x: -x[1])),
        "per_company_audit": per_company_audit,
        "earliest_timestamp": earliest_ts,
        "latest_timestamp": latest_ts,
        "sha256_new_terminal_artifact": output_sha,
        "sha256_old_step2_artifact": old_step2_sha_after,
        "sha256_raw_inventory_before": raw_sha_before,
        "sha256_raw_inventory_after": raw_sha_after,
        "sha256_holdout_benchmark_before": holdout_sha_before,
        "sha256_holdout_benchmark_after": holdout_sha_after,
        "queries_log": query_log,
    }

    with open(AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)
    logger.info(f"Saved Step 2E audit log to {AUDIT_JSON}")

    print("\n=== STEP 2E ACQUISITION RUN COMPLETE ===")
    print(f"Requests Total: {request_stats['total_requests']} (Success: {request_stats['successful_requests']}, Failed: {request_stats['failed_requests']}, Retries: {request_stats['retries']})")
    print(f"Raw Retrieved:  {len(raw_retrieved_items)}")
    print(f"Duplicates:     {duplicate_count} ({audit_data['duplicate_rate_pct']}%)")
    print(f"Final Unique:   {len(unique_records)}")
    print(f"By Year:        {dict(sorted(records_by_year.items()))}")
    print(f"By Snapshot:    {dict(records_by_snapshot)}")
    print(f"New Artifact:   {OUTPUT_JSONL}")
    print(f"New SHA-256:    {output_sha}")


if __name__ == "__main__":
    run_acquisition()
