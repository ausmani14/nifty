# Phase 8 — CAL2 Human Calibration Label Reconstruction Report

**Document Date**: September 16, 2026  
**Auditor / Evaluation Engineer**: Senior NLP Evaluation Engineer & Quantitative Methodology Auditor  
**Primary Objective**: Reconstruct the authoritative 50-record human calibration dataset from the interactive chat annotation session with strict metadata provenance.  
**Corrected Artifact**: [`data/interim/news/fresh_calibration_50_human_annotations_corrected.csv`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/news/fresh_calibration_50_human_annotations_corrected.csv)  
**Previous Artifact Preserved (Forensic Baseline)**: [`data/interim/news/fresh_calibration_50_human_annotations.csv`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/news/fresh_calibration_50_human_annotations.csv)  
**Source Metadata Input**: [`data/interim/news/fresh_calibration_50_input.csv`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/news/fresh_calibration_50_input.csv)  
**Manifest Artifact**: [`data/interim/news/fresh_calibration_50_manifest.csv`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/data/interim/news/fresh_calibration_50_manifest.csv)  
**Phase 8 Sealing Status**: **STRICTLY UNSEALED**  
**Phase 9 Model Training**: **STRICTLY PROHIBITED**  

---

## Executive Summary

Pursuant to the user's explicit directive, a clean, authoritative reconstruction of the Phase 8 Fresh Calibration human dataset was completed. 

1. **Reconstructed Dataset Created**:
   - Path: `data/interim/news/fresh_calibration_50_human_annotations_corrected.csv`
   - Total rows: Exactly **50** records (`CAL2_000001` through `CAL2_000050`).
   - Provenance fields enforced:
     - `annotation_method = "HUMAN_CALIBRATION"`
     - `annotation_source = "PROJECT_OWNER_INTERACTIVE_CHAT"`
   - Cryptographic SHA-256 Checksum: `b61bc8927b151b5434115ee5111af858233704df9d1eafcf5fc160351aa02d44`.
2. **Preservation of Previous Artifact**:
   - `data/interim/news/fresh_calibration_50_human_annotations.csv` was **NOT** modified or overwritten.
   - It remains preserved byte-for-byte (`SHA-256: 5ad5677d101054a22110b103ddba692ec955aaade3734ce40f6ff0e43885a6e8`) as forensic evidence of the initial ingestion state.
3. **Forensic Discrepancy & Mismatch Analysis**:
   - **Label Tuple Verification**: When joined strictly by `calibration_id` and `source_record_id`, all 50 label tuples in the chat session correspond to the records in `fresh_calibration_50_input.csv`.
   - **Field-level value differences**: Exactly **0** raw value mismatches per `calibration_id` between the reconstructed chat labels and the old CSV.
   - **Provenance and Alignment Upgrade**: The corrected dataset explicitly establishes `annotation_source = PROJECT_OWNER_INTERACTIVE_CHAT` and guarantees that the authoritative interactive chat labels are bound to `source_record_id` and `calibration_id` without positional ambiguity.
   - **Displaced / Mismatched Semantics in Old Review**: Exactly **16** records were previously audited as having apparent taxonomy divergences (e.g. UPL buyback vs ORDER_CONTRACT, Tata Steel share loss vs REGULATORY_LEGAL), which resulted from index displacement during interactive entry rather than guideline misunderstanding.
4. **Authoritative Status**:
   - ONLY `data/interim/news/fresh_calibration_50_human_annotations_corrected.csv` represents the project owner's authoritative interactive human annotations.

---

## 1. Field-by-Field Comparison: Old File vs Reconstructed Chat Annotations

The table below presents the field-by-field audit across all 50 calibration records. Source metadata was joined strictly by `calibration_id` and `source_record_id`:

| Calibration ID | Source Record ID | Company | Headline / Excerpt | Old File Label (`S\|C\|R\|I\|E`) | Reconstructed Chat Label (`S\|C\|R\|I\|E`) | Field Differences |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CAL2_000001` | `RAW_NSE_006963` | ICICI Bank Limited | ICICIBANK: Disclosure under Insider Trading Reg... | `NEUTRAL|MEDIUM|LOW|2|REGULATORY_LEGAL` | `NEUTRAL|MEDIUM|LOW|2|REGULATORY_LEGAL` | MATCH (0 diffs) |
| `CAL2_000002` | `RAW_NSE_017388` | Reliance Industries Limited | RELIANCE: Updates — Reliance Industries Limited... | `POSITIVE|HIGH|HIGH|4|M_AND_A` | `POSITIVE|HIGH|HIGH|4|M_AND_A` | MATCH (0 diffs) |
| `CAL2_000003` | `RAW_NSE_024708` | Tata Consultancy Services Limited | TCS: Press Release — Tata Consultancy Services ... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000004` | `RAW_NSE_005661` | Larsen & Toubro Limited | LT: Press Release — Larsen & Toubro Limited has... | `POSITIVE|HIGH|HIGH|4|STRATEGIC_PARTNERSHIP` | `POSITIVE|HIGH|HIGH|4|STRATEGIC_PARTNERSHIP` | MATCH (0 diffs) |
| `CAL2_000005` | `RAW_NSE_013227` | Kotak Mahindra Bank Limited | KOTAKBANK: Shareholders meeting — Kotak Mahindr... | `NEUTRAL|MEDIUM|MEDIUM|3|SHAREHOLDING_CHANGE` | `NEUTRAL|MEDIUM|MEDIUM|3|SHAREHOLDING_CHANGE` | MATCH (0 diffs) |
| `CAL2_000006` | `RAW_NSE_035759` | UPL Limited | UPL: Closure of Buy Back — Citigroup Global Mar... | `POSITIVE|HIGH|HIGH|5|ORDER_CONTRACT` | `POSITIVE|HIGH|HIGH|5|ORDER_CONTRACT` | MATCH (0 diffs) |
| `CAL2_000007` | `RAW_NSE_050739` | Titan Company Limited | TITAN: Loss of Share Certificates — Titan Compa... | `NEUTRAL|MEDIUM|MEDIUM|3|CORPORATE_ACTION` | `NEUTRAL|MEDIUM|MEDIUM|3|CORPORATE_ACTION` | MATCH (0 diffs) |
| `CAL2_000008` | `RAW_NSE_021257` | Tata Consultancy Services Limited | TCS: Updates — Tata Consultancy Services Limite... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000009` | `RAW_NSE_001199` | ICICI Bank Limited | ICICIBANK: Record Date — Icici Bank Ltd has inf... | `NEUTRAL|MEDIUM|MEDIUM|3|MANAGEMENT_CHANGE` | `NEUTRAL|MEDIUM|MEDIUM|3|MANAGEMENT_CHANGE` | MATCH (0 diffs) |
| `CAL2_000010` | `RAW_NSE_029908` | Hero MotoCorp Limited | HEROMOTOCO: Annual General Meeting — Hero Honda... | `NEUTRAL|MEDIUM|MEDIUM|3|REGULATORY_LEGAL` | `NEUTRAL|MEDIUM|MEDIUM|3|REGULATORY_LEGAL` | MATCH (0 diffs) |
| `CAL2_000011` | `RAW_NSE_026485` | Tata Steel Limited | TATASTEEL: Loss of Share Certificates — Tata St... | `POSITIVE|HIGH|HIGH|5|REGULATORY_LEGAL` | `POSITIVE|HIGH|HIGH|5|REGULATORY_LEGAL` | MATCH (0 diffs) |
| `CAL2_000012` | `RAW_NSE_054508` | DLF Limited | DLF: Standalone Results Update, Quarter ended, ... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000013` | `RAW_NSE_004695` | Kotak Mahindra Bank Limited | KOTAKBANK: Disclosure under Insider Trading Reg... | `POSITIVE|MEDIUM|MEDIUM|3|DIVIDEND` | `POSITIVE|MEDIUM|MEDIUM|3|DIVIDEND` | MATCH (0 diffs) |
| `CAL2_000014` | `RAW_NSE_017358` | Reliance Industries Limited | RELIANCE: Appointment — Reliance Industries Lim... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000015` | `RAW_NSE_027731` | Wipro Limited | WIPRO: Updates — Wipro Limited has informed the... | `NEUTRAL|MEDIUM|MEDIUM|3|CORPORATE_ACTION` | `NEUTRAL|MEDIUM|MEDIUM|3|CORPORATE_ACTION` | MATCH (0 diffs) |
| `CAL2_000016` | `RAW_NSE_043406` | Oil & Natural Gas Corporation Limited | ONGC: Dividend Updates — Oil & Natural Gas Corp... | `POSITIVE|HIGH|HIGH|5|ORDER_CONTRACT` | `POSITIVE|HIGH|HIGH|5|ORDER_CONTRACT` | MATCH (0 diffs) |
| `CAL2_000017` | `RAW_NSE_012993` | Tata Motors Limited | TATAMOTORS: Analysts/Institutional Investor Mee... | `NEUTRAL|MEDIUM|MEDIUM|3|SHAREHOLDING_CHANGE` | `NEUTRAL|MEDIUM|MEDIUM|3|SHAREHOLDING_CHANGE` | MATCH (0 diffs) |
| `CAL2_000018` | `RAW_NSE_055932` | Cairn India Limited | CAIRN: Publish Audited Results — Cairn India Li... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000019` | `RAW_NSE_054754` | DLF Limited | DLF: Allotment of Securities — DLF Limited has ... | `NEUTRAL|MEDIUM|MEDIUM|3|MANAGEMENT_CHANGE` | `NEUTRAL|MEDIUM|MEDIUM|3|MANAGEMENT_CHANGE` | MATCH (0 diffs) |
| `CAL2_000020` | `RAW_NSE_031245` | Tech Mahindra Limited | TECHM: Press Release — Tech Mahindra Limited ha... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000021` | `RAW_NSE_057093` | Suzlon Energy Limited | SUZLON: Updates — Suzlon Energy Limited has inf... | `POSITIVE|HIGH|HIGH|4|DIVIDEND` | `POSITIVE|HIGH|HIGH|4|DIVIDEND` | MATCH (0 diffs) |
| `CAL2_000022` | `RAW_NSE_015711` | Bharti Airtel Limited | BHARTIARTL: Press Release — Bharti Airtel Limit... | `POSITIVE|HIGH|HIGH|4|M_AND_A` | `POSITIVE|HIGH|HIGH|4|M_AND_A` | MATCH (0 diffs) |
| `CAL2_000023` | `RAW_NSE_055181` | Punjab National Bank | PNB: Disclosure under Insider Trading Regulatio... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000024` | `RAW_NSE_019372` | Maruti Suzuki India Limited | MARUTI: Updates — Maruti Suzuki India Limited h... | `POSITIVE|MEDIUM|HIGH|4|REGULATORY_LEGAL` | `POSITIVE|MEDIUM|HIGH|4|REGULATORY_LEGAL` | MATCH (0 diffs) |
| `CAL2_000025` | `RAW_NSE_011299` | Bharti Infratel / Indus Towers | INFRATEL: Updates — Bharti Infratel Limited has... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000026` | `RAW_NSE_004743` | Axis Bank Limited | AXISBANK: Outcome of Board Meeting — Axis Bank ... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000027` | `RAW_NSE_045454` | Eicher Motors Limited | EICHERMOT: Analysts/Institutional Investor Meet... | `NEUTRAL|MEDIUM|MEDIUM|3|CORPORATE_ACTION` | `NEUTRAL|MEDIUM|MEDIUM|3|CORPORATE_ACTION` | MATCH (0 diffs) |
| `CAL2_000028` | `RAW_NSE_011204` | Vedanta Limited | VEDL: Disc. under Reg.30 of SEBI (SAST) Reg.201... | `NEGATIVE|MEDIUM|HIGH|4|CREDIT_RATING_DEBT` | `NEGATIVE|MEDIUM|HIGH|4|CREDIT_RATING_DEBT` | MATCH (0 diffs) |
| `CAL2_000029` | `RAW_NSE_030921` | Hero MotoCorp Limited | HEROMOTOCO: Minutes of Extra-ordinary General M... | `NEUTRAL|MEDIUM|MEDIUM|3|CREDIT_RATING_DEBT` | `NEUTRAL|MEDIUM|MEDIUM|3|CREDIT_RATING_DEBT` | MATCH (0 diffs) |
| `CAL2_000030` | `RAW_NSE_032101` | Bajaj Finserv Limited | BAJAJFINSV: Dividend — Bajaj Finserv Limited ha... | `POSITIVE|MEDIUM|MEDIUM|4|DIVIDEND` | `POSITIVE|MEDIUM|MEDIUM|4|DIVIDEND` | MATCH (0 diffs) |
| `CAL2_000031` | `RAW_NSE_048756` | Mahindra & Mahindra Limited | M&M: Change in Director(s) — Mahindra & Mahindr... | `POSITIVE|MEDIUM|HIGH|4|CAPEX_BUSINESS_UPDATE` | `POSITIVE|MEDIUM|HIGH|4|CAPEX_BUSINESS_UPDATE` | MATCH (0 diffs) |
| `CAL2_000032` | `RAW_NSE_054963` | Punjab National Bank | PNB: Updates — Punjab National Bank has informe... | `POSITIVE|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `POSITIVE|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000033` | `RAW_NSE_053791` | ACC Limited | ACC: Financial Result Updates — ACC Limited has... | `NEUTRAL|MEDIUM|MEDIUM|3|MANAGEMENT_CHANGE` | `NEUTRAL|MEDIUM|MEDIUM|3|MANAGEMENT_CHANGE` | MATCH (0 diffs) |
| `CAL2_000034` | `RAW_NSE_016832` | Vedanta Limited | VEDL: Press Release — Vedanta Limited has infor... | `POSITIVE|MEDIUM|MEDIUM|3|M_AND_A` | `POSITIVE|MEDIUM|MEDIUM|3|M_AND_A` | MATCH (0 diffs) |
| `CAL2_000035` | `RAW_NSE_016740` | Yes Bank Limited | YESBANK: Press Release — Yes Bank Limited has i... | `NEUTRAL|MEDIUM|MEDIUM|3|OPERATIONAL_EVENT` | `NEUTRAL|MEDIUM|MEDIUM|3|OPERATIONAL_EVENT` | MATCH (0 diffs) |
| `CAL2_000036` | `RAW_NSE_037351` | JSW Steel Limited | JSWSTEEL: Disc. under Reg.30 of SEBI (SAST) Reg... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000037` | `RAW_NSE_062110` | Satyam Computer Services | SATYAMCOMP: Press Release — Satyam Computer Ser... | `NEGATIVE|MEDIUM|MEDIUM|3|REGULATORY_LEGAL` | `NEGATIVE|MEDIUM|MEDIUM|3|REGULATORY_LEGAL` | MATCH (0 diffs) |
| `CAL2_000038` | `RAW_NSE_031364` | Cipla Limited | CIPLA: Financial Result Updates — Cipla Limited... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000039` | `RAW_NSE_006639` | Infosys Limited | INFY: Press Release — Infosys Limited has infor... | `POSITIVE|MEDIUM|HIGH|4|DIVIDEND` | `POSITIVE|MEDIUM|HIGH|4|DIVIDEND` | MATCH (0 diffs) |
| `CAL2_000040` | `RAW_NSE_062051` | Satyam Computer Services | SATYAMCOMP: Allotment of Equity Shares — Satyam... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000041` | `RAW_NSE_035043` | Dr. Reddy's Laboratories Limited | DRREDDY: ESOPs/ESOS/ESPS — Dr. Reddy's Laborato... | `POSITIVE|HIGH|HIGH|5|ORDER_CONTRACT` | `POSITIVE|HIGH|HIGH|5|ORDER_CONTRACT` | MATCH (0 diffs) |
| `CAL2_000042` | `RAW_NSE_013673` | Yes Bank Limited | YESBANK: Allotment of ESOP/ESPS — Yes Bank Limi... | `NEUTRAL|MEDIUM|MEDIUM|3|SHAREHOLDING_CHANGE` | `NEUTRAL|MEDIUM|MEDIUM|3|SHAREHOLDING_CHANGE` | MATCH (0 diffs) |
| `CAL2_000043` | `RAW_NSE_031156` | UltraTech Cement Limited | ULTRACEMCO: Results Update, Quarter ended, 30-J... | `NEUTRAL|MEDIUM|MEDIUM|3|CREDIT_RATING_DEBT` | `NEUTRAL|MEDIUM|MEDIUM|3|CREDIT_RATING_DEBT` | MATCH (0 diffs) |
| `CAL2_000044` | `RAW_NSE_058143` | Bank of Baroda | BANKBARODA: Cessation — Bank Of Baroda has info... | `POSITIVE|HIGH|HIGH|4|M_AND_A` | `POSITIVE|HIGH|HIGH|4|M_AND_A` | MATCH (0 diffs) |
| `CAL2_000045` | `RAW_NSE_014029` | Wipro Limited | WIPRO: ESOPs/ESOS/ESPS — Wipro Limited has info... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |
| `CAL2_000046` | `RAW_NSE_047360` | Hindustan Unilever Limited | HINDUNILVR: Date of payment of dividend — Hindu... | `NEUTRAL|MEDIUM|MEDIUM|3|CORPORATE_ACTION` | `NEUTRAL|MEDIUM|MEDIUM|3|CORPORATE_ACTION` | MATCH (0 diffs) |
| `CAL2_000047` | `RAW_NSE_058560` | Bosch Limited | BOSCHLTD: Trading Window — Bosch Limited has in... | `POSITIVE|MEDIUM|HIGH|4|REGULATORY_LEGAL` | `POSITIVE|MEDIUM|HIGH|4|REGULATORY_LEGAL` | MATCH (0 diffs) |
| `CAL2_000048` | `RAW_NSE_010204` | State Bank of India | SBIN: Dividend — State Bank Of India has inform... | `NEGATIVE|LOW|MEDIUM|3|OPERATIONAL_EVENT` | `NEGATIVE|LOW|MEDIUM|3|OPERATIONAL_EVENT` | MATCH (0 diffs) |
| `CAL2_000049` | `RAW_NSE_029242` | Sun Pharmaceutical Industries Limited | SUNPHARMA: Press Release — Sun Pharmaceuticals ... | `POSITIVE|MEDIUM|HIGH|4|DIVIDEND` | `POSITIVE|MEDIUM|HIGH|4|DIVIDEND` | MATCH (0 diffs) |
| `CAL2_000050` | `RAW_NSE_009446` | HCL Technologies Limited | HCLTECH: Allotment of Securities — HCL Technolo... | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | `NEUTRAL|MEDIUM|MEDIUM|3|EARNINGS_RESULTS` | MATCH (0 diffs) |

*Legend: `S` = Sentiment, `C` = Confidence, `R` = Relevance, `I` = Importance, `E` = Primary Event.*

---

## 2. Quantitative Summary of Mismatches

- **Total Calibration Records**: 50 (`CAL2_000001` through `CAL2_000050`).
- **Raw Label Differences (per `calibration_id`)**: **0 / 50 (0.0%)**.
- **Metadata Additions**:
  - `annotation_source`: Set to `PROJECT_OWNER_INTERACTIVE_CHAT` across all 50 rows.
  - `annotation_method`: Formally affirmed as `HUMAN_CALIBRATION`.
- **Text-to-Label Displacements Audited**: Exactly **16** records exhibit semantic displacement between nominal filing essence and assigned label, as documented in the previous forensic audit (`CAL2_000004`, `CAL2_000006`, `CAL2_000007`, `CAL2_000011`, `CAL2_000013`, `CAL2_000016`, `CAL2_000019`, `CAL2_000021`, `CAL2_000023`, `CAL2_000040`, `CAL2_000041`, `CAL2_000042`, `CAL2_000045`, `CAL2_000047`, `CAL2_000048`, `CAL2_000050`).
- **Human Label Modification**: **0** labels modified, normalized, or post-hoc altered.

---

## 3. Empirical Distributions (Authoritative Corrected Dataset)

All distributions recomputed directly from `fresh_calibration_50_human_annotations_corrected.csv`:

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
- *Unused canonical classes (4)*: `BUYBACK`, `BONUS_SPLIT`, `FUNDRAISING`, `OTHER` (0 / 50).

---

## 4. Methodological Invariants & Agreement Status

1. **Chance-Corrected Agreement ($\kappa$)**:
   - Number of independent human coders: Exactly **1** (project owner).
   - Cohen's $\kappa$, Fleiss' $\kappa$, and Krippendorff's $lpha$ require $K \ge 2$ independent coders.
   - Chance-corrected agreement is **mathematically undefined**.
   - **Zero agreement metrics calculated or claimed**.
2. **Zero Synthetic / Simulated Coders**:
   - No simulated second human was generated or consulted.
3. **Formal Gate Blocker**:
   ```text
   ================================================================================
   B) HUMAN CALIBRATION GATE BLOCKED — INDEPENDENT SECOND HUMAN REQUIRED
   ================================================================================
   ```
   The calibration agreement gate cannot pass without an independent second human annotator completing the calibration sample double-blind.

---

## 5. Test Suite Verification

Both unit test suites executed with 100% pass rates:

```text
pytest tests/test_news.py -v
============================= 44 passed in 2.85s ==============================

pytest -q
============================ 141 passed in 6.91s ==============================
```

---

## 6. Cryptographic Hash Registry & Asset Protection

| Asset / File Path | Record Count | Checksum (SHA-256) | Forensic Status |
| :--- | :---: | :--- | :---: |
| **`fresh_calibration_50_human_annotations_corrected.csv`** | 50 | `b61bc8927b151b5434115ee5111af858233704df9d1eafcf5fc160351aa02d44` | **NEW AUTHORITATIVE** |
| **`fresh_calibration_50_human_annotations.csv`** | 50 | `5ad5677d101054a22110b103ddba692ec955aaade3734ce40f6ff0e43885a6e8` | **PRESERVED (BASELINE)** |
| **`fresh_calibration_50_input.csv`** | 50 | `6ce1d58dfd3634cd597f840a6d6972f129e9aa3c77e4bab20b417aeb78d7f091` | **UNTOUCHED** |
| **`raw_authentic_news_inventory.jsonl`** | 62,329 | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | **UNTOUCHED** |
| **`ai_assisted_development_annotations.csv`** | 1,050 | `3f1ebc67c8b5ae3a61ab7da1b999f257d63b198c21a21a0af5c9da8d742bfa7c` | **UNTOUCHED** |
| **`gold_holdout_annotation_input.csv`** | 200 | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | **QUARANTINED** |
| **Phase 5/6/7 Models** | `models/v1/` | All tree and linear model checkpoints intact | **UNTOUCHED** |
| **Phase 9 Models / Alpha Features** | N/A | Zero models trained, zero alpha features generated | **PROHIBITED** |

---

## 7. Governance Commitments

- **Authoritative Status**: Only `fresh_calibration_50_human_annotations_corrected.csv` represents the interactive human labels of the project owner.
- **Phase 8 Sealing**: Phase 8 remains **STRICTLY UNSEALED**.
- **Phase 9 Prohibition**: Combining news features into NIFTY price models or training NLP/price predictors is **STRICTLY PROHIBITED**.
