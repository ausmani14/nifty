# FREE-TIER COST, LIMITS & SECURITY GOVERNANCE
## Zero-Cost Operations & Infrastructure Capacity Accounting for NIFTY AI

**Phase**: Master Cloud Implementation — Phase 12  
**Auditor**: DevOps Engineer & Financial Data Integrity Auditor  
**Date**: October 31, 2026  
**Infrastructure Target**: **Zero Monthly Infrastructure Cost ($0.00 / month)**  

---

## 1. GitHub Actions Free Allowance Accounting

Every free GitHub user account receives **2,000 free runner minutes per month** on Linux runners (`ubuntu-latest`).

### 1.1 Daily Execution Profile
| Operation | Scheduled Time (IST) | Tasks Executed | Typical Duration | Billable Runner Minutes |
|---|---|---|---|---|
| **Snapshot B** | 08:35–08:50 AM (Mon–Fri) | Setup, dependency cache restore, model audit, inference, ledger commit | 60–75 seconds | ~1.2 min |
| **Reconcile** | 03:40 PM (Mon–Fri) | Outcome acquisition, alignment, error metrics, website JSON export, commit | 45–60 seconds | ~0.9 min |
| **Daily Total** | — | 2 cloud executions | ~120 seconds | **~2.1 min / day** |

### 1.2 Monthly Consumption Estimate
- Average trading days per calendar month: **21 days**.
- Monthly Actions consumption:
  $$\text{Monthly Minutes} = 21 \text{ days} \times 2.1 \text{ min/day} \approx \mathbf{44.1 \text{ minutes / month}}$$
- **Quota Utilization**:
  $$\frac{44.1 \text{ minutes}}{2,000 \text{ free minutes}} = \mathbf{2.20\%}$$
- **Safety Margin**: **97.8% of the free quota remains untouched** for routine testing, manual dispatches, and ad-hoc audits.

---

## 2. Storage & Repository Size Impact

NIFTY AI persists predictions and outcomes directly in the repository via append-only JSONL files:
- Each prediction record in `shadow_predictions_ledger.jsonl`: **~550 bytes**.
- Each outcome record in `shadow_outcomes_ledger.jsonl`: **~450 bytes**.
- Total per trading day: **~1.0 KB**.
- Annual forward ledger growth (252 sessions):
  $$252 \times 1.0 \text{ KB} \approx \mathbf{252 \text{ KB / year}}$$
- **GitHub Repository Size Limit**: Standard personal repositories allow up to 1–2 GB. At 252 KB/year, thousands of years of forward shadow predictions can be stored without exceeding free repository storage limits.

---

## 3. Strict Free-Tier Safeguards (Zero Paid Overage)

1. **GitHub Spending Limit**: Always keep the GitHub account spending limit at **$0.00** (default). Navigate to:
   `https://github.com/settings/billing` &rarr; Ensure *Spending Limit* is set to **$0.00**.
2. **Fail-Closed Limit Policy**: If the 2,000 free minute quota is ever exhausted (e.g. from unrelated projects or long-running tests), GitHub halts further scheduled Actions runs and marks them queued or cancelled. The system reports `FREE_TIER_LIMIT_REACHED` instead of auto-provisioning billable resources.
3. **Prohibited Paid Infrastructure**: The project strictly prohibits:
   - AWS / GCP / Azure compute instances.
   - Cloud SQL / Supabase / Redis databases.
   - Paid financial API subscriptions (e.g. Bloomberg / Refinitiv / paid Bloomberg terminal feeds).
   - Paid web hosting tiers.

---

## 4. Security & Credential Hygiene

- **Repository Secrets**: GitHub Actions uses the built-in runner token (`secrets.GITHUB_TOKEN`) with scoped `contents: write` permissions. No external repository secrets are required for daily cloud operation.
- **Mobile PAT Token**: If using MacroDroid on an Android phone, the fine-grained PAT is stored exclusively inside the phone's secure storage. It is never logged, never committed, and never exposed in workflow runs.
- **Private Repository Protection**: The repository remains private. The static website dashboard in `web/` reads static data from `website_data/` and requires no database credentials or backend secrets.
