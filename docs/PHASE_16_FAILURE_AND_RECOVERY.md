# NIFTY AI — PHASE 16 FAILURE & RECOVERY RUNBOOK

**Classification**: Emergency Operating Procedures & Failure Recovery  
**Target Subsystems**: GitHub Actions Automation, Append-Only Ledgers, Frozen Model Integrity, Website Mirroring  

---

## 1. INCIDENT TRIAGE MATRIX

| Failure Code | Severity | Root Cause | System Response | Recovery Action |
| :--- | :--- | :--- | :--- | :--- |
| `MISSED_CUTOFF` | Low | GitHub Actions queue delay or late manual trigger past 08:50:00 IST | Aborts prediction generation; logs `MISSED CUTOFF` to dashboard | No action required. Next trading day will execute normally. Backdating is prohibited. |
| `DATA_SOURCE_BLOCKED` | Low | Free public market data API unreachable or format changed | Fails closed; exports `DATA_SOURCE_BLOCKED` state | Inspect network/provider; optionally inject verified point-in-time input vector via `--input-file`. |
| `MODEL_INTEGRITY_FAILURE` | **Critical** | Model file bytes or metadata altered, or non-matching SHA-256 | Immediate fatal abort; blocks all inference operations | Restore frozen model artifact from sealed Phase 13 backup. |
| `LEDGER_CORRUPTED` | **Critical** | Record tampered or hash chain broken in prediction ledger | Halts operations; flags chain corruption on dashboard | Run `scripts/verify_shadow_ledger.py` to identify offending record; revert corrupted line from Git history. |
| `GIT_PUSH_CONFLICT` | Medium | Concurrent commit on remote branch rejected runner push | Runner retries 3 times with rebase before failing | Workflow automatically runs `git pull --rebase origin master`. If failed, re-run workflow dispatch. |
| `STALE_WEBSITE_JSON` | Low | Browser cache or failed commit step | Frontend displays older IST timestamp | Hard refresh browser (`Ctrl+F5`); verify GitHub Actions commit step succeeded. |

---

## 2. RECOVERY PROCEDURES BY FAILURE TYPE

### 2.1 Recovery: Model Integrity Failure (`MODEL_INTEGRITY_FAILURE`)
If an operator accidentally edits, overwrites, or reformats the frozen model or metadata:
```bash
# 1. Run local audit to inspect error details
python -c "from nifty_ai.shadow.model_protection import assert_frozen_model_intact; assert_frozen_model_intact()"

# 2. Check Git diff on the model directory
git diff data/interim/phase13_steps2_4/models/

# 3. Restore frozen model and metadata from clean Git commit
git checkout HEAD -- data/interim/phase13_steps2_4/models/snapshot_b_t0_primary_model.json
git checkout HEAD -- data/interim/phase13_steps2_4/models/snapshot_b_t0_primary_model.meta.json

# 4. Re-verify SHA-256 matches registered canonical hash
python -c "from nifty_ai.shadow.model_protection import assert_frozen_model_intact; print('Model Intact:', assert_frozen_model_intact().is_intact)"
```

### 2.2 Recovery: Ledger Hash Chain Corruption
If a line in `shadow_predictions_ledger.jsonl` was edited manually or truncated:
```bash
# 1. Run ledger audit script
python scripts/verify_shadow_ledger.py

# 2. The script will identify the exact record index and broken hash link:
# Broken hash chain at record pred_YYYY-MM-DD_0850 (index N): prev_record_hash ... != expected ...

# 3. If an unauthorized edit occurred, restore the ledger from the last verified commit:
git checkout HEAD~1 -- data/interim/phase14_shadow/shadow_predictions_ledger.jsonl

# 4. Re-run verification:
python scripts/verify_shadow_ledger.py
```

### 2.3 Recovery: Missed Cutoff / Delayed Runner
If high GitHub Actions traffic causes a 03:05 UTC (08:35 IST) scheduled workflow to queue until 08:52 IST:
1. The system detects `now_ist.time() > 08:50:00` and immediately halts.
2. It exports `current_system_state: "MISSED CUTOFF"`.
3. **DO NOT** attempt to bypass the cutoff or force a delayed prediction.
4. The system is designed to preserve research validity over uptime; missing a single session is infinitely better than introducing lookahead leakage.
5. In the afternoon at 15:40 IST, reconciliation will recognize that no prediction was generated for the session and skip evaluation safely.

### 2.4 Recovery: Git Push Conflicts
If a scheduled runner fails at the push step due to conflicting manual commits:
```bash
# In your local repository:
git pull --rebase origin master
git push origin master

# Then trigger manual health check to sync website data:
python scripts/run_daily_ops.py --operation health_check
```

---

## 3. EMERGENCY KILL-SWITCH & RESET PROCEDURE

If the autonomous workflow ever needs to be paused:
1. Go to repository **Actions** tab.
2. Select **"NIFTY AI Daily Shadow Operations"**.
3. Click the **"..."** (three dots) icon at the top right of the workflow list and select **"Disable workflow"**.
4. To resume operations, click **"Enable workflow"**.
