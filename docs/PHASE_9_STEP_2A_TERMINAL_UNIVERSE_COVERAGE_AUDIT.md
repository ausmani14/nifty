# Phase 9 — Step 2A: Terminal Acquisition Universe Coverage Audit Report

**NIFTY AI — Next-Trading-Day Return Forecasting Engine**  
**Role:** Senior Data Engineer & Quantitative Verification Auditor  
**Date:** 2026-09-16  
**Status:** **READ-ONLY AUDIT COMPLETE**  
**Target Window**: `2022-01-01` through `2026-09-04`  

---

## 1. Executive Summary & Audit Scope

Following the execution of Phase 9 Step 2, which yielded 18,203 authentic disclosures across 104 constituent-year queries and 24 companies, this audit evaluates whether that acquisition represented the **complete Point-in-Time (PIT) NIFTY 50 universe** for the terminal out-of-sample window (`2022-01-01` to `2026-09-04`).

### Core Audit Discoveries:
1. **The Step 2 Acquisition Queried Only 26 Companies**:
   The Step 2 script queried strictly the active constituents codified in `CANONICAL_CONSTITUENTS` (`src/nifty_ai/data/news/constituents.py`). That registry codified only 30 constituents total (15 continuous heavyweights, 4 pre-2022 exits, 6 2022–2024 exits, and 5 entrants). Across 2022–2026, exactly **26 constituents** were active in `CANONICAL_CONSTITUENTS`.
2. **The True Historical NIFTY 50 Universe Contained at Least 56 Documented Unique Companies**:
   The NIFTY 50 is a 50-stock index. Across 2022–2026, based on authoritative repository evidence (`docs/PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md` and `docs/PHASE_8_COMPLETE_NIFTY_50_COVERAGE_REPORT.md`), there were **49 documented active baseline constituents** on `2022-01-01` plus **6 documented reconstitution entrants** (`APOLLOHOSP`, `ADANIENT`, `LTIM`, `SHRIRAMFIN`, `BEL`, `TRENT`) and `LICI`, totaling **56 unique documented companies** (and 57 in the true market index when accounting for the 50th baseline constituent).
3. **30 Undisputed Historical NIFTY 50 Companies Were Completely Omitted From Acquisition**:
   Major index heavyweights—including `ASIANPAINT`, `BAJFINANCE`, `BAJAJFINSV`, `BPCL`, `BRITANNIA`, `CIPLA`, `COALINDIA`, `DRREDDY`, `EICHERMOT`, `GRASIM`, `HCLTECH`, `HEROMOTOCO`, `HINDALCO`, `HINDUNILVR`, `INDUSINDBK`, `JSWSTEEL`, `M&M`, `NESTLEIND`, `NTPC`, `ONGC`, `POWERGRID`, `SBILIFE`, `SUNPHARMA`, `TATACONSUM`, `TECHM`, `TITAN`, `ULTRACEMCO`, `WIPRO`, `ADANIPORTS`, and `BAJAJ-AUTO`—were **never queried**.
4. **Massive Shortfall in Constituent-Year Query Matrix**:
   - Expected constituent-year queries across documented universe: **254 queries**.
   - Actual queries executed: **104 queries (40.94% coverage)**.
   - Missing queries: **150 constituent-year queries (59.06% unacquired)**.
5. **Acquired Artifact Integrity**:
   The existing 18,203-record terminal artifact (`raw_authentic_news_holdout_2022_2026.jsonl`) is internally consistent, 100% authentic, cleanly deduplicated, and strictly quarantined. However, **it covers only ~43% of the active corporate constituents**.

---

## 2. AUDIT 1 — Reconstruct the Required PIT Universe (2022–2026)

Using strictly the repository's authoritative documentation (`docs/PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md`, `docs/PHASE_8_COMPLETE_NIFTY_50_COVERAGE_REPORT.md`, `docs/NEWS_NLP_INTELLIGENCE.md`, and official NSE rebalancing circulars recorded therein), the table below details the complete documented PIT universe for 2022-01-01 through 2026-09-04.

### Documented NIFTY 50 Constituents Active in 2022–2026 (56 Unique Companies):

| Symbol | Company Name | Sector | Active Tenure in 2022–2026 Window | Required Query Years | Step 2 Status |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **ADANIENT** | Adani Enterprises Ltd. | `NIFTY_METALS` | 2022-09-30 to 2026-09-04 | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **ADANIPORTS** | Adani Ports & SEZ Ltd. | `NIFTY_INFRA` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **APOLLOHOSP** | Apollo Hospitals Enterprise | `NIFTY_PHARMA` | 2022-03-31 to 2026-09-04 | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **ASIANPAINT** | Asian Paints Ltd. | `NIFTY_CONSUMPTION` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **AXISBANK** | Axis Bank Ltd. | `NIFTY_BANK` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **BAJAJ-AUTO** | Bajaj Auto Ltd. | `NIFTY_AUTO` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **BAJAJFINSV** | Bajaj Finserv Ltd. | `NIFTY_FIN_SERVICE` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **BAJFINANCE** | Bajaj Finance Ltd. | `NIFTY_FIN_SERVICE` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **BEL** | Bharat Electronics Ltd. | `NIFTY_INFRA` | 2024-09-30 to 2026-09-04 | 2024, 2025, 2026 | QUERIED |
| **BHARTIARTL** | Bharti Airtel Ltd. | `NIFTY_TELECOM` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **BPCL** | Bharat Petroleum Corp. Ltd. | `NIFTY_OIL_GAS` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **BRITANNIA** | Britannia Industries Ltd. | `NIFTY_FMCG` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **CIPLA** | Cipla Ltd. | `NIFTY_PHARMA` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **COALINDIA** | Coal India Ltd. | `NIFTY_METALS` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **DIVISLAB** | Divi's Laboratories Ltd. | `NIFTY_PHARMA` | 2022-01-01 to 2024-09-30 (Exited) | 2022, 2023, 2024 | QUERIED |
| **DRREDDY** | Dr. Reddy's Laboratories | `NIFTY_PHARMA` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **EICHERMOT** | Eicher Motors Ltd. | `NIFTY_AUTO` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **GRASIM** | Grasim Industries Ltd. | `NIFTY_METALS` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **HCLTECH** | HCL Technologies Ltd. | `NIFTY_IT` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **HDFC** | Housing Dev. Finance Corp. | `NIFTY_FIN_SERVICE` | 2022-01-01 to 2023-07-13 (Merged) | 2022, 2023 | QUERIED |
| **HDFCBANK** | HDFC Bank Ltd. | `NIFTY_BANK` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **HEROMOTOCO** | Hero MotoCorp Ltd. | `NIFTY_AUTO` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **HINDALCO** | Hindalco Industries Ltd. | `NIFTY_METALS` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **HINDUNILVR** | Hindustan Unilever Ltd. | `NIFTY_FMCG` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **ICICIBANK** | ICICI Bank Ltd. | `NIFTY_BANK` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **INDUSINDBK** | IndusInd Bank Ltd. | `NIFTY_BANK` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **INFY** | Infosys Ltd. | `NIFTY_IT` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **IOC** | Indian Oil Corp. Ltd. | `NIFTY_OIL_GAS` | 2022-01-01 to 2022-03-31 (Exited) | 2022 | QUERIED |
| **ITC** | ITC Ltd. | `NIFTY_FMCG` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **JSWSTEEL** | JSW Steel Ltd. | `NIFTY_METALS` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **KOTAKBANK** | Kotak Mahindra Bank Ltd. | `NIFTY_BANK` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **LICI** | Life Insurance Corp. of India | `NIFTY_FIN_SERVICE` | 2024-03-28 to 2026-09-04 | 2024, 2025, 2026 | QUERIED |
| **LT** | Larsen & Toubro Ltd. | `NIFTY_INFRA` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **LTIM** | LTIMindtree Ltd. | `NIFTY_IT` | 2023-07-13 to 2024-09-30 (Exited) | 2023, 2024 | QUERIED |
| **M&M** | Mahindra & Mahindra Ltd. | `NIFTY_AUTO` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **MARUTI** | Maruti Suzuki India Ltd. | `NIFTY_AUTO` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **NESTLEIND** | Nestle India Ltd. | `NIFTY_FMCG` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **NTPC** | NTPC Ltd. | `NIFTY_INFRA` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **ONGC** | Oil & Natural Gas Corp. | `NIFTY_OIL_GAS` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **POWERGRID** | Power Grid Corp. of India | `NIFTY_INFRA` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **RELIANCE** | Reliance Industries Ltd. | `NIFTY_OIL_GAS` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **SBILIFE** | SBI Life Insurance Co. Ltd. | `NIFTY_FIN_SERVICE` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **SBIN** | State Bank of India | `NIFTY_BANK` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **SHREECEM** | Shree Cement Ltd. | `NIFTY_INFRA` | 2022-01-01 to 2022-09-30 (Exited) | 2022 | QUERIED |
| **SHRIRAMFIN** | Shriram Finance Ltd. | `NIFTY_FIN_SERVICE` | 2024-03-28 to 2026-09-04 | 2024, 2025, 2026 | QUERIED |
| **SUNPHARMA** | Sun Pharmaceutical Industries | `NIFTY_PHARMA` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **TATACONSUM** | Tata Consumer Products Ltd. | `NIFTY_FMCG` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **TATAMOTORS** | Tata Motors Ltd. | `NIFTY_AUTO` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED (GAP) |
| **TATASTEEL** | Tata Steel Ltd. | `NIFTY_METALS` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **TCS** | Tata Consultancy Services | `NIFTY_IT` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | QUERIED |
| **TECHM** | Tech Mahindra Ltd. | `NIFTY_IT` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **TITAN** | Titan Company Ltd. | `NIFTY_CONSUMPTION` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **TRENT** | Trent Ltd. | `NIFTY_CONSUMPTION`| 2024-09-30 to 2026-09-04 | 2024, 2025, 2026 | QUERIED |
| **ULTRACEMCO** | UltraTech Cement Ltd. | `NIFTY_INFRA` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |
| **UPL** | UPL Ltd. | `NIFTY_CHEM` | 2022-01-01 to 2024-03-28 (Exited) | 2022, 2023, 2024 | QUERIED |
| **WIPRO** | Wipro Ltd. | `NIFTY_IT` | Continuous (2022-01-01 to 2026-09-04) | 2022, 2023, 2024, 2025, 2026 | **NOT QUERIED** |

*Note on Repository Evidence*: The repository documentation accounts for 49 baseline constituents on 2022-01-01 (19 in `CANONICAL_CONSTITUENTS` + 29 from the Phase 8 77-table + 1 `HEROMOTOCO`). Exactly 1 baseline constituent out of 50 (historically HDFC Life Insurance Company / `HDFCLIFE`) is omitted from repository circular documentation.

---

## 3. AUDIT 2 — Expected vs. Actually Queried Constituent-Year Matrix

### Aggregate Comparison
| Metric | Count | Percentage |
| :--- | :---: | :---: |
| **Expected Constituent-Year Queries (Documented Universe)** | **254** | **100.00%** |
| **Actual Constituent-Year Queries Executed** | **104** | **40.94%** |
| - Queries with Records (>0) | 97 | 38.19% |
| - Zero-Result Queries (Documented Gap / Temporary) | 7 | 2.76% |
| - HTTP / Network Failures | 0 | 0.00% |
| **Missing Constituent-Year Queries (Completely Omitted)** | **150** | **59.06%** |

### Table of Missing Constituent-Year Queries (30 Companies $\times$ 5 Years = 150 Missing Queries):
Every single query listed below was required by historical NIFTY 50 index membership but was **never executed** in Step 2:

| Symbol | Company Name | 2022 | 2023 | 2024 | 2025 | 2026 (thru Sep 04) | Total Missing |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `ADANIPORTS` | Adani Ports and Special Economic Zone Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `ASIANPAINT` | Asian Paints Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `BAJAJ-AUTO` | Bajaj Auto Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `BAJAJFINSV` | Bajaj Finserv Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `BAJFINANCE` | Bajaj Finance Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `BPCL` | Bharat Petroleum Corporation Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `BRITANNIA` | Britannia Industries Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `CIPLA` | Cipla Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `COALINDIA` | Coal India Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `DRREDDY` | Dr. Reddy's Laboratories Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `EICHERMOT` | Eicher Motors Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `GRASIM` | Grasim Industries Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `HCLTECH` | HCL Technologies Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `HEROMOTOCO` | Hero MotoCorp Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `HINDALCO` | Hindalco Industries Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `HINDUNILVR` | Hindustan Unilever Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `INDUSINDBK` | IndusInd Bank Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `JSWSTEEL` | JSW Steel Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `M&M` | Mahindra & Mahindra Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `NESTLEIND` | Nestle India Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `NTPC` | NTPC Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `ONGC` | Oil & Natural Gas Corporation Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `POWERGRID` | Power Grid Corporation of India Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `SBILIFE` | SBI Life Insurance Company Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `SUNPHARMA` | Sun Pharmaceutical Industries Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `TATACONSUM` | Tata Consumer Products Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `TECHM` | Tech Mahindra Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `TITAN` | Titan Company Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `ULTRACEMCO` | UltraTech Cement Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| `WIPRO` | Wipro Ltd | MISSING | MISSING | MISSING | MISSING | MISSING | 5 |
| **TOTAL** | **30 Unique Companies** | **30** | **30** | **30** | **30** | **30** | **150** |

---

## 4. AUDIT 3 — Company Coverage Reconciliation

Comparison across the three cohorts:
- **A. Complete Expected PIT Universe**: **56 unique companies** documented in repository evidence.
- **B. Companies Actually Queried in Step 2**: **26 unique companies**.
- **C. Companies Present with $\ge 1$ Announcement in Terminal Artifact**: **24 unique companies**.

### Discrepancy Analysis:
1. **Queried but 0 Announcements Acquired (2 Companies)**:
   - `TATAMOTORS`: Queried across 5 years (2022–2026); returned 0 records due to confirmed official endpoint gap.
   - `LTIM`: Queried across 2 years (2023, 2024); returned 0 records on official equity endpoint.
2. **Never Queried (30 Companies)**:
   - 30 companies were omitted because `src/nifty_ai/data/news/constituents.py` only contained 30 total records, of which 4 were pre-2022 exits and 26 were active in 2022–2026.
   - These 30 companies represent **53.57% of the expected NIFTY 50 corporate constituents**.

---

## 5. AUDIT 4 — Year-by-Year Coverage Analysis

| Year | Expected Active Constituents | Actual Queried Constituents | Successful Queries (>0) | Zero-Result Queries | Failed Queries | Final Unique Announcements |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2022** | 51 | 21 | 20 | 1 (`TATAMOTORS`) | 0 | 3,777 |
| **2023** | 50 | 20 | 18 | 2 (`TATAMOTORS`, `LTIM`) | 0 | 4,299 |
| **2024** | 53 | 23 | 21 | 2 (`TATAMOTORS`, `LTIM`) | 0 | 4,642 |
| **2025** | 50 | 20 | 19 | 1 (`TATAMOTORS`) | 0 | 3,150 |
| **2026** (thru 09-04) | 50 | 20 | 19 | 1 (`TATAMOTORS`) | 0 | 2,335 |
| **Total** | **254** | **104** | **97** | **7** | **0** | **18,203** |

*Key Takeaway*: In every calendar year, fewer than half of the active NIFTY 50 constituents were queried.

---

## 6. AUDIT 5 — Special Cases & Reconstitution Invariants

1. **`TATAMOTORS`**:
   - Accurately isolated as a confirmed official dissemination endpoint gap.
   - All 5 queries (2022–2026) returned HTTP 200 with `[]` (0 records).
   - Ordinary equity gap preserved without synthetic or DVR substitution.
2. **`LTIM`**:
   - Queried strictly for its tenure (`2023-07-13` to `2024-09-30`). Both queries returned HTTP 200 with 0 records. Preserved honestly as zero disclosures without heuristic distortion.
3. **`HDFC` / `HDFCBANK` Merger**:
   - `HDFC` was queried strictly for its pre-merger PIT window (`2022-01-01` to `2023-07-13`). Acquired 441 authentic announcements before exiting.
   - `HDFCBANK` was queried continuously; post-merger disclosures reside under `HDFCBANK`.
4. **`IOC` Exit**:
   - Queried strictly for Q1 2022 (`2022-01-01` to `2022-03-31`). Acquired 22 records before exiting on March 31, 2022.
5. **`SHREECEM` Exit**:
   - Queried strictly for 9 months (`2022-01-01` to `2022-09-30`). Acquired 74 records before exiting on September 30, 2022.
6. **`UPL` Exit**:
   - Queried strictly through exit date (`2022-01-01` to `2024-03-28`). Acquired 410 records before exiting.
7. **`DIVISLAB` Exit**:
   - Queried strictly through semi-annual exit (`2022-01-01` to `2024-09-30`). Acquired 146 records before exiting.
8. **`APOLLOHOSP` Entry**:
   - Queried starting from inclusion date (`2022-03-31` to `2026-09-04`). Acquired 533 records with zero pre-entry leakage.
9. **`ADANIENT` Entry**:
   - Queried starting from inclusion date (`2022-09-30` to `2026-09-04`). Acquired 630 records with zero pre-entry leakage.
10. **`SHRIRAMFIN` Entry**:
    - Queried starting from inclusion date (`2024-03-28` to `2026-09-04`). Acquired 612 records with zero pre-entry leakage.
11. **`BEL` Entry**:
    - Queried starting from inclusion date (`2024-09-30` to `2026-09-04`). Acquired 182 records with zero pre-entry leakage.
12. **`TRENT` Entry**:
    - Queried starting from inclusion date (`2024-09-30` to `2026-09-04`). Acquired 245 records with zero pre-entry leakage.

*Defect Identified*: While the 11 special reconstitution intervals implemented in Step 1 were executed with 100% mathematical precision, **the 30 ongoing baseline constituents were completely left out of `CANONICAL_CONSTITUENTS`**.

---

## 7. AUDIT 6 — Registry Completeness Verification

- **Code Inspection**: [`src/nifty_ai/data/news/constituents.py`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/src/nifty_ai/data/news/constituents.py) defines `CANONICAL_CONSTITUENTS` with **exactly 30 records**.
- **Historical Comparison**:
  - `YESBANK`, `INFRATEL`, `VEDL`, `ZEEL` exited between 2020 and 2021 (4 records).
  - The remaining 26 records represent the entire active pool available to the acquisition script.
  - The registry was built as a lightweight prototype rather than an exhaustive index catalog.
- **Verdict on Registry**:
  The current registry in `constituents.py` is **INCOMPLETE**. It contains only 26 of the 56 documented unique companies that formed the NIFTY 50 during 2022–2026.

---

## 8. AUDIT 7 — Acquired Data Forensic Integrity

A comprehensive read-only scan of [`data/interim/news/raw_authentic_news_holdout_2022_2026.jsonl`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/news/raw_authentic_news_holdout_2022_2026.jsonl) confirmed:
- **Total Records Scanned**: 18,203
- **Out-of-Window Records**: **0** (Earliest: `2022-01-01T14:42:19+05:30`; Latest: `2026-09-04T20:16:35+05:30`)
- **Invalid Provenance Records**: **0** (100% regulatory `NSE_OFFICIAL_DISCLOSURE`)
- **Invalid / Ambiguous Timestamps**: **0** (100% verified `Asia/Kolkata` second-level precision)
- **Duplicate Sequence IDs**: **0**
- **Duplicate Content Signatures**: **0**
- **Point-in-Time Partition**:
  - Snapshot A (Intraday $\le 15:30$ IST): **5,048 (27.73%)**
  - Snapshot B (Overnight $> 15:30$ IST): **13,155 (72.27%)**
- **Cryptographic Quarantine & Immutability**:
  - `raw_authentic_news_inventory.jsonl`: `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` (**MATCH / INTACT**)
  - `gold_holdout_annotation_input.csv`: `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` (**MATCH / INTACT**)
  - `raw_authentic_news_holdout_2022_2026.jsonl`: `f2cab28eaa624d5bc8d72169798655e7fb82b6b4e68102e93179eaffcadd335e` (**INTACT**)

The data acquired is authentic and uncorrupted, but **it represents an incomplete universe**.

---

## 9. AUDIT 8 — Record Volume vs. Universe Coverage Fallacy

Acquiring 18,203 announcements creates a false impression of completeness. In quantitative financial machine learning:
$$\text{Universe Coverage} = \frac{\text{Queried Member-Years}}{\text{Required Member-Years}} = \frac{104}{254} = 40.94\%$$
Predicting the NIFTY 50 using disclosures from only 24–26 companies introduces severe **omitted variable bias**. Large-cap market-moving moves driven by Reliance, TCS, or ICICI Bank are captured, but moves driven by Hindustan Unilever, Larsen & Toubro's omitted peers, Asian Paints, Bajaj Finance, or the entire FMCG/pharma cohort would appear as "zero news days" simply because those companies were never queried.

---

## 10. Summary Audit Metrics & Mandatory Classification

```yaml
EXPECTED UNIQUE COMPANIES: 56 (documented in repository evidence; 57 in physical market index)
EXPECTED CONSTITUENT-YEAR QUERIES: 254 (documented universe)
ACTUAL CONSTITUENT-YEAR QUERIES: 104
MISSING QUERIES: 150
ZERO-RESULT QUERIES: 7 (TATAMOTORS: 5 years; LTIM: 2 years)
FAILED QUERIES: 0
COMPANIES PRESENT: 24
COMPANIES MISSING: 32 (2 queried with zero records + 30 unqueried companies)
```

---

## FINAL AUDIT VERDICT

### **B) ACQUISITION UNIVERSE INCOMPLETE — ADDITIONAL PIT QUERIES REQUIRED**
*(Secondary Condition: **C) REGISTRY EVIDENCE INSUFFICIENT** regarding the 50th baseline constituent on 2022-01-01, but the 30 omitted constituents identified above are fully documented in repository circular evidence).*
