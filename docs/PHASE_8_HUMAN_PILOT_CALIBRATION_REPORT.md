# Phase 8 — Human Pilot Calibration & Annotation Quality Audit Report

**Audit Date**: September 15, 2026  
**Auditor**: Senior NLP Evaluation Engineer & Quantitative Research Methodology Auditor  
**Audit Scope**: Exactly 50 Records (`ANN_000001` through `ANN_000050`)  
**Data Artifact**: `data/interim/news/ai_assisted_development_annotations.csv`  
**Dataset SHA-256**: `3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c`  
**Pilot Status**: Authoritative Single-Annotator Human Pilot  

---

## 1. Executive Summary

A formal calibration and quality audit was conducted on the 50-record human pilot annotation package (`ANN_000001` to `ANN_000050`). These records were manually labeled by a single human annotator and integrated as the authoritative benchmark anchor for the Phase 8 NLP validation framework.

### Key Audit Findings:
1. **Pilot Scope & Integrity**: Exactly 50 records were audited. All 50 records trace back byte-for-byte to authentic NSE corporate announcements from 2008. No synthetic records, model-hallucinated announcements, or post-2021 contamination exist.
2. **Schema Compliance**: 49 of 50 records (98.0%) adhere strictly to the Phase 8 categorical schema. Record `ANN_000014` exhibits an explicit schema violation (`confidence = NEUTRAL`, `relevance = NEUTRAL`), which is preserved verbatim in accordance with the audit protocol.
3. **Distribution Profiles**:
   - **Sentiment**: Dominantly `NEUTRAL` (72.0%, 36 records), with `POSITIVE` at 20.0% (10 records) and `NEGATIVE` at 8.0% (4 records). Zero records were tagged `UNCERTAIN`.
   - **Confidence**: `MEDIUM` (78.0%, 39 records), `HIGH` (12.0%, 6 records), `LOW` (8.0%, 4 records), Schema Error (2.0%, 1 record).
   - **Relevance**: `MEDIUM` (70.0%, 35 records), `HIGH` (16.0%, 8 records), `LOW` (12.0%, 6 records), Schema Error (2.0%, 1 record).
   - **Importance**: Skewed to standard corporate baseline: 68.0% (34 records) rated `3`, 14.0% (7 records) rated `2`, 10.0% (5 records) rated `5`, and 8.0% (4 records) rated `4`. Zero records were rated `1`.
   - **Primary Event**: Heavily concentrated in `EARNINGS_RESULTS` (52.0%, 26 records), reflecting the statutory corporate reporting cycle. 8 canonical event categories had zero representation in this 50-record sample.
4. **Content-Level Defensibility**: The majority (88.0%) of annotations are defensible and sound. However, 6 records (12.0%) have been flagged as `REVIEW_REQUIRED` due to schema invalidity, keyword traps (e.g., classifying bond maturity redemption as `NEGATIVE`), or sentiment/importance misalignments.
5. **Methodological Boundaries**: Because only one human annotator participated in this calibration round, **no inter-annotator agreement metrics (Cohen's Kappa, Fleiss' Kappa, or Krippendorff's Alpha) can be calculated or claimed**. Doing so would constitute scientific fabrication.
6. **Final Audit Verdict**: **`C) PILOT DATA REQUIRES HUMAN REVIEW`** (with `A` as an operational fallback once documented human sign-off on the 6 flagged items is recorded).

---

## 2. Pilot Scope (`ANN_000001` through `ANN_000050`)

The calibration sample consists of the initial 50 rows of `data/interim/news/ai_assisted_development_annotations.csv`:
- **ID Range**: `ANN_000001` through `ANN_000050` (sequential, zero gaps, zero duplicates).
- **Annotation Method**: Strictly recorded as `HUMAN_PILOT`.
- **Temporal Window**: Authentic calendar year 2008 (January 2008 – May 2008).
- **Constituent Representation**: Covers 24 distinct historical NIFTY 50 constituent companies, including Bajaj Auto Finance, ICICI Bank, Punjab National Bank, Tata Consultancy Services, Infosys, GAIL, BHEL, DLF, ITC, and Larsen & Toubro.
- **Corpus Provenance**: All records are direct, unedited extracts from `data/interim/news/raw_authentic_news_inventory.jsonl` (SHA-256: `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3`).

---

## 3. Annotation Schema Validation

The audit evaluated each field against the canonical Phase 8 Annotation Schema:

| Field Name | Allowed Canonical Domain | Valid Count (N=50) | Violation Count | Compliance Rate |
| :--- | :--- | :---: | :---: | :---: |
| `annotation_id` | `^ANN_[0-9]{6}$` | 50 | 0 | 100.0% |
| `source_record_id`| Non-empty string | 50 | 0 | 100.0% |
| `company` | Valid NIFTY constituent symbol | 50 | 0 | 100.0% |
| `timestamp` | ISO 8601 formatted datetime | 50 | 0 | 100.0% |
| `sentiment` | `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `UNCERTAIN` | 50 | 0 | 100.0% |
| `confidence` | `HIGH`, `MEDIUM`, `LOW` | 49 | 1 (`ANN_000014`) | 98.0% |
| `relevance` | `HIGH`, `MEDIUM`, `LOW`, `NONE` | 49 | 1 (`ANN_000014`) | 98.0% |
| `importance` | Integer scale `1` to `5` | 50 | 0 | 100.0% |
| `primary_event` | Canonical 16 corporate event classes | 50 | 0 | 100.0% |
| `annotation_method` | `HUMAN_PILOT` | 50 | 0 | 100.0% |

All 50 records contain non-empty headlines and summaries, valid timestamps, and consistent metadata.

---

## 4. Sentiment Distribution

The sentiment distribution displays a healthy realism for statutory corporate disclosures:

| Sentiment | Count | Percentage | Methodological Assessment |
| :--- | :---: | :---: | :--- |
| **`NEUTRAL`** | 36 | 72.0% | **Realistic / High Quality**. Indian corporate disclosures are overwhelmingly compliance-driven (board meetings, book closures, outcome notices), making a neutral baseline structurally sound. |
| **`POSITIVE`** | 10 | 20.0% | **Moderate Representation**. Consists of robust quarterly financial expansions, order wins, and dividend announcements. |
| **`NEGATIVE`** | 4 | 8.0% | **Low Representation**. Reflects natural corporate filing asymmetry (companies rarely file overtly negative voluntary releases). However, 3 of the 4 negative tags warrant scrutiny (see Section 11). |
| **`UNCERTAIN`** | 0 | 0.0% | **Under-utilized**. Human annotator exhibited forced decisiveness, categorizing ambiguous items as `NEUTRAL` rather than selecting `UNCERTAIN`. |
| **Total** | **50** | **100.0%** | |

---

## 5. Confidence Distribution

| Confidence | Count | Percentage | Notes |
| :--- | :---: | :---: | :--- |
| **`MEDIUM`** | 39 | 78.0% | Modal category. Annotator felt reasonably secure but appropriately restrained from claiming absolute certainty. |
| **`HIGH`** | 6 | 12.0% | Used for unambiguous quarterly filings, large contract wins, and clear dividend payouts. |
| **`LOW`** | 4 | 8.0% | Used for vague outcome notices or incomplete disclosure texts. |
| **`NEUTRAL`** (Invalid) | 1 | 2.0% | Schema violation in `ANN_000014`. |
| **Total** | **50** | **100.0%** | |

---

## 6. Relevance Distribution

| Relevance | Count | Percentage | Notes |
| :--- | :---: | :---: | :--- |
| **`MEDIUM`** | 35 | 70.0% | Standard corporate disclosure relevance to market valuation. |
| **`HIGH`** | 8 | 16.0% | Material earnings announcements, major commercial contracts, and key structural changes. |
| **`LOW`** | 6 | 12.0% | Minor administrative filings, routine committee changes, and pro-forma AGM dates. |
| **`NONE`** | 0 | 0.0% | Not utilized in pilot. |
| **`NEUTRAL`** (Invalid) | 1 | 2.0% | Schema violation in `ANN_000014`. |
| **Total** | **50** | **100.0%** | |

---

## 7. Importance Distribution

The 1–5 importance scale represents economic impact on share price and volatility:

| Importance Level | Count | Percentage | Operational Definition in Phase 8 Rubric | Observed Pilot Alignment |
| :---: | :---: | :---: | :--- | :--- |
| **1** | 0 | 0.0% | Negligible / Noise (trivial statutory notices) | None assigned; annotator treated lowest items as level 2. |
| **2** | 7 | 14.0% | Minor statutory / routine notice | Assigned to routine committee notices and date updates. |
| **3** | 34 | 68.0% | Standard material announcement | The dominant baseline category for statutory board actions. |
| **4** | 4 | 8.0% | High-impact commercial / financial event | Assigned to full-year earnings and director demise notices. |
| **5** | 5 | 10.0% | Major structural shock / market-moving event | Over-assigned to subsidiary incorporations and capital shifts. |
| **Total** | **50** | **100.0%** | | Mean Importance: **3.18 / 5.00** |

---

## 8. Primary Event Distribution

The 50 pilot records map across 8 of the 16 canonical corporate event classes:

| Event Class | Count | Percentage | Status in Sample |
| :--- | :---: | :---: | :--- |
| `EARNINGS_RESULTS` | 26 | 52.0% | Heavily represented (quarterly/annual disclosures) |
| `CORPORATE_ACTION` | 6 | 12.0% | Well represented (record dates, bond servicing) |
| `MANAGEMENT_CHANGE` | 6 | 12.0% | Well represented (director resignations, appointments) |
| `DIVIDEND` | 5 | 10.0% | Well represented (dividend recommendations) |
| `ORDER_CONTRACT` | 3 | 6.0% | Represented (BHEL, L&T commercial wins) |
| `STRATEGIC_PARTNERSHIP` | 2 | 4.0% | Represented (commercial tie-ups) |
| `SHAREHOLDING_CHANGE` | 1 | 2.0% | Low representation |
| `CAPEX_BUSINESS_UPDATE` | 1 | 2.0% | Low representation |
| `M_AND_A` | 0 | 0.0% | Zero representation in 50 pilot sample |
| `BUYBACK` | 0 | 0.0% | Zero representation in 50 pilot sample |
| `FUNDRAISING` | 0 | 0.0% | Zero representation in 50 pilot sample |
| `BONUS_SPLIT` | 0 | 0.0% | Zero representation in 50 pilot sample |
| `CREDIT_RATING_DEBT` | 0 | 0.0% | Zero representation in 50 pilot sample |
| `REGULATORY_LEGAL` | 0 | 0.0% | Zero representation in 50 pilot sample |
| `OPERATIONAL_EVENT` | 0 | 0.0% | Zero representation in 50 pilot sample |
| `OTHER` | 0 | 0.0% | Zero representation in 50 pilot sample |
| **Total** | **50** | **100.0%** | **8 / 16 classes active** |

*Note*: The absence of 8 event classes in 50 records is expected under random sampling from a power-law distribution where earnings announcements dominate the filing calendar.

---

## 9. `ANN_000014` Schema Violation Documentation

A prominent anomaly identified during validation is record `ANN_000014`:

```text
Record ID: ANN_000014
Company: INFY (Infosys Limited)
Timestamp: 2008-04-15T09:07:00
Headline: Financial Results & Investor Call on April 15, 2008 - Q1 results
Summary: Infosys Technologies Ltd has informed the Exchange that a meeting of the Board of Directors of the Company will be held on April 15, 2008, inter alia, to consider the Audited Financial Results...
Provided Annotation:
  sentiment=NEUTRAL
  confidence=NEUTRAL    <--- SCHEMA VIOLATION
  relevance=NEUTRAL     <--- SCHEMA VIOLATION
  importance=3
  primary_event=EARNINGS_RESULTS
  annotation_method=HUMAN_PILOT
```

### Forensic Analysis:
- The human annotator inadvertently replicated the string `"NEUTRAL"` from the `sentiment` field into both `confidence` and `relevance`.
- `confidence` strictly admits: `HIGH`, `MEDIUM`, `LOW`.
- `relevance` strictly admits: `HIGH`, `MEDIUM`, `LOW`, `NONE`.
- **Protocol Adherence**: Under the Phase 8 audit mandate, this field has been preserved **verbatim** in `ai_assisted_development_annotations.csv` to ensure tamper-proof historical provenance. It has not been silently sanitized.
- **Remediation Recommendation**: A dedicated human review must explicitly re-assign `confidence = MEDIUM` (or `HIGH`) and `relevance = HIGH` (or `MEDIUM`) prior to model training in Phase 9.

---

## 10. Content-Level Review

A qualitative review of the text content across all 50 records indicates that the human annotator applied high analytical rigor to complex disclosures. Specifically:
- Disclosures of quarterly board meeting scheduling were uniformly and correctly identified as `EARNINGS_RESULTS` with `NEUTRAL` sentiment.
- Statutory dividend recommendations were cleanly separated from earnings releases.
- Large industrial contracts awarded to BHEL and L&T were correctly tagged as `ORDER_CONTRACT` with `POSITIVE` sentiment and `HIGH` relevance.

However, content-level evaluation also revealed three systematic human vulnerabilities:
1. **Keyword Traps**: Words such as "demise" or "suspension" triggered negative sentiment classifications regardless of financial market substance.
2. **Preference Share vs Equity Dividends**: Dividend amounts on preference shares (e.g. Re. 0.07 per share on Re. 1/- face value RPS) were misinterpreted as poor returns or dividend cuts.
3. **Importance Inflation**: The highest category (`importance = 5`) was occasionally applied to routine corporate housekeeping (e.g. forming a subsidiary company).

---

## 11. Review-Required Records

Six records (12.0% of the pilot) exhibit actionable issues and have been designated **`REVIEW_REQUIRED`**:

| Annotation ID | Company | Current Annotation | Content Summary | Identified Issue & Forensic Evidence | Recommended Resolution |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ANN_000001`** | `BAJFINANCE` | `sentiment=POSITIVE`<br>`confidence=MEDIUM`<br>`relevance=MEDIUM`<br>`importance=3`<br>`event=CORPORATE_ACTION` | Fixing record date for annual interest payment on 6% Non-Convertible Debentures (NCDs). | **Non-Material Value Transfer**: Paying scheduled contractual interest on debentures is an ordinary debt servicing obligation, not an equity-accretive event. | Change sentiment to `NEUTRAL`. Event class could optionally be refined to `CREDIT_RATING_DEBT` or kept `CORPORATE_ACTION`. |
| **`ANN_000007`** | `ICICIBANK` | `sentiment=NEGATIVE`<br>`confidence=MEDIUM`<br>`relevance=HIGH`<br>`importance=4`<br>`event=CORPORATE_ACTION` | Trading in ICICI Bank Tax Saving Bond suspended on account of **final redemption**. | **Keyword Trap ("Suspension")**: Bond trading suspension due to final redemption at maturity is a routine, planned repayment. It is not an adverse regulatory suspension. | Change sentiment to `NEUTRAL`, importance to `2`, and relevance to `LOW` or `MEDIUM`. |
| **`ANN_000008`** | `PNB` | `sentiment=NEGATIVE`<br>`confidence=MEDIUM`<br>`relevance=HIGH`<br>`importance=4`<br>`event=MANAGEMENT_CHANGE` | Announcement of the sad demise of Shri Mohanjit Singh, Director on the Board of PNB. | **Emotional vs Financial Conflation**: The loss of an individual director is solemn, but carries negligible market impact for a major public sector bank. The Phase 8 rubric states: *"Do not infer market sentiment from emotional wording alone."* | Change sentiment to `NEUTRAL`, importance to `2`, and relevance to `LOW`. |
| **`ANN_000014`** | `INFY` | `sentiment=NEUTRAL`<br>`confidence=NEUTRAL`<br>`relevance=NEUTRAL`<br>`importance=3`<br>`event=EARNINGS_RESULTS` | Notice of Q1 Audited Financial Results board meeting and investor conference call. | **Explicit Schema Violation**: `NEUTRAL` is an invalid categorical value for `confidence` and `relevance`. | Re-assign `confidence=MEDIUM`, `relevance=HIGH` (or `MEDIUM`) via explicit human sign-off. |
| **`ANN_000015`** | `TCS` | `sentiment=NEGATIVE`<br>`confidence=LOW`<br>`relevance=MEDIUM`<br>`importance=3`<br>`event=DIVIDEND` | Recommendation of dividend of Re. 0.07 per Redeemable Preference Share (RPS) of Re. 1/-. | **Unit Misinterpretation**: The annotator assigned `NEGATIVE` with low confidence, likely perceiving Re. 0.07 as an inadequate dividend, unaware that on a Re. 1/- RPS this represents a standard pro-rata preference dividend yield. | Change sentiment to `POSITIVE` or `NEUTRAL`, and importance to `2`. |
| **`ANN_000028`** | `GAIL` | `sentiment=POSITIVE`<br>`confidence=HIGH`<br>`relevance=HIGH`<br>`importance=5`<br>`event=CAPEX_BUSINESS_UPDATE` | Formation of a wholly owned subsidiary "GAIL Gas Limited" on May 27, 2008. | **Importance Inflation**: Level 5 is reserved for structural index-moving mega-events. The incorporation of a subsidiary, while positive, is a standard expansion step. | Change importance from `5` to `3`. |

---

## 12. Inter-Annotator Agreement Limitation

### Strict Methodological Prohibition:
In accordance with international standards for empirical NLP evaluation:
1. **Single Human Coder**: Exactly one human annotator participated in the manual annotation of the 50 pilot records.
2. **Mathematical Non-Applicability**: Chance-corrected agreement coefficients (Cohen's $\kappa$, Fleiss' $\kappa$, Krippendorff's $lpha$, and Gwet's $AC_1$) require a minimum of two independent coders evaluated across identical items.
3. **Prohibition of Fabricated Metrics**: It is scientifically invalid to report a pseudo-Kappa between the human annotator and an LLM/rule-based assistant, or to artificially compute self-agreement. No inter-annotator agreement score is claimed or calculated.
4. **Conclusion**: Formal inter-annotator reliability must be measured only when an independent second human annotator completes the duplicate annotation package in a future audit phase.

---

## 13. AI-Assistance Methodological Limitation

The remaining 1,000 development records (`ANN_000051` through `ANN_001050`) were generated using AI-assisted annotation calibrated against the guidelines. Methodological safeguards must be documented:
- **No Circular Self-Validation**: The AI-assisted annotations must never be validated against the model that generated them.
- **Domain Drift Warning**: The 50 human pilot records were sampled entirely from 2008. While they establish baseline human labeling tendencies, they do not expose modern disclosure formats (e.g., ESG disclosures, investor PPT submissions, post-2015 SEBI LODR Regulation 30 formats).
- **Validation Mandate**: Before any NLP model trained on these annotations is permitted to generate alpha features for NIFTY direction prediction, it must undergo out-of-sample temporal validation on the untouched 2022+ terminal holdout.

---

## 14. Recommendations

To bring the annotation framework to institutional research grade, the following actions are recommended:

1. **Guideline Clarification on Keyword Traps**:
   - Explicitly instruct annotators that debt-related administrative terms such as `"Suspension on account of final redemption"` are non-negative debt retirements (`NEUTRAL`).
   - Reiterate that director demise notices are `NEUTRAL` unless the executive was an indispensable founder or executive leader whose departure immediately threatens operations.
2. **Standardization of Preference Share Dividends**:
   - Provide a guideline rule for preference shares, noting that statutory percentage-based preference dividends should be coded as `NEUTRAL` or `POSITIVE`, never `NEGATIVE`.
3. **Calibrate the 1–5 Importance Scale**:
   - Enforce an importance ceiling: reserve `importance = 5` strictly for events causing an estimated $>3\%$ immediate move in the underlying security (e.g. mega-mergers, unexpected fraud discoveries, catastrophic plant shutdowns). Routine subsidiary creation must be capped at `importance = 3`.
4. **Resolution of Flagged Records**:
   - Convene a 15-minute human adjudication session to sign off on the 6 recommended adjustments for `ANN_000001`, `ANN_000007`, `ANN_000008`, `ANN_000014`, `ANN_000015`, and `ANN_000028`.

---

## 15. Final Calibration Verdict

Based on forensic verification of the 50 pilot records:

### **`C) PILOT DATA REQUIRES HUMAN REVIEW`**

#### Rationale for Verdict C:
1. One record (`ANN_000014`) contains an unresolved schema violation (`confidence=NEUTRAL`, `relevance=NEUTRAL`) that causes validator failures unless explicitly exempted.
2. Five records exhibit keyword traps, emotional-financial conflation, or importance inflation that warrant human sign-off before these pilot records are frozen into permanent ground truth.
3. The underlying annotation guidelines are fundamentally sound (Option A), but the dataset itself requires this documented human review pass.

---

*Report compiled and forensically validated for the NIFTY AI quantitative research repository.*
