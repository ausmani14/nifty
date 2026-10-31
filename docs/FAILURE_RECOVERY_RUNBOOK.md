# FAILURE RECOVERY & INCIDENT RUNBOOK
## Incident Triage, Diagnostic Protocols & Safe Recovery Procedures

**Phase**: Master Cloud Implementation — Phase 14  
**Date**: October 31, 2026  
**Auditor**: DevOps Engineer & Software Auditor  
**System**: NIFTY AI Automated Shadow System  

---

## 1. Failure Taxonomy & Automated Responses

| Incident Scenario | Automated System Behavior | Operational Severity | Safe Operator Action |
|---|---|---|---|
| **Data Feed Unavailable at 08:50 IST** | Fails closed; logs `DATA_SOURCE_BLOCKED`. Real ledger remains unmutated. | Medium | If verified data available before 08:50, pass `--input-file`. Otherwise, skip session. **Never fabricate values.** |
| **Workflow Started After 08:50 IST** | Raises `MISSED_CUTOFF`; halts prediction generation. | Low | Safe. Do not force late execution. The session cannot qualify as prospective Snapshot B. |
| **Model SHA-256 Mismatch** | Raises `MODEL_INTEGRITY_FAILURE`; immediately aborts. | **Critical** | Inspect git history. Restore frozen model from sealed manifest backup. |
| **Concurrent / Duplicate Triggers** | Returns `DUPLICATE_IGNORED`; preserves original entry. | Zero | None needed. Ledger idempotency guarantees exactly one entry per session. |
| **Git Push Conflict on Runner** | Automated workflow executes `git pull --rebase` (up to 3 retries). | Low | If all 3 fail, runner exits cleanly. Re-trigger via manual workflow dispatch. |
| **Delayed Market Close Data at 15:40 IST** | Leaves outcome `RECONCILIATION PENDING`. | Low | Wait until NSE finalizes official daily bhavcopy; re-trigger `reconcile_outcomes`. |

---

## 2. Step-by-Step Diagnostic Procedures

### 2.1 Diagnosing a Blocked Morning Prediction
1. Navigate to **Actions** in your GitHub repository.
2. Select the failed/blocked run &rarr; Click **execute-operation**.
3. Inspect step **Run Daily Operations CLI**.
4. Check error status:
   - If `DATA_SOURCE_BLOCKED`: The public chart API was rate-limited or unreachable.
   - If `MISSED_CUTOFF`: GitHub runner was queued past 08:50:00 IST.
5. In both cases, the ledger remains in a pristine state. The dashboard automatically displays `DATA_SOURCE_BLOCKED` or `MISSED CUTOFF`.

### 2.2 Recovering from a Model Integrity Failure
If `MODEL_INTEGRITY_FAILURE` occurs:
1. Verify the model file hash locally:
   ```powershell
   .\.venv\Scripts\python.exe -c "import hashlib; print(hashlib.sha256(open('data/interim/phase13_steps2_4/models/snapshot_b_t0_primary_model.json', 'rb').read()).hexdigest())"
   ```
2. The hash must equal:
   `981bbc806160090e339093686c61b660368427860451d9720824720dd031c5df`
3. If corrupted, restore the exact file from git commit history:
   ```powershell
   git checkout HEAD -- data/interim/phase13_steps2_4/models/snapshot_b_t0_primary_model.json
   ```

### 2.3 Resolving a Delayed Post-Market Reconciliation
If the 03:40 PM IST reconciliation did not find finalized cash prices:
1. Obtain the official NIFTY 50 cash Open and Close prices from NSE India (`www.nseindia.com`).
2. Open GitHub on mobile or desktop &rarr; **Actions** &rarr; **NIFTY AI Daily Shadow Operations**.
3. Tap **Run workflow** &rarr; Select `reconcile_outcomes`.
4. The workflow fetches latest prices, reconciles the outcome, updates `shadow_outcomes_ledger.jsonl`, and updates the dashboard.
