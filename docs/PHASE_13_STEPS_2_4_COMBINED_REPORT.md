# PHASE 13 — STEPS 2–4 COMBINED RESEARCH REPORT
## Holdout Exposure Audit, Frozen Snapshot B Evaluation & Economic Assessment

**Status**: STAGES A, B, AND C COMPLETE & SEALED (UNDER RETROSPECTIVE GOVERNANCE)  
**Date**: October 31, 2026  
**Auditor / Specialist**: Independent Quantitative Research Auditor, ML Validation Specialist & Financial Data Integrity Engineer  
**Pipeline**: Phase 13 Combined Execution (`scripts/run_phase13_steps2_4_evaluation.py`)  
**Holdout Exposure Classification**: **`PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA`**  
**Evidentiary Standing**: **STRICTLY RETROSPECTIVE OUT-OF-SAMPLE EVALUATION (NOT AN UNTOUCHED CONFIRMATORY HOLDOUT)**  
**Repository Test Suite**: **490 / 490 PASSED**  

---

## 1. Executive Summary & Governance Verdict

This combined report delivers the definitive forensic evaluation of Phase 13 Steps 2–4, investigating the historical exposure of the post-2022 dataset, executing the single-pass evaluation of the frozen Snapshot B $T0$ production model, and assessing the economic viability of intraday trading strategies under pre-registered transaction frictions.

```
========================================================================================
PHASE 13 STEPS 2–4 GATE DECISIONS:
- STAGE A (Exposure Audit): COMPLETE & SEALED -> PREVIOUSLY EXPOSED RETROSPECTIVE DATA
- STAGE B (Model Evaluation): COMPLETE & SEALED -> OUTCOME B: WEAK OR ABSENT (p = 0.4945 >= 0.05)
- STAGE C (Economic Assessment): COMPLETE & SEALED -> NEGATIVE AFTER COSTS (-13.96% at 10 bps)
========================================================================================
```

### Core Scientific Findings

1. **Prior Exposure Audit (Stage A)**:
   - The $2022-01-03$ to $2026-09-03$ partition ($N=1,154$ sessions) was **extensively loaded, evaluated, and consumed on September 18, 2026** during Phase 9 Step 4, Phase 10, and Phase 11 Stage 2.
   - Most crucially, Phase 11 Stage 2's terminal holdout evaluation documented an annualized net loss of **-27.17%** for Strategy 1 under Open-to-Close execution. **This empirical breakdown was the direct, formative impetus for Phase 12 (Target Redesign).**
   - The label "Untouched Terminal Holdout" applied in Phase 13 Step 1 was historically inaccurate. The period is formally reclassified as **`PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA`**.
   - Because the dedicated Snapshot B $T0$ model ($N^*=43$ trees, 63 features) was frozen prior to Phase 13 and never evaluated on 2022+, an evaluation on this partition is authorized strictly as a **retrospective out-of-sample diagnostic**.

2. **Frozen Model Performance (Stage B)**:
   - Evaluated on $N=1,154$ retrospective sessions ($2022-01-03$ to $2026-09-03$), the Primary Full Development Production Model ($N=3,299, N^*=43$ trees) achieves:
     - **Pearson IC**: **$+0.02013$ ($p = 0.4945$, two-sided; $p = 0.2472$, one-sided)**. The correlation is not statistically significant at conventional levels ($\alpha = 0.05$).
     - **Spearman IC**: **$+0.00424$ ($p = 0.8856$)**.
     - **MAE**: **$50.42$ bps** (compared to $50.47$ bps for the reported zero-return benchmark, an improvement of only $0.05$ bps; under exact array recomputation, zero-return MAE is $50.30$ bps, against which the model is $0.13$ bps higher).
     - **RMSE**: **$67.78$ bps** (worse than the zero-return benchmark RMSE of $67.65$ bps reported, and worse than the exact recomputed RMSE of $67.69$ bps).
     - **Mean Directional Accuracy (MDA)**: **$52.43\%$** (compared to $51.91\%$ for Always Short, representing an incremental difference of only 6 net sessions out of 1,154).
     - **Incremental $R^2$**: **$-0.003574$** (relative to the historical development training mean $\mu_{\text{train}} = -0.0556\%$).
   - Under the pre-registered decision criteria, this result falls squarely into:
     $$\mathbf{OUTCOME\ B:\ WEAK\ OR\ ABSENT\ (p \ge 0.05)}$$
   - *Mandatory Statement*: **"The Snapshot B intraday predictive relationship fails to reject the null hypothesis of zero or negative correlation on the retrospective evaluation partition."**
   - *Epistemic Note*: A nonsignificant statistical test indicates the absence of evidence for a robust relationship; it does not constitute mathematical proof that the true latent association is identically zero.
   - Secondary diagnostic models independently corroborate the absence of signal:
     - **Fold 8 Model ($N^*=40$)**: Pearson IC = $+0.00119$ ($p = 0.9678$).
     - **8-Fold Uniform Ensemble**: Pearson IC = $-0.01742$ ($p = 0.5545$).

3. **Economic Diagnostics (Stage C)**:
   - Model predictions are negative on **$96.88\%$ of sessions** ($1,118$ short vs $36$ long), primarily reflecting the unconditional historical negative drift of Indian spot cash during daytime trading hours rather than demonstrated directional predictive skill.
   - At 0 bps frictionless, Strategy 1 achieves $+10.70\%$ annualized return (Sharpe 1.001) vs $+7.48\%$ (Sharpe 0.726) for the Always Short Benchmark.
   - Under realistic market frictions, continuous daily turnover leads to substantial net losses and severe drawdowns:
     - **5 bps friction**: Net annualized return declines to **$-2.40\%$** (Sharpe $-0.173$, Max DD $-21.72\%$).
     - **10 bps friction (Baseline)**: Net annualized return declines to **$-13.96\%$** (Sharpe $-1.348$, Max DD **$-54.05\%$**).
     - **20 bps friction (Stress)**: Net annualized return declines to **$-33.15\%$** (Sharpe $-3.697$, Max DD **$-84.78\%$**).
   - The strategy demonstrates **no reliable predictive power or commercial trading viability**.

---

## 2. Historical Holdout-Exposure Forensic Audit (Stage A)

### Evidence Matrix Across Research Lifecycle

| Activity ID | Phase & Date | Activity Description | Target Values Read? | Predictions Generated? | Metrics Calculated? | Influenced Decisions? | Historical Classification |
|---|---|---|---|---|---|---|---|
| **ACT_01** | Phase 5<br>(2026-09-14) | Dataset-wide target generation (`data/targets/nifty50_targets_snapshot_b.csv`) | YES (Close-to-Close $T1$ target generated through 2026-09-04) | NO | NO | Established initial target files | **CONFIRMED EXPOSED** |
| **ACT_02** | Phase 9 Step 4<br>(2026-09-18) | Incremental News evaluation (`data/interim/news/phase9_step4_holdout_results.csv`) | YES ($N=1,154$ sessions $y_{\text{true}}$) | YES (Models 0, 1, 2, 3 and 6 ablations) | YES (LogLoss, IC, Accuracy, DM tests) | **Direct**: Sealed exclusion of News; locked Model 1 (0 News) | **CONFIRMED EXPOSED** |
| **ACT_03** | Phase 10<br>(2026-09-18) | Regime explainability (`data/interim/regime/phase10_holdout_diagnostics.csv`) | YES ($N=1,154$ sessions $y_{\text{true}}$) | YES (Model 1 predictions and cal probabilities) | YES (RMSE, IC, ECE across vol regimes) | **Direct**: Confirmed Low-Vol stability out-of-sample | **CONFIRMED EXPOSED** |
| **ACT_04** | Phase 11 Stage 2<br>(2026-09-18) | Strategy validation (`data/interim/strategy/phase11_stage2_strategy_results.csv`) | YES (Realized trade returns for $N=1,154$) | YES (Strategies 1–5 trade positions) | YES (Ann Return, Sharpe, Drawdown at 0–20 bps) | **FORMATIVE**: Strategy 1 failed at -27.17% net; directly triggered Phase 12 Target Redesign! | **CONFIRMED EXPOSED** |
| **ACT_05** | Phase 12 Steps 1–12<br>(Sept 2026) | Target Redesign & Intraday Research (`data/interim/phase12/`) | NO (Strictly quarantined to $\le 2021-12-31$) | NO (Only OOF $N=1,960$ predictions) | NO (Zero holdout metrics computed) | Developed $T0$ target and established weak OOF IC (+0.0476) | **CONFIRMED NOT EXPOSED** (Within Phase 12 scope) |
| **ACT_06** | Phase 13 Step 1<br>(2026-10-31) | Untouched Holdout Protocol Freeze (`data/interim/phase13_step1/`) | NO (Zero holdout rows accessed) | NO | NO | Locked protocol, but mischaracterized 2022+ as 'untouched' | **CONFIRMED NOT EXPOSED** (Within Step 1 scope) |

### Forensic Resolution & Reclassification

The empirical facts prove that the 2022+ partition was **not** untouched prior to Phase 13:
- It was consumed and reported in Phase 11 Stage 2 (`docs/PHASE_11_STAGE_2_TERMINAL_HOLDOUT_REPORT.md`: *"STAGE 2 TERMINAL HOLDOUT EVALUATION COMPLETE — TERMINAL HOLDOUT CONSUMED"*).
- The knowledge of its failure under Open-to-Close trading shaped the conceptual design of Phase 12.
- Therefore, the dataset must never be presented as an unexposed prospective validation set.
- Formal Reclassification: **`PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA`**.

---

## 3. Model Identity, Feature Space & Training Boundary Verification (Stage B)

### Model Specification

| Parameter | Frozen Requirement | Audited Value | Status |
|---|---|---|:---:|
| **Architecture** | `xgboost.XGBRegressor` | `xgboost.XGBRegressor` | **VERIFIED** |
| **Training Partition** | `2008-07-08` to `2021-12-31` | $N=3,299$ sessions strictly $\le 2021-12-31$ | **VERIFIED** |
| **Training Cutoff** | Max Date $\le 2021-12-31$ | `2021-12-31` (0 holdout observations used) | **VERIFIED** |
| **Tree Count ($N^*$)** | Exactly 43 trees | 43 trees | **VERIFIED** |
| **Learning Rate ($\eta$)** | 0.05 | 0.05 | **VERIFIED** |
| **Max Depth** | 2 | 2 | **VERIFIED** |
| **Min Child Weight** | 20.0 | 20.0 | **VERIFIED** |
| **Subsample** | 0.8 | 0.8 | **VERIFIED** |
| **Colsample By Tree** | 0.7 | 0.7 | **VERIFIED** |
| **Reg Alpha** | 0.5 | 0.5 | **VERIFIED** |
| **Reg Lambda** | 2.0 | 2.0 | **VERIFIED** |
| **Random State** | 42 | 42 | **VERIFIED** |
| **Features Count** | Exactly 63 features | 63 features (45 Price + 18 Context) | **VERIFIED** |
| **News Features** | Strictly 0 | 0 included | **VERIFIED** |
| **Volume / Flow Features** | Strictly 0 | 0 included | **VERIFIED** |
| **Serialized Model** | `models/snapshot_b_t0_primary_model.json` | Hash: `981bbc806160090e339093686c61b660368427860451d9720824720dd031c5df` | **VERIFIED** |

---

## 4. Retrospective Model Evaluation Results (Stage B)

### Primary Model ($N=3,299, N^*=43$) vs Secondary Diagnostic Models

| Model Identity | Evaluation Scope | Pearson IC ($r_p$) | Two-Sided $p$-value | One-Sided $p$-value | Spearman IC ($r_s$) | Spearman $p$-value | Outcome Decision |
|---|---|---|---|---|---|---|---|
| **Primary Production Model** | Full Dev ($N^*=43$) | **+0.02013** | **0.4945** | **0.2472** | **+0.00424** | **0.8856** | **OUTCOME B (Weak / Absent)** |
| **Secondary Diagnostic 1** | Fold 8 Model ($N^*=40$) | **+0.00119** | **0.9678** | **0.4839** | **-0.00767** | **0.7942** | **OUTCOME B (Weak / Absent)** |
| **Secondary Diagnostic 2** | 8-Fold Uniform Ensemble | **-0.01742** | **0.5545** | **0.7228** | **-0.02381** | **0.4187** | **OUTCOME B (Weak / Absent)** |

### Error Metrics & Fixed Benchmark Comparisons

| Predictor / Model | Target | MAE (bps) | RMSE (bps) | Incremental $R^2$ vs Training Mean | Hit Rate (MDA) |
|---|---|---|---|---|---|
| **Primary Model ($N^*=43$)** | $T0$ Return | **50.42** | **67.78** | **-0.003574** | **52.43%** |
| **Benchmark 1: Zero Return ($\hat{y} \equiv 0$) (Reported)** | $T0$ Return | 50.47 | 67.65 | -0.000000 | N/A |
| **Benchmark 1: Zero Return ($\hat{y} \equiv 0$) (Exact Recomputed)** | $T0$ Return | 50.30 | 67.69 | -0.002811 | N/A |
| **Benchmark 2: Historical Mean ($\hat{y} \equiv \mu_{\text{train}}$)** | $T0$ Return | 50.28 | 67.66 | 0.000000 (Baseline) | N/A |
| **Benchmark 3: Always Short ($\text{pos} \equiv -1.0$)** | $T0$ Return | N/A | N/A | N/A | 51.91% |

### Statistical Takeaway
The primary model's Pearson correlation ($r_p = +0.0201, p = 0.4945$) is not statistically significant at conventional levels. The model's MAE improvement over the reported zero-return benchmark is only $0.05$ bps (and against exact array zero MAE, the model is $0.13$ bps higher), while its RMSE is strictly worse ($67.78$ bps vs $67.69$ bps). Furthermore, the incremental $R^2$ is negative ($-0.36\%$), indicating that the model does not explain return variance beyond the unconditional historical training mean $\mu_{\text{train}} = -0.0556\%$.

---

## 5. Frozen Economic Assessment (Stage C)

### Strategy 1 (Unrestricted Directional Intraday Trading)

- **Entry**: 09:15 IST Open on Session $T+1$
- **Exit**: 15:30 IST Close on Session $T+1$
- **Position Rule**: $+1.0$ if $\hat{y} > 0$; $-1.0$ if $\hat{y} < 0$; $0.0$ if $\hat{y} == 0$.
- **Position Breakdown**: Long = 36 sessions ($3.12\%$), Short = 1,118 sessions ($96.88\%$), Flat = 0 sessions ($0.00\%$).

### Performance Across Cost Scenarios ($N=1,154$ Sessions)

| Strategy | Cost Scenario | Cumulative Return | Annualized Return | Annualized Volatility | Sharpe Ratio | Maximum Drawdown | Win Rate | Profit Factor |
|---|---|---|---|---|---|---|---|---|
| **Strategy 1** | **0 bps (Gross)** | **+59.28%** | **+10.70%** | **10.68%** | **1.001** | **-13.18%** | **52.43%** | **1.22** |
| | **5 bps Round-Trip** | **-10.55%** | **-2.40%** | **10.68%** | **-0.173** | **-21.72%** | **48.70%** | **0.96** |
| | **10 bps (Baseline)** | **-49.78%** | **-13.96%** | **10.68%** | **-1.348** | **-54.05%** | **44.97%** | **0.78** |
| | **20 bps (Stress)** | **-84.18%** | **-33.15%** | **10.68%** | **-3.697** | **-84.78%** | **37.61%** | **0.53** |
| **Always Short** | **0 bps (Gross)** | +39.17% | +7.48% | 10.74% | 0.726 | -12.07% | 51.56% | 1.15 |
| | **5 bps Round-Trip** | -21.84% | -5.24% | 10.74% | -0.448 | -25.59% | 47.75% | 0.91 |
| | **10 bps (Baseline)** | -56.12% | -16.46% | 10.74% | -1.621 | -57.14% | 44.02% | 0.73 |
| | **20 bps (Stress)** | -86.18% | -35.09% | 10.74% | -3.968 | -86.13% | 36.83% | 0.50 |

### Economic Conclusion
1. **Transaction Cost Drag**: At 10 bps round-trip friction, daily turnover across 1,154 sessions incurs a substantial penalty, resulting in an annualized net loss of **$-13.96\%$** and a maximum drawdown of **$-54.05\%$**. At 20 bps, the loss widens to **$-33.15\%$ annualized** with an **$-84.78\%$ drawdown**.
2. **Gross Drift Confounding**: Strategy 1 is short $96.88\%$ of the time. The frictionless gross return ($+10.70\%$) is largely driven by the structural negative drift of Indian cash markets during daytime hours ($+7.48\%$ gross for Always Short). The model's incremental active return ($+3.22\%$ annualized gross) is statistically non-significant ($p = 0.494$) and is eliminated once trading costs are incorporated.
3. **No Commercial Trading Viability**: These results confirm that unconstrained daily trading on Snapshot B intraday return predictions cannot overcome execution frictions in cash index markets.

---

## 6. Cryptographic Integrity Manifest

All Phase 13 Steps 2–4 output artifacts have been serialized to `data/interim/phase13_steps2_4/` and verified with bit-for-bit SHA256 hashes:

| Artifact Path | SHA256 Checksum | Description |
|---|---|---|
| `step2_holdout_exposure_audit.json` | `3ae7668bac47d76b54660ae66ffa63880bd7210ec9a91398c820881486216097` | Exposure audit metadata and gate classification |
| `step2_holdout_exposure_evidence.csv` | `d6b2b8963ea2220d93019279c713f532ec66011a60f643a1ecf99e0ba04420c9` | Cross-phase historical exposure evidence matrix |
| `step2_holdout_exposure_report.md` | `fd8dce77d05255da24189400b535234f7a2a06b51098a4b01c8982dedd66ad7d` | Forensic report on historical holdout exposure |
| `step3_retrospective_model_evaluation.json` | `e8103726125a7970cdc147ab1baf0b2403ccaf53c41169a921f1e10a0c6d5aba` | Complete Stage B model evaluation metrics & diagnostics |
| `step3_retrospective_model_predictions.csv` | `2593c2cbe98f145788903660329f4a2315a6b1fe9502f2a948bdeb8895550e0e` | Session-by-session predictions across 1,154 sessions |
| `step3_retrospective_evaluation_summary.csv` | `95b9adff3a7099fcc00d15d4107d38c304fdf00cfbabfa7d6b425aaa1b01e267` | Tabular summary of primary, secondary, and benchmark metrics |
| `step4_economic_assessment.csv` | `c4f97175d7f61cbdf1a11a7d64b2d7e5e5a3eb3e418e88500dc6187ee85b99ba` | Strategy 1 & Always Short economic performance across costs |
| `step4_economic_assessment.json` | `f38d9efb01b17df58ff3879559172c120d2199e0571fb47eee49864809023f0e` | JSON summary of economic diagnostics |
| `step4_equity_curves.csv` | `1f63e6363594e8da85c8e8a3de9601650094e482fed74059dee9a5b5db6dae79` | Daily equity curves for all strategies and cost scenarios |
| `models/snapshot_b_t0_primary_model.json` | `981bbc806160090e339093686c61b660368427860451d9720824720dd031c5df` | Serialized primary XGBoost production regressor model |
| `models/snapshot_b_t0_primary_model.meta.json` | `651dc290cd3ffc22e65a759bda190f7de4c533d8ed9f0fd67b51e36fda592bac` | Model metadata, feature list, hyperparameters & hash |
| `phase13_steps2_4_manifest.json` | `88c6bb94c1c91cff356fc8f39fc734d57c2bc35fc20fec098bb37e721fc002ea` | Integrity manifest recording all 11 artifact checksums |

---

## 7. Regression Test Suite & Verification

- Dedicated Test Suite: [`tests/test_phase13_steps2_4_evaluation.py`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/tests/test_phase13_steps2_4_evaluation.py) (**17 / 17 passed**).
- Dedicated Audit Suite: [`tests/test_phase13_steps2_4_final_audit.py`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/tests/test_phase13_steps2_4_final_audit.py) (**10 / 10 passed**).
- Full Repository Test Suite Pass: **490 / 490 passed** with zero regressions.
- All Phase 0–12 sealed artifacts verified bit-for-bit unchanged.
- All Phase 13 Step 1 protocol artifacts verified bit-for-bit unchanged.

---

## 8. Limitations & Epistemic Boundaries

1. **Retrospective Nature**: All results reported herein are derived from historical data that was previously accessed during Phase 9–11. They represent retrospective out-of-sample evidence, not prospective forward confirmation.
2. **Drift Confounding**: Intraday returns in Indian equities exhibit structural negative drift during regular market hours, which biases unconstrained models toward persistent short positions.
3. **Execution Frictions**: In spot index markets, transaction costs, taxes (STT), and bid-ask spread impose severe friction penalties on daily turnover that easily exceed the marginal statistical predictive signal.

---

## 9. Final Governance Statement

- **Stages Completed**: Stage A (Exposure Audit), Stage B (Model Evaluation), Stage C (Economic Assessment), Stage D (Integrity Tests), Stage E (Final Report).
- **Stages Blocked**: NONE.
- **Prior Holdout Exposure Status**: **CONFIRMED PREVIOUSLY EXPOSED**.
- **New Metrics Computed**: Retrospective Pearson IC, Spearman IC, MAE, RMSE, MDA, Residual ICs, Incremental $R^2$, and 0–20 bps economic diagnostics for $T0$.
- **Protected Artifact Modifications**: **ZERO**. All Phase 0–12 artifacts and Phase 13 Step 1 protocol artifacts remain bit-for-bit identical to their sealed baselines.
- **Next Authorized Action**: No further actions are authorized within this task. Await explicit user authorization before considering any subsequent research activity or project conclusion.
