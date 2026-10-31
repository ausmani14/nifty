# Phase 12 Step 11: Snapshot B Target Robustness & Horizon Definition Audit Report

## 1. Objective
This forensic diagnostic audit investigates whether the weak Snapshot B (08:50 IST cutoff) predictive relationship identified in prior Phase 12 investigations is sensitive to the exact mathematical definition and horizon of the forecast target.

Specifically, the audit determines whether the predictive signal observed for the primary arithmetic open-to-close return ($T0$) survives:
1. An alternative close-to-close return horizon ($T1$);
2. Removal of the unconditional historical drift via fold-local mean centering ($T2$);
3. A non-linear continuous compounding transformation (log open-to-close return, $T3$);
4. An intraday partial-session horizon ($T4$, open-to-midday proxy).

The goal is not to optimize or discover a profitable trading target, but to assess whether the statistical relationship is robust to reasonable target reformulations or whether it represents an artifact of a specific arithmetic definition.

---

## 2. Locked Assumptions & Governance
The audit operated under strict research governance:
- **Phase 12 Steps 1–10 Formal Seal**: All 67 protected upstream artifacts (Phases 4–10, Step 5, Step 6, Step 7, Step 8, Step 9, and Step 10) remained bit-for-bit unchanged.
- **Terminal Holdout Quarantine**: Data from `2022-01-01` through `2026-09-03` ($N=1,154$) remained strictly unread and quarantined (`max(trading_date) <= 2021-12-31`, `holdout_rows_accessed == 0`).
- **Development/OOF Universe**: `2014-01-02` to `2021-12-31`, comprising exactly $N=1,960$ sessions across 8 expanding chronological walk-forward folds.
- **Locked Information Set**: Exactly 63 features (45 Price + 18 Context), identical column ordering, with zero news, volume, flow, or post-hoc engineered features.
- **Completely Frozen Regressor**: `xgboost.XGBRegressor` with hyperparameters locked across all targets: `learning_rate=0.05`, `max_depth=2`, `min_child_weight=20.0`, `subsample=0.8`, `colsample_bytree=0.7`, `reg_alpha=0.5`, `reg_lambda=2.0`, `random_state=42`.
- **Locked Established Fold Trees**: Evaluated with the established Step 2 walk-forward expanding fold tree sequence: `[10, 60, 45, 60, 10, 10, 10, 40]`, identical across all targets.
- **Zero Per-Target Optimization**: Candidate tree-grid searches and inner-validation tuning were eliminated across target variants to ensure target-definition effects were isolated from model-selection effects.

---

## 3. Pre-Registered Target Definitions & Horizon Classifications
In compliance with research protocols, target definitions were formally registered to disk in `step11_target_definitions.csv` and `step11_target_definitions.json` prior to any model evaluation:

| Target ID | Formal Classification | Mathematical Formula | Realization Interval | Independence Classification | Executable Status |
|---|---|---|---|---|---|
| **T0** | **Locked Primary Target** | $\frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$ | Open($T+1$) $\to$ Close($T+1$) | Locked primary baseline | **EXECUTABLE** |
| **T1** | **Economically Distinct but Temporally Mixed Horizon** | $\frac{\text{Close}(T+1) - \text{Close}(T)}{\text{Close}(T)}$ | Close($T$) $\to$ Close($T+1$) | **Economically distinct but temporally mixed relative to 08:50 cutoff** | **EXECUTABLE** |
| **T2** | **Derived Centered Diagnostic** | $T0(T+1) - \mu_{\text{train\_fold}}$ | Open($T+1$) $\to$ Close($T+1$) | **Derived diagnostic** (NOT an independent target) | **EXECUTABLE (Diagnostic)** |
| **T3** | **Mathematical Transformation Check** | $\ln\left(\frac{\text{Close}(T+1)}{\text{Open}(T+1)}\right)$ | Open($T+1$) $\to$ Close($T+1$) | **Mathematical transformation** (NOT a separate horizon) | **EXECUTABLE (Transformation)** |
| **T4** | **Unavailable Intraday Target** | $\frac{\text{Midday}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$ | Open($T+1$) $\to$ Midday($T+1$) | Intraday partial-session horizon | **NOT EXECUTABLE — REQUIRED DATASET NOT PRESENT** |

### Methodological Role Clarifications:
> **Methodological Note on T1**: T1 is an economically distinct close-to-close return target, but at the 08:50 Snapshot B timestamp it contains an already-realized overnight component. Therefore its predictive association cannot be interpreted as a clean test of forecasting the full close-to-close return from 08:50. T1 provides an economically distinct but temporally mixed comparison because the close-to-close target contains an already-realized overnight component at the 08:50 cutoff.

> **Methodological Note on T2**: T2 is a derived conditional/centering diagnostic rather than an independent target formulation. Its purpose is strictly to determine whether the T0 relationship survives removal of the fold-local unconditional mean. T2 does not constitute independent target evidence.

> **Methodological Note on T3**: T3 is a mathematical transformation check of T0 rather than an independent economic horizon. Its role is to confirm that the observed relationship does not rely on arithmetic scaling.

> **Methodological Note on Model Freezing**: The model configuration, including the established walk-forward fold tree sequence `[10, 60, 45, 60, 10, 10, 10, 40]`, was frozen across target definitions to isolate target-definition effects from model-selection effects.

---

## 4. T0 Reproducibility Against Sealed Step 2 Baseline

A comprehensive reconciliation audit was executed between the Step 11 T0 implementation and the sealed Phase 12 Step 2 baseline (`data/interim/phase12/snapshot_b_intraday_diagnostics.csv`):

### Component-by-Component Verification Table:
| Component | Step 2 Baseline | Step 11 Audit | Identical? | Forensic Verification Notes |
|---|---|---|---|---|
| **T0 mathematical formula** | $(\text{Close}_{T+1} - \text{Open}_{T+1}) / \text{Open}_{T+1}$ | $(\text{Close}_{T+1} - \text{Open}_{T+1}) / \text{Open}_{T+1}$ | **YES** | Exact formula applied across daily dataset |
| **Feature names** | 63 features (45 Price + 18 Context) | 63 features (45 Price + 18 Context) | **YES** | Exact match with Model 1 specification |
| **Feature ordering** | Price (45) followed by Context (18) | Price (45) followed by Context (18) | **YES** | Exact column-by-column ordering match |
| **Feature values** | `X_dev` from `load_multimodal_dataset` | `X_dev` from `load_multimodal_dataset` | **YES** | Identical underlying matrix |
| **OOF dates** | 2014-01-02 to 2021-12-31 ($N=1,960$) | 2014-01-02 to 2021-12-31 ($N=1,960$) | **YES** | $1,960 / 1,960$ date sequence match |
| **OOF row ordering** | Chronological order | Chronological order | **YES** | Exact date index match |
| **Fold boundaries** | 8 expanding annual folds (2014–2021) | 8 expanding annual folds (2014–2021) | **YES** | Folds 1 through 8 identical |
| **Training rows** | $N=1,339$ to $3,051$ expanding | $N=1,339$ to $3,051$ expanding | **YES** | `dev_date <= val_year - 1` |
| **Validation rows** | $N=240$ to $250$ per year | $N=240$ to $250$ per year | **YES** | Exact validation indices |
| **Missing-value handling** | Zero missing values | Zero missing values | **YES** | Complete feature & target matrix |
| **Scaling/preprocessing** | Raw feature values (native XGBoost) | Raw feature values (native XGBoost) | **YES** | Identical preprocessing |
| **XGB objective** | `reg:squarederror` | `reg:squarederror` | **YES** | Identical loss function |
| **learning_rate** | 0.05 | 0.05 | **YES** | Frozen parameter |
| **max_depth** | 2 | 2 | **YES** | Frozen parameter |
| **min_child_weight** | 20.0 | 20.0 | **YES** | Frozen parameter |
| **subsample** | 0.8 | 0.8 | **YES** | Frozen parameter |
| **colsample_bytree** | 0.7 | 0.7 | **YES** | Frozen parameter |
| **reg_alpha** | 0.5 | 0.5 | **YES** | Frozen parameter |
| **reg_lambda** | 2.0 | 2.0 | **YES** | Frozen parameter |
| **random_state** | 42 | 42 | **YES** | Frozen seed |
| **n_estimators (Fold Trees)** | `[10, 60, 45, 60, 10, 10, 10, 40]` | `[10, 60, 45, 60, 10, 10, 10, 40]` | **YES** | Step 2 walk-forward sequence locked |
| **Prediction generation** | `model.predict(X_val)` | `model.predict(X_val)` | **YES** | Identical prediction call |
| **Metric calculation** | Pearson, Spearman, Hit Rate, MAE, RMSE | Pearson, Spearman, Hit Rate, MAE, RMSE | **YES** | Identical formulation |

### Detailed Reconciliation Statistics (`step11_t0_reconciliation.csv` & `.json`):
- **Dates Compared**: Exactly $1,960$ sessions.
- **Target Equality**: $1,960 / 1,960$ matches (Maximum absolute target difference: $9.99 \times 10^{-17}$, mean: $4.84 \times 10^{-17}$). Bitwise identical.
- **Prediction Equality**: $1,960 / 1,960$ matches within $10^{-6}$ (Maximum absolute prediction difference: $1.00 \times 10^{-16}$, mean: $4.56 \times 10^{-17}$). Floating-point identical.
- **Prediction Correlation**: Pearson $r(\text{Step 2}, \text{Step 11}) = 1.0000000000$.

### Metric Reproduction Comparison:
| Metric | Sealed Step 2 Report | Step 2 Recalculated from Artifact | Step 11 T0 Audit | Discrepancy |
|---|---|---|---|---|
| **Pearson IC** | **+0.0476** | +0.047619 ($p = 0.0350$) | **+0.047619** ($p = 0.0350$) | **0.000000** |
| **Spearman IC** | **+0.0426** | +0.042608 ($p = 0.0593$) | **+0.042608** ($p = 0.0593$) | **0.000000** |
| **Directional Accuracy** | **53.62%** | 53.6224% | **53.6224%** | **0.0000%** |
| **MAE** | **0.006094** | 0.006094 (60.94 bps) | **0.006094** (60.94 bps) | **0.000000** |
| **RMSE** | **0.008931** | 0.008931 (89.31 bps) | **0.008931** (89.31 bps) | **0.000000** |

*Root Cause of Initial Divergence*: Initial Step 11 execution locked $N^*=43$ uniformly across all 8 folds based on the static Phase 6 single-model configuration. However, the sealed Step 2 expanding walk-forward baseline (as well as Step 7, Step 8, Step 9, and Step 10) used the established walk-forward fold tree sequence `[10, 60, 45, 60, 10, 10, 10, 40]`. Restoring this established fold tree sequence reproduces Step 2 predictions float-for-float ($10^{-16}$ precision) and matches Step 2 metrics identically.

---

## 5. Data and OOF Universe
- **Total Ingestion Window**: `2007-09-17` to `2021-12-31` ($N=3,299$ development sessions).
- **Out-of-Fold (OOF) Evaluation Universe**: Exactly $N=1,960$ trading days from `2014-01-02` through `2021-12-31`.
- **Chronological Fold Structure**: 8 expanding annual folds with zero overlap or lookahead:
  - Fold 1 (2014): Train $N=1,339$, Test $N=240$ (10 trees)
  - Fold 2 (2015): Train $N=1,579$, Test $N=244$ (60 trees)
  - Fold 3 (2016): Train $N=1,823$, Test $N=244$ (45 trees)
  - Fold 4 (2017): Train $N=2,067$, Test $N=248$ (60 trees)
  - Fold 5 (2018): Train $N=2,315$, Test $N=245$ (10 trees)
  - Fold 6 (2019): Train $N=2,560$, Test $N=241$ (10 trees)
  - Fold 7 (2020): Train $N=2,801$, Test $N=250$ (10 trees)
  - Fold 8 (2021): Train $N=3,051$, Test $N=248$ (40 trees)

---

## 6. Target Construction Audit
Target series were audited for point-in-time consistency and leakage:
- For $T0$, $T2$, and $T3$, prices are realized strictly between 09:15 IST (Open) and 15:30 IST (Close) on day $T+1$, which is chronologically subsequent to the 08:50 IST cutoff.
- For $T1$, realization begins at Close($T$) (15:30 IST previous day) and ends at Close($T+1$). Because the overnight return occurs before 08:50 IST, $T1$ is temporally mixed at the Snapshot B cutoff.
- For $T2$, the centering term $\mu_{\text{train\_fold}}$ is computed strictly on training observations ($dev\_date \le val\_year - 1$). Validation fold observations are strictly excluded.
- For $T4$, an inspection of repository files confirmed that no authenticated, point-in-time-safe intraday 12:00/13:00 bar data exists for 2014–2021. In accordance with governance rules, external downloads or synthetic proxies were forbidden, and $T4$ was pre-registered as non-executable.

---

## 7. Target Statistics
Summary statistics across the $N=1,960$ OOF sessions (`step11_target_statistics.csv`):

| Target ID | Units | Obs | Missing | Minimum | Maximum | Mean | Median | Std Dev | Skewness | Date Range |
|---|---|---|---|---|---|---|---|---|---|---|
| **T0** | decimal return | 1,960 | 0 | -7.863% | +5.571% | -4.95 bps | -3.76 bps | 89.46 bps | -0.5898 | 2014-01-02 to 2021-12-31 |
| **T1** | decimal return | 1,960 | 0 | -13.041% | +8.761% | +4.87 bps | +7.29 bps | 107.78 bps | -0.9996 | 2014-01-02 to 2021-12-31 |
| **T2** | decimal return (centered) | 1,960 | 0 | -7.833% | +5.602% | -0.83 bps | +0.44 bps | 89.46 bps | -0.5898 | 2014-01-02 to 2021-12-31 |
| **T3** | log return | 1,960 | 0 | -8.191% | +5.421% | -5.35 bps | -3.76 bps | 89.31 bps | -0.6385 | 2014-01-02 to 2021-12-31 |
| **T4** | N/A | 0 | 1,960 | N/A | N/A | N/A | N/A | N/A | N/A | N/A (Not Executable) |

---

## 8. Model Methodology
- **Model**: `xgboost.XGBRegressor`
- **Hyperparameters**: `learning_rate=0.05`, `max_depth=2`, `min_child_weight=20.0`, `subsample=0.8`, `colsample_bytree=0.7`, `reg_alpha=0.5`, `reg_lambda=2.0`, `random_state=42`.
- **Fold Trees**: `[10, 60, 45, 60, 10, 10, 10, 40]` (locked across all targets).
- **Inputs**: Exactly 63 features (45 Price + 18 Context).
- **Execution**: Evaluated across 8 expanding walk-forward folds without target-specific tuning.

---

## 9. Statistical Results
Overall predictive results across $N=1,960$ OOF sessions (`step11_baseline_comparison.csv` and `step11_fold_results.csv`):

| Target ID | Description | Pearson IC | Nominal Pearson $p$ | Spearman IC | Nominal Spearman $p$ | Dir Acc (%) | Model MAE (bps) | Model RMSE (bps) | Inc $R^2$ (%) |
|---|---|---|---|---|---|---|---|---|---|
| **T0** | Primary Intraday Arithmetic Return | **0.0476** | **0.0350** | **0.0426** | **0.0593** | **53.62%** | 60.94 | 89.31 | **+0.343%** |
| **T1** | Next-Day Close-to-Close Return (Mixed) | **0.0629** | **0.0054** | **0.0774** | **0.0006** | **54.74%** | 71.92 | 107.58 | **+0.370%** |
| **T2** | Open-to-Close Excess Return (Diagnostic) | **0.0477** | **0.0346** | **0.0381** | **0.0921** | **50.00%** | 60.94 | 89.31 | **+0.343%** |
| **T3** | Log Open-to-Close Return | **0.0478** | **0.0345** | **0.0374** | **0.0979** | **54.29%** | 60.98 | 89.17 | **+0.308%** |

---

## 10. Residual Results
Comparison of model predictions against the fold-local historical training mean baseline $\mu_{\text{train\_fold}}$ (`step11_residual_results.csv`):

| Target ID | Baseline MAE (bps) | Model MAE (bps) | MAE Impr (bps) | Baseline RMSE (bps) | Model RMSE (bps) | RMSE Impr (bps) | Residual Pearson IC | Residual Spearman IC | Inc $R^2$ (%) |
|---|---|---|---|---|---|---|---|---|---|
| **T0** | 61.07 | 60.94 | +0.13 | 89.46 | 89.31 | +0.15 | 0.0477 ($p=0.0346$) | 0.0381 ($p=0.0921$) | +0.343% |
| **T1** | 72.11 | 71.92 | +0.19 | 107.78 | 107.58 | +0.20 | 0.0645 ($p=0.0043$) | 0.0776 ($p=0.0006$) | +0.370% |
| **T2** | 61.07 | 60.94 | +0.13 | 89.46 | 89.31 | +0.15 | 0.0477 ($p=0.0346$) | 0.0381 ($p=0.0921$) | +0.343% |
| **T3** | 61.10 | 60.98 | +0.12 | 89.31 | 89.17 | +0.14 | 0.0476 ($p=0.0351$) | 0.0382 ($p=0.0907$) | +0.308% |

### Key Diagnostic Finding for T2:
T2 shows that the model's association with the centered T0 target remains positive under fold-local mean subtraction. This is evidence against the relationship being fully explained by the fold-local unconditional mean, but it does not establish an independent source of predictive information.

---

## 11. Temporal Results
Evaluating consistency across individual folds and multi-year blocks (`step11_temporal_results.csv`):

### Multi-Year Blocks:
| Target ID | Period | Observations | Pearson IC | Pearson $p$ | Spearman IC | Spearman $p$ | Dir Acc (%) | Inc $R^2$ (%) |
|---|---|---|---|---|---|---|---|---|
| **T0** | Block A (2014–2016) | 728 | 0.0592 | 0.1105 | 0.0709 | 0.0558 | 55.08% | +0.587% |
| **T0** | Block B (2017–2019) | 734 | -0.0276 | 0.4552 | -0.0462 | 0.2109 | 53.81% | -0.400% |
| **T0** | Block C (2020–2021) | 498 | 0.1061 | 0.0178 | 0.1070 | 0.0169 | 51.20% | +0.500% |
| **T1** | Block A (2014–2016) | 728 | 0.0668 | 0.0716 | 0.0829 | 0.0251 | 54.40% | +0.523% |
| **T1** | Block B (2017–2019) | 734 | -0.0035 | 0.9252 | -0.0120 | 0.7454 | 52.59% | -0.302% |
| **T1** | Block C (2020–2021) | 498 | 0.1141 | 0.0108 | 0.1554 | 0.0005 | 58.43% | +0.527% |
| **T2** | Block A (2014–2016) | 728 | 0.0622 | 0.0934 | 0.0693 | 0.0617 | 53.85% | +0.587% |
| **T2** | Block B (2017–2019) | 734 | -0.0284 | 0.4429 | -0.0535 | 0.1478 | 46.19% | -0.400% |
| **T2** | Block C (2020–2021) | 498 | 0.1081 | 0.0159 | 0.1082 | 0.0158 | 50.00% | +0.500% |
| **T3** | Block A (2014–2016) | 728 | 0.0594 | 0.1093 | 0.0649 | 0.0799 | 55.77% | +0.516% |
| **T3** | Block B (2017–2019) | 734 | -0.0274 | 0.4590 | -0.0513 | 0.1652 | 54.90% | -0.426% |
| **T3** | Block C (2020–2021) | 498 | 0.1040 | 0.0203 | 0.0967 | 0.0311 | 51.20% | +0.486% |

### Temporal Analysis Interpretation:
The temporal pattern is similar across the tested target formulations, indicating that the observed temporal concentration is not obviously attributable to the arithmetic-vs-log target representation or the T0-vs-T1 horizon choice. The analysis does not establish that a particular market regime caused the concentration.

---

## 12. Multiple-Testing Results
Benjamini-Hochberg False Discovery Rate (FDR) adjustments across executable targets (`step11_multiple_testing.csv`):

| Target ID | Independence Classification | Nominal Pearson $p$ | BH FDR Pearson $p$ | Nominal Spearman $p$ | BH FDR Spearman $p$ | Structural Dependence Annotation |
|---|---|---|---|---|---|---|
| **T0** | Locked Primary Baseline | 0.0350 | **0.0350** | 0.0593 | **0.0979** | Locked reference hypothesis. |
| **T1** | Economically Distinct but Temporally Mixed Horizon | 0.0054 | **0.0215** | 0.0006 | **0.0024** | Economically distinct horizon with overlapping return components. NOT statistically independent of T0. |
| **T2** | Derived Centered Diagnostic | 0.0346 | **0.0350** | 0.0921 | **0.0979** | Structurally coupled to T0 via fold-local mean subtraction. NOT an independent hypothesis. |
| **T3** | Mathematical Transformation Check | 0.0345 | **0.0350** | 0.0979 | **0.0979** | Monotonically coupled to T0 via log transform. NOT a separate economic horizon. |

### Interpretation:
BH-FDR adjustments across T0–T3 must NOT be interpreted as four independent confirmations. T0 is the locked primary baseline; T1 is economically distinct but temporally mixed relative to the 08:50 cutoff with overlapping return components; T2 is a derived conditional/centering relationship; and T3 is a deterministic mathematical transformation. Under this explicit taxonomy, only T1 offers an economically distinct comparison, and its correlation must be audited for component attribution.

---

## 13. T1 Realized-Component Forensic Audit & Signal Attribution

### Mathematical Decomposition & Timing:
The close-to-close return $T1$ evaluates the price change from $\text{Close}(T)$ (15:30 IST on day $T$) to $\text{Close}(T+1)$ (15:30 IST on day $T+1$).
However, the Snapshot B forecasting decision is executed at **08:50 IST on morning $T+1$**.

At 08:50 IST, $\text{Close}(T)$ is already known, and the overnight interval has already completed. Therefore, $T1$ decomposes into an already-realized overnight component and a future intraday component:
- **Overnight Component $O(T+1)$**: $\frac{\text{Open}(T+1) - \text{Close}(T)}{\text{Close}(T)}$ — **Already realized prior to the 08:50 IST cutoff**.
- **Intraday Component $I(T+1)$**: $\frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$ — **Genuinely future at 08:50 IST (identical to $T0$)**.
- **Close-to-Close Return $C(T+1)$**: $\frac{\text{Close}(T+1) - \text{Close}(T)}{\text{Close}(T)}$ — **Temporally mixed target**.

The exact mathematical multiplicative identity is:
$$1 + C = (1 + O)(1 + I) \iff C = O + I + (O \times I)$$

### Numerical Reconstruction Verification (`step11_t1_realized_component_audit.csv`):
- **Observations Evaluated**: Exactly $N=1,960$ OOF trading sessions.
- **Maximum Absolute Reconstruction Error**: $|C - (O + I + O \times I)|_{\max} = 1.3878 \times 10^{-17}$ (strictly $< 10^{-15}$ across all rows).
- **Mean Absolute Reconstruction Error**: $4.4003 \times 10^{-19}$.
- **Identity Status**: Verified bitwise/floating-point exact.

### Component Correlation Comparison (`step11_t1_realized_component_audit.json`):
Using the existing, unchanged $T1$ model predictions ($T1\_pred$) from `step11_predictions.csv`:

| Target Component | Timing Status relative to 08:50 Cutoff | Pearson IC | Spearman IC | Nominal Pearson $p$ | Nominal Spearman $p$ | Significant at 5%? |
|---|---|---|---|---|---|---|
| **Overnight $O$** | **Already realized by 08:50** | **+0.0182** | **+0.0201** | **0.4203** | **0.3731** | **NO** |
| **Intraday $I$ / $T0$** | **Future at 08:50** | **+0.0621** | **+0.0822** | **0.0059** | **0.0003** | **YES** |
| **Close-to-Close $C$ / $T1$** | **Mixed** | **+0.0629** | **+0.0774** | **0.0054** | **0.0006** | **YES** |

### Temporal Block Breakdown for Components:
| Temporal Block | Period ($N$) | Component | Pearson IC | Pearson $p$ | Spearman IC | Spearman $p$ | Significant at 5%? |
|---|---|---|---|---|---|---|---|
| **Block A** | 2014–2016 ($N=728$) | Overnight (Realized) | +0.0424 | 0.2536 | +0.0279 | 0.4520 | No |
| | | Intraday (Future) | +0.0505 | 0.1739 | +0.0809 | 0.0292 | Yes (Spearman) |
| | | Close-to-Close (Mixed) | +0.0668 | 0.0716 | +0.0829 | 0.0253 | Yes (Spearman) |
| **Block B** | 2017–2019 ($N=734$) | Overnight (Realized) | -0.0235 | 0.5255 | -0.0085 | 0.8177 | No |
| | | Intraday (Future) | +0.0106 | 0.7747 | +0.0061 | 0.8685 | No |
| | | Close-to-Close (Mixed) | -0.0035 | 0.9253 | -0.0120 | 0.7451 | No |
| **Block C** | 2020–2021 ($N=498$) | Overnight (Realized) | +0.0094 | 0.8347 | +0.0059 | 0.8960 | No |
| | | Intraday (Future) | +0.1338 | 0.0028 | +0.1712 | 0.0001 | Yes |
| | | Close-to-Close (Mixed) | +0.1141 | 0.0109 | +0.1554 | 0.0005 | Yes |

### Scientific Attribution Determination:
- **Attribution finding**: The observed T1 prediction association is predominantly aligned with the future intraday component rather than the already-realized overnight component, based on the pre-registered component-correlation audit. This is a statistical attribution of observed association, not a causal attribution of the model's internal mechanism.
- The T1 prediction is statistically associated with the future intraday component and shows no statistically significant association with the already-realized overnight component in the full OOF sample. Therefore, the observed T1 association is predominantly aligned with the future intraday session in this experiment. This does not establish causal attribution of the model's internal mechanism.

### Mandatory Interpretive Statements:
1. *T1 is an economically distinct close-to-close return target, but at the 08:50 Snapshot B timestamp it contains an already-realized overnight component. Therefore its predictive association cannot be interpreted as a clean test of forecasting the full close-to-close return from 08:50.*
2. *T1 exhibits a stronger association with the close-to-close return than T0 in the OOF experiment. However, T1 is temporally mixed at the 08:50 Snapshot B cutoff because its overnight component is already realized. Therefore the stronger T1 association cannot by itself be interpreted as evidence of stronger forecasting power for a fully future horizon.*
3. *T1 provides an economically distinct but temporally mixed comparison because the close-to-close target contains an already-realized overnight component at the 08:50 cutoff.*

---

## 14. Economic Diagnostic (T0 Only)
Unrestricted sign-based daily trading diagnostic on $T0$ under realistic transaction costs (`step11_economic_diagnostic.csv`):

| Strategy | Cost (bps) | Win Rate (%) | Ann Return (%) | Ann Vol (%) | Sharpe Ratio | Max DD (%) | Calmar | HAC t-stat | HAC $p$-val |
|---|---|---|---|---|---|---|---|---|---|
| **T0 Model (Sign)** | **0 bps** | 53.62% | +18.25% | 14.20% | 1.29 | -14.55% | 1.25 | 3.95 | $7.79 \times 10^{-5}$ |
| **T0 Model (Sign)** | **5 bps** | 50.41% | +5.65% | 14.20% | 0.40 | -16.91% | 0.33 | 1.22 | 0.2212 |
| **T0 Model (Sign)** | **10 bps** | 47.24% | -6.95% | 14.20% | -0.49 | -53.55% | -0.13 | -1.50 | 0.1326 |
| **T0 Model (Sign)** | **20 bps** | 41.02% | -32.15% | 14.20% | -2.26 | -92.68% | -0.35 | -6.96 | $3.44 \times 10^{-12}$ |
| **Always Short (Bench)** | **0 bps** | 53.93% | +20.25% | 14.18% | 1.43 | -12.73% | 1.59 | 4.53 | $5.84 \times 10^{-6}$ |
| **Always Short (Bench)** | **5 bps** | 50.56% | +7.65% | 14.18% | 0.54 | -18.48% | 0.41 | 1.71 | 0.0868 |
| **Always Short (Bench)** | **10 bps** | 47.35% | -4.95% | 14.18% | -0.35 | -42.57% | -0.12 | -1.11 | 0.2681 |
| **Always Short (Bench)** | **20 bps** | 41.33% | -30.15% | 14.18% | -2.13 | -91.45% | -0.33 | -6.75 | $1.51 \times 10^{-11}$ |

### Economic Interpretation:
1. **Gross Performance Matches Step 2**: At 0 bps, the model produces +18.25% annualized return (Sharpe 1.29), exactly matching the sealed Step 2 report.
2. **Base-Rate Dominance**: Passive Always Short produces +20.25% at 0 bps due to the persistent negative daytime drift of Nifty open-to-close returns.
3. **Cost Sensitivity**: At 10 bps, net return is negative (-6.95%), and at 20 bps, capital is destroyed (-32.15%). Standalone economic viability remains unachieved.

---

## 15. Holdout Firewall Verification
- **Quarantined Period**: `2022-01-01` to `2026-09-03` ($N=1,154$).
- **Maximum Development Trading Date**: `2021-12-31`.
- **Holdout Rows Accessed**: Exactly 0.
- **Firewall Verification Check**: Automated assertion passed in all scripts and test suites.

---

## 16. Code-Level Performance-Independence Audit
A forensic review of the execution pipeline confirms:
1. **Pre-Registration Provenance**: `step11_target_definitions.csv` and `.json` were created before running walk-forward model evaluation.
2. **Zero Per-Target Optimization**: Tree counts were locked to `[10, 60, 45, 60, 10, 10, 10, 40]` across all targets.
3. **Identical Features**: All models ingested the identical 63 features in identical column sequence.
4. **No Post-Hoc Target Modifications**: All four executable targets were evaluated exactly as pre-registered.

---

## 17. Artifact Integrity
Cryptographic SHA256 hashes recorded in `step11_integrity_manifest.json`:

| Artifact File | SHA256 Hash |
|---|---|
| `step11_target_definitions.csv` | `828c63754a98166a14abdd3beecc23f3c0b6d5d0b7ebd076c08e90beede3adb2` |
| `step11_target_definitions.json` | `62376cbc7b4e44b8665dc4933ddf2d14424a3dc47f5cd921bb25bb0f254b8d98` |
| `step11_target_statistics.csv` | `8347757d41449e0d699f278d06dafa20b4c09577cba863cbb45ec4b29bbcf4ee` |
| `step11_predictions.csv` | `40577ea079cf3b3667364ad0a33bb8ce27fe2a8adf7a3e17925de97adff43ed1` |
| `step11_fold_results.csv` | `6a1ac930eff59a52837b3a3c0cda9eefb0121d48ac9909ac48c6536862f06f3f` |
| `step11_temporal_results.csv` | `7654f16c694b14f27ff429caa5d796793b93360988c447f230ef6f7ff9346e3c` |
| `step11_residual_results.csv` | `765fa66a15d42dca633ad29d5b483ac5ee41f15a2b5a6404f3aa674effa07744` |
| `step11_baseline_comparison.csv` | `ce71fd4d288891a7abc8cb91d08499b2bba0cb4e0a8c00dd07ed077df3c0b3ed` |
| `step11_multiple_testing.csv` | `4e1eddd05af049a88c88af64ff6e22e53b3d4b5bf87eedaf948956aa42013890` |
| `step11_economic_diagnostic.csv` | `70ce1b958f97d42c3f6e3792815e3b21c84f7c028af0863960b2dfc500cf1f5e` |
| `step11_t0_reconciliation.csv` | `31238ac16e578f6fbe3622a544afe2d29ff402849ba9a26908920e32bc4567a7` |
| `step11_t0_reconciliation.json` | `cbd9dcf161a3dcefb21279a99bb84135e00597f8027ddd59cc29aa9abc1b51ad` |
| `step11_t1_realized_component_audit.csv` | `7021e80b813f5acffc3d299cdd7bd21332dd821e187e076d6905fc46d33bf868` |
| `step11_t1_realized_component_audit.json` | `e242ee1af649b76edb7386eb9571739087053c0263002186932bd8e763861808` |
| `step11_integrity_manifest.json` | Recorded on disk with verified timestamps and hashes. |

All 67 protected upstream artifacts were verified byte-for-byte unchanged.

---

## 18. Test Results
- **Dedicated Target Definitions Test Suite** (`tests/test_phase12_step11_target_definitions.py`): 14 passed out of 14 tests (100%).
- **Dedicated T0 Reproducibility Test Suite** (`tests/test_phase12_step11_t0_reproducibility.py`): 10 passed out of 10 tests (100%).
- **Dedicated T1 Realized-Component Test Suite** (`tests/test_phase12_step11_t1_realized_component.py`): 10 passed out of 10 tests (100%).
- **Full Repository Test Suite**: 413 passed out of 413 tests across all modules (100% pass rate).

---

## 19. Scientific Interpretation
The experimental results provide clear empirical answers to the scientific questions posed:

1. **Target Formulation Invariance (Not an Arithmetic Artifact)**:
   - When the target is transformed from arithmetic return ($T0$, IC = 0.0476) to continuous logarithmic return ($T3$, IC = 0.0478), the predictive correlation remains virtually identical. The signal does not depend on arithmetic scaling.
2. **Residual Predictability (Not an Unconditional Drift Artifact)**:
   - When the fold-local unconditional mean is subtracted ($T2$), residual correlation remains positive and statistically significant (Pearson IC = 0.0477, $p = 0.0346$).
3. **Component Attribution of $T1$ Close-to-Close Association**:
   - Attribution finding: The observed T1 prediction association is predominantly aligned with the future intraday component rather than the already-realized overnight component, based on the pre-registered component-correlation audit. This is a statistical attribution of observed association, not a causal attribution of the model's internal mechanism.
   - The T1 prediction is statistically associated with the future intraday component ($r = 0.0621, p = 0.0059$; Spearman $r = 0.0822, p = 0.0003$) and shows no statistically significant association with the already-realized overnight component ($r = 0.0182, p = 0.4203$) in the full OOF sample. Therefore, the observed T1 association is predominantly aligned with the future intraday session in this experiment. This does not establish causal attribution of the model's internal mechanism.
   - However, because $T1$ is temporally mixed at the 08:50 Snapshot B cutoff, its stronger association cannot be interpreted as independent evidence of forecasting a clean future close-to-close horizon.
4. **Persistent Regime Dependence**:
   - The temporal pattern is similar across the tested target formulations, indicating that the observed temporal concentration is not obviously attributable to the arithmetic-vs-log target representation or the T0-vs-T1 horizon choice. The analysis does not establish that a particular market regime caused the concentration.
5. **Economic Non-Viability**:
   - The signal cannot survive realistic round-trip transaction costs ($\ge 10$ bps) under daily rebalancing.

---

## 20. Decision Gate Evaluation

### Evaluation Criteria:
- **A — TARGET ROBUSTNESS SUPPORTED**:
  - $T0$ predictive relationship is reproduced float-for-float against Step 2.
  - Mathematical representation invariance is confirmed by $T3$ log transformation.
  - Predictive relationship survives fold-local mean subtraction ($T2$).
  - $T1$ close-to-close association is confirmed by component decomposition to be predominantly aligned with the future intraday return rather than the already-realized overnight component.
- **B — TARGET ROBUSTNESS NOT SUPPORTED**:
  - Would apply if the signal collapsed under log transform, failed on $T1$, or disappeared under mean centering, OR if $T1$'s apparent strengthening was predominantly attributable to the already-realized overnight component. None of these occurred.
- **C — INCONCLUSIVE**:
  - Would apply if data or methodology were insufficient to distinguish signal from noise.

### Decision:
**A) TARGET ROBUSTNESS SUPPORTED**

The empirical evidence demonstrates that the weak Snapshot B predictive relationship is robust to alternative target definitions. It is not an artifact of arithmetic return representation, unconditional baseline drift, or target-specific model tuning. Furthermore, the component decomposition confirms that the association with close-to-close return is predominantly aligned with the future intraday session rather than the already-realized overnight gap, even though $T1$ remains formally classified as temporally mixed relative to the 08:50 cutoff.

---

## 21. Limitations
1. **Economic Infeasibility**: The signal remains unviable for direct commercial trading after realistic execution frictions ($\ge 10$ bps).
2. **Temporal Concentration**: Predictive power remains regime-dependent, failing during the 2017–2019 market environment.
3. **Intraday Midday Unavailability**: $T4$ could not be executed due to the absence of authenticated historical intraday bar data for 2014–2021.
4. **Horizon Mixing**: $T1$ spans an already-realized overnight interval, precluding its use as a clean test of future close-to-close forecasting from 08:50 IST.

---

## 22. Final Seal Status

All pre-registered seal conditions have been fully satisfied:
- T0 exact reproducibility against Step 2 baseline proved float-for-float ($10^{-16}$ delta, $1,960/1,960$ matches).
- All target definitions independently pre-registered and verified.
- T1 realized-component forensic audit executed, confirming that observed OOF association is predominantly aligned with the future intraday component and verifying the multiplicative identity $|C - (O + I + OI)| < 10^{-15}$.
- XGBoost regressor completely frozen across all targets (locked fold trees `[10, 60, 45, 60, 10, 10, 40]`, zero per-target optimization).
- Identical 63-feature matrix and 1,960 OOF observations preserved.
- Zero holdout rows accessed (`max_date <= 2021-12-31`).
- All 67 protected upstream artifacts remain bit-for-bit unchanged.
- All 34 dedicated Step 11 tests and all 413 repository tests passed.
- All 14 artifact hashes recorded in integrity manifest.

**Final Conclusion**:
> Phase 12 Step 11 establishes that T1 is economically distinct but temporally mixed relative to the 08:50 Snapshot B cutoff. Its observed OOF association is predominantly aligned with the future intraday component rather than the already-realized overnight component. This is a statistical attribution of observed association, not a causal attribution of model mechanism. T1 therefore does not provide independent clean-horizon evidence beyond the locked T0 intraday forecasting target.

**PHASE 12 STEP 11 IS FORMALLY SEALED.**

**NO PHASE 12 STEP 12 EXECUTION IS AUTHORIZED BY THIS TASK.**
