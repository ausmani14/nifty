# Phase 9 — Stage 4A: Authentic News NLP Preprocessing & Daily Snapshot Feature Build Report

**Execution Timestamp**: September 16, 2026  
**Operating Role**: Senior ML/Data Engineer  
**Task Scope**: Stage 4A Only — Offline Deterministic NLP Preprocessing & Daily Snapshot Feature Generation  
**Final Verdict**: **STAGE 4A COMPLETE**

---

## 1. Executive Summary

In Stage 4A, the legacy synthetic fixture news data (previously populated with 1–2 synthetic records per day) was completely replaced with authentic, point-in-time, deterministic NLP-derived features computed across the authoritative 62,329-record historical NSE disclosure inventory (`data/interim/news/raw_authentic_news_inventory.jsonl`).

Every derived record-level attribute was evaluated causally and deterministically without human annotation leakage, without LLM dependencies, and without future lookahead. The verified Phase 8 Point-in-Time (PIT) calendar partition was executed, reproducing the exact expected partition: **25,523 records for Snapshot A** and **36,806 records for Snapshot B**, with zero unassigned records. Authentic daily feature tables for both Snapshot A and Snapshot B were generated across the entire 4,653-trading-day history of the NIFTY 50 (September 17, 2007 through September 4, 2026).

---

## 2. Source Inventory Verification

| Attribute | Expected Ground Truth | Actual Verified State | Status |
| :--- | :--- | :--- | :---: |
| **Source Path** | `data/interim/news/raw_authentic_news_inventory.jsonl` | `data/interim/news/raw_authentic_news_inventory.jsonl` | **VERIFIED** |
| **Total Record Count** | Exactly `62,329` | Exactly `62,329` | **PASSED** |
| **Cryptographic Hash (SHA-256)** | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | **MATCH** |
| **Temporal Span** | 2008-01-01 through 2021-12-31 | 2008-01-01 through 2021-12-31 | **VERIFIED** |
| **Terminal Holdout Isolation** | 0 records $\ge$ 2022-01-01 | 0 records $\ge$ 2022-01-01 (100% pre-2022) | **PASSED** |
| **Quarantined Holdout Hash** | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | **UNTOUCHED** |

No annotation files (`fresh_calibration_50_human_annotations_corrected.csv`, `fresh_calibration_50_annotator_2_completed.csv`, `ai_assisted_development_annotations.csv`, or `gold_holdout_annotation_input.csv`) were accessed or used as model features.

---

## 3. Record-Level NLP Extraction & Taxonomy Coverage

Deterministic NLP was executed across all 62,329 authentic disclosures using the existing codebase algorithms:
- **Entities & Sectors**: Point-in-time entity resolution using `extract_entities` and `map_sectors_from_entities` (`src/nifty_ai/data/news/nlp_engine.py`) with historical constituent tenure gating (`is_active_nifty_constituent`).
- **Event Taxonomy**: Finalized Phase 8 canonical taxonomy: 17 substantive categories plus `OTHER` fallback.
- **Market Relevance**: Graded relevance classification (`MarketRelevanceCategory`).
- **Ex-Ante Importance**: Four-component weighting (Source authority, event severity, market scope, coverage breadth).
- **Financial Sentiment**: Domain-adapted Loughran-McDonald lexicon (`LoughranMcDonaldIndianSentiment`).
- **Causal Novelty**: Streaming causal deduplicator with 7-day lookback buffer (`StreamingDeduplicator`).

### A. Canonical Event Distribution (62,329 Records)

| Category # | Event Taxonomy Category | Class Type | Record Count | Percentage |
| :---: | :--- | :--- | ---: | ---: |
| 1 | **`EARNINGS_RESULTS`** | Substantive | 7,211 | 11.57% |
| 2 | **`DIVIDEND`** | Substantive | 2,911 | 4.67% |
| 3 | **`BONUS_SPLIT`** | Substantive | 76 | 0.12% |
| 4 | **`RIGHTS_ISSUE`** | Substantive | 118 | 0.19% |
| 5 | **`BUYBACK`** | Substantive | 474 | 0.76% |
| 6 | **`M_AND_A`** | Substantive | 2,823 | 4.53% |
| 7 | **`CAPEX_BUSINESS_UPDATE`** | Substantive | 156 | 0.25% |
| 8 | **`FINANCIAL_IRREGULARITY`** | Substantive | 17 | 0.03% |
| 9 | **`SHAREHOLDING_CHANGE`** | Substantive | 2,749 | 4.41% |
| 10 | **`OPERATIONAL_EVENT`** | Substantive | 112 | 0.18% |
| 11 | **`STRATEGIC_PARTNERSHIP`** | Substantive | 516 | 0.83% |
| 12 | **`CREDIT_RATING_DEBT`** | Substantive | 491 | 0.79% |
| 13 | **`FUNDRAISING`** | Substantive | 433 | 0.70% |
| 14 | **`REGULATORY_LEGAL`** | Substantive | 3,026 | 4.85% |
| 15 | **`CORPORATE_ACTION`** | Substantive | 6,784 | 10.88% |
| 16 | **`MANAGEMENT_CHANGE`** | Substantive | 2,078 | 3.33% |
| 17 | **`ORDER_CONTRACT`** | Substantive | 18 | 0.03% |
| 18 | **`OTHER`** | Fallback (Administrative/Procedural) | 32,336 | 51.88% |
| **TOTAL** | | | **62,329** | **100.00%** |

### B. Event Taxonomy Compatibility Decision for Daily Aggregates
- **`earnings_event_count`**: Mapped directly to canonical `EARNINGS_RESULTS` records (plus secondary events).
- **`macro_event_count`**: The authoritative 18-category corporate disclosure taxonomy does not define a separate macroeconomic wire category (since all 62,329 items are official NSE corporate filings, not macroeconomic agency prints). In accordance with instructions, no category was fabricated; `macro_event_count` is legitimately 0 across authentic corporate filings.
- **`monetary_event_count`**: The authoritative 18-category corporate disclosure taxonomy does not define a separate central bank monetary policy category. In accordance with instructions, no category was fabricated; `monetary_event_count` is legitimately 0 across authentic corporate filings.

### C. Sentiment Class Distribution

| Sentiment Class | Records | Percentage | Mean Polarity | Polarity Range |
| :--- | ---: | ---: | ---: | :---: |
| **`POSITIVE`** | 11,828 | 18.98% | +0.4712 | $[+0.10, +1.00]$ |
| **`NEGATIVE`** | 3,408 | 5.47% | -0.4285 | $[-1.00, -0.10]$ |
| **`NEUTRAL`** | 47,093 | 75.55% | 0.0000 | $0.00$ |
| **TOTAL** | **62,329** | **100.00%** | | |

### D. Market Relevance Distribution

| Market Relevance Category | Criteria | Records | Percentage |
| :--- | :--- | ---: | ---: |
| **`high_direct`** | Active constituent direct corporate catalyst | 24,139 | 38.73% |
| **`moderate_sector`** | Sectoral / regulatory catalyst | 4,332 | 6.95% |
| **`broad_macro`** | Systemic macro impact | 2 | 0.00% |
| **`low_incidental`** | Minor or incidental mention | 1,137 | 1.82% |
| **`zero_irrelevant`** | Administrative noise or secretarial routine | 32,719 | 52.50% |
| **TOTAL** | | **62,329** | **100.00%** |

### E. Ex-Ante Importance Rubric Distribution

| Importance Level | Score Range | Rubric Interpretation | Records | Percentage |
| :---: | :---: | :--- | ---: | ---: |
| **Level 2** | $[0.20, 0.45)$ | Routine corporate notices / procedural compliance | 32,719 | 52.50% |
| **Level 3** | $[0.45, 0.70)$ | Standard operational filings / commercial updates | 29,610 | 47.50% |
| **Level 4 / 5** | $\ge 0.70$ | High-severity material corporate catalysts | 0 | 0.00% |
| **TOTAL** | | | **62,329** | **100.00%** |

---

## 4. Point-in-Time (PIT) Assignment Verification

All 62,329 records were assigned using the verified Phase 8 function [`assign_record_pit`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/src/nifty_ai/data/news/preprocessing.py) grounded in the official trading calendar (`data/processed/nifty_50_daily.csv`):

| Snapshot | Window Definition | Allocated Records | Expected Target | Status |
| :--- | :--- | ---: | ---: | :---: |
| **`Snapshot A`** | $(T-1\ 15:30\text{ IST}, T\ 15:30\text{ IST}]$ (intraday trading hours $08:50 < t \le 15:30$) | **25,523** | 25,523 | **EXACT MATCH** |
| **`Snapshot B`** | $(T\ 15:30\text{ IST}, T+1\ 08:50\text{ IST}]$ (post-close, overnight, weekend, pre-open) | **36,806** | 36,806 | **EXACT MATCH** |
| **Unassigned** | Out of bounds / missing trading day | **0** | 0 | **EXACT MATCH** |
| **TOTAL** | Disjoint union: $A \cup B$ | **62,329** | 62,329 | **100.00%** |

### Boundary Rules & Integrity Checks
1. **Intraday Boundary**: Every record in Snapshot A on trading day $T$ satisfies $\text{timestamp} \le T\text{ 15:30:00 IST}$ (0 violations).
2. **Overnight Lower Bound**: Every record in Snapshot B on trading day $T$ satisfies $\text{timestamp} > T\text{ 15:30:00 IST}$ (0 violations).
3. **Pre-Open Upper Bound**: Every record in Snapshot B satisfies $\text{timestamp} \le T+1\text{ 08:50:00 IST}$ (0 violations).
4. **Disjointness**: Invariant $A(T) \cap B(T) = \emptyset$ is strictly satisfied. Zero records are double-counted.

---

## 5. Daily Aggregates Verification

Two authentic daily aggregate feature tables were constructed covering all 4,653 trading day pairs from September 17, 2007 through September 4, 2026:
- `data/interim/news/snapshot_a_news_daily.csv`
- `data/interim/news/snapshot_b_news_daily.csv`
- Diagnostic delta table: `data/interim/news/diagnostic_delta_b_minus_a_news.csv`

### A. Aggregate Table Summary

| Metric | Snapshot A Daily | Snapshot B Daily | Status |
| :--- | :---: | :---: | :---: |
| **Total Rows** | 4,653 | 4,653 | **EXACT MATCH** |
| **Unique Trading Dates** | 4,653 (100% unique) | 4,653 (100% unique) | **PASSED** |
| **Total Underlying News Count** | 25,523 | 36,806 | **100% RECONCILED** |
| **Days With Authentic News** | 3,382 (72.68%) | 3,381 (72.66%) | **AUTHENTIC COVERAGE** |
| **Zero-News Days** | 1,271 (27.32%) | 1,272 (27.34%) | **VERIFIED** |
| **Missing / NaN / Inf Values** | **0 (0.00%)** | **0 (0.00%)** | **CLEAN** |

### B. Daily News Feature Statistics (Across All 4,653 Trading Days)

#### Snapshot A Features:
- `news_volume_total`: Mean = 5.49, Std = 5.03, Median = 5.0, Min = 0, Max = 49
- `high_relevance_count`: Mean = 1.97, Std = 2.29, Median = 1.0, Min = 0, Max = 25
- `max_importance_score`: Mean = 0.4372, Std = 0.2716, Median = 0.6200, Min = 0.0, Max = 0.62
- `earnings_event_count`: Mean = 0.74, Std = 1.89, Median = 0.0, Min = 0, Max = 28
- `mean_sentiment_polarity`: Mean = +0.0636, Std = 0.1610, Min = -1.0, Max = +1.0
- `sentiment_dispersion`: Mean = 0.1292, Std = 0.1706, Min = 0.0, Max = 0.9428
- `importance_weighted_sentiment`: Mean = +0.0636, Std = 0.1610, Min = -1.0, Max = +1.0
- `novelty_weighted_sentiment`: Mean = +0.0636, Std = 0.1610, Min = -1.0, Max = +1.0

#### Snapshot B Features:
- `news_volume_total`: Mean = 7.91, Std = 8.16, Median = 6.0, Min = 0, Max = 81
- `high_relevance_count`: Mean = 3.22, Std = 3.79, Median = 2.0, Min = 0, Max = 41
- `max_importance_score`: Mean = 0.4372, Std = 0.2717, Median = 0.6200, Min = 0.0, Max = 0.62
- `earnings_event_count`: Mean = 0.81, Std = 2.12, Median = 0.0, Min = 0, Max = 32
- `mean_sentiment_polarity`: Mean = +0.0543, Std = 0.1469, Min = -1.0, Max = +1.0
- `sentiment_dispersion`: Mean = 0.1632, Std = 0.1834, Min = 0.0, Max = 0.9428
- `importance_weighted_sentiment`: Mean = +0.0546, Std = 0.1470, Min = -1.0, Max = +1.0
- `novelty_weighted_sentiment`: Mean = +0.0547, Std = 0.1471, Min = -1.0, Max = +1.0

### C. Proof of Synthetic Fixture Replacement
- Old synthetic fixtures had constant daily volume of 1 or 2 items per day, generated mechanically via `d.toordinal() % len(templates)`.
- The new authentic datasets reflect empirical corporate filing seasonality: earnings season peaks reach up to **49 filings/day in Snapshot A** and **81 filings/day in Snapshot B**, with realistic mean volumes (5.49 and 7.91) and authentic standard deviations (5.03 and 8.16).
- 1,271 zero-news days (consisting of the pre-2008 initialization period and post-2021 holdout period) have cleanly initialized zero-fill feature vectors with `news_observed = False`.

---

## 6. Generated Artifacts & Cryptographic Checksums

| Artifact Path | Description | Records / Rows | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| `data/interim/news/canonical_news_records.jsonl` | Canonical authentic news items with derived NLP attributes | 62,329 | `2a53d55cd8f7da5f3995135f0c6091ba26efb4ba234d4642c9367b303c7dc3a6` |
| `data/interim/news/snapshot_a_news_daily.csv` | Daily authentic Snapshot A feature aggregates | 4,653 | `430972eb54d0274f96051bd74c4cc9d7bdb3255799bfdc01bfffb444d06fe31f` |
| `data/interim/news/snapshot_b_news_daily.csv` | Daily authentic Snapshot B feature aggregates | 4,653 | `087485ec68bf91350d3492b31f46d8e0449e92886d293707962782d757a8eeaa` |
| `data/interim/news/diagnostic_delta_b_minus_a_news.csv` | Daily overnight sentiment shift diagnostic | 4,653 | `6ecddbe5fdf3f8415131a1134dcb939d4b92a2521bdf40cad947fd407479d9a0` |
| `data/interim/news/stage_4a_summary.json` | Execution metadata and distribution summaries | 1 | `7381ffdb2142aa7842618991a0c4fbf50697ad9871c5a96a12b2a608107da48f` |

---

## 7. Automated Test Suite & Forensic Validation

All tests passed with zero failures and zero regressions:

1. **Anti-Leakage & PIT Suite**:
   ```text
   pytest tests/test_phase9_leakage.py -v
   ============================== 6 passed in 0.90s ==============================
   ```
2. **Full Repository Regression Suite**:
   ```text
   pytest -q
   ============================= 147 passed in 5.77s =============================
   ```
3. **Dedicated Stage 4A Forensic Script** (`scripts/validate_stage_4a.py`):
   - Raw authentic inventory checksum: **MATCH**
   - Terminal holdout cryptographic quarantine: **MATCH**
   - Canonical JSONL schema, bounds, and taxonomy validity: **MATCH**
   - Daily CSV row counts (4,653 each): **MATCH**
   - Trading date key uniqueness: **MATCH**
   - Zero NaNs, zero Infs, non-negative event counts: **MATCH**
   - PIT mapping replication ($A=25,523, B=36,806, \text{Unassigned}=0$): **MATCH**
   - Underlying volume reconciliation ($\sum A + \sum B = 62,329$): **100% RECONCILED**
   - Synthetic fixture removal & authentic variance: **CONFIRMED**

---

## 8. Final Status

**STAGE 4A COMPLETE**

All Stage 4A tasks and validation criteria have been satisfied:
- Authentic 62,329-record inventory deterministically preprocessed.
- Finalized Phase 8 18-category canonical event taxonomy enforced.
- Causal novelty and Loughran-McDonald financial sentiment evaluated point-in-time.
- Authoritative Phase 8 PIT calendar partition replicated ($25,523 / 36,806$).
- Daily feature tables built across all 4,653 trading days.
- Legacy synthetic fixture files permanently replaced.
- 100% test suite pass rate maintained.
- Quarantined terminal holdout verified untouched.

*Per project protocol, no models were trained, no predictive claims are made, and execution stops cleanly at the boundary of Stage 4A.*
