# WEBSITE DATA CONTRACT & FRONTEND INTEGRATION SPECIFICATION
## Standardized JSON Schemas for the NIFTY AI Web Dashboard

**Phase**: Master Cloud Implementation — Phase 9 & 10  
**Date**: October 31, 2026  
**Directory**: `website_data/`  
**Frontend**: `web/` (HTML5 / Vanilla JavaScript / CSS3)  

---

## 1. Architectural Overview

The NIFTY AI web dashboard runs as a zero-dependency static web application. It requires **no database server** and **no always-on backend process**. 

The daily cloud operations workflow periodically writes structured JSON files into `website_data/`. The client-side dashboard (`web/app.js`) fetches these static files over HTTPS and renders them into the UI.

```
[GitHub Actions Cloud Runner]
             │
             ▼
[writes static JSON files to website_data/]
             │
             ▼
[User's Static Host: GitHub Pages / Cloudflare Pages / Vercel / Netlify]
             │
             ▼
[User Browser loads web/index.html & reads website_data/*.json]
```

---

## 2. Standard JSON Schemas

### 2.1 `latest_prediction.json`
Exposes the single most recent prediction or current pre-market status.

```json
{
  "has_prediction": true,
  "prediction_id": "pred_2026-11-02_0850",
  "prediction_date": "2026-11-02",
  "target_date": "2026-11-02",
  "snapshot": "SNAPSHOT_0850",
  "expected_return": 0.00058388,
  "expected_return_bps": 5.84,
  "directional_bias": "POSITIVE",
  "prediction_status": "VALID",
  "outcome_status": "RECONCILIATION PENDING",
  "realized_outcome": null,
  "model_name": "Snapshot B T0 Full Development Production Model",
  "model_sha256": "981bbc806160090e339093686c61b660368427860451d9720824720dd031c5df",
  "information_cutoff": "08:50:00 Asia/Kolkata",
  "last_updated_utc": "2026-11-02T03:20:00Z",
  "message": "Prospective prediction active."
}
```

### 2.2 `prediction_history.json`
Historical array of all recorded prospective predictions.

```json
{
  "total_count": 1,
  "predictions": [
    {
      "prediction_id": "pred_2026-11-02_0850",
      "session_date": "2026-11-02",
      "target_date": "2026-11-02",
      "predicted_return": 0.00058388,
      "predicted_return_bps": 5.84,
      "record_hash": "...",
      "prev_record_hash": "0000000000000000000000000000000000000000000000000000000000000000"
    }
  ]
}
```

### 2.3 `outcome_history.json`
Historical array of post-market reconciled outcomes.

```json
{
  "total_count": 1,
  "outcomes": [
    {
      "outcome_id": "out_2026-11-02_T0",
      "prediction_id": "pred_2026-11-02_0850",
      "session_date": "2026-11-02",
      "realized_open": 24200.0,
      "realized_close": 24250.0,
      "realized_t0": 0.002066,
      "realized_t0_bps": 20.66,
      "prediction_error": -0.001482,
      "absolute_error_bps": 14.82,
      "directional_match": true,
      "status": "RECONCILED"
    }
  ]
}
```

### 2.4 `system_status.json`
Real-time system health, cryptographic tip hash, and scheduler state.

```json
{
  "current_system_state": "IMPLEMENTED — WAITING FOR LIVE INPUT",
  "last_updated_utc": "2026-10-31T20:00:00Z",
  "model_integrity": {
    "is_intact": true,
    "status": "PASS",
    "model_sha256": "981bbc80...",
    "n_estimators": 43,
    "feature_count": 63
  },
  "ledger_integrity": {
    "is_valid": true,
    "prediction_count": 0,
    "outcome_count": 0,
    "tip_hash": "00000000..."
  },
  "scheduler_status": "ENABLED"
}
```

### 2.5 `model_info.json`
Authoritative model identity, classification, and research governance disclaimers.

### 2.6 `performance_summary.json`
Forward metrics calculated exclusively on prospective observations, tracking progress toward the pre-registered checkpoints ($N=60, 120, 252$).

---

## 3. Critical Status Labels

The frontend strictly displays one of the following canonical status labels:
- `VALID`: Pre-market prediction successfully generated and verified.
- `NO VALID PREDICTION`: Initial state or session with no prediction recorded.
- `PENDING`: Waiting for 08:50 IST cutoff.
- `MISSED CUTOFF`: Execution started after 08:50:00 IST; prediction generation was blocked.
- `DATA SOURCE BLOCKED`: Market data feed unavailable; automated prediction halted.
- `MODEL INTEGRITY FAILURE`: Checksum mismatch; system halted.
- `RECONCILIATION PENDING`: Market open or in session; waiting for 15:30 IST close.
- `RECONCILED`: Session closed and outcome linked.
- `HOLIDAY`: Exchange holiday or weekend; no trading session.
- `SYSTEM ERROR`: Unhandled exception or runner failure.

---

## 4. Free Static Hosting Setup

Because `web/` consists of static HTML, CSS, and JavaScript, it can be hosted for **free** on any static web host:

### Option A: GitHub Pages (Recommended — Zero Extra Accounts)
1. In repository **Settings** &rarr; **Pages**.
2. Under **Build and deployment**:
   - Source: **Deploy from a branch**.
   - Branch: `master` (or `main`) &rarr; Folder: `/ (root)` or `/web`.
3. The dashboard is live at: `https://{username}.github.io/nifty-ai/web/`.

### Option B: Cloudflare Pages / Vercel / Netlify
1. Connect your private GitHub repository to Cloudflare Pages or Vercel.
2. Build command: None (Static site).
3. Output directory: `web`.
4. Deploy: Automatic upon every git commit pushed by GitHub Actions.
