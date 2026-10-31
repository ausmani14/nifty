# Stage A: Historical Holdout-Exposure Forensic Audit Report

**Date**: 2026-10-31  
**Auditor**: Senior Quantitative ML Research Auditor & Data Integrity Specialist  
**Classification**: **`PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA`**  
**Gate Verdict**: **CONDITIONALLY AUTHORIZED FOR RETROSPECTIVE EVALUATION ONLY**  

---

## 1. Executive Summary & Root Cause Reconstruction

A forensic examination of repository commit histories, documentation, interim datasets, and execution configs confirms an irreconcilable conflict between the Phase 13 Step 1 framing and historical research records:

1. **Phase 13 Step 1 Framing**: Described the `2022-01-03` through `2026-09-03` partition ($N=1,154$ sessions) as an **"Untouched Terminal Holdout"**.
2. **Historical Reality**: The `2022-01-03` through `2026-09-03` partition was **extensively loaded, evaluated, and consumed on September 18, 2026** during Phase 9 Step 4, Phase 10, and Phase 11 Stage 2.
3. **Formative Influence**: Most critically, Phase 11 Stage 2's terminal holdout evaluation documented an annualized net loss of **-27.17%** for Strategy 1 under Open-to-Close execution. This empirical breakdown directly caused the formulation of Phase 12 (*"Phase 12 — Overnight / Intraday Return Decomposition & Target Redesign"*).

Therefore, calling the 2022+ dataset "untouched" or "confirmatory" is mathematically and epistemically false.

---

## 2. Evidence Inventory Table

| Activity ID | Phase | Date | Target Values Read? | Predictions Generated? | Metrics Calculated? | Influenced Decisions? | Classification |
|---|---|---|---|---|---|---|---|
| **ACT_01** | Phase 5 | 2026-09-14 | YES (T1) | NO | NO | Base targets | CONFIRMED EXPOSED |
| **ACT_02** | Phase 9 Step 4 | 2026-09-18 | YES (T1) | YES (M0-M3) | YES (LogLoss, IC) | Locked Model 1 (0 News) | CONFIRMED EXPOSED |
| **ACT_03** | Phase 10 | 2026-09-18 | YES (T1) | YES (M1) | YES (RMSE, Regimes) | Shaped Low-Vol filter | CONFIRMED EXPOSED |
| **ACT_04** | Phase 11 Stage 2 | 2026-09-18 | YES (T0 & T1) | YES (Strategies 1-5)| YES (Ret, Sharpe, DD) | **Direct cause of Phase 12** | CONFIRMED EXPOSED |
| **ACT_05** | Phase 12 Steps 1-12 | Sept 2026 | NO (Quarantined) | NO (Quarantined) | NO (Quarantined) | Developed T0 target | CONFIRMED NOT EXPOSED |
| **ACT_06** | Phase 13 Step 1 | Oct 2026 | NO (Quarantined) | NO (Quarantined) | NO (Quarantined) | Froze protocol | CONFIRMED NOT EXPOSED |

---

## 3. Decision Gate Resolution

- **Confirmatory Holdout Claim**: **REJECTED**. The 2022+ dataset cannot serve as an independent confirmatory holdout.
- **Retrospective Evaluation Authorization**: **APPROVED UNDER STRICT CONSTRAINTS**.
  - A model trained specifically on $T0$ (Snapshot B Open-to-Close return) has never been evaluated on the 2022+ period.
  - The model specification was frozen in Phase 12 Step 2 / Phase 13 Step 1 ($N^*=43$ trees, 63 features, `xgboost.XGBRegressor`).
  - Evaluating this frozen model on 2022+ provides a legitimate **retrospective out-of-sample diagnostic**, provided it is never represented as prospective proof or untouched validation.
