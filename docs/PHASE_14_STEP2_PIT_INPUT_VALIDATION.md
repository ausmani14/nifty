# PHASE 14 — STEP 2: POINT-IN-TIME SNAPSHOT B INPUT CAPTURE & VALIDATION
## Input Validation Specification & Provenance Schema

**Phase**: Phase 14 (Step 2)  
**Date**: October 31, 2026  
**Status**: **IMPLEMENTED & VERIFIED**  
**Module**: `src/nifty_ai/shadow/input_validator.py`, `src/nifty_ai/shadow/contracts.py`  

---

## 1. Overview & Architectural Principles

Step 2 establishes the point-in-time input ingestion and validation boundary for the Phase 14 forward shadow system. It guarantees that any vector presented to the frozen model satisfies strict temporal isolation, canonical schema alignment, and fail-closed integrity checks.

### Core Guarantees:
1. **Temporal Cutoff**: Enforced strictly at `08:50:00 Asia/Kolkata`. Any observation published, available, or ingested after 08:50:00 IST is blocked.
2. **Canonical 63-Feature Schema**: Exactly 45 price features followed by 18 market-context features. The ordering matches `snapshot_b_t0_primary_model.meta.json` bit-for-bit.
3. **Forbidden Information Filtration**:
   - Zero current-session OHLCV (no same-day Open, High, Low, Close, or Volume).
   - Zero news sentiment or NLP features.
   - Zero institutional flow features (FII/DII).
   - Zero unapproved or experimental features.
4. **Numerical Validation**: All 63 feature values must be finite floating-point numbers. Any NaN, +inf, -inf, or missing field triggers an immediate fail-closed rejection.
5. **Activation Boundary Enforcement**: Any record tagged as `prospective_live_capture` must possess an observation timestamp $\ge \text{2026-10-31T14:47:00Z}$. Historical sessions cannot masquerade as prospective captures.

---

## 2. Validation Flowchart

```
[Incoming Feature Vector]
          │
          ▼
[Check 1: Exact 63 Feature Count?] ──► Fail ──► [Record Validation Failure & Block]
          │ Pass
          ▼
[Check 2: Exact Canonical Ordering?] ──► Fail ──► [Record Validation Failure & Block]
          │ Pass
          ▼
[Check 3: All 63 Values Finite?] ──► Fail ──► [Record Validation Failure & Block]
          │ Pass
          ▼
[Check 4: Zero Forbidden Columns?] ──► Fail ──► [Record Validation Failure & Block]
          │ Pass
          ▼
[Check 5: Cutoff <= 08:50:00 IST?] ──► Fail ──► [Record Validation Failure & Block]
          │ Pass
          ▼
[Check 6: Avail Time <= Cutoff?] ──► Fail ──► [Record Validation Failure & Block]
          │ Pass
          ▼
[Check 7: Activation Boundary?] ──► Fail ──► [Record Validation Failure & Block]
          │ Pass
          ▼
[Check 8: Feature Hash Verified?] ──► Fail ──► [Record Validation Failure & Block]
          │ Pass
          ▼
[ValidationStatus: PASSED — Eligible for Inference]
```

---

## 3. Provenance Schema Details

Every captured feature vector is paired with a `SourceProvenance` metadata object:
- `source_id`: Identifier of upstream data source (e.g. NSE daily archives, Yahoo Finance context feeds).
- `observation_time`: Point-in-time timestamp of raw market data.
- `availability_time`: Verified publication/availability timestamp.
- `ingestion_time`: Timestamp when pipeline read the data.
- `timezone`: Explicitly `Asia/Kolkata`.
- `raw_data_hash`: SHA-256 digest of raw inputs.
- `provenance_type`: One of `prospective_live_capture`, `historical_backfill`, `retrospective_reference`, or `invalid_or_quarantined`.
- `quarantine_reason`: Reason string if quarantined.

---

## 4. Audit & Reproducibility

Every run generates a persistent `ValidationReport` stored in `data/interim/phase14_shadow/validation_reports/`. Blocked runs are preserved for governance review rather than discarded, guaranteeing full observability.
