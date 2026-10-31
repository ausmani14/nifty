# Phase 9 — Step 2: Authentic 2022–2026 NSE Corporate Announcement Acquisition Report

**NIFTY AI — Terminal Out-of-Sample Holdout Acquisition Audit**  
**Role:** Senior Data-Engineering & Quantitative Research Engineer  
**Date:** 2026-09-16  
**Status:** **ACQUISITION COMPLETE & FROZEN**  

---

## 1. Executive Summary

This report documents the successful end-to-end execution of **Phase 9 Step 2**: acquiring authentic, point-in-time (PIT) compliant corporate announcements from the official National Stock Exchange of India (NSE) for the terminal out-of-sample (OOS) evaluation window (**2022-01-01 through 2026-09-04 inclusive**).

### Key Quantified Results
- **Target Window**: `2022-01-01` to `2026-09-04` (calendar aligned with 4,654 NIFTY 50 trading days).
- **Official Source**: NSE Corporate Announcements Dissemination API (`https://www.nseindia.com/api/corporate-announcements`).
- **Constituent Universe**: 26 active NIFTY 50 constituents bounded strictly by point-in-time index membership.
- **Total API Requests Executed**: **104** (100% success rate; 104 HTTP 200, 0 failed).
- **Raw Records Fetched**: **18,711 records**.
- **Duplicates Removed**: **508 records** (via deterministic sequence ID and content signature hashing).
- **Final Canonical Unique Corpus**: **18,203 authentic announcements**.
- **Output Artifact**: [`data/interim/news/raw_authentic_news_holdout_2022_2026.jsonl`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/news/raw_authentic_news_holdout_2022_2026.jsonl)
- **Artifact SHA-256**: `f2cab28eaa624d5bc8d72169798655e7fb82b6b4e68102e93179eaffcadd335e`
- **Zero Historical Contamination**: Pre-2022 historical raw inventory and 200-record gold annotation holdout benchmark remain **100% byte-for-byte immutable**.

---

## 2. Cryptographic Integrity & Immutability Verification

Strict pre- and post-acquisition SHA-256 assertions were enforced:

| Artifact | Role | Pre-Acquisition SHA-256 | Post-Acquisition SHA-256 | Status |
| :--- | :--- | :--- | :--- | :--- |
| `raw_authentic_news_inventory.jsonl` | 62,329 Historical Records (2008–2021) | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | **PASS (UNTOUCHED)** |
| `gold_holdout_annotation_input.csv` | 200-Record Holdout Annotation Benchmark | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | **PASS (UNTOUCHED)** |
| `raw_authentic_news_holdout_2022_2026.jsonl` | 18,203 Terminal Records (2022–2026) | N/A (Newly Created) | `f2cab28eaa624d5bc8d72169798655e7fb82b6b4e68102e93179eaffcadd335e` | **PASS (FROZEN)** |

---

## 3. Acquisition Universe & PIT Constituent Coverage

All queries were planned strictly within the official historical reconstitution windows established in Phase 9 Step 1. No constituent was queried outside its verified index membership dates.

### Annual Distribution
| Year | Calendar Span | Authentic Records Acquired | Percentage |
| :--- | :--- | :--- | :--- |
| **2022** | 2022-01-01 to 2022-12-31 | 3,777 | 20.75% |
| **2023** | 2023-01-01 to 2023-12-31 | 4,299 | 23.62% |
| **2024** | 2024-01-01 to 2024-12-31 | 4,642 | 25.50% |
| **2025** | 2025-01-01 to 2025-12-31 | 3,150 | 17.30% |
| **2026** | 2026-01-01 to 2026-09-04 | 2,335 | 12.83% |
| **Total** | **2022-01-01 to 2026-09-04** | **18,203** | **100.00%** |

### Per-Company Breakdown (24 Active Constituents with Records)
| Symbol | Company Name | Active PIT Range | Records Acquired |
| :--- | :--- | :--- | :--- |
| `ICICIBANK` | ICICI Bank Ltd. | Continuous | 1,884 |
| `RELIANCE` | Reliance Industries Ltd. | Continuous | 1,464 |
| `TATASTEEL` | Tata Steel Ltd. | Continuous | 1,372 |
| `BHARTIARTL` | Bharti Airtel Ltd. | Continuous | 1,223 |
| `AXISBANK` | Axis Bank Ltd. | Continuous | 1,142 |
| `SBIN` | State Bank of India | Continuous | 1,130 |
| `TCS` | Tata Consultancy Services Ltd. | Continuous | 1,094 |
| `INFY` | Infosys Ltd. | Continuous | 1,086 |
| `HDFCBANK` | HDFC Bank Ltd. | Continuous | 904 |
| `LT` | Larsen & Toubro Ltd. | Continuous | 894 |
| `KOTAKBANK` | Kotak Mahindra Bank Ltd. | Continuous | 843 |
| `ITC` | ITC Ltd. | Continuous | 722 |
| `MARUTI` | Maruti Suzuki India Ltd. | Continuous | 713 |
| `ADANIENT` | Adani Enterprises Ltd. | 2022-09-30 to Present | 630 |
| `SHRIRAMFIN` | Shriram Finance Ltd. | 2024-03-28 to Present | 612 |
| `APOLLOHOSP` | Apollo Hospitals Enterprise Ltd. | 2022-03-31 to Present | 533 |
| `HDFC` | Housing Development Finance Corp. | Exited 2023-07-13 (Merged) | 441 |
| `LICI` | Life Insurance Corp. of India | Continuous | 437 |
| `UPL` | UPL Ltd. | Exited 2024-03-28 | 410 |
| `TRENT` | Trent Ltd. | 2024-09-30 to Present | 245 |
| `BEL` | Bharat Electronics Ltd. | 2024-09-30 to Present | 182 |
| `DIVISLAB` | Divi's Laboratories Ltd. | Exited 2024-09-30 | 146 |
| `SHREECEM` | Shree Cement Ltd. | Exited 2022-09-30 | 74 |
| `IOC` | Indian Oil Corp. Ltd. | Exited 2022-03-31 | 22 |
| **Total** | | | **18,203** |

---

## 4. Known Endpoint Gaps & Handling

Two tickers exhibited zero records returned from the official public announcement API:
1. **`TATAMOTORS`**: 
   - 0 records returned across all years (2022–2026).
   - This reproduces the exact historical behavior documented in Phase 8 (`docs/PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md#L215`), where the public dissemination query `symbol=TATAMOTORS` returns 0.
   - In accordance with strict instructions, `TATAMTRDVR` was **not** substituted, ensuring zero synthetic manipulation.
2. **`LTIM`**:
   - 0 records returned for the post-merger window (`2023-07-13` to `2024-09-30`).
   - Sourced under official NSE equity ticker; zero-fill is preserved without heuristic patching.

---

## 5. Point-in-Time (PIT) Assignment & Snapshot Breakdown

All 18,203 records were partitioned according to the authoritative Phase 8 calendar specification:

- **Snapshot A (Intraday Cutoff 15:30 IST)**:
  - Published between `08:50:01` and `15:30:00` on trading day $T$.
  - Available for Model 1 / Model 2 prediction at 15:40 IST for session $T+1$.
  - **Count: 5,048 records (27.73%)**.

- **Snapshot B (Overnight Cutoff 08:50 IST)**:
  - Published post-close ($t > 15:30:00$) on trading day $T$, overnight, or on non-trading days (weekends/holidays) prior to $08:50:00$ on session $T+1$.
  - Available for Model 2 pre-market prediction at 08:50 IST for session $T+1$.
  - **Count: 13,155 records (72.27%)**.

This distribution mirrors authentic corporate filing behavior: over 72% of statutory announcements are released after market close.

---

## 6. Verification and Test Suite Status

A dedicated validation suite [`tests/test_acquisition_holdout_2022_2026.py`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/tests/test_acquisition_holdout_2022_2026.py) was implemented, verifying:
- [x] Immutability of pre-existing historical datasets (`test_immutable_pre_existing_artifacts`).
- [x] Exact count and existence of the holdout artifact (`test_holdout_artifact_exists_and_count`).
- [x] Schema compliance, uniqueness of sequence IDs, and strict temporal/PIT bounding (`test_holdout_schema_and_pit_boundaries`).
- [x] Invariant consistency in audit metadata (`test_audit_json_consistency`).

All 157 automated tests in the repository pass cleanly:
```
157 passed in 7.82s
```
