# PHASE 13 — STEP 1 RESEARCH REPORT

## UNTOUCHED HOLDOUT EVALUATION PROTOCOL FREEZE

**Role**: Quantitative Researcher, ML Validation Specialist & Forensic Financial-Data Auditor  
**Phase**: Phase 13 Step 1  
**Status**: FORMALLY SEALED & FROZEN  
**Execution Authorization**: Protocol Freeze Only (Zero holdout observations read or evaluated)  
**Governance**: Strict Firewall Intact (`holdout_rows_accessed == 0`, `max(dev_trading_date) <= 2021-12-31`)

---

## 1. Executive Summary & Purpose

Phase 12 established that the weak Snapshot B intraday predictive relationship ($T0$ Open-to-Close return) exhibits statistically unusual contemporaneous alignment relative to dependence-preserving null structures ($p_{\text{exact}} = 0.0476$ across all 40,320 year-block permutations). However, full-sample out-of-fold (OOF) statistical significance does not imply temporal stationarity, economic viability, or future generalizability.

The purpose of Phase 13 Step 1 is to freeze the **complete, immutable holdout evaluation protocol** before the untouched Terminal Holdout ($2022-01-01$ onward) is unsealed:
- **Zero holdout observations have been read, loaded, scanned, or peeked.**
- **Zero holdout predictions have been generated.**
- **Zero holdout metrics have been computed.**
- **Zero holdout-derived parameters, normalizations, thresholds, or models exist.**

All evaluation criteria, model architectures, feature spaces, benchmarks, metric hierarchies, and statistical interpretation rules are frozen into deterministic artifacts.

---

## 2. Terminal Holdout Partition Definition

The holdout partition is formally defined from previously sealed Phase 11 configuration metadata:
- **Partition Identifier**: Terminal Holdout (`terminal_holdout_partition`)
- **Calendar Boundary**: `2022-01-01` onward
- **Expected Trading Range**: `2022-01-03` through `2026-09-03`
- **Expected Sample Size**: $N = 1,154$ trading sessions (recovered strictly from `configs/phase11_strategy_validation_config.json`; unaccessed in Step 1)
- **Governance Mandate**: `EVALUATION_ONLY_SINGLE_PASS`
- **Sub-Period Structure (Pre-Registered for Diagnostic Reporting)**:
  - Sub-Block 1: `2022-01-03` to `2023-12-29`
  - Sub-Block 2: `2024-01-01` to `2026-09-03`

---

## 3. Frozen Primary Evaluation Target

- **Primary Target ID**: `T0`
- **Target Name**: Snapshot B Morning-to-Close Intraday Return
- **Mathematical Definition**:
  $$R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$$
- **Information Cutoff Timestamp**: `08:50 IST` on Session $T+1$ (after observing overnight global context, pre-market signals, and SGX/GIFT Nifty indications).
- **Execution Entry**: `09:15 IST` market open on Session $T+1$.
- **Execution Exit**: `15:30 IST` market close on Session $T+1$.
- **Holding Period**: Strictly intraday daytime session (zero overnight gap risk).
- **Multiple-Testing Quarantine**:
  - $T0$ is the **sole primary target** for the first holdout evaluation.
  - $T1$ ($\text{Close}(T+1)/\text{Close}(T)-1$) contains an already-realized overnight component and is rejected as a primary holdout target.
  - $T2$ (Centered diagnostic), $T3$ (Log-return check), and $T4$ (Intraday extremes) are strictly non-primary diagnostics.

---

## 4. Frozen Feature Space Specification (63 Features)

The feature space is strictly frozen to the established 63-feature Model 1 specification:
- **45 Price Features**:
  `ret_1d`, `ret_2d`, `ret_3d`, `ret_5d`, `ret_10d`, `ret_20d`, `ret_lag_1`, `ret_lag_2`, `ret_lag_3`, `ret_lag_5`, `ret_lag_10`, `sma_5`, `close_to_sma_5`, `sma_10`, `close_to_sma_10`, `sma_20`, `close_to_sma_20`, `sma_50`, `close_to_sma_50`, `sma_100`, `close_to_sma_100`, `sma_200`, `close_to_sma_200`, `mom_5d`, `mom_10d`, `mom_20d`, `mom_60d`, `volatility_5d`, `volatility_10d`, `volatility_20d`, `volatility_60d`, `volatility_ann_20d`, `hl_range_pct`, `close_pos_in_range`, `open_to_close_ret`, `high_to_close_dist`, `low_to_close_dist`, `sma_ratio_20_50`, `sma_ratio_50_200`, `trend_slope_20d`, `day_of_week`, `day_of_month`, `month`, `quarter`, `is_month_end`.
- **18 Context Features**:
  `ctx_ret_1d_nifty_bank`, `ctx_ret_1d_sp500`, `ctx_ret_1d_nasdaq`, `ctx_ret_1d_dow_jones`, `ctx_ret_1d_brent_crude`, `ctx_ret_1d_wti_crude`, `ctx_ret_1d_gold`, `ctx_ret_1d_dxy`, `ctx_ret_1d_nikkei_225`, `ctx_ret_1d_hang_seng`, `ctx_ret_1d_ftse_100`, `ctx_diff_1d_india_vix`, `ctx_diff_1d_us_vix`, `ctx_diff_1d_india_10y_yield`, `ctx_diff_1d_us_10y_yield`, `ctx_diff_1d_usd_inr`, `ctx_level_india_vix`, `ctx_level_us_vix`.
- **Strict Exclusions**:
  - News features: `EXCLUDED` (`news_features_included: false`)
  - Volume features: `EXCLUDED` (`volume_features_included: false`)
  - Flow features: `EXCLUDED` (`flow_features_included: false`)

---

## 5. Model Architecture & Training Boundary Policy

### Locked Policy: Option A — Frozen Historical Models

**Architectural Justification**:
1. Recovered directly from the foundational system design in [`MASTER_SPECIFICATION.md`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/MASTER_SPECIFICATION.md) Section 9.1:
   ```
   Split 1: [--- Train 1 ---][ Val 1 ]
   Split 2: [----- Train 2 -----][ Val 2 ]
   Split 3: [------- Train 3 -------][ Val 3 ]
   Final:   [---------------- Train Full ----------------][ Final Test (Frozen) ]
   ```
2. Aligned with [`configs/phase11_strategy_validation_config.json`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/configs/phase11_strategy_validation_config.json) line 58: `"governance": "EVALUATION_ONLY_SINGLE_PASS"`.
3. Option A guarantees zero hyperparameter tuning, zero retraining schedule leakage, and zero data snooping during the holdout period.

### Model Definitions:
- **Primary Holdout Model (Full Development Production Model)**:
  - Architecture: `xgboost.XGBRegressor`
  - Training Dataset: Full Development Partition (`2008-07-08` through `2021-12-31`, $N=3,299$ sessions)
  - Number of Trees ($N^*$): **43 trees** (locked production regressor tree count)
  - Hyperparameters:
    - `objective`: `"reg:squarederror"`
    - `learning_rate`: `0.05`
    - `max_depth`: `2`
    - `min_child_weight`: `20.0`
    - `subsample`: `0.8`
    - `colsample_bytree`: `0.7`
    - `reg_alpha`: `0.5`
    - `reg_lambda`: `2.0`
    - `random_state`: `42`
    - `n_jobs`: `-1`

- **Pre-Registered Secondary Diagnostic Models**:
  1. *Fold 8 Frozen Model*: Trained on `2008-07-08` through `2020-12-31` ($N=3,051$) with $N^*=40$ trees (representing the maximum walk-forward development fold).
  2. *8-Fold Walk-Forward Uniform Ensemble*: Unweighted average prediction of the 8 walk-forward development models (`[10, 60, 45, 60, 10, 10, 10, 40]`).

---

## 6. Pre-Registered Metric Hierarchy & Evaluation Rules

### Primary Test Metric:
- **Pearson Correlation (IC)**:
  $$r_p = \frac{\sum (\hat{y}_t - \bar{\hat{y}})(y_t - \bar{y})}{\sqrt{\sum (\hat{y}_t - \bar{\hat{y}})^2 \sum (y_t - \bar{y})^2}}$$
  - Sole primary test statistic evaluated at the $\alpha = 0.05$ significance level.

### Secondary Forecasting Metrics:
- **Spearman Rank Correlation (IC)** ($r_s$)
- **Mean Absolute Error (MAE)**
- **Root Mean Squared Error (RMSE)**
- **Mean Directional Accuracy (MDA / Hit Rate)**:
  $$\text{MDA} = \frac{1}{N} \sum_{t=1}^N \mathbb{I}(\text{sign}(\hat{y}_t) == \text{sign}(y_t))$$

### Secondary Statistical Diagnostics:
- **Residual Pearson IC**: Correlation against the historical training baseline mean ($\mu_{\text{train}}$).
- **Residual Spearman IC**
- **Incremental $R^2$**: Variance explained relative to unconditional historical mean baseline.

### Secondary Economic Diagnostics:
- **Trading Rule**: Strategy 1 — Unrestricted Direction (Long if $\hat{y} > 0$, Short if $\hat{y} < 0$, Flat if $\hat{y} == 0$).
- **Position Sizing**: Fixed notional, gross exposure = 1.0, leverage = 1.0.
- **Transaction Cost Scenarios**:
  1. Gross ($0$ bps)
  2. $5$ bps round-trip
  3. $10$ bps round-trip (standard baseline)
  4. $20$ bps round-trip (adverse friction stress)
- **Reported Diagnostics**: Gross/Net Annualized Return, Annualized Sharpe Ratio, Maximum Drawdown, Active Session Count.
- *Strict Rule*: Economic diagnostics are descriptive feasibility checks, not strategy search targets.

---

## 7. Fixed Benchmark Specifications

1. **Benchmark 1 (Zero-Return Predictor)**:
   $$\hat{y}_t \equiv 0.0 \quad \forall t$$
   Evaluates performance against an uninformative constant zero baseline.
2. **Benchmark 2 (Historical Training Mean Predictor)**:
   $$\hat{y}_t \equiv \mu_{\text{train}} = \text{mean}(y_{\text{dev}}) \quad \forall t$$
   Evaluates whether the model outperforms the unconditional historical daytime drift using strictly pre-holdout data ($\le 2021-12-31$).
3. **Benchmark 3 (Always Short Benchmark)**:
   $$\text{position}_t \equiv -1.0 \quad \forall t$$
   Captures the structural negative daytime drift of the Nifty 50.

---

## 8. Statistical Interpretation Framework

The holdout outcome will be classified under one of three pre-registered cases:

- **CASE A — DIRECTIONALLY CONSISTENT**:
  - *Condition*: Holdout Pearson IC $> 0$ with $p < 0.05$ and directionally aligned with OOF ($+0.0476$).
  - *Mandatory Statement*:
    > *"The observed holdout result is directionally consistent with the historical OOF relationship under the predefined evaluation protocol."*

- **CASE B — WEAK OR ABSENT**:
  - *Condition*: Holdout Pearson IC is weak, near zero, or statistically non-significant ($p \ge 0.05$).
  - *Mandatory Statement*:
    > *"The historical OOF relationship did not reproduce strongly in the untouched holdout under the predefined evaluation protocol."*

- **CASE C — MATERIALLY CONTRADICTORY**:
  - *Condition*: Holdout Pearson IC is negative or significantly inverted ($r_p < 0$, $p < 0.05$).
  - *Mandatory Statement*:
    > *"The holdout result is inconsistent with the historical OOF relationship under the predefined evaluation protocol."*

### Mandatory Negative Constraints:
1. No outcome may be described as proof of future persistence.
2. No outcome may be described as proving commercial trading viability.
3. Statistical association does not imply economic viability or causal mechanism.

---

## 9. Holdout Firewall & Verification Audit

The firewall audit conducted in Step 1 verifies:
- `holdout_rows_accessed == 0`
- `no_holdout_rows_loaded == True`
- `no_holdout_targets_loaded == True`
- `no_holdout_predictions_generated == True`
- `no_holdout_metrics_computed == True`
- `no_holdout_derived_parameters == True`
- `no_strategy_optimization_performed == True`

The audit is persisted in [`step1_holdout_firewall_audit.json`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/phase13_step1/step1_holdout_firewall_audit.json).

---

## 10. Artifact Manifest & Cryptographic Hashes

All newly created Phase 13 Step 1 artifacts are stored in [`data/interim/phase13_step1/`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/phase13_step1) with hashes recorded in [`step1_integrity_manifest.json`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/phase13_step1/step1_integrity_manifest.json):

| Artifact File | Description | SHA256 Checksum |
|---|---|---|
| [`step1_holdout_protocol.json`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/phase13_step1/step1_holdout_protocol.json) | Complete machine-readable holdout evaluation protocol | `21e5b9b001f16e2acc003b78e6af78e2c8cdb1ebc44f389c18c0d1957e689395` |
| [`step1_holdout_protocol.md`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/phase13_step1/step1_holdout_protocol.md) | Human-readable frozen protocol specification | `3c64b2355b09b5e4ab85d838c0080a380d91f80c2831f4449c83dd011422f03a` |
| [`step1_holdout_firewall_audit.json`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/phase13_step1/step1_holdout_firewall_audit.json) | Audit verifying zero holdout data access | `6704e275d9c66fd50c2bc964509cbacc76212e9b2cea06f9dad5fb2375625188` |
| [`step1_integrity_manifest.json`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/phase13_step1/step1_integrity_manifest.json) | Cryptographic verification manifest | Verified on disk |

All 67 protected upstream artifacts from Phases 4–10 and Step 5–12 remain byte-for-byte unmodified.

---

## 11. Test Verification Summary

The dedicated test suite [`tests/test_phase13_step1_holdout_protocol.py`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/tests/test_phase13_step1_holdout_protocol.py) passed all 20 assertions:
- `test_phase12_artifacts_unchanged`: Sealed Phase 12 artifacts verified intact.
- `test_primary_target_is_t0`: Primary target verified as $T0$ Open-to-Close return.
- `test_63_feature_model_specification_frozen`: Exactly 63 features verified (45 Price + 18 Context).
- `test_news_excluded`: News features verified excluded.
- `test_volume_excluded`: Volume features verified excluded.
- `test_flow_excluded`: Flow features verified excluded.
- `test_xgboost_configuration_matches_sealed_spec`: Regressor hyperparameters verified.
- `test_primary_metric_is_pearson_ic`: Pearson IC verified as primary metric.
- `test_holdout_start_remains_2022_01_01`: Holdout boundary verified as `2022-01-01` / `2022-01-03`.
- `test_oof_cutoff_remains_2021_12_31`: Development cutoff verified as `2021-12-31`.
- `test_no_holdout_rows_loaded`: `holdout_rows_accessed == 0` verified.
- `test_no_holdout_metrics_exist`: Zero holdout metrics in Step 1 verified.
- `test_no_holdout_derived_parameters_exist`: Zero holdout-derived parameters verified.
- `test_no_strategy_optimization_performed`: No strategy tuning verified.
- `test_protocol_deterministic_and_structured`: Protocol structure verified.
- `test_protocol_hash_reproducible`: Artifact hashes verified against disk.
- `test_protected_upstream_hashes_unchanged`: All 67 upstream protected hashes verified.
- `test_training_policy_option_a`: Training policy verified as Option A (Frozen historical models).
- `test_benchmarks_strictly_pre_registered`: Zero, Historical Mean, Always Short benchmarks verified.
- `test_interpretation_framework_outcomes`: Outcomes A, B, C and negative constraints verified.

**Repository Test Suite Status**:
- `pytest -q`: **463 passed out of 463 tests** across the complete test suite in 34.75s (zero regressions).

---

## 12. Final Seal Status

All pre-registered requirements of Phase 13 Step 1 have been fulfilled:
- Zero holdout data was read, loaded, or evaluated (`holdout_rows_accessed == 0`).
- Evaluation protocol is fully frozen and documented in machine-readable and human-readable formats.
- All methodological choices (target, features, model, training boundary Option A, metrics, benchmarks, interpretation rules) are locked.
- All 20 dedicated unit tests and all 463 repository tests passed.
- All 67 protected upstream artifacts from Phases 4–12 remain unmodified.

**PHASE 13 STEP 1 IS FORMALLY SEALED.**

**NO PHASE 13 STEP 2 EXECUTION IS AUTHORIZED BY THIS TASK.**
