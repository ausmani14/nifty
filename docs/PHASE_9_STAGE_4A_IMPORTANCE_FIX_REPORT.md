# Phase 9 — Stage 4A Importance-Score Defect Correction Report

**Project**: NIFTY AI Next-Trading-Day Directional Prediction Engine  
**Phase**: Phase 9 (Authentic News & Empirical Evaluation)  
**Stage**: Stage 4A Correction (Importance-Score Defect Resolution & Pipeline Re-Execution)  
**Date**: 2026-09-16  
**Status**: `STAGE_4A_IMPORTANCE_FIX_COMPLETE`  

---

## 1. Executive Summary

During the pre-model forensic audit of Phase 9 Stage 4A, a single verified implementation defect was identified in `src/nifty_ai/data/news/preprocessing.py`:
- In the preprocessing loop, `compute_ex_ante_importance()` was receiving `EventType.ROUTINE_COMMENTARY` instead of passing the event derived from `classify_phase8_events(full_text)`.
- This hardcoding forced the event severity component $E$ to $0.20$ across all 62,329 authentic NSE disclosures, compressing the importance score distribution to $[0.44, 0.62]$ and causing the aggregate feature `news_volume_high_importance` (defined as $\text{importance} \ge 0.70$) to be identically zero across all 4,653 trading days.

### Correction Executed
1. Defined `PHASE8_TO_EVENT_TYPE` mapping dictionary in `src/nifty_ai/data/news/preprocessing.py` mapping each of the 18 Phase 8 canonical categories to its corresponding `EventType` enum member.
2. Updated the calls to both `evaluate_market_relevance()` and `compute_ex_ante_importance()` to use `primary_evt_enum`, ensuring that material events (earnings, corporate actions, management changes, capex, legal/regulatory) receive their true rubric event severity ($0.80, 0.50$).
3. Preserved canonical string representations in `CanonicalNewsRecord.primary_event` and `secondary_events` to maintain strict schema adherence with the 18-category canonical Phase 8 taxonomy.
4. Re-executed deterministic preprocessing across the complete authentic 62,329-record inventory (`scripts/preprocess_authentic_news.py`).

---

## 2. Invariant & Forensic Verification Matrix

| Verification Item | Required Specification | Measured Post-Fix Result | Compliance Status |
| :--- | :--- | :--- | :--- |
| **A. Raw Inventory Integrity** | SHA-256: `6134fd770b30...`, 62,329 records | SHA-256: `6134fd770b30...`, 62,329 records | **PASS (EXACT)** |
| **B. PIT Calendar Partition** | Snap A = 25,523, Snap B = 36,806, Unassigned = 0 | Snap A = 25,523, Snap B = 36,806, Unassigned = 0 | **PASS (EXACT)** |
| **C. Importance Score Range** | Expanded from $[0.44, 0.62]$ up to $0.80$ | Min: `0.4400`, Max: `0.8000`, Mean: `0.6075` | **PASS (RESOLVED)** |
| **C. High-Importance Count** | $\ge 0.70$ count > 0 | `15,483` records ($24.84\%$) | **PASS (ACTIVE)** |
| **C. Daily High-Imp Volume** | Non-zero volume on material news days | Snap A: 2,372 days (max 44), Snap B: 2,683 days (max 28) | **PASS (CONFIRMED)** |
| **D. Holdout Isolation** | 2022-01-01 to 2026-09-04 = 0 news rows | 1,154 days, 0 news records across both daily CSVs | **PASS (QUARANTINED)** |
| **E. Sentiment Invariance** | 20 audit records polarity/class unchanged | 100% identical polarities & classifications | **PASS (VERIFIED)** |
| **F. Novelty Distribution** | Causal 7-day deduplication unchanged | Min: `0.0000`, Max: `1.0000`, Mean: `0.4092` | **PASS (UNCHANGED)** |
| **G. Leakage & Test Suite** | All leakage & system tests pass | 6/6 leakage tests pass; 147/147 test suite pass | **PASS (100%)** |

---

## 3. Detailed Distribution Comparison: Before vs. After

### Canonical News Record Importance Distribution (N = 62,329)

| Metric | Pre-Correction (Buggy) | Post-Correction (Fixed) | Delta / Impact |
| :--- | :--- | :--- | :--- |
| **Minimum Score** | 0.4400 | 0.4400 | Identical base for routine/incidental filings |
| **Maximum Score** | 0.6200 | 0.8000 | +0.1800 (Reflects $E=0.80, S=1.00, M=0.90$) |
| **Mean Score** | 0.5342 | 0.6075 | +0.0733 (Accurate economic weighting) |
| **Median Score** | 0.5000 | 0.6200 | +0.1200 |
| **Standard Deviation** | 0.0891 | 0.1288 | Higher authentic signal variance |
| **Count $\ge 0.70$** | 0 ($0.0\%$) | 15,483 ($24.84\%$) | Unlocked high-importance signal |
| **Count $\ge 0.60$** | 24,141 ($38.7\%$) | 43,045 ($69.06\%$) | Material events elevated above incidental filings |

### 5-Point Ordinal Importance Distribution

| Rubric Level | Score Range | Record Count | Proportion | Economic Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| **Level 1 (Very Low)** | $[0.00, 0.30)$ | 0 | 0.0% | Tier 1 regulatory floor prevents scores $< 0.30$ |
| **Level 2 (Low)** | $[0.30, 0.45)$ | 18,303 | 29.37% | Non-active constituent, low relevance or routine filings |
| **Level 3 (Moderate)** | $[0.45, 0.65)$ | 27,737 | 44.50% | Sector-material updates or intermediate relevance |
| **Level 4 (High)** | $[0.65, 0.80)$ | 5,694 | 9.14% | Capex / contracts / moderate severity active constituents |
| **Level 5 (Critical)** | $[0.80, 1.00]$ | 10,595 | 17.00% | Direct active constituent earnings, corporate actions, legal |
| **Total** | | **62,329** | **100.0%** | |

---

## 4. Daily Feature Impact on Snapshot A and Snapshot B

With importance scores uncompressed:
1. **Snapshot A (`snapshot_a_news_daily.csv`)**:
   - `news_volume_high_importance`: Mean = 1.217, Max = 44.0.
   - Non-zero days: 2,372 out of 4,653 trading sessions (50.98%).
   - `max_importance_score`: Mean = 0.5358, Median = 0.7600, Max = 0.8000.
2. **Snapshot B (`snapshot_b_news_daily.csv`)**:
   - `news_volume_high_importance`: Mean = 1.761, Max = 28.0.
   - Non-zero days: 2,683 out of 4,653 trading sessions (57.66%).
   - `max_importance_score`: Mean = 0.5731, Median = 0.8000, Max = 0.8000.

---

## 5. Sentiment Audit Verification (20 Sample Records)

The 20 audit records selected during pre-model forensic validation were inspected to verify that deterministic sentiment scoring remained 100% invariant:

| ID | Date | Primary Event | Imp Score | Sentiment Class | Polarity | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `RAW_NSE_028050` | 2008-01-01 | OTHER | 0.44 | POSITIVE | +1.0000 | 0.90 |
| `RAW_NSE_028049` | 2008-01-02 | OTHER | 0.44 | POSITIVE | +1.0000 | 1.00 |
| `RAW_NSE_000341` | 2008-01-02 | M_AND_A | 0.80 | POSITIVE | +1.0000 | 0.82 |
| `RAW_NSE_000340` | 2008-01-02 | M_AND_A | 0.80 | POSITIVE | +1.0000 | 0.82 |
| `RAW_NSE_000113` | 2008-01-03 | MANAGEMENT_CHANGE | 0.80 | POSITIVE | +1.0000 | 0.82 |
| `RAW_NSE_028244` | 2008-01-03 | M_AND_A | 0.62 | POSITIVE | +1.0000 | 0.82 |
| `RAW_NSE_000215` | 2008-01-04 | CORPORATE_ACTION | 0.80 | POSITIVE | +1.0000 | 0.73 |
| `RAW_NSE_062215` | 2008-01-04 | OTHER | 0.44 | POSITIVE | +1.0000 | 0.73 |
| `RAW_NSE_000473` | 2008-01-07 | ORDER_CONTRACT | 0.71 | POSITIVE | +1.0000 | 1.00 |
| `RAW_NSE_057073` | 2008-01-07 | OTHER | 0.44 | POSITIVE | +0.3333 | 1.00 |
| `RAW_NSE_028902` | 2008-01-07 | MANAGEMENT_CHANGE | 0.62 | NEGATIVE | -1.0000 | 0.82 |
| `RAW_NSE_057072` | 2008-01-07 | OTHER | 0.44 | POSITIVE | +0.3333 | 1.00 |
| `RAW_NSE_062214` | 2008-01-07 | OTHER | 0.44 | POSITIVE | +1.0000 | 0.82 |
| `RAW_NSE_054971` | 2008-01-07 | REGULATORY_LEGAL | 0.76 | POSITIVE | +1.0000 | 0.90 |
| `RAW_NSE_028774` | 2008-01-07 | OTHER | 0.44 | POSITIVE | +1.0000 | 0.82 |
| `RAW_NSE_028490` | 2008-01-08 | M_AND_A | 0.62 | POSITIVE | +1.0000 | 0.90 |
| `RAW_NSE_028773` | 2008-01-08 | OTHER | 0.44 | NEGATIVE | -1.0000 | 0.82 |
| `RAW_NSE_057071` | 2008-01-09 | OTHER | 0.44 | POSITIVE | +1.0000 | 0.98 |
| `RAW_NSE_062213` | 2008-01-09 | OTHER | 0.44 | POSITIVE | +1.0000 | 0.73 |
| `RAW_NSE_000772` | 2008-01-09 | OTHER | 0.48 | POSITIVE | +1.0000 | 0.82 |

---

## 6. Output Artifact Cryptographic Signatures

The regenerated Stage 4A artifacts possess the following SHA-256 checksums:
- `raw_authentic_news_inventory.jsonl`: `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` (Input source, unmodified)
- `gold_holdout_annotation_input.csv`: `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` (Quarantined holdout, unmodified)
- `canonical_news_records.jsonl`: `703497c6d121fb2e940324376df7d1f1b14114e1c5a057769e1ca112a210c0e9`
- `snapshot_a_news_daily.csv`: `207b888092b7876f3fea1221580eb2fd9b7e0168a34c72d834e328289645a1d5`
- `snapshot_b_news_daily.csv`: `0feb728a02d39474142937552bc93ade8ce3ed4421de64c7d935749535c6f0b9`
- `diagnostic_delta_b_minus_a_news.csv`: `353a06ce0e71669f3f875ea4135cfc3213f25315d2589f024e4cda6b0c5b888e`

---

## 7. Conclusion & Governance Sign-Off

The importance-score implementation defect has been completely resolved. All 62,329 authentic NSE records have been reprocessed deterministically, restoring the full variance of the ex-ante importance rubric ($[0.44, 0.80]$) and enabling the `news_volume_high_importance` feature without altering sentiment, novelty, PIT partitions, or terminal holdout zero-coverage integrity.

Phase 9 Stage 4A is certified **COMPLETE** and ready for downstream modeling.
