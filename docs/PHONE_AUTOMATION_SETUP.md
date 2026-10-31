# PHONE AUTOMATION SETUP GUIDE
## Android MacroDroid & GitHub Mobile Remote Triggers for NIFTY AI

**Phase**: Master Cloud Implementation — Phase 5  
**Auditor / Architect**: DevOps Engineer & Research Governance Specialist  
**System**: NIFTY AI Prospective Shadow Prediction Framework  
**Governance**: **Observational Trigger Only — The Phone Never Runs Models or Stores Ledgers**  

---

## 1. Operating Principle & Role of the Mobile Phone

In this cloud architecture, **all machine learning inference, data validation, and append-only ledger storage run exclusively on GitHub Actions cloud infrastructure**.

The user's laptop does **not** need to stay awake or powered on. The mobile phone acts strictly as an **optional, remote webhook trigger** sending an authenticated HTTP request to GitHub's REST API. If the phone is offline, powered down, or out of battery, the native GitHub Actions schedule automatically fires in the cloud as the primary cron runner.

---

## 2. Generating a Fine-Grained GitHub Personal Access Token (PAT)

To allow your phone to trigger GitHub Actions without granting access to any other repository or account setting, configure a fine-grained token with **least-privilege access**:

1. On a desktop or mobile browser, navigate to:  
   **GitHub Settings** &rarr; **Developer Settings** &rarr; **Personal Access Tokens** &rarr; **Fine-grained tokens**  
   (Direct link: `https://github.com/settings/tokens?type=beta`)
2. Click **Generate new token**.
3. Fill in the token details:
   - **Token name**: `NiftyAI-Phone-Trigger`
   - **Expiration**: Select `90 days` (recommended for periodic security rotation).
   - **Repository access**: Select **Only select repositories**, then choose `nifty-ai` (your private repository).
   - **Permissions** &rarr; **Repository permissions**:
     - Locate **Actions**: Select **Access: Read and write**.
     - (All other permissions should remain set to *No access*).
4. Click **Generate token**.
5. Copy the generated token string (`github_pat_...`).  
   > [!IMPORTANT]
   > Never share this token, commit it to git, or paste it in public forums. Store it securely in a password manager.

---

## 3. Configuring Android MacroDroid (Free Version Compatible)

MacroDroid is a free automation app available on the Google Play Store. It supports HTTP requests and time-of-day triggers without requiring root access.

### Automation 1: Morning Snapshot B Trigger (08:35 AM IST)
1. Open **MacroDroid** &rarr; Tap **Add Macro**.
2. **Name**: `NIFTY AI - 08:35 AM Snapshot B`.
3. **Trigger (+)**:
   - Tap **Date/Time** &rarr; **Regular Interval / Day of Week** (or **Time of Day**).
   - Set time: `08:35 AM`.
   - Days: Check `Monday, Tuesday, Wednesday, Thursday, Friday` (uncheck Saturday and Sunday).
4. **Action (+)**:
   - Tap **Connectivity** &rarr; **HTTP Request**.
   - **Method**: `POST`.
   - **URL**:
     ```
     https://api.github.com/repos/{YOUR_GITHUB_USERNAME}/nifty-ai/actions/workflows/daily_shadow_ops.yml/dispatches
     ```
     *(Replace `{YOUR_GITHUB_USERNAME}` with your exact GitHub username).*
   - **Request Headers**:
     - `Authorization`: `Bearer github_pat_YOUR_TOKEN_HERE`
     - `Accept`: `application/vnd.github+json`
     - `X-GitHub-Api-Version`: `2022-11-28`
     - `User-Agent`: `MacroDroid-NiftyAI-Trigger`
   - **Content-Type**: `application/json`
   - **Request Body**:
     ```json
     {"ref": "master", "inputs": {"operation": "snapshot_b"}}
     ```
5. Tap the tick mark & Save the macro.

---

### Automation 2: Afternoon Reconciliation Trigger (03:40 PM IST)
1. Add a second macro: `NIFTY AI - 03:40 PM Reconcile`.
2. **Trigger (+)**:
   - **Time of Day**: `03:40 PM`, Monday through Friday.
3. **Action (+)**:
   - Same HTTP POST endpoint.
   - **Request Body**:
     ```json
     {"ref": "master", "inputs": {"operation": "reconcile_outcomes"}}
     ```
4. Save the macro.

---

## 4. Android Reliability & Battery Optimization Settings

Android's aggressive background power-saving can suspend automation apps when the phone is locked. To guarantee execution:
1. **Disable Battery Optimization**:
   - Go to phone **Settings** &rarr; **Apps** &rarr; **MacroDroid** &rarr; **Battery**.
   - Change from *Optimized* to **Unrestricted**.
2. **Autostart / Background Run**:
   - On Xiaomi/MIUI/OnePlus/Oppo/Samsung devices: Enable **Autostart** and allow background activity.
3. **Network Availability**:
   - If the phone has no internet connection at 08:35 IST, the phone request will fail silently. However, the cloud **GitHub Actions schedule** will execute anyway.

---

## 5. Zero-App Manual Mobile Fallback (GitHub Mobile App)

If you do not want to install MacroDroid or want a zero-configuration manual backup:
1. Install the official **GitHub Mobile** app on Android or iOS (or open GitHub in your mobile browser).
2. Open your `nifty-ai` repository.
3. Tap **Actions** &rarr; Select **NIFTY AI Daily Shadow Operations**.
4. Tap **Run workflow**.
5. Select the operation:
   - `snapshot_b` (Pre-market prediction)
   - `reconcile_outcomes` (Post-market reconciliation)
   - `health_check` (Preflight audit)
   - `dry_run` (Isolated test)
6. Tap **Run workflow**.
7. The cloud runner starts immediately and completes within 60–90 seconds.

---

## 6. Token Rotation and Revocation

If your phone is lost, replaced, or your token expires:
1. Visit `https://github.com/settings/tokens?type=beta`.
2. Select `NiftyAI-Phone-Trigger`.
3. Click **Revoke** or **Regenerate token**.
4. The cloud runner and GitHub Actions schedules continue running with zero downtime because the cloud uses GitHub's internal runner token (`GITHUB_TOKEN`), not your personal phone token.
