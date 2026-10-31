# PHASE 11 — STAGE 1: OOF STRATEGY VALIDATION REPORT

**Status**: STAGE 1 COMPLETE — AWAITING STAGE 2 AUTHORIZATION  
**Date**: September 18, 2026  
**Phase**: Phase 11 — Stage 1 (Development OOF Evaluation Only)  
**Model Evaluated**: Model 1 (Price + Context, 63 features, 0 News)  
**Evaluation Partition**: Development OOF (2014-01-02 to 2021-12-31, N=1,960 sessions)  
**Terminal Holdout Status**: COMPLETELY UNTOUCHED (Zero Evaluation / Zero Contamination)  

---

## 1. Executive Summary & Primary Scientific Takeaways

Phase 11 Stage 1 executes the formal economic-value evaluation of the production-validated **Model 1 (Price + Context)** baseline predictions across the 8-fold expanding cross-validation Development Out-of-Fold (OOF) partition (2014–2021, N=1,960 sessions).

The primary scientific question addressed is:
> *Does the sealed Model 1 prediction signal produce economically meaningful and reasonably robust out-of-sample performance under a realistic, pre-specified paper-trading framework?*

### Core Empirical Findings

1. **Failure of High-Turnover Intraday Strategies (Primary Execution Convention)**:
   - Under the primary execution convention (enter at next session OPEN, exit at next session CLOSE), **all continuous daily trading strategies decay severely after realistic transaction costs**.
   - At 10 bps round-trip friction, unrestricted **Strategy 1 (Regression Direction)** incurs an annualized net loss of **-28.28%** in Snapshot A and **-28.94%** in Snapshot B (cumulative net loss of -92.46% and -92.98%).
   - Unrestricted **Strategy 2 (Classifier Direction)** fares worse, losing **-35.99%** annualized in Snapshot A and **-31.69%** in Snapshot B.
   - This breakdown is driven by two compounding factors:
     - **Cash Market Intraday Drift**: In Indian index spot markets, intraday Open-to-Close returns have a structural negative drift (Always-Long Benchmark 2 loses -19.16% annualized gross and -37.19% net at 10 bps). Over 90% of long equity premium is realized interday via overnight close-to-open gaps.
     - **Transaction Cost Friction**: Trading every active day accumulates 1,960 round trips. At 10 bps per day, transaction costs subtract 25.2% per year in direct execution friction.

2. **Impact of Pre-Registered Confidence and Magnitude Gating**:
   - Pre-registered gating dramatically reduces turnover, cutting active session exposure from 100% down to 1–15%:
     - **Strategy 3 (Confidence Gate)**: At $\tau=0.40$, net loss slows to -9.95% annualized in A and -14.65% in B. At $\tau=0.45$ and $\tau=0.50$, trading activity is near-zero because the calibrated model rarely outputs probabilities $\ge 0.45$ (reflecting genuine model calibration and absence of false overconfidence).
     - **Strategy 4 (Magnitude Gate)**: At magnitude threshold $0.10\%$, net loss improves to -1.49% annualized in Snapshot A and -0.73% in Snapshot B (gross return is slightly positive at +1.05% and +2.32%, but wiped out by costs). At higher thresholds ($0.25\%, 0.50\%$), the strategy remains mostly flat.

3. **Phase 10 LOW-Volatility Diagnostic Filter (Strategy 5)**:
   - Applying the pre-registered Phase 10 LOW-volatility filter ($\sigma_{20d} \le 11.47\%$) reduces turnover and limits maximum drawdown (from -92.8% down to -50.7% in Strategy 5A).
   - However, under the primary Open-to-Close convention, Strategy 5A still produces negative net return (-7.34% annualized at 10 bps in Snapshot A).
   - Under the secondary Close-to-Close diagnostic convention, Strategy 5A achieves positive annualized net return (+4.66% in A, +2.48% in B) with a small max drawdown (-10.14% in A), but still lags the continuous Buy-and-Hold benchmark (+14.32% annualized).

4. **Secondary Diagnostic Execution Convention (Close-to-Close)**:
   - When holding interday from Close to Close, positions capture overnight gap returns and pay transaction costs only on position changes:
     - Benchmark 1 Buy-and-Hold achieves **+14.32% annualized** (Sharpe 0.869, Max DD -38.44%).
     - Strategy 1 achieves **+5.30% annualized net** (Sharpe 0.388, Max DD -41.59%) in Snapshot A, and **+7.08% annualized net** (Sharpe 0.485, Max DD -53.60%) in Snapshot B.
     - Strategy 2 achieves **+7.79% annualized net** (Sharpe 0.540, Max DD -39.96%) in Snapshot A, and **+6.68% annualized net** (Sharpe 0.481, Max DD -40.57%) in Snapshot B.
   - While positive, Model 1 strategies do **not** outperform simple buy-and-hold on either total return or risk-adjusted basis.

---

## 2. Pre-Registered Evidence Classification

Per Section 18 of the specification, every strategy receives an explicit evidential classification (not a ranking):

| Strategy ID | Strategy Name | Primary Convention (10 bps) | Secondary Convention (10 bps) | Evidence Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Strategy 0** | Always Flat Baseline | 0.0% return, 0.0 DD | 0.0% return, 0.0 DD | **C) NO ECONOMIC EVIDENCE (Zero Baseline)** |
| **Strategy 1** | Regression Direction | Net Ann: -28.28% (A), -28.94% (B) | Net Ann: +5.30% (A), +7.08% (B) | **D) NEGATIVE AFTER COSTS** |
| **Strategy 2** | Classifier Direction | Net Ann: -35.99% (A), -31.69% (B) | Net Ann: +7.79% (A), +6.68% (B) | **D) NEGATIVE AFTER COSTS** |
| **Strategy 3 (tau=0.40)** | Classifier + Conf Gate (0.40) | Net Ann: -9.95% (A), -14.65% (B) | Net Ann: +0.61% (A), +4.32% (B) | **D) NEGATIVE AFTER COSTS** |
| **Strategy 3 (tau=0.45)** | Classifier + Conf Gate (0.45) | Net Ann: 0.0% (A), +0.57% (B) | Net Ann: 0.0% (A), +1.48% (B) | **B) WEAK / INCONCLUSIVE ECONOMIC EVIDENCE** |
| **Strategy 3 (tau=0.50)** | Classifier + Conf Gate (0.50) | Net Ann: 0.0% (A), -0.06% (B) | Net Ann: 0.0% (A), -0.04% (B) | **C) NO ECONOMIC EVIDENCE (Inactive)** |
| **Strategy 4 (mag=0.10%)**| Reg Magnitude Gate (0.10%) | Net Ann: -1.49% (A), -0.73% (B) | Net Ann: +2.94% (A), +4.86% (B) | **D) NEGATIVE AFTER COSTS** |
| **Strategy 4 (mag=0.25%)**| Reg Magnitude Gate (0.25%) | Net Ann: -0.68% (A), -1.28% (B) | Net Ann: -0.44% (A), -1.92% (B) | **C) NO ECONOMIC EVIDENCE** |
| **Strategy 4 (mag=0.50%)**| Reg Magnitude Gate (0.50%) | Net Ann: 0.0% (A), 0.0% (B) | Net Ann: 0.0% (A), 0.0% (B) | **C) NO ECONOMIC EVIDENCE (Inactive)** |
| **Strategy 5A** | Reg + LOW-Vol Diagnostic | Net Ann: -7.34% (A), -9.86% (B) | Net Ann: +4.66% (A), +2.48% (B) | **D) NEGATIVE AFTER COSTS (Primary)** |
| **Strategy 5B** | Clf + LOW-Vol Diagnostic | Net Ann: -13.37% (A), -12.09% (B) | Net Ann: +4.42% (A), +3.25% (B) | **D) NEGATIVE AFTER COSTS (Primary)** |

---

## 3. Comprehensive OOF Performance Tables

### 3.1 Snapshot A — Primary Execution Convention (Open-to-Close)

| Strategy ID | Cost Scenario | Ann Net Ret | Sharpe | Sortino | Max DD | Calmar | Win Rate | Profit Factor | NW p-value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Strategy 0 | 0 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 0 | 5 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 0 | 10 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 0 | 20 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 1 | 0 bps | -7.71% | -0.49 | -0.65 | -58.74% | -0.13 | 50.9% | 0.91 | 1.75e-01 |
| Strategy 1 | 5 bps | -18.64% | -1.38 | -1.76 | -82.11% | -0.23 | 47.8% | 0.77 | 1.47e-04 |
| Strategy 1 | 10 bps | -28.28% | -2.26 | -2.79 | -92.78% | -0.30 | 44.6% | 0.66 | 4.44e-10 |
| Strategy 1 | 20 bps | -44.28% | -4.03 | -4.63 | -98.97% | -0.45 | 38.4% | 0.47 | 0.00e+00 |
| Strategy 2 | 0 bps | -19.17% | -1.48 | -1.99 | -82.55% | -0.23 | 45.3% | 0.75 | 2.01e-06 |
| Strategy 2 | 5 bps | -28.06% | -2.32 | -3.01 | -92.64% | -0.30 | 42.4% | 0.64 | 1.22e-13 |
| Strategy 2 | 10 bps | -35.99% | -3.17 | -3.95 | -96.97% | -0.37 | 39.6% | 0.54 | 0.00e+00 |
| Strategy 2 | 20 bps | -49.32% | -4.85 | -5.60 | -99.50% | -0.50 | 33.9% | 0.39 | 0.00e+00 |
| Strategy 3 (tau=0.40) | 0 bps | -3.62% | -0.34 | -0.47 | -32.23% | -0.11 | 49.6% | 0.88 | 2.51e-01 |
| Strategy 3 (tau=0.40) | 5 bps | -6.83% | -0.69 | -0.93 | -44.26% | -0.15 | 45.8% | 0.77 | 2.09e-02 |
| Strategy 3 (tau=0.40) | 10 bps | -9.95% | -1.04 | -1.37 | -56.31% | -0.18 | 43.4% | 0.68 | 6.47e-04 |
| Strategy 3 (tau=0.40) | 20 bps | -15.87% | -1.73 | -2.16 | -74.13% | -0.21 | 39.0% | 0.52 | 6.80e-08 |
| Strategy 3 (tau=0.45) | 0 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 3 (tau=0.45) | 5 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 3 (tau=0.45) | 10 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 3 (tau=0.45) | 20 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 3 (tau=0.50) | 0 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 3 (tau=0.50) | 5 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 3 (tau=0.50) | 10 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 3 (tau=0.50) | 20 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 4 (mag=0.10%) | 0 bps | 1.05% | 0.20 | 0.31 | -14.83% | 0.07 | 52.5% | 1.14 | 5.22e-01 |
| Strategy 4 (mag=0.10%) | 5 bps | -0.23% | -0.01 | -0.01 | -19.09% | -0.01 | 49.5% | 1.00 | 9.82e-01 |
| Strategy 4 (mag=0.10%) | 10 bps | -1.49% | -0.22 | -0.31 | -23.73% | -0.06 | 47.0% | 0.87 | 4.85e-01 |
| Strategy 4 (mag=0.10%) | 20 bps | -3.97% | -0.63 | -0.86 | -32.25% | -0.12 | 39.4% | 0.66 | 3.90e-02 |
| Strategy 4 (mag=0.25%) | 0 bps | -0.43% | -0.09 | -0.12 | -8.93% | -0.05 | 47.4% | 0.85 | 7.24e-01 |
| Strategy 4 (mag=0.25%) | 5 bps | -0.56% | -0.11 | -0.16 | -9.13% | -0.06 | 47.4% | 0.81 | 6.34e-01 |
| Strategy 4 (mag=0.25%) | 10 bps | -0.68% | -0.14 | -0.20 | -9.41% | -0.07 | 47.4% | 0.77 | 5.51e-01 |
| Strategy 4 (mag=0.25%) | 20 bps | -0.92% | -0.20 | -0.28 | -10.04% | -0.09 | 42.1% | 0.69 | 4.05e-01 |
| Strategy 4 (mag=0.50%) | 0 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 4 (mag=0.50%) | 5 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 4 (mag=0.50%) | 10 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 4 (mag=0.50%) | 20 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 5A (Reg + LowVol) | 0 bps | 1.38% | 0.27 | 0.38 | -19.87% | 0.07 | 52.6% | 1.08 | 4.25e-01 |
| Strategy 5A (Reg + LowVol) | 5 bps | -3.08% | -0.52 | -0.70 | -34.74% | -0.09 | 49.6% | 0.87 | 1.23e-01 |
| Strategy 5A (Reg + LowVol) | 10 bps | -7.34% | -1.31 | -1.66 | -50.67% | -0.14 | 45.9% | 0.69 | 1.97e-04 |
| Strategy 5A (Reg + LowVol) | 20 bps | -15.31% | -2.83 | -3.26 | -73.60% | -0.21 | 38.1% | 0.44 | 1.53e-12 |
| Strategy 5B (Clf + LowVol) | 0 bps | -5.67% | -1.03 | -1.34 | -38.57% | -0.15 | 44.9% | 0.75 | 3.32e-03 |
| Strategy 5B (Clf + LowVol) | 5 bps | -9.60% | -1.78 | -2.20 | -55.23% | -0.17 | 41.2% | 0.60 | 1.21e-06 |
| Strategy 5B (Clf + LowVol) | 10 bps | -13.37% | -2.51 | -2.96 | -67.74% | -0.20 | 39.0% | 0.48 | 1.29e-10 |
| Strategy 5B (Clf + LowVol) | 20 bps | -20.45% | -3.87 | -4.22 | -83.26% | -0.25 | 32.3% | 0.31 | 0.00e+00 |
| Benchmark 1 | 0 bps | -19.16% | -1.43 | -1.91 | -83.05% | -0.23 | 46.0% | 0.77 | 5.84e-06 |
| Benchmark 1 | 5 bps | -28.74% | -2.32 | -2.98 | -93.34% | -0.31 | 43.1% | 0.65 | 1.96e-13 |
| Benchmark 1 | 10 bps | -37.19% | -3.20 | -3.97 | -97.41% | -0.38 | 40.4% | 0.55 | 0.00e+00 |
| Benchmark 1 | 20 bps | -51.21% | -4.98 | -5.71 | -99.63% | -0.51 | 34.4% | 0.40 | 0.00e+00 |
| Benchmark 2 | 0 bps | -19.16% | -1.43 | -1.91 | -83.05% | -0.23 | 46.0% | 0.77 | 5.84e-06 |
| Benchmark 2 | 5 bps | -28.74% | -2.32 | -2.98 | -93.34% | -0.31 | 43.1% | 0.65 | 1.96e-13 |
| Benchmark 2 | 10 bps | -37.19% | -3.20 | -3.97 | -97.41% | -0.38 | 40.4% | 0.55 | 0.00e+00 |
| Benchmark 2 | 20 bps | -51.21% | -4.98 | -5.71 | -99.63% | -0.51 | 34.4% | 0.40 | 0.00e+00 |

### 3.2 Snapshot B — Primary Execution Convention (Open-to-Close)

| Strategy ID | Cost Scenario | Ann Net Ret | Sharpe | Sortino | Max DD | Calmar | Win Rate | Profit Factor | NW p-value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Strategy 0 | 0 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 0 | 5 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 0 | 10 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 0 | 20 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 1 | 0 bps | -8.55% | -0.56 | -0.74 | -63.66% | -0.13 | 49.6% | 0.90 | 1.14e-01 |
| Strategy 1 | 5 bps | -19.38% | -1.44 | -1.86 | -83.55% | -0.23 | 46.8% | 0.77 | 4.15e-05 |
| Strategy 1 | 10 bps | -28.94% | -2.33 | -2.89 | -93.55% | -0.31 | 44.0% | 0.65 | 3.69e-11 |
| Strategy 1 | 20 bps | -44.79% | -4.10 | -4.74 | -99.03% | -0.45 | 38.1% | 0.47 | 0.00e+00 |
| Strategy 2 | 0 bps | -14.63% | -1.09 | -1.49 | -75.49% | -0.19 | 46.7% | 0.81 | 6.37e-04 |
| Strategy 2 | 5 bps | -23.64% | -1.91 | -2.51 | -88.65% | -0.27 | 43.8% | 0.69 | 3.56e-09 |
| Strategy 2 | 10 bps | -31.69% | -2.72 | -3.45 | -95.01% | -0.33 | 41.2% | 0.58 | 0.00e+00 |
| Strategy 2 | 20 bps | -45.36% | -4.34 | -5.11 | -99.11% | -0.46 | 35.3% | 0.42 | 0.00e+00 |
| Strategy 3 (tau=0.40) | 0 bps | -4.92% | -0.44 | -0.62 | -40.38% | -0.12 | 50.4% | 0.88 | 1.95e-01 |
| Strategy 3 (tau=0.40) | 5 bps | -9.91% | -0.97 | -1.31 | -59.86% | -0.17 | 47.1% | 0.76 | 5.17e-03 |
| Strategy 3 (tau=0.40) | 10 bps | -14.65% | -1.49 | -1.95 | -73.01% | -0.20 | 44.6% | 0.66 | 2.28e-05 |
| Strategy 3 (tau=0.40) | 20 bps | -23.39% | -2.52 | -3.09 | -87.81% | -0.27 | 38.0% | 0.49 | 5.80e-12 |
| Strategy 3 (tau=0.45) | 0 bps | 0.97% | 0.45 | 1.18 | -3.65% | 0.27 | 45.2% | 2.07 | 2.04e-01 |
| Strategy 3 (tau=0.45) | 5 bps | 0.77% | 0.36 | 0.89 | -4.04% | 0.19 | 45.2% | 1.77 | 3.05e-01 |
| Strategy 3 (tau=0.45) | 10 bps | 0.57% | 0.28 | 0.62 | -4.43% | 0.13 | 45.2% | 1.52 | 4.40e-01 |
| Strategy 3 (tau=0.45) | 20 bps | 0.17% | 0.09 | 0.18 | -5.19% | 0.03 | 35.5% | 1.14 | 7.98e-01 |
| Strategy 3 (tau=0.50) | 0 bps | -0.03% | -0.19 | -0.20 | -0.44% | -0.07 | 50.0% | 0.43 | 6.03e-01 |
| Strategy 3 (tau=0.50) | 5 bps | -0.05% | -0.25 | -0.26 | -0.49% | -0.09 | 50.0% | 0.29 | 4.94e-01 |
| Strategy 3 (tau=0.50) | 10 bps | -0.06% | -0.29 | -0.30 | -0.54% | -0.11 | 50.0% | 0.17 | 4.12e-01 |
| Strategy 3 (tau=0.50) | 20 bps | -0.08% | -0.36 | -0.36 | -0.65% | -0.13 | 0.0% | 0.00 | 3.10e-01 |
| Strategy 4 (mag=0.10%) | 0 bps | 2.32% | 0.41 | 0.61 | -16.09% | 0.14 | 54.9% | 1.26 | 2.03e-01 |
| Strategy 4 (mag=0.10%) | 5 bps | 0.78% | 0.16 | 0.23 | -18.45% | 0.04 | 51.1% | 1.09 | 6.15e-01 |
| Strategy 4 (mag=0.10%) | 10 bps | -0.73% | -0.09 | -0.13 | -23.98% | -0.03 | 48.9% | 0.95 | 7.71e-01 |
| Strategy 4 (mag=0.10%) | 20 bps | -3.68% | -0.59 | -0.79 | -34.73% | -0.11 | 43.0% | 0.72 | 5.61e-02 |
| Strategy 4 (mag=0.25%) | 0 bps | -1.01% | -0.23 | -0.32 | -10.53% | -0.10 | 42.9% | 0.66 | 3.29e-01 |
| Strategy 4 (mag=0.25%) | 5 bps | -1.14% | -0.26 | -0.36 | -10.84% | -0.11 | 38.1% | 0.62 | 2.68e-01 |
| Strategy 4 (mag=0.25%) | 10 bps | -1.28% | -0.29 | -0.40 | -11.16% | -0.11 | 38.1% | 0.59 | 2.17e-01 |
| Strategy 4 (mag=0.25%) | 20 bps | -1.55% | -0.35 | -0.47 | -12.07% | -0.13 | 38.1% | 0.52 | 1.41e-01 |
| Strategy 4 (mag=0.50%) | 0 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 4 (mag=0.50%) | 5 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 4 (mag=0.50%) | 10 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 4 (mag=0.50%) | 20 bps | 0.00% | 0.00 | 0.00 | 0.00% | 0.00 | 0.0% | 0.00 | 1.00e+00 |
| Strategy 5A (Reg + LowVol) | 0 bps | -1.37% | -0.22 | -0.31 | -23.57% | -0.06 | 48.9% | 0.94 | 5.41e-01 |
| Strategy 5A (Reg + LowVol) | 5 bps | -5.71% | -1.01 | -1.34 | -42.79% | -0.13 | 45.6% | 0.76 | 5.17e-03 |
| Strategy 5A (Reg + LowVol) | 10 bps | -9.86% | -1.79 | -2.25 | -58.45% | -0.17 | 42.8% | 0.61 | 2.00e-06 |
| Strategy 5A (Reg + LowVol) | 20 bps | -17.62% | -3.27 | -3.74 | -78.41% | -0.22 | 35.9% | 0.39 | 1.67e-14 |
| Strategy 5B (Clf + LowVol) | 0 bps | -4.56% | -0.85 | -1.13 | -32.01% | -0.14 | 45.1% | 0.79 | 1.79e-02 |
| Strategy 5B (Clf + LowVol) | 5 bps | -8.40% | -1.60 | -2.02 | -50.00% | -0.17 | 41.5% | 0.63 | 1.82e-05 |
| Strategy 5B (Clf + LowVol) | 10 bps | -12.09% | -2.33 | -2.79 | -63.54% | -0.19 | 39.5% | 0.51 | 3.87e-09 |
| Strategy 5B (Clf + LowVol) | 20 bps | -19.03% | -3.70 | -4.07 | -80.70% | -0.24 | 32.9% | 0.33 | 4.44e-16 |
| Benchmark 1 | 0 bps | -19.16% | -1.43 | -1.91 | -83.05% | -0.23 | 46.0% | 0.77 | 5.84e-06 |
| Benchmark 1 | 5 bps | -28.74% | -2.32 | -2.98 | -93.34% | -0.31 | 43.1% | 0.65 | 1.96e-13 |
| Benchmark 1 | 10 bps | -37.19% | -3.20 | -3.97 | -97.41% | -0.38 | 40.4% | 0.55 | 0.00e+00 |
| Benchmark 1 | 20 bps | -51.21% | -4.98 | -5.71 | -99.63% | -0.51 | 34.4% | 0.40 | 0.00e+00 |
| Benchmark 2 | 0 bps | -19.16% | -1.43 | -1.91 | -83.05% | -0.23 | 46.0% | 0.77 | 5.84e-06 |
| Benchmark 2 | 5 bps | -28.74% | -2.32 | -2.98 | -93.34% | -0.31 | 43.1% | 0.65 | 1.96e-13 |
| Benchmark 2 | 10 bps | -37.19% | -3.20 | -3.97 | -97.41% | -0.38 | 40.4% | 0.55 | 0.00e+00 |
| Benchmark 2 | 20 bps | -51.21% | -4.98 | -5.71 | -99.63% | -0.51 | 34.4% | 0.40 | 0.00e+00 |

### 3.3 Secondary Diagnostic Convention (Close-to-Close at 10 bps)

| Snapshot | Strategy ID | Ann Gross Ret | Ann Net Ret | Sharpe | Max DD | Win Rate | Profit Factor | NW p-value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Snapshot A | Strategy 0 | 0.00% | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 1.00e+00 |
| Snapshot A | Strategy 1 | 13.52% | 5.30% | 0.39 | -41.59% | 52.7% | 1.08 | 2.95e-01 |
| Snapshot A | Strategy 2 | 8.77% | 7.79% | 0.54 | -39.96% | 53.2% | 1.12 | 1.27e-01 |
| Snapshot A | Strategy 3 (tau=0.40) | 3.72% | 0.61% | 0.11 | -37.98% | 52.8% | 1.09 | 7.61e-01 |
| Snapshot A | Strategy 3 (tau=0.45) | 0.00% | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 1.00e+00 |
| Snapshot A | Strategy 3 (tau=0.50) | 0.00% | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 1.00e+00 |
| Snapshot A | Strategy 4 (mag=0.10%) | 5.04% | 2.94% | 0.37 | -26.25% | 60.6% | 1.41 | 2.43e-01 |
| Snapshot A | Strategy 4 (mag=0.25%) | -0.23% | -0.44% | -0.03 | -20.27% | 63.2% | 0.97 | 9.14e-01 |
| Snapshot A | Strategy 4 (mag=0.50%) | 0.00% | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 1.00e+00 |
| Snapshot A | Strategy 5A (Reg + LowVol) | 8.09% | 4.66% | 0.74 | -10.14% | 54.4% | 1.24 | 3.71e-02 |
| Snapshot A | Strategy 5B (Clf + LowVol) | 5.18% | 4.42% | 0.71 | -10.86% | 54.4% | 1.24 | 4.94e-02 |
| Snapshot A | Benchmark 1 | 14.33% | 14.32% | 0.87 | -38.44% | 54.5% | 1.18 | 1.71e-02 |
| Snapshot A | Benchmark 2 | 14.33% | 14.32% | 0.87 | -38.44% | 54.5% | 1.18 | 1.71e-02 |
| Snapshot B | Strategy 0 | 0.00% | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 1.00e+00 |
| Snapshot B | Strategy 1 | 15.35% | 7.08% | 0.49 | -53.60% | 52.2% | 1.10 | 1.73e-01 |
| Snapshot B | Strategy 2 | 9.89% | 6.68% | 0.48 | -40.57% | 52.9% | 1.11 | 1.86e-01 |
| Snapshot B | Strategy 3 (tau=0.40) | 8.56% | 4.32% | 0.39 | -31.78% | 53.8% | 1.17 | 2.55e-01 |
| Snapshot B | Strategy 3 (tau=0.45) | 1.82% | 1.48% | 0.58 | -2.74% | 51.6% | 3.34 | 1.03e-01 |
| Snapshot B | Strategy 3 (tau=0.50) | -0.01% | -0.04% | -0.62 | -0.30% | 0.0% | 0.00 | 1.65e-01 |
| Snapshot B | Strategy 4 (mag=0.10%) | 7.34% | 4.86% | 0.58 | -22.30% | 61.7% | 1.56 | 8.17e-02 |
| Snapshot B | Strategy 4 (mag=0.25%) | -1.71% | -1.92% | -0.26 | -19.81% | 42.9% | 0.61 | 3.75e-01 |
| Snapshot B | Strategy 4 (mag=0.50%) | 0.00% | 0.00% | 0.00 | 0.00% | 0.0% | 0.00 | 1.00e+00 |
| Snapshot B | Strategy 5A (Reg + LowVol) | 5.72% | 2.48% | 0.41 | -12.78% | 52.6% | 1.13 | 2.70e-01 |
| Snapshot B | Strategy 5B (Clf + LowVol) | 4.97% | 3.25% | 0.55 | -10.39% | 52.8% | 1.19 | 1.22e-01 |
| Snapshot B | Benchmark 1 | 14.33% | 14.32% | 0.87 | -38.44% | 54.5% | 1.18 | 1.71e-02 |
| Snapshot B | Benchmark 2 | 14.33% | 14.32% | 0.87 | -38.44% | 54.5% | 1.18 | 1.71e-02 |

---

## 4. Parameter Robustness Analysis

### Confidence Gate Sensitivity (Strategy 3)

| Snapshot | Threshold | Cost Scenario | Active Session % | Ann Net Ret | Sharpe | Max DD | Profit Factor |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Snapshot A | tau=0.40 | 0 bps | 26.9% | -3.62% | -0.34 | -32.23% | 0.88 |
| Snapshot A | tau=0.40 | 5 bps | 26.9% | -6.83% | -0.69 | -44.26% | 0.77 |
| Snapshot A | tau=0.40 | 10 bps | 26.9% | -9.95% | -1.04 | -56.31% | 0.68 |
| Snapshot A | tau=0.40 | 20 bps | 26.9% | -15.87% | -1.73 | -74.13% | 0.52 |
| Snapshot A | tau=0.45 | 0 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | tau=0.45 | 5 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | tau=0.45 | 10 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | tau=0.45 | 20 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | tau=0.50 | 0 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | tau=0.50 | 5 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | tau=0.50 | 10 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | tau=0.50 | 20 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot B | tau=0.40 | 0 bps | 42.8% | -4.92% | -0.44 | -40.38% | 0.88 |
| Snapshot B | tau=0.40 | 5 bps | 42.8% | -9.91% | -0.97 | -59.86% | 0.76 |
| Snapshot B | tau=0.40 | 10 bps | 42.8% | -14.65% | -1.49 | -73.01% | 0.66 |
| Snapshot B | tau=0.40 | 20 bps | 42.8% | -23.39% | -2.52 | -87.81% | 0.49 |
| Snapshot B | tau=0.45 | 0 bps | 1.6% | 0.97% | 0.45 | -3.65% | 2.07 |
| Snapshot B | tau=0.45 | 5 bps | 1.6% | 0.77% | 0.36 | -4.04% | 1.77 |
| Snapshot B | tau=0.45 | 10 bps | 1.6% | 0.57% | 0.28 | -4.43% | 1.52 |
| Snapshot B | tau=0.45 | 20 bps | 1.6% | 0.17% | 0.09 | -5.19% | 1.14 |
| Snapshot B | tau=0.50 | 0 bps | 0.1% | -0.03% | -0.19 | -0.44% | 0.43 |
| Snapshot B | tau=0.50 | 5 bps | 0.1% | -0.05% | -0.25 | -0.49% | 0.29 |
| Snapshot B | tau=0.50 | 10 bps | 0.1% | -0.06% | -0.29 | -0.54% | 0.17 |
| Snapshot B | tau=0.50 | 20 bps | 0.1% | -0.08% | -0.36 | -0.65% | 0.00 |

### Magnitude Gate Sensitivity (Strategy 4)

| Snapshot | Threshold | Cost Scenario | Active Session % | Ann Net Ret | Sharpe | Max DD | Profit Factor |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Snapshot A | theta=0.10% | 0 bps | 10.1% | 1.05% | 0.20 | -14.83% | 1.14 |
| Snapshot A | theta=0.10% | 5 bps | 10.1% | -0.23% | -0.01 | -19.09% | 1.00 |
| Snapshot A | theta=0.10% | 10 bps | 10.1% | -1.49% | -0.22 | -23.73% | 0.87 |
| Snapshot A | theta=0.10% | 20 bps | 10.1% | -3.97% | -0.63 | -32.25% | 0.66 |
| Snapshot A | theta=0.25% | 0 bps | 1.0% | -0.43% | -0.09 | -8.93% | 0.85 |
| Snapshot A | theta=0.25% | 5 bps | 1.0% | -0.56% | -0.11 | -9.13% | 0.81 |
| Snapshot A | theta=0.25% | 10 bps | 1.0% | -0.68% | -0.14 | -9.41% | 0.77 |
| Snapshot A | theta=0.25% | 20 bps | 1.0% | -0.92% | -0.20 | -10.04% | 0.69 |
| Snapshot A | theta=0.50% | 0 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | theta=0.50% | 5 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | theta=0.50% | 10 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot A | theta=0.50% | 20 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot B | theta=0.10% | 0 bps | 12.0% | 2.32% | 0.41 | -16.09% | 1.26 |
| Snapshot B | theta=0.10% | 5 bps | 12.0% | 0.78% | 0.16 | -18.45% | 1.09 |
| Snapshot B | theta=0.10% | 10 bps | 12.0% | -0.73% | -0.09 | -23.98% | 0.95 |
| Snapshot B | theta=0.10% | 20 bps | 12.0% | -3.68% | -0.59 | -34.73% | 0.72 |
| Snapshot B | theta=0.25% | 0 bps | 1.1% | -1.01% | -0.23 | -10.53% | 0.66 |
| Snapshot B | theta=0.25% | 5 bps | 1.1% | -1.14% | -0.26 | -10.84% | 0.62 |
| Snapshot B | theta=0.25% | 10 bps | 1.1% | -1.28% | -0.29 | -11.16% | 0.59 |
| Snapshot B | theta=0.25% | 20 bps | 1.1% | -1.55% | -0.35 | -12.07% | 0.52 |
| Snapshot B | theta=0.50% | 0 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot B | theta=0.50% | 5 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot B | theta=0.50% | 10 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |
| Snapshot B | theta=0.50% | 20 bps | 0.0% | 0.00% | 0.00 | 0.00% | 0.00 |

---

## 5. Temporal Stability (Chronological Blocks at 10 bps)

| Snapshot | Block | Dates | Strategy ID | Ann Net Ret | Sharpe | Max DD | Profit Factor | Win Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Snapshot A | 2014-2016 | 2014-01-02 to 2016-12-31 | Strategy 1 | -22.20% | -1.88 | -53.46% | 0.73 | 45.6% |
| Snapshot A | 2014-2016 | 2014-01-02 to 2016-12-31 | Strategy 2 | -36.31% | -3.50 | -73.47% | 0.55 | 38.5% |
| Snapshot A | 2014-2016 | 2014-01-02 to 2016-12-31 | Strategy 4 (mag=0.10%) | -2.25% | -0.57 | -11.34% | 0.71 | 48.6% |
| Snapshot A | 2014-2016 | 2014-01-02 to 2016-12-31 | Strategy 5A (Reg + LowVol) | 2.45% | 0.53 | -4.62% | 1.23 | 52.3% |
| Snapshot A | 2014-2016 | 2014-01-02 to 2016-12-31 | Benchmark 2 | -35.70% | -3.37 | -73.02% | 0.57 | 39.7% |
| Snapshot A | 2017-2019 | 2017-01-02 to 2019-12-31 | Strategy 1 | -27.91% | -3.05 | -61.62% | 0.60 | 43.9% |
| Snapshot A | 2017-2019 | 2017-01-02 to 2019-12-31 | Strategy 2 | -34.13% | -4.02 | -71.08% | 0.49 | 39.6% |
| Snapshot A | 2017-2019 | 2017-01-02 to 2019-12-31 | Strategy 4 (mag=0.10%) | -2.60% | -1.21 | -9.11% | 0.35 | 35.5% |
| Snapshot A | 2017-2019 | 2017-01-02 to 2019-12-31 | Strategy 5A (Reg + LowVol) | -16.62% | -2.59 | -41.72% | 0.59 | 45.2% |
| Snapshot A | 2017-2019 | 2017-01-02 to 2019-12-31 | Benchmark 2 | -36.31% | -4.25 | -73.61% | 0.49 | 39.4% |
| Snapshot A | 2020-2021 | 2020-01-01 to 2021-12-31 | Strategy 1 | -36.81% | -2.22 | -60.95% | 0.64 | 44.4% |
| Snapshot A | 2020-2021 | 2020-01-01 to 2021-12-31 | Strategy 2 | -38.17% | -2.44 | -62.53% | 0.59 | 41.5% |
| Snapshot A | 2020-2021 | 2020-01-01 to 2021-12-31 | Strategy 4 (mag=0.10%) | 1.31% | 0.17 | -14.46% | 1.09 | 49.5% |
| Snapshot A | 2020-2021 | 2020-01-01 to 2021-12-31 | Strategy 5A (Reg + LowVol) | -6.53% | -1.43 | -13.16% | 0.57 | 41.2% |
| Snapshot A | 2020-2021 | 2020-01-01 to 2021-12-31 | Benchmark 2 | -40.52% | -2.53 | -65.29% | 0.60 | 42.8% |
| Snapshot B | 2014-2016 | 2014-01-02 to 2016-12-31 | Strategy 1 | -19.67% | -1.63 | -51.58% | 0.76 | 46.0% |
| Snapshot B | 2014-2016 | 2014-01-02 to 2016-12-31 | Strategy 2 | -30.93% | -2.89 | -66.79% | 0.60 | 40.9% |
| Snapshot B | 2014-2016 | 2014-01-02 to 2016-12-31 | Strategy 4 (mag=0.10%) | -2.09% | -0.43 | -10.68% | 0.80 | 50.6% |
| Snapshot B | 2014-2016 | 2014-01-02 to 2016-12-31 | Strategy 5A (Reg + LowVol) | -2.33% | -0.46 | -13.33% | 0.84 | 47.0% |
| Snapshot B | 2014-2016 | 2014-01-02 to 2016-12-31 | Benchmark 2 | -35.70% | -3.37 | -73.02% | 0.57 | 39.7% |
| Snapshot B | 2017-2019 | 2017-01-02 to 2019-12-31 | Strategy 1 | -33.07% | -3.76 | -68.90% | 0.53 | 41.6% |
| Snapshot B | 2017-2019 | 2017-01-02 to 2019-12-31 | Strategy 2 | -30.62% | -3.56 | -66.32% | 0.53 | 40.4% |
| Snapshot B | 2017-2019 | 2017-01-02 to 2019-12-31 | Strategy 4 (mag=0.10%) | -2.43% | -1.00 | -9.67% | 0.49 | 38.6% |
| Snapshot B | 2017-2019 | 2017-01-02 to 2019-12-31 | Strategy 5A (Reg + LowVol) | -19.86% | -3.15 | -47.52% | 0.52 | 41.7% |
| Snapshot B | 2017-2019 | 2017-01-02 to 2019-12-31 | Benchmark 2 | -36.31% | -4.25 | -73.61% | 0.49 | 39.4% |
| Snapshot B | 2020-2021 | 2020-01-01 to 2021-12-31 | Strategy 1 | -35.11% | -2.09 | -58.24% | 0.66 | 44.6% |
| Snapshot B | 2020-2021 | 2020-01-01 to 2021-12-31 | Strategy 2 | -34.32% | -2.14 | -57.93% | 0.62 | 43.1% |
| Snapshot B | 2020-2021 | 2020-01-01 to 2021-12-31 | Strategy 4 (mag=0.10%) | 3.92% | 0.43 | -11.44% | 1.21 | 51.9% |
| Snapshot B | 2020-2021 | 2020-01-01 to 2021-12-31 | Strategy 5A (Reg + LowVol) | -4.65% | -1.01 | -9.62% | 0.68 | 42.2% |
| Snapshot B | 2020-2021 | 2020-01-01 to 2021-12-31 | Benchmark 2 | -40.52% | -2.53 | -65.29% | 0.60 | 42.8% |

---

## 6. Regime-Conditioned Performance Profile

| Snapshot | Strategy ID | Regime Dim | Category | Governance | Sessions | Ann Net Ret | Sharpe | Max DD | Win Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Snapshot A | Strategy 1 | Volatility | LOW | STRONG_STATISTICAL | 699 | -19.25% | -2.21 | -50.67% | 45.9% |
| Snapshot A | Strategy 1 | Volatility | NORMAL | STRONG_STATISTICAL | 1011 | -32.15% | -2.88 | -79.67% | 43.0% |
| Snapshot A | Strategy 1 | Volatility | HIGH | STRONG_STATISTICAL | 215 | -31.07% | -1.74 | -33.01% | 47.9% |
| Snapshot A | Strategy 1 | Volatility | EXTREME | DESCRIPTIVE_ONLY | 35 | -57.52% | -1.64 | -12.52% | 45.7% |
| Snapshot A | Strategy 1 | Trend | BEARISH | STRONG_STATISTICAL | 567 | -28.81% | -1.66 | -58.04% | 47.6% |
| Snapshot A | Strategy 1 | Trend | NEUTRAL | STRONG_STATISTICAL | 755 | -28.10% | -2.86 | -63.20% | 43.4% |
| Snapshot A | Strategy 1 | Trend | BULLISH | STRONG_STATISTICAL | 638 | -28.01% | -2.70 | -57.63% | 43.4% |
| Snapshot A | Strategy 1 | Stress | CALM | STRONG_STATISTICAL | 1398 | -30.09% | -2.51 | -86.68% | 43.6% |
| Snapshot A | Strategy 1 | Stress | STRESSED | STRONG_STATISTICAL | 562 | -23.56% | -1.71 | -46.57% | 47.2% |
| Snapshot A | Strategy 2 | Volatility | LOW | STRONG_STATISTICAL | 699 | -33.13% | -4.30 | -67.74% | 39.0% |
| Snapshot A | Strategy 2 | Volatility | NORMAL | STRONG_STATISTICAL | 1011 | -37.28% | -3.59 | -85.02% | 39.3% |
| Snapshot A | Strategy 2 | Volatility | HIGH | STRONG_STATISTICAL | 215 | -35.29% | -2.13 | -32.23% | 42.5% |
| Snapshot A | Strategy 2 | Volatility | EXTREME | DESCRIPTIVE_ONLY | 35 | -54.85% | -1.59 | -10.86% | 46.2% |
| Snapshot A | Strategy 2 | Trend | BEARISH | STRONG_STATISTICAL | 567 | -33.35% | -2.04 | -62.28% | 44.2% |
| Snapshot A | Strategy 2 | Trend | NEUTRAL | STRONG_STATISTICAL | 755 | -40.44% | -4.68 | -78.87% | 36.5% |
| Snapshot A | Strategy 2 | Trend | BULLISH | STRONG_STATISTICAL | 638 | -32.74% | -3.56 | -64.03% | 39.1% |
| Snapshot A | Strategy 2 | Stress | CALM | STRONG_STATISTICAL | 1398 | -35.91% | -3.21 | -91.64% | 39.1% |
| Snapshot A | Strategy 2 | Stress | STRESSED | STRONG_STATISTICAL | 562 | -36.18% | -3.07 | -64.24% | 41.1% |
| Snapshot A | Strategy 3 (tau=0.45) | Volatility | LOW | STRONG_STATISTICAL | 699 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Strategy 3 (tau=0.45) | Volatility | NORMAL | STRONG_STATISTICAL | 1011 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Strategy 3 (tau=0.45) | Volatility | HIGH | STRONG_STATISTICAL | 215 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Strategy 3 (tau=0.45) | Volatility | EXTREME | DESCRIPTIVE_ONLY | 35 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Strategy 3 (tau=0.45) | Trend | BEARISH | STRONG_STATISTICAL | 567 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Strategy 3 (tau=0.45) | Trend | NEUTRAL | STRONG_STATISTICAL | 755 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Strategy 3 (tau=0.45) | Trend | BULLISH | STRONG_STATISTICAL | 638 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Strategy 3 (tau=0.45) | Stress | CALM | STRONG_STATISTICAL | 1398 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Strategy 3 (tau=0.45) | Stress | STRESSED | STRONG_STATISTICAL | 562 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot A | Benchmark 2 | Volatility | LOW | STRONG_STATISTICAL | 699 | -34.05% | -4.37 | -69.45% | 39.2% |
| Snapshot A | Benchmark 2 | Volatility | NORMAL | STRONG_STATISTICAL | 1011 | -38.67% | -3.66 | -86.36% | 40.2% |
| Snapshot A | Benchmark 2 | Volatility | HIGH | STRONG_STATISTICAL | 215 | -32.60% | -1.85 | -29.83% | 44.7% |
| Snapshot A | Benchmark 2 | Volatility | EXTREME | DESCRIPTIVE_ONLY | 35 | -69.37% | -2.36 | -12.42% | 42.9% |
| Snapshot A | Benchmark 2 | Trend | BEARISH | STRONG_STATISTICAL | 567 | -34.10% | -2.07 | -63.24% | 44.6% |
| Snapshot A | Benchmark 2 | Trend | NEUTRAL | STRONG_STATISTICAL | 755 | -40.69% | -4.61 | -79.13% | 37.4% |
| Snapshot A | Benchmark 2 | Trend | BULLISH | STRONG_STATISTICAL | 638 | -35.57% | -3.64 | -68.46% | 40.1% |
| Snapshot A | Benchmark 2 | Stress | CALM | STRONG_STATISTICAL | 1398 | -36.90% | -3.25 | -92.42% | 39.6% |
| Snapshot A | Benchmark 2 | Stress | STRESSED | STRONG_STATISTICAL | 562 | -37.88% | -3.09 | -66.32% | 42.3% |
| Snapshot B | Strategy 1 | Volatility | LOW | STRONG_STATISTICAL | 699 | -25.24% | -3.02 | -58.45% | 42.8% |
| Snapshot B | Strategy 1 | Volatility | NORMAL | STRONG_STATISTICAL | 1011 | -30.81% | -2.73 | -77.75% | 43.5% |
| Snapshot B | Strategy 1 | Volatility | HIGH | STRONG_STATISTICAL | 215 | -22.74% | -1.17 | -29.28% | 49.8% |
| Snapshot B | Strategy 1 | Volatility | EXTREME | DESCRIPTIVE_ONLY | 35 | -66.60% | -2.16 | -12.42% | 45.7% |
| Snapshot B | Strategy 1 | Trend | BEARISH | STRONG_STATISTICAL | 567 | -22.91% | -1.25 | -51.07% | 48.7% |
| Snapshot B | Strategy 1 | Trend | NEUTRAL | STRONG_STATISTICAL | 755 | -34.83% | -3.75 | -72.60% | 41.6% |
| Snapshot B | Strategy 1 | Trend | BULLISH | STRONG_STATISTICAL | 638 | -26.76% | -2.55 | -56.29% | 42.6% |
| Snapshot B | Strategy 1 | Stress | CALM | STRONG_STATISTICAL | 1400 | -25.90% | -2.07 | -82.52% | 44.1% |
| Snapshot B | Strategy 1 | Stress | STRESSED | STRONG_STATISTICAL | 560 | -35.99% | -2.92 | -63.75% | 43.6% |
| Snapshot B | Strategy 2 | Volatility | LOW | STRONG_STATISTICAL | 699 | -30.32% | -3.98 | -63.54% | 39.5% |
| Snapshot B | Strategy 2 | Volatility | NORMAL | STRONG_STATISTICAL | 1011 | -33.08% | -3.11 | -80.66% | 41.3% |
| Snapshot B | Strategy 2 | Volatility | HIGH | STRONG_STATISTICAL | 215 | -26.82% | -1.51 | -26.01% | 45.3% |
| Snapshot B | Strategy 2 | Volatility | EXTREME | DESCRIPTIVE_ONLY | 35 | -45.69% | -1.18 | -10.20% | 52.0% |
| Snapshot B | Strategy 2 | Trend | BEARISH | STRONG_STATISTICAL | 567 | -28.97% | -1.72 | -56.00% | 45.1% |
| Snapshot B | Strategy 2 | Trend | NEUTRAL | STRONG_STATISTICAL | 755 | -36.70% | -4.12 | -74.76% | 38.3% |
| Snapshot B | Strategy 2 | Trend | BULLISH | STRONG_STATISTICAL | 638 | -27.81% | -3.00 | -57.14% | 41.2% |
| Snapshot B | Strategy 2 | Stress | CALM | STRONG_STATISTICAL | 1400 | -28.91% | -2.46 | -85.22% | 40.9% |
| Snapshot B | Strategy 2 | Stress | STRESSED | STRONG_STATISTICAL | 560 | -38.19% | -3.38 | -66.36% | 42.0% |
| Snapshot B | Strategy 3 (tau=0.45) | Volatility | LOW | STRONG_STATISTICAL | 699 | -0.13% | -0.39 | -0.64% | 33.3% |
| Snapshot B | Strategy 3 (tau=0.45) | Volatility | NORMAL | STRONG_STATISTICAL | 1011 | 0.50% | 0.21 | -3.90% | 40.0% |
| Snapshot B | Strategy 3 (tau=0.45) | Volatility | HIGH | STRONG_STATISTICAL | 215 | 3.34% | 0.96 | -1.14% | 62.5% |
| Snapshot B | Strategy 3 (tau=0.45) | Volatility | EXTREME | DESCRIPTIVE_ONLY | 35 | 0.00% | 0.00 | 0.00% | 0.0% |
| Snapshot B | Strategy 3 (tau=0.45) | Trend | BEARISH | STRONG_STATISTICAL | 567 | 2.69% | 0.76 | -2.09% | 42.9% |
| Snapshot B | Strategy 3 (tau=0.45) | Trend | NEUTRAL | STRONG_STATISTICAL | 755 | -1.03% | -0.83 | -3.90% | 45.5% |
| Snapshot B | Strategy 3 (tau=0.45) | Trend | BULLISH | STRONG_STATISTICAL | 638 | 0.62% | 0.58 | -1.02% | 50.0% |
| Snapshot B | Strategy 3 (tau=0.45) | Stress | CALM | STRONG_STATISTICAL | 1400 | 0.87% | 0.38 | -2.71% | 47.6% |
| Snapshot B | Strategy 3 (tau=0.45) | Stress | STRESSED | STRONG_STATISTICAL | 560 | -0.17% | -0.11 | -2.50% | 40.0% |
| Snapshot B | Benchmark 2 | Volatility | LOW | STRONG_STATISTICAL | 699 | -34.05% | -4.37 | -69.45% | 39.2% |
| Snapshot B | Benchmark 2 | Volatility | NORMAL | STRONG_STATISTICAL | 1011 | -38.67% | -3.66 | -86.36% | 40.2% |
| Snapshot B | Benchmark 2 | Volatility | HIGH | STRONG_STATISTICAL | 215 | -32.60% | -1.85 | -29.83% | 44.7% |
| Snapshot B | Benchmark 2 | Volatility | EXTREME | DESCRIPTIVE_ONLY | 35 | -69.37% | -2.36 | -12.42% | 42.9% |
| Snapshot B | Benchmark 2 | Trend | BEARISH | STRONG_STATISTICAL | 567 | -34.10% | -2.07 | -63.24% | 44.6% |
| Snapshot B | Benchmark 2 | Trend | NEUTRAL | STRONG_STATISTICAL | 755 | -40.69% | -4.61 | -79.13% | 37.4% |
| Snapshot B | Benchmark 2 | Trend | BULLISH | STRONG_STATISTICAL | 638 | -35.57% | -3.64 | -68.46% | 40.1% |
| Snapshot B | Benchmark 2 | Stress | CALM | STRONG_STATISTICAL | 1400 | -34.99% | -3.02 | -91.04% | 39.9% |
| Snapshot B | Benchmark 2 | Stress | STRESSED | STRONG_STATISTICAL | 560 | -42.36% | -3.64 | -71.19% | 41.6% |

---

## 7. Drawdown & Worst 5 Drawdown Episodes

Top peak-to-trough drawdowns for primary strategies at 10 bps friction:

| Snapshot | Strategy ID | Rank | Peak Date | Trough Date | Recovery Date | Max DD | Duration (Sessions) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Snapshot A | Strategy 1 | #1 | 2014-05-12 | 2021-12-23 | UNRECOVERED | -92.78% | 1876 |
| Snapshot A | Strategy 1 | #2 | 2014-01-06 | 2014-03-04 | 2014-05-09 | -7.25% | 81 |
| Snapshot A | Strategy 2 | #1 | 2014-01-02 | 2021-12-23 | UNRECOVERED | -96.97% | 1960 |
| Snapshot A | Strategy 4 (mag=0.10%) | #1 | 2014-04-07 | 2020-05-15 | UNRECOVERED | -23.73% | 1896 |
| Snapshot A | Strategy 4 (mag=0.10%) | #2 | 2014-01-10 | 2014-01-13 | 2014-03-06 | -0.39% | 37 |
| Snapshot A | Strategy 5A (Reg + LowVol) | #1 | 2015-10-21 | 2021-10-27 | UNRECOVERED | -50.67% | 1523 |
| Snapshot A | Strategy 5A (Reg + LowVol) | #2 | 2014-09-15 | 2014-09-19 | 2014-11-21 | -3.35% | 41 |
| Snapshot A | Strategy 5A (Reg + LowVol) | #3 | 2014-11-27 | 2014-12-12 | 2015-07-20 | -2.00% | 157 |
| Snapshot A | Strategy 5A (Reg + LowVol) | #4 | 2014-03-26 | 2014-04-02 | 2014-04-11 | -1.70% | 11 |
| Snapshot A | Strategy 5A (Reg + LowVol) | #5 | 2014-04-15 | 2014-04-16 | 2014-04-28 | -1.35% | 7 |
| Snapshot B | Strategy 1 | #1 | 2014-05-12 | 2021-12-23 | UNRECOVERED | -93.55% | 1876 |
| Snapshot B | Strategy 1 | #2 | 2014-01-03 | 2014-02-06 | 2014-03-05 | -4.56% | 41 |
| Snapshot B | Strategy 1 | #3 | 2014-03-07 | 2014-04-04 | 2014-04-16 | -3.26% | 25 |
| Snapshot B | Strategy 1 | #4 | 2014-04-17 | 2014-05-06 | 2014-05-08 | -1.81% | 12 |
| Snapshot B | Strategy 2 | #1 | 2014-03-27 | 2021-12-20 | UNRECOVERED | -95.01% | 1903 |
| Snapshot B | Strategy 2 | #2 | 2014-01-02 | 2014-02-12 | 2014-03-24 | -4.76% | 54 |
| Snapshot B | Strategy 2 | #3 | 2014-03-24 | 2014-03-25 | 2014-03-26 | -0.32% | 2 |
| Snapshot B | Strategy 4 (mag=0.10%) | #1 | 2014-04-07 | 2020-05-13 | UNRECOVERED | -23.98% | 1896 |
| Snapshot B | Strategy 4 (mag=0.10%) | #2 | 2014-01-10 | 2014-02-05 | 2014-03-06 | -0.62% | 37 |
| Snapshot B | Strategy 5A (Reg + LowVol) | #1 | 2014-11-27 | 2021-10-27 | UNRECOVERED | -58.45% | 1744 |
| Snapshot B | Strategy 5A (Reg + LowVol) | #2 | 2014-09-05 | 2014-09-16 | 2014-11-26 | -2.40% | 50 |
| Snapshot B | Strategy 5A (Reg + LowVol) | #3 | 2014-03-27 | 2014-04-04 | 2014-04-15 | -2.29% | 11 |
| Snapshot B | Strategy 5A (Reg + LowVol) | #4 | 2014-04-17 | 2014-05-06 | 2014-05-08 | -1.81% | 12 |
| Snapshot B | Strategy 5A (Reg + LowVol) | #5 | 2014-01-22 | 2014-01-23 | 2014-03-05 | -0.65% | 28 |

---

## 8. Time-Series Statistical Robustness

Newey-West HAC standard errors and stationary block bootstrap 95% confidence intervals:

| Snapshot | Strategy ID | Mean Daily Net Ret | HAC Std Error | HAC t-stat | HAC p-value | Ann Net Ret 95% CI | Sharpe 95% CI |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Snapshot A | Strategy 1 | -0.1278% | 0.0205% | -6.24 | 4.44e-10 | [-35.2%, -21.2%] | [-2.95, -1.68] |
| Snapshot A | Strategy 2 | -0.1731% | 0.0173% | -10.03 | 0.00e+00 | [-41.0%, -30.8%] | [-3.97, -2.44] |
| Snapshot A | Strategy 4 (mag=0.10%) | -0.0052% | 0.0075% | -0.70 | 4.85e-01 | [-4.8%, 2.2%] | [-0.89, 0.39] |
| Snapshot A | Strategy 5A (Reg + LowVol) | -0.0296% | 0.0080% | -3.72 | 1.97e-04 | [-11.2%, -3.5%] | [-1.98, -0.63] |
| Snapshot B | Strategy 1 | -0.1314% | 0.0199% | -6.62 | 3.69e-11 | [-35.8%, -22.0%] | [-3.04, -1.70] |
| Snapshot B | Strategy 2 | -0.1475% | 0.0177% | -8.33 | 0.00e+00 | [-37.8%, -25.6%] | [-3.53, -1.97] |
| Snapshot B | Strategy 4 (mag=0.10%) | -0.0022% | 0.0075% | -0.29 | 7.71e-01 | [-4.5%, 3.2%] | [-0.74, 0.59] |
| Snapshot B | Strategy 5A (Reg + LowVol) | -0.0405% | 0.0085% | -4.75 | 2.00e-06 | [-13.8%, -5.8%] | [-2.48, -1.05] |

---

## 9. Protected Invariant Audit

All 19 protected Phase 4–10 artifacts remain 100% byte-for-byte unmodified:
```
data/features/nifty50_features_clean.csv: afa2e68f50f1ad0f4b1adbbec3df294d474d688dbf481cf53c76c4db0a78914b
data/targets/nifty50_targets_snapshot_a.csv: a13fed61f92c3fcccf9fe09ce59eb0df4d95ef8dce0aef970ff5ed1220ea055d
data/targets/nifty50_targets_snapshot_b.csv: 54ac54fdeafd53ddea20b1d31cd89c1fbaebdbc88c0f24f8a1f73ce2867e01d2
data/interim/context/snapshot_a_context_daily.csv: 26f41d5978b2f78fb9fad223d9efe9970820ab7f81510490ed6f1b39872178af
data/interim/context/snapshot_b_context_daily.csv: 08a694f86f70c5246b8b6b4928283b676dd998912e481d88a718ba08970237be
data/interim/news/features_news_snapshot_a.csv: 487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7
data/interim/news/features_news_snapshot_b.csv: f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606
data/interim/news/phase9_step4_oof_results.csv: 62b88a1689c7ed57e1ddf79ca0064356eec5d2a16e00f7975998a155141f02d8
data/interim/news/phase9_step4_holdout_results.csv: 4359edb7e585053c676e444d958a4265c584b9b13a58c89dd38067fc0bc41967
data/interim/news/phase9_step4_experiment_results.csv: 7d0f39f7ce8a50b6f8b1591dc6ce9b3a4af8f75507531740a06147cb4aedffc3
configs/phase9_step4_experiment_config.json: 8940206588dad34eb5a9d2fdb01ecbfeb629930374a733c15d077b2281ae7547
data/interim/regime/phase10_regime_performance.csv: a4a0eda897d97e81d8e2ebadac169cb8e476609506553802dc98e5cd5db62024
data/interim/regime/phase10_temporal_stability.csv: f9e04538bf3eca7ff00861a2728bd770c1d17fa1a10d4319e10a84788d16bf17
data/interim/regime/phase10_error_analysis.csv: 9b5091538f37ad2a6c4d6598a616c20d6cebb82b8dae0abb97d287119e5d2d3d
data/interim/regime/phase10_confidence_calibration.csv: 06b784ef89e19528bfa4d5fbca4d5c5718f2b87403bdc4c914dee0d34fdaa82f
data/interim/regime/phase10_feature_importance.csv: d276270720829419a7b4b5d6ff5807cc7e59df4762b6e2f549f7b5d48c80af21
data/interim/regime/phase10_shap_summary.csv: 71e899b599a443d152350460dc96dd3334465b71c8e6388613b08d44098a070a
configs/phase10_regime_explainability_config.json: 9230e238172bac572bd01451fb848a960dd7676191737833029be90cea1af3f1
docs/PHASE_10_REGIME_EXPLAINABILITY_ERROR_ANALYSIS_REPORT.md: 282c65112a64e4a547cab6e82861f1ec513c7a833c738ce8a9524f8d88ed5c8a
```

---

## 10. Final Status & Strict Stop Condition

> [!IMPORTANT]
> **STAGE 1 COMPLETE — TERMINAL HOLDOUT SEALED**  
> 1. The Development OOF evaluation is fully complete and frozen.
> 2. The 2022–2026 Terminal Holdout ($N=1,154$) remains **100% unaccessed and unpolluted**.
> 3. No strategy selection or threshold tuning has taken place.
> 4. In accordance with the Stage 1 authorization rules, execution is **HALTED**. Awaiting explicit user authorization before Stage 2.