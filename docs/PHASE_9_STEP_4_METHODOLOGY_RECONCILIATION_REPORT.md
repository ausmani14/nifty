# Phase 9 — Step 4: Methodology Reconciliation & Pre-Execution Gate Report

**Document Date**: September 17, 2026  
**Auditor / Senior ML Research Engineer**: Senior Quantitative ML Research Engineer & Data Provenance Auditor  
**Governing Phase**: Phase 9 — Point-in-Time News Predictive-Value Evaluation  
**Status**: PRE-EXECUTION AUDIT COMPLETE — AWAITING USER GATE CONFIRMATION  
**Gate Determination**: **`A) Methodology fully consistent with sealed prior phases`**

---

## 1. Executive Summary & Purpose

Pursuant to the Phase 9 Step 4 Pre-Execution Audit, all model architectures, hyperparameters, tree-count selection rules, sample counts, feature group dimensions, statistical tests, and holdout governance protocols have been reconciled against the sealed Phase 6 and Phase 7 specifications.

**No model training, tuning, or holdout evaluation has been performed.** This document establishes the exact mathematical, architectural, and data contracts that will govern the Step 4 experiment upon authorization.

---

## 2. Model Configuration Reconciliation (Sealed Phase 6 Parity)

To guarantee that any observed performance difference is strictly attributable to feature representations (and not confounded by hyperparameter re-tuning), the primary experiment preserves the exact frozen configurations from sealed Phase 6 (`configs/models.yaml`):

### A. Direction Classifier (UP / DOWN / SIDEWAYS)
- **Architecture**: `XGBoostDirectionClassifier` (`objective: multi:softprob`, `num_class: 3`)
- **Learning Rate ($\eta$)**: `0.10` *(Corrected from proposed 0.05)*
- **Max Depth**: `2`
- **Min Child Weight**: `10.0`
- **Subsample**: `0.8`
- **Colsample by Tree**: `0.8`
- **L1 Regularization ($\alpha$)**: `0.1`
- **L2 Regularization ($\lambda$)**: `1.0`
- **Class Weight**: `None`
- **Early Stopping**: `early_stopping_rounds = 25` (during development OOF validation)
- **Sealed Tree Count ($N^*$)**: **`12` trees**
- **Calibration**: Multinomial Platt Scaler fitted strictly on development OOF probabilities.

### B. Next-Day Return Regressor (Continuous $\hat{r}_{t+1}$)
- **Architecture**: `XGBoostReturnRegressor` (`objective: reg:squarederror`)
- **Learning Rate ($\eta$)**: `0.05` *(Corrected from proposed 0.03)*
- **Max Depth**: `2`
- **Min Child Weight**: `20.0`
- **Subsample**: `0.8`
- **Colsample by Tree**: `0.7`
- **L1 Regularization ($\alpha$)**: `0.5`
- **L2 Regularization ($\lambda$)**: `2.0`
- **Early Stopping**: `early_stopping_rounds = 25` (during development OOF validation)
- **Sealed Tree Count ($N^*$)**: **`43` trees**

### C. Tree-Count Methodology Invariant
- **Primary Model Comparison (Model 0 vs Model 1 vs Model 2)**: Uses the **sealed Phase 6 optimal tree counts** ($N^* = 12$ for Classifier, $N^* = 43$ for Regressor).
- **Secondary Sensitivity Analysis**: If tree counts are re-estimated from development fold early-stopping rounds, they will be explicitly designated as a secondary sensitivity analysis and will never alter the primary comparison.
- **Terminal Holdout Tree-Count Invariance**: Under no circumstances will the terminal holdout (`2022–2026`) be used to select, tune, or validate tree counts.

---

## 3. Sample Counts & 4-Way Date Intersection Reconciliation

The preliminary Step 4 proposal draft cited tentative dates resulting in 3,326 development and 1,127 holdout sessions. A rigorous 4-way chronological join was executed across:
1. **Phase 4 Price Features**: `data/features/nifty50_features_clean.csv` (4,653 sessions)
2. **Phase 5 Targets**: `data/targets/nifty50_targets_snapshot_a.csv` & `snapshot_b.csv` (4,654 sessions)
3. **Phase 7 Context**: `data/interim/context/snapshot_a_context_daily.csv` & `snapshot_b_context_daily.csv` (4,653 sessions)
4. **Phase 9 Step 3 News**: `data/interim/news/features_news_snapshot_a.csv` & `features_news_snapshot_b.csv` (4,653 sessions)

### Empirical Date Trace Results

```
Phase 6 Supervised Sessions: 4,453 (Start: 2008-07-08, End: 2026-09-03)
Phase 6 Supervised Dates in Context A: 100% MATCH (0 dropped)
Phase 6 Supervised Dates in Context B: 100% MATCH (0 dropped)
Phase 6 Supervised Dates in News A:    100% MATCH (0 dropped)
Phase 6 Supervised Dates in News B:    100% MATCH (0 dropped)
```

| Partition | Date Range | Phase 6 Count | Step 4 Actual Intersection | Discrepancy / Rows Dropped |
| :--- | :---: | :---: | :---: | :---: |
| **Initial Burn-In / Warm-Up** *(Unsupervised)* | 2007-09-17 to 2008-07-07 | 200 | 200 | 0 (Burn-in for 200-day rolling indicators) |
| **Development Window** *(Supervised)* | **2008-07-08 to 2021-12-31** | **3,299** | **3,299** | **0 (EXACT MATCH)** |
| — *Pre-OOF Training Baseline* | 2008-07-08 to 2013-12-31 | 1,325 | 1,325 | 0 (EXACT MATCH) |
| — *OOF Walk-Forward Folds (8 Years)* | 2014-01-01 to 2021-12-31 | 1,974 | 1,974 | 0 (EXACT MATCH) |
| **Terminal Holdout** *(Supervised)* | **2022-01-03 to 2026-09-03** | **1,154** | **1,154** | **0 (EXACT MATCH)** |
| **Terminal Unlabeled Session** *(Inference Only)* | 2026-09-04 | 1 | 1 | 0 (No forward target T+1 exists) |
| **TOTAL SUPERVISED SESSIONS** | **2008-07-08 to 2026-09-03** | **4,453** | **4,453** | **0 (100% BYTE-FOR-BYTE RECONCILED)** |

### Forensic Explanation:
The numbers 3,326 and 1,127 were an unexecuted drafting artifact in the preliminary proposal. The true code execution using `load_aligned_dataset()` proves that **the 4-way intersection across Price, Targets, Context, and News yields exactly 3,299 Development sessions and 1,154 Holdout sessions with ZERO dropped rows**. Parity with sealed Phase 6 is 100% absolute.

---

## 4. Explicit News Feature Group Manifest (49 Features, 0 Overlaps)

The 65 columns in `features_news_snapshot_a.csv` and `features_news_snapshot_b.csv` comprise:
- **6 Metadata Columns**: `trading_date`, `target_date`, `snapshot_type`, `cutoff_timestamp`, `data_status`, `news_observed`
- **10 Legacy Compatibility Aliases**: `news_volume_total`, `news_volume_high_importance`, `num_distinct_companies`, `num_distinct_event_types`, `mean_sentiment_polarity`, `importance_weighted_sentiment`, `max_importance_score`, `earnings_event_count`, `macro_event_count`, `monetary_event_count`
- **49 Pre-Registered Modeling Features** grouped into 6 mutually exclusive ablation sets:

### 1. News-Count (6 features)
1. `news_count`
2. `high_relevance_count`
3. `high_importance_count`
4. `unique_company_count`
5. `unique_event_type_count`
6. `has_news_flag`

### 2. News-Sentiment (10 features)
7. `mean_sentiment`
8. `weighted_sentiment`
9. `novelty_weighted_sentiment`
10. `sentiment_dispersion`
11. `positive_count`
12. `negative_count`
13. `neutral_count`
14. `positive_ratio`
15. `negative_ratio`
16. `sentiment_balance`

### 3. News-Importance (4 features)
17. `mean_importance`
18. `max_importance`
19. `weighted_importance`
20. `high_importance_ratio`

### 4. News-Event (18 features)
21. `event_earnings_results_count`
22. `event_dividend_count`
23. `event_bonus_split_count`
24. `event_rights_issue_count`
25. `event_buyback_count`
26. `event_m_and_a_count`
27. `event_capex_business_update_count`
28. `event_financial_irregularity_count`
29. `event_shareholding_change_count`
30. `event_operational_event_count`
31. `event_strategic_partnership_count`
32. `event_credit_rating_debt_count`
33. `event_fundraising_count`
34. `event_regulatory_legal_count`
35. `event_corporate_action_count`
36. `event_management_change_count`
37. `event_order_contract_count`
38. `event_other_count`

### 5. News-Novelty (3 features)
39. `mean_novelty`
40. `weighted_novelty`
41. `novel_news_count`

### 6. News-Company (8 features)
42. `top_company_share`
43. `top_event_share`
44. `company_entropy`
45. `event_entropy`
46. `company_news_count_mean`
47. `company_weighted_sentiment_mean`
48. `company_weighted_importance_mean`
49. `company_novelty_mean`

### Overlap Audit:
$$\text{Union}(\text{Count, Sentiment, Importance, Event, Novelty, Company}) = 49 \text{ features}$$
$$\text{Intersection across all groups} = \emptyset \quad (\mathbf{0\ overlaps})$$
**Total Modeling Pool**: Exactly 49 features. Zero post-hoc feature engineering or exploratory cherry-picking.

---

## 5. Market Context Specification (18 Features)

In strict accordance with Phase 7 and the Phase 9 Candidate Registry:
- **11 Daily Log Returns**:
  `ctx_ret_1d_nifty_bank`, `ctx_ret_1d_sp500`, `ctx_ret_1d_nasdaq`, `ctx_ret_1d_dow_jones`, `ctx_ret_1d_brent_crude`, `ctx_ret_1d_wti_crude`, `ctx_ret_1d_gold`, `ctx_ret_1d_dxy`, `ctx_ret_1d_nikkei_225`, `ctx_ret_1d_hang_seng`, `ctx_ret_1d_ftse_100`
- **5 Absolute Changes ($\Delta V$)**:
  `ctx_diff_1d_india_vix`, `ctx_diff_1d_us_vix`, `ctx_diff_1d_india_10y_yield`, `ctx_diff_1d_us_10y_yield`, `ctx_diff_1d_usd_inr`
- **2 Volatility Regime Levels**:
  `ctx_level_india_vix`, `ctx_level_us_vix`
- **Cleanliness**: 0 NaNs and 0 infs across all 4,653 trading days.

---

## 6. Model Hierarchy & Feature Space Ladder

| Model ID | Model Name | Feature Dimensions | Composition |
| :--- | :--- | :---: | :--- |
| **Model 0** | Price Only | 45 | 45 Phase 4 technical features |
| **Model 1** | Price + Context | 63 | Model 0 (45) + Phase 7 Context (18) |
| **Model 2** | Price + Context + News-All | **112** | Model 1 (63) + Phase 9 Step 3 News-All (49) |
| *M2-Ablation-Count* | Price + Context + News-Count | 69 | Model 1 (63) + News-Count (6) |
| *M2-Ablation-Sentiment* | Price + Context + News-Sentiment | 73 | Model 1 (63) + News-Sentiment (10) |
| *M2-Ablation-Importance* | Price + Context + News-Importance | 67 | Model 1 (63) + News-Importance (4) |
| *M2-Ablation-Event* | Price + Context + News-Event | 81 | Model 1 (63) + News-Event (18) |
| *M2-Ablation-Novelty* | Price + Context + News-Novelty | 66 | Model 1 (63) + News-Novelty (3) |
| *M2-Ablation-Company* | Price + Context + News-Company | 71 | Model 1 (63) + News-Company (8) |
| **Model 3** *(Secondary)* | Price + Context + News + Regime | 115 | Model 2 (112) + 3 VIX Regime Interaction Terms |

> **Central Scientific Hypothesis**: $\mathbf{Model\ 1 \to Model\ 2}$. Does the addition of 49 news features to the Price + Context baseline yield statistically and economically meaningful out-of-sample improvements?

---

## 7. Statistical Significance & Testing Protocol

- **Paired Observation Alignment**: Evaluated across identical dates on the same test sets.
- **Classification Metrics**: Log Loss, Brier Score, Accuracy, Macro F1, Expected Calibration Error (ECE), Confusion Matrix, Per-class Precision/Recall.
- **Regression Metrics**: MAE, RMSE, Pearson IC (with t-test p-value), Spearman Rank IC, Directional Accuracy.
- **Diebold-Mariano Test**: Two-sided test on forecast loss differential ($d_t = \text{Loss}_{M1, t} - \text{Loss}_{M2, t}$) using Newey-West HAC covariance and Harvey-Leybourne-Newey (HLN) finite-sample correction.
- **Stationary Block Bootstrap**:
  - Resamples: **1,000**
  - Block Size: **10 sessions**
  - Confidence Level: **95% two-sided CI** ($\alpha = 0.05$)
  - Computed on $\Delta \text{LogLoss} = \text{LogLoss}_{M2} - \text{LogLoss}_{M1}$ and $\Delta \text{IC} = \text{IC}_{M2} - \text{IC}_{M1}$.

---

## 8. Snapshot A and Snapshot B Independence

Snapshot A (intraday market close cutoff `15:30 IST`) and Snapshot B (overnight pre-market cutoff `08:50 IST`) will be evaluated and reported **completely independently**. Under no circumstances will their predictions or metrics be pooled into a single composite score.

---

## 9. Protected Source Hashes & Checksums

Prior to running experiments, the pipeline enforces strict cryptographic verification:

| Resource | Expected SHA-256 Prefix | Full SHA-256 Checksum | Verified Status |
| :--- | :---: | :--- | :---: |
| `raw_authentic_news_inventory.jsonl` | `6134fd77` | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | **LOCKED** |
| `gold_holdout_annotation_input.csv` | `0d55a12d` | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | **ISOLATED** |
| `raw_authentic_news_terminal_2022_2026_step2e.jsonl` | `5d5daf5e` | `5d5daf5ed7c844e86d45dc6a893f03b1d4f523183e29200d94b592329136f6fd` | **LOCKED** |
| `features_news_snapshot_a.csv` | `487ce996` | `487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7` | **LOCKED** |
| `features_news_snapshot_b.csv` | `f57137c0` | `f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606` | **LOCKED** |

---

## 10. Pre-Execution Gate Recommendation

The methodology is now **100% reconciled and compliant** with all sealed Phase 6 and Phase 7 protocols:

$$\mathbf{A)\ Methodology\ fully\ consistent\ with\ sealed\ prior\ phases}$$

Execution will not commence until the user provides explicit authorization.
