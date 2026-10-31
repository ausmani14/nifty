# PHASE 14 — STEP 1: PROSPECTIVE RESEARCH PROTOCOL FREEZE
## Prospective Shadow Prediction & Forward Validation Protocol

**Phase**: Phase 14 (Step 1)  
**Date**: October 31, 2026  
**Status**: **FROZEN & IMMUTABLE**  
**Role**: Senior Quantitative Research Engineer, ML Systems Architect, Financial Data Integrity Auditor, and Research Governance Specialist  
**System Status**: **`RESEARCH_BASELINE_ONLY`** (Zero Live Trading Authorization)  

---

## 1. Executive Summary & Authoritative Roadmap Reconciliation

### 1.1 Master Specification Reconciliation
In `MASTER_SPECIFICATION.md` Section 19, Phase 14 was originally designated as *Paper-Trading Execution Engine (Virtual order lifecycle, risk controls, daily snapshot execution)*. 

However, Phase 13 Step 5 formally evaluated the primary candidate model across all 8 pre-registered promotion criteria and sealed its final disposition as **`RESEARCH BASELINE ONLY`**:
- Statistical significance failed ($r_p = +0.02013, p = 0.4945$).
- Regression errors were worse than the zero-return benchmark.
- Incremental $R^2$ was negative ($-0.003574$).
- Net annualized return under realistic costs was heavily negative ($-13.96\%$ at 10 bps, $-33.15\%$ at 20 bps).
- Live real-money trading was **strictly disqualified**.

Under strict research governance, virtual order routing and execution simulation of an unpromoted, economically negative baseline model would violate capital safety principles. Therefore, Phase 14 is authoritatively instantiated as a **Prospective Shadow Prediction & Forward Validation System**. 

This system observes whether the frozen Snapshot B $T0$ predictive model can generate reproducible, point-in-time compliant predictions on genuinely future sessions before market open (08:50 IST), recording them in an immutable ledger and evaluating them against realized daytime returns ($T0$) after market close (15:30 IST).

### 1.2 Core Research Question
> *"Can the frozen Snapshot B $T0$ research-baseline model ($N^*=43$ trees, 63 features) demonstrate stable, point-in-time predictive association and bounded forecast error on genuinely prospective, unexposed NIFTY 50 trading sessions when evaluated in an append-only forward shadow framework?"*

---

## 2. Prospective Activation Boundary & Provenance Taxonomy

### 2.1 Activation Boundary
- **System Activation Timestamp (UTC)**: `2026-10-31T14:47:00Z`
- **System Activation Timestamp (IST)**: `2026-10-31 20:17:00 Asia/Kolkata`
- **Rule**: The first qualifying prospective prediction session must occur strictly **after** this activation boundary.
- **Prohibition of Backdating**: No completed historical trading session (e.g. data $\le 2026-09-03$ or historical partitions) may ever be designated as prospective.
- **Missing Inputs**: If real-time or verified daily inputs are unavailable at 08:50 IST, the session must be recorded as **BLOCKED** with a documented root cause; **no fabricated prediction may be generated**.

### 2.2 Data Provenance Taxonomy
Every record entering the Phase 14 shadow system must carry an unambiguous provenance tag:

1. **`prospective_live_capture`**: A point-in-time observation captured in real-time or verified point-in-time before 08:50 IST for a future trading session, executed strictly after the activation boundary. **Only this class enters prospective performance statistics.**
2. **`historical_backfill`**: Data loaded from retrospective periods to populate historical feature lookbacks (e.g. 200-day rolling SMAs). Strictly prohibited from entering forward statistical scorecards.
3. **`retrospective_reference`**: Baseline reference results from Phase 12 or Phase 13, maintained solely for comparative benchmarking.
4. **`invalid_or_quarantined`**: Inputs failing point-in-time validation, timestamp checks, or completeness constraints. Blocked from prediction generation.

---

## 3. Snapshot B Information Contract

### 3.1 Timing & Cutoff
- **Snapshot Designation**: `SNAPSHOT_0850`
- **Information Cutoff**: `08:50:00 Asia/Kolkata`
- **Execution Window**: 08:50:00 to 08:55:00 IST on trading day $T$.

### 3.2 Eligible Information
1. **NIFTY 50 Daily Price History**: Finalized daily OHLCV records through Day $T-1$ ($15:30$ IST close of the previous trading day).
2. **45 Price Features**: Standard technical, momentum, volatility, and calendar features computed strictly on data $\le T-1$.
3. **18 Market-Context Features**: Global indices, commodities, currencies, and fixed income metrics satisfying the Phase 7 point-in-time publication availability contract (e.g., US market closes and Asian pre-market levels published prior to 08:50 IST).
4. **Feature Count & Ordering**: Exactly **63 features** matching the registered sequence of `snapshot_b_t0_primary_model.meta.json`.

### 3.3 Strictly Forbidden Information
1. **Current-Session Prices**: Day $T$ Open, High, Low, Close, or Volume.
2. **Future Realized Returns**: Same-day or future returns.
3. **Post-Cutoff Context**: Any macro or global indicator timestamped after 08:50:00 IST on Day $T$.
4. **Retrospectively Revised Data**: Revisions published after 08:50 IST.
5. **Excluded Feature Families**: Zero news features, zero volume features, zero flow features, zero experimental features.

---

## 4. Target Contract

### 4.1 Target Definition
$$\mathbf{T0\_return} = \frac{\text{Close}_T}{\text{Open}_T} - 1$$

- **Target Identifier**: `T0` (Snapshot B Daytime Intraday Return).
- **Target Realization Timestamp**: $\ge 15:30:00 \text{ Asia/Kolkata}$ on Day $T$ (after official cash market close).
- **Temporal Alignment**:
  $$\text{Prediction Timestamp } \le \text{08:50:00 IST (Day } T) < \text{Session Open (09:15:00 IST)} < \text{Session Close (15:30:00 IST)}$$
  The prediction **must exist in the append-only ledger** before the market opens and before the target return is realized.

---

## 5. Frozen Model Identity & Verification

The primary model is immutable and sealed:
- **Model Name**: Snapshot B T0 Full Development Production Model
- **Algorithm**: `xgboost.XGBRegressor`
- **Hyperparameters**: `n_estimators=43`, `learning_rate=0.05`, `max_depth=2`, `min_child_weight=20.0`, `subsample=0.8`, `colsample_bytree=0.7`, `reg_alpha=0.5`, `reg_lambda=2.0`, `random_state=42`
- **Training Boundary**: $2008-07-08$ through $2021-12-31$ ($N=3,299$ sessions)
- **Model Binary SHA-256**: `981bbc806160090e339093686c61b660368427860451d9720824720dd031c5df`
- **Model Metadata SHA-256**: `d64fee485721cc4e2596e8fd10039d9ea2a7e41ce84b90e19b6bd994ea5d7f33`
- **Retraining / Parameter Tuning**: Strictly forbidden.

---

## 6. Forward Evaluation & Monitoring Checkpoints

To prevent informal p-hacking and multiple-testing bias, forward evaluation is restricted to pre-registered sample milestones:

1. **Checkpoint 1 ($N = 60$ Prospective Sessions)**:
   - **Scope**: Data quality, pipeline uptime, point-in-time timestamp verification, input feature integrity.
   - **Restriction**: **No performance assessment or promotion decisions permitted.**
2. **Checkpoint 2 ($N = 120$ Prospective Sessions)**:
   - **Scope**: Interim descriptive scorecard (realized vs predicted distribution, MAE, directional accuracy).
   - **Restriction**: Descriptive research review only. No promotion decisions permitted.
3. **Checkpoint 3 ($N = 252$ Prospective Sessions — ~1 Calendar Year)**:
   - **Scope**: Formal annual statistical and econometric evaluation:
     - Pearson IC and Spearman rank IC with block-bootstrap or Newey-West adjustment.
     - Incremental $R^2$ vs historical training mean baseline ($\mu_{\text{train}} = -0.0556\%$).
     - Regression MAE/RMSE vs zero-return benchmark.
     - Net economic return under 5 bps, 10 bps, and 20 bps transaction frictions.
   - **Decision Gate**: Formal review by Quantitative Governance Committee.

---

## 7. Governance Invariants

1. **Research Status**: Every prediction record must have `research_status = "RESEARCH_BASELINE_ONLY"` and `trading_authorized = false`.
2. **Zero Automated Execution**: No orders or brokerage API credentials exist in this system.
3. **Immutable Hash Chaining**: Every prediction entry is hashed and appended to a tamper-evident ledger.
4. **Separation of Concerns**: Predictions and outcomes are stored in distinct records and joined via unique prediction IDs.
