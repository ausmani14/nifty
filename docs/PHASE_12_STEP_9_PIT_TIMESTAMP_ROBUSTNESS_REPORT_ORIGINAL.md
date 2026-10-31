# PHASE 12 — STEP 9 RESEARCH REPORT

## Point-in-Time Availability, Timestamp Alignment & Context-Feature Robustness Audit

> [!IMPORTANT]
> **RESEARCH & FORENSIC AUDIT ONLY**
> This experiment is an immutable diagnostic audit designed to verify whether the weak predictive relationship identified in Snapshot B (08:50 IST) Model 1 survives rigorous point-in-time (PIT) availability, market-session timing, and information cutoff scrutiny. It does NOT constitute a live trading strategy, production pipeline, or deployment recommendation.
>
> **GOVERNANCE INTEGRITY VERIFIED**:
> - Terminal Holdout (`2022-01-03` to `2026-09-03`, $N=1,154$) remained strictly quarantined (zero rows loaded, accessed, or evaluated).
> - All 53 upstream artifacts across Phase 4–10, Step 5, Step 6, Step 7, and Step 8 were cryptographically verified and preserved byte-for-byte.
> - Evaluation population: Exactly $N=1,960$ OOF sessions (2014–2021) across 8 chronological walk-forward folds.
> - Zero News, Zero Volume, Zero Flow proxy features.

---

## 1. Executive Summary

Phase 12 Step 8 demonstrated that the weak statistical association observed in Snapshot B Model 1 was almost exclusively concentrated in the **Macro Context** feature family (`ctx_ret_1d_brent_crude`, `ctx_ret_1d_wti_crude`, `ctx_ret_1d_gold`, `ctx_ret_1d_dxy`, `ctx_diff_1d_us_10y_yield`). Removing this family collapsed residual Pearson IC from $+0.0477$ ($p = 0.0346$) down to $+0.0157$ ($p = 0.4885$, placebo $p = 0.2300$).

Step 9 subjected all 18 market context features to an exhaustive point-in-time availability and timestamp alignment audit. The investigation revealed a decisive structural finding:
1. **Timing Risk Dichotomy**: 11 features represent premier exchange-calculated cash equity/volatility index closes (e.g., S&P 500, Nasdaq, Dow Jones, CBOE VIX, NIFTY Bank, India VIX, Nikkei 225, Hang Seng, FTSE 100). These indices finalize between 5.8 and 21.0 hours before the 08:50 IST prediction cutoff and carry **LOW TIMING RISK**.
2. **Medium Timing Risk in Macro Variables**: The remaining 7 features—including all 5 Macro Context features (Brent, WTI, Gold, DXY, US 10Y) as well as USD/INR and India 10Y—rely on continuous front-month futures contracts, electronic bar endpoints rather than exchange settlement fixings, or OTC indicative composite quotes.
3. **Decisive Empirical Result**:
   - Under **Model P1** (Original PIT, 63 features): Residual Pearson IC is $+0.0477$ ($p = 0.0346$, placebo $p = 0.0190$, incremental $R^2 = +0.3425\%$).
   - Under **Model P2** (Conservative PIT, 56 features; removing all 7 MEDIUM RISK features): Residual Pearson IC drops to **$+0.0203$** ($p = 0.3699$, placebo $p = 0.1840$, incremental $R^2 = +0.1559\%$). The relationship loses all statistical significance.
   - Under **Model P3** (Strict PIT, 53 features; retaining only unambiguous domestic and US overnight equity/VIX indices): Residual Pearson IC collapses to **$+0.0126$** ($p = 0.5781$, placebo $p = 0.2930$, incremental $R^2 = +0.1207\%$), statistically indistinguishable from zero and nearly identical to Price-Only (**Model P0**: $-0.0101$, $p = 0.6544$).

**Scientific Conclusion**: The observed predictive relationship does **NOT** survive conservative point-in-time treatment. The apparent edge is driven entirely by commodity futures and yield index features that possess settlement ambiguity, continuous contract roll conventions, or unverified OTC aggregation.

---

## 2. Full 18-Feature Point-in-Time Availability Matrix

Every context feature was independently audited across source exchange, native timezone, observation schedule, availability lead time, and timing risk classification prior to running any model experiments.

| Feature Name | Feature Family | Source Symbol | Native Timezone | Session Description | Nominal Bar End | Assumed Availability (IST) | Lead Time to 08:50 IST | Timing Risk | Revision Risk | Treatment |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ctx_ret_1d_nifty_bank` | domestic_equity | `^NSEBANK` | Asia/Kolkata | Domestic Cash (09:15-15:30 IST) | 15:30 IST | 15:30 IST (Day T) | 17.3 hours | **LOW RISK** | NONE | VALID |
| `ctx_diff_1d_india_vix` | domestic_volatility | `^INDIAVIX` | Asia/Kolkata | Domestic Derivatives (09:15-15:30 IST) | 15:30 IST | 15:30 IST (Day T) | 17.3 hours | **LOW RISK** | NONE | VALID |
| `ctx_level_india_vix` | domestic_volatility | `^INDIAVIX` | Asia/Kolkata | Domestic Derivatives (09:15-15:30 IST) | 15:30 IST | 15:30 IST (Day T) | 17.3 hours | **LOW RISK** | NONE | VALID |
| `ctx_diff_1d_india_10y_yield` | domestic_rates | `IN10Y=RR` | Asia/Kolkata | OTC Bond Trading (09:00-17:00 IST) | 16:30 IST | 16:45 IST (Day T) | 16.1 hours | **MEDIUM RISK** | LOW | CONDITIONAL |
| `ctx_diff_1d_usd_inr` | domestic_fx | `USDINR=X` | Asia/Kolkata | OTC Spot FX (~09:00-15:30 IST) | 15:30 IST | 15:30 IST (Day T) | 17.3 hours | **MEDIUM RISK** | LOW | CONDITIONAL |
| `ctx_ret_1d_sp500` | global_equity | `^GSPC` | America/New_York | US Cash Regular (09:30-16:00 EST) | 16:00 EST | 02:00 / 03:00 IST (Day T+1) | 5.8–6.8 hours | **LOW RISK** | NONE | VALID |
| `ctx_ret_1d_nasdaq` | global_equity | `^IXIC` | America/New_York | US Cash Regular (09:30-16:00 EST) | 16:00 EST | 02:00 / 03:00 IST (Day T+1) | 5.8–6.8 hours | **LOW RISK** | NONE | VALID |
| `ctx_ret_1d_dow_jones` | global_equity | `^DJI` | America/New_York | US Cash Regular (09:30-16:00 EST) | 16:00 EST | 02:00 / 03:00 IST (Day T+1) | 5.8–6.8 hours | **LOW RISK** | NONE | VALID |
| `ctx_diff_1d_us_vix` | global_volatility | `^VIX` | America/New_York | US Options Close (09:30-16:15 EST) | 16:15 EST | 02:00 / 03:00 IST (Day T+1) | 5.8–6.8 hours | **LOW RISK** | NONE | VALID |
| `ctx_level_us_vix` | global_volatility | `^VIX` | America/New_York | US Options Close (09:30-16:15 EST) | 16:15 EST | 02:00 / 03:00 IST (Day T+1) | 5.8–6.8 hours | **LOW RISK** | NONE | VALID |
| `ctx_ret_1d_nikkei_225` | global_equity | `^N225` | Asia/Tokyo | TSE Afternoon (closes 15:00 JST) | 15:00 JST | 11:45 IST (Day T) | 21.0 hours | **LOW RISK** | NONE | VALID |
| `ctx_ret_1d_hang_seng` | global_equity | `^HSI` | Asia/Hong_Kong | HKEX Afternoon (closes 16:00 HKT) | 16:00 HKT | 13:45 IST (Day T) | 19.0 hours | **LOW RISK** | NONE | VALID |
| `ctx_ret_1d_ftse_100` | global_equity | `^FTSE` | Europe/London | LSE Regular (closes 16:30 BST/GMT) | 16:30 BST | 21:15 IST (Day T) | 11.5 hours | **LOW RISK** | NONE | VALID |
| `ctx_ret_1d_brent_crude` | global_commodities | `BZ=F` | America/New_York | ICE Electronic (closes 17:00 EST) | 17:00 EST | 03:00 / 04:00 IST (Day T+1) | 4.8–5.8 hours | **MEDIUM RISK** | LOW | CONDITIONAL |
| `ctx_ret_1d_wti_crude` | global_commodities | `CL=F` | America/New_York | NYMEX Electronic (closes 17:00 EST) | 17:00 EST | 03:00 / 04:00 IST (Day T+1) | 4.8–5.8 hours | **MEDIUM RISK** | LOW | CONDITIONAL |
| `ctx_ret_1d_gold` | global_commodities | `GC=F` | America/New_York | COMEX Electronic (closes 17:00 EST) | 17:00 EST | 03:00 / 04:00 IST (Day T+1) | 4.8–5.8 hours | **MEDIUM RISK** | LOW | CONDITIONAL |
| `ctx_ret_1d_dxy` | global_fx | `DX-Y.NYB` | America/New_York | ICE Electronic (closes 17:00 EST) | 17:00 EST | 03:00 / 04:00 IST (Day T+1) | 4.8–5.8 hours | **MEDIUM RISK** | LOW | CONDITIONAL |
| `ctx_diff_1d_us_10y_yield` | global_rates | `^TNX` | America/New_York | CBOE Index (~15:00 EST) | 15:00 EST | 01:00 / 02:00 IST (Day T+1) | 6.8–7.8 hours | **MEDIUM RISK** | LOW | CONDITIONAL |

---

## 3. Timestamp Methodology & Cutoff Mechanics

Snapshot B generates predictions at **08:50 IST on Day T+1** for NIFTY 50 trading session Day T+1 (market opens at 09:15 IST). 

### Global Market Alignment
1. **US Overnight Cash Markets (S&P 500, Nasdaq, Dow Jones, US VIX)**:
   - Regular cash equity trading in New York concludes at 16:00 EST/EDT (options at 16:15).
   - Under Eastern Daylight Time (EDT, UTC-4), 16:00 EDT corresponds to 20:00 UTC = 01:30 IST on Day T+1. Adding a conservative 30-minute closing auction buffer yields 02:00 IST.
   - Under Eastern Standard Time (EST, UTC-5), 16:00 EST corresponds to 21:00 UTC = 02:30 IST on Day T+1. Adding a 30-minute buffer yields 03:00 IST.
   - Therefore, US closing prices arrive between 02:00 and 03:00 IST, providing **5.8 to 6.8 hours of lead time** before the 08:50 IST cutoff.
2. **Asian Markets (Nikkei 225, Hang Seng)**:
   - Nikkei closes at 15:00 JST (11:30 IST on Day T). Lead time = **21.0 hours**.
   - Hang Seng closes at 16:00 HKT (13:30 IST on Day T). Lead time = **19.0 hours**.
3. **European Markets (FTSE 100)**:
   - FTSE 100 closes at 16:30 BST/GMT (21:00/22:00 IST on Day T). Lead time = **11.5 hours**.
4. **Domestic Markets (NIFTY Bank, India VIX)**:
   - Domestic market regular session closes at 15:30 IST on Day T. Lead time = **17.3 hours**.

### The Timing Risk Source: Continuous Futures and Electronic Endpoints
While all nominal timestamps arrive before 08:50 IST, seven variables involve significant operational ambiguities:
- **Commodities (`BZ=F`, `CL=F`, `GC=F`)**: The daily bar close represents the electronic session close (17:00 EST), which is NOT the official exchange settlement price (e.g., COMEX Gold settles at 13:30 EST; WTI settles at 14:30 EST). Furthermore, continuous contract series require roll methodology adjustments that vary by provider.
- **US 10Y Yield (`^TNX`)**: ^TNX is a CBOE index derived from CME futures, not a cash Treasury bond yield.
- **Domestic FX (`USDINR=X`)**: OTC interbank aggregation that differs from the official Reserve Bank of India (RBI) / FBIL benchmark reference rate published at 13:30 IST.
- **Domestic Rates (`IN10Y=RR`)**: Indicative Reuters quote rather than the CCIL exchange clearing settlement.

---

## 4. Stale-Value & Forward-Fill Forensic Audit

The Phase 7 pipeline applied forward-filling (up to 5 calendar days) across foreign holidays to guarantee zero dropped sessions.

| Feature Name | Total OOF Sessions | Same-Day Sessions | Stale Observations | Stale % | Max Stale Lag | Avg Stale Lag | High-Vol Stale Count | Stale Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ctx_ret_1d_nifty_bank` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_diff_1d_india_vix` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_level_india_vix` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_sp500` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_nasdaq` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_dow_jones` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_diff_1d_us_vix` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_level_us_vix` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_nikkei_225` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_hang_seng` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_ftse_100` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_brent_crude` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_wti_crude` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_gold` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_ret_1d_dxy` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_diff_1d_us_10y_yield` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_diff_1d_india_10y_yield` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |
| `ctx_diff_1d_usd_inr` | 1,960 | 1,960 | 0 | 0.0% | 0 days | 0.00 days | 0 | **NEGLIGIBLE** |

*Audit Findings*: In Snapshot B, every single one of the 1,960 OOF observations has `obs_date == Day T` (zero forward-fill lag across all 18 series). The forward-filling logic was invoked only during non-overlapping calendar holidays in Snapshot A, but for Snapshot B, previous-day observations were uniformly present. Stale value propagation does **not** explain the empirical results.

---

## 5. Historical Data Revision Audit

| Feature Name | Source Instrument | Historical Data Nature | Revision Classification | PIT-Clean Certified | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ctx_ret_1d_nifty_bank` | `^NSEBANK` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | Exchange index values are never retrospectively revised. |
| `ctx_diff_1d_india_vix` | `^INDIAVIX` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | Implied volatility index fixing is immutable once calculated. |
| `ctx_level_india_vix` | `^INDIAVIX` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | Level is immutable once finalized. |
| `ctx_ret_1d_sp500` | `^GSPC` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | Cash equity index closes are immutable post closing cross. |
| `ctx_ret_1d_nasdaq` | `^IXIC` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | Nasdaq composite official close is immutable. |
| `ctx_ret_1d_dow_jones` | `^DJI` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | Dow Jones Industrial Average is immutable. |
| `ctx_diff_1d_us_vix` | `^VIX` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | CBOE VIX official settlement is immutable. |
| `ctx_level_us_vix` | `^VIX` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | CBOE VIX level is immutable. |
| `ctx_ret_1d_nikkei_225` | `^N225` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | TSE official close is immutable. |
| `ctx_ret_1d_hang_seng` | `^HSI` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | HKEX official close is immutable. |
| `ctx_ret_1d_ftse_100` | `^FTSE` | Official Exchange Benchmark | `IMMUTABLE_BENCHMARK` | **YES** | LSE official close is immutable. |
| `ctx_diff_1d_india_10y_yield` | `IN10Y=RR` | Indicative OTC Composite | `POTENTIALLY_REVISED_OR_UNSPECIFIED` | **NO** | Indicative Reuters quotes can experience feed reconsolidations. |
| `ctx_diff_1d_usd_inr` | `USDINR=X` | Indicative OTC Composite | `POTENTIALLY_REVISED_OR_UNSPECIFIED` | **NO** | Interbank FX OTC aggregations vary across data vendor snapshots. |
| `ctx_ret_1d_brent_crude` | `BZ=F` | Continuous Futures Bar | `POTENTIALLY_REVISED_OR_UNSPECIFIED` | **NO** | Continuous contract back-adjustment conventions can shift historical bars. |
| `ctx_ret_1d_wti_crude` | `CL=F` | Continuous Futures Bar | `POTENTIALLY_REVISED_OR_UNSPECIFIED` | **NO** | Continuous contract back-adjustment conventions can shift historical bars. |
| `ctx_ret_1d_gold` | `GC=F` | Continuous Futures Bar | `POTENTIALLY_REVISED_OR_UNSPECIFIED` | **NO** | Continuous contract back-adjustment conventions can shift historical bars. |
| `ctx_ret_1d_dxy` | `DX-Y.NYB` | Continuous Futures Bar | `POTENTIALLY_REVISED_OR_UNSPECIFIED` | **NO** | Continuous contract roll methodology is unspecified by vendor. |
| `ctx_diff_1d_us_10y_yield` | `^TNX` | Futures-Derived Index | `POTENTIALLY_REVISED_OR_UNSPECIFIED` | **NO** | Derived yield index based on futures pricing. |

---

## 6. Diagnostic Model Information Sets

To cleanly test point-in-time timing robustness, four frozen model configurations were evaluated using identical expanding-window walk-forward training across the 2014–2021 OOF population:

1. **Model P0 (Price Only Baseline, 45 features)**:
   - Retains all 45 Phase 4 Price features (returns, moving averages, momentum, volatility, calendar).
   - Zero Context features.
2. **Model P1 (Original PIT Reference, 63 features)**:
   - 45 Price + all 18 Phase 7 Context features.
   - Exactly reproduces the Step 8 `G0_ALL` reference configuration.
3. **Model P2 (Conservative PIT, 56 features)**:
   - 45 Price + 11 LOW RISK Context features.
   - **Removes all 7 MEDIUM RISK features**: excludes Brent crude, WTI crude, Gold, DXY, US 10Y yield, USD/INR, and India 10Y yield.
   - Retains only unambiguous cash equity and implied volatility index closes.
4. **Model P3 (Strict PIT, 53 features)**:
   - 45 Price + 8 strictly certified overnight cash equity and volatility indices.
   - Excludes Asian and European indices (`ctx_ret_1d_nikkei_225`, `ctx_ret_1d_hang_seng`, `ctx_ret_1d_ftse_100`) to isolate purely domestic and US overnight equity information.

---

## 7. Full Out-of-Fold (OOF) Empirical Results

*Evaluation Period: 2014-01-02 to 2021-12-31 | N = 1,960 sessions | Target: Intraday Open-to-Close Return*

| Model Code | Configuration Description | Features | Raw Pearson IC (p-val) | Residual Pearson IC (p-val) | Residual Spearman IC | Incr. $R^2$ (%) | Res. Dir. Acc. (%) | Raw RMSE (bps) | % Short | vs Short Mean (bps) | vs Short HAC t (p-val) | FDR Res. p-val |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P0_PRICE_ONLY** | 45 Price Features Only | 45 | -0.0088 (0.6975) | **-0.0101** (0.6544) | +0.0068 | +0.0121% | 52.50% | 89.46 | 96.79% | -1.155 | -1.226 (0.2202) | 0.6544 |
| **P1_ORIGINAL_PIT** | 45 Price + 18 PIT-A Context | 63 | +0.0476 (0.0350) | **+0.0477** (0.0346) | +0.0381 | +0.3425% | 50.26% | 89.31 | 90.71% | -0.793 | -0.584 (0.5591) | 0.1383 |
| **P2_CONSERVATIVE_PIT** | 45 Price + 11 PIT-B Context | 56 | +0.0210 (0.3524) | **+0.0203** (0.3699) | +0.0072 | +0.1559% | 52.55% | 89.39 | 95.41% | -0.561 | -0.550 (0.5822) | 0.6544 |
| **P3_STRICT_PIT** | 45 Price + 8 PIT-C Context | 53 | +0.0134 (0.5537) | **+0.0126** (0.5781) | +0.0161 | +0.1207% | 52.14% | 89.41 | 95.87% | -1.178 | -1.249 (0.2115) | 0.6544 |

### Statistical Comparison (P1 Reference vs Conservative / Strict)
- **P1 vs P2**: Removing the 7 medium-risk context features causes residual Pearson IC to drop from $+0.0477$ to $+0.0203$ ($\Delta = -0.0275$, a **57.5% reduction**), increasing the p-value from $0.0346$ to $0.3699$.
- **P1 vs P3**: Under strict timing, residual Pearson IC drops to $+0.0126$ ($\Delta = -0.0352$, a **73.7% collapse**), with $p = 0.5781$.
- **FDR-Adjusted Significance**: Following Benjamini-Hochberg adjustment across the tested models, zero configurations exhibit statistically significant residual predictability (P1 FDR $p = 0.1383$; P2 FDR $p = 0.6544$; P3 FDR $p = 0.6544$).

---

## 8. Fold-by-Fold Stability & Tree-Count Analysis

| Fold ID | Val Year | Train N | Val N | Model P0 N* (Res IC) | Model P1 N* (Res IC) | Model P2 N* (Res IC) | Model P3 N* (Res IC) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fold 1** | 2014 | 1,339 | 240 | 60 (+0.0272) | 10 (+0.1095) | 60 (+0.0596) | 50 (+0.0732) |
| **Fold 2** | 2015 | 1,579 | 244 | 10 (+0.0351) | 60 (+0.0382) | 10 (-0.0208) | 15 (+0.0128) |
| **Fold 3** | 2016 | 1,823 | 244 | 60 (-0.0230) | 45 (+0.0746) | 30 (-0.0290) | 50 (-0.0027) |
| **Fold 4** | 2017 | 2,067 | 248 | 60 (+0.0796) | 60 (+0.0254) | 15 (+0.0457) | 45 (+0.0195) |
| **Fold 5** | 2018 | 2,315 | 245 | 10 (-0.0546) | 10 (-0.1248) | 10 (-0.1003) | 10 (-0.0321) |
| **Fold 6** | 2019 | 2,560 | 241 | 25 (+0.0355) | 10 (-0.0963) | 20 (+0.0112) | 20 (+0.0276) |
| **Fold 7** | 2020 | 2,801 | 250 | 35 (-0.0597) | 10 (+0.0143) | 20 (-0.0140) | 20 (-0.0173) |
| **Fold 8** | 2021 | 3,051 | 248 | 10 (+0.1822) | 40 (+0.2539) | 60 (+0.1588) | 15 (+0.1303) |

### Fold Dynamics
In 5 out of 8 folds (Folds 2, 3, 5, 6, 7), Model P2 and Model P3 produce negative or negligible residual correlation. Across the entire 2014–2020 history (excluding 2021), the conservative and strict models show zero persistent predictive structure.

---

## 9. Temporal Block Stability

| Period Block | Date Range | Sessions | P0 Price Only Res IC | P1 Original PIT Res IC | P2 Conservative PIT Res IC | P3 Strict PIT Res IC |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Block A** | 2014–2016 | 728 | -0.0220 ($p=0.5543$) | +0.0622 ($p=0.0935$) | -0.0143 ($p=0.7000$) | +0.0126 ($p=0.7340$) |
| **Block B** | 2017–2019 | 734 | +0.0249 ($p=0.5013$) | -0.0284 ($p=0.4422$) | -0.0135 ($p=0.7149$) | +0.0051 ($p=0.8901$) |
| **Block C** | 2020–2021 | 498 | -0.0176 ($p=0.6952$) | +0.1081 ($p=0.0158$) | +0.0536 ($p=0.2323$) | +0.0195 ($p=0.6638$) |
| **Full OOF** | 2014–2021 | 1,960 | -0.0101 ($p=0.6544$) | +0.0477 ($p=0.0346$) | +0.0203 ($p=0.3699$) | +0.0126 ($p=0.5781$) |

Under Conservative (P2) and Strict (P3) timing, Block A and Block B show virtually zero predictive association (all $p > 0.70$). Block C correlation is cut in half under P2 ($+0.0536$, $p=0.2323$) and vanishes under P3 ($+0.0195$, $p=0.6638$).

---

## 10. Forensic Check: Year 2021 Anomaly Analysis

| Model Code | Year 2021 Residual Pearson IC | 2021 p-value | 2021 Incremental $R^2$ (%) | 2021 Pred. Variance ($	ext{bps}^2$) | Full OOF Res IC | 2021 Share of Total OOF Signal |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **P0_PRICE_ONLY** | +0.1822 | 0.0040 | +0.7179% | 2.30 | -0.0101 | 100%+ (Isolated) |
| **P1_ORIGINAL_PIT** | +0.2539 | 0.0001 | +2.1987% | 13.83 | +0.0477 | Dominant |
| **P2_CONSERVATIVE_PIT** | +0.1588 | 0.0123 | +1.4968% | 16.84 | +0.0203 | Dominant |
| **P3_STRICT_PIT** | +0.1303 | 0.0404 | +0.5294% | 2.32 | +0.0126 | Dominant |

*Forensic Conclusion*: While 2021 exhibits a positive coefficient across all models, removing the macro variables substantially dampens its magnitude (dropping from $+0.2539$ in P1 to $+0.1303$ in P3). The full OOF relationship remains heavily dependent on this single terminal development year.

---

## 11. Forensic Check: Years 2017–2019 Dead-Zone Analysis

| Model Code | 2017–2019 Residual Pearson IC | 2017–2019 p-value | 2017–2019 Incremental $R^2$ (%) | % Predicted Short | Model Gross (bps/day) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **P0_PRICE_ONLY** | +0.0249 | 0.5013 | +0.2657% | 99.32% | +8.03 |
| **P1_ORIGINAL_PIT** | -0.0284 | 0.4422 | -0.3999% | 95.37% | +7.24 |
| **P2_CONSERVATIVE_PIT** | -0.0135 | 0.7149 | +0.0258% | 99.05% | +7.48 |
| **P3_STRICT_PIT** | +0.0051 | 0.8901 | +0.1314% | 98.64% | +6.86 |

Across the entire 3-year pre-COVID expansion period (2017–2019, $N=734$), all four models show essentially zero predictive capacity ($R^2 pprox 0\%$, all $p > 0.44$). The models behave as unconditional short baselines (>95% short predictions).

---

## 12. Placebo & Permutation Diagnostic

*1,000 Permutations | Seed = 42 | Shuffled Residual Target Returns*

| Model Code | Observed Residual IC | Placebo Mean IC | Placebo Std IC | Empirical Percentile | Empirical p-value | Placebo Significance ($lpha=0.05$) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **P0_PRICE_ONLY** | -0.0101 | -0.0001 | 0.0234 | 33.6% | 0.6640 | Not Significant |
| **P1_ORIGINAL_PIT** | +0.0477 | -0.0012 | 0.0227 | 98.1% | **0.0190** | Significant |
| **P2_CONSERVATIVE_PIT** | +0.0203 | -0.0002 | 0.0232 | 81.6% | **0.1840** | **NOT SIGNIFICANT** |
| **P3_STRICT_PIT** | +0.0126 | -0.0004 | 0.0233 | 70.7% | **0.2930** | **NOT SIGNIFICANT** |

*Interpretation*: Model P1 was the only specification to pass the empirical placebo test ($p = 0.0190$). Once the 7 ambiguous/indicative features are excluded (P2), the empirical placebo p-value jumps to $0.1840$. Under strict timing (P3), it rises to $0.2930$. A random permutation of returns achieves a higher IC than Model P3 nearly 30% of the time.

---

## 13. Economic Cost Stress Test (Diagnostic Only)

*Raw Sign-Signal Intraday Strategy vs Always Short Baseline ($+8.04$ bps/day)*

| Model Code | Cost (bps) | % Short | Daily Return (bps) | HAC SE (bps) | HAC t-stat | HAC p-value | Sharpe Ratio | Max Drawdown (%) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **P0_PRICE_ONLY** | 0 bps | 96.79% | +6.88 | 1.74 | +3.95 | 0.0001 | 1.33 | -19.66% |
| P0_PRICE_ONLY | 5 bps | 96.79% | +1.88 | 1.74 | +1.08 | 0.2797 | 0.34 | -21.62% |
| P0_PRICE_ONLY | 10 bps | 96.79% | -3.12 | 1.74 | -1.79 | 0.0732 | -0.53 | -54.20% |
| P0_PRICE_ONLY | 20 bps | 96.79% | -13.12 | 1.74 | -7.54 | 0.0000 | -1.98 | -93.18% |
| **P1_ORIGINAL_PIT** | 0 bps | 90.71% | +7.24 | 1.83 | +3.95 | 0.0001 | 1.41 | -14.55% |
| P1_ORIGINAL_PIT | 5 bps | 90.71% | +2.24 | 1.83 | +1.22 | 0.2212 | 0.41 | -16.91% |
| P1_ORIGINAL_PIT | 10 bps | 90.71% | -2.76 | 1.83 | -1.50 | 0.1326 | -0.47 | -53.55% |
| P1_ORIGINAL_PIT | 20 bps | 90.71% | -12.76 | 1.83 | -6.96 | 0.0000 | -1.94 | -92.68% |
| **P2_CONSERVATIVE_PIT**| 0 bps | 95.41% | +7.48 | 1.77 | +4.22 | 0.0000 | 1.46 | -20.68% |
| P2_CONSERVATIVE_PIT | 5 bps | 95.41% | +2.48 | 1.77 | +1.40 | 0.1620 | 0.45 | -21.95% |
| P2_CONSERVATIVE_PIT | 10 bps | 95.41% | -2.52 | 1.77 | -1.43 | 0.1539 | -0.43 | -48.54% |
| P2_CONSERVATIVE_PIT | 20 bps | 95.41% | -12.52 | 1.77 | -7.07 | 0.0000 | -1.91 | -92.34% |
| **P3_STRICT_PIT** | 0 bps | 95.87% | +6.86 | 1.76 | +3.90 | 0.0001 | 1.33 | -20.93% |
| P3_STRICT_PIT | 5 bps | 95.87% | +1.86 | 1.76 | +1.06 | 0.2909 | 0.34 | -24.15% |
| P3_STRICT_PIT | 10 bps | 95.87% | -3.14 | 1.76 | -1.78 | 0.0743 | -0.54 | -54.41% |
| P3_STRICT_PIT | 20 bps | 95.87% | -13.14 | 1.76 | -7.47 | 0.0000 | -1.99 | -93.21% |
| **Always Short** | 0 bps | 100.0% | **+8.04** | 1.77 | +4.53 | 0.0000 | 1.49 | -12.73% |

*Diagnostic Takeaway*: None of the models outperform the unconditional Always Short benchmark at zero cost ($+8.04$ bps/day). Under realistic transaction costs of 10 bps, all configurations turn negative ($-2.5$ to $-3.1$ bps/day).

---

## 14. Comprehensive Information Leakage Audit

A forensic scan across data sources, timezone math, and bar endpoint alignment confirmed:
1. **Timezone Offset Verification**:
   - New York market close (16:00 EST / 21:00 UTC = 02:30 IST; 16:00 EDT / 20:00 UTC = 01:30 IST) is mathematically guaranteed to conclude $>5.5$ hours before 08:50 IST. Zero timezone crossing errors exist.
2. **Date Indexing**: All 16 raw context series map `obs_date == Day T` to target session `Day T+1`. There is zero same-day look-ahead leakage.
3. **No Current-Day Leakage**: No Indian data from session Day T+1 between 00:00 and 08:50 IST is utilized.
4. **Data Provider Attribution**: All context features originate from Yahoo Finance free-tier chart feeds, where publication times are unobserved and assumed based on exchange operating hours.

---

## 15. Terminal Holdout Firewall Audit

Strict quarantine verification:
- `max(loaded_trading_date) == 2021-12-31`
- `count(trading_date >= 2022-01-03) == 0`
- Zero terminal holdout rows ($N=1,154$) were accessed, inspected, loaded, or evaluated during Phase 12 Step 9.

---

## 16. Interim Artifact Inventory & Cryptographic Hashes

All 12 Step 9 artifacts were generated deterministically and written to `data/interim/phase12_step9/`:

| Filename | SHA256 Cryptographic Hash |
| :--- | :--- |
| `step9_pit_availability_matrix.csv` | `d5d58fbd2d70a7869e65c7add8c978502367581b84e894c95d52391c1e3d590b` |
| `step9_pit_availability_matrix.json` | `7f012158ad959b65cd81844717fc10eba1cfb67b76c9d0aea5f0e1533a92259b` |
| `step9_feature_timestamp_audit.csv` | `7c262121639fdeb4fa7e9bf7ce19d40fa4147e04aff9b0978028920c61ecf583` |
| `step9_predictions.csv` | `9b7c9ca96f83a31df64576941776bb3e36e33772fa6bd23e7a891ba8fc7e0961` |
| `step9_fold_results.csv` | `6ba0d15c406bb07de075462def79278248c90eb16fd808b0192d5585b1adb87d` |
| `step9_temporal_results.csv` | `8ccc4590ce28de2da17731105a0958ba8441c42202df3cc66d56b3cf4c4d92c2` |
| `step9_summary.csv` | `df853b743dca06ef926a117ba36d2ba41d69ef7ae48fd52af9cf412358589113` |
| `step9_stale_value_audit.csv` | `587068edb13b66b59ffc7bebbe06513edcfebb959f5db3d8b08a5c340d7da6f6` |
| `step9_revision_audit.csv` | `b5266afa4c18d3d1a7ab59c52c2ad5fbb7a231d7dddc18c520179565d2131299` |
| `step9_placebo_results.csv` | `2adcc3ee64c9972f291cc3e6aef300edbcf199c5c77a3deef7a242a6d8b1454f` |
| `step9_economic_diagnostic.csv` | `4b471582bfa174854d020f28c7d3dc39bcdd88015b29b31462ca11205268177a` |
| `step9_integrity_manifest.json` | `5c47957ee14fa8e98341e3d6402447fa41639d6796c9c613fa1be5d6912354a8` |

---

## 17. Final Decision Gate & Scientific Recommendation

### Pre-Registered Decision Gate Options:
- **A) PIT ROBUSTNESS SUPPORTED**: The predictive relationship remains materially similar under conservative and strict point-in-time treatment, with no material leakage concern.
- **B) PIT ROBUSTNESS NOT SUPPORTED**: The relationship materially weakens/disappears under conservative or strict timing treatment, or one/more important features fail the PIT audit.
- **C) TIMING EVIDENCE INCONCLUSIVE**: Timestamp/settlement/revision evidence is insufficient to determine whether the original information set is genuinely point-in-time valid.

### Formally Recorded Gate Decision:
$$\mathbf{B)\ PIT\ ROBUSTNESS\ NOT\ SUPPORTED}$$

### Rigorous Scientific Justification:
1. **Material Weakening Under Conservative Timing**: Under Model P2 (Conservative PIT), removing the 7 features with settlement or continuous-contract ambiguity reduces residual Pearson IC from $+0.0477$ to $+0.0203$ ($p = 0.3699$), an insignificant effect size. Under Model P3 (Strict PIT), the correlation collapses to $+0.0126$ ($p = 0.5781$).
2. **Placebo Test Failure**: While Model P1 achieved an empirical placebo p-value of $0.0190$, Model P2 ($p = 0.1840$) and Model P3 ($p = 0.2930$) fail the pre-registered permutation test.
3. **Dependence on Ambiguous Features**: The marginal information content detected in Step 8 was concentrated entirely in Macro Context (Brent, WTI, Gold, DXY, US 10Y). Because these series represent continuous futures rollover constructions and electronic bar endpoints rather than cash exchange settlement fixings, the apparent signal cannot be certified as point-in-time robust.
4. **Binding Pre-Registered Language**:
   > *“The observed relationship is sensitive to point-in-time treatment and therefore cannot currently be regarded as timing-robust.”*

---

## Formal Sealing Notice
```
==========================================================================================
PHASE 12 STEP 9 IS FORMALLY SEALED.
NO PHASE 12 STEP 10 EXECUTION IS AUTHORIZED BY THIS TASK.
==========================================================================================
```
