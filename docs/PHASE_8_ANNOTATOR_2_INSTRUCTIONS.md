# Phase 8 — Independent Human Annotator 2 Protocol & Guidelines

**Document Date**: September 16, 2026  
**Evaluation Role**: Independent Human Annotator 2  
**Dataset Scope**: Fresh 50-Record Calibration Package (`CAL2_000001` through `CAL2_000050`)  
**Input Template**: [`data/interim/news/fresh_calibration_50_annotator_2_template.csv`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/news/fresh_calibration_50_annotator_2_template.csv)  
**Expected Submission**: `data/interim/news/fresh_calibration_50_annotator_2_completed.csv`  
**Governing Guidelines**: [`docs/PHASE_8_HUMAN_ANNOTATION_GUIDELINES.md`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/docs/PHASE_8_HUMAN_ANNOTATION_GUIDELINES.md) (Version 1.1.0)  
**Machine-Readable Rules**: [`configs/annotation_guidelines_rules.json`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/configs/annotation_guidelines_rules.json)  

---

## 1. Protocol & Blind Independence Rules

> [!IMPORTANT]
> ### Strict Double-Blind Independence
> 1. **Zero Access to Annotator 1 Labels**: You must NOT view, request, or consult the labels assigned by Annotator 1 (`fresh_calibration_50_human_annotations_corrected.csv`).
> 2. **Zero Access to Model Predictions**: You must NOT consult any machine learning model, NLP classifier, or heuristic predictor outputs.
> 3. **Zero Access to Market Outcomes**: Do NOT inspect subsequent NIFTY 50 price movements or stock price performance following the announcement date. Annotation must be performed strictly **ex-ante** based on information available at the snapshot timestamp.
> 4. **Self-Contained Evaluation**: Code each record solely on the basis of the company name, timestamp, headline, summary/body text, and Version 1.1 Annotation Guidelines.

---

## 2. Annotation Task & Required Schema

For each of the 50 records in `fresh_calibration_50_annotator_2_template.csv`, populate the six blank fields:

| Field Name | Allowed Values | Description |
| :--- | :--- | :--- |
| **`sentiment`** | `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `UNCERTAIN` | Financial directional sentiment for the focal NIFTY constituent company. |
| **`confidence`** | `HIGH`, `MEDIUM`, `LOW` | Degree of certainty in interpreting the disclosure and its economic meaning. |
| **`relevance`** | `HIGH`, `MEDIUM`, `LOW`, `NONE` | Graded direct relevance to the company's valuation or operational prospects. |
| **`importance`** | `1`, `2`, `3`, `4`, `5` | Ex-ante economic significance (1 = routine noise, 5 = transformative/index-moving). |
| **`primary_event`** | One of the 16 canonical categories | The single dominant material corporate event type. |
| **`secondary_events`** | Comma-separated list or `NONE` | Additional concurrent corporate event types (up to 3). |

---

## 3. Canonical Event Taxonomy (17 Substantive + 1 Fallback = 18 Total Categories)

Annotators select the **`primary_event`** strictly from these **17 substantive canonical primary-event categories plus 1 fallback category (`OTHER`), yielding 18 total primary-event categories**:

1. `EARNINGS_RESULTS`: Quarterly/annual audited or unaudited financial statements, revenue/profit summaries.
2. `DIVIDEND`: Dividend declarations, recommendations, interim/final payouts, record dates for dividends.
3. `BONUS_SPLIT`: Stock splits, sub-division of shares, bonus share issues.
4. `RIGHTS_ISSUE`: Rights entitlement offerings and rights issue pricing.
5. `BUYBACK`: Share buyback approvals, tenders, open market offers, buyback closure.
6. `M_AND_A`: Mergers, acquisitions, demergers, amalgamations, business takeovers.
7. `CAPEX_BUSINESS_UPDATE`: Capacity expansions, new plant commissioning, general operational updates.
8. `FINANCIAL_IRREGULARITY`: Audit qualifications, forensic probes, defaults, accounting restatements.
9. `SHAREHOLDING_CHANGE`: Promoter pledging/revocation, insider trading disclosures, SAST takeover filings.
10. `OPERATIONAL_EVENT`: Strike, plant shutdown, regulatory inspection, minor incident, factory disruption.
11. `STRATEGIC_PARTNERSHIP`: Joint ventures, non-equity commercial alliances, technology collaborations.
12. `CREDIT_RATING_DEBT`: Credit rating upgrades/downgrades, bond issuances, debenture redemptions.
13. `FUNDRAISING`: Qualified institutional placements (QIP), preferential allotments, ADR/GDR issuances.
14. `REGULATORY_LEGAL`: Court rulings, CCI/SEBI orders, USFDA drug approvals/warning letters, tax disputes.
15. `CORPORATE_ACTION`: Routine corporate actions, loss of share certificates, secretarial filings, ESOP allotments.
16. `MANAGEMENT_CHANGE`: Appointment, resignation, cessation, or demise of Directors, CEO, CFO, or key personnel.
17. `ORDER_CONTRACT`: Commercial contract wins, client orders, government tenders, infrastructure awards.
*(Note: `OTHER` is reserved solely as a fallback when none of the above substantive categories apply).*

---

## 4. Key Precedence Rules (Version 1.1 Guidelines)

### A. Multi-Event Precedence Waterfall
When a filing contains multiple corporate events, assign `primary_event` using this priority hierarchy:
$$\text{EARNINGS\_RESULTS} > \text{DIVIDEND} > \text{M\_AND\_A} > \text{MANAGEMENT\_CHANGE} > \text{CORPORATE\_ACTION} > \text{OTHER}$$
* **Exception (Standalone Dividend)**: If a filing is solely a dividend recommendation/announcement without accompanying financial results or earnings figures, classify it as **`DIVIDEND`**.

### B. ESOP Dilution Ceiling Rule
- If an allotment under ESOP/ESOS/ESPS represents $< 0.1\%$ of the company's issued share capital:
  - Classify as **`CORPORATE_ACTION`** (or `SHAREHOLDING_CHANGE`).
  - Importance MUST NOT exceed **`2`** (typically `1` or `2`).
  - Sentiment is strictly **`NEUTRAL`**.

### C. Procedural vs Substantive Filings
- Routine secretarial notifications (e.g. loss of share certificates, trading window closures, newspaper publication intimations) have negligible market impact:
  - Importance: **`1`** or **`2`**.
  - Sentiment: **`NEUTRAL`**.
  - Event: **`CORPORATE_ACTION`** or **`OTHER`**.
- Substantive commercial order awards (e.g. EPC infrastructure wins, equipment supply contracts):
  - Classify as **`ORDER_CONTRACT`**.
  - Importance: **`3`**, **`4`**, or **`5`** depending on contract value relative to revenue.
  - Sentiment: **`POSITIVE`**.

---

## 5. Submission Procedure

1. Complete all 50 rows in `data/interim/news/fresh_calibration_50_annotator_2_template.csv`.
2. Ensure there are **no missing fields** and that all values adhere to the allowed schema.
3. Save the completed file as:
   `data/interim/news/fresh_calibration_50_annotator_2_completed.csv`
4. Provide this completed file to the Evaluation Lead for automated calibration gate processing.
