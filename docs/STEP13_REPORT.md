# PHASE 13 MASTER RESEARCH REPORT
## Steps 1–5: Protocol Freeze, Exposure Audit, Retrospective Evaluation, Economic Assessment & Decision Gate

**Role**: Independent Quantitative Research Auditor, ML Validation Specialist & Financial Data Integrity Engineer  
**Phase Status**: PHASE 13 STEPS 1–5 FORMALLY COMPLETED & SEALED  
**Holdout Exposure Status**: **`PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA`**  
**Evidentiary Standing**: **STRICTLY RETROSPECTIVE OUT-OF-SAMPLE EVALUATION (NOT AN UNTOUCHED CONFIRMATORY HOLDOUT)**  
**Repository Test Suite**: **496 / 496 PASSED**  

---

## 1. Executive Summary & Progression of Findings

Phase 13 conducts the out-of-sample evaluation of the frozen Snapshot B $T0$ predictive architecture on the post-2022 dataset ($2022-01-03$ to $2026-09-03$, $N=1,154$ sessions).

### Key Empirical Verdicts

1. **Step 1 (Protocol Freeze)**:
   - Evaluated Option A (Frozen Historical Models) vs Option B (Walk-Forward Retraining).
   - Option A locked: model trained strictly on data $\le 2021-12-31$ ($N=3,299$), with zero holdout retraining, to prevent prospective hyperparameter contamination.
   - Primary target strictly frozen to Snapshot B $T0$ (Open-to-Close return). Feature space locked to 63 features (45 Price + 18 Context, 0 News, 0 Volume, 0 Flow).

2. **Step 2 (Historical Exposure Audit - Stage A)**:
   - A rigorous forensic audit of repository logs, interim data, and historical reports revealed that the post-2022 partition was **not** untouched.
   - The partition was loaded and evaluated on September 18, 2026 in Phase 9 Step 4 (News evaluation), Phase 10 (Regime diagnostics), and Phase 11 Stage 2 (Strategy evaluation).
   - In Phase 11 Stage 2, Strategy 1 incurred a -27.17% net loss on the 2022+ partition under Open-to-Close trading. This catastrophic failure was the direct, formative cause of Phase 12 (Target Redesign).
   - The partition is formally reclassified as **`PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA`**.
   - An evaluation of the dedicated $T0$ model ($N^*=43$ trees) was authorized strictly as a **retrospective out-of-sample diagnostic**.

3. **Step 3 (Frozen Snapshot B T0 Evaluation - Stage B)**:
   - Primary Full Development Model ($N=3,299, N^*=43$ trees) achieves:
     - **Pearson IC**: **$+0.02013$ ($p = 0.4945$, non-significant)**.
     - **Spearman IC**: **$+0.00424$ ($p = 0.8856$, non-significant)**.
     - **MAE**: **$50.42$ bps**; **RMSE**: **$67.78$ bps**.
     - **Directional Accuracy (MDA)**: **$52.43\%$**.
     - **Incremental $R^2$**: **$-0.003574$** (worse variance explanation than static historical training mean).
   - Pre-registered Outcome Classification:
     $$\mathbf{OUTCOME\ B:\ WEAK\ OR\ ABSENT\ (p \ge 0.05)}$$
   - *Mandatory Statement*: **"The Snapshot B intraday predictive relationship fails to reject the null hypothesis of zero or negative correlation on the retrospective evaluation partition."**
   - Secondary models confirm: Fold 8 Model ($r_p = +0.00119, p = 0.9678$), 8-Fold Ensemble ($r_p = -0.01742, p = 0.5545$).

4. **Step 4 (Frozen Economic Assessment - Stage C)**:
   - The model predicts negative return on **$96.88\%$ of sessions** ($1,118$ short vs $36$ long), capturing the unconditional negative intraday drift of Indian spot cash.
   - At 0 bps frictionless, Strategy 1 achieves $+10.70\%$ annualized return (Sharpe 1.001) vs $+7.48\%$ (Sharpe 0.726) for Always Short.
   - Under transaction frictions, the strategy suffers extreme capital destruction:
     - **5 bps friction**: $-2.40\%$ annualized net return (Sharpe $-0.173$, Max DD $-21.72\%$).
     - **10 bps friction (Baseline)**: **$-13.96\%$ annualized net return** (Sharpe **$-1.348$**, Max DD **$-54.05\%$**).
     - **20 bps friction (Stress)**: **$-33.15\%$ annualized net return** (Sharpe **$-3.697$**, Max DD **$-84.78\%$**).
   - Strategy 1 provides **zero commercial trading viability**.

5. **Step 5 (Model Promotion Decision Gate & Research Disposition)**:
   - Formally audited the frozen Snapshot B $T0$ production model ($N=3,299, N^*=43$ trees) across all 8 pre-registered promotion criteria.
   - Criteria Summary: 0/6 performance/economic criteria met; historical exposure confirmed (retrospective only); model disposition resolved.
   - Final Classification: **`RESEARCH BASELINE ONLY`**.
   - Production Promotion: **STRICTLY REJECTED**.
   - Discard / Complete Retirement: **REJECTED** (preserves pipeline reproducibility and benchmark value).
   - Real-money trading: **STRICTLY INELIGIBLE**.

---

## 2. Comprehensive Metric & Benchmark Summary Table

| Metric / Specification | Primary Model ($N^*=43$) | Fold 8 Model ($N^*=40$) | 8-Fold Uniform Ensemble | Benchmark 1 (Zero Return) | Benchmark 2 (Training Mean) | Benchmark 3 (Always Short) |
|---|---|---|---|---|---|---|
| **Pearson IC ($r_p$)** | **+0.02013** | +0.00119 | -0.01742 | N/A | N/A | N/A |
| **Pearson $p$-value (2-sided)** | **0.4945** | 0.9678 | 0.5545 | N/A | N/A | N/A |
| **Spearman IC ($r_s$)** | **+0.00424** | -0.00767 | -0.02381 | N/A | N/A | N/A |
| **MAE (bps)** | **50.42** | 50.44 | 50.46 | 50.47 | 50.48 | N/A |
| **RMSE (bps)** | **67.78** | 67.82 | 67.80 | 67.65 | 67.66 | N/A |
| **Incremental $R^2$** | **-0.003574** | -0.004755 | -0.004163 | 0.000000 | Baseline (0.0) | N/A |
| **Directional Hit Rate** | **52.43%** | 52.08% | 51.39% | N/A | N/A | 51.56% |
| **Ann Net Ret (0 bps)** | **+10.70%** | +9.12% | +8.45% | 0.00% | 0.00% | +7.48% |
| **Ann Net Ret (5 bps)** | **-2.40%** | -3.81% | -4.41% | 0.00% | 0.00% | -5.24% |
| **Ann Net Ret (10 bps)** | **-13.96%** | -15.19% | -15.72% | 0.00% | 0.00% | -16.46% |
| **Sharpe Ratio (10 bps)** | **-1.348** | -1.482 | -1.543 | 0.000 | 0.000 | -1.621 |
| **Max Drawdown (10 bps)** | **-54.05%** | -55.82% | -56.31% | 0.00% | 0.00% | -57.14% |

---

## 3. Cryptographic Manifest (Phase 13 Steps 1–4)

All Phase 13 artifacts are sealed and cryptographically verified:

```json
{
  "step1_holdout_protocol.json": "21e5b9b001f16e2acc003b78e6af78e2c8cdb1ebc44f389c18c0d1957e689395",
  "step1_holdout_protocol.md": "3c64b2355b09b5e4ab85d838c0080a380d91f80c2831f4449c83dd011422f03a",
  "step1_holdout_firewall_audit.json": "6704e275d9c66fd50c2bc964509cbacc76212e9b2cea06f9dad5fb2375625188",
  "step2_holdout_exposure_audit.json": "3ae7668bac47d76b54660ae66ffa63880bd7210ec9a91398c820881486216097",
  "step2_holdout_exposure_evidence.csv": "d6b2b8963ea2220d93019279c713f532ec66011a60f643a1ecf99e0ba04420c9",
  "step2_holdout_exposure_report.md": "fd8dce77d05255da24189400b535234f7a2a06b51098a4b01c8982dedd66ad7d",
  "step3_retrospective_model_evaluation.json": "e8103726125a7970cdc147ab1baf0b2403ccaf53c41169a921f1e10a0c6d5aba",
  "step3_retrospective_model_predictions.csv": "2593c2cbe98f145788903660329f4a2315a6b1fe9502f2a948bdeb8895550e0e",
  "step3_retrospective_evaluation_summary.csv": "95b9adff3a7099fcc00d15d4107d38c304fdf00cfbabfa7d6b425aaa1b01e267",
  "step4_economic_assessment.csv": "c4f97175d7f61cbdf1a11a7d64b2d7e5e5a3eb3e418e88500dc6187ee85b99ba",
  "step4_economic_assessment.json": "f38d9efb01b17df58ff3879559172c120d2199e0571fb47eee49864809023f0e",
  "step4_equity_curves.csv": "1f63e6363594e8da85c8e8a3de9601650094e482fed74059dee9a5b5db6dae79",
  "models/snapshot_b_t0_primary_model.json": "981bbc806160090e339093686c61b660368427860451d9720824720dd031c5df",
  "models/snapshot_b_t0_primary_model.meta.json": "651dc290cd3ffc22e65a759bda190f7de4c533d8ed9f0fd67b51e36fda592bac"
}
```

---

## 4. Phase 13 Step 5 Model Promotion Decision & Governance Manifest

```json
{
  "docs/PHASE_13_STEP5_MODEL_PROMOTION_DECISION.md": "66d30e0ff0fa3906d463634a7d0bfd9ba5c202bc05a27a8c41a3c49a55ac632c",
  "data/interim/phase13_step5/phase13_step5_decision.json": "2bf0d8eca553580a4fe2e0a12896ad7d92707bed1e01ef50b1881fe4bf0506ff"
}
```

---

## 5. Governance & Final Disposition Status

- **Completed Stages**: Steps 1, 2, 3, 4, 5.
- **Sealed Outcome**: OUTCOME B (Weak or Absent) / NEGATIVE AFTER COSTS.
- **Model Promotion Verdict**: **RESEARCH BASELINE ONLY** (Production promotion strictly rejected; live real-money trading strictly unauthorized).
- **Evaluation Partition Classification**: **`PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA`**.
- **Next Action**: Await explicit instructions from project governance. Phase 14 and all subsequent phases remain strictly unauthorized until prospective shadow-trading protocols are commissioned.
