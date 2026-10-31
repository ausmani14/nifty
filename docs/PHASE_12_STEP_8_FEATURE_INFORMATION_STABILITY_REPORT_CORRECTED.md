# PHASE 12 — STEP 8: FEATURE INFORMATION STABILITY & INFORMATION-SET ABLATION RESEARCH (CORRECTED)

> [!IMPORTANT]
> **Forensic Interpretation Correction Notice:**  
> This is a forensic interpretation correction of the original Phase 12 Step 8 report. Computational results and protected upstream artifacts are unchanged. The original report (`docs/PHASE_12_STEP_8_FEATURE_INFORMATION_STABILITY_REPORT.md`) is preserved byte-for-byte. This corrected document reconciles the scientific interpretation to remove overclaims regarding causality, establishes clear distinctions between model attribution and marginal predictive value, avoids non-causal claims regarding 2021 regime drivers, and formulates precise conclusions regarding Macro Context and the unconditional short drift baseline.

**Document:** `docs/PHASE_12_STEP_8_FEATURE_INFORMATION_STABILITY_REPORT_CORRECTED.md`  
**Correction Date:** 2026-09-19T10:35:00Z  
**Phase:** Phase 12 — Research Diagnostic Step 8 (Reconciled & Corrected)  
**Model Family:** XGBoost Regressor (Walk-Forward W0 Expanding Baseline, Fold-Local N* Inner Validation)  
**Target:** $R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)}$ (Snapshot B 08:50 IST)  
**Population:** Development OOF Period `2014-01-02` through `2021-12-31` ($N = 1,960$ sessions, 8 folds)  
**Holdout Discipline:** Zero access to Terminal Holdout (`2022-01-03` to `2026-09-03`, $N=1,154$ strictly quarantined)  
**Decision Gate:** **B) FEATURE INFORMATION STABILITY NOT SUPPORTED**

---

## 1. Executive Summary

Phase 12 Step 8 evaluates the **information-set dependence and feature stability** of the sealed Snapshot B (08:50 IST) Model 1 regressor predicting same-day NIFTY 50 intraday open-to-close returns ($R_{\text{intraday}}$).

Following the findings of Step 5 (unconditional short drift explains zero-cost profitability), Step 6 (apparent residual edge is driven by temporal concentration in 2021), and Step 7 (the residual edge collapses under rolling training windows), Step 8 systematically decomposes the **63-feature information space** (45 Price + 18 Context; 0 News, 0 Volume, 0 Flow proxies) into pre-registered, mutually interpretable information families and evaluates:
1. **Isolated Standalone Predictability:** How each feature family performs in complete isolation.
2. **Leave-One-Out (LOO) Ablation:** The marginal information change ($\Delta \text{IC} = \text{IC}_{\text{ref}} - \text{IC}_{\text{ablated}}$ and $\Delta R^2 = R^2_{\text{ref}} - R^2_{\text{ablated}}$) when each family is omitted.
3. **Temporal Non-Stationarity & Base-Rate Dependence:** Whether any family demonstrates persistent predictive association across chronological blocks (Block A 2014–2016, Block B 2017–2019, Block C 2020–2021) or provides incremental edge over the unconditional short baseline.

### Primary Forensic Findings

1. **Price-Only Information Does Not Demonstrate Distinguishable Residual Signal:**
   The tested Price-only configuration (`G1_PRICE`, 45 features) did not demonstrate statistically distinguishable residual predictive information in this OOF experiment: residual Pearson IC is **$-0.0101$** ($p = 0.6544$) and incremental $R^2$ is $+0.0121\%$. In a 1,000-permutation placebo test, `G1_PRICE` yields an empirical p-value of **$0.6640$**, confirming that under this model specification, isolated technical price patterns contain no statistically distinguishable predictive information for intraday returns.

2. **Macro Context Accounts for Observed Residual Correlation (Non-Causal):**
   Within the tested model and feature specification, Macro Context features account for a substantial portion of the observed residual predictive relationship. However, the ablation experiment does not establish that these variables causally generate the return relationship.
   - Removing Context features (`LOO_NO_CONTEXT` / `G1_PRICE`) causes the reference model's residual IC to drop from $+0.0477$ to $-0.0101$ ($\Delta \text{IC} = +0.0579$, $\Delta R^2 = +0.3304\%$, $p = 0.6544$).
   - Within Context, **Macro Context (`G8_MACRO_CTX`: Brent, WTI, Gold, DXY, US 10Y Yield)** exhibits the strongest evidence of marginal statistical association: omitting Macro Context (`LOO_NO_MACRO_CTX`) reduces residual IC from $+0.0477$ to $+0.0157$ ($\Delta \text{IC} = +0.0321$, $\Delta R^2 = +0.2302\%$, placebo empirical $p = 0.2300$).
   - Conversely, standalone Macro Context (`G8_MACRO_CTX`, 5 features) achieves a residual IC of $+0.0436$ ($p = 0.0537$, placebo $p = 0.0240$).

3. **Tree Attribution Does Not Equal Marginal Predictive Contribution:**
   In the reference 63-feature model (`G0_ALL`), tree splits are heavily concentrated in Short-Horizon Price features (`G3_SHORT_PRICE`), which receive **44.15% of total booster split gain**. However, the ablation results demonstrate that high internal split attribution does not necessarily imply that removing the feature family will reduce OOF predictive performance:
   - Omitting Short Price (`LOO_NO_SHORT_PRICE`) yields residual IC of $+0.0532$ ($\Delta \text{IC} = -0.0055$).
   - Omitting Medium/Long Price (`LOO_NO_MED_LONG_PRICE`) yields residual IC of $+0.0680$ ($\Delta \text{IC} = -0.0203$).
   Booster split gain describes how the fitted model used features internally to segment the data; it does not measure causal importance or marginal predictive value.

4. **Temporal Non-Stationarity Across Historical Blocks:**
   The results demonstrate temporal instability of the measured relationship. The experiment does not identify whether the instability arises from market-regime changes, changing data relationships, model specification, or other unobserved factors:
   - In **Block B (2017–2019)**, the reference model and major ablations exhibit negative or near-zero residual IC (`G0_ALL`: $-0.0284$; `LOO_NO_MACRO_CTX`: $-0.0382$; `G7_GLOBAL_CTX`: $-0.0354$).
   - In **Year 2021**, multiple feature configurations exhibit elevated relationships (`G0_ALL`: $+0.2539$; `LOO_NO_GLOBAL_CTX`: $+0.2590$; `LOO_NO_MED_LONG_PRICE`: $+0.2500$; `G1_PRICE`: $+0.1822$).
   - The 2021 concentration is consistent with substantial temporal non-stationarity. Because multiple feature configurations exhibit elevated 2021 relationships, the experiment does not establish that the concentration was specifically caused by macroeconomic conditions.

5. **Statistical Differences Do Not Translate Into Economic Outperformance:**
   The statistical feature-family differences do not translate into demonstrated economic superiority over the unconditional short baseline, and all tested configurations remain negative under the 10 bps diagnostic cost assumption:
   - Always Short baseline: $+8.04$ bps/day gross.
   - Reference `G0_ALL`: $+7.24$ bps/day gross (difference $-0.79$ bps/day, HAC $t = -0.58$, $p = 0.5591$).
   - Standalone `G8_MACRO_CTX`: $+5.66$ bps/day gross (difference $-2.37$ bps/day, HAC $t = -1.87$, $p = 0.0621$).
   - Standalone `G1_PRICE`: $+6.88$ bps/day gross (difference $-1.15$ bps/day, HAC $t = -1.23$, $p = 0.2202$).
   - Standalone `G4_MED_LONG_PRICE`: $+8.04$ bps/day gross (100% short predictions, difference $0.00$ bps/day).
   Under a 10 bps roundtrip diagnostic friction, every tested configuration generates negative net daily returns ($-1.53$ to $-4.34$ bps/day) and severe drawdowns ($-39.2\%$ to $-63.9\%$). No configuration is economically validated or production-ready.

### Central Scientific Conclusion
**No pre-registered feature family demonstrates a stable and economically meaningful incremental predictive relationship beyond the unconditional intraday short drift across the tested folds and temporal blocks. Macro Context exhibits the strongest evidence of marginal statistical association in the tested information set, but this relationship is temporally unstable and does not establish statistically significant economic outperformance versus the Always Short baseline.**

---

## 2. Exact Feature Taxonomy & Registry

Before model execution, the 63 features were pre-registered and mapped into mutually exclusive families based on the frozen specifications in `docs/FEATURE_ENGINEERING.md` and `docs/MARKET_CONTEXT_DATA.md`.

```
                        ┌─────────────────────────────────────────────────────────┐
                        │          Snapshot B Model 1 Space (63 Features)         │
                        └────────────────────────────┬────────────────────────────┘
                                                     │
                     ┌───────────────────────────────┴───────────────────────────────┐
                     ▼                                                               ▼
        ┌─────────────────────────┐                                     ┌─────────────────────────┐
        │  Price Features (45)    │                                     │  Context Features (18)  │
        │  (Source: Phase 4)      │                                     │  (Source: Phase 7)      │
        └────────────┬────────────┘                                     └────────────┬────────────┘
                     │                                                               │
     ┌───────────────┼───────────────┬──────────────┐                ┌───────────────┼───────────────┐
     ▼               ▼               ▼              ▼                ▼               ▼               ▼
┌──────────┐   ┌───────────┐   ┌───────────┐  ┌───────────┐    ┌───────────┐   ┌───────────┐   ┌───────────┐
│ G3: Short│   │ G4: Med/  │   │ G5: Vol / │  │ Calendar  │    │ G6: Dom.  │   │ G7: Global│   │ G8: Macro │
│ Price    │   │ Long Price│   │ Risk      │  │ Seasonal  │    │ Context   │   │ Equities  │   │ Context   │
│ (25 feats)│  │ (10 feats)│   │ (5 feats) │  │ (5 feats) │    │ (5 feats) │   │ (8 feats) │   │ (5 feats) │
└──────────┘   └───────────┘   └───────────┘  └───────────┘    └───────────┘   └───────────┘   └───────────┘
```

### Taxonomy Partition Breakdown

| Group Code | Information Family | Count | Primary Features Included | Description |
| :--- | :--- | :---: | :--- | :--- |
| **G3_SHORT_PRICE** | Short-Horizon Price | 25 | `ret_1d`..`ret_20d` (6), `ret_lag_1`..`lag_10` (5), `sma_5`..`sma_20` & distances (6), `mom_5d`..`mom_20d` (3), `hl_range_pct`, `close_pos_in_range`, `open_to_close_ret`, shadow distances (5) | Short-term momentum, mean-reversion, intraday bar geometry, and trailing short-term moving average spreads. |
| **G4_MED_LONG_PRICE** | Medium/Long Price | 10 | `sma_50`, `sma_100`, `sma_200` & distances (6), `mom_60d` (1), `sma_ratio_20_50`, `sma_ratio_50_200`, `trend_slope_20d` (3) | Structural trend alignment, moving average ribbons, multi-month price trajectory slope, and long-term momentum. |
| **G5_VOLATILITY** | Price Volatility / Risk | 5 | `volatility_5d`, `volatility_10d`, `volatility_20d`, `volatility_60d`, `volatility_ann_20d` | Sample return standard deviations across varying rolling lookback windows. |
| **G_CALENDAR** | Calendar & Seasonal | 5 | `day_of_week`, `day_of_month`, `month`, `quarter`, `is_month_end` | Point-in-time deterministic calendar day/month markers and settlement expiry proximity flags. |
| **G6_DOMESTIC_CTX** | Domestic Context | 5 | `ctx_ret_1d_nifty_bank`, `ctx_diff_1d_india_vix`, `ctx_level_india_vix`, `ctx_diff_1d_india_10y_yield`, `ctx_diff_1d_usd_inr` | Indian domestic banking equity, domestic implied volatility level and shift, 10Y sovereign yield shift, and USD/INR currency move. |
| **G7_GLOBAL_CTX** | Global Equity & Volatility | 8 | `ctx_ret_1d_sp500`, `ctx_ret_1d_nasdaq`, `ctx_ret_1d_dow_jones`, `ctx_ret_1d_nikkei_225`, `ctx_ret_1d_hang_seng`, `ctx_ret_1d_ftse_100`, `ctx_diff_1d_us_vix`, `ctx_level_us_vix` | Overnight US equity market performance, regional Asian closes (Nikkei, Hang Seng), European FTSE close, and CBOE VIX implied volatility. |
| **G8_MACRO_CTX** | Global Macro & Commodities | 5 | `ctx_ret_1d_brent_crude`, `ctx_ret_1d_wti_crude`, `ctx_ret_1d_gold`, `ctx_ret_1d_dxy`, `ctx_diff_1d_us_10y_yield` | Energy commodity benchmarks (Brent, WTI), precious metals (Gold), US Dollar Index (DXY), and US 10-Year Treasury yield changes. |

- *Total Partition Sum:* $25 + 10 + 5 + 5 + 5 + 8 + 5 = 63$ features (100% complete and mutually exclusive).  
- *Price Total:* $25 + 10 + 5 + 5 = 45$ features (`G1_PRICE`).  
- *Context Total:* $5 + 8 + 5 = 18$ features (`G2_CONTEXT`).  
- *Audit Check:* The pre-registered registry (`data/interim/phase12_step8/step8_feature_group_registry.csv`) matches this partition exactly with zero unassigned or invented features.

---

## 3. Ablation Methodology & Causal Scope Boundaries

The experimental setup adheres strictly to the frozen walk-forward development framework:

1. **Chronological Walk-Forward Folds:**
   - 8 chronological outer folds spanning validation years 2014 through 2021.
   - Expanding historical training set (W0 baseline) starting 2008-07-08 up to December 31 of year $k-1$.
   - Exactly $N = 1,960$ OOF sessions evaluated.

2. **One-Session Causal Embargo:**
   - The target is $R_{\text{intraday}}(T+1) = \text{Close}(T+1)/\text{Open}(T+1) - 1$.
   - All training observations strictly terminate at or before $T-1$ relative to the validation partition. Zero target overlap or lookahead leakage exists across fold boundaries.

3. **Deterministic Inner Validation Tree Selection ($N^*$):**
   - For every configuration and fold, tree counts $N^* \in [10, 15, 20, 25, 30, 35, 40, 45, 50, 60]$ were selected using the final 20% of the training fold as an inner validation set.
   - The model was refit on the full training fold using the selected $N^*$. Zero hyperparameter tuning or tree-selection access to OOF validation data was permitted.

4. **Fold-Local Target Baselines:**
   - For each validation session in fold $k$, the target baseline $\mu_{\text{train}}$ was calculated strictly as the sample mean of historical intraday returns available in that fold's training set:
     $$\text{excess\_prediction} = \hat{y} - \mu_{\text{train}}, \quad \text{residual\_return} = y - \mu_{\text{train}}$$

5. **Methodological Scope Boundary:**
   - Feature ablation evaluates how model predictions and validation metrics shift when information groups are withheld.
   - **Ablation establishes predictive dependence or marginal information contribution under the specified model; it does NOT establish that those variables causally generate the observed market return.**

---

## 4. Full OOF Results Across All 19 Configurations

The table below presents the primary evaluation metrics across the entire 1,960-session development OOF population (2014–2021). FDR adjusted p-values apply the Benjamini-Hochberg procedure across all 19 hypotheses.

| Configuration | Category | Features | Raw Pearson IC | Residual Pearson IC | p-value (FDR) | Δ Residual IC | Incremental R² (%) | Δ R² (%) | % Short | Gross (bps) | Net @ 10bps | HAC p vs Always Short |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `G0_ALL` | Reference | 63 | +0.0476 | +0.0477 | 0.0346 (0.1095) | +0.0000 | +0.343% | +0.000% | 90.7% | +7.24 | -2.76 | 0.5591 |
| `G1_PRICE` | Standalone | 45 | -0.0088 | -0.0101 | 0.6544 (0.7314) | +0.0579 | +0.012% | +0.330% | 96.8% | +6.88 | -3.12 | 0.2202 |
| `G2_CONTEXT` | Standalone | 18 | +0.0386 | +0.0387 | 0.0870 (0.1502) | +0.0091 | +0.220% | +0.122% | 92.4% | +6.79 | -3.21 | 0.2711 |
| `G3_SHORT_PRICE` | Standalone | 25 | +0.0158 | +0.0153 | 0.4997 (0.7304) | +0.0325 | +0.139% | +0.203% | 95.6% | +7.53 | -2.47 | 0.6084 |
| `G4_MED_LONG_PRICE` | Standalone | 10 | -0.0314 | -0.0408 | 0.0708 (0.1494) | +0.0886 | +0.007% | +0.336% | 100.0% | +8.04 | -1.96 | 1.0000 |
| `G5_VOLATILITY` | Standalone | 5 | -0.0043 | -0.0117 | 0.6052 (0.7314) | +0.0594 | -0.035% | +0.378% | 99.0% | +6.78 | -3.22 | 0.1039 |
| `G6_DOMESTIC_CTX` | Standalone | 5 | +0.0136 | +0.0111 | 0.6237 (0.7314) | +0.0367 | +0.031% | +0.311% | 96.1% | +7.55 | -2.45 | 0.4321 |
| `G7_GLOBAL_CTX` | Standalone | 8 | -0.0013 | -0.0045 | 0.8423 (0.8516) | +0.0522 | +0.001% | +0.341% | 95.8% | +7.71 | -2.29 | 0.6836 |
| `G8_MACRO_CTX` | Standalone | 5 | +0.0426 | +0.0436 | 0.0539 (0.1462) | +0.0042 | +0.123% | +0.220% | 88.2% | +5.66 | -4.34 | 0.0621 |
| `G_CALENDAR` | Standalone | 5 | +0.0072 | +0.0042 | 0.8516 (0.8516) | +0.0435 | -0.038% | +0.380% | 92.3% | +6.81 | -3.19 | 0.3016 |
| `LOO_NO_PRICE` | Ablation | 18 | +0.0386 | +0.0387 | 0.0870 (0.1502) | +0.0091 | +0.220% | +0.122% | 92.4% | +6.79 | -3.21 | 0.2711 |
| `LOO_NO_CONTEXT` | Ablation | 45 | -0.0088 | -0.0101 | 0.6544 (0.7314) | +0.0579 | +0.012% | +0.330% | 96.8% | +6.88 | -3.12 | 0.2202 |
| `LOO_NO_SHORT_PRICE` | Ablation | 38 | +0.0519 | +0.0532 | 0.0185 (0.0703) | -0.0055 | +0.372% | -0.029% | 94.3% | +7.23 | -2.77 | 0.3978 |
| `LOO_NO_MED_LONG_PRICE` | Ablation | 53 | +0.0676 | +0.0680 | 0.0026 (0.0399) | -0.0203 | +0.540% | -0.197% | 91.6% | +9.46 | -0.54 | 0.3182 |
| `LOO_NO_VOLATILITY` | Ablation | 58 | +0.0413 | +0.0418 | 0.0641 (0.1494) | +0.0059 | +0.278% | +0.064% | 94.9% | +7.97 | -2.03 | 0.9542 |
| `LOO_NO_DOMESTIC_CTX` | Ablation | 58 | +0.0643 | +0.0646 | 0.0042 (0.0399) | -0.0169 | +0.512% | -0.169% | 94.5% | +8.13 | -1.87 | 0.9408 |
| `LOO_NO_GLOBAL_CTX` | Ablation | 55 | +0.0573 | +0.0591 | 0.0089 (0.0421) | -0.0114 | +0.406% | -0.063% | 96.3% | +7.94 | -2.06 | 0.9311 |
| `LOO_NO_MACRO_CTX` | Ablation | 58 | +0.0168 | +0.0157 | 0.4885 (0.7304) | +0.0321 | +0.112% | +0.230% | 95.7% | +7.21 | -2.79 | 0.3984 |
| `LOO_NO_CALENDAR` | Ablation | 58 | +0.0583 | +0.0595 | 0.0084 (0.0421) | -0.0118 | +0.438% | -0.095% | 94.0% | +8.47 | -1.53 | 0.7467 |

---

## 5. Fold Stability Analysis

Evaluating performance fold-by-fold across the 8 chronological folds demonstrates severe instability and frequent sign inversions:

| Configuration | 2014 (F1) | 2015 (F2) | 2016 (F3) | 2017 (F4) | 2018 (F5) | 2019 (F6) | 2020 (F7) | 2021 (F8) | Positive Folds | Mean N* |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `G0_ALL` (Ref) | **+0.1264** | **+0.0577** | +0.0076 | -0.0131 | -0.0384 | -0.0319 | -0.0469 | **+0.2539** | 4 / 8 | 44.4 |
| `G1_PRICE` | -0.0381 | -0.0617 | +0.0335 | +0.0125 | +0.0199 | +0.0435 | -0.2185 | **+0.1822** | 4 / 8 | 36.9 |
| `G2_CONTEXT` | **+0.1348** | **+0.0717** | -0.0145 | -0.0405 | +0.0210 | +0.0118 | +0.0645 | **+0.1199** | 5 / 8 | 41.9 |
| `G3_SHORT_PRICE` | -0.0354 | -0.0385 | +0.0632 | -0.0147 | +0.0223 | -0.0032 | -0.1130 | **+0.1977** | 3 / 8 | 40.6 |
| `G4_MED_LONG` | -0.0727 | -0.0519 | -0.0917 | +0.0000 | +0.0000 | +0.0350 | -0.0863 | -0.0161 | 1 / 8 | 13.8 |
| `G5_VOLATILITY` | -0.0526 | -0.0615 | -0.0571 | -0.0000 | -0.0000 | -0.0463 | -0.0062 | +0.0178 | 1 / 8 | 21.2 |
| `G6_DOMESTIC` | +0.0485 | +0.0537 | +0.0330 | -0.0382 | -0.0318 | -0.0022 | +0.0628 | -0.0220 | 4 / 8 | 34.4 |
| `G7_GLOBAL_CTX` | -0.0343 | +0.0560 | -0.0197 | -0.0463 | -0.0464 | -0.0139 | -0.0125 | +0.0297 | 2 / 8 | 36.9 |
| `G8_MACRO_CTX` | **+0.1066** | -0.0478 | +0.0140 | +0.0068 | +0.0264 | +0.0456 | +0.0298 | **+0.1389** | 7 / 8 | 38.8 |
| `LOO_NO_MACRO` | **+0.1198** | +0.0371 | -0.0382 | -0.0415 | -0.0583 | -0.0146 | -0.1100 | **+0.1916** | 3 / 8 | 41.9 |

### Observations on Fold Stability
1. In the reference model `G0_ALL`, 4 out of 8 folds produce negative residual correlation (2017, 2018, 2019, 2020).
2. The tested Price-only configuration `G1_PRICE` is negative in 4 of 8 folds, dropping to $-0.2185$ in 2020.
3. Standalone Macro Context `G8_MACRO_CTX` achieves positive correlation across 7 of 8 folds, but its correlation magnitude is modest ($+0.0068$ to $+0.0456$ in 2017–2019) and elevates primarily in 2014 and 2021.

---

## 6. Temporal Block Analysis

The 8-year evaluation window was divided into three pre-registered historical blocks to test for temporal persistence:
- **Block A (2014–2016):** 744 sessions.
- **Block B (2017–2019):** 741 sessions.
- **Block C (2020–2021):** 475 sessions.

| Configuration | Block A (2014–16) | Block B (2017–19) | Block C (2020–21) | Year 2021 Residual IC | Year 2021 Inc R² (%) | 2021 Pred Var (bps²) | 2017–19 Residual IC | 2017–19 Inc R² (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `G0_ALL` | +0.0622 | -0.0284 | +0.1081 | +0.2539 | +2.199% | 13.83 | -0.0284 | -0.400% |
| `G1_PRICE` | -0.0220 | +0.0249 | -0.0176 | +0.1822 | +0.718% | 2.30 | +0.0249 | +0.266% |
| `G2_CONTEXT` | +0.0624 | -0.0028 | +0.0920 | +0.1199 | +0.492% | 2.80 | -0.0028 | -0.166% |
| `G3_SHORT_PRICE` | -0.0033 | +0.0016 | +0.0424 | +0.1977 | +1.332% | 7.05 | +0.0016 | +0.121% |
| `G4_MED_LONG_PRICE` | -0.0727 | +0.0125 | -0.0512 | -0.0161 | +0.115% | 0.17 | +0.0125 | +0.263% |
| `G5_VOLATILITY` | -0.0570 | -0.0170 | +0.0056 | +0.0178 | +0.010% | 0.59 | -0.0170 | -0.104% |
| `G6_DOMESTIC_CTX` | +0.0451 | -0.0239 | +0.0204 | -0.0220 | -0.034% | 1.28 | -0.0239 | -0.242% |
| `G7_GLOBAL_CTX` | +0.0002 | -0.0354 | +0.0086 | +0.0297 | +0.197% | 10.57 | -0.0354 | -0.189% |
| `G8_MACRO_CTX` | +0.0242 | +0.0262 | +0.0843 | +0.1389 | +0.994% | 13.77 | +0.0262 | -0.042% |
| `G_CALENDAR` | +0.0078 | +0.0164 | -0.0347 | +0.0032 | -0.006% | 0.44 | +0.0164 | -0.049% |
| `LOO_NO_PRICE` | +0.0624 | -0.0028 | +0.0920 | +0.1199 | +0.492% | 2.80 | -0.0028 | -0.166% |
| `LOO_NO_CONTEXT` | -0.0220 | +0.0249 | -0.0176 | +0.1822 | +0.718% | 2.30 | +0.0249 | +0.266% |
| `LOO_NO_SHORT_PRICE` | +0.0665 | +0.0004 | +0.0875 | +0.1422 | +1.137% | 10.67 | +0.0004 | +0.010% |
| `LOO_NO_MED_LONG_PRICE` | +0.0748 | -0.0060 | +0.1161 | +0.2500 | +2.799% | 24.79 | -0.0060 | -0.131% |
| `LOO_NO_VOLATILITY` | +0.0659 | -0.0044 | +0.0897 | +0.2297 | +1.075% | 3.61 | -0.0044 | -0.109% |
| `LOO_NO_DOMESTIC_CTX` | +0.0383 | +0.0203 | +0.1138 | +0.2468 | +2.632% | 21.87 | +0.0203 | +0.210% |
| `LOO_NO_GLOBAL_CTX` | +0.0736 | -0.0145 | +0.1099 | +0.2590 | +2.218% | 13.17 | -0.0145 | -0.143% |
| `LOO_NO_MACRO_CTX` | +0.0382 | -0.0382 | +0.0408 | +0.1916 | +0.664% | 1.79 | -0.0382 | -0.215% |
| `LOO_NO_CALENDAR` | +0.0769 | -0.0131 | +0.0931 | +0.2245 | +2.305% | 19.89 | -0.0131 | -0.146% |

### Critical Block Diagnostics
- **Block B Breakdown:** Across 2017–2019, the reference model and almost all ablations exhibit weak or inverted relationships. `G0_ALL` registers a negative residual IC of **$-0.0284$**. Global Equities (`G7`) registers **$-0.0354$**, and removing Macro Context (`LOO_NO_MACRO_CTX`) yields **$-0.0382$**.
- **Block C Concentration:** The full-period correlation of `G0_ALL` ($+0.0477$) is driven disproportionately by Block C ($+0.1081$), specifically Year 2021 ($+0.2539$).

---

## 7. Forensic Check: The 2021 Temporal Concentration

Step 6 identified an elevated concentration of predictive performance in 2021, and Step 7 demonstrated that this relationship was not stable under rolling training windows. In Step 8, we examine the behavior of feature ablations during 2021:

1. **Elevation Across Configurations:**
   In 2021, residual Pearson IC reaches $+0.2539$ in `G0_ALL`, $+0.2500$ in `LOO_NO_MED_LONG_PRICE`, $+0.2468$ in `LOO_NO_DOMESTIC_CTX`, and $+0.2590$ in `LOO_NO_GLOBAL_CTX`. Standalone Price (`G1_PRICE`), which is negative across the full sample ($-0.0101$), also exhibits $+0.1822$ in 2021.
2. **Reconciled Forensic Interpretation:**
   The 2021 concentration is consistent with substantial temporal non-stationarity. The ablation results show that multiple feature configurations also exhibit elevated 2021 relationships, so the experiment does not establish that the concentration was specifically caused by macroeconomic conditions.

---

## 8. Forensic Check: The 2017–2019 Block B Breakdown

During Block B (2017–2019, 741 sessions), the NIFTY 50 experienced distinct market conditions.

1. **Ablation Comparison in Block B:**
   - Removing Context (`LOO_NO_CONTEXT`) produced a slight positive IC in Block B ($+0.0249$), but this coincided with negative IC in Block A ($-0.0220$) and Block C ($-0.0176$).
   - Removing Price (`LOO_NO_PRICE`) left Block B near zero ($-0.0028$).
   - Removing Macro Context (`LOO_NO_MACRO_CTX`) yielded **$-0.0382$** in Block B.
2. **Reconciled Forensic Interpretation:**
   The results demonstrate temporal instability of the measured relationship. The experiment does not identify whether the instability arises from market-regime changes, changing data relationships, model specification, or other unobserved factors.

---

## 9. Residual Information Analysis: Tree Attribution vs. Marginal Predictive Contribution

### Distinct Concepts: Internal Split Use vs. Marginal Information

Booster split gain describes how the fitted model used features internally. It does not measure causal importance or marginal predictive value. The ablation results demonstrate that high internal split attribution does not necessarily imply that removing the feature family will reduce OOF predictive performance:

#### Top 15 Features by Model Attribution (Booster Gain)

| Rank | Feature Name | Canonical Family | Information Group | Source Phase | Relative Gain (%) | Mean Gain | Mean Split Weight | Mean Cover |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 1 | `sma_20` | `short_moving_averages` | `G3_SHORT_PRICE` | Phase 4 | 6.39% | 0.000856 | 3.25 | 666.71 |
| 2 | `close_pos_in_range` | `ohlc_shape` | `G3_SHORT_PRICE` | Phase 4 | 5.23% | 0.000700 | 2.12 | 302.62 |
| 3 | `sma_200` | `med_long_moving_averages` | `G4_MED_LONG_PRICE` | Phase 4 | 4.89% | 0.000655 | 4.50 | 1717.11 |
| 4 | `ctx_ret_1d_sp500` | `global_equity` | `G7_GLOBAL_CTX` | Phase 7 | 4.66% | 0.000624 | 0.75 | 183.25 |
| 5 | `ctx_ret_1d_hang_seng` | `global_equity` | `G7_GLOBAL_CTX` | Phase 7 | 3.74% | 0.000500 | 3.38 | 762.28 |
| 6 | `volatility_5d` | `volatility_risk` | `G5_VOLATILITY` | Phase 4 | 3.52% | 0.000472 | 2.50 | 430.12 |
| 7 | `ret_1d` | `trailing_returns` | `G3_SHORT_PRICE` | Phase 4 | 3.40% | 0.000455 | 7.25 | 1635.97 |
| 8 | `hl_range_pct` | `ohlc_shape` | `G3_SHORT_PRICE` | Phase 4 | 3.23% | 0.000432 | 7.00 | 1170.33 |
| 9 | `ret_2d` | `trailing_returns` | `G3_SHORT_PRICE` | Phase 4 | 3.10% | 0.000415 | 1.38 | 775.88 |
| 10 | `ctx_ret_1d_brent_crude` | `global_commodities` | `G8_MACRO_CTX` | Phase 7 | 3.07% | 0.000411 | 8.62 | 1710.86 |
| 11 | `high_to_close_dist` | `ohlc_shape` | `G3_SHORT_PRICE` | Phase 4 | 2.89% | 0.000387 | 0.75 | 419.69 |
| 12 | `ctx_diff_1d_us_10y_yield` | `global_rates` | `G8_MACRO_CTX` | Phase 7 | 2.75% | 0.000368 | 1.62 | 162.25 |
| 13 | `ctx_ret_1d_wti_crude` | `global_commodities` | `G8_MACRO_CTX` | Phase 7 | 2.57% | 0.000344 | 1.12 | 731.54 |
| 14 | `sma_10` | `short_moving_averages` | `G3_SHORT_PRICE` | Phase 4 | 2.45% | 0.000327 | 0.88 | 509.75 |
| 15 | `ctx_diff_1d_usd_inr` | `domestic_fx` | `G6_DOMESTIC_CTX` | Phase 7 | 2.41% | 0.000323 | 11.38 | 1379.93 |

#### Aggregated Information Group Attributions

| Information Group | Features | Price / Context | Aggregated Gain (%) | Aggregated Split Weight | Mean Gain per Feature | Description |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `G3_SHORT_PRICE` | 25 | Price | 44.15% | 31.75 | 0.000236 | Short returns, lags, short SMAs, short mom, OHLC shape |
| `G7_GLOBAL_CTX` | 8 | Context | 13.55% | 10.62 | 0.000227 | Global equities (S&P, Nasdaq, Dow, Nikkei, HSI, FTSE) & US VIX |
| `G4_MED_LONG_PRICE` | 10 | Price | 12.65% | 9.12 | 0.000169 | Med/long SMAs (50, 100, 200), mom_60d, trend ratios & slopes |
| `G8_MACRO_CTX` | 5 | Context | 9.67% | 12.50 | 0.000259 | Commodities (Brent, WTI, Gold), DXY, US 10Y Treasury yield |
| `G5_VOLATILITY` | 5 | Price | 9.49% | 8.38 | 0.000254 | Rolling volatilities (5d, 10d, 20d, 60d, ann_20d) |
| `G6_DOMESTIC_CTX` | 5 | Context | 7.76% | 17.50 | 0.000208 | Nifty Bank, India VIX (diff/level), India 10Y, USD/INR |
| `G_CALENDAR` | 5 | Price | 2.74% | 1.25 | 0.000073 | Day of week/month, month, quarter, month-end flag |

### Reconciled Attribution Findings

1. **Short-Horizon Price receives 44.15% of booster gain**, split across `sma_20`, `close_pos_in_range`, `ret_1d`, and `hl_range_pct`. However, in ablation testing, removing Short-Horizon Price (`LOO_NO_SHORT_PRICE`) results in residual IC of $+0.0532$ ($\Delta 	ext{IC} = -0.0055$). Standalone Short Price (`G3_SHORT_PRICE`) achieves IC of $+0.0153$ ($p = 0.4988$, placebo $p = 0.2690$).
2. **Macro Context receives 9.67% of booster gain**, yet it exhibits the primary marginal information contribution within the tested set:
   - Standalone `G8_MACRO_CTX`: IC $= +0.0436$ ($p = 0.0537$, placebo $p = 0.0240$).
   - Ablation `LOO_NO_MACRO_CTX`: IC drops to $+0.0157$ ($\Delta 	ext{IC} = +0.0321$, $\Delta R^2 = +0.2302\%$, placebo $p = 0.2300$).
3. **Forensic Distinction:** Internal split gain reflects how the gradient boosting algorithm partitions feature space during tree construction. It must not be interpreted as evidence of external causal influence.

---

## 10. Base-Rate Control & Macro Context Economic Claims

To ensure scientific rigor, we distinguish three separate claims regarding Macro Context:

- **Claim A — Statistical Association:** Macro Context shows measurable association with the residual target under the specified OOF experiment (standalone IC $= +0.0436$, nominal $p = 0.0537$, placebo empirical $p = 0.0240$).
- **Claim B — Marginal Information Contribution:** Removing Macro Context materially reduces the reference-model residual IC (dropping from $+0.0477$ to $+0.0157$, $\Delta 	ext{IC} = +0.0321$, ablation placebo $p = 0.2300$).
- **Claim C — Economic Usefulness:** Macro Context does **NOT** demonstrate statistically significant outperformance versus the Always Short baseline (HAC $t = -1.87$, $p = 0.0621$). Therefore, Macro Context is **not** economically validated alpha.

| Configuration | % Predicted Short | % Predicted Long | Model Gross Return (bps/day) | Always Short Gross (bps/day) | Difference (Model - Short) | HAC SE (bps) | HAC t-stat | HAC p-value |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `G0_ALL` | 90.7% | 9.3% | +7.24 | +8.04 | -0.79 bps | 1.36 | -0.58 | **0.5591** |
| `G1_PRICE` | 96.8% | 3.2% | +6.88 | +8.04 | -1.15 bps | 0.94 | -1.23 | **0.2202** |
| `G2_CONTEXT` | 92.4% | 7.6% | +6.79 | +8.04 | -1.25 bps | 1.14 | -1.10 | **0.2711** |
| `G3_SHORT_PRICE` | 95.6% | 4.4% | +7.53 | +8.04 | -0.51 bps | 0.99 | -0.51 | **0.6084** |
| `G4_MED_LONG` | 100.0% | 0.0% | +8.04 | +8.04 | 0.00 bps | 0.00 | 0.00 | **1.0000** |
| `G5_VOLATILITY` | 99.0% | 1.0% | +6.78 | +8.04 | -1.26 bps | 0.77 | -1.63 | **0.1039** |
| `G6_DOMESTIC` | 96.1% | 3.9% | +7.55 | +8.04 | -0.49 bps | 0.62 | -0.79 | **0.4321** |
| `G7_GLOBAL_CTX` | 95.8% | 4.2% | +7.71 | +8.04 | -0.33 bps | 0.80 | -0.41 | **0.6836** |
| `G8_MACRO_CTX` | 88.2% | 11.8% | +5.66 | +8.04 | -2.37 bps | 1.27 | -1.87 | **0.0621** |
| `LOO_NO_MACRO` | 95.7% | 4.3% | +7.21 | +8.04 | -0.83 bps | 0.98 | -0.84 | **0.3984** |
| `LOO_NO_MED_LONG` | 91.6% | 8.4% | +9.46 | +8.04 | +1.43 bps | 1.43 | +1.00 | **0.3182** |

### Base-Rate Verdict
The statistical feature-family differences do not translate into demonstrated economic superiority over the unconditional short baseline, and all tested configurations remain negative under the 10 bps diagnostic cost assumption.

---

## 11. Placebo & Permutation Analysis

To establish whether observed correlations could arise by chance, 1,000 synthetic placebo permutations were executed for all 17 major configurations with a frozen random seed (`seed=42`), shuffling the target returns while preserving sample size ($N=1,960$) and prediction structure.

| Configuration | N Sessions | Permutations | Observed Residual IC | Observed p-value | Placebo Mean IC | Placebo Std Dev | Empirical Percentile | Empirical p-value | Interpretation |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `G0_ALL` | 1960 | 1000 | +0.0477 | 0.0346 | -0.0012 | 0.0227 | 98.1% | 0.0190 | Distinguishable from permutation noise |
| `G1_PRICE` | 1960 | 1000 | -0.0101 | 0.6544 | -0.0001 | 0.0234 | 33.6% | 0.6640 | Indistinguishable from permutation noise |
| `G2_CONTEXT` | 1960 | 1000 | +0.0387 | 0.0870 | -0.0012 | 0.0228 | 96.6% | 0.0340 | Distinguishable from permutation noise |
| `G3_SHORT_PRICE` | 1960 | 1000 | +0.0153 | 0.4997 | +0.0004 | 0.0235 | 73.1% | 0.2690 | Indistinguishable from permutation noise |
| `G4_MED_LONG_PRICE` | 1960 | 1000 | -0.0408 | 0.0708 | +0.0011 | 0.0228 | 3.7% | 0.9630 | Indistinguishable from permutation noise |
| `G5_VOLATILITY` | 1960 | 1000 | -0.0117 | 0.6052 | +0.0005 | 0.0225 | 30.4% | 0.6960 | Indistinguishable from permutation noise |
| `G6_DOMESTIC_CTX` | 1960 | 1000 | +0.0111 | 0.6237 | -0.0010 | 0.0227 | 70.7% | 0.2930 | Indistinguishable from permutation noise |
| `G7_GLOBAL_CTX` | 1960 | 1000 | -0.0045 | 0.8423 | -0.0013 | 0.0231 | 44.2% | 0.5580 | Indistinguishable from permutation noise |
| `G8_MACRO_CTX` | 1960 | 1000 | +0.0436 | 0.0539 | +0.0002 | 0.0223 | 97.6% | 0.0240 | Distinguishable from permutation noise |
| `G_CALENDAR` | 1960 | 1000 | +0.0042 | 0.8516 | -0.0000 | 0.0219 | 59.1% | 0.4090 | Indistinguishable from permutation noise |
| `LOO_NO_SHORT_PRICE` | 1960 | 1000 | +0.0532 | 0.0185 | -0.0005 | 0.0224 | 99.2% | 0.0080 | Distinguishable from permutation noise |
| `LOO_NO_MED_LONG_PRICE` | 1960 | 1000 | +0.0680 | 0.0026 | -0.0011 | 0.0228 | 99.9% | 0.0010 | Distinguishable from permutation noise |
| `LOO_NO_VOLATILITY` | 1960 | 1000 | +0.0418 | 0.0641 | -0.0006 | 0.0219 | 96.9% | 0.0310 | Distinguishable from permutation noise |
| `LOO_NO_DOMESTIC_CTX` | 1960 | 1000 | +0.0646 | 0.0042 | -0.0004 | 0.0233 | 99.7% | 0.0030 | Distinguishable from permutation noise |
| `LOO_NO_GLOBAL_CTX` | 1960 | 1000 | +0.0591 | 0.0089 | -0.0007 | 0.0218 | 99.6% | 0.0040 | Distinguishable from permutation noise |
| `LOO_NO_MACRO_CTX` | 1960 | 1000 | +0.0157 | 0.4885 | -0.0010 | 0.0228 | 77.0% | 0.2300 | Indistinguishable from permutation noise |
| `LOO_NO_CALENDAR` | 1960 | 1000 | +0.0595 | 0.0084 | -0.0007 | 0.0218 | 99.6% | 0.0040 | Distinguishable from permutation noise |

---

## 12. Economic Stress Diagnostic

A sign-signal economic diagnostic evaluated daily portfolio performance across four transaction cost scenarios: 0 bps (frictionless), 5 bps, 10 bps, and 20 bps roundtrip per session.

| Configuration | Friction Scenario | Mean Daily Return (bps) | HAC t-stat | HAC p-value | Annualized Return (%) | Annualized Vol (%) | Sharpe Ratio | Max Drawdown (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `G0_ALL` | 0 bps | +7.24 | +3.95 | 0.0001 | +18.8% | 14.2% | +1.32 | -14.5% |
| `G1_PRICE` | 0 bps | +6.88 | +3.95 | 0.0001 | +17.7% | 14.2% | +1.25 | -19.7% |
| `G2_CONTEXT` | 0 bps | +6.79 | +3.78 | 0.0002 | +17.5% | 14.2% | +1.23 | -12.7% |
| `G3_SHORT_PRICE` | 0 bps | +7.53 | +4.38 | 0.0000 | +19.7% | 14.2% | +1.39 | -17.0% |
| `G8_MACRO_CTX` | 0 bps | +5.66 | +3.27 | 0.0011 | +14.2% | 14.2% | +1.00 | -15.3% |
| `LOO_NO_PRICE` | 0 bps | +6.79 | +3.78 | 0.0002 | +17.5% | 14.2% | +1.23 | -12.7% |
| `LOO_NO_CONTEXT` | 0 bps | +6.88 | +3.95 | 0.0001 | +17.7% | 14.2% | +1.25 | -19.7% |
| `LOO_NO_MACRO_CTX` | 0 bps | +7.21 | +4.10 | 0.0000 | +18.7% | 14.2% | +1.32 | -21.6% |
| `G0_ALL` | 5 bps | +2.24 | +1.22 | 0.2212 | +4.8% | 14.2% | +0.33 | -16.9% |
| `G1_PRICE` | 5 bps | +1.88 | +1.08 | 0.2797 | +3.8% | 14.2% | +0.27 | -21.6% |
| `G2_CONTEXT` | 5 bps | +1.79 | +1.00 | 0.3195 | +3.6% | 14.2% | +0.25 | -18.0% |
| `G3_SHORT_PRICE` | 5 bps | +2.53 | +1.47 | 0.1410 | +5.5% | 14.2% | +0.39 | -18.9% |
| `G8_MACRO_CTX` | 5 bps | +0.66 | +0.38 | 0.7008 | +0.7% | 14.2% | +0.05 | -31.9% |
| `LOO_NO_PRICE` | 5 bps | +1.79 | +1.00 | 0.3195 | +3.6% | 14.2% | +0.25 | -18.0% |
| `LOO_NO_CONTEXT` | 5 bps | +1.88 | +1.08 | 0.2797 | +3.8% | 14.2% | +0.27 | -21.6% |
| `LOO_NO_MACRO_CTX` | 5 bps | +2.21 | +1.26 | 0.2089 | +4.7% | 14.2% | +0.33 | -22.8% |
| `G0_ALL` | 10 bps | -2.76 | -1.50 | 0.1326 | -7.7% | 14.2% | -0.54 | -53.6% |
| `G1_PRICE` | 10 bps | -3.12 | -1.79 | 0.0732 | -8.5% | 14.2% | -0.60 | -54.2% |
| `G2_CONTEXT` | 10 bps | -3.21 | -1.79 | 0.0737 | -8.7% | 14.2% | -0.61 | -55.0% |
| `G3_SHORT_PRICE` | 10 bps | -2.47 | -1.44 | 0.1503 | -7.0% | 14.2% | -0.49 | -48.3% |
| `G8_MACRO_CTX` | 10 bps | -4.34 | -2.51 | 0.0122 | -11.3% | 14.2% | -0.79 | -63.9% |
| `LOO_NO_PRICE` | 10 bps | -3.21 | -1.79 | 0.0737 | -8.7% | 14.2% | -0.61 | -55.0% |
| `LOO_NO_CONTEXT` | 10 bps | -3.12 | -1.79 | 0.0732 | -8.5% | 14.2% | -0.60 | -54.2% |
| `LOO_NO_MACRO_CTX` | 10 bps | -2.79 | -1.59 | 0.1128 | -7.7% | 14.2% | -0.54 | -51.2% |
| `G0_ALL` | 20 bps | -12.76 | -6.96 | 0.0000 | -28.2% | 14.2% | -1.99 | -92.7% |
| `G1_PRICE` | 20 bps | -13.12 | -7.54 | 0.0000 | -28.9% | 14.2% | -2.03 | -93.2% |
| `G2_CONTEXT` | 20 bps | -13.21 | -7.36 | 0.0000 | -29.1% | 14.2% | -2.05 | -93.3% |
| `G3_SHORT_PRICE` | 20 bps | -12.47 | -7.26 | 0.0000 | -27.7% | 14.2% | -1.95 | -92.3% |
| `G8_MACRO_CTX` | 20 bps | -14.34 | -8.28 | 0.0000 | -31.0% | 14.2% | -2.18 | -94.6% |
| `LOO_NO_PRICE` | 20 bps | -13.21 | -7.36 | 0.0000 | -29.1% | 14.2% | -2.05 | -93.3% |
| `LOO_NO_CONTEXT` | 20 bps | -13.12 | -7.54 | 0.0000 | -28.9% | 14.2% | -2.03 | -93.2% |
| `LOO_NO_MACRO_CTX` | 20 bps | -12.79 | -7.27 | 0.0000 | -28.3% | 14.2% | -1.99 | -92.7% |

---

## 13. Leakage & Point-in-Time Audit

A comprehensive leakage audit confirmed strict chronological integrity:
1. **Timestamp Cutoff Strictness:** Snapshot B enforces an absolute cutoff of `08:50 IST` on Session $T+1$. All US and European markets observed concluded overnight before 03:00 IST. Zero same-day Indian market data ($T+1$) enters the feature vector.
2. **Embargo Integrity:** The causal embargo ensures that training fold targets do not overlap with validation periods. Training sets terminate strictly at December 31 of Year $k-1$, leaving a minimum 1-day causal separation before the January validation window.
3. **Inner Validation Isolation:** All tree-count selections ($N^*$) were executed strictly on the training fold's historical partition. Zero OOF validation rows were accessed during hyperparameter selection.
4. **Baseline Isolation:** Target baselines $\mu_{\text{train}}$ were computed exclusively from training fold observations.

---

## 14. Terminal Holdout Firewall Audit

The project holdout firewall was verified programmatically before, during, and after experiment execution:
- **Maximum Loaded Date:** `2021-12-31`.
- **Terminal Holdout Boundary:** `2022-01-03` through `2026-09-03` ($N = 1,154$ sessions).
- **Holdout Rows Accessed:** Exactly **0**.
- **Holdout Predictions Emitted:** Exactly **0**.
- **Firewall Status:** **PERMANENTLY SEALED & UNBREACHED**.

---

## 15. Artifact Checksums & Integrity Manifest

The integrity of all 10 Step 8 interim artifacts was verified via SHA-256 cryptographic hashes:

| Artifact Filename | SHA-256 Checksum | Description |
| :--- | :--- | :--- |
| `step8_economic_diagnostic.csv` | `13aead08232aae96af2e57c5c4d7dd6651ecc29d3291a1bce600ca6a3bc64bee` | Sign-signal economic stress test across 0, 5, 10, 20 bps transaction frictions |
| `step8_feature_contribution.csv` | `4d73edd23dd8218813addc13bbb77cd42c533b41564f8357dea6158ab39ffad5` | Model attribution: booster gain, weight, cover across 63 features |
| `step8_feature_group_registry.csv` | `7fd8479a21f61f3d852405dc679e261cd4b1e0c4d741bd42712e06020c78eec0` | Machine-readable 63-feature taxonomy & group membership matrix |
| `step8_feature_group_registry.json` | `695718620348e4fc6e9cc72829a409f03604e42ce86f60aac3f5e5a51a90cefc` | JSON feature metadata, group partitions, and count specifications |
| `step8_fold_results.csv` | `dd283306bac4dc3c017cfadf34c3acd71ff355ec6c3807215a1292769578eb38` | Fold-by-fold metrics across 8 chronological folds for all 19 configs (152 rows) |
| `step8_placebo_results.csv` | `94b6951406065d5a8ee745fa5aef76dd2f0342c8122958aa31bc4353eb944d26` | Placebo permutation test results (1,000 permutations, seed 42) for 17 configs |
| `step8_predictions.csv` | `d5a3c1c8122531a0d0104421cf87a9c957a40a01ff1826936fc4cf52989e3f6a` | 1,960 OOF sessions with fold-local baselines & predictions across all 19 configs |
| `step8_summary.csv` | `6c7043f0c4c909e62bfa0f084e8b270147b79f5adf5e75deec80f6f43b533576` | Consolidated summary table with delta IC, delta R2, FDR p-values, base-rate metrics |
| `step8_temporal_results.csv` | `abc427ca94d66c2ca2053fa69450baf177e4fbfddae1a0c99bfcff983bac25b0` | Metrics partitioned by Block A, Block B, Block C, 2021, and 2017-2019 |

---

## 16. Verification Test Results

The dedicated Step 8 test suite (`tests/test_phase12_step8_feature_information.py`) covers 18 rigorous verification checks plus reconciliation assertions:
- Dedicated tests: 18 / 18 PASSED.
- Full repository test suite: 309 / 309 PASSED (`pytest -q`).

---

## 17. Reconciled Decision Gate

Based on the empirical evidence gathered across 19 pre-registered configurations, 8 walk-forward folds, 3 temporal blocks, 1,000 placebo permutations, and 4 cost stress scenarios, the reconciled formal decision for Phase 12 Step 8 is:

```
==========================================================================================
                     FINAL RESEARCH DECISION: GATE B
             FEATURE INFORMATION STABILITY NOT SUPPORTED
==========================================================================================
```

### Reconciled Justification:
1. **Price-only information does not demonstrate statistically distinguishable residual predictive information** in this OOF experiment (residual IC $-0.0101$, nominal $p = 0.6544$, placebo empirical $p = 0.6640$).
2. **Macro Context shows the strongest marginal statistical association** among the tested families within the specified OOF design (standalone residual IC $+0.0436$, nominal $p = 0.0537$, placebo $p = 0.0240$).
3. **Removing Macro Context materially reduces the reference residual relationship** (residual IC drops from $+0.0477$ to $+0.0157$, $\Delta 	ext{IC} = +0.0321$, $\Delta R^2 = +0.2302\%$, ablation placebo $p = 0.2300$).
4. **Macro Context does not demonstrate statistically significant outperformance versus Always Short** (difference $-2.37$ bps/day, HAC $t = -1.87$, $p = 0.0621$). It cannot be described as economically validated alpha.
5. **The relationship is temporally unstable**, exhibiting near-zero or negative association across 2017–2019 (Block B IC $-0.0284$) and heavy elevation in 2021 across multiple configurations.
6. **Feature ablation cannot establish causal mechanisms**, only predictive dependence and marginal information within the specified model.
7. **No feature family demonstrates stable, economically meaningful incremental predictive value** beyond the unconditional intraday short drift.
8. **No production feature set or live trading strategy is justified.**

---

## 18. Stop Condition & Governance Attestation

In accordance with Section 13 of the forensic reconciliation instructions:

**PHASE 12 STEP 8 IS FORMALLY SEALED AFTER FORENSIC INTERPRETATION CORRECTION.**

**NO PHASE 12 STEP 9 EXECUTION IS AUTHORIZED BY THIS TASK.**
