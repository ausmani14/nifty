# PHASE 14 — STEP 5: OUTCOME RECONCILIATION & FORWARD RESEARCH REPORTING
## Target Alignment, Forward Metric Evaluation & Governance Checkpoints

**Phase**: Phase 14 (Step 5)  
**Date**: October 31, 2026  
**Status**: **IMPLEMENTED & VERIFIED**  
**Module**: `src/nifty_ai/shadow/reconciliation.py`  
**Storage**: `data/interim/phase14_shadow/shadow_outcomes_ledger.jsonl`  

---

## 1. Realized Outcome Acquisition & Exact Alignment

Outcome reconciliation runs strictly post-market ($\ge \text{15:30:00 Asia/Kolkata}$) when official daily cash market session prices are finalized.

### Strict Guarantees:
1. **Timing Enforcement**: Any reconciliation attempt prior to 15:30 IST is rejected.
2. **Deterministic Formula**:
   $$\mathbf{T0\_realized} = \frac{\text{Close}_T}{\text{Open}_T} - 1$$
3. **Exact Session Alignment**: An outcome can only be reconciled against an existing pre-market prediction matching the exact `session_date`. Unpredicted sessions or mismatched timestamps cannot be reconciled.
4. **Independent Ledger**: Reconciled outcomes are appended to `shadow_outcomes_ledger.jsonl`. Pre-market predictions in `shadow_predictions_ledger.jsonl` remain strictly immutable.

---

## 2. Forward Evaluation Metric Suite

Metrics are computed exclusively over records carrying `provenance_type == "prospective_live_capture"`. Historical backfills or synthetic fixtures are strictly excluded from forward performance scorecards.

### Registered Metrics:
- **Correlation**: Pearson IC ($r_p$, two-sided and one-sided p-values) and Spearman rank IC ($r_s$).
- **Forecast Errors**: MAE (bps) and RMSE (bps) compared directly to the Zero-Return Benchmark ($50.30$ bps MAE, $67.69$ bps RMSE).
- **Incremental $R^2$**: Evaluated against the frozen historical training mean ($\mu_{\text{train}} = -5.56\text{ bps}$).
- **Directional Accuracy**: Mean Directional Accuracy (MDA) compared against Always Short ($51.91\%$) and Zero Return.
- **Positioning Bias**: Counts of Long, Short, and Flat predictions.

---

## 3. Pre-Registered Monitoring Checkpoints

To eliminate interim p-hacking and selective stopping, reviews are scheduled at fixed sample milestones:
1. **$N = 60$ Prospective Sessions**: Operational integrity and data quality audit only. **Zero promotion decisions permitted.**
2. **$N = 120$ Prospective Sessions**: Interim descriptive review. **Zero promotion decisions permitted.**
3. **$N = 252$ Prospective Sessions (~1 Calendar Year)**: Formal annual econometric evaluation with dependence-aware adjustments (block-bootstrap or Newey-West) submitted to Quantitative Governance.
