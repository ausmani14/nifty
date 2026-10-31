# NIFTY AI — PHASE 12 STEP 2 RESEARCH REPORT
# SNAPSHOT B MORNING-TO-CLOSE INTRADAY TARGET RESEARCH
## Expanding Walk-Forward Validation & Diagnostic Economic Evaluation (2014–2021)

**Execution Date**: September 18, 2026  
**Auditor**: Lead Quantitative Researcher & Forensic Validation Agent  
**Dataset**: Snapshot B (08:50 IST information set)  
**Partition Scope**: Strictly Development (`2008-07-08` through `2021-12-31`, $N = 3,299$)  
**Holdout Firewall**: Sealed Terminal Holdout (`2022-01-03` through `2026-09-03`, $N = 1,154$) — ZERO ACCESS / PERMANENTLY QUARANTINED  
**Feature Architecture**: Model 1 (63 Features: 45 Price + 18 Context, 0 News)  
**Validation Engine**: 8-Fold Expanding Walk-Forward (`2014` through `2021`, $N_{\text{OOF}} = 1,960$ sessions)  
**Hyperparameter Selection**: Inner Chronological Split on Training Folds (Validation on most recent 20% to select tree count $N^*$)  

---

## 1. Executive Summary & Decision Gate Determination

### Core Finding
Aligning the Snapshot B (08:50 IST) information set with the subsequent same-day intraday return target:
$$R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$$
demonstrates a **statistically detectable positive out-of-fold linear association** on development data ($2014–2021$, $N = 1,960$):
* **Aggregate OOF Pearson IC**: $+0.0476$ ($p = 0.0350$, statistically significant at $\alpha = 0.05$)
* **Aggregate OOF Spearman IC**: $+0.0426$ ($p = 0.0593$, marginally significant at $\alpha = 0.10$)
* **Model RMSE vs Zero Baseline**: $0.008931$ vs $0.008971$ (Diebold-Mariano $t = -3.11$, $p = 0.0019$)

However, when translated into an unrestricted diagnostic trading policy taking positions daily ($100\%$ session exposure, 1,960 round-trip trades), the strategy encounters severe economic friction:
* **Gross Return ($0$ bps)**: $+18.25\%$ annualized, Sharpe $+1.29$, Max Drawdown $-14.55\%$, Newey-West HAC $t = +3.95$ ($p = 7.79 \times 10^{-5}$).
* **Breakeven Transaction Friction**: **$7.24$ bps/trade**.
* **Institutional Cost ($10$ bps)**: **$-6.95\%$ annualized**, Sharpe $-0.49$, Max Drawdown $-53.55\%$, Newey-West HAC $t = -1.50$ ($p = 0.1326$).
* **Friction Decay**: Because trades are taken every single session ($252$ trades/year), every 10 bps round-trip cost subtracts exactly $25.2\%$ annualized performance ($252 \times 0.0010 = 0.0252$).
* **Directional Asymmetry & Drift Conflation**: The underlying intraday market exhibits a heavy negative drift ($-14.01\%$ annualized across development, $-20.25\%$ annualized over 2014–2021 OOF). The model captures this drift by predicting negative returns on $90.71\%$ of sessions ($1,778 / 1,960$). Its directional hit rate ($53.62\%$) slightly underperforms a naive **Always-Short** baseline ($53.93\%$).

### Formal Decision Gate Determination

$$\mathbf{DECISION\ GATE:\ B)\ WEAK\ /\ INCONCLUSIVE}$$

#### Quantitative Justification:
1. **Predictive Association is Present**: A positive OOF association is detected ($IC = +0.0476, p = 0.0350$; Diebold-Mariano $p = 0.0019$). Overnight US equity indices (S&P 500: $5.31\%$, Hang Seng: $5.27\%$) and energy/currency commodities were among the higher-weighted features ($32.44\%$ context split weight).
2. **Economic Survivability Fails Institutional Hurdle**: The strategy does not clear the 10 bps institutional transaction cost threshold ($7.24$ bps breakeven vs $10.0$ bps hurdle). At 10 bps, net annual return is $-6.95\%$ and 7 out of 8 folds suffer net losses.
3. **Temporal Instability**: The signal inverts during stress regimes (Fold 5 / 2018 IL&FS crisis: $IC = -0.1248$; Fold 6 / 2019 corporate tax cut rally: $IC = -0.0963$).
4. **Drift Mimicry Risk**: The model functions primarily as a short-biased drift harvester ($90.7\%$ short exposure) rather than demonstrating balanced two-sided classification skill.

Under our charter as skeptical quantitative researchers, Gate A is rejected because an unconstrained model cannot be deployed profitably at realistic costs, and Gate C is rejected because statistical association and gross performance are demonstrably positive. **Gate B accurately reflects a statistically detectable association that is economically constrained by turnover and friction.**

---

## 2. Hypothesis & Target Alignment Rationale

### The Structural Flaw in Prior Phases
In Phases 4 through 11, Model 1 was trained on Close-to-Close returns:
$$R_{\text{close\_to\_close}}(T+1) = \frac{\text{Close}(T+1) - \text{Close}(T)}{\text{Close}(T)}$$
When Phase 11 evaluated execution at $T+1$ Open $\to$ $T+1$ Close, the model was tested on an objective function orthogonal to its training target. As established in Phase 12 Step 1:
$$(1 + R_{\text{overnight}})(1 + R_{\text{intraday}}) - 1 \equiv R_{\text{close\_to\_close}}$$
where:
* $R_{\text{overnight}}$ has an annualized drift of **$+27.70\%$**.
* $R_{\text{intraday}}$ has an annualized drift of **$-14.01\%$**.
* The sample correlation between $R_{\text{overnight}}$ and $R_{\text{intraday}}$ is $-0.0190$ ($p = 0.274$), demonstrating they are fundamentally orthogonal market processes.

Training a model on $R_{\text{close\_to\_close}}$ forced the algorithm to learn the overnight drift. Testing it intraday forced it to fight the negative intraday drift with a model that anticipated an upward trajectory.

### The Phase 12 Step 2 Aligned Formulation
Snapshot B captures the market state at 08:50 IST on Day $T+1$, exactly 25 minutes before the NSE cash market opens at 09:15 IST.
At 08:50 IST:
1. All global overnight equity markets (US closes, European closes, Asian morning developments) are known.
2. Overnight commodity shifts (Brent, WTI, Gold) and currency dynamics (USD/INR) are known.
3. Domestic Indian 10Y yield and India VIX from Day $T$ close are known.
4. **NIFTY Open($T+1$) and Close($T+1$) are completely unknown.**

By setting the target specifically to:
$$R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$$
the regressor is evaluated on whether the 08:50 IST information set contains linear predictability regarding the subsequent Open-to-Close return.

---

## 3. Forensic Data Integrity & Holdout Quarantine Proof

### Absolute Holdout Firewall
The sealed Terminal Holdout (`2022-01-03` through `2026-09-03`, $N = 1,154$) was consumed in Phase 11 Stage 2 and remains permanently locked.
* **Target Dataset (`snapshot_b_intraday_target_dev.csv`)**:
  * Min Date: `2008-07-08`
  * Max Date: `2021-12-31`
  * Total Sessions: $3,299$
  * Terminal Holdout Observations: **EXACTLY ZERO** (verified programmatically).
* **OOF Diagnostics (`snapshot_b_intraday_diagnostics.csv`)**:
  * Min Date: `2014-01-02`
  * Max Date: `2021-12-31`
  * Total Sessions: $1,960$
  * Terminal Holdout Observations: **EXACTLY ZERO**.

### Protected Artifact Checksums
All 19 sealed Phase 4–10 baseline artifacts were audited via SHA-256 before model execution. All 19 hashes matched byte-for-byte with zero discrepancy.

### Temporal Causality Proof
* Feature vector timestamp: $\le 08:50$ IST Day $T+1$.
* Cash market opening: $09:15$ IST Day $T+1$.
* Cash market closing: $15:30$ IST Day $T+1$.
* Zero lookahead: Neither Open($T+1$), High($T+1$), Low($T+1$), nor Close($T+1$) enter the feature vector. Reference prices and price features derive exclusively from Day $T$ (closing at 15:30 IST yesterday) and earlier.

---

## 4. Experimental Setup & Model Architecture

### Governance Rules
1. **Model Hierarchy**: Model 1 = Price + Context (63 features: 45 Price + 18 Context). Zero News features allowed.
2. **Cross-Validation**: 8-fold expanding walk-forward validation on development data:
   * Fold 1 (2014): Train 2008–2013 ($N = 1,339$) $\to$ Val 2014 ($N = 240$)
   * Fold 2 (2015): Train 2008–2014 ($N = 1,579$) $\to$ Val 2015 ($N = 244$)
   * Fold 3 (2016): Train 2008–2015 ($N = 1,823$) $\to$ Val 2016 ($N = 244$)
   * Fold 4 (2017): Train 2008–2016 ($N = 2,067$) $\to$ Val 2017 ($N = 248$)
   * Fold 5 (2018): Train 2008–2017 ($N = 2,315$) $\to$ Val 2018 ($N = 245$)
   * Fold 6 (2019): Train 2008–2018 ($N = 2,560$) $\to$ Val 2019 ($N = 241$)
   * Fold 7 (2020): Train 2008–2019 ($N = 2,801$) $\to$ Val 2020 ($N = 250$)
   * Fold 8 (2021): Train 2008–2020 ($N = 3,051$) $\to$ Val 2021 ($N = 248$)
   * Total OOF Sessions: $1,960$.
3. **Hyperparameter Selection ($N^*$)**:
   To eliminate the arbitrary reuse of Phase 6's $N^* = 43$ (which was tuned on Close-to-Close returns), an inner chronological validation split was conducted on the training set of each fold (last $20\%$ as inner validation). Candidates evaluated: $N \in [10, 15, 20, 25, 30, 35, 40, 45, 50, 60]$.
   * Base Hyperparameters: `learning_rate = 0.05`, `max_depth = 2`, `min_child_weight = 20.0`, `subsample = 0.8`, `colsample_bytree = 0.7`, `reg_alpha = 0.5`, `reg_lambda = 2.0`, `n_jobs = -1`.
   * Selected $N^*$ per fold:
     * Folds 1, 5, 6, 7 selected $N^* = 10$ (conservative shrinkage).
     * Folds 2, 4 selected $N^* = 60$.
     * Fold 3 selected $N^* = 45$.
     * Fold 8 selected $N^* = 40$.

---

## 5. Out-of-Fold Predictive Performance

### Summary Table: Predictive Accuracy ($N = 1,960$)

| Metric | Model 1 (Intraday) | Zero Forecast Baseline | Historical Mean Baseline | Statistical Test / Significance |
| :--- | :---: | :---: | :---: | :--- |
| **MAE** | **0.006094** | 0.006121 | 0.006107 | Lower point error than both baselines |
| **RMSE** | **0.008931** | 0.008971 | 0.008946 | DM Stat: $-3.11$ ($p = 0.0019$) |
| **Pearson IC** | **+0.0476** | $0.0000$ | N/A | **$t = 2.11$, $p = 0.0350$** (Significant at $5\%$) |
| **Spearman IC** | **+0.0426** | $0.0000$ | N/A | **$p = 0.0593$** (Marginally Significant at $10\%$) |
| **Directional Hit Rate** | **53.62%** | N/A | N/A | vs Always Long: $46.07\%$ \| vs Always Short: $53.93\%$ |
| **Forecast Bias** | **+0.000321** | $0.0000$ | N/A | Under-predicts negative drift magnitude |

### Diebold-Mariano Hypothesis Test
* Null Hypothesis $H_0$: Expected squared error loss of Model 1 equals Zero Forecast baseline.
* Alternative $H_1$: Expected squared error loss of Model 1 is strictly lower than Zero Forecast baseline.
* Test Statistic: $t = -3.11$.
* Asymptotic $p$-value: $0.00190$.
* **Interpretation**: Reject $H_0$. Model 1 delivers point forecasts with strictly lower squared error than the zero forecast benchmark. This test evaluates forecast accuracy, not trading profitability.

---

## 6. Fold-by-Fold Performance Breakdown

| Fold | Era / Market Regime | Year | Train $N$ | Val $N$ | Selected $N^*$ | Pearson IC ($p$-val) | Spearman IC ($p$-val) | Hit Rate | Ann Net Ret (10 bps) | Sharpe (10 bps) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | General Election & Bull Rally | 2014 | 1,339 | 240 | 10 | **+0.1095** ($0.091$) | +0.0595 ($0.359$) | 53.75% | -21.45% | -1.92 |
| **2** | Commodity Deflation & Consolidation | 2015 | 1,579 | 244 | 60 | **+0.0382** ($0.553$) | +0.0773 ($0.229$) | 56.15% | -5.44% | -0.39 |
| **3** | Demonetization & Volatility Shock | 2016 | 1,823 | 244 | 45 | **+0.0746** ($0.246$) | +0.0446 ($0.488$) | 55.33% | -8.78% | -0.65 |
| **4** | Low-Volatility Secular Bull | 2017 | 2,067 | 248 | 60 | **+0.0254** ($0.690$) | +0.0071 ($0.912$) | 52.42% | -17.64% | -2.30 |
| **5** | IL&FS Credit Crisis & Correction | 2018 | 2,315 | 245 | 10 | **-0.1248** ($0.051$) | -0.1135 ($0.076$) | 52.65% | -6.80% | -0.61 |
| **6** | Tax Cut & Pre-COVID Rally | 2019 | 2,560 | 241 | 10 | **-0.0963** ($0.136$) | -0.1364 ($0.034$) | 56.43% | -1.41% | -0.12 |
| **7** | COVID-19 Crash & Rapid Rebound | 2020 | 2,801 | 250 | 10 | **+0.0143** ($0.823$) | +0.0557 ($0.380$) | 49.60% | -7.89% | -0.32 |
| **8** | Post-COVID Global Expansion | 2021 | 3,051 | 248 | 40 | **+0.2539** ($5.2 \times 10^{-5}$) | **+0.1701** ($0.007$) | 52.82% | **+13.51%** | **+1.05** |

### Key Fold Observations:
1. **IC Consistency**: 6 of 8 folds produce positive Pearson correlation.
2. **Signal Inversion in 2018 & 2019**: Both 2018 (IL&FS crisis) and 2019 (corporate tax cut announcement) produced negative ICs. This demonstrates temporal instability during domestic structural and policy shocks, decoupling intraday cash dynamics from overnight international cues.
3. **2021 Performance**: In 2021, global macroeconomic co-movement was pronounced, yielding a Pearson IC of $+0.2539$ ($p < 0.0001$) and positive net returns after costs ($+13.51\%$).

---

## 7. Directional Hit Rate vs Naive Baselines

| Strategy / Predictor | Directional Accuracy ($N = 1,960$) | Long Session Count | Short Session Count | Directional Skew |
| :--- | :---: | :---: | :---: | :--- |
| **Model 1 (Intraday)** | **53.62%** ($1,051 / 1,960$) | 182 ($9.29\%$) | 1,778 ($90.71\%$) | Heavily Short-Biased |
| **Always Short Baseline** | **53.93%** ($1,057 / 1,960$) | 0 ($0.00\%$) | 1,960 ($100.00\%$) | Ride negative intraday drift |
| **Always Long Baseline** | **46.07%** ($903 / 1,960$) | 1,960 ($100.00\%$) | 0 ($0.00\%$) | Standard passive buy-and-hold |

### Forensic Directional Analysis
The model's overall directional accuracy ($53.62\%$) is marginally lower than the naive Always-Short baseline ($53.93\%$).
* The market had 1,057 down sessions and 903 up sessions during 2014–2021.
* An Always-Short naive trader scores $1,057 / 1,960 = 53.93\%$.
* Model 1 predicted UP on 182 sessions. Of those 182 long calls, 96 were correct and 86 were incorrect.
* Because the model took those 86 losing long trades instead of shorting them, its overall hit rate was reduced by 6 sessions relative to the pure short heuristic.
* **Interpretation**: The directional result does NOT demonstrate balanced two-sided classification skill. Rather, the model's accuracy is substantially driven by the negative historical intraday drift, combined with occasional long predictions.

---

## 8. Forecast Calibration, Dispersion & Bias Analysis

### Distributional Characteristics
* **Realized Target $R_{\text{intraday}}$**:
  * Mean: $-0.000804$ ($-20.25\%$ annualized)
  * Standard Deviation: $0.008938$ ($14.19\%$ annualized)
  * Min: $-0.0742$, Max: $+0.0487$
* **Predicted Target $\widehat{R}_{\text{intraday}}$**:
  * Mean: $-0.000483$ ($-12.16\%$ annualized)
  * Standard Deviation: $0.000406$ ($0.64\%$ annualized)
  * Min: $-0.002339$, Max: $+0.001383$

### Dispersion & Shrinkage
The ratio of prediction standard deviation to realized standard deviation is:
$$\frac{\sigma(\widehat{y})}{\sigma(y)} = \frac{0.000406}{0.008938} = 0.0454\ (4.54\%)$$
This illustrates severe tree-based regularized shrinkage. The XGBoost regressor outputs predictions clustered tightly between $-23$ bps and $+14$ bps, reflecting the low signal-to-noise ratio inherent in daily returns.

### Forecast Bias
$$\text{Bias} = \mathbb{E}[\widehat{y}] - \mathbb{E}[y] = -0.000483 - (-0.000804) = +0.000321\ (+8.09\%\ \text{ann})$$
The positive bias indicates that while the model recognized the negative drift, it underestimated its severity by approximately $3.2$ bps per session.

---

## 9. Economic Diagnostic Performance across Cost Scenarios

Diagnostics were executed using an unrestricted sign policy:
$$\text{Position}(T+1) = \text{sign}(\widehat{R}_{\text{intraday}}(T+1)) \in \{+1, -1\}$$
Executed at Open($T+1$), exited at Close($T+1$), for all 1,960 OOF sessions.

### Economic Diagnostic Results Table ($N_{\text{OOF}} = 1,960$)

| Round-Trip Cost | Ann Net Return | Annualized Vol | Sharpe Ratio | Max Drawdown | Win Rate | Profit Factor | Newey-West HAC $t$-stat | HAC $p$-value |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.0 bps** | **+18.25%** | 14.20% | **+1.29** | **-14.55%** | 53.62% | 1.27 | **+3.95** | **$7.79 \times 10^{-5}$** |
| **2.5 bps** | **+11.95%** | 14.20% | **+0.84** | **-15.21%** | 51.63% | 1.17 | **+2.59** | **$9.68 \times 10^{-3}$** |
| **5.0 bps** | **+5.65%** | 14.20% | **+0.40** | **-16.91%** | 50.41% | 1.08 | **+1.22** | $0.2212$ |
| **7.24 bps** | **0.00%** | 14.20% | **0.00** | **-30.12%** | 48.91% | 1.00 | $0.00$ | $1.0000$ |
| **7.5 bps** | **-0.65%** | 14.20% | **-0.05** | **-32.70%** | 48.72% | 0.99 | $-0.14$ | $0.8884$ |
| **10.0 bps** | **-6.95%** | 14.20% | **-0.49** | **-53.55%** | 47.24% | 0.91 | **-1.50** | $0.1326$ |
| **15.0 bps** | **-19.55%** | 14.20% | **-1.38** | **-81.01%** | 44.13% | 0.78 | **-4.23** | **$2.32 \times 10^{-5}$** |
| **20.0 bps** | **-32.15%** | 14.20% | **-2.26** | **-92.68%** | 41.02% | 0.66 | **-6.96** | **$3.44 \times 10^{-12}$** |

```
                     ECONOMIC ATTRITION DECAY CURVE
   Net Ann Ret (%)
     +20% |  * (0 bps: +18.25%)
     +15% |     \
     +10% |        * (2.5 bps: +11.95%)
      +5% |           \
       0% |--------------* (Breakeven: 7.24 bps)----------------------
      -5% |                 \  * (10 bps: -6.95%)
     -10% |                    \
     -15% |                       \
     -20% |                          * (15 bps: -19.55%)
     -25% |                             \
     -30% |                                \  * (20 bps: -32.15%)
          +-----------------------------------------------------------
          0 bps   2.5 bps  5 bps  7.5 bps  10 bps  15 bps  20 bps
```

---

## 10. Attrition / Cost Decay Curve Analysis

### Mathematical Derivation of Frictional Decay
Because the diagnostic policy enters every morning and exits every evening:
$$\text{Annual Turnover} = 252\ \text{trades/year}$$
The relationship between net annualized return $R_{\text{net}}$ and round-trip cost $C_{\text{bps}}$ is strictly linear:
$$R_{\text{net}}(C_{\text{bps}}) = R_{\text{gross}} - (252 \times C_{\text{bps}} \times 10^{-4})$$
$$R_{\text{net}}(C_{\text{bps}}) = 0.1825 - 0.0252 \times C_{\text{bps}}$$

### Critical Thresholds
1. **Gross Daily Edge**: $7.24$ bps ($0.000724$ daily return).
2. **Breakeven Friction**: Exactly **$7.24$ bps/trade**. Any transaction friction exceeding $7.24$ bps turns the strategy net-negative.
3. **Attrition Velocity**: Every $1.0$ bps of execution cost eliminates **$2.52\%$ annualized net return**.
4. **Institutional Hurdle Deficit**: In liquid Indian equity index futures / options, realistic all-in institutional execution costs (bid-ask spread + STT + exchange fees + stamp duty + slippage) range between **$8$ and $12$ bps**. At 10 bps, the strategy experiences an annual drag of $-25.2\%$, converting an $18.25\%$ gross diagnostic return into a $-6.95\%$ net loss.

---

## 11. Feature Importance & Signal Attribution

### Top 15 Features across 8 Walk-Forward Folds

| Rank | Feature Name | Domain Group | Mean Importance | Cumulative | Diagnostic Notes |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1** | `sma_20` | Price Trend | **7.54%** | 7.54% | Medium-term trend benchmark |
| **2** | `close_pos_in_range` | Price Structure | **6.14%** | 13.68% | Previous session closing position within range |
| **3** | `sma_200` | Price Trend | **6.09%** | 19.77% | Long-term trend anchor |
| **4** | `ctx_ret_1d_sp500` | Global Equity | **5.31%** | 25.08% | Overnight US equity movement |
| **5** | `ctx_ret_1d_hang_seng` | Regional Equity | **5.27%** | 30.35% | Asian pre-market sentiment |
| **6** | `ret_1d` | Price Momentum | **4.06%** | 34.41% | Prior day Close-to-Close return |
| **7** | `ctx_ret_1d_brent_crude` | Commodities | **3.78%** | 38.19% | Overnight crude oil shift |
| **8** | `hl_range_pct` | Price Volatility | **3.76%** | 41.95% | Day $T$ session range |
| **9** | `ret_2d` | Price Momentum | **3.12%** | 45.07% | Short-term 2-day price change |
| **10** | `ctx_diff_1d_usd_inr` | Currency | **2.91%** | 47.98% | Overnight currency differential |
| **11** | `volatility_5d` | Price Volatility | **2.84%** | 50.82% | Realized rolling short-term volatility |
| **12** | `ctx_ret_1d_wti_crude` | Commodities | **2.82%** | 53.64% | US crude oil return |
| **13** | `high_to_close_dist` | Price Structure | **2.71%** | 56.35% | Day $T$ high-to-close distance |
| **14** | `ctx_level_india_vix` | Domestic Vol | **2.21%** | 58.56% | Implied volatility level |
| **15** | `ctx_diff_1d_india_10y_yield` | Rates | **2.21%** | 60.77% | Sovereign bond yield shift |

### Domain Attribution Breakdown
* **45 Price Features**: **67.56%** total split weight.
* **18 Context Features**: **32.44%** total split weight.
* **Observation**: Context features were among the higher-weighted features associated with tree splits, which is consistent with the hypothesis that overnight international and macro context contains relevant information for same-day domestic price formation.

---

## 12. Comparison with Prior Close-to-Close Model 1

| Property | Phase 6 / 11 Close-to-Close Model 1 | Phase 12 Step 2 Aligned Intraday Model 1 | Methodological Notes |
| :--- | :--- | :--- | :--- |
| **Target Variable** | $\text{Close}(T+1) / \text{Close}(T) - 1$ | $\text{Close}(T+1) / \text{Open}(T+1) - 1$ | Target strictly isolated to Open $\to$ Close |
| **Target Drift** | $+13.69\%$ annualized (Dev) | **$-14.01\%$ annualized (Dev)** | **$-27.7\%$** drift differential |
| **Information Set** | Snapshot A (15:30 IST) / B (08:50 IST) | Snapshot B (08:50 IST only) | Aligned immediately prior to Open($T+1$) |
| **Intraday Pearson IC** | $+0.0189$ ($p = 0.403$) in Phase 10 | **+0.0476** ($p = 0.0350$) in Phase 12 | Shift to statistically detectable correlation |
| **Intraday Spearman IC** | $+0.0134$ ($p = 0.552$) in Phase 10 | **+0.0426** ($p = 0.0593$) in Phase 12 | Shift in rank correlation |
| **Gross Return (0 bps)** | $-14.0\%$ annualized (Phase 11 S1 OOF) | **+18.25% annualized** | Reflects aligned drift expectation |
| **Sharpe Ratio (0 bps)** | $-0.95$ in Phase 11 S1 | **+1.29** in Phase 12 Step 2 | Gross diagnostic ratio |
| **10 bps Net Return** | $-39.2\%$ annualized in Phase 11 S1 | **-6.95% annualized** | Net performance remains negative at 10 bps |

### Methodological Interpretation
This comparison serves as a diagnostic validation of target alignment. In Phase 11, evaluating a Close-to-Close trained model on Open-to-Close execution produced large gross losses because the model expected upward drift. Direct training on the Open-to-Close target aligned the prediction sign with the negative intraday drift. **This does not imply that target realignment alone creates deployable alpha; rather, it resolves an objective mismatch.**

---

## 13. Risks, Leakage Checks & Governance Disclaimers

### 1. Leakage Forensic Audit
* Verified: No future price data ($T+1$ Open, High, Low, Close) exists in the feature matrix $X$.
* Verified: Context features represent Day $T$ close values for US/European markets and pre-market 08:50 IST readings for Asian indices.
* Verified: Inner hyperparameter tuning used only chronological historical observations from within each training fold.

### 2. High Turnover Risk
Trading every single session ($252$ trades per year) exposes capital to immense frictional drag ($25.2\%$ drag per 10 bps). A model that trades every session without position selectivity cannot survive real-world market microstructure frictions.

### 3. Drift Dependency Risk
The model took short positions on $90.71\%$ of OOF sessions. It largely reflects the empirical $-14\%$ to $-20\%$ intraday drift. If market dynamics change, a persistent short bias is exposed to substantial drawdown risk.

### 4. Regime Inversion Risk
As demonstrated in Folds 5 (2018) and 6 (2019), domestic structural shocks can decouple Indian intraday returns from global overnight cues. During such regimes, reliance on global context produced negative correlation ($IC = -0.12$).

### 5. Mandatory Governance Statements
* **The 2022–2026 Terminal Holdout remains completely untouched and quarantined.**
* **No live trading is justified or authorized based on these results.**
* **Step 2 represents development/OOF research only.**
* **The result is hypothesis-generating, not proof of deployable trading alpha.**
* **No threshold, position gating, or sizing optimization has been performed.**
* **No conclusion about the optimal future trading rule is allowed or asserted.**

---

## 14. Decision Gate Evaluation Matrix

| Decision Gate | Evaluation Criteria | Empirical Finding | Criteria Satisfied? |
| :--- | :--- | :--- | :---: |
| **Gate A: Supports Further Research** | 1. Statistically significant positive IC ($p < 0.05$)<br>2. Superior point forecasts vs Zero baseline ($p < 0.05$)<br>3. Positive gross economic alpha ($> 0$ bps)<br>4. **Economically viable after realistic costs ($\ge 10$ bps)**<br>5. Substantially beats naive directional baselines | 1. Pearson IC $= +0.0476, p = 0.0350$ (YES)<br>2. DM test $p = 0.0019$ (YES)<br>3. Gross Return $= +18.25\%$, Sharpe $1.29$ (YES)<br>4. **Fails 10 bps: Net Ann $= -6.95\%$ (NO)**<br>5. Hit rate $53.62\%$ vs Always Short $53.93\%$ (NO) | **NO** |
| **Gate B: Weak / Inconclusive** | 1. Positive predictive relationship detected ($IC > 0$)<br>2. Gross performance present but heavily decayed by frictions<br>3. Breakeven costs below institutional hurdle ($< 10$ bps)<br>4. Inconsistent fold stability or heavy directional skew<br>5. Does not warrant immediate live trading, but justifies target restructuring | 1. Verified ($IC = +0.0476, p = 0.0350$)<br>2. Verified ($+18.25\%$ gross decays to $-6.95\%$ at 10 bps)<br>3. Verified (Breakeven is $7.24$ bps $< 10.0$ bps)<br>4. Verified (2018/2019 negative ICs; $90.7\%$ short)<br>5. Verified (Confirms intraday target validity) | **YES** |
| **Gate C: Does Not Support Hypothesis** | 1. Near-zero or negative IC ($p > 0.20$)<br>2. Fails to outperform Zero forecast baseline<br>3. Negative gross returns at 0 bps | 1. IC is positive and significant ($p = 0.0350$)<br>2. Strictly outperforms Zero baseline ($p = 0.0019$)<br>3. Gross return is $+18.25\%$ ($p < 0.0001$) | **NO** |

---

## 15. Concluding Assessment & Next Steps

### Quantitative Conclusion
Phase 12 Step 2 establishes that **Snapshot B contains a statistically detectable linear association with same-day intraday NIFTY returns**:
1. Training directly on Open-to-Close returns produced a positive OOF Pearson IC of **$+0.0476$** ($p = 0.0350$).
2. Morning global context features were among the higher-weighted split features ($32.44\%$ split weight).
3. However, an unconstrained daily turnover trading policy is economically unviable after institutional transaction costs ($7.24$ bps breakeven vs $10.0$ bps hurdle).
4. Live deployment or proceeding to live trading is strictly unviable under this raw formulation.

### Governance Status
* **Step 2 is complete and audited.**
* **The 2022–2026 Terminal Holdout remains sealed and untouched.**
* **No trading strategy optimization or Step 3 execution is authorized by this report.**

---
*Report certified by Lead Quantitative Researcher & Forensic Validation Agent.*
