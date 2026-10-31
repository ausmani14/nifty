# NIFTY AI — PHASE 12 STEP 3
# FINAL FORENSIC RECONCILIATION, AUDIT & FORMAL SEAL
## Selective Trading & Turnover-Control Research (Snapshot B 08:50 IST)

**Execution Date**: September 18, 2026  
**Auditor**: Lead Quantitative Researcher & Forensic Validation Agent  
**Audit Status**: COMPLETE & VERIFIED  
**Final Decision Gate**: **A) SUPPORTS FURTHER RESEARCH** (Hypothesis-Level Decision Gate)  

---

## 1. Scope

Phase 12 Step 3 investigates whether applying an absolute forecast magnitude filter $\tau$ to the frozen Snapshot B intraday predictions:
$$\text{Position}(T+1) = \begin{cases} \text{sign}(\widehat{R}_{\text{intraday}}(T+1)), & \text{if } |\widehat{R}_{\text{intraday}}(T+1)| \ge \tau \\ 0, & \text{otherwise} \end{cases}$$
can reduce trading turnover and frictional execution drag while preserving positive predictive and economic characteristics, without introducing post-hoc threshold optimization or data leakage.

This forensic audit reviews the implementation, data integrity, mathematical calculations, threshold response surface, and governance compliance of Step 3.
The scope is strictly confined to the development out-of-fold partition (`2014-01-02` through `2021-12-31`, $N = 1,960$).

---

## 2. Holdout Firewall Proof

### Absolute Quarantine of Terminal Holdout
The Terminal Holdout (`2022-01-03` through `2026-09-03`, $N = 1,154$) was consumed in Phase 11 Stage 2 and remains permanently sealed.

### Programmatic Verification
1. **Diagnostics Artifact (`step3_selective_diagnostics.csv`)**:
   * Minimum Date: `2014-01-02`
   * Maximum Date: `2021-12-31`
   * Observations: Exactly $1,960$
   * Observations on or after `2022-01-03`: **EXACTLY 0**
2. **Dependency Check**:
   * `scripts/phase12_step3_selective_trading_research.py` reads exclusively from `data/interim/phase12/snapshot_b_intraday_diagnostics.csv` and `snapshot_b_intraday_fold_results.csv`.
   * No code path imports, reads, or evaluates any Phase 11 Stage 2 terminal holdout files (`phase11_stage2_*.csv`).
   * Zero holdout metrics influenced threshold selection, baseline construction, or reporting.

---

## 3. Causal Timing Proof

* **Signal Generation Cutoff**: 08:50 IST on Day $T+1$ (Snapshot B).
* **Trade Entry**: 09:15 IST on Day $T+1$ (Open price).
* **Trade Exit**: 15:30 IST on Day $T+1$ (Close price).
* **Zero Overnight Exposure**: All positions are closed at 15:30 IST on the same trading session.
* **Causality Integrity**: Signals depend strictly on $\widehat{R}_{\text{intraday}}$, which was generated in Step 2 using features finalized at 08:50 IST. No future OHLC from Day $T+1$ enters the position decision.

---

## 4. Exact 63-Feature Governance

* Model 1 was frozen in Phase 6 / Phase 7 with exactly 63 features (45 Price + 18 Context).
* Zero retraining was performed in Step 3.
* Zero News features were introduced.
* Zero Phase 10 regime filters (VIX, trend, volatility) were applied.
* Step 3 operates purely as a policy evaluation layer on top of the sealed Step 2 predictions.

---

## 5. Frozen Step 2 Prediction Dependency Audit

* Source file: `data/interim/phase12/snapshot_b_intraday_diagnostics.csv`.
* Verified row count: Exactly $1,960$ OOF sessions.
* Verified date span: `2014-01-02` through `2021-12-31`.
* Re-verification of SHA-256 hash of Step 2 diagnostics artifact confirms zero modification since Step 2 sealing.

---

## 6. Frozen Threshold Grid Audit

The threshold grid was pre-registered and frozen prior to evaluation:
$$\tau \in [0, 5, 10, 15, 20, 25, 30, 40, 50]\ \text{bps}$$
* Converted to decimal return: $[0.0, 0.0005, 0.0010, 0.0015, 0.0020, 0.0025, 0.0030, 0.0040, 0.0050]$.
* Verified that all 9 thresholds are present in output tables.
* Zero intermediate or tuned thresholds (e.g. 12.5 bps, 17 bps) were evaluated or added.

---

## 7. Mathematical Verification of Trading Policy & Cost Accounting

1. **Position Logic**:
   * For session $i$, if $|\widehat{R}_i| \ge \tau$, $\text{position}_i = \text{sign}(\widehat{R}_i) \in \{+1.0, -1.0\}$.
   * If $|\widehat{R}_i| < \tau$, $\text{position}_i = 0.0$.
2. **Friction Accounting**:
   * Active trade net return: $R_{\text{net}, i} = \text{position}_i \times R_{\text{true}, i} - C_{\text{frac}}$.
   * Flat session net return: $R_{\text{net}, i} = 0.0$ (zero transaction cost charged).
   * Total cost charged across $N$ sessions equals $\sum (\text{pos}_i \ne 0) \times C_{\text{frac}}$ (verified programmatically).
3. **Statistical Diagnostics**:
   * Newey-West HAC standard error, $t$-statistic, and $p$-value computed on daily strategy returns using Bartlett kernel with lag truncation $L = \min(20, \max(1, \lfloor 4 (N/100)^{2/9} \rfloor))$.

---

## 8. Step 2 $\tau = 0$ Reconciliation Proof

At $\tau = 0$ bps, the policy reproduces the Step 2 unrestricted baseline across all cost scenarios:
* **0 bps Gross Return**: $+18.2519\%$ annualized, Sharpe $+1.29$ (matches Step 2 reference to $10^{-6}$).
* **10 bps Net Return**: $-6.9481\%$ annualized, Sharpe $-0.49$ (matches Step 2 reference to $10^{-6}$).
* **Maximum Drawdown (10 bps)**: $-53.55\%$ (exact match).

---

## 9. Baseline Audit

Evaluated against 5 formal benchmarks across all cost scenarios:
1. **Unrestricted Model ($\tau = 0$)**: $-6.95\%$ at 10 bps.
2. **Always Short Baseline**: $-4.95\%$ at 10 bps (Sharpe $-0.35$).
3. **Always Long Baseline**: $-45.45\%$ at 10 bps (Sharpe $-3.20$).
4. **Zero-Position Baseline**: $0.00\%$ return, $0.00$ Sharpe.
5. **Matched-Activity Random Baseline**: Evaluated for every threshold using deterministic seeded PRNG (`RandomState(42)`). At $\tau = 10$ bps ($K=160$ active sessions), the matched random baseline yields **$-2.71\%$** annualized net return at 10 bps (Sharpe $-0.77$).
* The selective model ($+1.92\%$ at 10 bps) strictly outperforms all naive and matched-activity baselines.

---

## 10. Fold-by-Fold and Temporal Audit

* Evaluated across 8 expanding walk-forward folds (2014 through 2021).
* **Regime Concentration Finding**: In Folds 1, 5, 6, and 7 (2014, 2018, 2019, 2020), tree count selection chose $N^* = 10$. With strong regularization, the model never outputted predictions $\ge 10$ bps, resulting in zero trades during those years.
* In active years (2015, 2016, 2017, 2021), net returns at 10 bps were $+1.54\%$, $+9.24\%$, $-4.86\%$, and $+9.44\%$.
* Evaluated across 3 fixed temporal periods:
  * 2014–2016: $+3.61\%$ annualized at 10 bps (Sharpe $+0.86$, win rate $65.8\%$).
  * 2017–2019: $-1.64\%$ annualized at 10 bps (Sharpe $-0.73$, win rate $50.9\%$).
  * 2020–2021: $+4.70\%$ annualized at 10 bps (Sharpe $+1.21$, win rate $58.8\%$).

---

## 11. Feature Importance & Phase 11 Comparison Caveats

* Feature importance remains diagnostic and non-causal (unchanged from Step 2).
* The comparison with Phase 11 confirms that resolving target mismatch and applying turnover control mitigates friction drag, but does NOT prove live profitability.

---

## 12. Artifact SHA-256 Checksum Table

| File Path | Size (Bytes) | Lines | SHA-256 Hash |
| :--- | :---: | :---: | :--- |
| `scripts/phase12_step3_selective_trading_research.py` | 23,356 | 523 | `819ae0483fd4d2bf31f7bd653572ddcdd44fcf139b1fc906e8ab025ae645f947` |
| `data/interim/phase12/step3_selective_threshold_results.csv` | 13,201 | 37 | `4fece4dcde704af5925ef4369863a1fe4cc008a4d6282a12dcf9066f5ac59938` |
| `data/interim/phase12/step3_selective_fold_results.csv` | 6,863 | 73 | `3be44dbdba9537e3b77c2d03abdc044553b2d7031a38f5e82091935dd86dd48c` |
| `data/interim/phase12/step3_selective_temporal_results.csv` | 2,936 | 28 | `dbc96ba89fa5ca20bc0159fe0a5a2d5564fa7e0e20f3957bdd7007766814c5fd` |
| `data/interim/phase12/step3_selective_baseline_results.csv` | 9,153 | 53 | `5e13e0630276a6ce82a2ab62d09e786165633638acf6f4ecf3899386d502267e` |
| `data/interim/phase12/step3_selective_diagnostics.csv` | 329,333 | 1,961 | `b4ae9d5c8765f98c6e1bd04f0d69b535e3cbf296100aaa8c4f391b6f06fbbffc` |
| `tests/test_phase12_step3_selective_trading.py` | 7,399 | 160 | `c8434b78da418d126b45ce8b45c00059a8c1425dd5ead190c9546e8909412f8d` |
| `docs/PHASE_12_STEP_3_SELECTIVE_TRADING_RESEARCH_REPORT.md` | 19,250 | 229 | `56ab42bfd7ff35483ce9f6bee7ce990068c5c245e29e86f80f91da43f9eb8e39` |

All 19 protected Phase 4–10 baseline hashes remain identical to their sealed values in `configs/phase11_strategy_validation_config.json`.

---

## 13. Test Results

* **Dedicated Step 3 Test Suite** (`tests/test_phase12_step3_selective_trading.py`): **8/8 PASSED** in 0.88s.
* **Full Project Regression Suite**: **236/236 PASSED** in 10.61s.
* Discrepancies, regressions, or broken contracts: **ZERO**.

---

## 14. Final Scientific Conclusion

Phase 12 Step 3 establishes that **selective trading based on forecast magnitude is a valid mechanism for controlling turnover and reducing transaction cost drag**:
1. Turnover drops from $252$ to $20.6$ trades/year at $\tau = 10$ bps, reducing annual cost drag by $92\%$.
2. Net annualized return at $10$ bps institutional cost improves from $-6.95\%$ (unrestricted) to $+1.92\%$ ($\tau = 10$ bps).
3. Active directional hit rate scales positively with threshold magnitude ($53.6\% \to 59.4\% \to 67.4\% \to 80.0\%$).
4. Critical failure modes were identified: extreme short bias ($>95\%$ short) and trading dormancy during conservative tree regularization regimes ($N^* = 10$).
5. The evidence supports further research into adaptive/percentile-based turnover control, while strictly precluding live deployment.

---

## 15. Formal Governance Statements

$$\mathbf{PHASE\ 12\ STEP\ 3\ IS\ FORMALLY\ SEALED.}$$

$$\mathbf{NO\ PHASE\ 12\ STEP\ 4\ EXECUTION\ IS\ AUTHORIZED\ BY\ THIS\ TASK.}$$

* The 2022–2026 Terminal Holdout remains completely untouched and quarantined.
* No live trading is justified or authorized.
* No threshold was selected as a production rule.
* Step 3 is complete and permanently sealed.

---
*Certified by Lead Quantitative Researcher & Forensic Validation Agent.*
