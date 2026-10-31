# GITHUB ACTIONS CLOUD AUTOMATION SETUP
## Cloud-Operated Daily Forecasting System for NIFTY AI

**Phase**: Master Cloud Implementation — Phase 3 & 4  
**Date**: October 31, 2026  
**Target Environment**: GitHub Actions (`ubuntu-latest`, Python 3.13)  
**Governance**: **Zero Paid Resources &bull; Least-Privilege Scoped Permissions**  

---

## 1. Overview

The NIFTY AI cloud runner operates inside GitHub's cloud environment on a standard scheduled cron, completely eliminating the need to leave a laptop running overnight.

### Daily Cloud Schedule (Indian Standard Time):
- **08:35 AM IST (03:05 UTC)**: Pre-market preparation and Snapshot B prediction generation.
- **03:40 PM IST (10:10 UTC)**: Post-market outcome reconciliation against finalized cash market prices.

---

## 2. Mandatory GitHub Repository Settings

To allow the automated workflow to record predictions in the append-only ledger and push static website updates back to the repository, configure **Workflow Permissions**:

1. Open your `nifty-ai` repository on GitHub.
2. Click **Settings** (top navigation bar).
3. In the left sidebar, expand **Actions** &rarr; click **General**.
4. Scroll down to **Workflow permissions**:
   - Select **Read and write permissions** *(Allows `GITHUB_TOKEN` to commit validated ledger records and website data).*
   - Check the box: **Allow GitHub Actions to create and approve pull requests** (optional, recommended).
5. Click **Save**.

---

## 3. Workflow File Location & Architecture

The workflow configuration resides at:
`.github/workflows/daily_shadow_ops.yml`

### Core Workflow Features:
- **Zero Overhead**: Caches `pip` packages so subsequent runs complete in under 60 seconds.
- **Concurrency Guard**: Uses `concurrency: group: nifty-ai-daily-shadow-ops, cancel-in-progress: false` to prevent race conditions or simultaneous ledger writes.
- **Selective Commit Scope**: Only stages `shadow_predictions_ledger.jsonl`, `shadow_outcomes_ledger.jsonl`, and `website_data/*.json`. Never touches or commits model binaries, secrets, or temporary files.
- **Conflict Resilience**: Implements bounded rebase retry (`git pull --rebase`) in case of concurrent git updates.

---

## 4. Triggering a Test Run (Manual Dispatch)

You can verify the cloud runner immediately from your desktop or phone without waiting for the scheduled time:

1. In your GitHub repository, click the **Actions** tab.
2. In the left menu, select **NIFTY AI Daily Shadow Operations**.
3. Click the **Run workflow** dropdown on the right.
4. Select the operation to test:
   - `health_check`: Runs preflight model check and ledger audit (Safe, zero mutation).
   - `dry_run`: Executes end-to-end synthetic prediction and reconciliation in temporary directory.
   - `snapshot_b`: Executes morning prediction (if 08:50 IST cutoff criteria are met).
   - `reconcile_outcomes`: Executes post-market outcome reconciliation.
5. Click the green **Run workflow** button.
6. Refresh the page after 15 seconds to view the running job, terminal output, and job summary.

---

## 5. Reviewing Execution Logs and Workflow Summaries

Every run automatically appends a structured summary to the GitHub Actions run summary page:
- **Operation**: e.g. `snapshot_b`
- **Trigger**: `schedule` or `workflow_dispatch`
- **Timestamp (UTC)**: Verified execution timestamp
- **Prediction Status**: e.g. `VALID` or `DATA_SOURCE_BLOCKED`
- **Ledger Verification**: Status of cryptographic tip hash chaining.
