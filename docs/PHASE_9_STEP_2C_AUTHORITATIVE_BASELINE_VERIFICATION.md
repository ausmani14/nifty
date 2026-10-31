# Phase 9 — Step 2C: Authoritative NIFTY 50 Baseline Constituent Verification Report

**NIFTY AI — Next-Trading-Day Return Forecasting Engine**  
**Role:** Senior ML & Quantitative Verification Auditor  
**Date:** 2026-09-16  
**Status:** **OFFICIAL EVIDENCE RETRIEVAL COMPLETE (READ-ONLY)**  
**Target Date:** `2022-01-01` (Baseline Day of Terminal Out-of-Sample Window)  

---

## 1. Executive Summary & Audit Mandate

In Phase 9 Step 2B, an internal repository audit confirmed that existing repository documentation established only **49 active baseline constituents** on `2022-01-01`, with an apparent gap of 1 missing constituent stemming from a documented accounting imbalance around the March 31, 2021 reconstitution (where the repository recorded 2 exits: `GAIL`, `ZEEL`, but only 1 entry: `TATACONSUM`). Furthermore, an unverified entry for `LICI` from March 28, 2024 was flagged in `src/nifty_ai/data/news/constituents.py`.

Under Step 2C, official historical reconstitution documentation from **NSE India** and **NSE Indices Limited** (`niftyindices.com`) was retrieved to authoritatively resolve:
1. The exact NIFTY 50 reconstitution sequence during 2020–2021.
2. The true identity of the missing 50th baseline constituent on `2022-01-01`.
3. The true index membership status of `LICI` on March 28, 2024.
4. Any underlying discrepancies between official NSE records and the repository's constituent registry.

### Key Forensic Discoveries:
1. **The 50th Baseline Constituent is `HDFCLIFE` (HDFC Life Insurance Company Ltd.)**:
   Effective **July 31, 2020**, `HDFCLIFE` was included in the NIFTY 50 index to replace `VEDL` (Vedanta Ltd.) following Vedanta's proposed voluntary delisting.
2. **There was NO second entrant on March 31, 2021**:
   The official semi-annual review effective March 31, 2021 had exactly **1 replacement**: `TATACONSUM` replaced `GAIL`.
3. **`ZEEL` did NOT exit on March 31, 2021**:
   The repository table (`PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md` L92) misdated Zee Entertainment's exit as `2021-03-31`. Official NSE records prove `ZEEL` and `INFRATEL` exited together six months earlier on **September 25, 2020**, replaced by `DIVISLAB` and `SBILIFE`.
4. **`LICI` was NEVER a NIFTY 50 Constituent**:
   Official NSE Indices Circular Ref: `0214/2024` confirms that on March 28, 2024, the sole NIFTY 50 change was `UPL` out, `SHRIRAMFIN` in. `LICI` was added to **NIFTY Next 50**, not NIFTY 50.

---

## 2. Granular Investigation of 2020–2021 Reconstitutions

A chronological audit of official NSE Indices announcements completely resolves the ledger imbalance that produced the 49-constituent anomaly:

``mermaid
timeline
    title Official NIFTY 50 Reconstitution Chain (2020–2021)
    section 2020-03-27 : YESBANK out : SHREECEM in (Count = 50)
    section 2020-07-31 : VEDL out (Delisting) : HDFCLIFE in (Count = 50)
    section 2020-09-25 : INFRATEL & ZEEL out : DIVISLAB & SBILIFE in (Count = 50)
    section 2021-03-31 : GAIL out : TATACONSUM in (Count = 50)
    section 2022-01-01 : Baseline OOS Date : Exactly 50 Active Constituents
``

### 1. July 31, 2020 Reconstitution (Interim Replacement)
- **Official Action**: NSE Indices Press Release dated **July 03, 2020**.
- **Effective Date**: **July 31, 2020** (cut-off close of July 30, 2020).
- **Exclusion**: `VEDL` (Vedanta Ltd.) — excluded due to proposed voluntary delisting.
- **Inclusion**: `HDFCLIFE` (HDFC Life Insurance Company Ltd.).
- **Net Index Count**: Remained invariant at 50 (Delta = 0).
- *Repository Error*: `PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md` misrecorded `VEDL`'s exit as `2020-09-25` and completely omitted `HDFCLIFE`.

### 2. September 25, 2020 Reconstitution (Semi-Annual Review)
- **Official Action**: NSE Indices Press Release dated **August 20, 2020**.
- **Effective Date**: **September 25, 2020** (cut-off close of September 24, 2020).
- **Exclusions**:
  1. `INFRATEL` (Bharti Infratel Ltd.)
  2. `ZEEL` (Zee Entertainment Enterprises Ltd.)
- **Inclusions**:
  1. `DIVISLAB` (Divi's Laboratories Ltd.)
  2. `SBILIFE` (SBI Life Insurance Company Ltd.)
- **Net Index Count**: Remained invariant at 50 (Delta = 0, 2 out, 2 in).
- *Repository Error*: `PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md` misrecorded `ZEEL` as exiting on `2021-03-31` instead of `2020-09-25`.

### 3. March 31, 2021 Reconstitution (Semi-Annual Review)
- **Official Action**: NSE Indices Press Release dated **February 23, 2021**.
- **Effective Date**: **March 31, 2021** (cut-off close of March 30, 2021).
- **Exclusion**: `GAIL` (GAIL (India) Ltd.).
- **Inclusion**: `TATACONSUM` (Tata Consumer Products Ltd.).
- **Net Index Count**: Remained invariant at 50 (Delta = 0, 1 out, 1 in).
- *Repository Error*: Because the repository incorrectly placed `ZEEL`'s exit on `2021-03-31`, it showed 2 exits (`GAIL`, `ZEEL`) and only 1 entry (`TATACONSUM`), falsely implying a missing entrant (Delta = -1). In reality, the review had only 1 replacement.

---

## 3. Authoritative Official NSE / NSE Indices Citations

The following official circulars and press releases from NSE / NSE Indices Limited provide the evidentiary foundation:

| Rebalancing Date | Official Document Identifier | Issuing Authority | Release Date | Official Summary & Verbatim Actions |
| :--- | :--- | :--- | :--- | :--- |
| **2020-07-31** | Press Release: *Replacement of Vedanta in NIFTY 50* | NSE Indices Limited | 2020-07-03 | Exclusion of Vedanta Ltd. (`VEDL`) and inclusion of HDFC Life Insurance Company Ltd. (`HDFCLIFE`) in NIFTY 50, NIFTY 100, NIFTY 500, and NIFTY 200 effective July 31, 2020. |
| **2020-09-25** | Press Release: *Periodic Review of Indices - September 2020* | NSE Indices Limited | 2020-08-20 | NIFTY 50 Inclusions: `DIVISLAB`, `SBILIFE`. NIFTY 50 Exclusions: `INFRATEL`, `ZEEL`. Effective September 25, 2020. |
| **2021-03-31** | Press Release: *Periodic Review of Indices - March 2021* | NSE Indices Limited | 2021-02-23 | NIFTY 50 Inclusion: `TATACONSUM`. NIFTY 50 Exclusion: `GAIL`. Effective March 31, 2021. GAIL moved to NIFTY Next 50. |
| **2024-03-28** | Circular Ref: `0214/2024` (*Periodic Review of Indices*) | NSE Indices Limited | 2024-02-28 | NIFTY 50 Inclusion: `SHRIRAMFIN`. NIFTY 50 Exclusion: `UPL`. Effective March 28, 2024. `LICI` was included in NIFTY Next 50, NIFTY 100, and NIFTY 500, but **NOT** in NIFTY 50. |

---

## 4. Complete List of 50 NIFTY 50 Constituents Active on 2022-01-01

With `HDFCLIFE` authoritatively verified as the 50th constituent and the 2020–2021 timeline reconciled, the exact, complete, and unassailable cohort of all 50 NIFTY 50 constituents active on `2022-01-01` is established:

| # | Symbol | Company Name | Sector | Active Tenure Covering 2022-01-01 | Documented Provenance |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `ADANIPORTS` | Adani Ports & Special Economic Zone Ltd | `NIFTY_INFRA` | 2015-09-28 to Active | Phase 8 Audit Table (L44) |
| 2 | `ASIANPAINT` | Asian Paints Ltd | `NIFTY_CONSUMPTION`| 2012-04-27 to Active | Phase 8 Audit Table (L45) |
| 3 | `AXISBANK` | Axis Bank Ltd | `NIFTY_BANK` | 2009-03-27 to Active | Phase 8 Audit Table (L46) |
| 4 | `BAJAJ-AUTO` | Bajaj Auto Ltd | `NIFTY_AUTO` | 2010-10-01 to Active | Phase 8 Audit Table (L47) |
| 5 | `BAJAJFINSV` | Bajaj Finserv Ltd | `NIFTY_FIN_SERVICE`| 2018-09-28 to Active | Phase 8 Audit Table (L48) |
| 6 | `BAJFINANCE` | Bajaj Finance Ltd | `NIFTY_FIN_SERVICE`| 2017-09-29 to Active | Phase 8 Audit Table (L49) |
| 7 | `BHARTIARTL` | Bharti Airtel Ltd | `NIFTY_TELECOM` | 2004-04-01 to Active | Phase 8 Audit Table (L50) |
| 8 | `BPCL` | Bharat Petroleum Corporation Ltd | `NIFTY_OIL_GAS` | 2000-01-01 to Active | Phase 8 Audit Table (L52) |
| 9 | `BRITANNIA` | Britannia Industries Ltd | `NIFTY_FMCG` | 2019-04-01 to Active | Phase 8 Audit Table (L53) |
| 10 | `CIPLA` | Cipla Ltd | `NIFTY_PHARMA` | 2000-01-01 to Active | Phase 8 Audit Table (L54) |
| 11 | `COALINDIA` | Coal India Ltd | `NIFTY_METALS` | 2010-11-04 to Active | Phase 8 Audit Table (L55) |
| 12 | `DIVISLAB` | Divi's Laboratories Ltd | `NIFTY_PHARMA` | 2020-09-25 to 2024-09-30 | NSE PR 2020-08-20, Circular 0870/2024 |
| 13 | `DRREDDY` | Dr. Reddy's Laboratories Ltd | `NIFTY_PHARMA` | 2010-10-01 to Active | Phase 8 Audit Table (L57) |
| 14 | `EICHERMOT` | Eicher Motors Ltd | `NIFTY_AUTO` | 2016-04-01 to Active | Phase 8 Audit Table (L58) |
| 15 | `GRASIM` | Grasim Industries Ltd | `NIFTY_METALS` | 2000-01-01 to Active | Phase 8 Audit Table (L60) |
| 16 | `HCLTECH` | HCL Technologies Ltd | `NIFTY_IT` | 2000-01-01 to Active | Phase 8 Audit Table (L61) |
| 17 | `HDFC` | Housing Development Finance Corp. Ltd | `NIFTY_FIN_SERVICE`| 2000-01-01 to 2023-07-13 | Circular 0731/2023 |
| 18 | `HDFCBANK` | HDFC Bank Ltd | `NIFTY_BANK` | 2000-01-01 to Active | Phase 8 Audit Table (L62) |
| 19 | `HDFCLIFE` | HDFC Life Insurance Company Ltd | `NIFTY_FIN_SERVICE`| **2020-07-31 to Active** | **NSE PR 2020-07-03 (Verified 50th)** |
| 20 | `HEROMOTOCO`| Hero MotoCorp Ltd | `NIFTY_AUTO` | 2000-01-01 to Active | Phase 8 Coverage Table (L61) |
| 21 | `HINDALCO` | Hindalco Industries Ltd | `NIFTY_METALS` | 2000-01-01 to Active | Phase 8 Audit Table (L63) |
| 22 | `HINDUNILVR` | Hindustan Unilever Ltd | `NIFTY_FMCG` | 2000-01-01 to Active | Phase 8 Audit Table (L64) |
| 23 | `ICICIBANK` | ICICI Bank Ltd | `NIFTY_BANK` | 2002-01-01 to Active | Phase 8 Audit Table (L65) |
| 24 | `INDUSINDBK` | IndusInd Bank Ltd | `NIFTY_BANK | 2013-04-01 to Active | Phase 8 Audit Table (L104) |
| 25 | `INFY` | Infosys Ltd | `NIFTY_IT` | 2000-01-01 to Active | Phase 8 Audit Table (L67) |
| 26 | `IOC` | Indian Oil Corporation Ltd | `NIFTY_OIL_GAS` | 2000-01-01 to 2022-03-31 | Circular 0184/2022 |
| 27 | `ITC` | ITC Ltd | `NIFTY_FMCG` | 2000-01-01 to Active | Phase 8 Audit Table (L69) |
| 28 | `JSWSTEEL` | JSW Steel Ltd | `NIFTY_METALS` | 2018-09-28 to Active | Phase 8 Audit Table (L70) |
| 29 | `KOTAKBANK` | Kotak Mahindra Bank Ltd | `NIFTY_BANK` | 2010-04-01 to Active | Phase 8 Audit Table (L71) |
| 30 | `LT` | Larsen & Toubro Ltd | `NIFTY_INFRA` | 2000-01-01 to Active | Phase 8 Audit Table (L72) |
| 31 | `M&M` | Mahindra & Mahindra Ltd | `NIFTY_AUTO` | 2000-01-01 to Active | Phase 8 Audit Table (L73) |
| 32 | `MARUTI` | Maruti Suzuki India Ltd | `NIFTY_AUTO` | 2004-04-01 to Active | Phase 8 Audit Table (L74) |
| 33 | `NESTLEIND` | Nestle India Ltd | `NIFTY_FMCG` | 2019-09-27 to Active | Phase 8 Audit Table (L107) |
| 34 | `NTPC` | NTPC Ltd | `NIFTY_INFRA` | 2004-10-01 to Active | Phase 8 Audit Table (L75) |
| 35 | `ONGC` | Oil & Natural Gas Corporation Ltd | `NIFTY_OIL_GAS` | 2000-01-01 to Active | Phase 8 Audit Table (L76) |
| 36 | `POWERGRID` | Power Grid Corporation of India Ltd | `NIFTY_INFRA` | 2008-03-01 to Active | Phase 8 Audit Table (L77) |
| 37 | `RELIANCE` | Reliance Industries Ltd | `NIFTY_OIL_GAS` | 2000-01-01 to Active | Phase 8 Audit Table (L78) |
| 38 | `SBILIFE` | SBI Life Insurance Company Ltd | `NIFTY_FIN_SERVICE`| 2020-09-25 to Active | NSE PR 2020-08-20 |
| 39 | `SBIN` | State Bank of India | `NIFTY_BANK` | 2000-01-01 to Active | Phase 8 Audit Table (L79) |
| 40 | `SHREECEM` | Shree Cement Ltd | `NIFTY_INFRA` | 2020-03-27 to 2022-09-30 | Circular 0644/2022 |
| 41 | `SUNPHARMA` | Sun Pharmaceutical Industries Ltd | `NIFTY_PHARMA` | 2000-01-01 to Active | Phase 8 Audit Table (L81) |
| 42 | `TATACONSUM`| Tata Consumer Products Ltd | `NIFTY_FMCG` | 2021-03-31 to Active | NSE PR 2021-02-23 |
| 43 | `TATAMOTORS`| Tata Motors Ltd | `NIFTY_AUTO` | 2000-01-01 to Active | Phase 8 Audit Table (L82) |
| 44 | `TATASTEEL` | Tata Steel Ltd | `NIFTY_METALS` | 2000-01-01 to Active | Phase 8 Audit Table (L83) |
| 45 | `TCS` | Tata Consultancy Services Ltd | `NIFTY_IT` | 2004-08-25 to Active | Phase 8 Audit Table (L84) |
| 46 | `TECHM | Tech Mahindra Ltd | `NIFTY_IT` | 2014-03-28 to Active | Phase 8 Audit Table (L85) |
| 47 | `TITAN` | Titan Company Ltd | `NIFTY_CONSUMPTION`| 2018-04-02 to Active | Phase 8 Audit Table (L86) |
| 48 | `ULTRACEMCO`| UltraTech Cement Ltd | `NIFTY_INFRA` | 2012-09-28 to Active | Phase 8 Audit Table (L87) |
| 49 | `UPL` | UPL Ltd | `NIFTY_CHEM` | 2019-10-11 to 2024-03-28 | Circular 0214/2024 |
| 50 | `WIPRO` | Wipro Ltd | `NIFTY_IT` | 2000-01-01 to Active | Phase 8 Audit Table (L90) |

---

## 5. Authoritative Status of `LICI` in the March 28, 2024 Reconstitution

In `src/nifty_ai/data/news/constituents.py` (L100–108), `LICI` (Life Insurance Corporation of India) is recorded as:
```python
ConstituentInfo(
    symbol= LICI,
    company_name=Life Insurance Corporation of India,
    sector=NIFTY_FIN_SERVICE,
    valid_from=date(2024, 3, 28),
    valid_to=None,
    active=True,
    cik=None,
)
``

### Forensic Findings:
1. **Circular Ref: `0214/2024` Review**:
   Official NSE Indices Circular Ref: `0214/2024`, issued February 28, 2024 (effective March 28, 2024), specifies:
   - **NIFTY 50 Changes**:
     - *Inclusion*: `SHRIRAMFIN` (Shriram Finance Ltd.)
     - *Exclusion*: `UPL` (UPL Ltd.)
   - **NIFTY Next 50 Changes**:
     - *Inclusions*: `ADANIWILMAR`, `BOSCHLTD`, `CANBK`, `INDHOTEL`, `JIOFIN`, `LICI` (Life Insurance Corporation of India), `MUTHOOTFIN`, `PAYTM`, `POLYCAB`.
     - *Exclusions*: `PIIND`, `SHRIRAMFIN`, etc.
2. **Definitive Conclusion**:
   `LICI` was added to **NIFTY Next 50**, not NIFTY 50. It has **never been a constituent of NIFTY 50**.
   Its presence in `src/nifty_ai/data/news/constituents.py` is a verified defect that led Step 2 to execute 3 unnecessary constituent-year queries and ingest 437 records for an illegitimate entity.

---

## 6. Comprehensive Inventory of Repository Discrepancies

The retrieval of authoritative NSE Indices evidence exposes five distinct discrepancies across the codebase and documentation:

### Discrepancy 1: `LICI` Erroneously Registered in NIFTY 50 Registry
- **Location**: `src/nifty_ai/data/news/constituents.py` (L100–108).
- **Issue**: `LICI` is registered as a NIFTY 50 constituent from `2024-03-28` onwards.
- **Evidence**: Circular `0214/2024` proves `LICI` was added to NIFTY Next 50, not NIFTY 50.
- **Impact**: 437 non-index announcements ingested in Step 2; will corrupt constituent coverage if not removed.

### Discrepancy 2: `HDFCLIFE` Completely Missing from Registry and Documentation
- **Location**: `src/nifty_ai/data/news/constituents.py` and `docs/PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md`.
- **Issue**: `HDFCLIFE` is completely absent from all repository registries.
- **Evidence**: NSE Press Release dated July 03, 2020 confirms `HDFCLIFE` replaced `VEDL` on July 31, 2020 and has been an active NIFTY 50 constituent continuously since that date.
- **Impact**: The terminal holdout acquisition currently has zero announcements for an active index constituent.

### Discrepancy 3: 30 Documented Baseline Constituents Missing from Code Registry
- **Location**: `src/nifty_ai/data/news/constituents.py`.
- **Issue**: While 49 baseline constituents are recognized in Phase 8 documentation, only 19 baseline constituents are coded in `CANONICAL_CONSTITUENTS`.
- **Evidence**: Comparison between `docs/PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md` and `constituents.py`.
- **Impact**: Step 2 acquisition queried only 26 constituents instead of the complete 56-company PIT universe, omitting 150 constituent-year queries.

### Discrepancy 4: `ZEEL` Exit Date Misrecorded as `2021-03-31`
- **Location**: `docs/PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md` (L92).
- **Issue**: Table records `ZEEL` `valid_to = 2021-03-31`.
- **Evidence**: NSE Press Release dated August 20, 2020 confirms `ZEEL` exited on `2020-09-25`.
- **Impact**: Created the false appearance of 2 exclusions vs 1 inclusion in March 2021, concealing the true source of the missing constituent.

### Discrepancy 5: `VEDL` Exit Date Misrecorded as `2020-09-25`
- **Location**: `docs/PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md` (L89).
- **Issue**: Table records `VEDL` `valid_to = 2020-09-25`.
- **Evidence**: NSE Press Release dated July 03, 2020 confirms `VEDL` was excluded on `2020-07-31` due to delisting.
- **Impact**: Obscured the special interim reconstitution that brought `HDFCLIFE` into the index.

---

## 7. Reconciled 2022–2026 Complete PIT Universe Size

With all evidence verified, the true historical NIFTY 50 universe across the entire terminal out-of-sample window (2022-01-01 to 2026-09-04) is determined:

- **Active on 2022-01-01 (Baseline Cohort)**: Exactly **50 companies** (including `HDFCLIFE`).
- **Subsequent Entrants (Additions)**:
  1. `APOLLOHOSP` (entered 2022-03-31, replacing `IOC`)
  2. `ADANIENT` (entered 2022-09-30, replacing `SHREECEM`)
  3. `LTIM` (entered 2023-07-13, replacing `HDFC` due to merger)
  4. `SHRIRAMFIN` (entered 2024-03-28, replacing `UPL`)
  5. `BEL` (entered 2024-09-30, replacing `DIVISLAB`)
  6. `TRENT` (entered 2024-09-30, replacing `LTIM`)
- **Total Unique Historical Companies Across 2022–2026**:
  \text{Total Unique Entities} = 50 \text{ (Baseline)} + 6 \text{ (Unique Inclusions)} = \mathbf{56} \text{ unique companies}
  *(Note: `LTIM` entered on 2023-07-13 and subsequently exited on 2024-09-30, so both entries/exits are within the 6 additions).*

---

## 8. Final Mandated Verdict

In accordance with the required evaluation rubrics:

### **C) OFFICIAL EVIDENCE REVEALS ADDITIONAL REGISTRY DISCREPANCIES**

**Detailed Finding**:
1. The 50th baseline constituent active on `2022-01-01` is **authoritatively verified as `HDFCLIFE`** (HDFC Life Insurance Company Ltd., effective `2020-07-31` replacing `VEDL`, per NSE Press Release dated July 03, 2020).
2. However, the retrieval of official NSE evidence simultaneously reveals multiple substantial discrepancies in the repository:
   - `LICI` is falsely registered as a NIFTY 50 constituent in `src/nifty_ai/data/news/constituents.py` (it was added to NIFTY Next 50).
   - `HDFCLIFE` and 30 other baseline constituents are missing from `constituents.py`.
   - `ZEEL` and `VEDL` exit dates are misdated in repository documentation.
3. Therefore, before the terminal acquisition can be rerun across the true 56-company PIT universe, the codebase registry must be reconciled to remove `LICI` and add all 50 baseline constituents plus subsequent entrants with exact official dates.
