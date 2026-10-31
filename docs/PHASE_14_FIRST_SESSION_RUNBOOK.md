# PHASE 14 — FIRST SESSION OPERATING RUNBOOK
## Target Session: Monday, 2 November 2026

**System**: NIFTY AI Phase 14 Prospective Shadow Prediction & Forward Validation  
**Operating Horizon**: Snapshot B Pre-Market (`08:50:00 Asia/Kolkata`)  
**Outcome Horizon**: Post-Market Realization ($\ge \text{15:30:00 Asia/Kolkata}$)  
**Target Identifier**: `T0` (Same-Session Intraday Open-to-Close Return)  
**Governance Standing**: **`RESEARCH_BASELINE_ONLY`** (Zero Live Order Routing Authorization)  

---

## 1. Session Timeline & Operating Windows

```
08:00–08:45 IST: Data Ingestion & Input Vector Assembly (63 canonical features)
08:45–08:49 IST: Preflight Check & Point-in-Time Schema Validation
08:50:00 IST:    EXECUTE SHADOW PREDICTION RUNNER
09:15:00 IST:    NSE Cash Market Opens (No trading action taken)
15:30:00 IST:    NSE Cash Market Closes (Session Open & Close finalized)
15:45+ IST:      EXECUTE OUTCOME RECONCILIATION
16:00+ IST:      AUDIT LEDGER INTEGRITY & SCORECARD
```

---

## 2. Pre-Market Operating Workflow (08:30 to 08:50 IST)

### Step 1: Preflight Pipeline Check
Verify that the Python runtime, XGBoost libraries, and frozen model artifacts authenticate without errors:
```powershell
.\.venv\Scripts\python.exe scripts/run_shadow_prediction.py --preflight-only
```
**Expected Terminal Output**:
```
[1/4] Authenticating frozen model artifacts...
      Model authenticated: Snapshot B T0 Full Development Production Model
      Frozen trees: 43
      Feature count: 63
Preflight checks PASSED successfully.
```

### Step 2: Prepare Point-in-Time Input Vector File
Assemble the verified 63 features (45 Price + 18 Context) into a point-in-time JSON file:
`data/interim/phase14_shadow/input_2026-11-02_0850.json`

**Required JSON Structure**:
```json
{
  "session_date": "2026-11-02",
  "cutoff_time": "2026-11-02T08:50:00+05:30",
  "feature_names": [
    "ret_1d", "ret_2d", "ret_3d", "ret_5d", "ret_10d", "ret_20d",
    "ret_lag_1", "ret_lag_2", "ret_lag_3", "ret_lag_5", "ret_lag_10",
    "sma_5", "close_to_sma_5", "sma_10", "close_to_sma_10",
    "sma_20", "close_to_sma_20", "sma_50", "close_to_sma_50",
    "sma_100", "close_to_sma_100", "sma_200", "close_to_sma_200",
    "mom_5d", "mom_10d", "mom_20d", "mom_60d",
    "volatility_5d", "volatility_10d", "volatility_20d", "volatility_60d",
    "volatility_ann_20d", "hl_range_pct", "close_pos_in_range",
    "open_to_close_ret", "high_to_close_dist", "low_to_close_dist",
    "sma_ratio_20_50", "sma_ratio_50_200", "trend_slope_20d",
    "day_of_week", "day_of_month", "month", "quarter", "is_month_end",
    "ctx_ret_1d_nifty_bank", "ctx_ret_1d_sp500", "ctx_ret_1d_nasdaq",
    "ctx_ret_1d_dow_jones", "ctx_ret_1d_brent_crude", "ctx_ret_1d_wti_crude",
    "ctx_ret_1d_gold", "ctx_ret_1d_dxy", "ctx_ret_1d_nikkei_225",
    "ctx_ret_1d_hang_seng", "ctx_ret_1d_ftse_100", "ctx_diff_1d_india_vix",
    "ctx_diff_1d_us_vix", "ctx_diff_1d_india_10y_yield",
    "ctx_diff_1d_us_10y_yield", "ctx_diff_1d_usd_inr",
    "ctx_level_india_vix", "ctx_level_us_vix"
  ],
  "feature_values": [ ... 63 floating point values ... ],
  "feature_hash": "...",
  "provenance": {
    "source_id": "NSE_HISTORICAL_DAILY_AND_CONTEXT_FEEDS",
    "observation_time": "2026-11-02T08:45:00+05:30",
    "availability_time": "2026-11-02T08:48:00+05:30",
    "ingestion_time": "2026-11-02T08:49:00+05:30",
    "timezone": "Asia/Kolkata",
    "raw_data_hash": "...",
    "provenance_type": "prospective_live_capture",
    "quarantine_reason": null
  }
}
```

---

## 3. Prediction Execution (Strictly at 08:50:00 IST)

Run the prediction generator:
```powershell
.\.venv\Scripts\python.exe scripts/run_shadow_prediction.py --session-date 2026-11-02 --input-file data/interim/phase14_shadow/input_2026-11-02_0850.json
```

**Expected Successful Terminal Output**:
```
[1/4] Authenticating frozen model artifacts...
      Model authenticated: Snapshot B T0 Full Development Production Model
      Frozen trees: 43
      Feature count: 63
[2/4] Assembling Snapshot B input vector for session 2026-11-02...
      Loaded input vector from: data/interim/phase14_shadow/input_2026-11-02_0850.json
[3/4] Validating Point-in-Time input vector...
      Validation: PASSED
[4/4] Generating frozen model prediction and updating ledger...
STATUS: Successfully recorded prediction pred_2026-11-02_0850
        Predicted T0: <PRED_VALUE> (<PRED_BPS> bps)
        Record Hash:  <HASH_HEX>
```

---

## 4. Post-Market Outcome Reconciliation ($\ge$ 15:30:00 IST)

After official cash market close (15:30 IST), retrieve the official NIFTY 50 cash Open and Close prices from NSE:
```powershell
.\.venv\Scripts\python.exe scripts/reconcile_shadow_outcomes.py --session-date 2026-11-02 --open <ACTUAL_OPEN> --close <ACTUAL_CLOSE> --source "NSE_OFFICIAL_CASH"
```

**Expected Successful Terminal Output**:
```
STATUS: Successfully reconciled outcome for session 2026-11-02
        Realized T0:     <T0_FLOAT> (<T0_BPS> bps)
        Prediction Err:  <ERR_FLOAT> (<MAE_BPS> bps MAE)
        Direction Match: <YES / NO>
        Outcome Hash:    <HASH_HEX>
```

---

## 5. Ledger Integrity & Forward Scorecard Audit

Verify the cryptographic chain across all recorded predictions and outcomes:
```powershell
.\.venv\Scripts\python.exe scripts/verify_shadow_ledger.py
```

**Expected Terminal Output**:
```
Total Prediction Records: 1
LEDGER INTEGRITY AUDIT: PASSED (Cryptographic chain intact)
Tip Hash: <TIP_HASH>
Total Reconciled Outcomes: 1

Forward Validation Scorecard (Prospective Live Only):
{
  "sample_size": 1,
  "period_start": "2026-11-02",
  "period_end": "2026-11-02",
  ...
}
```

---

## 6. Failure & Recovery Protocols

| Scenario | System Behavior | Operator Action |
|---|---|---|
| **Data Provider Stale / Unavailable** | Preflight or input validator fails closed. | Log blocking reason; **DO NOT fabricate input values**. Leave session unpredicted. |
| **Prediction Timestamp $> \text{08:50:00 IST}$** | Input validator raises `CUTOFF_TIME_ENFORCEMENT`. | Do not force execution. The session cannot qualify as a prospective Snapshot B prediction. |
| **Model Hash Drift** | `verify_frozen_model_artifacts` raises security exception. | **Halt immediately**. Inspect git repository status for unauthorized model changes. |
| **Accidental Duplicate Submission** | Ledger returns `DUPLICATE_IGNORED`. | Safe. Ledger preserves original record without modification or duplicate insertion. |
| **Market Close Prices Unavailable** | Reconciler raises error if executed $< \text{15:30:00 IST}$. | Wait until official daily bhavcopy / finalized candles are released by NSE. |
