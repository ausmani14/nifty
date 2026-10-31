# TARGET CREATION & SIDEWAYS THRESHOLD METHODOLOGY

**Document:** `docs/TARGET_ENGINEERING.md`  
**Phase:** Phase 5 — Target Creation & SIDEWAYS Threshold Methodology  
**Asset:** NIFTY 50 Index (`^NSEI` / `NIFTY 50`)  
**Input Source:** [`data/processed/nifty_50_daily.csv`](../data/processed/nifty_50_daily.csv)  
**Target Registry Config:** [`configs/targets.yaml`](../configs/targets.yaml)  
**Frozen V1 Methodology:** **Method A: Dynamic Volatility-Scaled Threshold**  
**Frozen Parameters:** \( k = 0.35 \), \( \text{rolling window} = 20 \text{ trading sessions} \)  
**Snapshot A Targets Dataset:** `data/targets/nifty50_targets_snapshot_a.csv` (4,654 rows)  
**Snapshot B Targets Dataset:** `data/targets/nifty50_targets_snapshot_b.csv` (4,654 rows)  
**Diagnostic Analysis Report:** `data/targets/threshold_analysis.json`  
**Manifest:** `data/targets/nifty50_targets.meta.json`  
**Total Historical Sessions:** **4,654** (September 17, 2007 to September 4, 2026)  
**Classified Sessions:** **4,633** (99.55%)  
**Warm-Up Sessions:** **20**  
**Terminal Unlabeled Sessions:** **1**  

---

## 1. Executive Summary & Core Methodology

Phase 5 establishes the formal mathematical definitions, temporal semantics, and leakage-safe thresholding methodology for next-session NIFTY 50 prediction. 

For each eligible trading session \( T \), NIFTY AI produces two synchronized target variables:
1. **Continuous Regression Target:** Next-session close-to-close percentage price return:
   $$r_{T+1} = \frac{\text{Close}_{T+1}}{\text{Close}_T} - 1$$
2. **3-Class Directional Categorical Target:** Directional outcome classified into:
   $$y_{\text{dir}, T+1} \in \{\text{UP}, \text{DOWN}, \text{SIDEWAYS}\}$$
   governed by the frozen Method A dynamic volatility threshold \(\theta_T\).

---

## 2. Frozen V1 Methodology & Statistical Justification

Per `MASTER_SPECIFICATION.md` Section 5.2, NIFTY AI freezes **Method A (Dynamic Volatility-Scaled Thresholding)** as the production V1 methodology:

$$\theta_T = 0.35 \times \sigma_{20}(T)$$

Where:
- \( \sigma_{20}(T) = \text{Sample Standard Deviation}\left( \{ r_t \}_{t=T-19}^{T} \right) \) is the trailing 20-session sample standard deviation of daily close-to-close returns finalized by the cutoff of session \( T \).
- \( k = 0.35 \) scales the threshold in dimensionally consistent standard deviation units.

### Statistical & Economic Justification (Zero Target-Optimization)
1. **Dimensionally Consistent Volatility Scaling:** Rather than imposing an arbitrary fixed boundary (e.g. \(\pm 0.5\%\)), \(\theta_T\) represents a dynamic \(0.35\) standard deviation band of recent price fluctuations.
2. **Regime Responsiveness:** The threshold automatically expands during high-volatility turbulence (e.g., expanding to \(\theta_T > 1.0\%\) during the 2008 GFC and March 2020 COVID crisis) and contracts during quiet consolidation regimes (e.g., \(\theta_T \approx 0.20\%\) during 2017).
3. **No Optimization on SIDEWAYS Proportion:** The parameter \( k = 0.35 \) was **not** selected or tuned by optimizing toward an arbitrary SIDEWAYS percentage target. It is grounded in financial econometric volatility scaling, with resulting class distributions evaluated strictly as observational post-hoc diagnostics.
4. **Holdout Isolation:** All parameter evaluation was conducted exclusively on historical development data (\( \le \text{2021-12-31} \)). The out-of-sample holdout window (\( \text{2022-01-01} \) to \( \text{2026-09-04} \)) remained completely unseen during methodology specification.

---

## 3. Multi-Criteria Diagnostic Comparison

Thirteen candidate configurations were evaluated across development data (\( \le \text{2021-12-31} \), 3,499 trading sessions) using multi-criteria diagnostics without scalar score ranking or SIDEWAYS optimization:

| # | Methodology | Configuration | Mean Threshold \(\bar{\theta}\) | Threshold Stdev \(\sigma_\theta\) | UP % | DOWN % | SIDEWAYS %* | UP/DOWN Ratio |
|:---:|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | **`volatility_scaled` (Frozen V1)** | **`k=0.35, w=20`** | **0.413%** | **0.266%** | **38.0%** | **32.3%** | **29.7%** | **1.18** |
| 2 | `volatility_scaled` | `k=0.30, w=20` | 0.354% | 0.228% | 39.8% | 34.2% | 26.0% | 1.16 |
| 3 | `volatility_scaled` | `k=0.25, w=20` | 0.295% | 0.190% | 41.7% | 36.0% | 22.3% | 1.16 |
| 4 | `volatility_scaled` | `k=0.40, w=20` | 0.472% | 0.304% | 35.8% | 30.4% | 33.8% | 1.18 |
| 5 | `volatility_scaled` | `k=0.50, w=20` | 0.590% | 0.380% | 32.6% | 27.5% | 39.9% | 1.19 |
| 6 | `volatility_scaled` | `k=0.35, w=60` | 0.425% | 0.245% | 36.6% | 31.5% | 31.9% | 1.16 |
| 7 | `empirical_distribution` | `p=25.0%, w=252` | 0.313% | 0.142% | 39.7% | 33.9% | 26.4% | 1.17 |
| 8 | `empirical_distribution` | `p=30.0%, w=252` | 0.387% | 0.180% | 37.0% | 31.4% | 31.6% | 1.18 |
| 9 | `empirical_distribution` | `p=35.0%, w=252` | 0.460% | 0.214% | 34.7% | 28.8% | 36.5% | 1.20 |
| 10 | `empirical_distribution` | `p=40.0%, w=252` | 0.536% | 0.254% | 32.1% | 26.9% | 41.0% | 1.19 |
| 11 | `fixed_baseline` | `value=0.30%` | 0.300% | 0.000% | 39.4% | 33.8% | 26.8% | 1.17 |
| 12 | `fixed_baseline` | `value=0.50%` | 0.500% | 0.000% | 31.4% | 27.3% | 41.3% | 1.15 |
| 13 | `fixed_baseline` | `value=0.75%` | 0.750% | 0.000% | 23.3% | 20.6% | 56.1% | 1.13 |

*\* Note: SIDEWAYS % is recorded strictly as an observational post-hoc diagnostic, not an optimization target.*

---

## 4. Stability & Robustness Diagnostics (Frozen Method A)

### Chronological Era Stability (Development Partition)
Evaluated across three distinct historical market cycles:

| Market Era | Date Range | Sessions | UP % | DOWN % | SIDEWAYS %* | UP/DOWN | Mean Threshold \(\bar{\theta}\) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Early (GFC & Recovery)** | 2007–2013 | 1,519 | 36.3% | 34.6% | **29.1%** | 1.05 | 0.530% |
| **Middle (Consolidation / Low Vol)** | 2014–2018 | 1,221 | 38.2% | 30.2% | **31.5%** | 1.27 | 0.283% |
| **Recent Dev (Pre-COVID / 2020)** | 2019–2021 | 739 | 40.9% | 31.1% | **28.0%** | 1.31 | 0.388% |

**Diagnostic Finding:** Despite the mean threshold dynamically adjusting by nearly 2x (from 0.283% in 2014–2018 up to 0.530% during the volatile 2007–2013 era), the observed SIDEWAYS classification rate remained stable within a tight 28.0%–31.5% range across all three eras.

### Volatility Regime Sensitivity
- **Median Trailing 60-Day Volatility:** 1.01% daily return standard deviation.
- **Low-Volatility Sub-Sample (\( N = 1,720 \)):**
  - SIDEWAYS: **28.4%** | UP: **38.0%** | DOWN: **33.5%**
- **High-Volatility Sub-Sample (\( N = 1,719 \)):**
  - SIDEWAYS: **30.8%** | UP: **38.0%** | DOWN: **31.2%**
- **Spread (High Vol - Low Vol):** **+2.4%**

**Diagnostic Finding:** In contrast to fixed thresholds (where sideways classification fluctuates by >30% between high and low volatility regimes), Method A adapts dynamically, exhibiting only a minor +2.4% difference in sideways proportion between regimes.

### Out-of-Sample Holdout Audit (2022-01-01 to 2026-09-04)
*Audited purely out-of-sample; completely unseen during methodology specification:*
- **Holdout Window:** 2022-01-01 to 2026-09-04 (\( N = 1,154 \))
- **Observed Distribution:** UP = **37.35%**, DOWN = **32.15%**, SIDEWAYS = **30.50%**
- **UP/DOWN Ratio:** **1.162**
- **Conclusion:** Out-of-sample behavior is virtually identical to development period diagnostics (UP: 38.0%, DOWN: 32.3%, SIDEWAYS: 29.7%, UP/DOWN: 1.18), demonstrating zero over-fitting.

---

## 5. Formal Directional Classification Rules

The categorical label \( y_{\text{dir}, T+1} \) for next trading session \( T+1 \) is mathematically defined as:

$$y_{\text{dir}, T+1} = \begin{cases}
\text{UP}, & \text{if } r_{T+1} > +\theta_T \\
\text{DOWN}, & \text{if } r_{T+1} < -\theta_T \\
\text{SIDEWAYS}, & \text{if } -\theta_T \le r_{T+1} \le +\theta_T
\end{cases}$$

Where:
- \( r_{T+1} = \frac{\text{Close}_{T+1}}{\text{Close}_T} - 1 \)
- \( \theta_T = 0.35 \times \sigma_{20}(T) \)

---

## 6. Prediction Snapshots & Dataset Alignment

```
Trading Session T                                           Trading Session T + 1
─────────────────────────────────────────────────────────────────────────────────────────────
[09:15 - 15:30 IST]         15:40 IST                        08:50 IST       [09:15 - 15:30 IST]
Session T                   Snapshot A                       Snapshot B      Session T+1
                            Cutoff: 15:30 IST (Day T)        Cutoff: 08:50 IST (Day T+1)
                            Predicts: Session T+1            Predicts: Session T+1
```

### Snapshot A Alignment (`nifty50_targets_snapshot_a.csv`)
- **Row perspective:** Prediction generated at 15:40 IST after session \( T \) market close.
- **`trading_date`:** Session \( T \).
- **`close`:** \( \text{Close}_T \).
- **`threshold_value`:** \( \theta_T = 0.35 \times \sigma_{20}(T) \) (uses information finalized through Session \( T \) only).
- **`target_date`:** Session \( T+1 \).
- **`target_close`:** \( \text{Close}_{T+1} \).
- **`target_return`:** \( \text{Close}_{T+1} / \text{Close}_T - 1 \).

### Snapshot B Alignment (`nifty50_targets_snapshot_b.csv`)
- **Row perspective:** Prediction generated at 08:50 IST before session \( T+1 \) opens.
- **`prediction_date`:** Session \( T+1 \).
- **`feature_cutoff_session`:** Session \( T \) (latest finalized daily bar).
- **`feature_close`:** \( \text{Close}_T \).
- **`threshold_value`:** \( \theta_T \) (uses information finalized through Session \( T \) only; strictly **never** accesses Session \( T+1 \)).
- **`target_date`:** Session \( T+1 \).
- **`target_close`:** \( \text{Close}_{T+1} \).
- **`target_return`:** \( \text{Close}_{T+1} / \text{Close}_T - 1 \).

---

## 7. Target Datasets & Production Artifacts

| File | Description | Row Count | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| [`data/targets/nifty50_targets_snapshot_a.csv`](../data/targets/nifty50_targets_snapshot_a.csv) | Snapshot A target dataset | 4,654 | `a13fed61f92c3fcccf9fe09ce59eb0df4d95ef8dce0aef970ff5ed1220ea055d` |
| [`data/targets/nifty50_targets_snapshot_b.csv`](../data/targets/nifty50_targets_snapshot_b.csv) | Snapshot B target dataset | 4,654 | `54ac54fdeafd53ddea20b1d31cd89c1fbaebdbc88c0f24f8a1f73ce2867e01d2` |
| [`data/targets/nifty50_targets.meta.json`](../data/targets/nifty50_targets.meta.json) | Target metadata manifest | — | Structured JSON |
| [`data/targets/threshold_analysis.json`](../data/targets/threshold_analysis.json) | Multi-criteria diagnostic report | — | Structured JSON |
| [`configs/targets.yaml`](../configs/targets.yaml) | Production target registry specification | — | Structured YAML |

### Final Accounting Summary (Full Historical Dataset)
- **Total Sessions:** 4,654
- **Classified Sessions:** **4,633** (99.55%)
- **Warm-Up Excluded Sessions:** **20** (First 20 sessions: `2007-09-17` to `2007-10-15` required for \(\sigma_{20}\))
- **Terminal Unlabeled Sessions:** **1** (`2026-09-04` has `has_target = False`, `target_return = None`)
- **Observed Class Distribution (Post-Hoc Diagnostic):**
  - **UP:** 1,752 (37.82%)
  - **DOWN:** 1,495 (32.27%)
  - **SIDEWAYS:** 1,386 (29.92%)
  - **UP/DOWN Ratio:** 1.172

---

## 8. Anti-Leakage Verification Summary

The target engine is audited with 19 automated tests in [`tests/test_targets.py`](../tests/test_targets.py):
1. **Zero Optimization Target:** Verified that `selection_score` is completely eliminated and SIDEWAYS % is not an optimization target.
2. **Snapshot B Point-in-Time Isolation:** Verified that mutating Day \( T \)'s price/return leaves Snapshot B's threshold for predicting Day \( T \) 100% invariant.
3. **Future Mutation Invariance:** Verified that mutating future returns leaves historical thresholds bit-identical.
4. **Target Shift Correctness:** Verified that row \( T \) uses close of \( T+1 \) and never references \( T-1 \).
5. **Terminal Session Protection:** Verified that the final historical row has `None` for all targets.
6. **Preservation of Extreme Returns:** Verified that extreme moves ($\ge 10\%$) are preserved unclipped.
