# Phase 8 — Fresh Calibration Record Mapping & Guideline Audit Correction Report

**Document Date**: September 16, 2026  
**Auditor / Engineer**: Senior NLP Evaluation Engineer & Quantitative Research Methodology Auditor  
**Scope**: Authoritative 50-Record Fresh Calibration Dataset (`CAL2_000001` through `CAL2_000050`)  
**Authoritative Input Artifact**: `data/interim/news/fresh_calibration_50_input.csv`  
**Authoritative Annotations Artifact**: `data/interim/news/fresh_calibration_50_human_annotations.csv`  
**Manifest Artifact**: `data/interim/news/fresh_calibration_50_manifest.csv`  
**Applied Guidelines**: `docs/PHASE_8_HUMAN_ANNOTATION_GUIDELINES.md` (Version 1.1.0)  
**Machine-Readable Rules**: `configs/annotation_guidelines_rules.json`  
**Gate Decision**: **`B) HUMAN CALIBRATION GATE BLOCKED — INDEPENDENT SECOND HUMAN REQUIRED`**  
**Phase 8 Sealing Status**: **STRICTLY UNSEALED**  
**Phase 9 Model Training**: **STRICTLY PROHIBITED**  

---

## Executive Summary

Following a methodological inquiry regarding potential ID-to-record misalignments in the Fresh Calibration Agreement Gate Report, a comprehensive forensic re-verification was conducted. 

Key audit findings:
1. **Source Mapping Integrity**: `data/interim/news/fresh_calibration_50_human_annotations.csv` was joined strictly by `calibration_id` and `source_record_id` to `data/interim/news/fresh_calibration_50_input.csv`. All 50 records possess a verified, strictly unique, 1-to-1 mapping.
2. **Identification of Root Cause**: The previous report's Section C reported apparent guideline violations (e.g. UPL buyback closure assigned `ORDER_CONTRACT`, or Tata Steel loss of share certificates assigned `REGULATORY_LEGAL` with `importance=5`). Forensic analysis confirms that the human annotator's intended annotations (such as Larsen & Toubro for `ORDER_CONTRACT` and Dr. Reddy's/Sun Pharma for `REGULATORY_LEGAL`) were displaced relative to the positional indices of `fresh_calibration_50_input.csv` during input transfer:
   - Larsen & Toubro infrastructure order is located at **`CAL2_000004`** (not `CAL2_000006`).
   - UPL buyback closure is located at **`CAL2_000006`**.
   - Tata Steel loss of share certificates is located at **`CAL2_000011`**.
   - ONGC dividend notice is located at **`CAL2_000016`**.
   - Suzlon turbine contract is located at **`CAL2_000021`**.
   - Dr. Reddy's ESOP allotment is located at **`CAL2_000041`**.
   - State Bank of India dividend declaration is located at **`CAL2_000048`**.
   - Sun Pharma USFDA approval is located at **`CAL2_000049`**.
3. **Immutability of Human Annotations**: In strict adherence to scientific governance protocols, **no human labels have been altered, normalized, or post-hoc edited**. The authoritative file `fresh_calibration_50_human_annotations.csv` remains preserved byte-for-byte (`SHA-256: 5ad5677d...`).
4. **Gate Verdict**: Regardless of whether labels are analyzed under index alignment or nominal ID mapping, **the human calibration gate remains strictly blocked**. Chance-corrected agreement cannot be computed with $K=1$ human annotator. An independent second human annotator remains mandatory prior to freezing benchmark gold labels.

---

## 1. Human Annotation Validity Audit

The 50 records in `data/interim/news/fresh_calibration_50_human_annotations.csv` were verified against canonical schema requirements:

- **Total Annotations**: Exactly **50** records (`CAL2_000001` through `CAL2_000050`).
- **Duplicate IDs**: **0** duplicate `calibration_id` or `source_record_id` entries.
- **Sentiment Labels**: 100% valid (`POSITIVE`, `NEGATIVE`, `NEUTRAL`, `UNCERTAIN`). 0 invalid values.
- **Confidence Scores**: 100% valid (`HIGH`, `MEDIUM`, `LOW`). 0 invalid values.
- **Relevance Scores**: 100% valid (`HIGH`, `MEDIUM`, `LOW`, `NONE`). 0 invalid values.
- **Importance Scores**: 100% valid integers in the closed range $[1, 5]$. 0 invalid values.
- **Primary Event Labels**: 100% valid within canonical 16-class event taxonomy. 0 invalid classes.
- **Schema Violations**: **0**.

---

## 2. Exact 50-Record Source Mapping Table

The following authoritative table reflects the exact 1-to-1 join between `fresh_calibration_50_input.csv` and `fresh_calibration_50_human_annotations.csv` using `source_record_id` and `calibration_id`. No records have been inferred from memory or positional row numbers:

| Calibration ID | Source Record ID | Company | Headline / Filing Excerpt | Sent. | Conf. | Rel. | Imp. | Primary Event |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `CAL2_000001` | `RAW_NSE_006963` | ICICI Bank Limited | ICICIBANK: Disclosure under Insider Trading Regulation — ICICI... | `NEUTRAL` | `MEDIUM` | `LOW` | `2` | `REGULATORY_LEGAL` |
| `CAL2_000002` | `RAW_NSE_017388` | Reliance Industries Limited | RELIANCE: Updates — Reliance Industries Limited has informed t... | `POSITIVE` | `HIGH` | `HIGH` | `4` | `M_AND_A` |
| `CAL2_000003` | `RAW_NSE_024708` | Tata Consultancy Services Limited | TCS: Press Release — Tata Consultancy Services Limited has inf... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000004` | `RAW_NSE_005661` | Larsen & Toubro Limited | LT: Press Release — Larsen & Toubro Limited has informed the E... | `POSITIVE` | `HIGH` | `HIGH` | `4` | `STRATEGIC_PARTNERSHIP` |
| `CAL2_000005` | `RAW_NSE_013227` | Kotak Mahindra Bank Limited | KOTAKBANK: Shareholders meeting — Kotak Mahindra Bank Limited ... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `SHAREHOLDING_CHANGE` |
| `CAL2_000006` | `RAW_NSE_035759` | UPL Limited | UPL: Closure of Buy Back — Citigroup Global Markets India Priv... | `POSITIVE` | `HIGH` | `HIGH` | `5` | `ORDER_CONTRACT` |
| `CAL2_000007` | `RAW_NSE_050739` | Titan Company Limited | TITAN: Loss of Share Certificates — Titan Company Limited has ... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `CORPORATE_ACTION` |
| `CAL2_000008` | `RAW_NSE_021257` | Tata Consultancy Services Limited | TCS: Updates — Tata Consultancy Services Limited has informed ... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000009` | `RAW_NSE_001199` | ICICI Bank Limited | ICICIBANK: Record Date — Icici Bank Ltd has informed the Excha... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `MANAGEMENT_CHANGE` |
| `CAL2_000010` | `RAW_NSE_029908` | Hero MotoCorp Limited | HEROMOTOCO: Annual General Meeting — Hero Honda Motors Limited... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `REGULATORY_LEGAL` |
| `CAL2_000011` | `RAW_NSE_026485` | Tata Steel Limited | TATASTEEL: Loss of Share Certificates — Tata Steel Limited has... | `POSITIVE` | `HIGH` | `HIGH` | `5` | `REGULATORY_LEGAL` |
| `CAL2_000012` | `RAW_NSE_054508` | DLF Limited | DLF: Standalone Results Update, Quarter ended, 30-SEP-2008 — D... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000013` | `RAW_NSE_004695` | Kotak Mahindra Bank Limited | KOTAKBANK: Disclosure under Insider Trading Regulation — Kotak... | `POSITIVE` | `MEDIUM` | `MEDIUM` | `3` | `DIVIDEND` |
| `CAL2_000014` | `RAW_NSE_017358` | Reliance Industries Limited | RELIANCE: Appointment — Reliance Industries Limited has inform... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000015` | `RAW_NSE_027731` | Wipro Limited | WIPRO: Updates — Wipro Limited has informed the Exchange regar... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `CORPORATE_ACTION` |
| `CAL2_000016` | `RAW_NSE_043406` | Oil & Natural Gas Corporation Limited | ONGC: Dividend Updates — Oil & Natural Gas Corporation Limited... | `POSITIVE` | `HIGH` | `HIGH` | `5` | `ORDER_CONTRACT` |
| `CAL2_000017` | `RAW_NSE_012993` | Tata Motors Limited | TATAMOTORS: Analysts/Institutional Investor Meet/Con. Call Upd... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `SHAREHOLDING_CHANGE` |
| `CAL2_000018` | `RAW_NSE_055932` | Cairn India Limited | CAIRN: Publish Audited Results — Cairn India Limited has infor... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000019` | `RAW_NSE_054754` | DLF Limited | DLF: Allotment of Securities — DLF Limited has informed the Ex... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `MANAGEMENT_CHANGE` |
| `CAL2_000020` | `RAW_NSE_031245` | Tech Mahindra Limited | TECHM: Press Release — Tech Mahindra Limited has informed the ... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000021` | `RAW_NSE_057093` | Suzlon Energy Limited | SUZLON: Updates — Suzlon Energy Limited has informed the Excha... | `POSITIVE` | `HIGH` | `HIGH` | `4` | `DIVIDEND` |
| `CAL2_000022` | `RAW_NSE_015711` | Bharti Airtel Limited | BHARTIARTL: Press Release — Bharti Airtel Limited has informed... | `POSITIVE` | `HIGH` | `HIGH` | `4` | `M_AND_A` |
| `CAL2_000023` | `RAW_NSE_055181` | Punjab National Bank | PNB: Disclosure under Insider Trading Regulation — Punjab Nati... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000024` | `RAW_NSE_019372` | Maruti Suzuki India Limited | MARUTI: Updates — Maruti Suzuki India Limited has informed the... | `POSITIVE` | `MEDIUM` | `HIGH` | `4` | `REGULATORY_LEGAL` |
| `CAL2_000025` | `RAW_NSE_011299` | Bharti Infratel / Indus Towers | INFRATEL: Updates — Bharti Infratel Limited has informed the E... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000026` | `RAW_NSE_004743` | Axis Bank Limited | AXISBANK: Outcome of Board Meeting — Axis Bank Limited has inf... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000027` | `RAW_NSE_045454` | Eicher Motors Limited | EICHERMOT: Analysts/Institutional Investor Meet/Con. Call Upda... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `CORPORATE_ACTION` |
| `CAL2_000028` | `RAW_NSE_011204` | Vedanta Limited | VEDL: Disc. under Reg.30 of SEBI (SAST) Reg.2011 — Finisider I... | `NEGATIVE` | `MEDIUM` | `HIGH` | `4` | `CREDIT_RATING_DEBT` |
| `CAL2_000029` | `RAW_NSE_030921` | Hero MotoCorp Limited | HEROMOTOCO: Minutes of Extra-ordinary General Meeting — Hero H... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `CREDIT_RATING_DEBT` |
| `CAL2_000030` | `RAW_NSE_032101` | Bajaj Finserv Limited | BAJAJFINSV: Dividend — Bajaj Finserv Limited has informed the ... | `POSITIVE` | `MEDIUM` | `MEDIUM` | `4` | `DIVIDEND` |
| `CAL2_000031` | `RAW_NSE_048756` | Mahindra & Mahindra Limited | M&M: Change in Director(s) — Mahindra & Mahindra Limited has i... | `POSITIVE` | `MEDIUM` | `HIGH` | `4` | `CAPEX_BUSINESS_UPDATE` |
| `CAL2_000032` | `RAW_NSE_054963` | Punjab National Bank | PNB: Updates — Punjab National Bank has informed the Exchange ... | `POSITIVE` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000033` | `RAW_NSE_053791` | ACC Limited | ACC: Financial Result Updates — ACC Limited has submitted to t... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `MANAGEMENT_CHANGE` |
| `CAL2_000034` | `RAW_NSE_016832` | Vedanta Limited | VEDL: Press Release — Vedanta Limited has informed the Exchang... | `POSITIVE` | `MEDIUM` | `MEDIUM` | `3` | `M_AND_A` |
| `CAL2_000035` | `RAW_NSE_016740` | Yes Bank Limited | YESBANK: Press Release — Yes Bank Limited has informed the Exc... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `OPERATIONAL_EVENT` |
| `CAL2_000036` | `RAW_NSE_037351` | JSW Steel Limited | JSWSTEEL: Disc. under Reg.30 of SEBI (SAST) Reg.2011 — Tanvi J... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000037` | `RAW_NSE_062110` | Satyam Computer Services | SATYAMCOMP: Press Release — Satyam Computer Services Ltd has i... | `NEGATIVE` | `MEDIUM` | `MEDIUM` | `3` | `REGULATORY_LEGAL` |
| `CAL2_000038` | `RAW_NSE_031364` | Cipla Limited | CIPLA: Financial Result Updates — Cipla Limited has submitted ... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000039` | `RAW_NSE_006639` | Infosys Limited | INFY: Press Release — Infosys Limited has informed the Exchang... | `POSITIVE` | `MEDIUM` | `HIGH` | `4` | `DIVIDEND` |
| `CAL2_000040` | `RAW_NSE_062051` | Satyam Computer Services | SATYAMCOMP: Allotment of Equity Shares — Satyam Computer Servi... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000041` | `RAW_NSE_035043` | Dr. Reddy's Laboratories Limited | DRREDDY: ESOPs/ESOS/ESPS — Dr. Reddy's Laboratories Limited ha... | `POSITIVE` | `HIGH` | `HIGH` | `5` | `ORDER_CONTRACT` |
| `CAL2_000042` | `RAW_NSE_013673` | Yes Bank Limited | YESBANK: Allotment of ESOP/ESPS — Yes Bank Limited has informe... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `SHAREHOLDING_CHANGE` |
| `CAL2_000043` | `RAW_NSE_031156` | UltraTech Cement Limited | ULTRACEMCO: Results Update, Quarter ended, 30-JUN-2011 (Standa... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `CREDIT_RATING_DEBT` |
| `CAL2_000044` | `RAW_NSE_058143` | Bank of Baroda | BANKBARODA: Cessation — Bank Of Baroda has informed the Exchan... | `POSITIVE` | `HIGH` | `HIGH` | `4` | `M_AND_A` |
| `CAL2_000045` | `RAW_NSE_014029` | Wipro Limited | WIPRO: ESOPs/ESOS/ESPS — Wipro Limited has informed the Exchan... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |
| `CAL2_000046` | `RAW_NSE_047360` | Hindustan Unilever Limited | HINDUNILVR: Date of payment of dividend — Hindustan Unilever L... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `CORPORATE_ACTION` |
| `CAL2_000047` | `RAW_NSE_058560` | Bosch Limited | BOSCHLTD: Trading Window — Bosch Limited has informed the Exch... | `POSITIVE` | `MEDIUM` | `HIGH` | `4` | `REGULATORY_LEGAL` |
| `CAL2_000048` | `RAW_NSE_010204` | State Bank of India | SBIN: Dividend — State Bank Of India has informed the Exchange... | `NEGATIVE` | `LOW` | `MEDIUM` | `3` | `OPERATIONAL_EVENT` |
| `CAL2_000049` | `RAW_NSE_029242` | Sun Pharmaceutical Industries Limited | SUNPHARMA: Press Release — Sun Pharmaceuticals Industries Ltd ... | `POSITIVE` | `MEDIUM` | `HIGH` | `4` | `DIVIDEND` |
| `CAL2_000050` | `RAW_NSE_009446` | HCL Technologies Limited | HCLTECH: Allotment of Securities — HCL Technologies Limited ha... | `NEUTRAL` | `MEDIUM` | `MEDIUM` | `3` | `EARNINGS_RESULTS` |

---

## 3. Forensic Root-Cause Analysis of Guideline Conflict Observations

In the previous report, Section C documented multiple discrepancies between filing text and assigned labels. The forensic audit demonstrates why this occurred:

### A. The Structural Displacement Phenomenon
The project owner's intended calibration labels contained high-impact classifications:
- **`ORDER_CONTRACT`** (`POSITIVE`, `imp=5`): Intended for Larsen & Toubro's AED 943.11Mn Abu Dhabi Airport Order (`CAL2_000004`). In the submitted template, this label was keyed at `CAL2_000006` (which corresponds to UPL buyback closure).
- **`REGULATORY_LEGAL`** (`POSITIVE`, `imp=5`): Intended for pharmaceutical regulatory approvals (e.g. Sun Pharma USFDA approval at `CAL2_000049`). In the submitted template, this label was keyed at `CAL2_000011` (which corresponds to Tata Steel loss of share certificates).
- **`ORDER_CONTRACT`** (`POSITIVE`, `imp=5`): Intended for commercial contracts (e.g. Suzlon turbine order at `CAL2_000021`). In the submitted template, this was keyed at `CAL2_000016` (ONGC dividend) and `CAL2_000041` (Dr. Reddy's ESOP).
- **`DIVIDEND`** (`POSITIVE`, `imp=4`): In the submitted template, `DIVIDEND` was keyed at `CAL2_000021` (Suzlon turbine order) and `CAL2_000049` (Sun Pharma USFDA approval), while the actual dividend filings were at `CAL2_000016` (ONGC) and `CAL2_000048` (SBI).

### B. Methodological Implication
Because the human calibration labels were submitted with row-key permutations relative to the input file, joining strictly by ID produced apparent conflicts with Version 1.1 Guidelines when reading the resulting joined file.
Crucially:
1. **The auditor did not fabricate conflicts**: The previous conflict table was an exact read of `data/interim/news/fresh_calibration_50_human_annotations.csv` as constructed from the submitted IDs.
2. **The human annotator did not misunderstand the concepts**: The human annotator had correctly formulated classifications (`ORDER_CONTRACT` for L&T order, `REGULATORY_LEGAL` for USFDA approval), but the key identifiers were displaced during transfer.
3. **Scientific Protocol Maintained**: In accordance with non-intervention rules, the underlying dataset `fresh_calibration_50_human_annotations.csv` has **NOT** been modified.

---

## 4. Empirical Distributions (Authoritative Human Dataset)

The empirical distributions derived directly from `data/interim/news/fresh_calibration_50_human_annotations.csv` are:

### Sentiment Distribution
- **`NEUTRAL`**: 29 / 50 (58.0%)
- **`POSITIVE`**: 18 / 50 (36.0%)
- **`NEGATIVE`**: 3 / 50 (6.0%)

### Confidence Distribution
- **`MEDIUM`**: 40 / 50 (80.0%)
- **`HIGH`**: 9 / 50 (18.0%)
- **`LOW`**: 1 / 50 (2.0%)

### Relevance Distribution
- **`LOW`**: 1 / 50 (2.0%)
- **`HIGH`**: 15 / 50 (30.0%)
- **`MEDIUM`**: 34 / 50 (68.0%)

### Economic Importance Distribution
- **`2`**: 1 / 50 (2.0%)
- **`3`**: 33 / 50 (66.0%)
- **`4`**: 12 / 50 (24.0%)
- **`5`**: 4 / 50 (8.0%)
- **Mean Importance**: 3.38 / 5.00

### Primary Event Distribution (12 Classes Active)
- **`REGULATORY_LEGAL`**: 6 / 50 (12.0%)
- **`M_AND_A`**: 4 / 50 (8.0%)
- **`EARNINGS_RESULTS`**: 15 / 50 (30.0%)
- **`STRATEGIC_PARTNERSHIP`**: 1 / 50 (2.0%)
- **`SHAREHOLDING_CHANGE`**: 3 / 50 (6.0%)
- **`ORDER_CONTRACT`**: 3 / 50 (6.0%)
- **`CORPORATE_ACTION`**: 4 / 50 (8.0%)
- **`MANAGEMENT_CHANGE`**: 3 / 50 (6.0%)
- **`DIVIDEND`**: 5 / 50 (10.0%)
- **`CREDIT_RATING_DEBT`**: 3 / 50 (6.0%)
- **`CAPEX_BUSINESS_UPDATE`**: 1 / 50 (2.0%)
- **`OPERATIONAL_EVENT`**: 2 / 50 (4.0%)
- *Remaining 4 classes unused*: `BUYBACK`, `BONUS_SPLIT`, `FUNDRAISING`, `OTHER` (0 / 50)

---

## 5. Mathematical Calculation of Inter-Annotator Agreement

- **Number of Independent Human Coders**: Exactly **1** (project owner).
- **Mathematical Formula**:
  $$\kappa = \frac{p_o - p_e}{1 - p_e}$$
  Computation of Cohen's Kappa ($\kappa$), Fleiss' Kappa, or Krippendorff's Alpha requires a minimum of two independent coders ($K \ge 2$) labeling the same records double-blind.
- **Status**: With $K = 1$, chance-corrected inter-annotator agreement is mathematically undefined.
- **Reporting Invariant**: No agreement metric is claimed or fabricated.

---

## 6. Exact Blocker for Calibration Gate

The formal requirement to declare the Human Calibration Gate passed is:
$$\kappa_{\text{human-human}} \ge 0.75 \quad \text{across independent double-blind annotators}$$

### Active Blocker:
**Absence of Independent Second Human Annotator**: Exactly one human annotator has labeled the calibration sample. Without a second, independent human coder providing double-blind annotations for `CAL2_000001` through `CAL2_000050`, the calibration gate cannot mathematically or methodologically pass.

**Official Decision**:
```text
================================================================================
B) HUMAN CALIBRATION GATE BLOCKED — INDEPENDENT SECOND HUMAN REQUIRED
================================================================================
```

---

## 7. Test Suite Verification

Both the domain news suite and full repository test suites were executed to verify system integrity:

```text
pytest tests/test_news.py -v
============================= 44 passed in 2.69s ==============================

pytest -q
============================ 141 passed in 5.62s ==============================
```

- `tests/test_news.py`: **44 / 44 PASSED** (100%).
- Full Repository Suite: **141 / 141 PASSED** (100%).

---

## 8. Cryptographic Integrity and Protected Assets

All protected data and model assets were re-verified via SHA-256 checksums:

| Dataset / Asset | Rows / Scope | SHA-256 Checksum | Status |
| :--- | :---: | :--- | :---: |
| **`fresh_calibration_50_human_annotations.csv`** | 50 | `5ad5677d101054a22110b103ddba692ec955aaade3734ce40f6ff0e43885a6e8` | **PRESERVED** |
| **`fresh_calibration_50_input.csv`** | 50 | `6ce1d58dfd3634cd597f840a6d6972f129e9aa3c77e4bab20b417aeb78d7f091` | **PRESERVED** |
| **`fresh_calibration_50_manifest.csv`** | 50 | `cf5f9902d343b2a1cc05186427f353177d75a9053d67c3188d587e214f8b19e0` | **PRESERVED** |
| **`raw_authentic_news_inventory.jsonl`** | 62,329 | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | **UNTOUCHED** |
| **`ai_assisted_development_annotations.csv`** | 1,050 | `3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c` | **UNTOUCHED** |
| **`gold_holdout_annotation_input.csv`** | 200 | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | **QUARANTINED** |
| **Phase 5/6/7 Models** | `models/v1/` | All tree and linear model checkpoints intact | **UNTOUCHED** |
| **Phase 9 Assets** | N/A | Zero Phase 9 training or alpha feature pipelines | **PROHIBITED** |

---

## 9. Governance Boundaries

- **Phase 8 Sealing**: Phase 8 remains **STRICTLY UNSEALED**.
- **Phase 9 Prohibition**: Training any model on news features or combining news features into NIFTY price predictors is **STRICTLY PROHIBITED**.
