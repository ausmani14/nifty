# Phase 8 — Human Annotation Guideline Revision Report

**Document Date**: September 16, 2026  
**Auditor / Author**: Senior NLP Evaluation Engineer & Quantitative Research Methodology Auditor  
**Audit Trigger**: Disagreement Audit (Verdict: `B) GUIDELINES REQUIRE TARGETED CORRECTION`)  
**Target Guideline Document**: `docs/PHASE_8_HUMAN_ANNOTATION_GUIDELINES.md` (Updated to Version 1.1.0)  
**Machine-Readable Configuration**: `configs/annotation_guidelines_rules.json`  
**Phase 8 Sealing Status**: **STRICTLY UNSEALED**  
**Phase 9 Status**: **STRICTLY PROHIBITED**  

---

## 1. Executive Summary

Following the methodological disagreement audit comparing the corrected 50-record Human Pilot (`human_pilot_annotations_corrected.csv`) against the AI-Simulated Annotator 2 pass (`annotator_2_simulated_annotations_1050.csv`), four distinct, systematic divergence patterns were identified. These divergences were not caused by flaws in the underlying 16-class taxonomy or 4-way sentiment architecture, but rather by specific boundary ambiguities in the operational guidelines.

In accordance with Verdict **`B) GUIDELINES REQUIRE TARGETED CORRECTION`**, four targeted guideline refinements have been formulated, audited, codified in `docs/PHASE_8_HUMAN_ANNOTATION_GUIDELINES.md`, and formalized into a machine-readable schema at `configs/annotation_guidelines_rules.json`.

---

## 2. Refinement 1: Multi-Event Precedence Hierarchy

### Old Rule:
The original guidelines allowed annotators to assign a `primary_event` and up to 3 `secondary_events` from the 16 canonical event categories. However, the guidelines provided **no explicit prioritization or tie-breaking waterfall** when a single corporate disclosure contained multiple concurrent corporate actions.

### New Rule:
When an authentic corporate disclosure bundles multiple event types into a single filing, annotators must assign `primary_event` strictly according to the following precedence waterfall:

$$\text{EARNINGS\_RESULTS} > \text{DIVIDEND} > \text{M\_AND\_A} > \text{MANAGEMENT\_CHANGE} > \text{CORPORATE\_ACTION} > \text{OTHER}$$

- **Strict Exception**: If the disclosure is solely a dividend recommendation or announcement without accompanying financial statements or audited/unaudited operating figures, it must be classified strictly as **`DIVIDEND`**, NOT `EARNINGS_RESULTS`.
- **Secondary Capture**: Concurrent material events must be captured under `secondary_events` (up to 3) where supported by the schema.

### Reason for Change:
Indian corporate statutory compliance frequently bundles quarterly board meeting outcomes: a single circular often reports quarterly accounts, recommends a dividend, and intimates book closure dates. Without a priority waterfall, independent annotators arbitrarily chose different primary events, degrading apparent agreement.

### Affected Disagreement Pattern:
- **Pattern 1 & 4**: Divergence between `EARNINGS_RESULTS`, `CORPORATE_ACTION`, and `DIVIDEND` (accounted for 9 pairwise confusions in the 50 pilot records).

### Concrete Examples from 50-Record Pilot:
- **`ANN_000025` (Bajaj Auto)**: Headline: *"BAJAJ-AUTO: Dividend – Board recommends dividend of Rs. 20 per share (200%)"*. The human labeled this `EARNINGS_RESULTS` (because it arose from a board meeting), while AI2 labeled it `DIVIDEND`. Under the new rule, the absence of financial tables makes this strictly **`DIVIDEND`**.
- **`ANN_000026` (Britannia Industries)**: Headline: *"BRITANNIA: Dividend – Board recommended dividend of 180%"*. Human labeled `EARNINGS_RESULTS`; under the new rule, strictly **`DIVIDEND`**.

### Potential Unintended Consequences & Mitigations:
- *Risk*: Annotators might miss major subsidiary demergers announced concurrently with earnings.
- *Mitigation*: The guideline explicitly mandates recording concurrent material catalysts under `secondary_events`.

---

## 3. Refinement 2: ESOP Allotment vs. Capital Fundraising Materiality

### Old Rule:
The guidelines defined `CREDIT_DEBT` / `CORPORATE_ACTION` as balance sheet and share capital actions, and `FUNDRAISING` as debt/equity capital raising. However, it lacked a **quantitative economic materiality threshold** for share allotments.

### New Rule:
- Allotments of equity shares under Employee Stock Option Plans (ESOPs) or managerial schemes that represent **$< 0.1\%$ of existing paid-up share capital** must be classified as:
  - `primary_event = CORPORATE_ACTION`
  - `importance = 1` or `2`
  - `sentiment = NEUTRAL` (unless explicit, economically material information indicates otherwise).
- The `FUNDRAISING` event category is reserved strictly for **material external capital infusions**, such as Qualified Institutional Placements (QIPs), rights issues, global depository receipts (GDRs/ADRs), or material preferential allotments to strategic/private equity investors.
- **Denominator Safeguard**: Do **NOT** blindly apply the 0.1% threshold when total paid-up share capital is absent from the filing. In such cases, evaluate textual economic materiality evidence, assign conservative importance (`2`), and flag confidence as `MEDIUM` or `LOW`.

### Reason for Change:
AI2 systematically classified micro-share allotments under ESOP as `FUNDRAISING` with `Importance = 4` and `Sentiment = POSITIVE`, treating routine compensation issuances as significant capital raises.

### Affected Disagreement Pattern:
- **Pattern 2**: AI2 over-inflation on share allotments ($+2$ importance difference).

### Concrete Examples from 50-Record Pilot:
- **`ANN_000006` (ICICI Bank)**: Allotment of 16,850 equity shares (face value Rs. 10/-) under ESOP. For a multi-billion dollar bank, 16,850 shares represents $< 0.002\%$ dilution. Human labeled `CORPORATE_ACTION`, `imp=2`, `NEUTRAL`. AI2 labeled `FUNDRAISING`, `imp=4`, `POSITIVE`. The new rule confirms the human interpretation as canonical.
- **`ANN_000010` (Cairn India)**: Allotment of 792,240 shares under Senior Management ESOP. Human labeled `imp=2`; AI2 labeled `imp=4`, `FUNDRAISING`.

### Potential Unintended Consequences & Mitigations:
- *Risk*: A massive, highly dilutive promoter preferential allotment might be misclassified as routine corporate action if annotators conflate all share allotments.
- *Mitigation*: The rule explicitly restricts the `CORPORATE_ACTION` default to ESOP allotments representing $< 0.1\%$, while explicitly reserving `FUNDRAISING` for QIPs, rights issues, and preferential capital raises.

---

## 4. Refinement 3: Substantive Management Change vs. Board Meeting Mention

### Old Rule:
The guidelines defined `MANAGEMENT_CHANGE` as changes in key managerial personnel, but did not guard against annotators indexing on the procedural phrase *"Meeting of the Board of Directors"*.

### New Rule:
- Announcements of director appointments, resignations, cessations, or demises must **NOT** be classified as `EARNINGS_RESULTS` merely because the exchange circular references a meeting of the Board of Directors.
- Annotators must assign **`MANAGEMENT_CHANGE`** whenever management personnel or board composition change is the substantive operational event of the disclosure.
- **Director Demise Calibration**: Notices of director demise represent solemn personal loss but carry negligible ex-ante financial impact for large-cap constituents; code as **`NEUTRAL`**, `importance = 2`, `relevance = LOW`, and event category **`MANAGEMENT_CHANGE`**.

### Reason for Change:
The human pilot exhibited an inattention slip, coding an isolated independent director cessation as `EARNINGS_RESULTS` because the header mentioned the company informing the exchange of board actions.

### Affected Disagreement Pattern:
- **Pattern 1**: Human defaulting to `EARNINGS_RESULTS`.

### Concrete Examples from 50-Record Pilot:
- **`ANN_000020` (Indian Oil Corporation)**: Headline: *"IOC: Cessation of Directorship – Indian Oil Corporation Ltd has informed the Exchange that Shri. Vineet Nayyar, an Independent Director... has ceased to be a Director..."*. Human labeled `EARNINGS_RESULTS`. AI2 correctly labeled `MANAGEMENT_CHANGE`. Under the new rule, this is unambiguously `MANAGEMENT_CHANGE`.

### Potential Unintended Consequences & Mitigations:
- *Risk*: A CEO resignation announced concurrently with disastrous quarterly earnings might have earnings overlooked.
- *Mitigation*: Rule 1 (Multi-Event Precedence Waterfall) maintains `EARNINGS_RESULTS` as primary, while `MANAGEMENT_CHANGE` is captured as secondary.

---

## 5. Refinement 4: Strict Boundaries on the `OTHER` Event Category

### Old Rule:
`OTHER` (or `ROUTINE_COMMENTARY`) was available as a residual category for general market commentary and secretarial filings, but lacked guidance on how to evaluate press release announcements.

### New Rule:
- `OTHER` must be used **ONLY** when the filing cannot logically map to any of the 15 substantive canonical event classes.
- **Substance-First Evaluation for Press Releases**: Routine press release intimations or exchange cover letters must be examined for actual economic substance before assigning `OTHER`:
  - Major commercial contracts or customer wins $ightarrow$ **`ORDER_CONTRACT`**
  - Plant commissioning, capacity expansion, or physical investments $ightarrow$ **`CAPEX_BUSINESS_UPDATE`**
  - Strikes, factory disruptions, or regulatory inspections $ightarrow$ **`OPERATIONAL_EVENT`**
  - Show-cause notices, tax demand appeals, or court orders $ightarrow$ **`REGULATORY_LEGAL`**
  - Share capital alteration, record date, or book closure $ightarrow$ **`CORPORATE_ACTION`**
- Only purely procedural secretarial notifications with zero operational substance (e.g. change of company secretary address, registry update) may be assigned `OTHER`.

### Reason for Change:
AI2 exhibited an excessively high `OTHER` rate (34.19% across the full 1,050 dataset, compared to 12.10% in the original development set), collapsing valuable commercial announcements into the uninformative `OTHER` bucket.

### Affected Disagreement Pattern:
- **Pattern 4**: Model over-conservatism on procedural press release headers.

### Concrete Examples from 50-Record Pilot:
- **`ANN_000023` (JSW Steel)**: Headline: *"JSWSTEEL: Press Release – 14% growth in April 2008 in Crude Steel production"*. AI2 labeled `OTHER` simply because of the `"Press Release"` header, whereas the content represents an operational business volume update (`CAPEX_BUSINESS_UPDATE` or `OPERATIONAL_EVENT`).

### Potential Unintended Consequences & Mitigations:
- *Risk*: Annotators might force completely unclassifiable noise (e.g. loss of share certificates) into operational categories.
- *Mitigation*: The rule preserves `OTHER` for truly non-operational administrative filings.

---

## 6. Machine-Readable Configuration (`configs/annotation_guidelines_rules.json`)

To enable automated validation and prompt engineering for subsequent annotation runs, all four rules have been compiled into JSON:

```json
{
  "name": "nifty_ai_annotation_guidelines_rules",
  "version": "1.1.0",
  "multi_event_precedence": {
    "waterfall": [
      "EARNINGS_RESULTS",
      "DIVIDEND",
      "M_AND_A",
      "MANAGEMENT_CHANGE",
      "CORPORATE_ACTION",
      "OTHER"
    ],
    "dividend_exception": "Classify strictly as DIVIDEND if solely dividend announcement"
  },
  "esop_fundraising_materiality": {
    "esop_dilution_threshold_pct": 0.1,
    "below_threshold": {
      "primary_event": "CORPORATE_ACTION",
      "importance_range": [1, 2],
      "default_sentiment": "NEUTRAL"
    },
    "fundraising_reservation": "QIPs, rights issues, material preferential allotments"
  },
  "management_change": {
    "substantive_event_rule": "Must NOT be classified as EARNINGS_RESULTS merely due to board meeting reference",
    "required_event": "MANAGEMENT_CHANGE"
  },
  "other_category_boundaries": {
    "usage_rule": "ONLY when filing cannot logically map to 15 substantive canonical classes",
    "substance_first_press_releases": true
  }
}
```

---

## 7. Integrity Verification & Test Execution

All six protected datasets were verified byte-for-byte:
1. **Original Human Pilot** in `ai_assisted_development_annotations.csv`: Unchanged (SHA-256: `3f1ebc67...`).
2. **Corrected Human Pilot** in `human_pilot_annotations_corrected.csv`: Unchanged (SHA-256: `f01b5950...`).
3. **AI-Simulated Annotator 2** in `annotator_2_simulated_annotations_1050.csv`: Unchanged (SHA-256: `a0cb992b...`).
4. **Original AI Development Set** (1,000 records): Unchanged.
5. **200-Record Terminal Holdout** in `gold_holdout_annotation_input.csv`: Unchanged and quarantined (0 labels).
6. **Phase 5/6/7 Assets**: Unchanged.

### Test Results:
```text
pytest tests/test_news.py -v
============================= 44 passed in 3.83s ==============================

pytest -q
============================ 141 passed in 6.80s ==============================
```

---

## 8. Readiness Assessment for Fresh Independent Annotation

The Phase 8 annotation methodology has now completed:
1. Forensic audit of the historical 50-record human pilot.
2. Formal application and logging of human review corrections.
3. Sensitivity audit against AI-Simulated Annotator 2.
4. Identification of root-cause ambiguities.
5. Codification of targeted operational refinements in guidelines and machine-readable schema.

**Methodological Verdict**: **`READY FOR FRESH INDEPENDENT HUMAN ANNOTATION ROUND`**.

*Note: Phase 8 remains unsealed and Phase 9 prohibited until genuine independent human-human double annotation is completed.*
