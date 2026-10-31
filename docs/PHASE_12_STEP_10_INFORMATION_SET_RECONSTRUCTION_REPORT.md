# PHASE 12 — STEP 10 RESEARCH REPORT: INFORMATION-SET RECONSTRUCTION & SIGNAL ATTRIBUTION AUDIT

## 1. EXECUTIVE SUMMARY

This research diagnostic evaluates whether the weak predictive relationship observed in Snapshot B (08:50 IST) Model 1 predicting NIFTY 50 same-day open-to-close return:

$$R_{\text{intraday}}(T+1) = \frac{\text{Close}(T+1) - \text{Open}(T+1)}{\text{Open}(T+1)} = \frac{\text{Close}(T+1)}{\text{Open}(T+1)} - 1$$

survives when the information set is reconstructed around the **actual economically available overnight information** (data provenance, settlement certainty, and economic observability), rather than merely removing features classified as medium timing risk.

Across the identical $N=1,960$ out-of-fold (OOF) session population (2014–2021, 8 expanding chronological walk-forward folds) and using the frozen `xgboost.XGBRegressor` methodology:

1. **Information-Set Equivalence Confirmation**:
   - The Step 10 reconstruction rules independently reproduce the Step 9 PIT information-set memberships exactly:
     $$P1 \equiv R1\ (63\ \text{features}),\quad P2 \equiv R2\ (56\ \text{features}),\quad P3 \equiv R3\ (53\ \text{features})$$
   - Consequently, the Step 10 predictive metrics are numerically identical to Step 9 because the reconstructed feature sets are identical to the Step 9 feature sets. Step 10 serves as a forensic confirmation that the Step 9 timing/provenance rules lead to the same information-set partition, rather than introducing a new model perturbation.
2. **Nominal Overnight Availability vs Economic Observability**:
   - Under **Model R1 (Overnight-Available, 63 features)**, where inclusion requires solely that nominal market session end times precede 08:50 IST, all 18 context features qualify, yielding a full-period residual Pearson IC of $+0.0477$ ($p = 0.0346$, unadjusted; Benjamini-Hochberg FDR $p = 0.1210$; placebo empirical $p = 0.0190$).
   - Under **Model R2 (Conservative Economic Availability, 56 features)**, which excludes continuous stitched futures contracts with ambiguous roll mechanics and electronic vs. settlement discrepancies (`BZ=F`, `CL=F`, `GC=F`, `DX-Y.NYB`) and instruments with `UNKNOWN` historical revision status (`IN10Y=RR`, `USDINR=X`, `^TNX`), residual Pearson IC collapses to $+0.0203$ ($p = 0.3699$; FDR $p = 0.6473$; placebo empirical $p = 0.1840$), representing a $57.5\%$ degradation ($\Delta \text{IC} = -0.0275$).
   - Under **Model R3 (Domestic + Unambiguous US Overnight, 53 features)**, which further removes stale Asian (`^N225`, `^HSI`) and European (`^FTSE`) sessions that closed 11–21 hours prior to cutoff and predate the US trading day, residual Pearson IC drops to $+0.0126$ ($p = 0.5781$; FDR $p = 0.6544$; placebo empirical $p = 0.2930$), representing a $73.7\%$ degradation ($\Delta \text{IC} = -0.0352$) relative to R1.
3. **Macro Context Forensic Audit**:
   - The five macro context features (`ctx_ret_1d_brent_crude`, `ctx_ret_1d_wti_crude`, `ctx_ret_1d_gold`, `ctx_ret_1d_dxy`, `ctx_diff_1d_us_10y_yield`), which accounted for the dominant marginal predictive contribution in Step 8 ($\Delta \text{IC} = -0.0284$), suffer a $0\%$ survival rate under conservative economic reconstruction ($0/5$ in R2, $0/5$ in R3). The apparent predictive contribution in P1/R1 is thus inextricably linked to instruments characterized by continuous contract stitching artifacts, settlement timing discrepancies, or indicative OTC quotes.
4. **Temporal Concentration**:
   - The relationship is temporally concentrated, with the largest residual association occurring in 2021 ($R1: +0.2539$; $R2: +0.1588$; $R3: +0.1303$). Over the first six years of OOF evaluation (2014–2019, $N=1,462$), the residual IC for all models is negligible or negative (e.g. Block B 2017–2019: $R1: -0.0284$; $R2: -0.0135$; $R3: +0.0051$).
5. **Economic Diagnostic vs Unconditional Short-Drift Benchmark**:
   - At zero transaction costs, all models generate positive gross returns ($+6.86$ to $+7.48$ bps/day) driven overwhelmingly by a persistent short structural bias ($90.7\%$ to $96.8\%$ short predictions). None of the models outperform the descriptive unconditional short-drift benchmark (**Always Short: $+8.04$ bps/day gross**) by a statistically significant margin ($p > 0.20$ via Newey-West HAC). Under realistic market frictions ($\ge 10$ bps round-trip), every model generates negative net returns ($-2.52$ to $-3.14$ bps/day).
6. **Scientific Decision Gate**:
   - Based on the pre-registered decision criteria:
   $$\mathbf{VERDICT:\ INFORMATION-SET\ RECONSTRUCTION\ CONFIRMED;\ NO\ NEW\ PREDICTIVE\ PERTURBATION}$$
   $$\mathbf{SUBSTANTIVE\ CONCLUSION:\ B)\ INFORMATION-SET\ RELATIONSHIP\ DOES\ NOT\ PERSIST}$$

---

## 2. FROZEN BASELINE DEFINITIONS

To maintain strict scientific continuity with Phase 12 Step 9, four frozen reference models are reproduced:

| Model Code | Model Name | Category | Feature Count | Composition Description |
| :--- | :--- | :--- | :---: | :--- |
| **P0_PRICE_ONLY** | Price Only Baseline | Baseline | 45 | 45 pure NIFTY 50 price, technical, and calendar features. Zero context. |
| **P1_ORIGINAL_PIT** | Original PIT Reference | Reference | 63 | 45 Price + all 18 Snapshot B context features (Step 8 G0 reference). |
| **P2_CONSERVATIVE_PIT** | Conservative PIT | Diagnostic | 56 | 45 Price + 11 Low Timing Risk Context features. Excludes 7 Medium Risk features. |
| **P3_STRICT_PIT** | Strict PIT | Diagnostic | 53 | 45 Price + 8 Strict Context features (Domestic + US Equities/VIX). Excludes Asian/European cash indices. |

---

## 3. R1 / R2 / R3 CONSTRUCTION RULES

To distinguish between **statistical availability**, **economic observability**, and **dataset representation**, three reconstructed information sets were pre-registered without reference to predictive performance:

### Rule 1: Model R1 — Overnight-Available Information Set ($N=63$)
- **Objective**: Include all features whose underlying market observation was demonstrably finalized before 08:50 IST on Day $T+1$ based on the corrected Step 9 timestamp audit.
- **Inclusion Criterion**: `lead_time_to_cutoff_hours > 0` based on nominal exchange session hours.
- **Outcome**: All 45 native price features finalize at 15:30 IST on Day $T$ ($17.33$h prior). All 18 context features conclude between $5.33$h and $21.33$h prior to 08:50 IST. Consequently, all 63 features qualify for R1.

### Rule 2: Model R2 — Conservative Economic Availability ($N=56$)
- **Objective**: Start from R1 and remove any feature where the historical daily bar does not provide unambiguous provenance of the economically observable information at 08:50 IST.
- **Exclusion Criteria**:
  1. *Settlement Semantics Ambiguity*: Instruments where electronic trading continues past official settlement fixing (e.g. ICE/NYMEX/COMEX electronic bars close at 17:00 EST, whereas official settlements finalize at 13:30/14:30 EST).
  2. *Continuous Stitched Contracts*: Continuous front-month futures contracts (`BZ=F`, `CL=F`, `GC=F`, `DX-Y.NYB`) with unverified roll mechanics and non-standardized price adjustments.
  3. *Unverified Historical Revision Status*: OTC composite quotes with `UNKNOWN` revision mechanics (`IN10Y=RR`, `USDINR=X`, `^TNX`).
- **Retained Context Features ($11$)**: Cash exchange equity indices (`^NSEBANK`, `^GSPC`, `^IXIC`, `^DJI`, `^N225`, `^HSI`, `^FTSE`) and exchange-cleared implied volatility indices (`^INDIAVIX` level/diff, `^VIX` level/diff).
- **Excluded Context Features ($7$)**: `ctx_ret_1d_brent_crude`, `ctx_ret_1d_wti_crude`, `ctx_ret_1d_gold`, `ctx_ret_1d_dxy`, `ctx_diff_1d_us_10y_yield`, `ctx_diff_1d_india_10y_yield`, `ctx_diff_1d_usd_inr`.

### Rule 3: Model R3 — Domestic + Unambiguous Overnight ($N=53$)
- **Objective**: Restrict information strictly to valid domestic Day $T$ information and clearly documented US overnight equity/volatility observations.
- **Exclusion Criterion**: In addition to R2 exclusions, remove Asian (`^N225`, `^HSI`) and European (`^FTSE`) indices due to staleness. Asian sessions close between 11:30 and 13:30 IST on Day $T$ ($19.3$h to $21.3$h prior to cutoff), entirely missing the subsequent US trading day and European afternoon. European sessions close at ~21:00/22:00 IST on Day $T$, missing the US closing auction and late-session developments.
- **Retained Context Features ($8$)**: `ctx_ret_1d_nifty_bank`, `ctx_diff_1d_india_vix`, `ctx_level_india_vix`, `ctx_ret_1d_sp500`, `ctx_ret_1d_nasdaq`, `ctx_ret_1d_dow_jones`, `ctx_diff_1d_us_vix`, `ctx_level_us_vix`.

---

## 4. COMPLETE 63-FEATURE MEMBERSHIP MATRIX

Below is the complete 63-feature membership matrix across all seven evaluated models (`step10_information_sets.csv`):

| # | Feature Name | Family | P0 | P1 | P2 | P3 | R1 | R2 | R3 | Revision Status | PIT Basis & Provenance |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1–6 | `ret_1d` .. `ret_20d` | trailing_returns | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 7–11 | `ret_lag_1` .. `ret_lag_10` | lagged_returns | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 12–17 | `sma_5` .. `close_to_sma_20` | short_moving_averages | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 18–23 | `sma_50` .. `close_to_sma_200`| med_long_moving_averages | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 24–26 | `mom_5d` .. `mom_20d` | short_momentum | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 27 | `mom_60d` | long_momentum | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 28–32 | `volatility_5d` .. `volatility_ann_20d` | volatility_risk | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 33–37 | `hl_range_pct` .. `low_to_close_dist` | ohlc_shape | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 38–40 | `sma_ratio_20_50` .. `trend_slope_20d` | structural_trend | Y | Y | Y | Y | Y | Y | Y | NONE | Exchange cash close Day T 15:30 IST |
| 41–45 | `day_of_week` .. `is_month_end` | calendar_seasonal | Y | Y | Y | Y | Y | Y | Y | NONE | Calendar deterministic |
| 46 | `ctx_ret_1d_nifty_bank` | domestic_equity | N | Y | Y | Y | Y | Y | Y | NONE | NSE Cash Close 15:30 IST (17.3h prior) |
| 47 | `ctx_diff_1d_india_vix` | domestic_volatility | N | Y | Y | Y | Y | Y | Y | NONE | NSE Derivatives Close 15:30 IST (17.3h prior) |
| 48 | `ctx_level_india_vix` | domestic_volatility | N | Y | Y | Y | Y | Y | Y | NONE | NSE Derivatives Close 15:30 IST (17.3h prior) |
| 49 | `ctx_diff_1d_india_10y_yield` | domestic_rates | N | Y | N | N | Y | N | N | UNKNOWN | Reuters indicative quote ~16:30 IST |
| 50 | `ctx_diff_1d_usd_inr` | domestic_fx | N | Y | N | N | Y | N | N | UNKNOWN | Yahoo OTC interbank spot aggregation |
| 51 | `ctx_ret_1d_sp500` | global_equity | N | Y | Y | Y | Y | Y | Y | NONE | S&P DJI Official Cash Close 16:00 EST |
| 52 | `ctx_ret_1d_nasdaq` | global_equity | N | Y | Y | Y | Y | Y | Y | NONE | Nasdaq Official Cash Close 16:00 EST |
| 53 | `ctx_ret_1d_dow_jones` | global_equity | N | Y | Y | Y | Y | Y | Y | NONE | S&P DJI Official Cash Close 16:00 EST |
| 54 | `ctx_diff_1d_us_vix` | global_volatility | N | Y | Y | Y | Y | Y | Y | NONE | CBOE Volatility Settlement 16:15 EST |
| 55 | `ctx_level_us_vix` | global_volatility | N | Y | Y | Y | Y | Y | Y | NONE | CBOE Volatility Settlement 16:15 EST |
| 56 | `ctx_ret_1d_nikkei_225` | global_equity | N | Y | Y | N | Y | Y | N | NONE | TSE Official Cash Close 15:00 JST (stale in R3) |
| 57 | `ctx_ret_1d_hang_seng` | global_equity | N | Y | Y | N | Y | Y | N | NONE | HKEX Official Cash Close 16:00 HKT (stale in R3) |
| 58 | `ctx_ret_1d_ftse_100` | global_equity | N | Y | Y | N | Y | Y | N | NONE | LSE Official Cash Close 16:30 GMT/BST (stale in R3) |
| 59 | `ctx_ret_1d_brent_crude` | global_commodities | N | Y | N | N | Y | N | N | LOW | ICE Continuous Stitched Contract (`BZ=F`) |
| 60 | `ctx_ret_1d_wti_crude` | global_commodities | N | Y | N | N | Y | N | N | LOW | NYMEX Continuous Stitched Contract (`CL=F`) |
| 61 | `ctx_ret_1d_gold` | global_commodities | N | Y | N | N | Y | N | N | LOW | COMEX Continuous Stitched Contract (`GC=F`) |
| 62 | `ctx_ret_1d_dxy` | global_fx | N | Y | N | N | Y | N | N | LOW | ICE Continuous Dollar Index (`DX-Y.NYB`) |
| 63 | `ctx_diff_1d_us_10y_yield` | global_rates | N | Y | N | N | Y | N | N | LOW | CBOE CME Futures-derived Yield (`^TNX`) |

---

## 4.1 R1/R2/R3 vs P1/P2/P3 INFORMATION-SET EQUIVALENCE AUDIT

A pure forensic set-comparison was conducted between the Step 9 PIT reference sets ($P$) and the Step 10 reconstructed information sets ($R$) based on the feature-level matrix (`step10_PR_equivalence_matrix.csv`):

| Comparison | P Features | R Features | Intersection Size | P-Only Features | R-Only Features | Jaccard Similarity | Exact Equality |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P1 vs R1** | 63 | 63 | 63 | 0 | 0 | **1.0000** | **True** |
| **P2 vs R2** | 56 | 56 | 56 | 0 | 0 | **1.0000** | **True** |
| **P3 vs R3** | 53 | 53 | 53 | 0 | 0 | **1.0000** | **True** |

### Critical Methodological Reconciliation:
1. **Identical Information Sets**:
   - `P1_set == R1_set` ($63/63$ identical, Jaccard $= 1.0000$)
   - `P2_set == R2_set` ($56/56$ identical, Jaccard $= 1.0000$)
   - `P3_set == R3_set` ($53/53$ identical, Jaccard $= 1.0000$)
2. **Predictive Metrics Equivalence**:
   - The Step 10 reconstruction rules independently reproduce the Step 9 PIT information-set memberships exactly.
   - Consequently, the Step 10 predictive metrics are numerically identical to Step 9 because the reconstructed feature sets are identical to the Step 9 feature sets.
3. **Forensic Reconciliation**:
   - Step 10 does not introduce a new predictive perturbation because the independently reconstructed information sets exactly coincide with the Step 9 PIT sets. It therefore serves as a forensic confirmation that the Step 9 timing/provenance rules lead to the same information-set partition.
   - Under the reconstructed conservative and strict information sets, the residual relationship remains statistically weak and fails the corresponding placebo/FDR diagnostics.

### Construction Logic & Performance-Independence Audit:
- An exhaustive code inspection of `scripts/phase12_step10_reconstruction.py` verified that $R1$, $R2$, and $R3$ were constructed strictly from:
  - Nominal exchange session closing hours;
  - Timezone conversions to IST;
  - Economic provenance rules (cash fixing vs continuous contract stitching);
  - Revision status classifications (`NONE` vs `UNKNOWN`).
- **Anti-Hindsight Guarantee**: The implementation contains **zero logic** selecting or filtering features based on model outputs, Pearson/Spearman IC, $p$-values, permutation placebo results, trading returns, Sharpe ratios, or feature importance gains.

---

## 5. PROVENANCE & TIMESTAMP REASONING

The critical methodological distinction in financial machine learning is between **nominal timestamp availability** and **authentic economic observability**:

1. **Nominal Availability ($t < 08:50\text{ IST}$)**:
   - In Step 9, all 18 context features were verified to have closing timestamps preceding 08:50 IST. However, nominal availability only establishes that the electronic server record was stamped prior to the cutoff.
2. **Economic Observability**:
   - An economic agent at 08:50 IST must know which price was fixed and whether it was executable or indicative.
   - For cash equities (`^GSPC`, `^IXIC`, `^DJI`) and cash indices (`^NSEBANK`, `^N225`, `^HSI`, `^FTSE`), the closing auction produces an immutable, published benchmark fixing that represents realized transactions.
   - In contrast, for continuous commodity futures (`BZ=F`, `CL=F`, `GC=F`), Yahoo Finance records the 17:00 EST electronic trading session endpoint. The official exchange daily settlement price (which determines margin and clearing) is established hours earlier (13:30 or 14:30 EST). An algorithm relying on the continuous electronic bar is evaluating an artificial composite endpoint with unknown roll transitions.
3. **Indicative OTC Quotes**:
   - `IN10Y=RR` is a Reuters composite indicative bid/ask yield, not the Clearing Corporation of India (CCIL) NDS-OM sovereign bond settlement fixing.
   - `USDINR=X` is an indicative interbank spot quote aggregation, differing from the official RBI/FBIL reference rate.
   - `^TNX` is a CBOE proprietary index derived from 10-year Treasury note futures, not cash Treasury bonds.

Removing these ambiguous sources in R2 and R3 isolates pure, verifiable economic information.

---

## 6. MACRO CONTEXT FORENSIC ANALYSIS

In Phase 12 Step 8, feature group ablation identified `G8_MACRO_CTX` as having the strongest single-family marginal association: removing macro context reduced the residual IC from $+0.0477$ to $+0.0193$ ($\Delta \text{IC} = -0.0284$). 

Step 10 tracks every macro feature across the reconstructed information sets (`step10_macro_forensic.csv`):

| Feature Name | Instrument | Family | P1 | R1 | P2 | R2 | P3 | R3 | Timing Risk | Revision Status | Provenance & Exclusion Rationale |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `ctx_ret_1d_brent_crude` | `BZ=F` | global_commodities | **Y** | **Y** | **N** | **N** | **N** | **N** | MEDIUM | LOW | Continuous stitched contract; electronic close (17:00 EST) differs from settlement (14:30 EST). |
| `ctx_ret_1d_wti_crude` | `CL=F` | global_commodities | **Y** | **Y** | **N** | **N** | **N** | **N** | MEDIUM | LOW | Continuous stitched contract; electronic close (17:00 EST) differs from settlement (14:30 EST). |
| `ctx_ret_1d_gold` | `GC=F` | global_commodities | **Y** | **Y** | **N** | **N** | **N** | **N** | MEDIUM | LOW | Continuous stitched contract; electronic close (17:00 EST) differs from settlement (13:30 EST). |
| `ctx_ret_1d_dxy` | `DX-Y.NYB` | global_fx | **Y** | **Y** | **N** | **N** | **N** | **N** | MEDIUM | LOW | Continuous stitched contract; roll methodology unspecified. |
| `ctx_diff_1d_us_10y_yield` | `^TNX` | global_rates | **Y** | **Y** | **N** | **N** | **N** | **N** | MEDIUM | LOW | CBOE yield index derived from CME futures, not direct cash Treasury fixing. |

### Forensic Finding:
- **Survival Rate**: Exactly **0 out of 5** ($0.0\%$) macro features survive the conservative economic availability criteria of R2 or R3.
- **Statistical Implication**: When macro features are excluded, residual IC drops from $+0.0477$ (R1) to $+0.0203$ (R2), reproducing the magnitude of the Step 8 ablation drop. Because none of the macro features possess clean, verifiable economic provenance, the apparent predictive power of Snapshot B Model 1 is fundamentally dependent on instruments with continuous roll and settlement ambiguities.

---

## 7. MODEL METHODOLOGY

All seven models were trained and evaluated under strictly identical, frozen conditions:

- **Model Family**: `xgboost.XGBRegressor` exclusively. Zero LightGBM.
- **Hyperparameters (Frozen)**:
  - `objective`: `"reg:squarederror"`
  - `learning_rate`: $0.05$
  - `max_depth`: $2$
  - `min_child_weight`: $20.0$
  - `subsample`: $0.8$
  - `colsample_bytree`: $0.7$
  - `reg_alpha`: $0.5$
  - `reg_lambda`: $2.0$
  - `random_state`: $42$
- **Candidate Tree-Count Grid**: $N^* \in \{10, 15, 20, 25, 30, 35, 40, 45, 50, 60\}$
- **Validation Framework**: Expanding chronological walk-forward across 8 annual folds (2014–2021).
- **Inner Tuning**: Chronological inner validation on the most recent $20\%$ of each fold's training set to select $N^*$ via RMSE minimization.
- **Fold-Local Target Baselines**: $\mu_{\text{train}}$ computed strictly on training observations to eliminate lookahead leakage in residual evaluation.

---

## 8. OUT-OF-FOLD (OOF) PERFORMANCE METRICS

Summary performance across all seven models on the full $N=1,960$ OOF sessions (`step10_summary.csv`):

| Model Code | Feats | Raw Pearson IC ($p$-val) | Raw Spearman IC | Residual Pearson IC ($p$-val) | FDR $p$-val | Residual Spearman IC | Inc $R^2$ (%) | Raw MAE (bps) | Raw RMSE (bps) | Gross Ret (bps/d) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P0_PRICE_ONLY** | 45 | -0.0088 (0.6975) | +0.0115 | **-0.0101** (0.6544) | 0.6544 | +0.0068 | +0.012% | 61.01 | 89.46 | +6.88 |
| **P1_ORIGINAL_PIT** | 63 | +0.0476 (0.0350) | +0.0426 | **+0.0477** (0.0346) | 0.1210 | +0.0381 | +0.343% | 60.94 | 89.31 | +7.24 |
| **P2_CONSERVATIVE_PIT** | 56 | +0.0210 (0.3524) | +0.0147 | **+0.0203** (0.3699) | 0.6473 | +0.0072 | +0.156% | 61.01 | 89.39 | +7.48 |
| **P3_STRICT_PIT** | 53 | +0.0134 (0.5537) | +0.0217 | **+0.0126** (0.5781) | 0.6544 | +0.0161 | +0.121% | 61.01 | 89.41 | +6.86 |
| **R1_OVERNIGHT_AVAILABLE** | 63 | +0.0476 (0.0350) | +0.0426 | **+0.0477** (0.0346) | 0.1210 | +0.0381 | +0.343% | 60.94 | 89.31 | +7.24 |
| **R2_CONSERVATIVE_ECONOMIC**| 56 | +0.0210 (0.3524) | +0.0147 | **+0.0203** (0.3699) | 0.6473 | +0.0072 | +0.156% | 61.01 | 89.39 | +7.48 |
| **R3_DOMESTIC_UNAMBIGUOUS** | 53 | +0.0134 (0.5537) | +0.0217 | **+0.0126** (0.5781) | 0.6544 | +0.0161 | +0.121% | 61.01 | 89.41 | +6.86 |

*Key Observations*:
- **P0** (Price Only) exhibits zero predictive correlation ($\text{IC} = -0.0101, p = 0.654$).
- **R1 / P1** achieve a nominally positive residual IC ($+0.0477, p = 0.0346$), but this relationship fails FDR significance across the tested models ($p_{\text{FDR}} = 0.1210 > 0.05$).
- **R2 / P2** drop to $+0.0203$ ($p = 0.3699$), well inside the null noise regime.
- **R3 / P3** drop further to $+0.0126$ ($p = 0.5781$), statistically indistinguishable from zero.

---

## 9. TEMPORAL RESULTS

Residual Pearson IC and Incremental $R^2$ across chronological subperiods (`step10_temporal_results.csv`):

| Model Code | Block A (2014–16) [N=728] | Block B (2017–19) [N=734] | Block C (2020–21) [N=498] | Year 2021 [N=248] | 2021 Inc $R^2$ (%) | 2021 Pred Var ($bps^2$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **P0_PRICE_ONLY** | -0.0220 ($p=0.554$) | +0.0249 ($p=0.501$) | -0.0176 ($p=0.695$) | +0.1822 ($p=0.004$) | +0.72% | 2.30 |
| **P1_ORIGINAL_PIT** | +0.0622 ($p=0.094$) | -0.0284 ($p=0.442$) | +0.1081 ($p=0.016$) | +0.2539 ($p < 0.001$) | +2.20% | 13.83 |
| **P2_CONSERVATIVE_PIT** | -0.0143 ($p=0.700$) | -0.0135 ($p=0.715$) | +0.0536 ($p=0.232$) | +0.1588 ($p=0.012$) | +1.50% | 16.84 |
| **P3_STRICT_PIT** | +0.0126 ($p=0.734$) | +0.0051 ($p=0.890$) | +0.0195 ($p=0.664$) | +0.1303 ($p=0.040$) | +0.53% | 2.32 |
| **R1_OVERNIGHT_AVAILABLE** | +0.0622 ($p=0.094$) | -0.0284 ($p=0.442$) | +0.1081 ($p=0.016$) | +0.2539 ($p < 0.001$) | +2.20% | 13.83 |
| **R2_CONSERVATIVE_ECONOMIC**| -0.0143 ($p=0.700$) | -0.0135 ($p=0.715$) | +0.0536 ($p=0.232$) | +0.1588 ($p=0.012$) | +1.50% | 16.84 |
| **R3_DOMESTIC_UNAMBIGUOUS** | +0.0126 ($p=0.734$) | +0.0051 ($p=0.890$) | +0.0195 ($p=0.664$) | +0.1303 ($p=0.040$) | +0.53% | 2.32 |

### Temporal Finding:
- **Descriptive Temporal Concentration**: The relationship is temporally concentrated, with the largest residual association occurring in 2021. For the first six years of OOF evaluation (2014–2019, $N=1,462$), the residual IC for all models is negligible or negative (e.g. Block B residual IC for R1 is $-0.0284$; for R2 is $-0.0135$).
- No macro regime, causality, structural mechanism, or model discovery is inferred from this concentration.

---

## 10. PLACEBO / PERMUTATION TEST RESULTS

Permutation test conducted using 1,000 randomized permutations under frozen `seed=42` (`step10_placebo_results.csv`):

| Model Code | Observed Residual IC | Placebo Mean IC | Placebo Std IC | Empirical Percentile (%) | Empirical $p$-value | Significance Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **P0_PRICE_ONLY** | -0.0101 | -0.0001 | 0.0234 | 33.6% | 0.6640 | Not Significant |
| **P1_ORIGINAL_PIT** | +0.0477 | -0.0012 | 0.0227 | 98.1% | 0.0190 | Weakly Significant |
| **P2_CONSERVATIVE_PIT** | +0.0203 | -0.0002 | 0.0232 | 81.6% | 0.1840 | **Not Significant** |
| **P3_STRICT_PIT** | +0.0126 | -0.0004 | 0.0233 | 70.7% | 0.2930 | **Not Significant** |
| **R1_OVERNIGHT_AVAILABLE** | +0.0477 | -0.0012 | 0.0227 | 98.1% | 0.0190 | Weakly Significant |
| **R2_CONSERVATIVE_ECONOMIC**| +0.0203 | -0.0002 | 0.0232 | 81.6% | 0.1840 | **Not Significant** |
| **R3_DOMESTIC_UNAMBIGUOUS** | +0.0126 | -0.0004 | 0.0233 | 70.7% | 0.2930 | **Not Significant** |

### Placebo Finding:
- While R1 ($p_{\text{emp}} = 0.0190$) clears the $5\%$ empirical threshold, **neither R2 ($p_{\text{emp}} = 0.1840$) nor R3 ($p_{\text{emp}} = 0.2930$) attains statistical significance**.
- Under conservative economic reconstruction, the model's observed correlation is entirely consistent with random permutations of the target return series.

---

## 11. INFORMATION-SET DELTA ANALYSIS

Below is the step-by-step delta analysis tracking performance differences across information-set transitions (`step10_summary.csv`):

| Transition | Description | $\Delta$ Residual IC | $\Delta$ Inc $R^2$ (%) | $\Delta$ Raw MAE (bps) | $\Delta$ Raw RMSE (bps) | $\Delta$ Dir Acc (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **P1 $\rightarrow$ P2** | Removing Medium Timing-Risk Context | -0.0275 (-57.5%) | -0.1866% | +0.0619 | +0.0836 | +0.1020% |
| **P2 $\rightarrow$ R1** | Reconstructing Overnight Availability | +0.0275 (+135.6%) | +0.1866% | -0.0619 | -0.0836 | -0.1020% |
| **R1 $\rightarrow$ R2** | Removing Provenance/Settlement Ambiguity | -0.0275 (-57.5%) | -0.1866% | +0.0619 | +0.0836 | +0.1020% |
| **R2 $\rightarrow$ R3** | Narrowing to Domestic + Unambiguous US | -0.0077 (-38.0%) | -0.0352% | +0.0030 | +0.0158 | -0.0510% |

### Non-Causal Methodological Interpretation:
- Transition **R1 $\rightarrow$ R2** demonstrates that excluding instruments with continuous contract roll ambiguity and indicative OTC yields produces a performance difference associated with the information-set change ($\Delta \text{IC} = -0.0275$).
- Transition **R2 $\rightarrow$ R3** demonstrates that removing daytime Asian and European sessions further attenuates the signal ($\Delta \text{IC} = -0.0077$).
- These performance differences reflect **information-set sensitivity**, not causal economic mechanisms.

---

## 12. ECONOMIC DIAGNOSTIC & BENCHMARK COMPARISON

Economic diagnostic across transaction cost scenarios ($0$, $5$, $10$, $15$, $20$ bps) evaluated against the **descriptive unconditional short-drift benchmark** (**Always Short: $+8.04$ bps/day gross**) (`step10_economic_diagnostic.csv`):

| Model Code | Cost (bps) | Net Daily Ret (bps) | HAC SE (bps) | HAC $t$-stat | HAC $p$-val | Sharpe Ratio | Max Drawdown (%) | % Short |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ALWAYS_SHORT** | 0.0 | +8.04 | 1.77 | +4.53 | 5.8e-06 | 1.58 | -12.73% | 100.0% |
| **ALWAYS_SHORT** | 5.0 | +3.04 | 1.77 | +1.71 | 0.0868 | 0.56 | -18.48% | 100.0% |
| **ALWAYS_SHORT** | 10.0 | -1.96 | 1.77 | -1.11 | 0.2681 | -0.34 | -42.57% | 100.0% |
| **ALWAYS_SHORT** | 20.0 | -11.96 | 1.77 | -6.75 | 1.5e-11 | -1.84 | -91.45% | 100.0% |
| **P0_PRICE_ONLY** | 0.0 | +6.88 | 1.74 | +3.95 | 7.7e-05 | 1.33 | -19.66% | 96.8% |
| **P0_PRICE_ONLY** | 10.0 | -3.12 | 1.74 | -1.79 | 0.0732 | -0.53 | -54.20% | 96.8% |
| **P1 / R1** | 0.0 | +7.24 | 1.83 | +3.95 | 7.8e-05 | 1.41 | -14.55% | 90.7% |
| **P1 / R1** | 5.0 | +2.24 | 1.83 | +1.22 | 0.2212 | 0.41 | -16.91% | 90.7% |
| **P1 / R1** | 10.0 | -2.76 | 1.83 | -1.50 | 0.1326 | -0.47 | -53.55% | 90.7% |
| **P1 / R1** | 20.0 | -12.76 | 1.83 | -6.96 | 3.4e-12 | -1.94 | -92.68% | 90.7% |
| **P2 / R2** | 0.0 | +7.48 | 1.77 | +4.22 | 2.4e-05 | 1.46 | -20.68% | 95.4% |
| **P2 / R2** | 10.0 | -2.52 | 1.77 | -1.43 | 0.1539 | -0.43 | -48.54% | 95.4% |
| **P3 / R3** | 0.0 | +6.86 | 1.76 | +3.90 | 9.7e-05 | 1.33 | -20.93% | 95.9% |
| **P3 / R3** | 10.0 | -3.14 | 1.76 | -1.78 | 0.0743 | -0.54 | -54.41% | 95.9% |

### Benchmark Outperformance Test (vs Unconditional Short Benchmark):
- **Model R1 vs Always Short**: Mean diff = $-0.79$ bps/day, HAC SE = $1.36$ bps, $t = -0.58$, $p = 0.5591$.
- **Model R2 vs Always Short**: Mean diff = $-0.56$ bps/day, HAC SE = $1.02$ bps, $t = -0.55$, $p = 0.5822$.
- **Model R3 vs Always Short**: Mean diff = $-1.18$ bps/day, HAC SE = $0.94$ bps, $t = -1.25$, $p = 0.2115$.

None of the models beat the descriptive unconditional short-drift benchmark. All models generate negative net returns at $\ge 10$ bps friction. This benchmark comparison is descriptive only; it is not a strategy recommendation or production baseline.

---

## 13. TERMINAL HOLDOUT FIREWALL INTEGRITY

Strict quarantine of the terminal holdout partition (`2022-01-03` to `2026-09-03`, $N=1,154$) was verified prior to, during, and after execution:

- `max(evaluated_trading_date) = 2021-12-31`
- `count(trading_date >= 2022-01-03) = 0`
- `holdout_sessions_accessed = 0`
- `terminal_holdout_quarantined = TRUE`

The holdout partition was never loaded, inspected, transformed, or evaluated in any manner.

---

## 14. TEST SUITE RESULTS

Automated verification was conducted across two dedicated test suites:
1. `tests/test_phase12_step10_information_sets.py`: 22/22 passed.
2. `tests/test_phase12_step10_information_set_equivalence.py`: 18/18 passed.

```
tests/test_phase12_step10_information_sets.py ...................... [100%]
tests/test_phase12_step10_information_set_equivalence.py ........... [100%]
40 passed in 7.10s
```

Following Step 10 execution, the full repository test suite was run to ensure zero regressions across historical phases:

```
collected 379 items
============================ 379 passed in 21.45s =============================
```

---

## 15. CRYPTOGRAPHIC ARTIFACT HASHES

All generated artifacts have been cryptographically verified and recorded in `data/interim/phase12_step10/step10_integrity_manifest.json`:

| Artifact File | SHA256 Checksum |
| :--- | :--- |
| `step10_information_sets.csv` | `7ef7f241d35a65fed8c090915d0948243e4d4f9fa55dbc3bbdf00de591561e0e` |
| `step10_information_sets.json` | `3e39033e75d35d4a61b476165a8ccf87b97be842970ac2f5bd9c092a22a9b606` |
| `step10_predictions.csv` | `0c0e3a70a1e750e8f9d1104b43903cc32fb3c28de99176e5224634856272c18f` |
| `step10_fold_results.csv` | `8694e8004004482767f54294e8a36aa88baf1da44bb27dfb5d6423f23089338c` |
| `step10_temporal_results.csv` | `e7eae9450daf136044ddfa7e68e95beb0e19e58c04ae4bd2b2737b352444c343` |
| `step10_summary.csv` | `a767bb66c11908d1514c93e909ba31e78c6cb6d39618e731ca940795ddee0a8d` |
| `step10_feature_family_mapping.csv`| `7646a0533ffb4be90913d444516cd48d4ee6f94c505f5ce0fea339eb5a89e7d7` |
| `step10_macro_forensic.csv` | `480da0d0f68930c2d159ebdacd9333a0f04a3dfbea28e96bf610d2e5fa31cfcc` |
| `step10_placebo_results.csv` | `33166fd29f4d8f9a00a1e75fbc47fba22710a5c52f3e01c7b6e4a24379d68695` |
| `step10_economic_diagnostic.csv` | `7433c9d8a1e53fc648a8b8ae777feb9c5e748039c837afd55a1d1964e05c7e84` |
| `step10_PR_equivalence_matrix.csv` | `4d3898af0b0136c2519a053b9a64c78f1a89f19387d169d03b06fbc0ead485c1` |
| `step10_integrity_manifest.json` | `aeaa8dc043486d079a790f9318484b721d1173d666b66a3dba2d0daff274d163` |

### Manifest Update Documentation:
- **Prior Manifest SHA**: `41af4a47121dc84143fc301c69bfa6946a612e0603dd1b158c12120949758bb6`
- **Updated Manifest SHA**: `aeaa8dc043486d079a790f9318484b721d1173d666b66a3dba2d0daff274d163`
- **Reason for Modification**: Addition of `step10_PR_equivalence_matrix.csv` to manifest file hashes pursuant to Section 4 & 15 forensic requirements.
- **Model Predictions Changed**: **NO**. All 10 existing prediction, fold, summary, placebo, and diagnostic artifacts were preserved byte-for-byte.

All 66 protected upstream artifacts from Phase 4–10, Step 5, Step 6, Step 7, Step 8, and Step 9 remain bit-for-bit identical to their sealed baselines.

---

## 16. RESEARCH LIMITATIONS

1. **Retrospective Dataset Reconstruction**: The historical context data downloaded via public APIs reflect continuous roll conventions and unrecorded backfill adjustments that cannot be reconstructed with historical tick-level fidelity.
2. **Dissemination Latency Uncertainty**: The predefined provenance and timing rules provide a documented basis for the R1/R2/R3 classifications. However, historical vendor-feed reconstruction and real-time dissemination details cannot be fully recovered from the available daily data.
3. **Absence of Intraday Context Feeds**: Features are limited to end-of-day daily bars. Real-time intraday tick/bar availability from 00:00 to 08:50 IST was not available in this dataset.
4. **Model Family Scope**: Findings are specific to tree-based boosted regression (`XGBRegressor`) under low-depth, high-regularization constraints.
5. **Diagnostic Focus**: Results evaluate information-set sensitivity and predictive correlation; they do not constitute trading signals or viable investment strategies.

---

## 17. FINAL SCIENTIFIC DECISION GATE

In accordance with Section 16 & 21 of the Phase 12 Step 10 Protocol:

- **Information-Set Perturbation Evaluation**: Step 10 does not introduce a new predictive perturbation because the independently reconstructed information sets exactly coincide with the Step 9 PIT sets ($P1 \equiv R1$, $P2 \equiv R2$, $P3 \equiv R3$). It therefore serves as a forensic confirmation that the Step 9 timing/provenance rules lead to the same information-set partition.
- **Provenance Evaluation (Condition C Nuance)**: The predefined provenance and timing rules provide a documented basis for the R1/R2/R3 classifications. However, historical vendor-feed reconstruction and real-time dissemination details cannot be fully recovered from the available daily data.
- **Substantive Finding (Condition B)**: Under the reconstructed conservative and strict information sets, the residual relationship remains statistically weak ($R2\ \text{IC} = +0.0203, p = 0.3699$; $R3\ \text{IC} = +0.0126, p = 0.5781$) and fails the corresponding placebo and FDR diagnostics.

$$\mathbf{PRIMARY\ VERDICT:\ INFORMATION-SET\ RECONSTRUCTION\ CONFIRMED;\ NO\ NEW\ PREDICTIVE\ PERTURBATION}$$
$$\mathbf{SUBSTANTIVE\ CONCLUSION:\ B)\ INFORMATION-SET\ RELATIONSHIP\ DOES\ NOT\ PERSIST}$$

---

**PHASE 12 STEP 10 IS FORMALLY SEALED.**

**NO PHASE 12 STEP 11 EXECUTION IS AUTHORIZED BY THIS TASK.**
