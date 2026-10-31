# PHASE 12 — OVERNIGHT / INTRADAY RETURN DECOMPOSITION & TARGET REDESIGN
## METHODOLOGY DESIGN & SKEPTICAL DATA AUDIT REPORT

**Date**: September 18, 2026  
**Author**: Senior ML/Quant Research Engineer (Skeptical Quantitative Review)  
**Phase**: Phase 12 — Methodology Design + Data Audit Only  
**Scope**: Development Partition Only (`2008-07-08` through `2021-12-31`, $N=3,299$)  
**Holdout Firewall Status**: **2022–2026 TERMINAL HOLDOUT CONSUMED & STRICTLY QUARANTINED**  

---

## 1. Executive Summary & Decision Gate Verdict

```
========================================================================================
DECISION GATE VERDICT:
B) CONDITIONALLY JUSTIFIED — ADDITIONAL STRUCTURAL PREREQUISITES REQUIRED BEFORE IMPLEMENTATION
========================================================================================
```

### Core Scientific Findings of the Audit
1. **Mathematical Validation of the Return Decomposition**:
   The decomposition identity:
   $$(1 + R_{\text{overnight}}) \times (1 + R_{\text{intraday}}) - 1 \equiv R_{\text{close\_to\_close}}$$
   holds exactly across all 3,299 development sessions (maximum numerical error: $2.22 \times 10^{-16}$).
2. **The Empirical Driver of Phase 11 Failure**:
   Development-era analysis (`2008–2021`) reveals an extreme structural divergence between return components:
   - **Overnight Gap ($R_{\text{overnight}}$)**: Generates **$+27.66\%$ annualized drift** (mean $+10.98$ bps/session) with low volatility ($9.46\%$ ann vol) and is positive **$65.23\%$** of the time.
   - **Intraday Session ($R_{\text{intraday}}$)**: Generates **$-14.01\%$ annualized drift** (mean $-5.56$ bps/session) with high volatility ($19.19\%$ ann vol) and is negative **$52.83\%$** of the time.
   - **Target Mismatch in Prior Phases**: Phase 5 targets were trained on Close-to-Close ($R_{\text{close\_to\_close}}$), but Phase 11 Primary Execution traded Open-to-Close ($R_{\text{intraday}}$). The primary strategy was explicitly exposed to the negative intraday drift while discarding the entire overnight equity premium, resulting in severe losses after friction.
3. **The Causality & Executability Trap**:
   While the decomposition explains Phase 11's losses, **targeting $R_{\text{overnight}}$ directly introduces severe causality and execution constraints**:
   - **Snapshot B CANNOT trade $R_{\text{overnight}}$**: Snapshot B is generated at 08:50 IST on Day $T+1$. By definition, the overnight gap has already transpired; entering at $\text{Close}_T$ (15:30 IST yesterday) is temporally impossible.
   - **Snapshot A CANNOT predict $R_{\text{overnight}}$ effectively**: Snapshot A is finalized at 15:30 IST on Day $T$—prior to the US trading session, European close, crude/currency moves, and overnight SGX/GIFT Nifty price formation. In the development data, the Information Coefficient (IC) between Model 1 predictions and $R_{\text{overnight}}$ is **$+0.0090$ ($p=0.691$, non-significant)**.
   - **Cash Market Overnight Friction**: In Indian spot cash markets, holding overnight exposes capital to delivery transaction taxes (STT on buy and sell), capital gains treatment, and 100% gap liquidity risk.
4. **Conclusion**:
   Target redesign is **not a magic fix**. Simply switching the model target to overnight returns without addressing causality, timing, and instruments would be scientifically invalid. Phase 12 is **CONDITIONALLY JUSTIFIED**: we outline strict prerequisites that must be satisfied before any new model is trained.

---

## 2. Phase 11 Evidence Summary & Diagnostic Audit

Phase 11 evaluated Model 1 under two execution conventions across both OOF (`2014–2021`, $N=1,960$) and Terminal Holdout (`2022–2026`, $N=1,154$):

| Execution Convention | Target Traded | OOF Strategy 1 Net (10 bps) | Holdout Strategy 1 Net (10 bps) | Benchmark 1 (Buy & Hold) | Benchmark 2 (Always Long) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Primary (Open-to-Close)** | $R_{\text{intraday}}$ | $-28.28\%$ ann | $-27.17\%$ ann | N/A | $-37.19\%$ (OOF), $-28.53\%$ (Hold) |
| **Secondary (Close-to-Close)**| $R_{\text{close\_to\_close}}$ | $+5.30\%$ ann | $+5.80\%$ ann | $+14.32\%$ (OOF), $+6.86\%$ (Hold)| N/A |

### Critical Questions Answered

#### A. Does Phase 11 justify investigating return decomposition?
**YES**, but not for the naive reason that "overnight is profitable." Phase 11 proves that the primary execution convention was trading an entirely different economic quantity ($R_{\text{intraday}}$) than what the supervised model was trained to predict ($R_{\text{close\_to\_close}}$).

#### B. What drove the Open-to-Close losses?
Decomposition analysis proves that the loss was a compounding product of:
1. **Structural Market Drift**: NIFTY spot cash exhibits negative intraday drift ($-14.0\%$ per year in development). Always-Long Benchmark 2 lost $-19.16\%$ gross and $-37.19\%$ net in OOF.
2. **Transaction Cost Drag**: Daily round-trip friction at 10 bps subtracts $25.2\%$ annualized.
3. **Target Mismatch**: Model 1 was trained on $\text{Close}_{T+1}/\text{Close}_T - 1$, which incorporates the overnight gap ($+27.7\%$ drift). The model was never optimized to predict intraday drift.
4. **Weak Intraday Signal**: Model 1's rank correlation with intraday returns is marginal ($\text{IC} = +0.0189$, $p=0.403$).

---

## 3. Target Definitions & Mathematical Identity

### 3.1 Formal Target Definitions

Let $\text{Close}_T$ be the official NSE cash closing price of NIFTY 50 on Session $T$, $\text{Open}_{T+1}$ be the official opening price on Session $T+1$, and $\text{Close}_{T+1}$ be the closing price on Session $T+1$.

1. **Target 1: Overnight / Gap Return ($R_{\text{overnight}}$)**:
   $$R_{\text{overnight}}(T+1) = \frac{\text{Open}_{T+1} - \text{Close}_T}{\text{Close}_T} = \frac{\text{Open}_{T+1}}{\text{Close}_T} - 1$$
   - Measures price change while the Indian domestic cash market is closed.
   - Realized between 15:30 IST on Day $T$ and 09:15 IST on Day $T+1$.

2. **Target 2: Intraday Session Return ($R_{\text{intraday}}$)**:
   $$R_{\text{intraday}}(T+1) = \frac{\text{Close}_{T+1} - \text{Open}_{T+1}}{\text{Open}_{T+1}} = \frac{\text{Close}_{T+1}}{\text{Open}_{T+1}} - 1$$
   - Measures price change during normal domestic market trading hours.
   - Realized between 09:15 IST and 15:30 IST on Day $T+1$.

3. **Target 3: Close-to-Close Interday Return ($R_{\text{close\_to\_close}}$)**:
   $$R_{\text{close\_to\_close}}(T+1) = \frac{\text{Close}_{T+1} - \text{Close}_T}{\text{Close}_T} = \frac{\text{Close}_{T+1}}{\text{Close}_T} - 1$$
   - The full interday return evaluated in Phase 5 and Phase 6.

### 3.2 Compounding Identity & Numerical Verification

The theoretical compounding identity:
$$(1 + R_{\text{overnight}}) \times (1 + R_{\text{intraday}}) = \frac{\text{Open}_{T+1}}{\text{Close}_T} \times \frac{\text{Close}_{T+1}}{\text{Open}_{T+1}} = \frac{\text{Close}_{T+1}}{\text{Close}_T} = 1 + R_{\text{close\_to\_close}}$$
$$\implies (1 + R_{\text{overnight}}) \times (1 + R_{\text{intraday}}) - 1 \equiv R_{\text{close\_to\_close}}$$

**Empirical Verification**:
Evaluated across all $N=3,299$ development sessions (`2008-07-08` to `2021-12-31`):
$$\max_{t \in \text{Dev}} \left| (1 + R_{\text{overnight}, t})(1 + R_{\text{intraday}, t}) - 1 - R_{\text{close\_to\_close}, t} \right| = 2.22 \times 10^{-16}$$
The identity holds to floating-point machine epsilon precision.

---

## 4. Leakage & Timing Analysis

We perform a strict causality audit to establish which snapshot can predict and trade each decomposed target:

| Dimension | Target 1: $R_{\text{overnight}}(T+1)$ | Target 2: $R_{\text{intraday}}(T+1)$ | Target 3: $R_{\text{close\_to\_close}}(T+1)$ |
| :--- | :--- | :--- | :--- |
| **Information Cutoff** | Session $T$ 15:30 IST (A) / $T+1$ 08:50 IST (B) | Session $T$ 15:30 IST (A) / $T+1$ 08:50 IST (B) | Session $T$ 15:30 IST (A) / $T+1$ 08:50 IST (B) |
| **Realization Start** | Day $T$ 15:30 IST | Day $T+1$ 09:15 IST | Day $T$ 15:30 IST |
| **Realization End** | Day $T+1$ 09:15 IST | Day $T+1$ 15:30 IST | Day $T+1$ 15:30 IST |
| **Can Snapshot A Predict It?**| **YES (Causally Valid)** | **YES (Causally Valid)** | **YES (Causally Valid)** |
| **Can Snapshot A Trade It?** | **YES** (Enter $\text{Close}_T$, Exit $\text{Open}_{T+1}$) | **YES** (Enter $\text{Open}_{T+1}$, Exit $\text{Close}_{T+1}$) | **YES** (Enter $\text{Close}_T$, Exit $\text{Close}_{T+1}$) |
| **Can Snapshot B Predict It?**| **ANACHRONISTIC / IMPOSSIBLE** | **YES (Causally Valid)** | **YES (Causally Valid)** |
| **Can Snapshot B Trade It?** | **IMPOSSIBLE** (Entry $\text{Close}_T$ was 17h ago) | **YES** (Enter $\text{Open}_{T+1}$, Exit $\text{Close}_{T+1}$) | **PARTIAL** (Enter $\text{Open}_{T+1}$, Exit $\text{Close}_{T+1}$) |
| **Prohibited Information** | Any price after Day $T$ 15:30 IST (for A) | $\text{Open}_{T+1}$, $\text{High}_{T+1}$, $\text{Low}_{T+1}$, $\text{Close}_{T+1}$ | $\text{Open}_{T+1}$, $\text{High}_{T+1}$, $\text{Low}_{T+1}$, $\text{Close}_{T+1}$ |

> [!CRITICAL]
> **SNAPSHOT B CANNOT TRADE THE OVERNIGHT GAP**  
> Snapshot B prediction occurs at 08:50 IST on Day $T+1$. The opening price $\text{Open}_{T+1}$ is established 25 minutes later at 09:15 IST. Because entry for the overnight gap must occur at yesterday's close ($\text{Close}_T$), Snapshot B is physically incapable of participating in $R_{\text{overnight}}$. Any research proposing Snapshot B for overnight return is categorically rejected as a lookahead/anachronism violation.

---

## 5. Feature Compatibility Audit (Model 1 Baseline)

We audited all 63 Model 1 features (45 Price + 18 Context) against the three candidate targets:

| Feature Group | Features | Compatibility with $R_{\text{overnight}}$ | Compatibility with $R_{\text{intraday}}$ | Compatibility with $R_{\text{close\_to\_close}}$ | Key Causal Constraints |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Price Trend / Moving Avg** | 12 | Valid | Valid | Valid | Computed on $\le \text{Close}_T$. Zero future prices. |
| **Momentum / Oscillator** | 10 | Valid | Valid | Valid | RSI, MACD, ROC up to Day $T$. |
| **Volatility / ATR / BB** | 13 | Valid | Valid | Valid | Historical rolling volatility up to Day $T$. |
| **Volume / Flow Proxies** | 10 | Valid | Valid | Valid | Cash market volume up to Day $T$ 15:30 IST. |
| **Context: Global Markets** | 6 | **POOR ALIGNMENT** | Valid | Valid | Global markets at Day $T$ 15:30 IST do NOT reflect overnight US/European developments. |
| **Context: Macro / Rates / FX**| 6 | Valid | Valid | Valid | Daily macro indicators available at Day $T$. |
| **Context: Cross-Asset / Vol**| 6 | Valid | Valid | Valid | India VIX and crude at Day $T$ close. |

### The Information Gap in Snapshot A
For Snapshot A to predict $R_{\text{overnight}}$, the model would need to predict overnight US market action (S&P 500, Nasdaq), overnight geopolitical developments, and early Asian trading using data cut off at **15:30 IST on Day $T$**.
- This is an intrinsically difficult forecasting problem: domestic Indian prices at 15:30 IST cannot causally know US corporate earnings released at 21:30 IST or US CPI released at 18:00 IST.
- Therefore, expecting Model 1 to accurately predict overnight gap direction from domestic Day $T$ features alone is structurally unsound.

---

## 6. Statistical Characterization (Development Partition Only)

Using strictly the sealed Development partition (`2008-07-08` through `2021-12-31`, $N=3,299$ sessions):

### 6.1 Distributional Summary Statistics

| Statistic | Target 1: $R_{\text{overnight}}$ | Target 2: $R_{\text{intraday}}$ | Target 3: $R_{\text{close\_to\_close}}$ | Observations / Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Daily Mean** | **$+0.001098$ ($+10.98$ bps)** | **$-0.000556$ ($-5.56$ bps)** | **$+0.000540$ ($+5.40$ bps)** | Overnight captures $> 200\%$ of net equity drift! |
| **Annualized Mean (252d)**| **$+27.66\%$** | **$-14.01\%$** | **$+13.60\%$** | Intraday has severe negative structural drift. |
| **Daily Median** | $+0.000885$ | $-0.000531$ | $+0.000665$ | Negative median in intraday confirms widespread drag. |
| **Daily Std Dev** | $0.005958$ | $0.012090$ | $0.013365$ | Intraday volatility is $2.03\times$ overnight volatility. |
| **Annualized Volatility** | **$9.46\%$** | **$19.19\%$** | **$21.22\%$** | Overnight is lower risk in variance terms. |
| **Skewness** | $-1.567$ | $+0.854$ | $+0.149$ | Overnight has left-skew (rare large negative gap shocks). |
| **Excess Kurtosis** | $33.89$ | $22.02$ | $17.88$ | Overnight has extreme fat tails. |
| **Quantile 1% (Worst 1%)** | $-1.52\%$ | $-3.34\%$ | $-3.48\%$ | Worst 1% gap is $-1.52\%$, intraday is $-3.34\%$. |
| **Quantile 25%** | $-0.06\%$ | $-0.57\%$ | $-0.55\%$ | 75% of overnight returns are $> -0.06\%$. |
| **Quantile 75%** | $+0.34\%$ | $+0.46\%$ | $+0.67\%$ | Overnight gains are frequent but moderate. |
| **Quantile 99% (Best 1%)** | $+1.65\%$ | $+3.32\%$ | $+3.59\%$ | Large positive intraday moves offset negative drift. |
| **Positive Sessions (%)** | **$65.23\%$** | **$47.14\%$** | **$53.14\%$** | Overnight is positive nearly 2 out of 3 sessions. |
| **Negative Sessions (%)** | **$34.16\%$** | **$52.83\%$** | **$46.77\%$** | Intraday is negative in majority of sessions. |
| **Zero Return Sessions (%)**| $0.61\%$ | $0.03\%$ | $0.09\%$ | Minimal flat bars. |
| **Extreme Moves ($> 2\%$)** | $1.42\%$ | $7.24\%$ | $9.03\%$ | Intraday experiences $5\times$ more extreme volatility. |

### 6.2 Autocorrelation Structure (Lags 1 to 5)

| Lag | $R_{\text{overnight}}$ | $R_{\text{intraday}}$ | $R_{\text{close\_to\_close}}$ | Statistical Interpretation |
| :---: | :---: | :---: | :---: | :--- |
| **Lag 1** | $-0.0278$ | $+0.0217$ | $+0.0473$ | Weak, non-persistent serial correlation. |
| **Lag 2** | $+0.1099$ | $-0.0533$ | $-0.0346$ | Slight positive 2-day gap momentum. |
| **Lag 3** | $+0.0261$ | $-0.0230$ | $-0.0177$ | White noise regime. |
| **Lag 4** | $-0.0396$ | $+0.0157$ | $-0.0276$ | White noise regime. |
| **Lag 5** | $+0.1143$ | $-0.0254$ | $+0.0218$ | Weekly calendar seasonality. |

### 6.3 Cross-Correlation Matrix
| | $R_{\text{overnight}}$ | $R_{\text{intraday}}$ | $R_{\text{close\_to\_close}}$ |
| :--- | :---: | :---: | :---: |
| **$R_{\text{overnight}}$** | $1.0000$ | **$-0.0190$** | $+0.4285$ |
| **$R_{\text{intraday}}$** | **$-0.0190$** | $1.0000$ | **$+0.8952$** |
| **$R_{\text{close\_to\_close}}$** | $+0.4285$ | **$+0.8952$** | $1.0000$ |

**Key Takeaway**:
- The correlation between Overnight and Intraday returns is **$-0.019$**—statistically zero! They are virtually orthogonal return generating processes.
- Close-to-Close returns are dominated by intraday variance ($\rho = 0.895$), but overnight return dominates total cumulative return drift ($+27.7\%$ vs $-14.0\%$).

### 6.4 Temporal Sub-Period Stability

| Target Component | Early Development (`2008–2013`, $N=1,339$) | OOF Development (`2014–2021`, $N=1,960$) | Temporal Stability Assessment |
| :--- | :--- | :--- | :--- |
| **$R_{\text{overnight}}$** | Ann Mean: $+17.4\%$, Vol: $8.2\%$, Pos: $57.7\%$ | Ann Mean: $+34.8\%$, Vol: $10.2\%$, Pos: $70.4\%$ | **Stable Positive Drift** (strengthened post-2014) |
| **$R_{\text{intraday}}$** | Ann Mean: $-5.4\%$, Vol: $24.7\%$, Pos: $48.8\%$ | Ann Mean: $-19.8\%$, Vol: $14.1\%$, Pos: $46.0\%$ | **Stable Negative Drift** (persistent intraday drag) |
| **$R_{\text{close\_to\_close}}$**| Ann Mean: $+12.0\%$, Vol: $26.0\%$, Pos: $51.1\%$ | Ann Mean: $+15.0\%$, Vol: $17.3\%$, Pos: $54.5\%$ | **Stable Total Drift** ($12\text{--}15\%$ long equity drift) |

### 6.5 Volatility Regime Relationship (2014–2021)

| Volatility Regime | Sessions ($N$) | Overnight Ann Mean | Intraday Ann Mean | Close-to-Close Ann Mean |
| :--- | :---: | :---: | :---: | :---: |
| **LOW Volatility** | 699 | $+33.2\%$ | $-16.4\%$ | $+16.8\%$ |
| **NORMAL Volatility** | 1,011 | $+33.1\%$ | $-23.1\%$ | $+10.0\%$ |
| **HIGH Volatility** | 215 | $+51.2\%$ | $-12.4\%$ | $+38.8\%$ |
| **EXTREME Volatility**| 35 | $+50.2\%$ | $-82.7\%$ | $-31.4\%$ |

---

## 7. Predictability Diagnostics of Existing Model 1 OOF Predictions

Using the frozen Phase 10 OOF diagnostics across $N=1,960$ sessions (`2014–2021`):

| Diagnostic Metric | Target 1: $R_{\text{overnight}}$ | Target 2: $R_{\text{intraday}}$ | Target 3: $R_{\text{close\_to\_close}}$ | Scientific Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Information Coefficient (IC)** | **$+0.0090$** ($p=0.691$) | **$+0.0189$** ($p=0.403$) | **$+0.0229$** ($p=0.312$) | Model 1 has **NO statistically significant rank correlation** with any of the three targets! |
| **Regressor Sign Agreement** | **$61.79\%$** | **$50.87\%$** | **$53.88\%$** | High hit rate on overnight is an artifact of $65.2\%$ positive baseline frequency! |
| **Classifier Direction Agreement**| **$70.03\%$** | **$45.31\%$** | **$53.37\%$** | Classifier "UP" calls capture overnight positive drift, but lose money intraday ($45.3\%$ hit rate). |

### The "Overnight Illusion"
A naive analyst observing a $70.0\%$ hit rate for the Classifier on overnight returns might conclude the model is an exceptional overnight predictor.
**This is a statistical illusion**:
- In the OOF partition, $R_{\text{overnight}}$ was positive $70.4\%$ of the time!
- An always-long dummy baseline achieves a $70.4\%$ hit rate on overnight returns with zero predictive intelligence.
- When evaluated with rank correlation, the IC is $+0.0090$ ($p=0.691$), proving that Model 1 has **zero incremental ability to discriminate between large and small overnight gaps**.

---

## 8. Validation Architecture for Future Phases

Because the 2022–2026 Terminal Holdout is **CONSUMED and PERMANENTLY SEALED**, any future phase cannot use that data for out-of-sample validation.

### Proposed Chronological Validation Protocol:
1. **Development & Tuning Partition**: Strict subset of historical data ($\le \text{2021-12-31}$).
   - Cross-validation: 8-fold expanding walk-forward (`2014–2021`).
2. **Embargo Requirements**:
   - Because overnight returns span $T \to T+1$, an embargo of at least 1 session between training and validation folds is required to prevent gap autocorrelation leakage.
3. **Future Out-of-Sample Protocol**:
   - A genuine out-of-sample test can **only** be performed on post-2026 data (live paper-trading forward in time) or via a new, completely isolated external index (e.g. NIFTY Bank or NIFTY IT) with strict pre-registration.

---

## 9. Economic Test Architecture (Conceptual Design)

If economic evaluation were to be pursued in a future phase, it would require distinct, realistic trading protocols:

| Dimension | Overnight Strategy | Intraday Strategy | Close-to-Close Strategy |
| :--- | :--- | :--- | :--- |
| **Trading Instrument** | Index Futures (NIFTY Futures) | Cash Equities or Intraday Futures | Index Futures or Cash ETF |
| **Entry Timestamp** | 15:25 IST on Day $T$ | 09:20 IST on Day $T+1$ (post-open) | 15:25 IST on Day $T$ |
| **Exit Timestamp** | 09:20 IST on Day $T+1$ | 15:25 IST on Day $T+1$ | 15:25 IST on Day $T+1$ |
| **Transaction Cost** | Futures round-trip: $\approx 2.5\text{--}5.0$ bps | Cash round-trip: $\approx 10.0$ bps | Futures roll / turn: $\approx 2.5\text{--}5.0$ bps |
| **Overnight Risk** | Maximum (exposed to global shocks) | Zero (flat overnight) | Full overnight risk |
| **Benchmark** | Cash / Overnight Rate (TREPS) | Always-Long Intraday | NIFTY 50 Buy-and-Hold |

---

## 10. Critical Evaluation of Alternative Hypotheses

Before committing to target redesign, we must compare it against alternative failure hypotheses:

| Alternative Hypothesis | Core Mechanism | Supporting Evidence | Counter-Evidence / Limitations |
| :--- | :--- | :--- | :--- |
| **1. Instrument Mismatch** | Spot cash was the wrong instrument; should use NIFTY Futures. | Cash carries high STT and round-trip drag; futures have lower friction ($2\text{--}4$ bps). | Does not fix negative intraday drift; leverage increases drawdown risk. |
| **2. Target Mismatch (Phase 12)**| Model was trained on Close-to-Close but traded Open-to-Close. | Mathematically verified; $+27.7\%$ drift was discarded. | Model has no predictive power over overnight gap ($\text{IC}=0.009$). |
| **3. Lack of Overnight Features**| Model cannot predict gaps without overnight global data. | Snapshot A has zero knowledge of US markets, Asia, crude, GIFT Nifty. | Snapshot B has morning data but cannot trade the gap. |
| **4. Weak ML Signal (Skeptical)**| Daily directional equity forecasting at 1-day horizon has near-zero SNR. | OOF IC is $+0.0229$ ($p>0.30$); regression trees overfit noise. | Regime conditioning shows isolated pockets of statistical significance in Phase 10. |
| **5. High-Frequency Turnover Trap**| Trading every day at daily frequency guarantees friction death. | 1,960 round trips subtracts $25.2\%$ annually at 10 bps. | Gating reduces trades but leaves remaining trades flat. |

---

## 11. Decision Gate Determination & Concrete Next Steps

### Determination: `B) CONDITIONALLY JUSTIFIED`

Target decomposition is **empirically justified** as the structural explanation for why Phase 11 failed:
- Trading Open-to-Close in NIFTY cash markets is fundamentally fighting a structural $-14.0\%$ intraday drift while paying $25.2\%$ in annual friction.
- However, simply declaring "let's predict overnight returns" is **UNJUSTIFIED** because:
  1. Snapshot B cannot trade it.
  2. Snapshot A lacks the causal information (US/Asian overnight markets) to predict it.
  3. The existing Model 1 feature set has $\text{IC} = +0.009$ on overnight returns.

### Exact Prerequisites for ANY Next Phase:
1. **NO HOLDOUT ACCESS**: The 2022–2026 holdout remains permanently locked.
2. **Snapshot Timing Realignment**:
   - If predicting overnight returns, the research must define a new snapshot: e.g., Snapshot C at 23:00 IST or Snapshot B at 08:50 IST predicting *intraday* moves given the morning gap.
3. **Morning-to-Close Formulation (Intraday Conditional on Gap)**:
   - The most scientifically sound hypothesis is: **Can Snapshot B (at 08:50 IST, knowing the overnight global moves and expected gap) predict the INTRADAY reaction ($Open_{T+1} \to Close_{T+1}$)?**
   - This aligns with causality: Snapshot B knows the morning context and trades the subsequent intraday bar.
