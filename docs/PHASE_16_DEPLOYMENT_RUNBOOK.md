# NIFTY AI — PHASE 16 CLOUD DEPLOYMENT & OPERATIONS RUNBOOK

**Target Architecture**: 100% Free-Tier Cloud Automation (GitHub Actions) & Free Static Dashboard (GitHub Pages / Cloudflare Pages)  
**Governance Standing**: **`RESEARCH BASELINE ONLY`** (Observational Forward Validation; Zero Broker Integration)  
**Cost**: **$0.00 / month** (Within GitHub Free Tier 2,000 monthly minutes)  

---

## 1. REPOSITORY PERMISSIONS & SETUP (ONE-TIME CONFIGURATION)

Before running scheduled operations in GitHub Actions, configure the following settings in your GitHub repository:

### Step 1.1: Enable Workflow Write Permissions
By default, GitHub Actions has read-only access to repository files. The autonomous shadow system requires write access to commit append-only ledger entries and updated website JSON files.
1. Open your repository on **GitHub.com**.
2. Navigate to **Settings** (top menu bar) &rarr; **Actions** (left sidebar) &rarr; **General**.
3. Scroll down to **Workflow permissions**.
4. Select **"Read and write permissions"**.
5. Check the box: **"Allow GitHub Actions to create and approve pull requests"**.
6. Click **Save**.

### Step 1.2: Initialize Remote and Push Code
If the repository has not yet been pushed to GitHub:
```bash
# Set default branch to master (or main)
git branch -M master

# Add your GitHub remote repository URL
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPOSITORY_NAME>.git

# Stage all files and create genesis commit
git add .
git commit -m "feat(phase16): Complete verified deployment readiness and master cloud automation"

# Push to GitHub
git push -u origin master
```

---

## 2. STATIC DASHBOARD HOSTING OPTIONS

Choose the hosting option that matches your repository's visibility:

### Option A: Public Repository &rarr; Free GitHub Pages (Recommended)
If your repository is **Public**, GitHub Pages is 100% free with unlimited static hosting.

#### Method 1: GitHub Actions Deployment (Recommended — Instant Automated JSON Updates)
1. Go to repository **Settings** &rarr; **Pages** (left sidebar).
2. Under **Build and deployment** &rarr; **Source**, select **"GitHub Actions"**.
3. That's it! The daily cloud workflow `.github/workflows/daily_shadow_ops.yml` includes built-in `actions/deploy-pages` steps that publish the `web/` directory directly upon every scheduled execution.
4. Your live dashboard URL will be:
   `https://<YOUR_GITHUB_USERNAME>.github.io/<YOUR_REPOSITORY_NAME>/`

#### Method 2: Classic Branch Deployment (Root Redirect)
*Note: GitHub Pages branch publishing only supports `/ (root)` and `/docs` folders (arbitrary folders like `/web` are not supported by GitHub).*
1. Go to repository **Settings** &rarr; **Pages**.
2. Under **Build and deployment** &rarr; **Source**, select **"Deploy from a branch"**.
3. Under **Branch**, select **`master`** and folder **`/ (root)`**.
4. Click **Save**.
5. The repository's root `index.html` will automatically load and forward visitors seamlessly to `web/`.

### Option B: Private Repository &rarr; Free Cloudflare Pages
If your repository is **Private** and you do not have a paid GitHub Pro/Team subscription:
1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/) (100% Free account).
2. Navigate to **Workers & Pages** &rarr; **Create application** &rarr; **Pages** &rarr; **Connect to Git**.
3. Select your private GitHub repository `nifty-ai`.
4. Configure Build settings:
   - **Framework preset**: `None`
   - **Build command**: *(leave blank)*
   - **Build output directory**: `web`
5. Click **Save and Deploy**.
6. Your live dashboard URL will be provisioned immediately:
   `https://<project-name>.pages.dev/`

---

## 3. HOW TO TRIGGER WORKFLOWS MANUALLY

In addition to autonomous cron execution, you can trigger operations manually anytime:

### 3.1 Preflight Health Check (Safe Audit)
Audits frozen model hashes, verifies ledger hash chaining, and refreshes website exports without altering ledgers:
1. Go to the **Actions** tab on GitHub.
2. In the left sidebar, click **"NIFTY AI Daily Shadow Operations"**.
3. Click the **Run workflow** dropdown button (on the right).
4. Select `operation`: **`health_check`**.
5. Click **Run workflow**.
6. Verify green checkmark in ~45 seconds.

### 3.2 Dry Run Simulation (Full Pipeline Sandbox)
Simulates synthetic point-in-time capture, XGBoost inference, outcome reconciliation, and export in a temporary memory workspace without touching real ledgers:
1. In the **Actions** tab, select **"NIFTY AI Daily Shadow Operations"**.
2. Click **Run workflow**.
3. Select `operation`: **`dry_run`**.
4. Click **Run workflow**.

### 3.3 Manual Morning Prediction (`snapshot_b`)
If you wish to trigger morning prediction manually between 08:35 AM and 08:50 AM IST:
1. Select `operation`: **`snapshot_b`**.
2. *(Optional)* Provide `--input-file` if injecting an authenticated point-in-time JSON vector.
3. Click **Run workflow**.

---

## 4. AUTOMATED DAILY SCHEDULE LIFECYCLE

The cloud workflow runs autonomously on GitHub Actions every trading day (Monday through Friday):

```
08:35 AM IST (03:05 UTC)           08:50 AM IST                      15:40 PM IST (10:10 UTC)
     │                                  │                                  │
     ▼                                  ▼                                  ▼
[Workflow Awakens]             [Snapshot B Cutoff]               [Reconciliation Run]
- Model SHA-256 audit          - Finalize 63-feature vector      - Ingest cash Open & Close
- Calendar verification        - Execute frozen XGBoost          - Calculate realized T0
- Await cutoff boundary        - Append to predictions ledger    - Append to outcomes ledger
                               - Push website JSON data          - Update performance summary
```

---

## 5. MONITORING & VERIFYING OPERATIONS

### 5.1 How to Check Website JSON Updates
1. Visit your hosted dashboard URL.
2. Check the **Overview** tab:
   - **System State**: Should display `PREDICTION_RECORDED`, `DATA_SOURCE_BLOCKED`, or `RECONCILED`.
   - **Target Session**: Should show the current or next trading date (`YYYY-MM-DD`).
   - **Last Updated**: Shown in Indian Standard Time (**IST**).
3. If inspecting raw JSON files directly in browser or curl:
   - `https://<YOUR_DASHBOARD_URL>/data/latest_prediction.json`
   - `https://<YOUR_DASHBOARD_URL>/data/system_status.json`

### 5.2 How to Distinguish a Blocked Data Capture from a Valid Prediction
- **`VALID` (Green Badge)**: Genuine point-in-time feature vector was successfully validated prior to 08:50 IST and model inference recorded in ledger.
- **`DATA_SOURCE_BLOCKED` (Orange Badge)**: Free market-data feed could not provide verified point-in-time provenance at 08:50 IST. System safely halted without fabricating numbers.
- **`MISSED_CUTOFF` (Red Badge)**: Workflow started after 08:50:00 IST. Execution aborted to protect prospective purity.

### 5.3 How to Confirm Real Ledger Entries
Inspect the physical append-only ledgers in your repository:
- Predictions: `data/interim/phase14_shadow/shadow_predictions_ledger.jsonl`
- Outcomes: `data/interim/phase14_shadow/shadow_outcomes_ledger.jsonl`
Every valid record contains:
- `prediction_id`: Unique session identifier (e.g., `pred_2026-11-02_0850`).
- `predicted_return_bps`: Basis-point forecast ($T0$).
- `record_hash`: SHA-256 hash mathematically linked to `prev_record_hash`.

---

## 6. WHAT TO DO IF FREE DATA FEEDS ARE BLOCKED

Under Phase 14–16 zero-fabrication governance, the system **never** guesses or substitutes fake data when free public feeds (e.g. Yahoo Finance) experience downtime, formatting shifts, or rate limits.

If live public capture reports `DATA_SOURCE_BLOCKED`, the operator can inject a verified point-in-time input vector:
1. Export the verified 63 features available as of 08:50 IST into a JSON file formatted per `FeatureVector` schema:
   ```json
   {
     "session_date": "2026-11-02",
     "cutoff_time": "2026-11-02T08:50:00+05:30",
     "feature_names": ["ret_1d", "ret_2d", ...],
     "feature_values": [0.0012, -0.0034, ...],
     "feature_hash": "<SHA-256>",
     "provenance": {
       "source_id": "verified_terminal_feed",
       "observation_time": "2026-11-02T08:45:00+05:30",
       "availability_time": "2026-11-02T08:48:00+05:30",
       "ingestion_time": "2026-11-02T08:49:00+05:30",
       "provenance_type": "prospective_live_capture"
     }
   }
   ```
2. Commit the file to `data/inputs/pit_vector_2026-11-02.json` or pass via workflow dispatch:
   `--input-file data/inputs/pit_vector_2026-11-02.json`
3. The system will validate the schema, check the hash, verify point-in-time eligibility, and run inference cleanly.
