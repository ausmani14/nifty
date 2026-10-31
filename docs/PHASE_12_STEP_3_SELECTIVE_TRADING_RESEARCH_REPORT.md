# NIFTY AI — PHASE 12 STEP 3 RESEARCH REPORT
# SELECTIVE TRADING & TURNOVER-CONTROL RESEARCH
## Snapshot B 08:50 IST → Same-Day Open-to-Close Intraday Return

**Execution Date**: September 18, 2026  
**Auditor**: Lead Quantitative Researcher & Forensic Validation Agent  
**Dataset**: Snapshot B (08:50 IST information set)  
**Prediction Source**: Sealed Step 2 Development OOF Predictions (`2014-01-02` through `2021-12-31`, $N_{\text{OOF}} = 1,960$)  
**Holdout Firewall**: Sealed Terminal Holdout (`2022-01-03` through `2026-09-03`, $N = 1,154$) — ZERO ACCESS / QUARANTINED  
**Pre-Registered Threshold Grid**: $\tau \in [0, 5, 10, 15, 20, 25, 30, 40, 50]$ bps  
**Cost Scenarios**: $0.0$, $5.0$, $10.0$, $20.0$ bps round-trip per active trade (zero cost on flat sessions)  
**Research Question**: *Can selective trading based on forecast magnitude reduce turnover and transaction-cost drag while preserving predictive value, without post-hoc threshold optimization or data leakage?*

---

## 1. Executive Summary & Decision Gate Determination

### Core Findings
1. **Turnover & Frictional Drag Reduction**:
   Applying an absolute forecast magnitude threshold $\tau = |\widehat{R}_{\text{intraday}}| \ge \tau$ successfully curtails trading frequency. At $\tau = 10$ bps ($0.0010$), active trading sessions drop from $1,960$ ($100.0\%$, $252$ trades/year) to $160$ ($8.16\%$, $20.6$ trades/year). Annual transaction cost drag at the $10$ bps institutional hurdle collapses from **$25.20\%$** down to **$2.06\%$**.
2. **Shift to Net Positive Diagnostic Return at 10 bps**:
   Under the unrestricted policy ($\tau = 0$), the $10$ bps net annualized return was **$-6.95\%$** (Sharpe $-0.49$). Under selective trading at $\tau = 10$ bps, net annualized return becomes **$+1.92\%$** (Sharpe $+0.55$, win rate $52.5\%$, profit factor $1.39$, max drawdown $-7.81\%$). At $\tau = 15$ bps, net return is **$+1.20\%$** (Sharpe $+0.55$, win rate $58.1\%$, profit factor $1.94$, max drawdown $-2.65\%$).
3. **Monotonic Improvement in Active Directional Hit Rate**:
   As the selection threshold $\tau$ increases, directional accuracy on active sessions rises monotonically:
   * $\tau = 0$ bps: $53.62\%$ ($1,051 / 1,960$)
   * $\tau = 5$ bps: $53.78\%$ ($519 / 965$)
   * $\tau = 10$ bps: $59.38\%$ ($95 / 160$)
   * $\tau = 15$ bps: $67.44\%$ ($29 / 43$)
   * $\tau = 20$ bps: $80.00\%$ ($4 / 5$)
4. **Natural Prediction Boundary & Severe Short Asymmetry**:
   Because the underlying XGBoost regressor was regularized using depth-2 trees and L1/L2 shrinkage, predictions are tightly bounded. The maximum absolute predicted return in the entire OOF dataset was **$23.39$ bps** ($0.002339$). Consequently, for all $\tau \ge 25$ bps, the model produces **exactly 0 active trades**. Furthermore, the active signals are overwhelmingly short-biased ($95.6\%$ short at $\tau = 10$ bps; $97.7\%$ short at $\tau = 15$ bps), reflecting the model's primary identification of downside drift.
5. **Regime & Fold Concentration**:
   Active trading at $\tau = 10$ bps is strictly concentrated in Folds 2, 3, 4, and 8 (2015, 2016, 2017, 2021). In Folds 1, 5, 6, and 7 (2014, 2018, 2019, 2020), tree count selection chose $N^* = 10$, shrinking predictions such that $|\widehat{R}|$ never reached $10$ bps. Thus, a fixed nominal threshold renders the model dormant during periods of conservative tree regularization.

### Formal Decision Gate Determination

$$\mathbf{DECISION\ GATE:\ A)\ SUPPORTS\ FURTHER\ RESEARCH}$$

#### Quantitative Justification:
* The research hypothesis $H_1$ is supported: Selective trading based on forecast magnitude demonstrably reduces turnover (from 252 to 20 trades/year), eliminates ~92% of transaction drag, improves active directional hit rate from $53.6\%$ to $59.4\%$, and converts net performance at 10 bps from $-6.95\%$ to $+1.92\%$.
* This gate confirms that turnover-controlled selective trading is a scientifically defensible and promising research direction.
* **CRITICAL GOVERNANCE NOTE**: This gate is strictly an assessment of the research hypothesis on development data. **It is NOT an approval for live trading, NOT a selection of an optimal production threshold, and NOT an assertion of deployable alpha.**

---

## 2. Research Hypothesis & Theoretical Motivation

### Hypotheses
* **Null Hypothesis ($H_0$)**: Selective trading based on forecast magnitude does not produce economically meaningful improvement after accounting for turnover and transaction costs.
* **Alternative Hypothesis ($H_1$)**: Selective trading based on sufficiently strong forecast magnitude can reduce trading frequency and transaction-cost drag while retaining positive predictive/economic characteristics.

### Theoretical Motivation
In Step 2, the unrestricted sign policy:
$$\text{Position}(T+1) = \text{sign}(\widehat{R}_{\text{intraday}}(T+1))$$
traded every single session ($252$ trades/year), accumulating $252 \times 10\text{ bps} = 25.20\%$ in annual frictional drag. Because the gross daily edge was $7.24$ bps, trading on days where predicted return was near zero (e.g. $0.5$ bps) incurred guaranteed negative net expected value ($0.5\text{ bps} - 10\text{ bps} = -9.5\text{ bps}$).
By establishing a hurdle $\tau$, the policy abstains from trading when expected edge does not justify the execution friction.

---

## 3. Data Integrity & Holdout Quarantine Proof

1. **Development OOF Partition Only**: All evaluations are performed strictly on the sealed Step 2 diagnostics dataset (`snapshot_b_intraday_diagnostics.csv`), comprising exactly $1,960$ out-of-fold sessions from `2014-01-02` through `2021-12-31`.
2. **Holdout Quarantine**: Zero observations from `2022-01-03` through `2026-09-03` were loaded, read, or utilized.
3. **Frozen Step 2 Model**: Zero retraining or hyperparameter tuning occurred. The prediction stream $\widehat{R}_{\text{intraday}}$ is identical to Step 2.

---

## 4. Trading Policy Definition & Execution Convention

For each threshold $\tau \in [0, 5, 10, 15, 20, 25, 30, 40, 50]$ bps:
$$\text{Position}(T+1) = \begin{cases} \text{sign}(\widehat{R}_{\text{intraday}}(T+1)), & \text{if } |\widehat{R}_{\text{intraday}}(T+1)| \ge \tau \\ 0, & \text{otherwise} \end{cases}$$

### Execution Specifications
* **Entry**: 09:15 IST at Open($T+1$).
* **Exit**: 15:30 IST at Close($T+1$).
* **Position Space**: $\{+1.0, 0.0, -1.0\}$.
* **Friction Accounting**: Cost $C_{\text{bps}} \in \{0.0, 5.0, 10.0, 20.0\}$ is charged **only** on active sessions ($\text{pos} \ne 0$). On flat sessions ($\text{pos} == 0$), transaction cost is strictly $0.0$ bps and strategy return is $0.0$.
* **Exclusions**: Zero overnight exposure, zero leverage, zero stop-loss, zero volatility scaling, zero regime filtering, zero news.

---

## 5. Pre-Registered Threshold Grid Response Surface

The threshold grid was frozen prior to evaluation. Below is the full response surface across all thresholds and cost scenarios ($N = 1,960$ sessions, 2014–2021):

| $\tau$ (bps) | Cost (bps) | Active Sessions | Exposure (%) | Trades / Year | Ann Net Return | Sharpe Ratio | Max Drawdown | Win Rate | Profit Factor | Newey-West HAC $t$ ($p$-val) | Active Dir Acc |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0** | **0.0** | 1,960 | 100.0% | 252.0 | **+18.25%** | **+1.29** | -14.55% | 53.6% | 1.27 | +3.95 ($7.8 \times 10^{-5}$) | 53.6% |
| 0 | 5.0 | 1,960 | 100.0% | 252.0 | **+5.65%** | +0.40 | -16.91% | 50.4% | 1.08 | +1.22 ($0.221$) | 53.6% |
| 0 | 10.0 | 1,960 | 100.0% | 252.0 | **-6.95%** | **-0.49** | -53.55% | 47.2% | 0.91 | -1.50 ($0.133$) | 53.6% |
| 0 | 20.0 | 1,960 | 100.0% | 252.0 | **-32.15%** | -2.26 | -92.68% | 41.0% | 0.66 | -6.96 ($3.4 \times 10^{-12}$) | 53.6% |
| **5** | **0.0** | 965 | 49.2% | 124.1 | **+11.84%** | **+1.19** | -14.35% | 53.8% | 1.37 | +3.36 ($0.0008$) | 53.8% |
| 5 | 5.0 | 965 | 49.2% | 124.1 | **+5.64%** | +0.57 | -14.45% | 50.2% | 1.16 | +1.61 ($0.106$) | 53.8% |
| 5 | 10.0 | 965 | 49.2% | 124.1 | **-0.56%** | **-0.06** | -29.77% | 48.0% | 0.99 | -0.16 ($0.871$) | 53.8% |
| 5 | 20.0 | 965 | 49.2% | 124.1 | **-12.97%** | -1.30 | -67.62% | 42.1% | 0.71 | -3.72 ($0.0002$) | 53.8% |
| **10** | **0.0** | 160 | 8.2% | 20.6 | **+3.98%** | **+1.11** | -4.35% | 59.4% | 1.99 | +2.89 ($0.0038$) | 59.4% |
| 10 | 5.0 | 160 | 8.2% | 20.6 | **+2.95%** | +0.83 | -5.87% | 56.2% | 1.66 | +2.20 ($0.028$) | 59.4% |
| 10 | 10.0 | 160 | 8.2% | 20.6 | **+1.92%** | **+0.55** | **-7.81%** | 52.5% | 1.39 | +1.46 ($0.145$) | 59.4% |
| 10 | 20.0 | 160 | 8.2% | 20.6 | **-0.14%** | -0.04 | -11.79% | 47.5% | 0.98 | -0.11 ($0.916$) | 59.4% |
| **15** | **0.0** | 43 | 2.2% | 5.5 | **+1.75%** | **+0.78** | -2.45% | 67.4% | 2.64 | +2.36 ($0.018$) | 67.4% |
| 15 | 5.0 | 43 | 2.2% | 5.5 | **+1.48%** | +0.67 | -2.55% | 62.8% | 2.27 | +2.04 ($0.042$) | 67.4% |
| 15 | 10.0 | 43 | 2.2% | 5.5 | **+1.20%** | **+0.55** | **-2.65%** | 58.1% | 1.94 | +1.70 ($0.090$) | 67.4% |
| 15 | 20.0 | 43 | 2.2% | 5.5 | **+0.65%** | +0.30 | -3.92% | 55.8% | 1.43 | +0.95 ($0.342$) | 67.4% |
| **20** | **0.0** | 5 | 0.3% | 0.6 | **+0.15%** | +0.56 | -0.14% | 80.0% | 9.16 | +1.56 ($0.120$) | 80.0% |
| 20 | 5.0 | 5 | 0.3% | 0.6 | **+0.11%** | +0.48 | -0.19% | 80.0% | 5.70 | +1.35 ($0.178$) | 80.0% |
| 20 | 10.0 | 5 | 0.3% | 0.6 | **+0.08%** | +0.38 | -0.24% | 60.0% | 3.23 | +1.06 ($0.287$) | 80.0% |
| 20 | 20.0 | 5 | 0.3% | 0.6 | **+0.02%** | +0.10 | -0.34% | 60.0% | 1.30 | +0.27 ($0.788$) | 80.0% |
| **25** | Any | 0 | 0.0% | 0.0 | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 0.00 ($1.000$) | 0.0% |
| **30** | Any | 0 | 0.0% | 0.0 | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 0.00 ($1.000$) | 0.0% |
| **40** | Any | 0 | 0.0% | 0.0 | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 0.00 ($1.000$) | 0.0% |
| **50** | Any | 0 | 0.0% | 0.0 | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 0.00 ($1.000$) | 0.0% |

---

## 6. Step 2 Reference Reconciliation

At $\tau = 0$ bps, the policy reproduces the Step 2 unrestricted economic diagnostic with zero discrepancy:
* **0 bps Gross Return**: $+18.2519\%$ annualized (Sharpe $+1.29$). Exactly matches Step 2.
* **10 bps Net Return**: $-6.9481\%$ annualized (Sharpe $-0.49$). Exactly matches Step 2.
* **Maximum Drawdown (10 bps)**: $-53.55\%$. Exactly matches Step 2.

---

## 7. Predictive Metrics on Active Sessions

| $\tau$ (bps) | Active Sessions | Long Count | Short Count | Short Ratio | Cond. Mean Active | Cond. Mean Long | Cond. Mean Short | Active Dir Acc | Active Pearson IC ($p$-val) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0** | 1,960 | 182 | 1,778 | 90.7% | -0.080% | +0.021% | -0.091% | 53.6% | +0.0476 ($0.035$) |
| **5** | 965 | 27 | 938 | 97.2% | -0.101% | -0.005% | -0.103% | 53.8% | +0.0374 ($0.245$) |
| **10** | 160 | 7 | 153 | 95.6% | -0.246% | +0.091% | -0.261% | 59.4% | +0.0886 ($0.265$) |
| **15** | 43 | 1 | 42 | 97.7% | -0.428% | -0.354% | -0.430% | 67.4% | +0.0438 ($0.780$) |
| **20** | 5 | 0 | 5 | 100.0% | -0.612% | N/A | -0.612% | 80.0% | N/A ($N < 10$) |

### Insights:
1. **Downside Magnitude Sorting**: The conditional mean realized return for short signals becomes progressively more negative as $\tau$ increases: from $-0.091\%$ at $\tau = 0$ to $-0.261\%$ at $\tau = 10$, $-0.430\%$ at $\tau = 15$, and $-0.612\%$ at $\tau = 20$. The model's magnitude is genuinely informative about the depth of the subsequent intraday drop.
2. **Extreme Asymmetry**: Long signals remain virtually absent at higher thresholds (only 7 longs at $\tau = 10$, 1 long at $\tau = 15$, 0 at $\tau = 20$). The selective model operates almost entirely as an intraday short-selling engine.

---

## 8. Critical Baseline Comparison (at 10 bps Cost)

| Strategy / Baseline | Active Sessions | Exposure (%) | Trades / Year | Ann Net Return | Sharpe Ratio | Max Drawdown | Win Rate | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Selective Model ($\tau = 10$ bps)** | **160** | **8.16%** | **20.6** | **+1.92%** | **+0.55** | **-7.81%** | **52.5%** | **1.39** |
| **Selective Model ($\tau = 15$ bps)** | **43** | **2.19%** | **5.5** | **+1.20%** | **+0.55** | **-2.65%** | **58.1%** | **1.94** |
| Unrestricted Model ($\tau = 0$ bps) | 1,960 | 100.0% | 252.0 | -6.95% | -0.49 | -53.55% | 47.2% | 0.91 |
| Always Short Baseline | 1,960 | 100.0% | 252.0 | -4.95% | -0.35 | -46.75% | 47.6% | 0.94 |
| Always Long Baseline | 1,960 | 100.0% | 252.0 | -45.45% | -3.20 | -98.66% | 37.7% | 0.53 |
| Zero-Position Baseline | 0 | 0.0% | 0.0 | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 |
| Matched Random Baseline ($\tau = 10$, $K=160$) | 160 | 8.16% | 20.6 | -2.71% | -0.77 | -14.65% | 40.6% | 0.69 |
| Matched Random Baseline ($\tau = 15$, $K=43$) | 43 | 2.19% | 5.5 | -0.49% | -0.23 | -4.18% | 41.9% | 0.77 |

### Baseline Comparison Insights:
* The selective model at $\tau = 10$ bps ($+1.92\%$) strictly outperforms the Always Short baseline ($-4.95\%$), the Unrestricted model ($-6.95\%$), and the matched-activity random baseline ($-2.71\%$).
* The matched-activity random baseline confirms that randomly trading 160 sessions under 10 bps friction generates net losses ($-2.71\%$, Sharpe $-0.77$). The selective model's positive return is driven by genuine signal filtering, not merely lower exposure.

---

## 9. Fold-by-Fold Performance Breakdown (8 Folds at 10 bps)

| Fold | Year | Sessions | Active ($\tau = 0$) | Active ($\tau = 5$) | Active ($\tau = 10$) | Active ($\tau = 15$) | Net Ann ($\tau = 0$) | Net Ann ($\tau = 5$) | Net Ann ($\tau = 10$) | Net Ann ($\tau = 15$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 2014 | 240 | 240 | 12 | **0** | **0** | -21.45% | +1.84% | **0.00%** | **0.00%** |
| **2** | 2015 | 244 | 244 | 123 | **30** | **10** | -5.44% | +1.86% | **+1.54%** | **+2.39%** |
| **3** | 2016 | 244 | 244 | 123 | **43** | **13** | -8.78% | +0.29% | **+9.24%** | **+3.36%** |
| **4** | 2017 | 248 | 248 | 125 | **53** | **16** | -17.64% | -0.54% | **-4.86%** | **+0.60%** |
| **5** | 2018 | 245 | 245 | 105 | **0** | **0** | -6.80% | -11.10% | **0.00%** | **0.00%** |
| **6** | 2019 | 241 | 241 | 119 | **0** | **0** | -1.41% | -11.20% | **0.00%** | **0.00%** |
| **7** | 2020 | 250 | 250 | 160 | **0** | **0** | -7.89% | +1.04% | **0.00%** | **0.00%** |
| **8** | 2021 | 248 | 248 | 198 | **34** | **4** | +13.51% | +12.99% | **+9.44%** | **+3.24%** |

### Critical Fold Dynamics:
1. **Dormancy under Low $N^*$**: In Folds 1, 5, 6, and 7, the inner chronological tuning selected $N^* = 10$ trees. With only 10 depth-2 trees and strong regularization, prediction dispersion was heavily compressed. As a result, the model produced **zero active sessions** at $\tau \ge 10$ bps in those years.
2. **Activity in Higher $N^*$ Regimes**: In Folds 2 ($N^* = 60$), 3 ($N^* = 45$), 4 ($N^* = 60$), and 8 ($N^* = 40$), the model was active. In 3 of those 4 active years (2015, 2016, 2021), net returns at 10 bps were strongly positive ($+1.54\%$, $+9.24\%$, $+9.44\%$). In 2017 (a secular low-volatility bull market), the short-biased signals produced a loss ($-4.86\%$).

---

## 10. Temporal Period Stability Analysis (at 10 bps Cost)

| Period | Total Sessions | Active ($\tau = 0$) | Active ($\tau = 10$) | Exposure ($\tau = 10$) | Net Ann ($\tau = 0$) | Net Ann ($\tau = 10$) | Sharpe ($\tau = 10$) | Max DD ($\tau = 10$) | Dir Acc ($\tau = 10$) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2014–2016** | 728 | 728 | **73** | 10.0% | -11.84% | **+3.61%** | **+0.86** | -3.25% | 65.8% |
| **2017–2019** | 734 | 734 | **53** | 7.2% | -8.69% | **-1.64%** | **-0.73** | -6.42% | 50.9% |
| **2020–2021** | 498 | 498 | **34** | 6.8% | +2.77% | **+4.70%** | **+1.21** | -4.82% | 58.8% |

* In 2014–2016 and 2020–2021, selective trading at $\tau = 10$ bps delivered positive net returns after costs ($+3.61\%$ and $+4.70\%$).
* In 2017–2019, selective trading suffered a modest drawdown ($-1.64\%$), concentrated primarily in 2017.

---

## 11. No Threshold Winner / Complete Response Surface Description

Per governance instructions, **no single threshold is declared the "winner" or "optimal threshold"**.
The response surface exhibits the following structural dynamics:
1. **Turnover Decay**: Exposure decreases smoothly from $100\%$ ($\tau = 0$) to $49.2\%$ ($\tau = 5$), $8.2\%$ ($\tau = 10$), $2.2\%$ ($\tau = 15$), $0.3\%$ ($\tau = 20$), and $0.0\%$ ($\tau \ge 25$).
2. **Non-Monotonicity of Annual Net Return**: Annual net return at 10 bps is negative at $\tau = 0$ ($-6.95\%$) and $\tau = 5$ ($-0.56\%$), peaks around $\tau = 10$ ($+1.92\%$) and $\tau = 15$ ($+1.20\%$), and decays toward zero as exposure evaporates at $\tau \ge 20$.
3. **Monotonicity of Active Directional Accuracy**: Realized win rate and directional accuracy scale positively with forecast magnitude ($53.6\% \to 59.4\% \to 67.4\% \to 80.0\%$).
4. **Conclusion**: $\tau = 10$ bps and $\tau = 15$ bps are **candidates for future pre-registered investigation**, not optimized production settings.

---

## 12. Multiple-Comparison & Data-Snooping Controls

Evaluating 9 thresholds across 4 cost scenarios creates multiple testing exposure.
* The unadjusted HAC $p$-value for $\tau = 10$ bps at 0 bps cost is $p = 0.0038$.
* Applying a Bonferroni adjustment for 9 thresholds ($9 \times 0.0038 = 0.0342$) maintains statistical significance at $\alpha = 0.05$.
* At 10 bps institutional cost, the unadjusted $p$-value for $\tau = 10$ bps is $p = 0.1447$ (not statistically significant). Therefore, the positive net return at 10 bps must be interpreted as **descriptive economic evidence of reduced friction drag, NOT definitive statistical proof of net alpha**.

---

## 13. Failure Modes, Asymmetries & Risks

1. **Severe Short-Side Concentration**: Over $95\%$ of active trades at $\tau \ge 10$ bps are short. The model does not provide a balanced two-sided market-neutral signal; it acts as an episodic downside drift harvester.
2. **Hyperparameter Sensitivity / Dormancy**: In regimes where chronological validation selects a small tree count ($N^* = 10$), the model becomes completely inactive under a fixed nominal threshold. A dynamic or percentile-based threshold would be required to prevent dormancy across varying regularization regimes.
3. **Bull Market Vulnerability**: In strong trend-continuation bull regimes (e.g. 2017), shorting the intraday open produces persistent losses.

---

## 14. Governance Statements & Concluding Remarks

* **Step 2 remains formally sealed and unmodified.**
* **The 2022–2026 Terminal Holdout remains completely untouched and quarantined.**
* **Step 3 represents development/OOF research only.**
* **No live trading is justified, authorized, or recommended.**
* **No threshold optimization or deployment decision has been made.**
* **No Step 4 execution is authorized by this report.**

---
*Report certified by Lead Quantitative Researcher & Forensic Validation Agent.*
