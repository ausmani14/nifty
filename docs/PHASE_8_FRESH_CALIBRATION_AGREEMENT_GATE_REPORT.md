# Phase 8 — Fresh Calibration Agreement Gate Report

**Audit Date**: September 16, 2026  
**Auditor**: Senior NLP Evaluation Engineer & Quantitative Research Methodology Auditor  
**Calibration Package**: Fresh 50-Record Independent Sample (`CAL2_000001` through `CAL2_000050`)  
**Input Artifact**: `data/interim/news/fresh_calibration_50_input.csv` (SHA-256: `6ce1d58dfd3634cd597f840a6d6972f129e9aa3c77e4bab20b417aeb78d7f091`)  
**Manifest Artifact**: `data/interim/news/fresh_calibration_50_manifest.csv` (SHA-256: `cf5f9902d343b2a1cc05186427f353177d75a9053d67c3188d587e214f8b19e0`)  
**Human Annotations Artifact**: `data/interim/news/fresh_calibration_50_human_annotations.csv` (SHA-256: `5ad5677d101054a22110b103ddba692ec955aaade3734ce40f6ff0e43885a6e8`)  
**Applied Guidelines Version**: Version 1.1.0 (`docs/PHASE_8_HUMAN_ANNOTATION_GUIDELINES.md`)  
**Machine-Readable Rules**: `configs/annotation_guidelines_rules.json`  
**Phase 8 Sealing Status**: **STRICTLY UNSEALED**  
**Phase 9 Status**: **STRICTLY PROHIBITED**  

---

## 1. Executive Summary

A formal calibration agreement gate evaluation was conducted on the fresh 50-record calibration dataset (`CAL2_000001` through `CAL2_000050`). The 50 annotations were provided directly by the project owner as authoritative human judgments. In strict compliance with research governance protocols:
1. **Preservation Verbatim**: The 50 human labels were merged with the source metadata and preserved byte-for-byte in `data/interim/news/fresh_calibration_50_human_annotations.csv` without automated normalization, filtering, or silent correction.
2. **Methodological Independence**: Zero labels were copied or derived from the previous pilot (`ANN_000001`–`ANN_000050`) or AI-Simulated Annotator 2.
3. **Inter-Annotator Agreement Status**: Because only a single human annotator provided labels for this calibration round, **no chance-corrected inter-annotator agreement coefficient (Cohen's $\kappa$, Fleiss' $\kappa$, Krippendorff's $\alpha$) can be calculated**.
4. **Final Gate Verdict**: **`B) HUMAN CALIBRATION GATE BLOCKED — INDEPENDENT SECOND HUMAN REQUIRED`**.

---

## A. Schema and Label Validity

All 50 human-provided annotations were audited against the canonical Phase 8 categorical schema:

| Evaluation Field | Allowed Canonical Domain | Valid Count (N=50) | Violation Count | Compliance Rate |
| :--- | :--- | :---: | :---: | :---: |
| `calibration_id` | `^CAL2_[0-9]{6}$` | 50 | 0 | 100.0% |
| `source_record_id`| Non-empty string (`RAW_NSE_*`) | 50 | 0 | 100.0% |
| `sentiment` | `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `UNCERTAIN` | 50 | 0 | 100.0% |
| `confidence` | `HIGH`, `MEDIUM`, `LOW` | 50 | 0 | 100.0% |
| `relevance` | `HIGH`, `MEDIUM`, `LOW`, `NONE` | 50 | 0 | 100.0% |
| `importance` | Integer scale `1` to `5` | 50 | 0 | 100.0% |
| `primary_event` | Canonical 16 corporate event classes | 50 | 0 | 100.0% |
| `annotation_method`| Set explicitly to `HUMAN_CALIBRATION` | 50 | 0 | 100.0% |

**Result**: **100.0% Schema Compliance** (0 schema errors, zero formatting defects).

---

## B. Empirical Distributions of Human Calibration Labels (N = 50)

### 1. Sentiment Distribution
| Sentiment | Count | Percentage | Methodological Notes |
| :--- | :---: | :---: | :--- |
| **`NEUTRAL`** | 29 | 58.0% | Reflects realistic dominance of statutory corporate disclosures |
| **`POSITIVE`** | 18 | 36.0% | Strong representation of commercial orders, acquisitions, and dividends |
| **`NEGATIVE`** | 3 | 6.0% | Low incidence, consistent with voluntary corporate filing asymmetry |
| **`UNCERTAIN`** | 0 | 0.0% | Annotator demonstrated decisive categorizations across all items |
| **Total** | **50** | **100.0%** | |

### 2. Annotator Confidence Distribution
| Confidence Level | Count | Percentage | Notes |
| :--- | :---: | :---: | :--- |
| **`MEDIUM`** | 40 | 80.0% | Modal category; healthy epistemic modesty on complex disclosures |
| **`HIGH`** | 9 | 18.0% | Assigned to unambiguous commercial contracts and major M&A announcements |
| **`LOW`** | 1 | 2.0% | Assigned to ambiguous outcome filings (`CAL2_000048`) |
| **Total** | **50** | **100.0%** | |

### 3. Market Relevance Distribution
| Relevance Level | Count | Percentage | Notes |
| :--- | :---: | :---: | :--- |
| **`MEDIUM`** | 34 | 68.0% | Standard corporate disclosure relevance to NIFTY constituents |
| **`HIGH`** | 15 | 30.0% | Significant index-heavyweight financial and strategic catalysts |
| **`LOW`** | 1 | 2.0% | Minor administrative/insider disclosure (`CAL2_000001`) |
| **`NONE`** | 0 | 0.0% | Unused |
| **Total** | **50** | **100.0%** | |

### 4. Economic Importance Distribution
| Importance Level | Count | Percentage | Operational Definition |
| :---: | :---: | :---: | :--- |
| **1** | 0 | 0.0% | Negligible / Noise (unused) |
| **2** | 1 | 2.0% | Minor statutory notice (`CAL2_000001`) |
| **3** | 33 | 66.0% | Standard material announcement (dominant baseline) |
| **4** | 12 | 24.0% | High-impact commercial, M&A, and regulatory catalysts |
| **5** | 4 | 8.0% | Transformational / index-shifting events |
| **Total** | **50** | **100.0%** | Mean Importance: **3.38 / 5.00** |

### 5. Primary Event Distribution (12 Canonical Classes Represented)
| Primary Event Category | Count | Percentage | Representation Status |
| :--- | :---: | :---: | :--- |
| `EARNINGS_RESULTS` | 15 | 30.0% | Healthy reduction from 52.0% in Pilot 1 |
| `REGULATORY_LEGAL` | 6 | 12.0% | Substantial regulatory representation |
| `DIVIDEND` | 5 | 10.0% | Routine dividend recommendations |
| `M_AND_A` | 4 | 8.0% | Material corporate amalgamations |
| `CORPORATE_ACTION` | 4 | 8.0% | Balance sheet and capital filings |
| `SHAREHOLDING_CHANGE` | 3 | 6.0% | Ownership and promoter disclosures |
| `ORDER_CONTRACT` | 3 | 6.0% | Major commercial wins |
| `MANAGEMENT_CHANGE` | 3 | 6.0% | Board appointments and resignations |
| `CREDIT_RATING_DEBT` | 3 | 6.0% | Rating agency updates and debt notes |
| `OPERATIONAL_EVENT` | 2 | 4.0% | Factory and operational updates |
| `STRATEGIC_PARTNERSHIP`| 1 | 2.0% | Commercial alliances |
| `CAPEX_BUSINESS_UPDATE`| 1 | 2.0% | Expansion updates |
| *Remaining 4 Classes* | 0 | 0.0% | `BUYBACK`, `BONUS_SPLIT`, `FUNDRAISING`, `OTHER` (Unused) |
| **Total** | **50** | **100.0%** | **12 / 16 Classes Active** |

---

## C. Analysis of Conflicts with Version 1.1 Annotation Guidelines

Without modifying any human-provided label, an objective forensic check of the 50 labels against the primary filing text revealed several notable internal discrepancies with Version 1.1 Guidelines:

| Calibration ID | Company | Filing Text Essence | Human Label Assigned | Guideline v1.1 Rule Conflict |
| :--- | :--- | :--- | :--- | :--- |
| **`CAL2_000006`** | `UPL` | Public announcement regarding **completion/closure of buyback** of shares. | `sent=POSITIVE`, `imp=5`, **`ev=ORDER_CONTRACT`** | **Event & Importance Conflict**: Buyback closure is `CORPORATE_ACTION` (or `BUYBACK`), not `ORDER_CONTRACT`. `imp=5` violates importance ceiling guidelines for routine buyback closure. |
| **`CAL2_000011`** | `TATASTEEL` | Intimation informing exchange about **Loss of Share Certificates**. | `sent=POSITIVE`, **`imp=5`**, **`ev=REGULATORY_LEGAL`** | **Event, Polarity & Importance Conflict**: Loss of share certificates is purely procedural secretarial noise; guidelines mandate `NEUTRAL`, `imp=1`, and event `ROUTINE_COMMENTARY` / `OTHER`. |
| **`CAL2_000013`** | `KOTAKBANK` | Submission of copy of disclosure under **Insider Trading Regulation** 13(3). | `sent=POSITIVE`, `imp=3`, **`ev=DIVIDEND`** | **Event Conflict**: Insider trading shareholding change is `SHAREHOLDING_CHANGE` or `REGULATORY_LEGAL`, not `DIVIDEND`. |
| **`CAL2_000016`** | `ONGC` | Intimation of board meeting considering **recommendation of final dividend**. | `sent=POSITIVE`, **`imp=5`**, **`ev=ORDER_CONTRACT`** | **Event & Importance Conflict**: Dividend recommendation is `DIVIDEND` under Rule 1 Exception, not `ORDER_CONTRACT`. `imp=5` violates ceiling for dividend notices. |
| **`CAL2_000021`** | `SUZLON` | Signing of repeat **commercial order for 57 MW wind turbines** with Ayen Enerji. | `sent=POSITIVE`, `imp=4`, **`ev=DIVIDEND`** | **Event Conflict**: A major commercial equipment supply contract is unambiguously `ORDER_CONTRACT`, not `DIVIDEND`. |
| **`CAL2_000024`** | `MARUTI` | Intimation informing exchange regarding monthly **Production Figures**. | `sent=POSITIVE`, `imp=4`, **`ev=REGULATORY_LEGAL`** | **Event Conflict**: Monthly production figures are operational metrics (`OPERATIONAL_EVENT` or `CAPEX_BUSINESS_UPDATE`), not `REGULATORY_LEGAL`. |
| **`CAL2_000028`** | `VEDL` | Disclosure under Reg 30 of SEBI (SAST) Reg. 2011 by Finisider International. | `sent=NEGATIVE`, `imp=4`, **`ev=CREDIT_RATING_DEBT`** | **Event Conflict**: Substantial acquisition of shares and takeovers (SAST) disclosure is `SHAREHOLDING_CHANGE`, not `CREDIT_RATING_DEBT`. |
| **`CAL2_000041`** | `DRREDDY` | Intimation of Nomination & Compensation Committee regarding **ESOPs/ESOS/ESPS**. | `sent=POSITIVE`, **`imp=5`**, **`ev=ORDER_CONTRACT`** | **Event, Materiality & Importance Conflict**: ESOP grants are `CORPORATE_ACTION`, not `ORDER_CONTRACT`. Violates Rule 2 (ESOP dilution ceiling: importance must be 1 or 2). |
| **`CAL2_000047`** | `BOSCHLTD` | Notice of **closure of Trading Window** pursuant to Insider Trading Code. | `sent=POSITIVE`, `imp=4`, **`ev=REGULATORY_LEGAL`** | **Polarity & Importance Conflict**: Trading window closure is routine secretarial notice (`sent=NEUTRAL`, `imp=1`, `ROUTINE_COMMENTARY`/`OTHER`). |
| **`CAL2_000048`** | `SBIN` | Board recommended **dividend of Rs. 2.60 per share** (260%). | `sent=NEGATIVE`, `imp=3`, **`ev=OPERATIONAL_EVENT`** | **Event Conflict**: Stated dividend recommendation is `DIVIDEND`, not `OPERATIONAL_EVENT`. |

*Note*: These observations demonstrate why independent double-annotation and formal adjudication are indispensable prior to freezing gold benchmarks.

---

## D. Mathematical Calculation of Inter-Annotator Agreement

- **Number of Human Coders**: Exactly **1** (project owner).
- **Mathematical Reality**:
  $$\kappa = rac{p_o - p_e}{1 - p_e}$$
  Cohen's Kappa ($\kappa$), Fleiss' Kappa, and Krippendorff's Alpha ($lpha$) require a minimum of two independent coders evaluated across identical items.
- **Scientific Prohibition**: With $K = 1$, chance-corrected agreement statistics are mathematically undefined. Reporting an artificial agreement metric would constitute scientific fabrication.
- **Conclusion**: **No inter-annotator agreement score is calculated or claimed**.

---

## E. Exact Blocker for Declaring the Calibration Gate Passed

The formal calibration gate requires:
$$\kappa_{	ext{human-human}} \ge 0.75 \quad 	ext{across independent double-blind annotators}$$

### The Blocking Factor:
1. **Absence of Independent Second Human Annotator**: Exactly one set of human labels was provided. Without an independent Annotator 2 submitting a blind template on `CAL2_000001`–`CAL2_000050`, inter-annotator agreement cannot be computed.
2. **Internal Taxonomy Divergences**: As documented in Section C, multiple records exhibit clear divergences from the canonical guidelines (e.g. order contracts coded as dividends, loss of share certificates coded as regulatory legal with importance 5). These require formal adjudication.

---

## F. Tests Executed and Verification Results

```text
pytest tests/test_news.py -v
============================= 44 passed in 3.27s ==============================

pytest -q
============================ 141 passed in 5.72s ==============================
```

- **News and Point-in-Time Test Suite**: **44 / 44 PASSED** (100%).
- **Full Repository Test Suite**: **141 / 141 PASSED** (100%).

---

## G. Checksums of Calibration Artifacts

```text
data/interim/news/fresh_calibration_50_input.csv
SHA-256: 6ce1d58dfd3634cd597f840a6d6972f129e9aa3c77e4bab20b417aeb78d7f091

data/interim/news/fresh_calibration_50_manifest.csv
SHA-256: cf5f9902d343b2a1cc05186427f353177d75a9053d67c3188d587e214f8b19e0

data/interim/news/fresh_calibration_50_human_annotations.csv
SHA-256: 5ad5677d101054a22110b103ddba692ec955aaade3734ce40f6ff0e43885a6e8
```

---

## H. Immutable Asset Confirmations

- [x] **Raw Authentic News Inventory** (`raw_authentic_news_inventory.jsonl`): Exactly 62,329 records, SHA-256: `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` (**100% UNCHANGED**).
- [x] **Original AI-Assisted Development Set** (`ai_assisted_development_annotations.csv`): Exactly 1,050 records, SHA-256: `3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c` (**100% UNCHANGED**).
- [x] **Terminal Holdout** (`gold_holdout_annotation_input.csv`): Exactly 200 records, 0 labels, 0 model predictions (**STRICTLY QUARANTINED**).
- [x] **Phase 5/6/7 Assets**: All models and pipelines intact (**100% UNCHANGED**).
- [x] **Phase 9 Execution**: **STRICTLY PROHIBITED** (zero models trained, zero alpha features created).
- [x] **Phase 8 Sealing**: **STRICTLY UNSEALED**.

---

## 2. Final Calibration Gate Verdict

### **`B) HUMAN CALIBRATION GATE BLOCKED — INDEPENDENT SECOND HUMAN REQUIRED`**

#### Formal Rationale:
1. **Single-Annotator Limitation**: Inter-coder reliability ($\kappa \ge 0.75$) mathematically requires two independent human annotators. With only one human annotator participating, the calibration agreement gate cannot be certified.
2. **Guideline Adjudication Required**: Internal taxonomy discrepancies must be reconciled through formal adjudication before these 50 records can serve as certified ground truth.
3. **Strict Scientific Integrity**: The project maintains strict quantitative standards. Phase 8 will remain unsealed until a genuine second human annotator provides independent labels.

---

*Report compiled for the NIFTY AI quantitative research repository.*
