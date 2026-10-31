# PHASE 11 — STAGE 2: TERMINAL HOLDOUT STRATEGY EVALUATION REPORT

**Status**: STAGE 2 TERMINAL HOLDOUT EVALUATION COMPLETE — TERMINAL HOLDOUT CONSUMED  
**Date**: September 18, 2026  
**Auditor / Researcher**: Senior ML/Quant Research Engineer  
**Model Evaluated**: Model 1 (Price + Context, 63 features, 0 News)  
**Evaluation Partition**: Terminal Holdout (`2022-01-03` through `2026-09-03`, $N=1,154$ sessions)  
**Governance**: Single-Pass Evaluation — Zero Tuning / Zero Optimization / Zero Leakage  
**Regression Test Suite**: **221/221 PASSED** in 13.32s  

---

## 1. Executive Summary & Core Scientific Findings

Phase 11 Stage 2 executes the single-pass, out-of-sample economic-value evaluation of the production-validated **Model 1 (Price + Context)** baseline predictions across the sealed Terminal Holdout partition (`2022-01-03` to `2026-09-03`, $N=1,154$ sessions).

This evaluation follows the exact pre-registered methodology frozen in `configs/phase11_strategy_validation_config.json` and validated by the Stage 2 Pre-Authorization Forensic Audit.

### Core Empirical Findings

1. **Failure of High-Turnover Intraday Strategies (Primary Execution Convention)**:
   - Under the primary execution convention (enter at next session Open, exit at same session Close), **every continuous daily trading strategy incurs severe net losses across the 4.6-year holdout period**.
   - At 10 bps round-trip friction, unrestricted **Strategy 1 (Regression Direction)** incurs an annualized net loss of **-27.17%** in Snapshot A and **-27.17%** in Snapshot B (cumulative net loss of -76.8% and -76.8%, Max DD -77.5%).
   - Unrestricted **Strategy 2 (Classifier Direction)** loses **-28.11%** annualized in Snapshot A and **-24.96%** in Snapshot B (Max DD -78.3%).
   - This breakdown mirrors the Stage 1 OOF findings and is driven by the structural characteristics of spot index cash trading:
     - **Negative Cash Intraday Drift**: In Indian index spot markets, Open-to-Close price changes exhibit persistent negative drift. **Benchmark 2 (Always-Long Open-to-Close)** loses **-28.53% annualized net at 10 bps** (-78.97% max drawdown).
     - **Friction Drag**: Continuous daily round-trip transactions (1,154 trading days) subtract 25.2% annualized in direct execution friction at 10 bps.

2. **Confidence and Magnitude Gating Mitigate Friction but Remain Economically Inconclusive**:
   - Gating significantly curtails transaction frequency:
     - **Strategy 3 (Confidence Gate)**: At $\tau=0.40$, net annualized loss slows to **-8.44%** (Snapshot A, active session pct 49.8%) and **-9.35%** (Snapshot B, active session pct 66.6%). At $\tau=0.45$ and $\tau=0.50$, the calibrated model rarely triggers trades ($0.0\%$ active in Snapshot A, $2.0\%$ in Snapshot B), producing flat performance.
     - **Strategy 4 (Magnitude Gate)**: At $\theta=0.10\%$, net annualized loss slows to **-4.45%** (Snapshot A, active session pct 10.7%) and **-1.92%** (Snapshot B, active session pct 11.1%). At $\theta=0.25\%$ and $\theta=0.50\%$, the strategy is essentially inactive ($0.2\%$ active exposure).

3. **Phase 10 LOW-Volatility Diagnostic Filter (Strategy 5)**:
   - Applying the frozen Phase 10 LOW-volatility filter ($\sigma_{20d} \le 11.4675\%$) restricts trading to $49.3\%$ of holdout sessions.
   - While max drawdown is dampened relative to unrestricted trading (from -77.5% down to -45.7% in Strategy 5A), annualized net return under the primary convention remains negative (**-19.88%** in Snapshot A at 10 bps).
   - Under the secondary Close-to-Close diagnostic convention, Strategy 5A achieves **+0.64% annualized net** (Sharpe 0.122, Max DD -10.83%), but substantially underperforms buy-and-hold.

4. **Secondary Diagnostic Execution Convention (Close-to-Close Interday Holding)**:
   - When holding interday from Close to Close (turnover-based costs and overnight gap capture):
     - **Benchmark 1 Buy-and-Hold** achieves **+6.86% annualized net** (Sharpe 0.552, Max DD -16.47%).
     - **Strategy 1** achieves **+5.80% annualized net** (Sharpe 0.479, Max DD -18.33%) in Snapshot A, and **-2.54% annualized net** (Sharpe -0.118, Max DD -34.27%) in Snapshot B.
     - **Strategy 2** achieves **+5.01% annualized net** (Sharpe 0.427, Max DD -16.66%) in Snapshot A, and **+3.71% annualized net** (Sharpe 0.344, Max DD -25.56%) in Snapshot B.
   - Neither strategy demonstrates robust economic outperformance over simple buy-and-hold.

---

## 2. Pre-Registered Evidence Classification (Holdout)

Per Section 18 of the specification, every strategy is classified strictly by empirical evidence:

| Strategy ID | Strategy Name | Primary Convention (10 bps) | Secondary Convention (10 bps) | Evidence Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Strategy 0** | Always Flat Baseline | $0.0\%$ ret, $0.0$ DD | $0.0\%$ ret, $0.0$ DD | **C) NO ECONOMIC EVIDENCE (Zero Baseline)** |
| **Strategy 1** | Regression Direction | Net: **-27.17%** (A), **-27.17%** (B) | Net: $+5.80\%$ (A), $-2.54\%$ (B) | **D) NEGATIVE AFTER COSTS** |
| **Strategy 2** | Classifier Direction | Net: **-28.11%** (A), **-24.96%** (B) | Net: $+5.01\%$ (A), $+3.71\%$ (B) | **D) NEGATIVE AFTER COSTS** |
| **Strategy 3 ($\tau=0.40$)** | Classifier + Conf Gate (0.40) | Net: $-8.44\%$ (A), $-9.35\%$ (B) | Net: $+3.19\%$ (A), $-2.04\%$ (B) | **D) NEGATIVE AFTER COSTS** |
| **Strategy 3 ($\tau=0.45$)** | Classifier + Conf Gate (0.45) | Net: $0.0\%$ (A), $+0.03\%$ (B) | Net: $0.0\%$ (A), $+0.03\%$ (B) | **C) NO ECONOMIC EVIDENCE (Inactive)** |
| **Strategy 3 ($\tau=0.50$)** | Classifier + Conf Gate (0.50) | Net: $0.0\%$ (A), $0.0\%$ (B) | Net: $0.0\%$ (A), $0.0\%$ (B) | **C) NO ECONOMIC EVIDENCE (Inactive)** |
| **Strategy 4 (mag=$0.10\%$)**| Reg Magnitude Gate (0.10%) | Net: $-4.45\%$ (A), $-1.92\%$ (B) | Net: $+0.19\%$ (A), $+1.96\%$ (B) | **D) NEGATIVE AFTER COSTS** |
| **Strategy 4 (mag=$0.25\%$)**| Reg Magnitude Gate (0.25%) | Net: $-0.35\%$ (A), $+0.30\%$ (B) | Net: $-0.35\%$ (A), $+0.30\%$ (B) | **C) NO ECONOMIC EVIDENCE (Inactive)** |
| **Strategy 4 (mag=$0.50\%$)**| Reg Magnitude Gate (0.50%) | Net: $0.0\%$ (A), $0.0\%$ (B) | Net: $0.0\%$ (A), $0.0\%$ (B) | **C) NO ECONOMIC EVIDENCE (Inactive)** |
| **Strategy 5A** | Reg + LOW-Vol Diagnostic | Net: **-19.88%** (A), **-19.88%** (B) | Net: $+0.64\%$ (A), $+3.22\%$ (B) | **D) NEGATIVE AFTER COSTS (Primary)** |
| **Strategy 5B** | Clf + LOW-Vol Diagnostic | Net: **-17.76%** (A), **-17.76%** (B) | Net: $+2.55\%$ (A), $+2.33\%$ (B) | **D) NEGATIVE AFTER COSTS (Primary)** |

---

## 3. Comprehensive Holdout Performance Tables

### 3.1 Snapshot A — Primary Execution Convention (Open-to-Close)

| Strategy ID | Cost Scenario | Ann Net Ret | Sharpe | Sortino | Max DD | Calmar | Win Rate | Profit Factor | NW p-value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy 0** | 10 bps | $0.00\%$ | $0.00$ | $0.00$ | $0.00\%$ | $0.00$ | $0.0\%$ | $0.00$ | $1.00$ |
| **Strategy 1** | 0 bps | $-6.28\%$ | $-0.55$ | $-0.77$ | $-35.82\%$ | $-0.18$ | $48.9\%$ | $0.93$ | $0.194$ |
| | 5 bps | $-17.38\%$ | $-1.72$ | $-2.21$ | $-61.22\%$ | $-0.28$ | $45.6\%$ | $0.78$ | $1.15 \times 10^{-4}$ |
| | 10 bps | **$-27.17\%$** | $-2.90$ | $-3.50$ | **$-77.52\%$** | $-0.35$ | $42.2\%$ | $0.66$ | $1.02 \times 10^{-11}$ |
| | 20 bps | $-43.42\%$ | $-5.24$ | $-5.75$ | $-92.73\%$ | $-0.47$ | $35.4\%$ | $0.46$ | $< 10^{-15}$ |
| **Strategy 2** | 0 bps | $-8.46\%$ | $-0.78$ | $-1.09$ | $-37.18\%$ | $-0.23$ | $48.2\%$ | $0.89$ | $0.076$ |
| | 5 bps | $-18.88\%$ | $-1.92$ | $-2.48$ | $-62.48\%$ | $-0.30$ | $44.7\%$ | $0.76$ | $1.64 \times 10^{-5}$ |
| | 10 bps | **$-28.11\%$** | $-3.05$ | $-3.71$ | **$-78.34\%$** | $-0.36$ | $41.3\%$ | $0.65$ | $1.06 \times 10^{-12}$ |
| | 20 bps | $-43.56\%$ | $-5.32$ | $-5.93$ | $-92.78\%$ | $-0.47$ | $35.4\%$ | $0.47$ | $< 10^{-15}$ |
| **Strategy 3 ($\tau=0.40$)** | 10 bps | $-8.44\%$ | $-1.11$ | $-1.49$ | $-44.97\%$ | $-0.19$ | $43.3\%$ | $0.77$ | $2.55 \times 10^{-3}$ |
| **Strategy 4 ($0.10\%$)** | 0 bps | $-1.95\%$ | $-0.62$ | $-0.85$ | $-13.39\%$ | $-0.15$ | $46.8\%$ | $0.88$ | $0.219$ |
| | 10 bps | **$-4.45\%$** | $-1.47$ | $-1.86$ | **$-23.47\%$** | $-0.19$ | $39.5\%$ | $0.72$ | $1.04 \times 10^{-3}$ |
| **Strategy 5A (LowVol)** | 10 bps | **$-19.88\%$** | $-3.30$ | $-4.13$ | **$-45.65\%$** | $-0.44$ | $39.5\%$ | $0.57$ | $4.47 \times 10^{-11}$ |
| **Benchmark 2 (Long)** | 10 bps | $-28.53\%$ | $-3.07$ | $-3.68$ | $-78.97\%$ | $-0.36$ | $41.7\%$ | $0.59$ | $4.20 \times 10^{-14}$ |

### 3.2 Snapshot B — Primary Execution Convention (Open-to-Close)

| Strategy ID | Cost Scenario | Ann Net Ret | Sharpe | Sortino | Max DD | Calmar | Win Rate | Profit Factor | NW p-value |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Strategy 1** | 10 bps | **$-27.17\%$** | $-2.90$ | $-3.50$ | **$-77.52\%$** | $-0.35$ | $42.2\%$ | $0.66$ | $1.02 \times 10^{-11}$ |
| **Strategy 2** | 10 bps | **$-24.96\%$** | $-2.72$ | $-3.37$ | **$-75.87\%$** | $-0.33$ | $42.3\%$ | $0.67$ | $2.02 \times 10^{-10}$ |
| **Strategy 3 ($\tau=0.40$)** | 10 bps | $-9.35\%$ | $-0.95$ | $-1.27$ | $-52.79\%$ | $-0.18$ | $43.8\%$ | $0.81$ | $1.39 \times 10^{-2}$ |
| **Strategy 4 ($0.10\%$)** | 0 bps | $+0.62\%$ | $+0.19$ | $+0.29$ | $-8.53\%$ | $+0.07$ | $50.8\%$ | $1.09$ | $0.707$ |
| | 10 bps | **$-1.92\%$** | $-0.63$ | $-0.87$ | **$-14.48\%$** | $-0.13$ | $44.5\%$ | $0.84$ | $0.210$ |
| **Strategy 5A (LowVol)** | 10 bps | **$-19.88\%$** | $-3.30$ | $-4.13$ | **$-45.65\%$** | $-0.44$ | $39.5\%$ | $0.57$ | $4.47 \times 10^{-11}$ |

### 3.3 Secondary Diagnostic Convention (Close-to-Close)

| Strategy ID | Cost Scenario | Ann Net Ret | Sharpe | Sortino | Max DD | Calmar | Win Rate | Turn/yr |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Benchmark 1 (Buy & Hold)**| 10 bps | **$+6.86\%$** | **0.552** | **0.778** | **$-16.47\%$** | **0.42** | $52.5\%$ | 0.22 |
| **Strategy 1 (A)** | 10 bps | $+5.80\%$ | 0.479 | 0.685 | $-18.33\%$ | 0.32 | $52.2\%$ | 134.1 |
| **Strategy 1 (B)** | 10 bps | $-2.54\%$ | -0.118 | -0.162 | $-34.27\%$ | -0.07 | $49.7\%$ | 134.1 |
| **Strategy 2 (A)** | 10 bps | $+5.01\%$ | 0.427 | 0.601 | $-16.66\%$ | 0.30 | $51.9\%$ | 105.7 |
| **Strategy 2 (B)** | 10 bps | $+3.71\%$ | 0.344 | 0.491 | $-25.56\%$ | 0.15 | $50.9\%$ | 102.6 |
| **Strategy 5A (A - LowVol)**| 10 bps | $+0.64\%$ | 0.122 | 0.173 | **$-10.83\%$** | 0.06 | $52.9\%$ | 35.8 |
| **Strategy 5A (B - LowVol)**| 10 bps | $+3.22\%$ | 0.457 | 0.678 | **$-12.86\%$** | 0.25 | $51.1\%$ | 35.8 |

---

## 4. Cost Sensitivity Analysis

The impact of transaction costs across scenarios ($0, 5, 10, 20$ bps round-trip) on Strategy 1 and Strategy 2 under the primary Open-to-Close convention:

| Strategy | Cost Scenario | Ann Net Ret | Sharpe | Sortino | Max DD | Calmar | Active Sessions |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Strategy 1 (A)** | 0 bps (Gross) | $-6.28\%$ | $-0.55$ | $-0.77$ | $-35.82\%$ | $-0.18$ | 1,154 (100%) |
| | 5 bps | $-17.38\%$ | $-1.72$ | $-2.21$ | $-61.22\%$ | $-0.28$ | 1,154 (100%) |
| | 10 bps | $-27.17\%$ | $-2.90$ | $-3.50$ | $-77.52\%$ | $-0.35$ | 1,154 (100%) |
| | 20 bps | $-43.42\%$ | $-5.24$ | $-5.75$ | $-92.73\%$ | $-0.47$ | 1,154 (100%) |
| **Strategy 2 (A)** | 0 bps (Gross) | $-8.46\%$ | $-0.78$ | $-1.09$ | $-37.18\%$ | $-0.23$ | 1,106 (95.8%) |
| | 5 bps | $-18.88\%$ | $-1.92$ | $-2.48$ | $-62.48\%$ | $-0.30$ | 1,106 (95.8%) |
| | 10 bps | $-28.11\%$ | $-3.05$ | $-3.71$ | $-78.34\%$ | $-0.36$ | 1,106 (95.8%) |
| | 20 bps | $-43.56\%$ | $-5.32$ | $-5.93$ | $-92.78\%$ | $-0.47$ | 1,106 (95.8%) |

**Finding**: Even before costs (0 bps), gross return is negative ($-6.28\%$ in S1, $-8.46\%$ in S2), demonstrating that the primary intraday cash convention carries negative intrinsic drift. Transaction costs systematically amplify the loss rate.

---

## 5. Temporal Stability Across Holdout Sub-Periods

Evaluation across pre-registered temporal blocks and individual calendar years (Primary Convention at 10 bps):

| Temporal Period | Start Date | End Date | Sessions | Strategy 1 Ann Ret | Strategy 1 Sharpe | Strategy 2 Ann Ret | Benchmark 2 Ann Ret |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Block: 2022–2023** | 2022-01-03 | 2023-12-29 | 496 | $-24.08\%$ | $-2.85$ | $-27.18\%$ | $-30.13\%$ |
| **Block: 2024–2026** | 2024-01-01 | 2026-09-03 | 658 | $-29.43\%$ | $-2.93$ | $-28.80\%$ | $-27.30\%$ |
| **Year: 2022** | 2022-01-03 | 2022-12-30 | 248 | $-20.84\%$ | $-2.17$ | $-26.04\%$ | $-28.01\%$ |
| **Year: 2023** | 2023-01-02 | 2023-12-29 | 248 | $-27.18\%$ | $-3.70$ | $-28.30\%$ | $-32.16\%$ |
| **Year: 2024** | 2024-01-01 | 2024-12-31 | 246 | $-36.79\%$ | $-3.74$ | $-33.07\%$ | $-33.28\%$ |
| **Year: 2025** | 2025-01-01 | 2025-12-31 | 249 | $-24.95\%$ | $-2.99$ | $-22.17\%$ | $-21.72\%$ |
| **Year: 2026** | 2026-01-01 | 2026-09-03 | 163 | $-26.18\%$ | $-2.88$ | $-30.87\%$ | $-30.23\%$ |

**Finding**: Consistent negative performance across all sub-periods and individual years under the primary convention.

---

## 6. Regime Diagnostics (Holdout)

Performance conditioned on frozen Development regime thresholds (Primary Convention at 10 bps):

| Dimension | Regime Category | Sessions ($N$) | Governance | Strategy 1 Ann Ret | Strategy 1 Sharpe | Strategy 1 Max DD | Benchmark 2 Ann Ret |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: |
| **Volatility** | LOW ($\le 11.47\%$) | 569 | STRONG | $-32.16\%$ | $-4.37$ | $-58.12\%$ | $-29.84\%$ |
| | NORMAL ($11.47\%\text{--}16.48\%$) | 468 | STRONG | $-30.66\%$ | $-3.03$ | $-51.25\%$ | $-32.02\%$ |
| | HIGH ($> 16.48\%$) | 117 | STRONG | $+25.17\%$ | $+1.69$ | $-4.47\%$ | $-4.51\%$ |
| **Trend** | BEARISH | 399 | STRONG | $-22.21\%$ | $-2.06$ | $-36.58\%$ | $-26.33\%$ |
| | NEUTRAL | 457 | STRONG | $-26.83\%$ | $-3.15$ | $-45.57\%$ | $-26.48\%$ |
| | BULLISH | 298 | STRONG | $-33.81\%$ | $-3.83$ | $-39.37\%$ | $-34.29\%$ |
| **Stress** | CALM | 794 | STRONG | $-26.01\%$ | $-2.74$ | $-62.38\%$ | $-27.30\%$ |
| | STRESSED | 360 | STRONG | $-29.67\%$ | $-3.23$ | $-41.63\%$ | $-31.19\%$ |

---

## 7. Drawdown Analysis

Top peak-to-trough drawdown episodes for unrestricted strategies at 10 bps:

| Strategy | Rank | Peak Date | Trough Date | Recovery Date | Max Drawdown | Duration |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Strategy 1 (A)** | #1 | 2022-04-01 | 2026-08-31 | UNRECOVERED | **-77.52%** | 1,093 sessions |
| | #2 | 2022-01-14 | 2022-02-03 | 2022-03-02 | -6.20% | 31 sessions |
| | #3 | 2022-03-11 | 2022-03-30 | 2022-04-01 | -2.32% | 14 sessions |
| **Strategy 2 (A)** | #1 | 2022-01-14 | 2026-09-03 | UNRECOVERED | **-78.34%** | 1,145 sessions |
| | #2 | 2022-01-04 | 2022-01-06 | 2022-01-07 | -0.24% | 3 sessions |
| | #3 | 2022-01-11 | 2022-01-12 | 2022-01-13 | -0.10% | 2 sessions |

---

## 8. Holdout Integrity & Governance Audit

1. **Exact Pre-Execution Checksums**:
   All 19 protected Phase 4–10 artifacts verified 100% byte-for-byte unmodified:
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
2. **Post-Execution Invariance**: All protected input files remain identical after Stage 2 execution.
3. **Absence of Holdout Leakage / Retraining**: No holdout observation was used for feature selection, model training, tree-count selection, calibration fitting, or threshold selection.
4. **Single-Pass Discipline**: Evaluated exactly once under frozen configurations.

---

## 9. Scientific Governance & Conclusions

### 9.1 Distinguishing Predictive from Economic Performance
- The negative economic performance of continuous intraday trading strategies does **not** imply that Model 1 lacks statistical predictive signal.
- In Phase 6 and Phase 10, Model 1 demonstrated out-of-sample directional accuracy and calibration on its target.
- However, when translated into a **cash-market intraday execution framework** (Open-to-Close daily round-trips), the strategy faces two structural headwinds:
  1. The underlying market structure of NIFTY 50 spot cash trading carries a negative intraday drift (the equity premium is earned overnight via gap returns, while intraday spot prices drift slightly downward on average).
  2. Paying 10 bps round-trip transaction costs every day accumulates 25.2% in annualized friction.
- Gating and filtering substantially reduce transaction costs and drawdown, but do not generate positive alpha over buy-and-hold.

### 9.2 Terminal Status
The Terminal Holdout (`2022-01-03` to `2026-09-03`, $N=1,154$) is now **FULLY CONSUMED**. No further evaluation, retuning, or optimization may be conducted on this dataset.
