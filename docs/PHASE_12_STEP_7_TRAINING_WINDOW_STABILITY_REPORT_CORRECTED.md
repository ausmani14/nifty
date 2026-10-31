# PHASE 12 — STEP 7: TRAINING-WINDOW SPECIFICATION & SIGNAL STABILITY REPORT (CORRECTED)

**This is a forensic interpretation correction of the original Step 7 report. Computational results and protected upstream artifacts are unchanged.**

**Model:** Snapshot B (08:50 IST) Model 1 Regressor (63 Features: 45 Price + 18 Context, 0 News, 0 Volume, 0 Flow)  
**Target:** Intraday Open-to-Close Return: `R_intraday(T+1) = Close(T+1) / Open(T+1) - 1`  
**Evaluation Period:** 2014-01-02 through 2021-12-31 ($N = 1,960$ OOF sessions across 8 chronological folds)  
**Holdout Firewall:** Terminal Holdout 2022-01-03 through 2026-09-03 ($N = 1,154$) strictly quarantined and untouched  
**Status:** FORENSICALLY RECONCILED & SEALED  

---

## 1. EXECUTIVE SUMMARY

Phase 12 Step 7 investigated the central unresolved hypothesis from Step 6:
> *Does the weak residual predictive relationship observed in Step 6 survive when the model is trained under alternative but pre-specified chronological training-window structures (W0, W1, W2, W3), or is the observed signal mainly an artifact of the expanding-window history and temporal concentration?*

Four pre-registered, frozen chronological training-window specifications were evaluated across the identical $N=1,960$ out-of-fold (OOF) evaluation sessions:
1. **W0 (Expanding Window):** All preceding eligible development data from `2008-07-08` through fold $k-1$ (reproducing sealed Step 2 and Step 6).
2. **W1 (5-Year Rolling Window):** Preceding 5 calendar years of development data ($[Y_k - 5, Y_k - 1]$).
3. **W2 (3-Year Rolling Window):** Preceding 3 calendar years of development data ($[Y_k - 3, Y_k - 1]$).
4. **W3 (2-Year Rolling Window):** Preceding 2 calendar years of development data ($[Y_k - 2, Y_k - 1]$).

### Core Forensic Conclusions:
1. **The Current Experiment Does Not Demonstrate Stability:** The current experiment does not demonstrate that the conditional forecasting relationship is stable across alternative training-window specifications. The strongest non-degenerate alternative, the 5-year rolling window (W1), reduces the residual relationship to effectively zero: residual Pearson IC collapses from $+0.0477$ ($p = 0.0346$) in W0 down to $+0.0018$ ($p = 0.9348$) in W1, and incremental $R^2$ turns negative ($-0.0225\%$).
2. **Mandatory Distinction Between W1 and W2/W3:**
   - **W1 (5-Year Rolling Window):** Represents the primary viable alternative-window diagnostic ($N \approx 1,221$ training sessions). The model produces non-constant predictions, yet the residual correlation disappears ($+0.0018$) and the placebo test yields an empirical $p$-value of $0.4580$ (consistent with random noise).
   - **W2 (3-Year Rolling Window) & W3 (2-Year Rolling Window):** Expose model-capacity limitations under the frozen regularization configuration (`min_child_weight: 20.0`, `reg_alpha: 0.5`, `reg_lambda: 2.0`). In W2, the model fails to find valid tree splits in 7 of the 8 folds, collapsing to root-node constants. In W3, the model collapses across all 8 folds to a constant predictor (prediction std $= 0.0$). Therefore, W2 and W3 must be interpreted as **degeneracy diagnostics** rather than independent proof of signal absence.
3. **Training-Window Dependence of the 2021 Observation:** The 2021 residual relationship observed under the expanding-window specification ($+0.2539$, Inc $R^2 = +2.20\%$) is not robust to the 5-year rolling-window specification, falling to $+0.0222$ ($p = 0.728$, Inc $R^2 = +0.01\%$). This indicates substantial training-window dependence. However, because W2 and W3 exhibit model-capacity collapse, the experiment cannot distinguish completely between disappearance of the underlying relationship and sensitivity of the fixed model architecture/regularization to shorter training samples.
4. **Persistence of Base-Rate Short Bias:** All rolling specifications intensified the unconditional short bias. W1 predicted SHORT on $99.54\%$ of sessions, while W2 and W3 predicted SHORT on $100.0\%$ of sessions. Gross performance at 0 bps friction ($+8.04$ to $+8.27$ bps/day) is entirely explained by the development target's negative drift (Always Short baseline $= +8.04$ bps/day). Under realistic transaction costs of 10 bps/day, all specifications generate negative returns ($-1.73$ to $-2.76$ bps/day).

### Scientific Decision Gate:
**B) STABILITY NOT SUPPORTED.**  
Across the viable W0/W1 comparison, stability is not demonstrated.

---

## 2. EXACT METHODOLOGY

- **Target:** Same-day NIFTY 50 intraday return:
  `R_intraday(T+1) = Close(T+1) / Open(T+1) - 1`
- **Feature Set:** Frozen Snapshot B Model 1 (exactly 63 features: 45 Price + 18 Context). ZERO News, ZERO Volume, ZERO Flow proxy features.
- **Outer Folds:** 8 annual walk-forward folds covering 2014-01-02 through 2021-12-31 ($N=1,960$ OOF sessions), identical to Step 2, Step 3, Step 4, Step 5, and Step 6.
- **Model Architecture & Base Hyperparameters:**
  `reg:squarederror`, `learning_rate: 0.05`, `max_depth: 2`, `min_child_weight: 20.0`, `subsample: 0.8`, `colsample_bytree: 0.7`, `reg_alpha: 0.5`, `reg_lambda: 2.0`, `random_state: 42`, `n_jobs: -1`.
- **Deterministic Tree-Count Selection ($N^*$):**
  - Candidate grid: $[10, 15, 20, 25, 30, 35, 40, 45, 50, 60]$.
  - Inner validation is performed chronologically on the last $20\%$ of the training window.
  - The tree count minimizing validation RMSE is selected. Ties are broken deterministically by selecting the smallest tree count. Zero OOF tuning.
- **Fold-Local Training Baselines:**
  - Calculated strictly from training window observations:
    $$\mu_{\text{train}} = \frac{1}{|\mathcal{D}_{\text{train}}|} \sum_{t \in \mathcal{D}_{\text{train}}} R_{\text{intraday}}(t)$$
  - Excess predictions and residual returns:
    $$\hat{\varepsilon}_t = \hat{y}_t - \mu_{\text{train}}$$
    $$\varepsilon_t = R_t - \mu_{\text{train}}$$
  - Numerical identities verified: $R_t = \mu_{\text{train}} + \varepsilon_t$ and $\hat{y}_t = \mu_{\text{train}} + \hat{\varepsilon}_t$.

---

## 3. WINDOW DEFINITIONS & TRAINING BOUNDARIES

| Window Code | Window Name | Definition | Start Date Rule | End Date Rule | Mean Train $N$ | Primary Function |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **W0** | Expanding Window | Preceding development history | `2008-07-08` | `(val_year - 1)-12-31` | 2,191.9 | Sealed Reference Architecture |
| **W1** | 5-Year Rolling Window | Preceding 5 calendar years | `(val_year - 5)-01-01` | `(val_year - 1)-12-31` | 1,221.1 | **Primary Alternative-Window Stability Diagnostic** |
| **W2** | 3-Year Rolling Window | Preceding 3 calendar years | `(val_year - 3)-01-01` | `(val_year - 1)-12-31` | 732.8 | Model-Capacity / Degeneracy Diagnostic |
| **W3** | 2-Year Rolling Window | Preceding 2 calendar years | `(val_year - 2)-01-01` | `(val_year - 1)-12-31` | 488.8 | Model-Capacity / Degeneracy Diagnostic |

### Fold-by-Fold Training Sample Sizes ($N_{\text{train}}$):
| Fold | Val Year | Val $N$ | W0 (Expanding) | W1 (5Y Rolling) | W2 (3Y Rolling) | W3 (2Y Rolling) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 2014 | 240 | 1,339 | 1,222 | 731 | 489 |
| **2** | 2015 | 244 | 1,579 | 1,221 | 729 | 487 |
| **3** | 2016 | 244 | 1,823 | 1,215 | 731 | 484 |
| **4** | 2017 | 248 | 2,067 | 1,217 | 728 | 488 |
| **5** | 2018 | 245 | 2,315 | 1,223 | 736 | 492 |
| **6** | 2019 | 241 | 2,560 | 1,221 | 737 | 493 |
| **7** | 2020 | 250 | 2,801 | 1,222 | 734 | 486 |
| **8** | 2021 | 248 | 3,051 | 1,228 | 736 | 491 |
| **Total** | | **1,960** | | | | |

---

## 4. FOLD RESULTS ACROSS ALL FOUR WINDOWS

### Table 4.1: Selected Tree Counts ($N^*$) by Fold and Window
| Fold | Val Year | W0 $N^*$ | W1 $N^*$ | W2 $N^*$ | W3 $N^*$ |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 2014 | 10 | 60 | 10 | 10 |
| 2 | 2015 | 60 | 10 | 10 | 10 |
| 3 | 2016 | 45 | 50 | 10 | 10 |
| 4 | 2017 | 60 | 60 | 10 | 10 |
| 5 | 2018 | 10 | 60 | 10 | 10 |
| 6 | 2019 | 10 | 10 | 10 | 10 |
| 7 | 2020 | 10 | 10 | 10 | 10 |
| 8 | 2021 | 40 | 10 | 25 | 10 |
| **Mean** | | **30.6** | **33.8** | **11.9** | **10.0** |

### Table 4.2: Residual Pearson IC by Fold and Window
| Fold | Val Year | Val $N$ | W0 (Expanding) | W1 (5Y Rolling) | W2 (3Y Rolling)* | W3 (2Y Rolling)* |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 2014 | 240 | +0.1095 ($p=0.091$) | +0.0979 ($p=0.131$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 2 | 2015 | 244 | +0.0382 ($p=0.553$) | +0.0877 ($p=0.172$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 3 | 2016 | 244 | +0.0746 ($p=0.246$) | +0.0081 ($p=0.899$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 4 | 2017 | 248 | +0.0254 ($p=0.690$) | +0.0465 ($p=0.466$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 5 | 2018 | 245 | -0.1248 ($p=0.051$) | +0.0577 ($p=0.368$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 6 | 2019 | 241 | -0.0963 ($p=0.136$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 7 | 2020 | 250 | +0.0143 ($p=0.823$) | -0.0428 ($p=0.501$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 8 | 2021 | 248 | **+0.2539** ($p<0.001$) | **+0.0222** ($p=0.728$) | +0.0348 ($p=0.585$) | 0.0000 ($p=1.000$) |

*\*Note: For W2 and W3, zero IC reflects constant prediction degeneracy resulting from tree regularization on small training samples.*

### Table 4.3: Incremental $R^2$ (\%) by Fold and Window
| Fold | Val Year | W0 (Expanding) | W1 (5Y Rolling) | W2 (3Y Rolling) | W3 (2Y Rolling) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 2014 | +0.28% | -0.44% | +0.00% | +0.00% |
| 2 | 2015 | +0.61% | +0.06% | -0.00% | -0.00% |
| 3 | 2016 | +0.76% | +0.01% | -0.00% | +0.00% |
| 4 | 2017 | -0.50% | +0.05% | -0.00% | +0.00% |
| 5 | 2018 | -0.46% | +0.01% | +0.00% | +0.00% |
| 6 | 2019 | -0.30% | -0.00% | +0.00% | -0.00% |
| 7 | 2020 | +0.03% | -0.00% | -0.00% | +0.00% |
| 8 | 2021 | **+2.20%** | **+0.01%** | +0.01% | +0.00% |

---

## 5. TEMPORAL BLOCK RESULTS

Aggregated across three pre-registered temporal blocks:
- **Block A (2014–2016):** Pre-demonetization & commodity consolidation ($N=728$).
- **Block B (2017–2019):** Low-volatility rally & NBFC crisis ($N=734$).
- **Block C (2020–2021):** COVID-19 crash & recovery ($N=498$).

| Window | Temporal Block | $N$ | Residual Pearson IC | Residual $p$-val | Incremental $R^2$ | Res. Dir. Acc. |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **W0 (Expanding)** | Block A (2014-2016) | 728 | +0.0622 | 0.0934 | +0.587% | 53.98% |
| | Block B (2017-2019) | 734 | -0.0284 | 0.4418 | -0.399% | 46.73% |
| | Block C (2020-2021) | 498 | **+0.1081** | 0.0158 | **+0.500%** | 50.00% |
| **W1 (5Y Rolling)** | Block A (2014-2016) | 728 | -0.0076 | 0.8373 | -0.082% | 53.16% |
| | Block B (2017-2019) | 734 | +0.0079 | 0.8306 | +0.014% | 50.41% |
| | Block C (2020-2021) | 498 | -0.0007 | 0.9877 | -0.001% | 47.19% |
| **W2 (3Y Rolling)** | Block A (2014-2016) | 728 | 0.0000 | 1.0000 | -0.000% | 48.21% |
| | Block B (2017-2019) | 734 | 0.0000 | 1.0000 | +0.000% | 50.68% |
| | Block C (2020-2021) | 498 | +0.0126 | 0.7794 | +0.002% | 52.41% |
| **W3 (2Y Rolling)** | Block A (2014-2016) | 728 | 0.0000 | 1.0000 | -0.000% | 49.18% |
| | Block B (2017-2019) | 734 | 0.0000 | 1.0000 | +0.000% | 50.95% |
| | Block C (2020-2021) | 498 | 0.0000 | 1.0000 | +0.000% | 49.20% |

---

## 6. DIRECT STABILITY COMPARISON (FULL OOF POPULATION)

### Table 6.1: Direct Stability Comparison Table
| Window Specification | Raw IC | Residual IC | Inc. $R^2$ | Res. Dir. Acc. | Raw MAE (bps) | Raw RMSE (bps) | Diff Res. IC vs W0 | Diff Inc. $R^2$ vs W0 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **W0 (Expanding)** | +0.0476 | **+0.0477** | **+0.3425%** | 50.26% | 60.94 | 89.31 | 0.0000 | 0.0000% |
| **W1 (5Y Rolling)** | +0.0179 | **+0.0018** | **-0.0225%** | 50.61% | 61.06 | 89.35 | **-0.0459** | **-0.3650%** |
| **W2 (3Y Rolling)** | -0.0216 | **+0.0090** | **+0.0012%** | 50.20% | 61.07 | 89.45 | **-0.0387** | **-0.3413%** |
| **W3 (2Y Rolling)** | +0.0058 | **0.0000** | **+0.0000%** | 49.85% | 61.10 | 89.39 | **-0.0477** | **-0.3425%** |

### Table 6.2: Statistical Significance & Calibration Details
| Window Specification | Mean Pred (bps) | Realized Mean (bps) | Forecast Bias (bps) | Std Pred (bps) | Residual $p$-value | Placebo Emp. $p$-val | Diagnostic Role |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **W0 (Expanding)** | -4.83 | -8.04 | +3.21 | 4.06 | 0.0346 | **0.0130** | Baseline Architecture |
| **W1 (5Y Rolling)** | -6.75 | -8.04 | +1.29 | 1.85 | 0.9348 | **0.4580** | **Viable Alternative Window** |
| **W2 (3Y Rolling)** | -6.98 | -8.04 | +1.06 | 2.47 | 0.6901 | **0.3420** | Degeneracy Diagnostic |
| **W3 (2Y Rolling)** | -6.95 | -8.04 | +1.09 | 3.05 | 1.0000 | **1.0000** | Degeneracy Diagnostic |

---

## 7. 2021 FORENSIC ANALYSIS

In Phase 12 Step 6, Fold 8 (2021) was identified as an extreme concentration:
- W0 2021 Residual IC: $+0.2539$ ($p = 0.00005$, Inc $R^2 = +2.20\%$).
- Without 2021, the 2014–2020 OOF Residual IC in W0 was only $+0.0177$.

### Step 7 Empirical Findings for 2021:
- Under **W1 (5-Year Rolling Window: 2016–2020 training)**:
  - Selected tree count: $N^* = 10$ (compared to $N^* = 40$ in W0).
  - 2021 Residual IC dropped from **$+0.2539$ to $+0.0222$** ($p = 0.728$).
  - Incremental $R^2$ collapsed from **$+2.20\%$ to $+0.01\%$**.
- Under **W2 (3-Year Rolling Window: 2018–2020 training)**:
  - Selected tree count: $N^* = 25$.
  - 2021 Residual IC was $+0.0348$ ($p = 0.585$, Inc $R^2 = +0.01\%$).
- Under **W3 (2-Year Rolling Window: 2019–2020 training)**:
  - Model failed to split; 2021 Residual IC was $0.0000$.

### Scientific Interpretation:
The 2021 residual relationship observed under the expanding-window specification is not robust to the 5-year rolling-window specification. This indicates substantial training-window dependence. However, because W2/W3 also exhibit model-capacity collapse, the experiment cannot distinguish completely between disappearance of the underlying relationship and sensitivity of the fixed model architecture/regularization to shorter training samples.

---

## 8. 2017–2019 FORENSIC ANALYSIS

In Step 6, Block B (2017–2019) was negative across all metrics:
- W0 Block B Residual IC: $-0.0284$, Incremental $R^2 = -0.40\%$.

### Step 7 Comparison for Block B:
- Under **W1 (5-Year Rolling)**: Block B Residual IC shifted to $+0.0079$ ($p = 0.8306$), and Incremental $R^2 = +0.014\%$.
- Under **W2 (3-Year Rolling)**: Block B Residual IC was $0.0000$ ($p = 1.0000$).
- Under **W3 (2-Year Rolling)**: Block B Residual IC was $0.0000$ ($p = 1.0000$).

*Scientific Assessment:* The slight shift of Block B from negative in W0 to near-zero in W1 is consistent with parameter shrinkage and reduced variance towards the training baseline, rather than an authentic improvement in predictive accuracy.

---

## 9. SHORT-BIAS AUDIT

| Specification | % Predicted Short | % Predicted Long | Realized Return when Pred Short (bps) | Realized Return when Pred Long (bps) | Always Short Baseline Return (bps) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **W0 (Expanding)** | 90.71% | 9.29% | -8.42 | -4.27 | +8.04 |
| **W1 (5Y Rolling)** | 99.54% | 0.46% | -8.19 | +25.66* | +8.04 |
| **W2 (3Y Rolling)** | 100.00% | 0.00% | -8.04 | N/A | +8.04 |
| **W3 (2Y Rolling)** | 100.00% | 0.00% | -8.04 | N/A | +8.04 |

*\*Note: For W1, only 9 sessions out of 1,960 were predicted long ($0.46\%$), rendering the conditional return descriptive only ($N < 50$).*

### Findings:
1. Short predictions dominate across all specifications. As training window size decreases, the model's capacity to identify long conditions vanishes entirely.
2. In W2 and W3, the model predicts short on $100.0\%$ of all sessions. The model is functionally equivalent to an Always Short dummy rule.
3. The gross positive performance of raw sign signals at 0 bps friction is entirely an artifact of the negative intraday market drift ($-8.04$ bps/day) documented in Step 5 and Step 6.

---

## 10. PLACEBO / NULL HYPOTHESIS TEST

**Methodology:** For each window, the 1,960 excess predictions were randomly permuted 1,000 times (fixed seed 42) against the realized residual returns to generate empirical null distributions.

| Window Specification | Observed Residual IC | Observed $p$-val | Placebo Mean IC | Placebo Std IC | Empirical Percentile | Empirical $p$-value | Diagnostic Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **W0 (Expanding)** | +0.0477 | 0.0346 | -0.0012 | 0.0226 | 98.70% | **0.0130** | Baseline Reference |
| **W1 (5Y Rolling)** | +0.0018 | 0.9348 | -0.0000 | 0.0226 | 54.20% | **0.4580** | Indistinguishable from Noise |
| **W2 (3Y Rolling)** | +0.0090 | 0.6901 | -0.0001 | 0.0224 | 65.80% | **0.3420** | Degenerate Predictor |
| **W3 (2Y Rolling)** | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 50.05% | **1.0000** | Constant Predictor |

*Placebo Conclusion:*  
Under W1, the empirical $p$-value is $0.4580$, placing the observed relationship in the exact center of the random permutation distribution. Under the viable alternative window structure, there is insufficient evidence to establish that the predictions have any correspondence with realized residual returns.

---

## 11. ECONOMIC DIAGNOSTIC (NOT A STRATEGY)

Diagnostic raw sign return evaluation at 0, 5, 10, and 20 bps/day transaction friction:

| Window | Cost (bps) | % Short | Daily Return (bps) | HAC SE (bps) | HAC $t$-stat | HAC $p$-val | Sharpe Ratio | Max DD |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **W0** | 0 bps | 90.71% | +7.24 | 1.83 | +3.95 | 0.00008 | 1.32 | -14.55% |
| | 5 bps | 90.71% | +2.24 | 1.83 | +1.22 | 0.22120 | 0.33 | -16.91% |
| | 10 bps | 90.71% | -2.76 | 1.83 | -1.50 | 0.13260 | -0.54 | -53.55% |
| | 20 bps | 90.71% | -12.76 | 1.83 | -6.96 | <0.00001 | -1.99 | -92.68% |
| **W1** | 0 bps | 99.54% | +8.27 | 1.76 | +4.69 | <0.00001 | 1.55 | -12.73% |
| | 5 bps | 99.54% | +3.27 | 1.76 | +1.85 | 0.06369 | 0.53 | -15.21% |
| | 10 bps | 99.54% | -1.73 | 1.76 | -0.98 | 0.32741 | -0.37 | -39.85% |
| | 20 bps | 99.54% | -11.73 | 1.76 | -6.65 | <0.00001 | -1.86 | -91.04% |
| **W2** | 0 bps | 100.00% | +8.04 | 1.77 | +4.53 | <0.00001 | 1.49 | -12.73% |
| | 5 bps | 100.00% | +3.04 | 1.77 | +1.71 | 0.08685 | 0.48 | -18.48% |
| | 10 bps | 100.00% | -1.96 | 1.77 | -1.11 | 0.26813 | -0.41 | -42.57% |
| | 20 bps | 100.00% | -11.96 | 1.77 | -6.75 | <0.00001 | -1.89 | -91.45% |
| **W3** | 0 bps | 100.00% | +8.04 | 1.77 | +4.53 | <0.00001 | 1.49 | -12.73% |
| | 5 bps | 100.00% | +3.04 | 1.77 | +1.71 | 0.08685 | 0.48 | -18.48% |
| | 10 bps | 100.00% | -1.96 | 1.77 | -1.11 | 0.26813 | -0.41 | -42.57% |
| | 20 bps | 100.00% | -11.96 | 1.77 | -6.75 | <0.00001 | -1.89 | -91.45% |

### Economic Interpretation:
1. No configuration survives 10 bps transaction cost.
2. At 10 bps friction, W0 loses $-2.76$ bps/day, W1 loses $-1.73$ bps/day, and W2/W3 lose $-1.96$ bps/day.
3. The apparent gross return at 0 bps is exclusively a passive capture of the unconditional negative intraday drift.

---

## 12. MANDATORY DISTINCTION BETWEEN W1 AND W2/W3

In evaluating the stability of the predictive relationship, W1 and W2/W3 play fundamentally distinct roles:

### W1 (5-Year Rolling Window) — Primary Viable Stability Diagnostic:
- Training sample size is approximately 1,221 sessions per fold, which provides sufficient sample density for gradient-boosted trees.
- The model produces non-constant, variable predictions across all folds (mean tree count $N^* = 33.8$).
- Residual Pearson IC is $+0.0018$ ($p = 0.9348$), and incremental $R^2$ is $-0.0225\%$.
- In Fold 8 (2021), residual IC falls to $+0.0222$ ($p = 0.728$).
- **Conclusion for W1:** W1 provides valid and meaningful empirical evidence that the relationship detected in W0 does not survive a materially different but viable historical training window.

### W2 (3-Year Rolling) & W3 (2-Year Rolling) — Model-Capacity / Degeneracy Diagnostics:
- Training sample sizes are small ($N \approx 733$ for W2, $N \approx 489$ for W3).
- Combined with frozen regularization parameters (`min_child_weight: 20.0`, `reg_alpha: 0.5`, `reg_lambda: 2.0`), the tree-building algorithm could not identify splits with sufficient gain.
- In W2, the model collapsed to the root node in 7 out of 8 folds.
- In W3, the model collapsed across all 8 folds to a flat constant predictor (within-fold prediction std $= 0.0$).
- **Conclusion for W2/W3:** These specifications represent model-capacity and regularization constraints. Their flat ICs cannot be treated as clean independent evidence of signal absence, but rather as evidence that the frozen model architecture cannot operate effectively on short historical windows.

---

## 13. LEAKAGE AUDIT

1. **Embargo Integrity:** All training sets end strictly in December of year $Y_k - 1$ ($2013-12-31$ through $2020-12-31$). All validation sets begin in January of year $Y_k$. The minimum causal separation between the last training target observation and the first validation prediction is at least one market close.
2. **Disjoint Indices:** In all 32 fold/window combinations, the intersection of training indices and validation indices is strictly empty:
   $$\mathcal{D}_{\text{train}} \cap \mathcal{D}_{\text{val}} = \emptyset$$
3. **Chronological Inner Validation:** Tree count $N^*$ was selected strictly within the chronological last $20\%$ of each training set. No validation observation was accessible during tree selection.
4. **Feature Sanitization:** Feature extraction confirmed exactly 63 Model 1 features (45 Price + 18 Context). Zero News, Zero Volume, and Zero Flow proxy features.

---

## 14. HOLDOUT FIREWALL PROOF

1. Maximum `trading_date` across all Phase 12 Step 7 datasets: `2021-12-31`.
2. Target date for `2021-12-31` is `2022-01-03` (the next trading day Close-to-Open return), which was realized on the development boundary.
3. Exactly zero rows, records, or sessions with `trading_date >= 2022-01-03` were loaded, read, or evaluated.
4. Terminal Holdout (2022-01-03 through 2026-09-03, $N=1,154$) remains $100\%$ untouched, unconsumed, and quarantined.

---

## 15. ARTIFACT CHECKSUMS

### Computational Datasets (`data/interim/phase12_step7/`):
| File Name | SHA-256 Checksum |
| :--- | :--- |
| `step7_economic_diagnostic.csv` | `2801997a874ee0eb1778a273430f47c5472343b8419b4ebed7f0cd993ad10c90` |
| `step7_fold_results.csv` | `230e90c3b7415e9d19d7c01714c72d6a779f6b40050ad4e547648eddbe3575f7` |
| `step7_placebo_results.csv` | `977397dd78737150e5bbac8a9f1b1e8e1545604697cb978bcc2db06606b01667` |
| `step7_predictions.csv` | `3a2ec99ed398f4cb1047326df2cee879a355712c98aa306f8e87d0680291013e` |
| `step7_summary.csv` | `de3b4c8adde8c2861c452e08ca0a5da5b901596bf0ad62de320770a11800ac6f` |
| `step7_temporal_results.csv` | `5953cdbd1bfa67d85c4a58e129fda337dcdea3ab0da330bc79647d524d441ed9` |
| `step7_tree_counts.csv` | `de78be51942b03d27af3a681c65c204aef090f8f948169d3fcfcd3f3be06f2ad` |
| `step7_integrity_manifest.json` | `d867c3ee1adc4969d2a19fc9647b65d7872e8b2a73ae0048b6c5759f124c55b1` |

### Documentation Artifacts (`docs/`):
| File Name | Description | SHA-256 Checksum |
| :--- | :--- | :--- |
| `docs/PHASE_12_STEP_7_TRAINING_WINDOW_STABILITY_REPORT.md` | Original Step 7 Report | `739f4f4b9dc63a1fc450e78415e062c60f579f0718eae6459dbacb4d60e2188b` |
| `docs/PHASE_12_STEP_7_TRAINING_WINDOW_STABILITY_REPORT_CORRECTED.md` | Corrected Step 7 Report | *(Verified in Step 7 Forensic Seal)* |

### Protected Upstream Artifacts Verified:
- All 19 Phase 4–10 protected artifacts verified byte-for-byte.
- All 10 Phase 12 Step 5 artifacts verified byte-for-byte.
- All 7 Phase 12 Step 6 artifacts verified byte-for-byte.

---

## 16. TEST SUITE RESULTS

- **Step 7 Dedicated Test Suite:**
  `pytest -q tests/test_phase12_step7_window_stability.py`
  **Result:** **15 passed (100% pass rate).**
- **Full Repository Regression Suite:**
  `pytest -q`
  **Result:** **291 passed (100% pass rate across entire repository).**

---

## 17. FINAL SCIENTIFIC DECISION GATE

Pre-registered decision options:
- A) STABILITY SUPPORTED
- B) STABILITY NOT SUPPORTED
- C) INFORMATION TOO WEAK TO DECIDE

### Selected Decision:
$$\mathbf{B) \; STABILITY \; NOT \; SUPPORTED}$$

### Formal Justification:
1. **W0 residual IC = +0.0477.**
2. **W1 residual IC = +0.0018 and is statistically indistinguishable from zero ($p = 0.9348$).**
3. **The 2021 W0 concentration (+0.2539) falls to +0.0222 under W1.**
4. **W2/W3 show severe model degeneracy and therefore cannot be treated as clean independent evidence of signal absence.**
5. **Across the viable W0/W1 comparison, stability is not demonstrated.**
6. **Economic performance remains unattractive after transaction costs.**
7. **No production or trading rule is justified.**

---

## 18. GOVERNANCE & STOP CONDITION

**PHASE 12 STEP 7 IS FORMALLY SEALED AFTER FORENSIC INTERPRETATION CORRECTION.**

**NO PHASE 12 STEP 8 EXECUTION IS AUTHORIZED BY THIS TASK.**
