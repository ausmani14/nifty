# PHASE 12 — STEP 7: TRAINING-WINDOW SPECIFICATION & SIGNAL STABILITY REPORT
**Model:** Snapshot B (08:50 IST) Model 1 Regressor (63 Features: 45 Price + 18 Context, 0 News, 0 Volume, 0 Flow)  
**Target:** Intraday Open-to-Close Return: $R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$  
**Evaluation Period:** 2014-01-02 through 2021-12-31 ($N = 1,960$ OOF sessions across 8 chronological folds)  
**Holdout Firewall:** Terminal Holdout 2022-01-03 through 2026-09-03 ($N = 1,154$) strictly quarantined and untouched  
**Status:** COMPLETE & FORMALLY SEALED  

---

## 1. EXECUTIVE SUMMARY

Phase 12 Step 7 investigated the central unresolved question from Step 6:
> *Does the weak residual predictive relationship observed in Step 6 survive when the model is trained under alternative but pre-specified chronological training-window structures (W0, W1, W2, W3), or is the observed signal mainly an artifact of the expanding-window history and temporal concentration?*

To answer this question without post-hoc bias or hyperparameter optimization, four chronological training-window specifications were pre-registered, frozen, and executed across the identical $N=1,960$ out-of-fold (OOF) evaluation sessions:
1. **W0 (Expanding Window):** All preceding eligible development data from 2008-07-08 through fold $k-1$ (reproducing sealed Step 2 and Step 6).
2. **W1 (5-Year Rolling Window):** Preceding 5 calendar years of development data ($[Y_k - 5, Y_k - 1]$).
3. **W2 (3-Year Rolling Window):** Preceding 3 calendar years of development data ($[Y_k - 3, Y_k - 1]$).
4. **W3 (2-Year Rolling Window):** Preceding 2 calendar years of development data ($[Y_k - 2, Y_k - 1]$).

### Key Empirical Findings:
1. **Signal Evaporation Under Fixed Rolling Window (W1):** Under the 5-year rolling specification ($N \approx 1,220$ training sessions), the OOF residual Pearson IC collapses from **$+0.0477$ ($p = 0.0346$) in W0 down to $+0.0018$ ($p = 0.9348$) in W1**, which is statistically indistinguishable from pure noise. The incremental $R^2$ turns negative ($-0.0225\%$), and the placebo permutation test yields an empirical $p$-value of $0.4580$ (compared to $0.0130$ in W0).
2. **Model Collapse Under Shorter Windows (W2 & W3):** Under 3-year ($N \approx 733$) and 2-year ($N \approx 489$) rolling windows, the model suffers severe sample-shrinkage degeneracy under the pre-registered tree regularization (`min_child_weight: 20.0`, `reg_alpha: 0.5`, `reg_lambda: 2.0`). In W2, the model fails to find valid tree splits in 7 of the 8 folds, predicting the root node constant. In W3, the model completely degenerates across all 8 folds into a constant predictor with within-fold prediction standard deviation of $0.0$.
3. **Dissolution of the 2021 Signal Concentration:** In Step 6, the expanding window exhibited an extreme residual IC concentration in Fold 8 (2021) of $+0.2539$ ($p < 0.0001$, Inc $R^2 = +2.20\%$). Under W1 (5-year rolling window: 2016–2020 training), the tree-count selection $N^*$ drops from 40 to 10, and the 2021 residual IC completely evaporates to **$+0.0222$ ($p = 0.728$, Inc $R^2 = +0.01\%$)**. The signal in 2021 was heavily dependent on observing 2008–2015 historical training data.
4. **Persistence of Unconditional Short Bias:** All rolling specifications intensified the unconditional short bias. W1 predicted SHORT on $99.54\%$ of sessions, while W2 and W3 predicted SHORT on $100.0\%$ of sessions. Gross profitability at 0 bps friction ($+8.04$ to $+8.27$ bps/day) is entirely explained by the development target's negative drift (Always Short baseline $= +8.04$ bps/day). Under realistic transaction costs of 10 bps/day, all specifications lose between $-1.73$ and $-2.76$ bps/day.

### Scientific Decision Gate:
**B) STABILITY NOT SUPPORTED.**  
The weak residual predictive relationship observed in Step 6 does not survive alternative training-window specifications. It is highly unstable, collapses under fixed 5-year rolling windows, degenerates under shorter windows, and is primarily an artifact of expanding-window history and extreme temporal concentration in 2021.

---

## 2. EXACT METHODOLOGY

1. **Target:** Same-day NIFTY 50 intraday return:
   $$R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$$
2. **Feature Set:** Frozen Snapshot B Model 1 (exactly 63 features: 45 Price + 18 Context). ZERO News, ZERO Volume, ZERO Flow proxy features.
3. **Outer Folds:** 8 annual walk-forward folds covering 2014-01-02 through 2021-12-31 ($N=1,960$ OOF sessions), identical to Step 2, Step 3, Step 4, Step 5, and Step 6.
4. **Model Architecture & Base Hyperparameters:**
   ```python
   xgb_base_params = {
       "objective": "reg:squarederror",
       "learning_rate": 0.05,
       "max_depth": 2,
       "min_child_weight": 20.0,
       "subsample": 0.8,
       "colsample_bytree": 0.7,
       "reg_alpha": 0.5,
       "reg_lambda": 2.0,
       "random_state": 42,
       "n_jobs": -1,
   }
   ```
5. **Deterministic Tree-Count Selection ($N^*$):**
   - For each window and fold, the candidate grid is $[10, 15, 20, 25, 30, 35, 40, 45, 50, 60]$.
   - Inner validation is performed chronologically on the last $20\%$ of the training window.
   - The tree count minimizing validation RMSE is selected. Ties are broken deterministically by selecting the smallest tree count.
   - Zero OOF tuning or post-hoc adjustment.
6. **Fold-Local Training Baselines:**
   - For each fold and window, the unconditional baseline $\mu_{\text{train}}$ is calculated strictly using observations within the training window:
     $$\mu_{\text{train}} = \frac{1}{|\mathcal{D}_{\text{train}}|} \sum_{t \in \mathcal{D}_{\text{train}}} R_{\text{intraday}}(t)$$
   - Excess predictions and residual returns:
     $$\hat{\varepsilon}_t = \hat{y}_t - \mu_{\text{train}}$$
     $$\varepsilon_t = R_t - \mu_{\text{train}}$$
   - Numerical identities verified: $R_t = \mu_{\text{train}} + \varepsilon_t$ and $\hat{y}_t = \mu_{\text{train}} + \hat{\varepsilon}_t$.

---

## 3. WINDOW DEFINITIONS & TRAINING BOUNDARIES

| Window Code | Window Name | Definition | Start Date Rule | End Date Rule | Mean Train $N$ |
| :--- | :--- | :--- | :--- | :--- | :---: |
| **W0** | Expanding Window | Preceding development history | `2008-07-08` | `(val_year - 1)-12-31` | 2,191.9 |
| **W1** | 5-Year Rolling Window | Preceding 5 calendar years | `(val_year - 5)-01-01` | `(val_year - 1)-12-31` | 1,221.1 |
| **W2** | 3-Year Rolling Window | Preceding 3 calendar years | `(val_year - 3)-01-01` | `(val_year - 1)-12-31` | 732.8 |
| **W3** | 2-Year Rolling Window | Preceding 2 calendar years | `(val_year - 2)-01-01` | `(val_year - 1)-12-31` | 488.8 |

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

*Observation:* Under W2 and W3, inner validation consistently selected the minimum tree count ($N^* = 10$) because additional trees failed to reduce validation error on the smaller sample sizes.

### Table 4.2: Residual Pearson IC by Fold and Window
| Fold | Val Year | Val $N$ | W0 (Expanding) | W1 (5Y Rolling) | W2 (3Y Rolling) | W3 (2Y Rolling) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | 2014 | 240 | +0.1095 ($p=0.091$) | +0.0979 ($p=0.131$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 2 | 2015 | 244 | +0.0382 ($p=0.553$) | +0.0877 ($p=0.172$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 3 | 2016 | 244 | +0.0746 ($p=0.246$) | +0.0081 ($p=0.899$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 4 | 2017 | 248 | +0.0254 ($p=0.690$) | +0.0465 ($p=0.466$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 5 | 2018 | 245 | -0.1248 ($p=0.051$) | +0.0577 ($p=0.368$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 6 | 2019 | 241 | -0.0963 ($p=0.136$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 7 | 2020 | 250 | +0.0143 ($p=0.823$) | -0.0428 ($p=0.501$) | 0.0000 ($p=1.000$) | 0.0000 ($p=1.000$) |
| 8 | 2021 | 248 | **+0.2539** ($p<0.001$) | **+0.0222** ($p=0.728$) | +0.0348 ($p=0.585$) | 0.0000 ($p=1.000$) |

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

To evaluate whether performance is stable across historical market regimes or concentrated in specific eras, results were aggregated across three pre-registered temporal blocks:
- **Block A (2014–2016):** Pre-demonitization & commodity consolidation ($N=728$).
- **Block B (2017–2019):** Low-volatility rally & NBFC crisis ($N=734$).
- **Block C (2020–2021):** COVID-19 crash & rapid recovery ($N=498$).

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
| Window Specification | Mean Pred (bps) | Mean Realized (bps) | Forecast Bias (bps) | Std Pred (bps) | Std Realized (bps) | Residual $p$-val | Placebo Emp. $p$-val |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **W0 (Expanding)** | -4.83 | -8.04 | +3.21 | 4.06 | 89.38 | 0.0346 | **0.0130** |
| **W1 (5Y Rolling)** | -6.75 | -8.04 | +1.29 | 1.85 | 89.38 | 0.9348 | **0.4580** |
| **W2 (3Y Rolling)** | -6.98 | -8.04 | +1.06 | 2.47 | 89.38 | 0.6901 | **0.3420** |
| **W3 (2Y Rolling)** | -6.95 | -8.04 | +1.09 | 3.05 | 89.38 | 1.0000 | **1.0000** |

---

## 7. 2021 FORENSIC ANALYSIS

In Phase 12 Step 6, Fold 8 (2021) was identified as an extreme outlier:
- W0 2021 Residual IC: $+0.2539$ ($p = 0.00005$, Inc $R^2 = +2.20\%$)
- In Step 6, without 2021, the 2014–2020 OOF Residual IC was only $+0.0177$.

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
The apparent high predictability in 2021 under the expanding window (W0) **completely vanished** when training was restricted to the immediate preceding 5 years. This proves that the 2021 result was not a genuine robust intraday market relationship; rather, it was heavily dependent on the model fitting structural historical patterns from 2008–2015 that happened to align with the 2021 post-COVID liquidity environment.

---

## 8. 2017–2019 FORENSIC ANALYSIS

In Step 6, Block B (2017–2019) was negative across all metrics:
- W0 Block B Residual IC: $-0.0284$, Incremental $R^2 = -0.40\%$.

### Step 7 Comparison for Block B:
- Under **W1 (5-Year Rolling)**:
  - Block B Residual IC shifted to $+0.0079$ ($p = 0.8306$), and Incremental $R^2 = +0.014\%$.
  - Fold 4 (2017): $+0.0465$, Fold 5 (2018): $+0.0577$, Fold 6 (2019): $0.0000$.
- Under **W2 (3-Year Rolling)**:
  - Block B Residual IC was $0.0000$ ($p = 1.0000$, Inc $R^2 = +0.000\%$).
- Under **W3 (2-Year Rolling)**:
  - Block B Residual IC was $0.0000$ ($p = 1.0000$, Inc $R^2 = +0.000\%$).

*Scientific Assessment:* The slight reversal of Block B from negative in W0 to near-zero in W1 does not represent improved predictive skill; rather, the model simply experienced parameter shrinkage and reduced variance, driving predictions closer to the unconditional mean.

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

| Window Specification | Observed Residual IC | Observed $p$-val | Placebo Mean IC | Placebo Std IC | Empirical Percentile | Empirical $p$-value |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **W0 (Expanding)** | +0.0477 | 0.0346 | -0.0012 | 0.0226 | 98.70% | **0.0130** |
| **W1 (5Y Rolling)** | +0.0018 | 0.9348 | -0.0000 | 0.0226 | 54.20% | **0.4580** |
| **W2 (3Y Rolling)** | +0.0090 | 0.6901 | -0.0001 | 0.0224 | 65.80% | **0.3420** |
| **W3 (2Y Rolling)** | 0.0000 | 1.0000 | 0.0000 | 0.0000 | 50.05% | **1.0000** |

*Placebo Conclusion:*  
Under W1, the empirical $p$-value is $0.4580$, placing the observed relationship in the exact center of the random permutation distribution. Under alternative window structures, there is **zero statistical evidence** that the predictions have any correspondence with realized residual returns.

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

## 12. LEAKAGE AUDIT

1. **Embargo Integrity:** All training sets end strictly in December of year $Y_k - 1$ ($2013-12-31$ through $2020-12-31$). All validation sets begin in January of year $Y_k$. The minimum causal separation between the last training target observation and the first validation prediction is at least one market close.
2. **Disjoint Indices:** In all 32 fold/window combinations, the intersection of training indices and validation indices is strictly empty:
   $$\mathcal{D}_{\text{train}} \cap \mathcal{D}_{\text{val}} = \emptyset$$
3. **Chronological Inner Validation:** Tree count $N^*$ was selected strictly within the chronological last $20\%$ of each training set. No validation observation was accessible during tree selection.
4. **Feature Sanitization:** Feature extraction was audited to confirm exactly 63 Model 1 features (45 Price + 18 Context). Zero News, Zero Volume, and Zero Flow proxy features.

---

## 13. HOLDOUT FIREWALL PROOF

1. Maximum `trading_date` in all Phase 12 Step 7 datasets: `2021-12-31`.
2. Target date for `2021-12-31` is `2022-01-03` (the next trading day Close-to-Open return), which was realized on the development boundary.
3. Exactly zero rows, records, or sessions with `trading_date >= 2022-01-03` were loaded, read, or evaluated.
4. Terminal Holdout (2022-01-03 through 2026-09-03, $N=1,154$) remains $100\%$ untouched, unconsumed, and quarantined.

---

## 14. ARTIFACT CHECKSUMS

### Generated Step 7 Artifacts (`data/interim/phase12_step7/`):
- `step7_predictions.csv`: `1409da659550bca8cb655e889d1b0d2d385a02ecf2dbe0bda99525c35848bbdc`
- `step7_fold_results.csv`: `53a7a97efce8b4956d35706915386c95a09289cb7ecdc9c2794eb8e3f94e9f3b`
- `step7_temporal_results.csv`: `66bb22cbfe6f483d9e2b109e99c372551a31d9ea410fdb7c6c44fa70c40685e1`
- `step7_summary.csv`: `9a405c9a41c19d4b005feae71616c52a061bb0ee8029583b482f7c0a96dc5622`
- `step7_tree_counts.csv`: `93506720f785085e35fa84803aa788a44b939e6a00c6d7fa0710ba0d6bce72a3`
- `step7_placebo_results.csv`: `f0f9b360ea0f0559eb2491a67ce039478f692025cc502ba14a849405fc9444b0`
- `step7_economic_diagnostic.csv`: `5898858ff49f13e7102b489a2bc158b4f009e45e997fce45c76c0b39dd7567cb`
- `step7_integrity_manifest.json`: `2f9f8c65f958f00030c25a072922119eb45e7f12e1a384e9309228834458fef5`

### Protected Upstream Artifacts Verified:
- Phase 4–10 protected artifacts ($19/19$ verified byte-for-byte)
- Phase 12 Step 5 artifacts ($10/10$ verified byte-for-byte)
- Phase 12 Step 6 artifacts ($7/7$ verified byte-for-byte)

---

## 15. TEST SUITE VERIFICATION

1. **Step 7 Dedicated Test Suite:**
   `pytest -q tests/test_phase12_step7_window_stability.py`
   **Result: 15 passed in 4.21s (100% pass rate).**
2. **Full Repository Regression Suite:**
   `pytest -q`
   **Result: 291 passed in 14.67s (100% pass rate across entire repository).**

---

## 16. FINAL SCIENTIFIC DECISION GATE

Pre-registered decision options:
- A) STABILITY SUPPORTED
- B) STABILITY NOT SUPPORTED
- C) INFORMATION TOO WEAK TO DECIDE

### Selected Decision:
$$\mathbf{B) \; STABILITY \; NOT \; SUPPORTED}$$

### Formal Justification:
1. **Collapsing Correlation:** The residual predictive correlation observed under the expanding window ($+0.0477$) collapses to $+0.0018$ under a 5-year rolling window, and to $0.0000$ under shorter rolling windows.
2. **Disappearing 2021 Signal:** The dramatic 2021 residual IC ($+0.2539$) dissolves completely to $+0.0222$ when evaluated under the 5-year rolling model. The signal was not a persistent market dynamic, but a sample-specific artifact of including 2008–2015 data in the training set for that specific year.
3. **Structural Model Collapse:** Under 3-year and 2-year rolling windows, the model cannot support gradient-boosted tree splits under standard regularization, collapsing into a constant predictor.
4. **Dominance of Base-Rate Short Bias:** All rolling models amplify the unconditional short bias to $\ge 99.5\%$. There is no demonstrable conditional forecasting edge that survives alternative training-window specifications.

---

## 17. GOVERNANCE & STOP CONDITION

**PHASE 12 STEP 7 IS FORMALLY SEALED.**  
**NO PHASE 12 STEP 8 EXECUTION IS AUTHORIZED BY THIS TASK.**
