# DAILY OPERATIONS RUNBOOK
## Cloud-Automated Daily Lifecycle for NIFTY AI

**Phase**: Master Cloud Implementation — Phase 14  
**Date**: October 31, 2026  
**Operating Mode**: **Fully Autonomous Cloud Execution (Zero Laptop Dependency)**  

---

## 1. Automated Daily Schedule (Indian Standard Time)

```
08:35 AM IST: Cloud Runner Starts Pre-Market Preparation
08:50 AM IST: Snapshot B Cutoff — Feature Freeze & Model Inference
08:51 AM IST: Ledger Commit & Website Data Export
09:15 AM IST: NSE Cash Market Opens (No trading action taken)
03:30 PM IST: NSE Cash Market Closes
03:40 PM IST: Cloud Runner Reconciles Realized Open & Close
03:41 PM IST: Outcome Ledger Commit & Forward Scorecard Update
```

---

## 2. Normal Daily Flow (Zero-Touch)

Under normal operating conditions, **no user intervention is required**.

1. **At 08:35 AM IST**:
   - GitHub Actions awakens automatically via cron.
   - It checks whether today is a regular NSE trading session.
   - It verifies frozen model integrity (`N*=43`, SHA-256 `981bbc80...`).
   - It executes Snapshot B inference at the 08:50 IST cutoff.
   - It appends the prediction to `shadow_predictions_ledger.jsonl`.
   - It exports updated JSON to `website_data/` and pushes the commit.
2. **During Market Hours (09:15 AM to 03:30 PM IST)**:
   - The dashboard displays the active forecast with status `RECONCILIATION PENDING`.
3. **At 03:40 PM IST**:
   - GitHub Actions awakens for afternoon reconciliation.
   - It verifies that the cash market is closed ($\ge 15:30$ IST).
   - It obtains the official NIFTY 50 cash Open and Close.
   - It computes realized return $T0 = (\text{Close} / \text{Open}) - 1$.
   - It records the outcome in `shadow_outcomes_ledger.jsonl` and updates website data.

---

## 3. Manual Operator Overrides & Triggers

If you wish to trigger an operation manually from your phone or desktop:

### Via GitHub Mobile App or Browser
1. Open the repository &rarr; **Actions** &rarr; **NIFTY AI Daily Shadow Operations**.
2. Tap **Run workflow**.
3. Choose the operation:
   - `snapshot_b`: Runs morning prediction.
   - `reconcile_outcomes`: Runs afternoon outcome reconciliation.
   - `health_check`: Verifies model and ledger integrity without creating predictions.
   - `dry_run`: Runs isolated end-to-end simulation in temporary directories.
4. Tap **Run workflow**.

### Via Local Command Line (Optional Backup)
```powershell
# Pre-market prediction
.\.venv\Scripts\python.exe scripts/run_daily_ops.py --operation snapshot_b

# Post-market reconciliation (with official prices)
.\.venv\Scripts\python.exe scripts/run_daily_ops.py --operation reconcile_outcomes --open 24200.0 --close 24250.0

# Ledger audit
.\.venv\Scripts\python.exe scripts/verify_shadow_ledger.py
```
