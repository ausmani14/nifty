# NIFTY AI — PHASE 12 STEP 2
# FINAL FORENSIC RECONCILIATION, AUDIT & FORMAL SEAL
## Snapshot B 08:50 IST → Same-Day Open-to-Close Intraday Target

**Execution Date**: September 18, 2026  
**Auditor**: Lead Quantitative Researcher & Forensic Validation Agent  
**Audit Status**: COMPLETE & VERIFIED  
**Final Decision Gate**: **A) COMPLETE AND SEALED**  

---

## 1. Scope

Phase 12 Step 2 investigates whether the Snapshot B information set captured at 08:50 IST (25 minutes prior to the 09:15 IST NSE market open) contains statistically detectable linear predictive information regarding the subsequent same-day NIFTY Open-to-Close intraday return:
$$R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$$

This forensic audit reviews the implementation, artifacts, data dependencies, statistical integrity, causality, and mathematical calculations of Step 2.
The scope is strictly limited to development partition data (`2008-07-08` through `2021-12-31`, $N = 3,299$).

---

## 2. Holdout Firewall Proof

### Absolute Quarantine of Terminal Holdout
The Terminal Holdout (`2022-01-03` through `2026-09-03`, $N = 1,154$) was consumed in Phase 11 Stage 2 and remains permanently sealed.

### Programmatic Verification
1. **Target Artifact (`snapshot_b_intraday_target_dev.csv`)**:
   * Minimum Date: `2008-07-08`
   * Maximum Date: `2021-12-31`
   * Observations: Exactly $3,299$
   * Observations on or after `2022-01-03`: **EXACTLY 0**
2. **Diagnostics Artifact (`snapshot_b_intraday_diagnostics.csv`)**:
   * Minimum Date: `2014-01-02`
   * Maximum Date: `2021-12-31`
   * Observations: Exactly $1,960$
   * Observations on or after `2022-01-03`: **EXACTLY 0**
3. **Dependency Check**:
   * `scripts/phase12_snapshot_b_intraday_research.py` uses `WalkForwardSplitter(development_end_date=date(2021, 12, 31))` to explicitly slice only development indices (`dev_indices`).
   * No code path imports, reads, or processes any Phase 11 Stage 2 terminal holdout files (`phase11_stage2_*.csv`).
   * Zero holdout metrics influenced feature selection, target design, hyperparameter evaluation, or reporting.

---

## 3. Snapshot B Causality Audit

### Causal Timing Architecture
* **Feature Vector Cutoff**: 08:50 IST on Day $T+1$.
* **Domestic Market Open**: 09:15 IST on Day $T+1$.
* **Domestic Market Close**: 15:30 IST on Day $T+1$.

### Verification of Non-Leakage
Programmatic inspection of the feature matrix $X$ and the feature generator confirms that **NONE** of the following enter $X$:
* $\text{Open}(T+1)$: Unknown at 08:50 IST; excluded from $X$.
* $\text{High}(T+1)$: Unknown at 08:50 IST; excluded from $X$.
* $\text{Low}(T+1)$: Unknown at 08:50 IST; excluded from $X$.
* $\text{Close}(T+1)$: Unknown at 08:50 IST; excluded from $X$.
* Same-day $T+1$ return: Excluded from $X$.
* Future volume/order flow: Excluded from $X$.
* Future context readings: Excluded from $X$.

All 45 price features are derived exclusively from Day $T$ (market close at 15:30 IST yesterday) and earlier. All 18 context features represent Day $T$ close values for US/European markets and pre-market 08:50 IST readings for Asian indices.

---

## 4. Exact 63-Feature Architecture Reconciliation

### Alignment with Sealed Phase 4 Specification
Phase 4 sealed Model 1 with exactly 63 features: 45 Price + 18 Context. Phase 3 established that historical Yahoo volume was unreliable and excluded volume features.

### Reconciliation Table

| Category | Expected Count | Actual Count | Match Status | Volume / Flow Features | News Features |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Price Features** | 45 | 45 | **EXACT MATCH** | 0 | 0 |
| **Context Features** | 18 | 18 | **EXACT MATCH** | 0 | 0 |
| **Total Features** | **63** | **63** | **EXACT MATCH** | **0** | **0** |

* Volume-derived features in Model 1: **ZERO**.
* Flow-proxy features in Model 1: **ZERO**.
* News features in Model 1: **ZERO**.
* Semantic and byte-for-byte consistency with Phase 4: **CONFIRMED**.

---

## 5. Target Construction Audit

### Formulation
$$R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$$

### Numerical Identity Verification
The target values in `snapshot_b_intraday_target_dev.csv` were independently recomputed from raw daily NIFTY 50 OHLC data (`data/processed/nifty_50_daily.csv`):
* Maximum Absolute Difference: $0.00000000$ (machine epsilon).
* Directional Label: `'UP'` if $R > 0$, `'DOWN'` if $R < 0$, `'FLAT'` if $R = 0$.
* Integrity: Phase 5 and Phase 6 target files (`nifty50_targets_snapshot_a.csv`, `nifty50_targets_snapshot_b.csv`) remain byte-for-byte unmodified (verified via SHA-256).

---

## 6. Walk-Forward Validation Audit

### Expanding Window Structure ($N_{\text{OOF}} = 1,960$)

| Fold | Training Window | Validation Window | Train $N$ | Val $N$ | In-Sample Leakage | Shuffling |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 2008-07-08 to 2013-12-31 | 2014-01-02 to 2014-12-31 | 1,339 | 240 | None | None |
| **2** | 2008-07-08 to 2014-12-31 | 2015-01-02 to 2015-12-31 | 1,579 | 244 | None | None |
| **3** | 2008-07-08 to 2015-12-31 | 2016-01-04 to 2016-12-30 | 1,823 | 244 | None | None |
| **4** | 2008-07-08 to 2016-12-30 | 2017-01-02 to 2017-12-29 | 2,067 | 248 | None | None |
| **5** | 2008-07-08 to 2017-12-29 | 2018-01-02 to 2018-12-31 | 2,315 | 245 | None | None |
| **6** | 2008-07-08 to 2018-12-31 | 2019-01-02 to 2019-12-31 | 2,560 | 241 | None | None |
| **7** | 2008-07-08 to 2019-12-31 | 2020-01-02 to 2020-12-31 | 2,801 | 250 | None | None |
| **8** | 2008-07-08 to 2020-12-31 | 2021-01-04 to 2021-12-31 | 3,051 | 248 | None | None |

* Zero random splitting; zero shuffling.
* Training window expands strictly chronologically.
* No validation observation appears in its own training set.
* Each OOF prediction maps to exactly one validation session.

---

## 7. $N^*$ Selection Forensic Audit

### Outer Train $\to$ Inner Chronological Split Workflow
For each outer fold:
1. Outer training set ($X_{\text{tr}}, y_{\text{tr}}$) is partitioned chronologically:
   * Inner Validation Size: $n_{\text{val}} = \text{int}(n_{\text{total}} \times 0.20)$
   * Inner Training Size: $n_{\text{inner\_tr}} = n_{\text{total}} - n_{\text{val}}$ (first $80\%$)
   * Inner Validation: last $20\%$ of the outer training fold.
2. Evaluated $N \in [10, 15, 20, 25, 30, 35, 40, 45, 50, 60]$.
3. Selected $N^*$ minimizing RMSE on inner validation:
   * Fold 1: $N^* = 10$
   * Fold 2: $N^* = 60$
   * Fold 3: $N^* = 45$
   * Fold 4: $N^* = 60$
   * Fold 5: $N^* = 10$
   * Fold 6: $N^* = 10$
   * Fold 7: $N^* = 10$
   * Fold 8: $N^* = 40$
4. Retrained XGBoost on the FULL outer training set with selected $N^*$.
5. Evaluated out-of-fold on the outer validation set.

**Audit Result**: Independent programmatic reproduction confirmed identical $N^*$ values and identical out-of-fold predictions. Outer validation observations NEVER participated in $N^*$ selection.

---

## 8. Baseline Audit

### Verification of Benchmark Metrics ($N_{\text{OOF}} = 1,960$)

| Benchmark / Model | MAE | RMSE | Directional Hit Rate | Construction / Formula |
| :--- | :---: | :---: | :---: | :--- |
| **Model 1 (Intraday)** | **0.006094** | **0.008931** | **53.62%** | Walk-forward XGBoost Regressor |
| **Zero Forecast** | 0.006121 | 0.008971 | N/A | Constant $\widehat{y} = 0$ |
| **Historical Mean** | 0.006107 | 0.008946 | N/A | $\widehat{y} = \text{mean}(y_{\text{tr}})$ per fold (strictly causal) |
| **Always Short** | N/A | N/A | **53.93%** | Constant position $=-1$ |
| **Always Long** | N/A | N/A | **46.07%** | Constant position $=+1$ |

* The historical conditional mean was constructed causally using only the training fold observations. Zero full-sample leakage occurred.
* Model 1 achieves strictly lower MAE and RMSE than both the Zero forecast and Historical Mean baselines.

---

## 9. Statistical Verification

1. **Pearson IC**: $+0.0476$ ($p = 0.0350$, $t = 2.11$, $df = 1,958$).
   * Precision statement: *"A statistically detectable positive out-of-fold linear association was observed."*
   * This is an empirical association in historical data; it is not proof of live trading alpha.
2. **Spearman Rank IC**: $+0.0426$ ($p = 0.0593$, marginally significant at $\alpha = 0.10$).
3. **Diebold-Mariano Test**:
   * Loss function: Squared prediction error.
   * Null hypothesis: $\mathbb{E}[e_{\text{model}}^2] = \mathbb{E}[e_{\text{zero}}^2]$.
   * Test Statistic: $t = -3.11$ ($p = 0.00190$).
   * Explicit Note: The DM test evaluates point forecast accuracy, NOT trading profitability.

---

## 10. Directional Drift-Mimicry Audit

* Total OOF Sessions: $1,960$
* Model Predicted Long Sessions: $182$ ($9.29\%$)
* Model Predicted Short Sessions: $1,778$ ($90.71\%$)
* Model Directional Accuracy: **$53.62\%$** ($1,051 / 1,960$)
* Always-Short Baseline Accuracy: **$53.93\%$** ($1,057 / 1,960$)

### Quantitative Assessment
The model takes short positions on $90.71\%$ of sessions. Its directional hit rate does NOT outperform the naive Always-Short heuristic. The model has not demonstrated balanced two-sided classification skill; rather, its directional success is substantially driven by the negative historical intraday drift ($-14.01\%$ annualized).

---

## 11. Economic Diagnostic Verification

* Position rule: $\text{Position}(T+1) = \text{sign}(\widehat{R}_{\text{intraday}}(T+1)) \in \{+1, -1\}$.
* Execution: Enter at Open($T+1$), exit at Close($T+1$) ($252$ trades/year).
* Gross Annualized Return ($0$ bps): **$+18.25\%$** (Sharpe $+1.29$, Win Rate $53.62\%$, HAC $t = +3.95$, $p = 7.79 \times 10^{-5}$).
* Daily Mean Gross Return: $0.000724$ ($7.24$ bps/trade).
* **Breakeven Transaction Friction**: Exactly **$7.24$ bps/trade**.
* Net Annualized Return ($10$ bps): **$-6.95\%$** (Sharpe $-0.49$, Win Rate $47.24\%$, Max Drawdown $-53.55\%$, HAC $t = -1.50$, $p = 0.1326$).
* **Friction Drag Equation**: $252 \times 10\text{ bps} = 25.2\%$ annualized drag. Reconciles exactly: $18.25\% - 25.20\% = -6.95\%$.

---

## 12. Feature Importance & Phase 11 Comparison Caveats

1. **Feature Importance is Non-Causal**: Context features contributed $32.44\%$ of tree split importance. This indicates association with tree splits, not proof of invariant causality. Prohibited causal language ("vital transmission channel", "alpha source") has been purged.
2. **Phase 11 Comparison is Methodological Only**: Realignment to the Open-to-Close target resolves an objective function mismatch present in Phase 11. It does not prove that target realignment alone creates deployable alpha.

---

## 13. Artifact SHA-256 Checksum Table

| File Path | Size (Bytes) | Lines | SHA-256 Hash |
| :--- | :---: | :---: | :--- |
| `scripts/phase12_snapshot_b_intraday_research.py` | 18,947 | 451 | `63c819d52c8659b8ceb42be03d2d48e03799ba39cab6aa3b1837bba2c61792f4` |
| `data/interim/phase12/snapshot_b_intraday_target_dev.csv` | 225,391 | 3,300 | `ca8cbcb9fb45e86821aaaad09da67462fc7b2be373934c5ef180af4a8c08f8a0` |
| `data/interim/phase12/snapshot_b_intraday_oof_results.csv` | 1,918 | 5 | `2c9197be7c195551e5f5bada4abd2b92dcc3ab1cbf9c6823315a08c51a2de511` |
| `data/interim/phase12/snapshot_b_intraday_fold_results.csv` | 3,161 | 9 | `5ce0b96de6f3e47e37dbf6e5ed79aa2bfe363b6c1691a890764aaec0fd1108dc` |
| `data/interim/phase12/snapshot_b_intraday_diagnostics.csv` | 249,631 | 1,961 | `8fa2a9feffb097ff59782ba4baf7c86a7044fc646531bd3f3e1ffc9e245c6973` |
| `docs/PHASE_12_STEP_2_SNAPSHOT_B_INTRADAY_RESEARCH_REPORT.md` | 27,151 | 363 | `f545a5bc4ae50ac363399d72ff2d18803395ba1810dccf65f24ffafc0cd672b6` |
| `tests/test_phase12_snapshot_b_intraday.py` | 8,019 | 178 | `4f5eab2076c3e02889c8843e19dabe7c7be80e072d4e51bd1da68d860a64cdc9` |

All 19 protected Phase 4–10 baseline hashes remain identical to their sealed values in `configs/phase11_strategy_validation_config.json`.

---

## 14. Project Test Suite Results

* **Phase 12 Dedicated Suite** (`tests/test_phase12_snapshot_b_intraday.py`): **7/7 PASSED** in 2.08s.
* **Full Repository Regression Suite**: **228/228 PASSED** in 11.37s.
* Discrepancies, regressions, or broken contracts: **ZERO**.

---

## 15. Final Scientific Conclusion

Phase 12 Step 2 successfully resolved the target alignment question for Snapshot B:
1. When aligned with the Open-to-Close target, Snapshot B features demonstrate a statistically detectable linear predictive association ($IC = +0.0476, p = 0.0350$).
2. Point forecast error is strictly lower than zero and historical mean baselines ($DM\ t = -3.11, p = 0.0019$).
3. However, an unrestricted daily sign trading strategy cannot survive institutional execution costs ($7.24$ bps breakeven vs $10.0$ bps hurdle), suffering $-6.95\%$ net annual losses at 10 bps.
4. The directional hit rate is substantially driven by the negative historical intraday drift, rather than balanced two-sided classification skill.
5. The result is hypothesis-generating, validating target realignment while documenting that unconstrained daily turnover is economically unviable.

---

## 16. Formal Governance Statements

$$\mathbf{PHASE\ 12\ STEP\ 2\ IS\ FORMALLY\ SEALED.}$$

$$\mathbf{NO\ PHASE\ 12\ STEP\ 3\ EXECUTION\ IS\ AUTHORIZED\ BY\ THIS\ TASK.}$$

* The 2022–2026 Terminal Holdout remains completely untouched and quarantined.
* No live trading is justified or authorized.
* No new trading strategy, selective gating, or threshold optimization has been tested or deployed.

---
*Certified by Lead Quantitative Researcher & Forensic Validation Agent.*
