# Phase 8 — Human Pilot Review Decision Report

**Report Date**: September 15, 2026  
**Auditor**: Senior NLP Evaluation Engineer & Quantitative Research Methodology Auditor  
**Scope**: 6 Flagged Pilot Annotations (`ANN_000001`, `ANN_000007`, `ANN_000008`, `ANN_000014`, `ANN_000015`, `ANN_000028`)  
**Artifacts**:
- Provenance Layer: `data/interim/news/human_pilot_review_decisions.csv`
- Primary Pilot Anchor: `data/interim/news/ai_assisted_development_annotations.csv`
- Frozen Terminal Holdout: `data/interim/news/gold_holdout_annotation_input.csv` (100% untouched)
**Status**: **PENDING HUMAN DECISION**  
**Final Verdict**: **`C) PILOT DATA REQUIRES HUMAN REVIEW`**  

---

## 1. Executive Summary & Review Scope

Following the Phase 8 Human Pilot Calibration Audit, exactly six records from the 50-record human pilot sample (`ANN_000001` through `ANN_000050`) were identified as requiring explicit human review.

These records represent either:
1. An explicit schema violation (`ANN_000014`), or
2. Vulnerabilities to keyword traps, emotional framing, or importance inflation (`ANN_000001`, `ANN_000007`, `ANN_000008`, `ANN_000015`, `ANN_000028`).

In accordance with strict scientific protocol:
- The auditor's recommendations are **not automatically authoritative**.
- No synthetic or automated overwrites have been applied to the pilot dataset.
- A dedicated provenance review queue has been instantiated at `data/interim/news/human_pilot_review_decisions.csv`.
- All six records currently hold status **`PENDING_HUMAN_REVIEW`**.

---

## 2. The Six Flagged Records & Auditor Recommendations

### Record 1: `ANN_000001`
- **Company**: Bajaj Finance Limited (`BAJFINANCE`)
- **Headline**: `BAJFINANCE: Record Date – Bajaj Auto Finance Ltd has informed the Exchange that the Company has fixed January 09, 2008 as the Record Date for the purpose of payment of annual interest due on February 09, 20`
- **Summary / Body**: `Bajaj Auto Finance Ltd has informed the Exchange that the Company has fixed January 09, 2008 as the Record Date for the purpose of payment of annual interest due on February 09, 2008 on 6% Non-Convertible Debentures.`
- **Current Pilot Annotation**:
  - `sentiment = POSITIVE`
  - `confidence = MEDIUM`
  - `relevance = MEDIUM`
  - `importance = 3`
  - `primary_event = CORPORATE_ACTION`
- **Identified Defect / Issue**: Payment of contractually obligated annual interest on 6% NCDs is routine debt servicing. While fulfilling debt obligations is mandatory, it does not represent value creation or equity appreciation.
- **Auditor Recommendation**:
  - `sentiment = NEUTRAL`
  - `importance = 3` (or `2`)
  - `primary_event = CORPORATE_ACTION` (or `CREDIT_RATING_DEBT`)
- **Review Status**: `PENDING_HUMAN_REVIEW`

---

### Record 2: `ANN_000007`
- **Company**: ICICI Bank Limited (`ICICIBANK`)
- **Headline**: `ICICIBANK: Suspension of bonds – Members of the Exchange are hereby informed that the trading in the February 2003 Tax Saving Bond Sec 88 - Option III, Symbol - ICIBK0403, Series - N3 of ICICI Bank Ltd. shall be s`
- **Summary / Body**: `Members of the Exchange are hereby informed that the trading in the February 2003 Tax Saving Bond Sec 88 - Option III, Symbol - ICIBK0403, Series - N3 of ICICI Bank Ltd. shall be suspended w.e.f. February 25, 2008 on account of final redemption.`
- **Current Pilot Annotation**:
  - `sentiment = NEGATIVE`
  - `confidence = HIGH`
  - `relevance = HIGH`
  - `importance = 4`
  - `primary_event = CORPORATE_ACTION`
- **Identified Defect / Issue**: **Keyword Trap ("Suspension")**. The exchange notice states trading in a specific tax-saving bond series is suspended *"on account of final redemption"* (i.e. planned bond retirement at maturity). This is ordinary fixed-income administration, not an adverse disciplinary suspension.
- **Auditor Recommendation**:
  - `sentiment = NEUTRAL`
  - `confidence = HIGH`
  - `relevance = LOW` (or `MEDIUM`)
  - `importance = 2`
  - `primary_event = CORPORATE_ACTION`
- **Review Status**: `PENDING_HUMAN_REVIEW`

---

### Record 3: `ANN_000008`
- **Company**: Punjab National Bank (`PNB`)
- **Headline**: `PNB: Demise of Director – Punjab National Bank has informed the Exchange the sad demise of Shri Mohanjit Singh, Director on the Board of the Bank.`
- **Summary / Body**: `Punjab National Bank has informed the Exchange the sad demise of Shri Mohanjit Singh, Director on the Board of the Bank.`
- **Current Pilot Annotation**:
  - `sentiment = NEGATIVE`
  - `confidence = HIGH`
  - `relevance = HIGH`
  - `importance = 4`
  - `primary_event = MANAGEMENT_CHANGE`
- **Identified Defect / Issue**: **Emotional vs. Financial Conflation**. The loss of a director is human tragedy, but for a public-sector bank, the loss of an individual non-executive director carries negligible financial impact. The Phase 8 Annotation Guidelines explicitly state: *"Do not infer market sentiment from emotional or solemn wording alone."*
- **Auditor Recommendation**:
  - `sentiment = NEUTRAL`
  - `confidence = MEDIUM` (or `HIGH`)
  - `relevance = LOW`
  - `importance = 2`
  - `primary_event = MANAGEMENT_CHANGE`
- **Review Status**: `PENDING_HUMAN_REVIEW`

---

### Record 4: `ANN_000014`
- **Company**: Mahindra & Mahindra Limited (`M&M`)
- **Headline**: `M&M: Publish Audited Results – Mahindra & Mahindra Ltd. has informed the Exchange that: "Since the Company will be publishing the Audited Accounts for the financial year ended 31st March, 2008 within the three m`
- **Summary / Body**: `Mahindra & Mahindra Ltd. has informed the Exchange that: "Since the Company will be publishing the Audited Accounts for the financial year ended 31st March, 2008 within the three months period (i.e. on or before 30th June, 2008) the unaudited results for the quarter ended March 31, 2008 will not be published".`
- **Current Pilot Annotation**:
  - `sentiment = NEUTRAL`
  - `confidence = NEUTRAL` *(EXPLICIT SCHEMA VIOLATION)*
  - `relevance = NEUTRAL` *(EXPLICIT SCHEMA VIOLATION)*
  - `importance = 3`
  - `primary_event = EARNINGS_RESULTS`
- **Identified Defect / Issue**: Explicit schema violation. The string `"NEUTRAL"` was copied into the `confidence` and `relevance` fields. Allowed domains:
  - `confidence`: `HIGH`, `MEDIUM`, `LOW`
  - `relevance`: `HIGH`, `MEDIUM`, `LOW`, `NONE`
- **Auditor Recommendation**:
  - `sentiment = NEUTRAL`
  - `confidence = MEDIUM`
  - `relevance = HIGH` (or `MEDIUM`)
  - `importance = 3`
  - `primary_event = EARNINGS_RESULTS`
- **Review Status**: `PENDING_HUMAN_REVIEW`

---

### Record 5: `ANN_000015`
- **Company**: Tata Consultancy Services Limited (`TCS`)
- **Headline**: `TCS: Dividend – Tata Consultancy Services Limited has informed the Exchange that the Directors have also recommended for approval by the shareholders of the Company at the forthcoming Annual Gener`
- **Summary / Body**: `Tata Consultancy Services Limited has informed the Exchange that the Directors have also recommended for approval by the shareholders of the Company at the forthcoming Annual General Meeting of the Company, a Dividend of Re. 0.07 per Redeemable Preference Share (RPS) of Re. 1/- each of the Company. The dividend on the RPS shall be paid rata from the date of allotment of the RPS i.e. March 28, 2008.`
- **Current Pilot Annotation**:
  - `sentiment = NEGATIVE`
  - `confidence = LOW`
  - `relevance = MEDIUM`
  - `importance = 3`
  - `primary_event = DIVIDEND`
- **Identified Defect / Issue**: **Unit / Face Value Misinterpretation**. The human annotator marked the dividend `NEGATIVE` with low confidence, likely perceiving `Re. 0.07` as an unusually tiny payout. However, on a preference share with face value `Re. 1/-`, a `Re. 0.07` dividend represents a standard contractual yield (7% pro-rata). Unless a dividend is omitted or reduced, dividend declarations are non-negative.
- **Auditor Recommendation**:
  - `sentiment = POSITIVE` (or `NEUTRAL`)
  - `confidence = MEDIUM`
  - `relevance = MEDIUM` (or `LOW`)
  - `importance = 2`
  - `primary_event = DIVIDEND`
- **Review Status**: `PENDING_HUMAN_REVIEW`

---

### Record 6: `ANN_000028`
- **Company**: GAIL (India) Limited (`GAIL`)
- **Headline**: `GAIL: Updates – Gail (India) Limited has informed the Exchange that "A wholly owned subsidiary company of GAIL (India) Limited has been formed with the name of "GAIL Gas Limited" on May 27, 2008".`
- **Summary / Body**: `Gail (India) Limited has informed the Exchange that "A wholly owned subsidiary company of GAIL (India) Limited has been formed with the name of "GAIL Gas Limited" on May 27, 2008".`
- **Current Pilot Annotation**:
  - `sentiment = POSITIVE`
  - `confidence = HIGH`
  - `relevance = HIGH`
  - `importance = 5`
  - `primary_event = CAPEX_BUSINESS_UPDATE`
- **Identified Defect / Issue**: **Importance Scale Inflation**. Level 5 is strictly reserved for macro-level structural events (e.g. index reconstitution, catastrophic fraud, multi-billion dollar M&A). Incorporating a wholly-owned subsidiary is routine corporate expansion.
- **Auditor Recommendation**:
  - `sentiment = POSITIVE`
  - `confidence = HIGH`
  - `relevance = MEDIUM`
  - `importance = 3`
  - `primary_event = CAPEX_BUSINESS_UPDATE`
- **Review Status**: `PENDING_HUMAN_REVIEW`

---

## 3. Review Decisions Accounting

| Metric | Count | Records |
| :--- | :---: | :--- |
| **Total Flagged for Review** | 6 | `ANN_000001`, `ANN_000007`, `ANN_000008`, `ANN_000014`, `ANN_000015`, `ANN_000028` |
| **Corrections Approved** | 0 | None (no human decision supplied yet) |
| **Corrections Rejected** | 0 | None (no human decision supplied yet) |
| **Pending Decisions** | 6 | All 6 records awaiting formal human sign-off |

---

## 4. Provenance & Dataset Protection Architecture

To ensure strict compliance with scientific audit guidelines:

```
+-------------------------------------------------------------------------+
|                  HISTORICAL CORPUS (62,329 records)                     |
|            SHA-256: 6134fd770b30abe70ed1a839968ce165... (IMMUTABLE)    |
+-------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------+
|        ai_assisted_development_annotations.csv (1,050 records)          |
|            SHA-256: 3f1ebc67c8b5ae3a61ab7da1b999f257... (IMMUTABLE)    |
|   - Rows 1-50:    HUMAN_PILOT (ANN_000001–ANN_000050, UNTOUCHED)        |
|   - Rows 51-1050: AI_ASSISTED (ANN_000051–ANN_001050, UNTOUCHED)        |
+-------------------------------------------------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+------------------------------------+   +------------------------------------+
|  human_pilot_review_decisions.csv  |   | gold_holdout_annotation_input.csv  |
|       (PROVENANCE REVIEW LAYER)    |   |     (200 records, 2022-2023)       |
|  - Exactly 6 flagged records       |   |  - 0 labels, 0 predictions         |
|  - All original values preserved   |   |  - STRICTLY QUARANTINED            |
|  - Status: PENDING_HUMAN_REVIEW    |   |                                    |
+------------------------------------+   +------------------------------------+
```

1. **Original Pilot Preserved**: The primary artifact `data/interim/news/ai_assisted_development_annotations.csv` remains strictly bit-for-bit identical to its certified state.
2. **Decoupled Review Layer**: Decisions are recorded exclusively in `data/interim/news/human_pilot_review_decisions.csv`.
3. **No Automatic Overwrites**: If human corrections are ultimately approved, they will be written into a newly designated corrected pilot artifact (`data/interim/news/human_pilot_annotations_corrected.csv`), preserving the raw pilot as historical record.

---

## 5. Verification & Test Suite Execution

All test suites were executed to verify system integrity:

```
pytest tests/test_news.py -v
============================= 44 passed in 2.90s ==============================

pytest -q
============================ 141 passed in 4.98s ==============================
```

- **News & Sampling Invariants**: 44 / 44 tests passed.
- **Repository Full Test Suite**: 141 / 141 tests passed.
- **Protected Phase 5/6/7 Assets**: 100% untouched.
- **Zero Phase 9 Files**: No ML models trained, no NLP alpha features generated.

---

## 6. Phase 8 Sealing Status & Final Verdict

Because human decisions on the six flagged pilot records are currently pending:
- **Phase 8 Sealing**: **STRICTLY UNSEALED**.
- **Phase 9 Models**: **STRICTLY PROHIBITED**.
- **Inter-Annotator Kappa**: **NOT CALCULATED** (scientifically inapplicable with a single human coder).

### Final Formal Verdict:
### **`C) PILOT DATA REQUIRES HUMAN REVIEW`**

---

*Report compiled for the NIFTY AI quantitative research project.*
