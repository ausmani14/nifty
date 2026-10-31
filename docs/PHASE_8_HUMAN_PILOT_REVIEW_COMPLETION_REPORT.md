# Phase 8 — Human Pilot Review Completion Report

**Date**: September 15, 2026  
**Auditor**: Senior NLP Evaluation Engineer & Quantitative Research Methodology Auditor  
**Audit Target**: Phase 8 50-Record Human Pilot Calibration Package  
**Primary Pilot Artifact**: `data/interim/news/ai_assisted_development_annotations.csv`  
**Original Artifact SHA-256**: `3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c`  
**Corrected Pilot Artifact**: `data/interim/news/human_pilot_annotations_corrected.csv`  
**Corrected Pilot SHA-256**: `f01b5950edf405bf0a0b9b90d5fe50824d8f9f549414416b15f7d3e5dc62b19e`  
**Provenance Decision Log**: `data/interim/news/human_pilot_review_decisions.csv`  
**Review Status**: **HUMAN REVIEW COMPLETE**  
**Phase 8 Sealing Status**: **STRICTLY UNSEALED**  
**Phase 9 Status**: **STRICTLY PROHIBITED**  

---

## 1. Six Human-Approved Corrections

The human review of all six flagged records from the Phase 8 Human Pilot Calibration sample has been concluded. The human annotator explicitly reviewed each proposed correction against the primary filing text and the calibrated annotation guidelines.

All six corrections have been formally approved:
1. **`ANN_000001` (Bajaj Finance)**: Approved correction from `POSITIVE` to `NEUTRAL`. Scheduled annual interest payment on 6% NCDs is routine debt servicing obligation, not value creation.
2. **`ANN_000007` (ICICI Bank)**: Approved correction from `NEGATIVE` to `NEUTRAL` (and importance from 4 to 2, relevance from HIGH to LOW). Bond trading suspension on account of final redemption at maturity is planned retirement, not an adverse event.
3. **`ANN_000008` (Punjab National Bank)**: Approved correction from `NEGATIVE` to `NEUTRAL` (and importance from 4 to 2, relevance from HIGH to LOW). Demise of a single non-executive director carries negligible financial/market impact; emotional wording avoided.
4. **`ANN_000014` (Mahindra & Mahindra)**: Approved correction resolving explicit schema violation. Categorical values assigned to valid domains: `confidence = MEDIUM`, `relevance = MEDIUM`.
5. **`ANN_000015` (Tata Consultancy Services)**: Approved correction from `NEGATIVE` to `POSITIVE` (and importance from 3 to 2, confidence from LOW to MEDIUM). Re. 0.07 dividend on Re. 1/- Redeemable Preference Share is contractual yield, not an inadequate payout.
6. **`ANN_000028` (GAIL India)**: Approved correction reducing importance from 5 to 3 (and relevance from HIGH to MEDIUM). Formation of wholly owned subsidiary is routine corporate expansion, not a macro shock.

---

## 2. Before vs. After Calibration Table

| Annotation ID | Company | Field | Original Pilot Value | Human-Approved Corrected Value | Forensic Rationale |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ANN_000001`** | `BAJFINANCE` | `sentiment`<br>`importance`<br>`event` | `POSITIVE`<br>`3`<br>`CORPORATE_ACTION` | **`NEUTRAL`**<br>`3`<br>`CORPORATE_ACTION` | Routine debenture interest servicing is non-accretive to equity value. |
| **`ANN_000007`** | `ICICIBANK` | `sentiment`<br>`confidence`<br>`relevance`<br>`importance` | `NEGATIVE`<br>`HIGH`<br>`HIGH`<br>`4` | **`NEUTRAL`**<br>`HIGH`<br>**`LOW`**<br>**`2`** | Keyword trap ("suspension") resolved; final redemption at maturity is planned debt retirement. |
| **`ANN_000008`** | `PNB` | `sentiment`<br>`confidence`<br>`relevance`<br>`importance` | `NEGATIVE`<br>`HIGH`<br>`HIGH`<br>`4` | **`NEUTRAL`**<br>`HIGH`<br>**`LOW`**<br>**`2`** | Emotional framing corrected; death of single director does not impair bank balance sheet. |
| **`ANN_000014`** | `M&M` | `sentiment`<br>`confidence`<br>`relevance`<br>`importance` | `NEUTRAL`<br>`NEUTRAL` *(Schema error)*<br>`NEUTRAL` *(Schema error)*<br>`3` | `NEUTRAL`<br>**`MEDIUM`**<br>**`MEDIUM`**<br>`3` | Explicit schema violation resolved with valid categorical assignments. |
| **`ANN_000015`** | `TCS` | `sentiment`<br>`confidence`<br>`relevance`<br>`importance` | `NEGATIVE`<br>`LOW`<br>`MEDIUM`<br>`3` | **`POSITIVE`**<br>**`MEDIUM`**<br>`MEDIUM`<br>**`2`** | Unit/par value misinterpretation corrected; preference share dividend is contractual yield. |
| **`ANN_000028`** | `GAIL` | `sentiment`<br>`confidence`<br>`relevance`<br>`importance` | `POSITIVE`<br>`HIGH`<br>`HIGH`<br>`5` | `POSITIVE`<br>`HIGH`<br>**`MEDIUM`**<br>**`3`** | Importance scale inflation corrected; routine subsidiary formation is level 3, not 5. |

---

## 3. Provenance & Artifact Architecture

In strict adherence to quantitative data engineering standards, historical ground-truth datasets must never be silently overwritten. The architecture maintains a permanent, tamper-proof provenance chain:

```
+-------------------------------------------------------------------------------+
|                    HISTORICAL CORPUS (62,329 records)                         |
|         SHA-256: 6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3     |
|                             [BYTE-FOR-BYTE IMMUTABLE]                         |
+-------------------------------------------------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|           ai_assisted_development_annotations.csv (1,050 records)             |
|         SHA-256: 3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c     |
|   - Rows 1-50:    HUMAN_PILOT (ANN_000001–ANN_000050, UNTOUCHED HISTORICAL ANCHOR)    |
|   - Rows 51-1050: AI_ASSISTED (ANN_000051–ANN_001050, UNTOUCHED DEVELOPMENT SET)      |
|                             [BYTE-FOR-BYTE IMMUTABLE]                         |
+-------------------------------------------------------------------------------+
                  |                                             |
                  v                                             v
+------------------------------------+        +------------------------------------+
|  human_pilot_review_decisions.csv  |        | human_pilot_annotations_corrected.csv
|      [AUDIT DECISION LOG]          |        |     [50-RECORD HUMAN PILOT]        |
| - Exactly 6 reviewed records       |        | - Exactly 50 rows (ANN_000001–050) |
| - decision = APPROVED_CORRECTION   |        | - 6 human-approved corrections     |
| - Full before/after audit trail    |        | - SHA-256: f01b5950edf405bf...     |
+------------------------------------+        +------------------------------------+
                                                        |
                                                        | [QUARANTINE BOUNDARY]
                                                        v
                                      +------------------------------------+
                                      | gold_holdout_annotation_input.csv  |
                                      |   (200 records, 2022-2023 holdout) |
                                      |  - 0 labels, 0 model predictions   |
                                      |  - STRICTLY QUARANTINED            |
                                      +------------------------------------+
```

---

## 4. Primary Artifact SHA-256 Checksum

```text
data/interim/news/ai_assisted_development_annotations.csv
SHA-256: 3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c
Status:  100% UNCHANGED (Byte-for-byte verified)
```

---

## 5. Corrected Pilot Artifact SHA-256 Checksum

```text
data/interim/news/human_pilot_annotations_corrected.csv
SHA-256: f01b5950edf405bf0a0b9b90d5fe50824d8f9f549414416b15f7d3e5dc62b19e
Rows:    50 rows (ANN_000001 through ANN_000050)
Method:  HUMAN_PILOT
Status:  VERIFIED & COMMITTED
```

---

## 6. Comprehensive Validation Checks (A through L)

All 12 formal integrity invariants were verified programmatically:

| Check | Description | Status | Verification Detail |
| :---: | :--- | :---: | :--- |
| **A** | Original 1,050-row annotation artifact unchanged | **PASSED** | Exactly 1,050 rows present. |
| **B** | Original SHA-256 unchanged | **PASSED** | Hash matches `3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c`. |
| **C** | Corrected pilot contains exactly 50 rows | **PASSED** | 50 rows in `human_pilot_annotations_corrected.csv`. |
| **D** | Corrected pilot contains exactly 50 HUMAN_PILOT records | **PASSED** | All 50 records have `annotation_method == "HUMAN_PILOT"`. |
| **E** | No duplicate annotation IDs | **PASSED** | Perfectly sequential `ANN_000001` through `ANN_000050`. |
| **F** | All categorical values valid | **PASSED** | All sentiments, confidences, relevances, and events adhere to schema. `ANN_000014` violation resolved. |
| **G** | Importance values are 1–5 | **PASSED** | Integer values all in $[1, 5]$. |
| **H** | No AI_ASSISTED record modified | **PASSED** | Exactly 1,000 AI_ASSISTED records remain intact in primary artifact. |
| **I** | 200-record terminal holdout untouched | **PASSED** | Exactly 200 rows in `gold_holdout_annotation_input.csv`, 0 labels, 0 predictions. |
| **J** | Authentic 62,329-record inventory untouched | **PASSED** | SHA-256: `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3`. |
| **K** | Phase 5/6/7 assets untouched | **PASSED** | Direct and meta-labeler models in `models/` untouched. |
| **L** | No Phase 9 models/features created | **PASSED** | Zero Phase 9 artifacts or alpha features exist in the repository. |

---

## 7. Test Suite Execution Results

Both unit test and complete repository regression suites were executed:

```text
pytest tests/test_news.py -v
============================= 44 passed in 3.42s ==============================

pytest -q
============================ 141 passed in 6.08s ==============================
```

- **News & Point-in-Time Test Suite**: 44 / 44 tests passed (100%).
- **Repository Full Test Suite**: 141 / 141 tests passed (100%).

---

## 8. Terminal Holdout Strict Isolation

The 200-record terminal holdout (`gold_holdout_annotation_input.csv`) covers authentic disclosures from 2022–2023. It remains under strict quarantine:
- **Zero Labels Assigned**: No sentiment, event, confidence, relevance, or importance scores exist.
- **Zero Model Contact**: No language model, FinBERT pipeline, or human annotator has accessed the holdout.
- **Strict Isolation Maintained**: It is reserved exclusively for post-training out-of-sample temporal evaluation in Phase 9.

---

## 9. AI-Assisted Annotation Methodological Limitations

> [!WARNING]
> While the 50-record pilot has now been calibrated, audited, and human-corrected, **the remaining 1,000 development records (`ANN_000051` through `ANN_001050`) were produced via AI-assisted annotation**.
>
> 1. **NOT Independent Human Gold**: The 1,000 AI-assisted records must **NEVER** be described or treated as independent human gold standard data.
> 2. **Silver-Standard Training Utility**: They serve strictly as silver-standard developmental training/tuning material.
> 3. **Prohibition of Circular Validation**: Performance on these 1,000 records cannot validate an NLP model that was trained or calibrated on similar synthetic/assisted signals.

---

## 10. Inter-Annotator Agreement Limitation

> [!IMPORTANT]
> Because exactly **one human annotator** participated in this pilot calibration round:
> 1. **No Chance-Corrected Agreement**: Cohen's $\kappa$, Fleiss' $\kappa$, and Krippendorff's $lpha$ are mathematically undefined.
> 2. **Zero Agreement Metrics Claimed**: No inter-annotator reliability score is reported or claimed.
> 3. **Future Requirement**: True inter-coder reliability can only be computed when an independent second human annotator completes duplicate labeling of the benchmark package.

---

## 11. Remaining Phase 8 Requirements

Before Phase 8 can be sealed, the following prerequisites must be fulfilled:
1. **Annotator 2 Independent Package Execution**: Independent annotation of the sampling package by a second human coder to enable genuine Cohen's/Krippendorff agreement measurement.
2. **Dispute Adjudication Workflow**: Automated disagreement flagging and senior adjudicator sign-off on divergent items.
3. **Formal Phase 8 Sealing Gate**: Official sign-off of Phase 8 news integration infrastructure.

---

## 12. Final Status & Phase 8 Governance

```text
================================================================================
PHASE 8 REVIEW COMPLETION SUMMARY:
================================================================================
  - Human Pilot Review:          COMPLETE (All 6 flagged records resolved)
  - Corrected Pilot Artifact:    CREATED (human_pilot_annotations_corrected.csv)
  - Corrected Pilot Checksum:    f01b5950edf405bf0a0b9b90d5fe50824d8f9f549414416b15f7d3e5dc62b19e
  - Original 1,050 Artifact:     3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c (UNTOUCHED)
  - 1,000 AI Annotations:        NOT independent human gold (Development Silver)
  - 200-Record Terminal Holdout: FROZEN / UNTOUCHED (0 labels)
  - Inter-Annotator Agreement:   NOT AVAILABLE (Single human coder; Zero Kappa)
  - News Test Suite:             44 / 44 PASSED
  - Full Test Suite:             141 / 141 PASSED
  - Phase 8 Sealing Status:      STRICTLY UNSEALED
  - Phase 9 Models/Features:     STRICTLY PROHIBITED
================================================================================
```

---

*Report compiled for the NIFTY AI quantitative research repository.*
