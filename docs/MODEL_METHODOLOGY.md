# MODELING METHODOLOGY & WALK-FORWARD VALIDATION

**Document:** `docs/MODEL_METHODOLOGY.md`  
**Phase:** Phase 6 — XGBoost Direction & Return Models  
**Asset:** NIFTY 50 Index (`^NSEI` / `NIFTY 50`)  
**Input Features:** [`data/features/nifty50_features_clean.csv`](../data/features/nifty50_features_clean.csv) (45 price features, 4,454 sessions)  
**Input Targets:** [`data/targets/nifty50_targets_snapshot_a.csv`](../data/targets/nifty50_targets_snapshot_a.csv) (Phase 5 Method A, \(k=0.35, w=20\))  
**Development Window:** `2008-07-08` to `2021-12-31` (3,299 supervised sessions)  
**Holdout Window:** `2022-01-01` to `2026-09-03` (1,154 supervised sessions, strictly audited)  
**Production Artifacts:** `models/v1/classifier/` and `models/v1/regressor/`  
**Configuration Registry:** [`configs/models.yaml`](../configs/models.yaml)  

---

## 1. Executive Summary & Modeling Objectives

Phase 6 implements the core machine learning predictive layer for NIFTY AI. Directional classification and return regression are uncoupled into dedicated XGBoost estimators, each optimized strictly within an expanding-window chronological walk-forward framework on the historical development partition.

### Key Outputs Produced for Every Eligible Session
1. **Directional Classifier:** Predicts the 3-class probability simplex \(\mathbf{p} = [P(\text{DOWN}), P(\text{SIDEWAYS}), P(\text{UP})]\), categorical class assignment \(\hat{y} = \arg\max \mathbf{p}\), and optionally calibrated probabilities (note: raw tree probabilities remain primary in production, as proper CV calibration worsened log loss and Brier score; calibration remains an optional diagnostic artifact only).
2. **Return Regressor:** Predicts next-session percentage close-to-close return \(\hat{r}_{T+1}\) and derived next-session closing price:
   $$\hat{C}_{T+1} = \text{Close}_T \times (1 + \hat{r}_{T+1})$$

---

## 2. Canonical Snapshot Naming Convention & Alignment Contracts

To maintain complete clarity across domestic market close and morning execution, NIFTY AI operates on two distinct prediction snapshots:

```
Trading Session T                                           Trading Session T + 1
─────────────────────────────────────────────────────────────────────────────────────────────
[09:15 - 15:30 IST]         15:40 IST                        08:50 IST       [09:15 - 15:30 IST]
Session T                   Snapshot A                       Snapshot B      Session T+1
                            Cutoff: 15:30 IST (Day T)        Cutoff: 08:50 IST (Day T+1)
                            Predicts: Session T+1            Predicts: Session T+1
```

### Snapshot A (`SNAPSHOT_1540`)
- **Execution:** `15:40:00 IST` on Session \( T \) (post-close).
- **Information Cutoff:** Strictly `15:30:00 IST` on Session \( T \).
- **Input Features:** Computed from completed daily bar of Session \( T \) and trailing history.
- **Target Outcome:** Session \( T+1 \) close-to-close return (\( \text{Close}_{T+1} / \text{Close}_T - 1 \)).
- **Join Key:** `features.trading_date == targets.trading_date` (Session \( T \)).

### Snapshot B (`SNAPSHOT_0850`)
- **Execution:** `08:50:00 IST` on Session \( T+1 \) (pre-open).
- **Information Cutoff:** Strictly `08:50:00 IST` on Session \( T+1 \).
- **Latest Completed Daily Bar:** Session \( T \). The daily OHLC bar of Session \( T+1 \) has not occurred and is **strictly inaccessible**.
- **Target Outcome:** Session \( T+1 \) close-to-close return relative to Session \( T \).
- **Join Key:** `features.trading_date == targets.feature_cutoff_session` (Session \( T \)).

*Daily Equivalence in V1:* With daily OHLC features only, Snapshot A and Snapshot B consume identical price feature vectors. However, their execution timestamps, cutoff semantics, and join keys are decoupled so that future phases can add overnight global markets and news to Snapshot B without pipeline redesign.

---

## 3. Walk-Forward Expanding-Window Validation Methodology

### Partitioning Boundary
- **Development Partition:** `2008-07-08` to `2021-12-31` (3,299 supervised observations).
  - All hyperparameter selection, baseline benchmarking, early-stopping estimation, and calibration fitting are conducted **strictly** within this partition.
- **Final Holdout Partition:** `2022-01-01` to `2026-09-03` (1,154 supervised observations).
  - Strictly locked during all modeling and tuning stages. Evaluated **once** as a single final performance evaluation.

### Expanding-Window Development Folds (8 Folds: 2014–2021)
The development period was evaluated chronologically across 8 annual validation folds:

| Fold | Expanding Training Range | Validation Window | Val Sessions | Historical Market Era |
|:---:|:---|:---|:---:|:---|
| **1** | 2008-07-08 to 2013-12-31 (5.5 yrs) | **2014-01-01 to 2014-12-31** | 244 | 2014 General Election rally |
| **2** | 2008-07-08 to 2014-12-31 (6.5 yrs) | **2015-01-01 to 2015-12-31** | 247 | Commodity deflation & consolidation |
| **3** | 2008-07-08 to 2015-12-31 (7.5 yrs) | **2016-01-01 to 2016-12-31** | 247 | Demonetization & volatility shock |
| **4** | 2008-07-08 to 2016-12-31 (8.5 yrs) | **2017-01-01 to 2017-12-31** | 248 | Low-volatility secular bull market |
| **5** | 2008-07-08 to 2017-12-31 (9.5 yrs) | **2018-01-01 to 2018-12-31** | 246 | IL&FS NBFC credit crisis |
| **6** | 2008-07-08 to 2018-12-31 (10.5 yrs) | **2019-01-01 to 2019-12-31** | 245 | Corporate tax rate reduction rally |
| **7** | 2008-07-08 to 2019-12-31 (11.5 yrs) | **2020-01-01 to 2020-12-31** | 252 | COVID-19 crash & historic recovery |
| **8** | 2008-07-08 to 2020-12-31 (12.5 yrs) | **2021-01-01 to 2021-12-31** | 248 | Post-COVID global liquidity expansion |

---

## 4. Model Selection & Early Stopping Policy

### Determining `final_n_estimators` Without Holdout Leakage
During fold evaluation, early stopping (`early_stopping_rounds = 25`) monitors each fold's validation loss. To train the final Production Reference Model on the complete 3,299-session development set without touching the holdout, the final estimator count is derived as the **median of optimal early-stopping boosting rounds (1-based tree counts) across the 8 development folds**:

- In XGBoost, the raw property `best_iteration` is 0-based, where iteration 0 indicates that exactly $1$ boosting tree was constructed. The true optimal number of boosting trees for fold $f$ is therefore:
  $$\text{optimal\_trees}_f = \text{best\_iteration}_f + 1$$
- **Classifier per-fold optimal tree counts ($\text{best\_iteration} + 1$):** `[9, 20, 55, 10, 16, 5, 2, 14]`
  - Sorted: `[2, 5, 9, 10, 14, 16, 20, 55]`
  - Median of 8 observations: $(10 + 14) / 2 = 12.0$
  $$\text{final\_n\_estimators} = \mathbf{12}$$
- **Regressor per-fold optimal tree counts ($\text{best\_iteration} + 1$):** `[2, 78, 127, 8, 3, 90, 1, 281]`
  - Sorted: `[1, 2, 3, 8, 78, 90, 127, 281]`
  - Median of 8 observations: $(8 + 78) / 2 = 43.0$
  $$\text{final\_n\_estimators} = \mathbf{43}$$

### Frozen Hyperparameter Specifications
Selected strictly based on aggregate out-of-fold performance across all 8 development folds (1,977 validation sessions):

#### Classifier (`multi:softprob`, 3 classes)
- `learning_rate`: **0.10**
- `max_depth`: **2** (shallow depth prevents memorization of noise)
- `min_child_weight`: **10.0** (requires sufficient sample support per leaf)
- `final_n_estimators`: **12**
- `subsample`: **0.8**
- `colsample_bytree`: **0.8**
- `reg_alpha` (\(L_1\)): **0.1**
- `reg_lambda` (\(L_2\)): **1.0**
- `class_weight`: **None** (tested balanced weighting, but uniform achieved superior log loss: 1.082 vs 1.088)

#### Regressor (`reg:squarederror`, continuous return)
- `learning_rate`: **0.05**
- `max_depth`: **2**
- `min_child_weight`: **20.0**
- `final_n_estimators`: **43**
- `subsample`: **0.8**
- `colsample_bytree`: **0.7**
- `reg_alpha`: **0.5**
- `reg_lambda`: **2.0**

---

## 5. Probability Calibration Policy & Audit

1. **Development-Only Fitting:** Platt scaling (multinomial logistic regression) was fitted strictly on out-of-fold development probabilities from the 8 development folds (2014–2021).
2. **Zero Holdout Exposure:** The holdout set was never used to optimize calibration parameters, select bin boundaries, or evaluate calibration transforms.
3. **Cross-Validation Calibration Finding:**
   - In-sample resubstitution on development OOF showed an apparent reduction in Expected Calibration Error (ECE: 0.0275 to 0.0153) and Log Loss (1.08229 to 1.07904).
   - However, a strict 8-fold cross-validation of the calibrator itself across development folds demonstrated that unseen out-of-sample Log Loss slightly increased (1.08229 to 1.08453) due to parameter estimation variance on noisy logits.
   - **Production Policy:** The production model is **not** presented as strictly superior merely because ECE improved. Raw tree probabilities are preserved as the primary unconstrained predictive simplex, while Platt scaling is documented as a diagnostic transform for applications requiring uniform binning.

---

## 6. Empirical Performance & Baseline Benchmarking

### Directional Classifier Results (3-Class: DOWN / SIDEWAYS / UP)

| Metric | Dev OOF XGBoost | Dev Majority Baseline | Holdout XGBoost ($N^*=12$) | Holdout Majority Baseline |
|---|:---:|:---:|:---:|:---:|
| **Log Loss (Cross-Entropy)** | **1.08229** | 1.09156 | **1.08847** | 1.09512 |
| **Brier Score** | **0.65636** | 0.66182 | **0.66052** | 0.66430 |
| **Accuracy (%)** | **39.80%** | 39.23% | **37.52%** | 37.35% |
| **Macro F1** | **0.3303** | 0.1879 | **0.2374** | 0.1813 |
| **ECE (Calibration Error)** | **0.0275** | N/A | **0.0335** | N/A |

#### Holdout Per-Class Performance Breakdown ($N^*=12$, 2022–2026, N=1,154)
- **DOWN** (\(N=371\)): Precision = 0.000, Recall = 0.000, F1 = 0.000
- **SIDEWAYS** (\(N=352\)): Precision = **0.4038**, Recall = **0.1193**, F1 = **0.1842**
- **UP** (\(N=431\)): Precision = **0.3724**, Recall = **0.9072**, F1 = **0.5280**

### Return Regressor Results (Next-Session Return, $N^*=43$)

| Metric | Dev OOF XGBoost | Dev Zero-Return Baseline | Holdout XGBoost ($N^*=43$) | Holdout Zero-Return Baseline |
|---|:---:|:---:|:---:|:---:|
| **MAE (%)** | **0.7179%** | 0.7239% | **0.6290%** | 0.6305% |
| **RMSE (%)** | **1.0737%** | 1.0792% | **0.8659%** | 0.8665% |
| **\(R^2\) Score** | **+0.00724** | -0.00300 | **+0.00021** | -0.00121 |
| **Pearson IC** | **+0.0999** (\(p < 0.001\)) | 0.0000 | **+0.0294** (\(p = 0.3179\)) | 0.0000 |
| **Spearman Rank IC** | **+0.0766** (\(p < 0.001\)) | 0.0000 | **+0.0599** (\(p_{\text{iid}} = 0.0419\)) | 0.0000 |
| **Directional Agreement (%)** | **55.46%** | 0.00% | **52.34%** | 0.00% |

---

## 7. Statistical Testing & Significance Audit

### 1. Regression: Diebold-Mariano Test with Newey-West HAC Correction
- **Comparison:** XGBoost Regressor ($N^*=43$) vs. Zero-Return Martingale Baseline.
- **Test Details:** Loss function = Absolute Error (\(L_1\)), Horizon \(h = 1\), Newey-West lag truncation \(K = 6\), Harvey-Leybourne-Newey finite sample correction.
- **Results on Holdout:**
  - Mean Absolute Loss Differential: **+0.000015** (positive indicates XGBoost achieves lower error)
  - 95% Newey-West Confidence Interval: **\([-0.000017, +0.000047]\)**
  - HLN Test Statistic: **+0.9137**
  - \(p\)-value: **0.3611**
  - **Scientific Interpretation:** XGBoost achieves a marginal reduction in absolute prediction error over the zero-return baseline, but the improvement is **not statistically significant at \(\alpha = 0.05\)**. The confidence interval spans zero.

### 2. Spearman Rank IC Statistical Audit: IID vs. Time-Series Inference
- **Descriptive Metric:** Holdout Spearman Rank IC = **+0.0599**.
- **IID Assumption Test (SciPy standard):** Student's $t$ approximation assuming IID observations yields $p = 0.0419$ (nominally significant at $\alpha = 0.05$).
- **Time-Series Stationary Block Bootstrap (Block Size = 10, 2,000 Resamples):**
  - Standard Error: $0.02949$
  - 95% Bootstrap Confidence Interval: **$[-0.00153, +0.11629]$**
  - Time-series $Z$-statistic: $2.0324$, two-sided bootstrap $p$-value: **$0.0421$**.
  - **Scientific Distinction:** While the rank correlation is nominally positive and significant under IID asymptotics ($p=0.0419$), the time-series block bootstrap 95% confidence interval slightly crosses zero at its lower bound ($-0.00153$). It is properly treated as descriptive evidence of weak rank ordering rather than conclusive alpha.

### 3. Classification: Stationary Block Bootstrap Test ($N^*=12$)
- **Comparison:** XGBoost Classifier ($N^*=12$, Calibrated) vs. Expanding Majority Class Baseline.
- **Test Details:** Paired cross-entropy log-loss difference, stationary block bootstrap with block size \(B = 10\), 1,000 bootstrap replicates.
- **Results on Holdout:**
  - Mean Log-Loss Reduction: **+0.00665** (positive indicates XGBoost achieves lower log loss)
  - 95% Bootstrap Confidence Interval: **\([-0.00131, +0.01626]\)**
  - Standardized Effect Size (Cohen's \(d\)): **0.053**
  - **Scientific Interpretation:** XGBoost achieves lower log loss than the majority baseline (1.08847 vs. 1.09512), but the 95% confidence interval spans zero. The improvement is small and not statistically significant at $\alpha = 0.05$.

---

## 8. Model Artifacts & Production Provenance

| Artifact Path | Model Type | Checksum (SHA-256) |
|---|---|---|
| `models/v1/classifier/snapshot_a_xgboost_classifier.json` | 3-Class Classifier (Snap A, $N^*=12$) | `3bb447ad76d1294fff4e125499e0c461def89ec8f44073d98f6d556b9cbf6ce8` |
| `models/v1/classifier/snapshot_a_xgboost_classifier.meta.json` | Manifest (Snap A Classifier) | `e1e270b2d48b15389a1ff5cd87ea2a993ec013fa2de74488b6416d0886264c97` |
| `models/v1/classifier/snapshot_b_xgboost_classifier.json` | 3-Class Classifier (Snap B, $N^*=12$) | `3bb447ad76d1294fff4e125499e0c461def89ec8f44073d98f6d556b9cbf6ce8` |
| `models/v1/classifier/snapshot_b_xgboost_classifier.meta.json` | Manifest (Snap B Classifier) | `efab866a10c56eb636e977a44b6de6a453bee080a01667a9f4a9e2be98fb8cb3` |
| `models/v1/regressor/snapshot_a_xgboost_regressor.json` | Return Regressor (Snap A, $N^*=43$) | `97513ca39817714da5fe6ff8a5d3bbdd5237eac772a3f40803cf166dbf6874e6` |
| `models/v1/regressor/snapshot_a_xgboost_regressor.meta.json` | Manifest (Snap A Regressor) | `d338290575cd13a0d00f2d973a250904ef66529154961722f996c75abd51f996` |
| `models/v1/regressor/snapshot_b_xgboost_regressor.json` | Return Regressor (Snap B, $N^*=43$) | `97513ca39817714da5fe6ff8a5d3bbdd5237eac772a3f40803cf166dbf6874e6` |
| `models/v1/regressor/snapshot_b_xgboost_regressor.meta.json` | Manifest (Snap B Regressor) | `1b1458b8e5574b00c427981324400743c8d065a92560c7bd1ee2509b94d444a8` |
| `data/models/phase6_training_report.json` | Full Training Audit Report | JSON Manifest |
| `configs/models.yaml` | Production Model Registry Config | YAML Specification |

---

## 9. Methodological Limitations & Future Roadmap

1. **Weak Signal in Pure Daily OHLC:** Daily price-derived technical features alone carry low signal-to-noise ratios. While XGBoost achieves positive Information Coefficients (\(+0.0999\) in development, \(+0.0294\) in holdout) and beats baselines on log loss and MAE, the effect sizes are modest and not statistically overwhelming.
2. **DOWN Class Recall Challenge:** In the presence of secular upward market drift in India, the classifier heavily favors UP and SIDEWAYS predictions, exhibiting low recall on DOWN sessions.
3. **Motivation for Phase 9 & Phase 10:** These empirical findings provide clear, rigorous justification for subsequent phases:
   - **Phase 9 (Macro & Global Data):** Adding India VIX, US market overnight closes (S&P 500, Nasdaq), crude oil, and FII/DII institutional flows will introduce genuine exogenous signals.
   - **Phase 10 (News Sentiment):** Ingesting real-time corporate and macroeconomic news sentiment will help capture abrupt directional momentum shifts.
