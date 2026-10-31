# PRICE-BASED FEATURE ENGINEERING

**Document:** `docs/FEATURE_ENGINEERING.md`  
**Phase:** Phase 4 — Price-Based Feature Engineering  
**Asset:** NIFTY 50 Index (`^NSEI` / `NIFTY 50`)  
**Input Source:** [`data/processed/nifty_50_daily.csv`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/processed/nifty_50_daily.csv)  
**Feature Registry Config:** [`configs/features.yaml`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/configs/features.yaml)  
**Full Features Dataset:** `data/features/nifty50_features.csv` (4,654 rows)  
**Clean Features Dataset:** `data/features/nifty50_features_clean.csv` (4,454 rows)  
**Manifest:** `data/features/nifty50_features.meta.json`  
**Total Features:** **45 features** (across 8 distinct families)  
**Volume Inclusion Status:** **EXCLUDED** (Volume quarantined per Phase 3 audit)  

---

## 1. Feature Engineering Principles & Anti-Leakage Mandate

In predictive quantitative finance, look-ahead bias and data leakage are catastrophic flaws that produce artificially inflated backtests and failing real-world trading. To prevent this, NIFTY AI enforces the following core rules:

1. **Information Cutoff Rule:**
   $$\text{timestamp}(\text{feature inputs}) \le \text{cutoff timestamp}(\text{snapshot})$$
2. **Zero Forward Access:** No feature may reference future prices, future returns, or future calendar intervals.
3. **Sequential Chronological Integrity:** All rolling windows, moving averages, return shifts, and volatilities are calculated exclusively from trailing completed trading sessions.
4. **Volume Exclusion:** The volume column has been completely quarantined due to missing/zero values prior to 2013, preventing corrupt or discontinuous volume signals from leaking into models.

---

## 2. Snapshot Architecture & Temporal Semantics

NIFTY AI operates on two daily prediction snapshots for every target trading session \( T \):

```
Trading Day T - 1                                             Trading Day T
─────────────────────────────────────────────────────────────────────────────────
[09:15 - 15:30 IST]         15:40 IST                        08:50 IST   09:15 IST
Market Session T-1          Snapshot A                       Snapshot B  Market Open T
                            Cutoff: 15:30 IST                Cutoff: 08:50 IST
                            (Latest bar: T-1 Close)          (Latest bar: T-1 Close)
```

### Snapshot A (`SNAPSHOT_1540`)
* **Execution Timestamp:** `15:40:00 IST` on Day \( T-1 \).
* **Information Cutoff:** Strictly `15:30:00 IST` on Day \( T-1 \).
* **Target Prediction Horizon:** Day \( T \).
* **Permitted Price Bar:** The finalized Day \( T-1 \) bar (which concluded at 15:30:00 IST) is the latest eligible bar.

### Snapshot B (`SNAPSHOT_0850`)
* **Execution Timestamp:** `08:50:00 IST` on Day \( T \).
* **Information Cutoff:** Strictly `08:50:00 IST` on Day \( T \).
* **Target Prediction Horizon:** Day \( T \).
* **Permitted Price Bar:** The Day \( T \) daily bar has not yet occurred (market opens at 09:15:00 IST). Therefore, the latest completed daily OHLC bar is **also Day \( T-1 \)**.
* **Snapshot Differentiator (Future Phases):** In V1 daily OHLC, the price feature vector for Day \( T \) is identical across Snapshot A and Snapshot B. Snapshot B will be differentiated in Phases 9 and 10 when overnight US/Asian equity closes, early GIFT Nifty prints, and overnight news sentiment are layered on top of this baseline price matrix.

---

## 3. Catalog of Baseline Feature Families (45 Features)

### Family A: Trailing Price Returns (6 Features)
Historical close-to-close percentage returns calculated over trailing completed trading sessions:

| Feature Name | Lookback | Mathematical Definition | Description |
| :--- | :---: | :--- | :--- |
| `ret_1d` | 1 bar | \(\frac{\text{Close}_t}{\text{Close}_{t-1}} - 1\) | Trailing 1-day percentage price return. |
| `ret_2d` | 2 bars | \(\frac{\text{Close}_t}{\text{Close}_{t-2}} - 1\) | Trailing 2-day cumulative price return. |
| `ret_3d` | 3 bars | \(\frac{\text{Close}_t}{\text{Close}_{t-3}} - 1\) | Trailing 3-day cumulative price return. |
| `ret_5d` | 5 bars | \(\frac{\text{Close}_t}{\text{Close}_{t-5}} - 1\) | Trailing 5-day (1-week) cumulative return. |
| `ret_10d` | 10 bars | \(\frac{\text{Close}_t}{\text{Close}_{t-10}} - 1\) | Trailing 10-day (2-week) cumulative return. |
| `ret_20d` | 20 bars | \(\frac{\text{Close}_t}{\text{Close}_{t-20}} - 1\) | Trailing 20-day (1-month) cumulative return. |

### Family B: Lagged Returns (5 Features)
Past 1-day returns lagged by \(k\) completed sessions to capture serial correlation and mean-reversion signals:

| Feature Name | Lookback | Mathematical Definition | Description |
| :--- | :---: | :--- | :--- |
| `ret_lag_1` | 2 bars | \(\text{ret\_1d}_{t-1}\) | 1-day return from session \(t-2\) to \(t-1\). |
| `ret_lag_2` | 3 bars | \(\text{ret\_1d}_{t-2}\) | 1-day return from session \(t-3\) to \(t-2\). |
| `ret_lag_3` | 4 bars | \(\text{ret\_1d}_{t-3}\) | 1-day return from session \(t-4\) to \(t-3\). |
| `ret_lag_5` | 6 bars | \(\text{ret\_1d}_{t-5}\) | 1-day return from session \(t-6\) to \(t-5\). |
| `ret_lag_10` | 11 bars | \(\text{ret\_1d}_{t-10}\) | 1-day return from session \(t-11\) to \(t-10\). |

### Family C: Simple Moving Averages & Distances (12 Features)
Trailing simple moving averages and normalized relative distance metrics:

| Feature Name | Lookback | Mathematical Definition | Description |
| :--- | :---: | :--- | :--- |
| `sma_5`, `sma_10`, `sma_20` | 5, 10, 20 | \(\frac{1}{w}\sum_{i=0}^{w-1} \text{Close}_{t-i}\) | Short-term trailing moving averages. |
| `sma_50`, `sma_100`, `sma_200` | 50, 100, 200 | \(\frac{1}{w}\sum_{i=0}^{w-1} \text{Close}_{t-i}\) | Medium- and long-term institutional trend benchmarks. |
| `close_to_sma_w` (6 features) | \(w\) bars | \(\frac{\text{Close}_t}{\text{SMA}_w(t)} - 1\) | Percentage premium/discount of price relative to SMA. |

### Family D: Price Momentum (4 Features)
Absolute point differences across key trading horizons:

| Feature Name | Lookback | Mathematical Definition | Description |
| :--- | :---: | :--- | :--- |
| `mom_5d` | 5 bars | \(\text{Close}_t - \text{Close}_{t-5}\) | 5-session absolute index point momentum. |
| `mom_10d` | 10 bars | \(\text{Close}_t - \text{Close}_{t-10}\) | 10-session absolute index point momentum. |
| `mom_20d` | 20 bars | \(\text{Close}_t - \text{Close}_{t-20}\) | 20-session absolute index point momentum. |
| `mom_60d` | 60 bars | \(\text{Close}_t - \text{Close}_{t-60}\) | 60-session (quarterly) index point momentum. |

### Family E: Rolling Volatility (5 Features)
Sample standard deviation of daily percentage returns:

| Feature Name | Lookback | Mathematical Definition | Description |
| :--- | :---: | :--- | :--- |
| `volatility_5d` | 6 bars | \(\sigma(\text{ret\_1d}_{t-4 \dots t})\) | Trailing 5-session return standard deviation. |
| `volatility_10d` | 11 bars | \(\sigma(\text{ret\_1d}_{t-9 \dots t})\) | Trailing 10-session return standard deviation. |
| `volatility_20d` | 21 bars | \(\sigma(\text{ret\_1d}_{t-19 \dots t})\) | Trailing 20-session return standard deviation. |
| `volatility_60d` | 61 bars | \(\sigma(\text{ret\_1d}_{t-59 \dots t})\) | Trailing 60-session return standard deviation. |
| `volatility_ann_20d` | 21 bars | \(\text{volatility\_20d} \times \sqrt{252}\) | Annualized 20-day trailing volatility. |

### Family F: OHLC Bar Shape & Intraday Dynamics (5 Features)
Price structure indicators derived from single-session bar geometry:

| Feature Name | Lookback | Mathematical Definition | Description |
| :--- | :---: | :--- | :--- |
| `hl_range_pct` | 1 bar | \(\frac{\text{High}_t - \text{Low}_t}{\text{Low}_t}\) | Total intraday price expansion relative to Low. |
| `close_pos_in_range` | 1 bar | \(\frac{\text{Close}_t - \text{Low}_t}{\text{High}_t - \text{Low}_t}\) | Close location in session range (0.0 = low, 1.0 = high). |
| `open_to_close_ret` | 1 bar | \(\frac{\text{Close}_t - \text{Open}_t}{\text{Open}_t}\) | Intraday candle body return. |
| `high_to_close_dist` | 1 bar | \(\frac{\text{High}_t - \text{Close}_t}{\text{Close}_t}\) | Upper shadow length relative to Close. |
| `low_to_close_dist` | 1 bar | \(\frac{\text{Close}_t - \text{Low}_t}{\text{Close}_t}\) | Lower shadow length relative to Close. |

### Family G: Structural Trend Features (3 Features)
Multi-timeframe trend spreads and normalized linear regression slope:

| Feature Name | Lookback | Mathematical Definition | Description |
| :--- | :---: | :--- | :--- |
| `sma_ratio_20_50` | 50 bars | \(\frac{\text{SMA}_{20}}{\text{SMA}_{50}} - 1\) | Short-to-medium trend alignment spread. |
| `sma_ratio_50_200` | 200 bars | \(\frac{\text{SMA}_{50}}{\text{SMA}_{200}} - 1\) | Medium-to-long trend alignment spread (Golden Cross proxy). |
| `trend_slope_20d` | 20 bars | \(\frac{\text{slope}(\text{Close}_{t-19 \dots t})}{\text{mean}(\text{Close}_{t-19 \dots t})}\) | 20-session normalized linear regression price trajectory slope. |

### Family H: Calendar & Seasonal Features (5 Features)
Deterministic point-in-time temporal features:

| Feature Name | Lookback | Mathematical Definition | Description |
| :--- | :---: | :--- | :--- |
| `day_of_week` | 0 bars | `trading_date.weekday()` | Day of week integer (0=Mon, 1=Tue, ..., 4=Fri, 5=Sat). |
| `day_of_month` | 0 bars | `trading_date.day` | Day of calendar month (1 to 31). |
| `month` | 0 bars | `trading_date.month` | Calendar month (1 to 12). |
| `quarter` | 0 bars | `(month - 1) // 3 + 1` | Fiscal/calendar quarter (1 to 4). |
| `is_month_end` | 0 bars | `1 if next_calendar_day.month != current_month else 0` | Monthly settlement / expiry proximity flag. |

---

## 4. Warm-Up Policy & Dataset Partitions

### Maximum Lookback Window
The maximum lookback requirement across all 45 features is **200 trading sessions** (dictated by `sma_200`, `close_to_sma_200`, and `sma_ratio_50_200`).

### Two Deterministic Output Datasets
To prevent data distortion and respect downstream modeling needs, the pipeline exports two synchronized dataset files:

1. **Full Feature Matrix (`nifty50_features.csv`)**:
   * **Total Rows:** **4,654** (September 17, 2007 to September 4, 2026).
   * **NaN Treatment:** Rows 0 through 199 contain empty strings (`""` / `NaN`) for indicators that have not met their minimum lookback. No artificial forward-filling or back-filling is performed.
2. **Clean Feature Matrix (`nifty50_features_clean.csv`)**:
   * **Total Rows:** **4,454** (July 8, 2008 to September 4, 2026).
   * **Warm-up Rows Dropped:** Exactly the first **200 rows** (2007-09-17 to 2008-07-07) are trimmed.
   * **Missing Values:** **0.0% NaNs**. Every single row has complete, valid values for all 45 features.

---

## 5. Leakage Verification & Automated Tests

The feature engineering layer was audited with targeted adversarial leakage tests in [`tests/test_features.py`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/tests/test_features.py):

* **Future Mutation Invariance (`test_leakage_future_mutation_invariance`)**:
  * Altering the price of row 29 by 1,000% produces **bit-identical** feature outputs for rows 0 through 28.
* **Snapshot B Inaccessibility (`test_leakage_snapshot_b_never_uses_current_day`)**:
  * Passing a sequence containing Day \( T \) to `get_features_for_prediction` for target Day \( T \) strictly filters out Day \( T \), ensuring Snapshot B exclusively consumes Day \( T-1 \).
* **Volume Isolation (`test_volume_exclusion_invariance`)**:
  * Mutating the volume field by 100,000,000 produces zero change in any feature column, proving volume has no influence on the feature store.
* **Mathematical Determinism (`test_determinism`)**:
  * Re-running feature extraction on identical inputs produces bit-identical CSV files and SHA-256 hashes.
