# PHASE 12 — STEP 6 RESEARCH REPORT
## RESIDUAL SIGNAL & CONDITIONAL FORECASTING RESEARCH
### Snapshot B (08:50 IST) Model 1: Evaluation Beyond Unconditional Drift

---

## 1. Executive Summary

Phase 12 Step 6 investigates whether the existing Snapshot B (08:50 IST) Model 1 contains genuine, conditional predictive information about NIFTY 50 intraday returns after purging the unconditional daytime drift via a strictly out-of-fold, fold-local training baseline.

Step 5 previously demonstrated that the apparent gross profitability of Snapshot B Model 1 ($+7.24$ bps/day) was largely consistent with NIFTY's unconditional daytime negative drift ($-8.04$ bps/day), shorting $90.71\%$ of sessions and exhibiting zero statistically significant alpha over a naive **Always Short** benchmark ($t_{\text{HAC}} = -0.5842, p = 0.5591$).

Step 6 isolates the conditional expectation $E[\varepsilon_t \mid X_t]$ where $R_t = \mu_t + \varepsilon_t$, with $\mu_t$ estimated strictly from prior training observations.

### Core Empirical Findings:
1. **Nominal Aggregate Correlation Survives Centering**:
   The residual Pearson Information Coefficient (IC) is $+0.0477$ ($p = 0.0346$), matching the raw Pearson IC ($+0.0476, p = 0.0350$). Centering by the fold-local training mean baseline does not destroy the linear covariance between predicted and realized return deviations.
2. **Negligible Incremental Explanatory Power**:
   The model achieves an overall incremental $R^2$ of only **$+0.3425\%$** over the historical training baseline. Mean Absolute Error (MAE) improves by a negligible **$0.13$ bps** ($61.07$ bps $\to$ $60.94$ bps), and Root Mean Squared Error (RMSE) improves by only **$0.15$ bps** ($89.46$ bps $\to$ $89.31$ bps).
3. **Coin-Flip Residual Directional Accuracy**:
   While raw predictions exhibited a $53.62\%$ hit rate (by exploiting the market's $53.93\%$ down-drift), directional accuracy on residual returns ($	ext{sign}(\hat{y}_t - \mu_t) == \text{sign}(R_t - \mu_t)$) drops to **$50.26\%$** across all 1,960 sessions.
4. **Failure of Conditional Sign Probabilities**:
   Predicting above-baseline returns provides zero predictive edge:
   $$P(\text{residual} > 0 \mid \text{excess\_pred} > 0) = 48.24\% \quad \text{vs Unconditional } 48.57\% \; (-0.33\%)$$
   $$P(\text{residual} < 0 \mid \text{excess\_pred} < 0) = 51.27\% \quad \text{vs Unconditional } 51.43\% \; (-0.15\%)$$
   Mean residual return following a positive excess forecast is **$-3.38$ bps**.
5. **Severe Temporal Instability (The 2017–2019 Regime Breakdown)**:
   In Block B (2017–2019, $N=734$ sessions), the model completely decoupled from the market, producing a negative Pearson IC ($-0.0284$), negative Spearman IC ($-0.0535$), and **negative incremental $R^2$ ($-0.40\%$)**. In three consecutive years (2017, 2018, 2019), the model was inferior to a naive constant historical mean. The overall positive IC is heavily concentrated in 2021 (IC $= +0.2539$).
6. **Economic Diagnostic Collapse**:
   Trading the residual signal (`sign(excess_prediction)`) yields $+4.83\%$ annualized at 0 bps, but collapses to **$-7.58\%$ at 5 bps** (Sharpe $-0.53$, drawdown $-56.17\%$) and **$-18.53\%$ at 10 bps** (Sharpe $-1.30$, drawdown $-80.72\%$).

**Formal Decision Gate**:
**`B. CONDITIONAL INFORMATION WEAK / INCONCLUSIVE`**

---

## 2. Step 5 Corrected Baseline Context

Phase 12 Step 5 established the foundational baseline decomposition:
- **Intraday Return ($R_{\text{intraday}}$)**: Unconditional mean $-8.04$ bps/day ($53.93\%$ down sessions).
- **Snapshot B Model 1**: Short on $90.71\%$ of sessions, gross mean $+7.24$ bps/day.
- **Naive Always Short**: Gross mean $+8.04$ bps/day.
- **Paired Contrast**: Paired difference $-0.7935$ bps/day ($t_{\text{HAC}} = -0.5842, p = 0.5591$).
- **Resolution**: Incremental alpha beyond unconditional daytime negative drift was not demonstrated.

---

## 3. Research Question & Mathematical Formulation

Does Model 1 contain genuine conditional predictive power about deviations from the training baseline?

Let:
$$R_t = \mu_t + \varepsilon_t$$
where:
- $R_t = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$ is the realized Snapshot B intraday return.
- $\mu_t$ is the fold-local training mean baseline, estimated exclusively from training observations prior to outer fold validation.
- $\varepsilon_t = R_t - \mu_t$ is the realized residual/excess intraday return.
- $\hat{y}_t$ is the frozen Step 2 model forecast.
- $\hat{\varepsilon}_t = \hat{y}_t - \mu_t$ is the model's excess prediction.

We test:
$$H_0: \text{corr}(\hat{\varepsilon}_t, \varepsilon_t) = 0 \quad \text{and} \quad R^2_{\text{inc}} \le 0$$
$$H_1: \text{corr}(\hat{\varepsilon}_t, \varepsilon_t) > 0 \quad \text{and} \quad R^2_{\text{inc}} > 0$$

---

## 4. Protected Inputs & Model Configuration

- **Architecture**: Snapshot B (08:50 IST) Model 1.
- **Feature Set**: Exactly 63 features (45 Price + 18 Context).
- **Exclusions**: 0 News features, 0 Volume features, 0 Flow proxies, 0 Technical indicators.
- **Predictions**: Frozen Out-of-Fold (OOF) predictions from Phase 12 Step 2 / Step 3 (`data/interim/phase12/step3_selective_diagnostics.csv`). Zero model retraining was performed.

---

## 5. Data Provenance & OOF Partitions

- **Development Period**: `2014-01-02` through `2021-12-31` ($N = 1,960$ sessions).
- **Outer Walk-Forward Folds**:
  - Fold 1 (2014): $N = 240$
  - Fold 2 (2015): $N = 244$
  - Fold 3 (2016): $N = 244$
  - Fold 4 (2017): $N = 248$
  - Fold 5 (2018): $N = 245$
  - Fold 6 (2019): $N = 241$
  - Fold 7 (2020): $N = 250$
  - Fold 8 (2021): $N = 248$
- **Terminal Holdout Isolation**: `2022-01-03` to `2026-09-03` ($N = 1,154$) remains permanently quarantined. Zero observations $\ge 2022-01-03$ were accessed.

---

## 6. Residual Target & Excess Prediction Definitions

For each outer fold $k \in \{1, \dots, 8\}$:
1. **Fold-Local Training Baseline ($\mu_k$)**:
   $$\mu_k = \frac{1}{N_{\text{train}, k}} \sum_{i \in \text{Train}_k} R_i$$
2. **Residual Return**:
   $$\varepsilon_t = R_t - \mu_k \quad \forall t \in \text{Val}_k$$
3. **Excess Prediction**:
   $$\hat{\varepsilon}_t = \hat{y}_t - \mu_k \quad \forall t \in \text{Val}_k$$

### Numerical Accounting Verification:
- Target Reconstruction Error: $\max |R_t - (\mu_k + \varepsilon_t)| = 1.73 \times 10^{-18}$ [VERIFIED]
- Prediction Reconstruction Error: $\max |\hat{y}_t - (\mu_k + \hat{\varepsilon}_t)| = 2.17 \times 10^{-19}$ [VERIFIED]

---

## 7. Fold-Local Baseline Values

| Fold ID | Validation Year | Training Period | Training $N$ | Fold Baseline Mean ($\mu_k$) | OOF Realized Mean |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | 2014 | 2008-07-08 to 2013-12-31 | 1,339 | **$-1.9302$ bps** | $+1.4779$ bps |
| **Fold 2** | 2015 | 2008-07-08 to 2014-12-31 | 1,579 | **$-1.4122$ bps** | $-14.7279$ bps |
| **Fold 3** | 2016 | 2008-07-08 to 2015-12-31 | 1,823 | **$-3.1945$ bps** | $-8.1494$ bps |
| **Fold 4** | 2017 | 2008-07-08 to 2016-12-30 | 2,067 | **$-3.7794$ bps** | $-5.9893$ bps |
| **Fold 5** | 2018 | 2008-07-08 to 2017-12-29 | 2,315 | **$-4.0161$ bps** | $-7.6302$ bps |
| **Fold 6** | 2019 | 2008-07-08 to 2018-12-31 | 2,560 | **$-4.3620$ bps** | $-9.4403$ bps |
| **Fold 7** | 2020 | 2008-07-08 to 2019-12-31 | 2,801 | **$-4.7989$ bps** | $-10.6779$ bps |
| **Fold 8** | 2021 | 2008-07-08 to 2020-12-31 | 3,051 | **$-5.2807$ bps** | $-8.9695$ bps |

*Validation sessions never contribute to their own baseline.*

---

## 8. Primary Residual Results Overview

| Metric | Raw (Step 2/5) | Residual (Step 6) | Shift / Impact |
| :--- | :---: | :---: | :---: |
| **Pearson IC** | $+0.0476$ ($p=0.0350$) | **$+0.0477$** ($p=0.0346$) | $+0.0001$ (unaltered) |
| **Spearman IC** | $+0.0426$ ($p=0.0593$) | **$+0.0381$** ($p=0.0921$) | $-0.0045$ (weakened) |
| **Incremental $R^2$** | N/A | **$+0.3425\%$** | Economically negligible |
| **Directional Accuracy** | $53.62\%$ | **$50.26\%$** | Drops to coin-flip |
| **Prediction Direction Split** | $9.3\%$ Long / $90.7\%$ Short | **$32.3\%$ Long / $67.7\%$ Short** | Unconditional drift partially removed |
| **MAE** | $60.94$ bps | **$60.94$ bps** (vs Base $61.07$) | $-0.13$ bps reduction |
| **RMSE** | $89.31$ bps | **$89.31$ bps** (vs Base $89.46$) | $-0.15$ bps reduction |

---

## 9. Baseline vs Model MSE

Evaluating both the fold-local training baseline forecast $\hat{y}_{\text{base}, t} = \mu_k$ and the model forecast $\hat{y}_t$ against realized return $R_t$:
- **Baseline MSE**: $0.000080036$ (RMSE: $89.46$ bps)
- **Model MSE**: $0.000079762$ (RMSE: $89.31$ bps)
- **MSE Difference**: $-0.000000274$ (MSE reduction of $0.34\%$)

---

## 10. Incremental $R^2$ Analysis

The incremental out-of-fold explanatory power is:
$$R^2_{\text{inc}} = 1 - \frac{\text{MSE}_{\text{model}}}{\text{MSE}_{\text{baseline}}} = 1 - \frac{0.000079762}{0.000080036} = \mathbf{+0.003425 \; (+0.3425\%)}$$

While mathematically positive, an incremental $R^2$ of $0.34\%$ indicates that over $99.65\%$ of the return variance remains unexplained by the model beyond the unconditional historical training drift.

---

## 11. Residual Information Coefficients

- **Residual Pearson IC**:
  $$\rho_{\text{Pearson}}(\hat{\varepsilon}_t, \varepsilon_t) = \mathbf{+0.0477} \quad (t = 2.1129, \; p = 0.0346)$$
- **Residual Spearman Rank IC**:
  $$\rho_{\text{Spearman}}(\hat{\varepsilon}_t, \varepsilon_t) = \mathbf{+0.0381} \quad (t = 1.6853, \; p = 0.0921)$$

The rank correlation drops below the standard $5\%$ significance threshold ($p = 0.0921$), confirming that the linear correlation is sensitive to outlier observations in specific years.

---

## 12. Fold-by-Fold Detailed Results

| Fold | Year | Sessions | Baseline $\mu_k$ | Realized Raw | Mean Excess Pred | Pearson IC | Pearson $p$ | Spearman IC | Incremental $R^2$ | Residual Hit Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 2014 | 240 | $-1.93$ bps | $+1.48$ bps | $-0.89$ bps | **$+0.1095$** | $0.0906$ | $+0.0595$ | **$+0.28\%$** | $52.08\%$ |
| **2** | 2015 | 244 | $-1.41$ bps | $-14.73$ bps | $-1.81$ bps | **$+0.0382$** | $0.5527$ | $+0.0773$ | **$+0.61\%$** | $57.38\%$ |
| **3** | 2016 | 244 | $-3.19$ bps | $-8.15$ bps | $-2.03$ bps | **$+0.0746$** | $0.2459$ | $+0.0446$ | **$+0.76\%$** | $52.05\%$ |
| **4** | 2017 | 248 | $-3.78$ bps | $-5.99$ bps | $-2.03$ bps | **$+0.0254$** | $0.6903$ | $+0.0071$ | **$-0.50\%$** | $50.81\%$ |
| **5** | 2018 | 245 | $-4.02$ bps | $-7.63$ bps | $-0.78$ bps | **$-0.1248$** | $0.0510$ | $-0.1135$ | **$-0.46\%$** | $42.45\%$ |
| **6** | 2019 | 241 | $-4.36$ bps | $-9.44$ bps | $-0.85$ bps | **$-0.0963$** | $0.1361$ | $-0.1364$ | **$-0.30\%$** | $46.89\%$ |
| **7** | 2020 | 250 | $-4.80$ bps | $-10.68$ bps | $-0.16$ bps | **$+0.0143$** | $0.8225$ | $+0.0557$ | **$+0.03\%$** | $50.00\%$ |
| **8** | 2021 | 248 | $-5.28$ bps | $-8.97$ bps | $-1.21$ bps | **$+0.2539$** | $<0.0001$ | $+0.1701$ | **$+2.20\%$** | $50.81\%$ |

### Fold Consistency Summary:
- **Positive Pearson IC Folds**: 6 of 8 ($75.0\%$)
- **Negative Pearson IC Folds**: 2 of 8 ($25.0\%$) — Folds 5 & 6 (2018 & 2019)
- **Negative Incremental $R^2$ Folds**: 3 of 8 ($37.5\%$) — Folds 4, 5 & 6 (2017, 2018 & 2019)
- **Mean Fold IC**: $+0.0368$ (Median: $+0.0318$, Std: $0.1185$)

---

## 13. Temporal Stability Analysis

| Epoch / Block | Sessions | Pearson IC | Pearson $p$ | Spearman IC | Incremental $R^2$ | Residual Directional Accuracy | Model MSE | Baseline MSE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Block A (2014–2016)** | 728 | **$+0.0622$** | $0.0935$ | $+0.0693$ | **$+0.59\%$** | $53.85\%$ | $0.000065$ | $0.000066$ |
| **Block B (2017–2019)** | 734 | **$-0.0284$** | $0.4422$ | $-0.0535$ | **$-0.40\%$** | $46.73\%$ | $0.000044$ | $0.000044$ |
| **Block C (2020–2021)** | 498 | **$+0.1081$** | $0.0158$ | $+0.1082$ | **$+0.50\%$** | $50.40\%$ | $0.000154$ | $0.000154$ |

### Structural Temporal Breakdown:
In Block B (2017–2019), the model suffered complete structural failure:
- Pearson IC is **negative** ($-0.0284$).
- Rank correlation is **negative** ($-0.0535$).
- Incremental $R^2$ is **negative** ($-0.40\%$).
- Residual directional accuracy is **worse than chance** ($46.73\%$).

---

## 14. Conditional Sign & Base-Rate Test

Does predicting an above-baseline return provide information about achieving above-baseline realization?

- **Unconditional Probabilities**:
  - $P(\varepsilon_t > 0) = 48.57\%$ ($952 / 1,960$)
  - $P(\varepsilon_t < 0) = 51.43\%$ ($1,008 / 1,960$)
- **Conditional Probabilities**:
  - Positive Excess Predictions: $N = 626$ ($31.94\%$)
    $$P(\varepsilon_t > 0 \mid \hat{\varepsilon}_t > 0) = \mathbf{48.24\%} \quad (\text{Diff}: -0.33\%)$$
  - Negative Excess Predictions: $N = 1,334$ ($68.06\%$)
    $$P(\varepsilon_t < 0 \mid \hat{\varepsilon}_t < 0) = \mathbf{51.27\%} \quad (\text{Diff}: -0.15\%)$$
- **Conditional Realized Returns**:
  - Mean Residual Return given $\hat{\varepsilon}_t > 0$: **$-3.38$ bps/day** (Median: $-2.96$ bps)
  - Mean Residual Return given $\hat{\varepsilon}_t < 0$: **$-4.92$ bps/day** (Median: $-2.40$ bps)

**Inference**: The model possesses zero conditional sign skill. Conditioning on a positive excess prediction yields a lower probability of positive residual return than unconditional random selection ($48.24\%$ vs $48.57\%$).

---

## 15. Magnitude Calibration Analysis

Reusing the exact Step 4 magnitude bins applied to $|\hat{\varepsilon}_t|$:

| Bin Name | Observation Count | % of Total | Mean Excess Pred | Mean Residual Ret | Median Residual Ret | MAE (bps) | Hit Rate | 95% Confidence Interval | Sample Size Tier |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0–5 bps** | 1,630 | $83.16\%$ | $-0.51$ bps | $-3.16$ bps | $-2.16$ bps | $60.03$ | $49.26\%$ | $[-7.40, +1.08]$ bps | Inferential ($N \ge 50$) |
| **5–10 bps** | 260 | $13.27\%$ | $-3.57$ bps | $-9.77$ bps | $-7.42$ bps | $67.83$ | $53.46\%$ | $[-22.35, +2.80]$ bps | Inferential ($N \ge 50$) |
| **10–15 bps** | 51 | $2.60\%$ | $-8.72$ bps | $-12.31$ bps | $-2.49$ bps | $54.81$ | $58.82\%$ | $[-34.40, +9.78]$ bps | Inferential ($N \ge 50$) |
| **15–20 bps** | 18 | $0.92\%$ | $-9.25$ bps | $-19.95$ bps | $-22.40$ bps | $63.66$ | $72.22\%$ | $[-60.17, +20.26]$ bps | Descriptive Only ($N < 50$) |
| **20+ bps** | 1 | $0.05\%$ | $-21.97$ bps | $-3.70$ bps | $-3.70$ bps | $18.28$ | $100.00\%$ | Descriptive Only | Descriptive Only ($N < 50$) |

### Calibration Finding:
Over $96.4\%$ of observations ($1,890 / 1,960$) fall into the $0–10$ bps bins where directional accuracy is between $49.3\%$ and $53.5\%$. While bins $10–15$ and $15–20$ show negative mean realized returns, sample sizes are small and standard errors are wide ($[-34.4, +9.8]$ bps).

---

## 16. Placebo / Permutation Null Test

- **Null Hypothesis**: The excess predictions $\hat{\varepsilon}_t$ have no time-series pairing with realized residual returns $\varepsilon_t$.
- **Methodology**: $1,000$ random permutations of $\hat{\varepsilon}_t$ against $\varepsilon_t$ using fixed documented random seed $42$.
- **Results**:
  - Observed Residual Pearson IC: **$+0.0477$**
  - Placebo Null Mean IC: **$-0.0012$**
  - Placebo Null Std IC: **$0.0226$**
  - Empirical Percentile: **$98.70\%$**
  - Empirical One-Sided $p$-value: **$0.0130$**

*Methodological Limitation*: Simple permutation does not preserve autocorrelation. As documented in Section 19, Newey-West HAC inference yields $p = 0.0346$.

---

## 17. Economic Diagnostic (Zero Live Trading Intent)

Evaluating `position = sign(excess_prediction)` executed strictly against `residual_return`:

| Strategy / Cost Scenario | Active Sessions | Long / Short | Exposure | Cumulative Return | Annualized Return | Annualized Volatility | Sharpe Ratio | Maximum Drawdown |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Residual Signal (0 bps)** | 1,960 | 626 / 1,334 | 100.0% | **$+44.31\%$** | **$+4.83\%$** | $14.20\%$ | **$+0.34$** | **$-29.41\%$** |
| **Residual Signal (5 bps)** | 1,960 | 626 / 1,334 | 100.0% | **$-45.84\%$** | **$-7.58\%$** | $14.20\%$ | **$-0.53$** | **$-56.17\%$** |
| **Residual Signal (10 bps)** | 1,960 | 626 / 1,334 | 100.0% | **$-79.69\%$** | **$-18.53\%$** | $14.20\%$ | **$-1.30$** | **$-80.72\%$** |
| **Residual Signal (20 bps)** | 1,960 | 626 / 1,334 | 100.0% | **$-97.15\%$** | **$-36.70\%$** | $14.20\%$ | **$-2.58$** | **$-97.19\%$** |
| **Always Residual Long (0 bps)** | 1,960 | 1,960 / 0 | 100.0% | $-61.19\%$ | $-11.46\%$ | $14.19\%$ | $-0.81$ | $-66.60\%$ |
| **Always Residual Long (10 bps)** | 1,960 | 1,960 / 0 | 100.0% | $-94.54\%$ | $-31.20\%$ | $14.19\%$ | $-2.20$ | $-94.82\%$ |
| **Always Residual Short (0 bps)** | 1,960 | 0 / 1,960 | 100.0% | $+120.23\%$ | $+10.68\%$ | $14.19\%$ | $+0.75$ | $-13.66\%$ |
| **Always Residual Short (10 bps)** | 1,960 | 0 / 1,960 | 100.0% | $-68.99\%$ | $-13.97\%$ | $14.19\%$ | $-0.98$ | $-70.84\%$ |

### Economic Finding:
The residual conditional signal has a breakeven friction of less than **$2.0$ bps**. At institutional transaction costs ($5$ to $10$ bps), the residual strategy suffers severe, catastrophic decay.

---

## 18. Short-Drift Decomposition: What Disappears?

| Feature / Metric | Raw Analysis (Step 5) | Residual Analysis (Step 6) | Discrepancy / Explanation |
| :--- | :---: | :---: | :---: |
| **Target Return Mean** | $-8.04$ bps/day | **$-4.43$ bps/day** | Baseline adjustment removes $-3.61$ bps of historical drift |
| **Model Forecast Mean** | $-4.98$ bps/day | **$-1.37$ bps/day** | Model forecast was predominantly negative intercept |
| **Directional Bias** | $90.71\%$ Short | **$67.70\%$ Short** | Bias decreases, but model still tilts short |
| **Directional Hit Rate** | $53.62\%$ | **$50.26\%$** | **$3.36\%$ hit rate vanishes** once baseline drift is removed |
| **Gross Strategy Return** | $+7.24$ bps/day | **$+1.86$ bps/day** | **$74.3\%$ of gross strategy return is erased** |

**Conclusion**: Almost three-quarters ($74.3\%$) of the raw gross trading return observed in Step 2/3 was pure capture of unconditional daytime negative drift.

---

## 19. Statistical Inference & Econometric Modeling

Linear regression of realized residual returns on excess predictions:
$$\varepsilon_t = \alpha + \beta \hat{\varepsilon}_t + u_t$$
- Intercept ($\alpha$): **$-3.1120$ bps/day**
- Slope ($\beta$): **$1.0803$**
- OLS Standard Error: $0.5108$ $\to$ $t = 2.1149$ ($p = 0.0346$)
- Newey-West HAC Standard Error ($L=7$): $0.5113$ $\to$ $t = \mathbf2.1129$ ($p = \mathbf0.0346$)
- $R^2$: **$0.002279$ ($0.2279\%$)**

---

## 20. Multiple Testing & False Discovery Rate (FDR)

Across the 8 outer folds, Benjamini-Hochberg FDR adjustment at $\alpha = 0.05$:
- Fold 8 ($p = 0.000052$) survives FDR ($q < 0.001$).
- Fold 5 ($p = 0.0510$, negative IC) fails FDR.
- Fold 1 ($p = 0.0906$) fails FDR.
- Folds 2, 3, 4, 6, 7 all have $p > 0.13$.

Only **one single fold** (Fold 8, 2021) exhibits statistically significant residual IC after FDR correction.

---

## 21. Methodological Limitations

1. **Inner Tree Shrinkage ($N^*=10$)**: In Folds 1, 5, 6, and 7, extreme shrinkage compressed predictions, limiting cross-sectional variation.
2. **Serial Dependence**: While Newey-West HAC accounts for low-order autocorrelation, structural macroeconomic regimes (2017–2019 bull market) induce multi-year regime shifts.
3. **No Liquidity / Microstructure**: Spread dynamics at Open and Close are not modeled.

---

## 22. Holdout Firewall Attestation

- Development range: `2014-01-02` to `2021-12-31`.
- Verified zero records on or after `2022-01-03`.
- Terminal holdout remains permanently sealed and unaccessed.

---

## 23. Master Artifact SHA-256 Registry

| File Path | Size (Bytes) | SHA-256 Checksum |
| :--- | :---: | :--- |
| `scripts/phase12_step6_residual_signal.py` | 18,789 | `756ed00a2f1299874b2ff75113d6e616e381dc433697f10436dc4cf018392ed5` |
| `data/interim/phase12/phase12_step6_residual_predictions.csv` | 259,738 | `41dae563cbb48f2ab84cf1b8f18edf190abbecdf82d5b7104e797a63755604af` |
| `data/interim/phase12/phase12_step6_fold_results.csv` | 2,921 | `317e9fb735347351be6e4bb44b807b6f419aaa0021badf20f19b2e2cc8b36c11` |
| `data/interim/phase12/phase12_step6_temporal_results.csv` | 2,138 | `85e901e45e6327640131011460146b0221956d0a2f8ae15e8c6be1aceea6dfe8` |
| `data/interim/phase12/phase12_step6_magnitude.csv` | 1,065 | `f2f82819aad307aa5816dce101da847e52964ea880ddb6c9ea85293357467181` |
| `data/interim/phase12/phase12_step6_placebo.csv` | 397 | `a6e30a69c9a2229ddcb5855360cb2a54d214672b6ea4c201688afee388dbf9d1` |
| `data/interim/phase12/phase12_step6_economic_diagnostic.csv` | 1,352 | `19341254f4448d6a0628313c909d6b4ab82843f64363853a584961d8160041ce` |
| `data/interim/phase12/phase12_step6_manifest.json` | 898 | `cd39329b02772d81c5594bb1d3342795c8384f692952f4b293b8599c10bc6453` |
| `tests/test_phase12_step6_residual_signal.py` | 7,947 | `d3d388ef8c7baeb4482de339e24a7c3fc99c656579ad5f852f448b9a755b8eca` |

---

## 24. Test Suite Execution & Verification

1. **Step 6 Dedicated Test Suite**:
   `pytest -q tests/test_phase12_step6_residual_signal.py`
   $$\mathbf{10\text{ passed in } 5.01\text{s}}$$
2. **Full Repository Regression Suite**:
   `pytest -q`
   $$\mathbf{276\text{ passed in } 21.45\text{s}}$$

---

## 25. Formal Decision Gate Resolution

Among the four pre-registered decision outcomes:
- `A. CONDITIONAL INFORMATION DETECTED`
- `B. CONDITIONAL INFORMATION WEAK / INCONCLUSIVE`
- `C. SIGNAL CONSISTENT WITH UNCONDITIONAL DRIFT`
- `D. METHODOLOGY FAILURE`

The forensic audit conclusively dictates:

### **`B. CONDITIONAL INFORMATION WEAK / INCONCLUSIVE`**

#### Scientific Grounding:
1. **Some Residual Covariance Exists**: The overall residual Pearson IC is nominally positive ($+0.0477, p = 0.0346$), with a regression slope of $\beta = 1.0803$ ($t_{\text{HAC}} = 2.1129, p = 0.0346$), and a placebo permutation percentile of $98.70\%$ ($p = 0.0130$).
2. **Statistical and Temporal Stability is Insufficient**:
   - For an entire 3-year epoch (Block B: 2017–2019, $N=734$), the model completely decoupled from the market, producing negative ICs and negative incremental $R^2$.
   - Directional accuracy on residual returns is strictly $50.26\%$ (coin-flip).
   - Conditional probability of above-baseline return given an above-baseline prediction is $48.24\%$ (lower than random chance).
   - Only 1 of 8 folds survives False Discovery Rate (FDR) adjustment.
   - The economic diagnostic collapses at 5 bps round-trip friction.

---

## 26. Formal Interpretation & Governance Statement

In strict compliance with pre-registered research governance:
> *"OOF evidence indicates statistically detectable but weak and temporally unstable conditional information under the tested residual-return specification. Incremental explanatory power ($R^2 = +0.34\%$) is economically negligible and does not support live trading or production deployment."*

---

## 27. Formal Seal & Stop Condition

**PHASE 12 STEP 6 IS FORMALLY SEALED.**

**NO PHASE 12 STEP 7 EXECUTION IS AUTHORIZED BY THIS TASK.**
