# Phase 7 — Indian & Global Market Context Data Layer

## 1. Overview & Objective

Phase 7 establishes a leakage-safe, provider-agnostic market-context data layer for **NIFTY AI**. 

Its core objective is to ingest, validate, standardize, and timestamp Indian and global market variables that provide macro, cross-asset, currency, interest-rate, and regional market context beyond NIFTY 50's standalone OHLC history.

### Strict Scope Boundaries
- **No Model Retraining / Revision:** The frozen Phase 6 XGBoost models ($N^*=12$ classifier, $N^*=43$ regressor) remain completely untouched and frozen.
- **Holdout Discipline:** Data from `2022-01-01` onward remains locked. No context feature selection, tuning, or predictive evaluation has been performed against the holdout set.
- **No Look-Ahead Leakage:** All context series are timestamped with distinct **observation timestamps** (when the bar closes in its native timezone) and **availability/publication timestamps** (when the data point is verified and accessible to the system in IST).
- **Snapshot Integrity:** Distinct datasets are constructed for **Snapshot A** (`15:40 IST Day T`) and **Snapshot B** (`08:50 IST Day T+1`).

---

## 2. Ingested Canonical Context Variables

| Variable Name | Symbol / Instrument | Category | Exchange / Venue | Native Timezone | Market Close (Local) | Publication Delay | Missing Policy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `INDIA_VIX` | `^INDIAVIX` | Domestic Volatility | NSE India | `Asia/Kolkata` | 15:30 IST | 0 min | `no_fill` |
| `NIFTY_BANK` | `^NSEBANK` | Domestic Equity | NSE India | `Asia/Kolkata` | 15:30 IST | 0 min | `no_fill` |
| `USD_INR` | `USDINR=X` | Domestic FX | Spot / OTC | `Asia/Kolkata` | 15:30 IST | 0 min | `forward_fill_calendar` |
| `INDIA_10Y_YIELD` | `IN10Y=RR` | Domestic Rates | CCIL / RBI | `Asia/Kolkata` | 16:30 IST | 15 min | `forward_fill_calendar` |
| `SP500` | `^GSPC` | Global Equity | NYSE / NASDAQ | `America/New_York` | 16:00 EST/EDT | 30 min | `forward_fill_calendar` |
| `NASDAQ` | `^IXIC` | Global Equity | NASDAQ | `America/New_York` | 16:00 EST/EDT | 30 min | `forward_fill_calendar` |
| `DOW_JONES` | `^DJI` | Global Equity | NYSE | `America/New_York` | 16:00 EST/EDT | 30 min | `forward_fill_calendar` |
| `US_VIX` | `^VIX` | Global Volatility | CBOE | `America/New_York` | 16:15 EST/EDT | 15 min | `forward_fill_calendar` |
| `US_10Y_YIELD` | `^TNX` | Global Rates | CBOE / Treasuries | `America/New_York` | 15:00 EST/EDT | 30 min | `forward_fill_calendar` |
| `BRENT_CRUDE` | `BZ=F` | Global Commodities | ICE Futures | `America/New_York` | 17:00 EST/EDT | 30 min | `forward_fill_calendar` |
| `WTI_CRUDE` | `CL=F` | Global Commodities | NYMEX | `America/New_York` | 17:00 EST/EDT | 30 min | `forward_fill_calendar` |
| `GOLD` | `GC=F` | Global Commodities | COMEX | `America/New_York` | 17:00 EST/EDT | 30 min | `forward_fill_calendar` |
| `DXY` | `DX-Y.NYB` | Global FX | ICE US | `America/New_York` | 17:00 EST/EDT | 30 min | `forward_fill_calendar` |
| `NIKKEI_225` | `^N225` | Global Equity | Tokyo SE | `Asia/Tokyo` | 15:00 JST | 15 min | `forward_fill_calendar` |
| `HANG_SENG` | `^HSI` | Global Equity | HKEX | `Asia/Hong_Kong` | 16:00 HKT | 15 min | `forward_fill_calendar` |
| `FTSE_100` | `^FTSE` | Global Equity | LSE | `Europe/London` | 16:30 GMT/BST | 15 min | `forward_fill_calendar` |

---

## 3. Snapshot Information Timing & Anti-Leakage Contracts

The mathematical formulation of point-in-time usability for any context observation $obs$ against snapshot cutoff $C$ is:
$$\text{Usable}(obs, C) \iff \text{timestamp}_{\text{availability}}(obs) \le \text{timestamp}_{\text{cutoff}}(C)$$

### Snapshot A (Post-Market Close)
- **Cutoff Time:** `15:30 IST` on Session `T`
- **Prediction Emitted:** `15:40 IST` on Session `T`
- **Target Horizon:** Session `T+1` close-to-close outcome
- **Information Boundary:**
  - Indian equity markets have concluded Session $T$ (15:30 IST).
  - Tokyo (`15:00 JST` = `11:30 IST`) and Hong Kong (`16:00 HKT` = `13:30 IST`) Session $T$ are complete and usable.
  - **CRITICAL US RESTRICTION:** US equity/commodity markets do not close until 16:00–17:00 EST (01:30–02:30 IST on Day $T+1$). Therefore, **Day $T$ US closing prices are strictly excluded from Snapshot A**. Snapshot A only incorporates US session **$T-1$**.
  - European FTSE 100 closes at 16:30 GMT/BST (21:00/22:00 IST), so Session $T$ FTSE is also excluded from Snapshot A.

### Snapshot B (Pre-Market Open)
- **Cutoff Time:** `08:50 IST` on Session `T+1`
- **Prediction Emitted:** `08:50 IST` on Session `T+1`
- **Target Horizon:** Session `T+1` close-to-close outcome
- **Information Boundary:**
  - US markets for Session $T$ completed overnight (at 01:30–02:30 IST) and are legitimately available.
  - Snapshot B incorporates Day $T$ US closes (S&P 500, Nasdaq, Dow Jones, US VIX, Crude, Gold, US 10Y, DXY) and Day $T$ FTSE 100.
  - Snapshot B **NEVER** incorporates Day $T+1$ prices (which have not traded yet).

---

## 4. Timezone, Calendar & DST Architecture

### Native Timezone Conversion
Every asset is recorded in its native exchange timezone via Python's standard `zoneinfo.ZoneInfo`:
- `Asia/Kolkata` (IST, UTC+5:30, no DST)
- `America/New_York` (EST/EDT, UTC-5 / UTC-4)
- `Asia/Tokyo` (JST, UTC+9:00, no DST)
- `Asia/Hong_Kong` (HKT, UTC+8:00, no DST)
- `Europe/London` (GMT/BST, UTC+0 / UTC+1)

Daylight Saving Time transitions in New York (second Sunday in March to first Sunday in November) and London (last Sunday in March to last Sunday in October) are automatically converted to Asia/Kolkata time. For example:
- S&P 500 summer close (`16:00 EDT` + 30m lag = `16:30 EDT`) $\to$ `02:00 IST` on Day $T+1$.
- S&P 500 winter close (`16:00 EST` + 30m lag = `16:30 EST`) $\to$ `03:00 IST` on Day $T+1$.

### Missing Data & Holiday Policies
1. **Calendar Gaps:** Different markets observe distinct national holidays (e.g. US Thanksgiving, Memorial Day, Indian Diwali, Japanese Golden Week).
2. **Forward-Fill Limit:** For macro, FX, and global equities (`FORWARD_FILL_CALENDAR`), missing values are forward-filled up to a maximum calendar limit of **5 calendar days** (accommodating 3-day holiday weekends or 4-day bank holidays). Gaps exceeding 5 days revert to `NaN`.
3. **No-Fill Series:** Domestic volatility (`INDIA_VIX`) and equity index (`NIFTY_BANK`) enforce `NO_FILL`; unobserved sessions remain `NaN`.
4. **Zero Backfilling:** Backward filling is strictly prohibited across all series to prevent look-ahead leakage.

---

## 5. Storage & Provenance Layout

```
data/
├── raw/
│   └── context/
│       ├── INDIA_VIX.json
│       ├── NIFTY_BANK.json
│       ├── SP500.json
│       ├── ... (16 pristine raw JSON payloads)
├── interim/
│   └── context/
│       ├── snapshot_a_context_daily.csv   (Aligned to Snapshot A cutoff 15:30 IST)
│       ├── snapshot_b_context_daily.csv   (Aligned to Snapshot B cutoff 08:50 IST)
│       ├── availability_matrix.json       (Machine-readable availability schedule)
│       └── context_manifest.json          (Pipeline audit, row counts, data hashes)
docs/
├── DATA_AVAILABILITY_MATRIX.md           (Human-readable publication & cutoff contract)
└── MARKET_CONTEXT_DATA.md                (Architecture and design documentation)
```

---

## 6. Verification & Automated Test Suite

The test suite in [`tests/test_context.py`](file:///c:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/tests/test_context.py) provides 21 automated anti-leakage, point-in-time, and data provenance checks:

1. `test_publication_time_cutoff_strictness`: Confirms observations with availability timestamps past the snapshot cutoff are rejected.
2. `test_snapshot_a_vs_b_us_divergence`: Confirms Snapshot A selects Day $T-1$ for US series, while Snapshot B selects Day $T$.
3. `test_future_mutation_invariance`: Mutating future context bars (at $T+2$) does not change historical dataset values up to $T$.
4. `test_timezone_and_dst_handling`: Verifies exact IST arrival times across EDT (02:00 IST) and EST (03:00 IST) transitions.
5. `test_holiday_calendar_isolation_and_missing_policy`: Verifies 5-day forward fill ceiling and zero backfill enforcement.
6. `test_terminal_holdout_isolation`: Verifies development partition ($< 2022-01-01$) cutoffs contain zero holdout timestamps.
7. `test_no_future_rolling_statistics`: Confirms rolling return and volatility statistics operate strictly backward without forward lookahead.
8. `test_all_16_canonical_variables_exist`: Verifies all 16 variables exist in registry with required schema and generated CSV columns.
9. `test_availability_timestamp_type_semantics`: Verifies all 16 variables have `availability_timestamp_type == ASSUMED_SCHEDULE` and `provider_availability_observed == False`.
10. `test_source_specific_instrument_semantics`: Verifies financial quotation conventions (^TNX yield x 10, USDINR=X OTC, commodity futures).
11. `test_cutoff_exact_boundary_edge_cases`: Verifies exact-second cutoff acceptance vs 1-second-late rejection.
12. `test_friday_to_monday_forward_fill`: Verifies weekend forward fill preserves source timestamps and values.
13. `test_us_holiday_with_indian_trading_day`: Verifies Snapshot B forward-fills prior available session on US holidays without leakage.
14. `test_all_variables_are_assumed_schedule`: Universal invariant asserting 100% of variables are `ASSUMED_SCHEDULE`.
15. `test_availability_spec_provenance_fields`: Asserts all 16 specs have non-empty instrument and provider provenance descriptions.
16. `test_usdinr_provenance_semantics`: Asserts USD_INR notes separate OTC/interbank spot from RBI reference rate.
17. `test_vix_and_nifty_bank_boundary_documentation`: Asserts INDIA_VIX and NIFTY_BANK document Snapshot A eligibility as an assumption-dependent boundary condition.
18. `test_tnx_yield_index_semantics`: Asserts ^TNX is documented as a CBOE yield index (yield x 10), not a cash Treasury yield.
19. `test_commodity_continuous_contract_semantics`: Asserts commodity continuous contracts document settlement vs electronic session distinction.
20. `test_target_session_fill_diagnostics`: Verifies `align_and_fill_series_with_diagnostics` computes both calendar and NIFTY session aging.
21. `test_phase6_calibration_wording_integrity`: Verifies `MODEL_METHODOLOGY.md` states raw tree probabilities remain primary and calibration is an optional diagnostic.

### Test Count Progression
- **Phase 6 Sealed:** 76 tests (core models, evaluation, targets, features, data architecture, quality)
- **Phase 7 Initial:** 83 tests (+7 initial context point-in-time tests)
- **Phase 7 Provenance Audit:** 89 tests (+6 audit tests: inventory, semantics, edge cases, weekend fills)
- **Phase 7 Final Correction:** 97 tests (+8 tests: universal assumed schedule, provenance fields, USDINR, VIX/Bank boundary, ^TNX, commodities, session fill aging, calibration wording integrity)

All **97 project tests** pass with 100% success rate.

---

## 7. Data Provenance & Timestamp Architecture

### Instrument vs. Provider Availability Separation
For every variable, Phase 7 strictly distinguishes:
1. **Instrument/Session Close:** The moment trading concludes or the official index/settlement is calculated on the host exchange.
2. **Settlement Timing:** When official settlement is published (for commodities and volatility products).
3. **Provider Availability:** When the provider (Yahoo Finance) actually exposes the daily bar to consumers.
4. **Historical Bar Timestamp:** The nominal date stamped on the bar by the provider.

Because Yahoo Finance (free tier) does not provide historical publication timestamps, **ALL 16 variables are classified as `ASSUMED_SCHEDULE`** with `provider_availability_observed = False`.

### Assumption-Dependent Boundary Conditions
- **INDIA_VIX & NIFTY_BANK:** Instrument finalization occurs at 15:30 IST. Snapshot A cutoff is 15:30 IST. Because historical Yahoo publication timing is unobserved, Snapshot A eligibility is based on an **explicit conservative modeling assumption** that the provider value is available at instrument close. This boundary condition is NOT empirically verified.
- **USD_INR:** Domestic interbank spot close ~15:30 IST is used as the assumed availability timestamp. Yahoo USDINR=X OTC aggregation is NOT identical to the RBI/FBIL reference rate. Snapshot A eligibility is likewise an assumption-dependent development rule.

