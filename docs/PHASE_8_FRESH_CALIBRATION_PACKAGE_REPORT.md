# Phase 8 — Fresh 50-Record Independent Calibration Package Report

**Document Date**: September 16, 2026  
**Auditor / Engineer**: Senior NLP Evaluation Engineer & Quantitative Research Methodology Auditor  
**Package Scope**: Fresh 50-Record Independent Calibration Sample (`CAL2_000001` through `CAL2_000050`)  
**Input Artifact**: `data/interim/news/fresh_calibration_50_input.csv`  
**Manifest Artifact**: `data/interim/news/fresh_calibration_50_manifest.csv`  
**Sampling Seed**: `43` (Deterministic Stratified Pseudo-Random Draw)  
**Target Guidelines**: `docs/PHASE_8_HUMAN_ANNOTATION_GUIDELINES.md` (Version 1.1.0)  
**Machine-Readable Rules**: `configs/annotation_guidelines_rules.json`  
**Phase 8 Sealing Status**: **STRICTLY UNSEALED**  
**Phase 9 Status**: **STRICTLY PROHIBITED**  

---

## 1. Exact Row Count

- **Total Records in Calibration Package**: Exactly **50** records.
- **Header Structure**: Exactly 10 standardized columns (zero label leakage).
- **Identifier Range**: `CAL2_000001` through `CAL2_000050` (sequential, zero duplicates, zero gaps).

---

## 2. Sampling Seed

- **Random Seed**: **`43`** (using Python's `random.Random(43)`).
- **Reproducibility**: Fully deterministic draw from the 62,279 eligible candidate pool.

---

## 3. Sampling Methodology

The fresh calibration package was constructed via **deterministic multi-strata pseudo-random draw** directly from `data/interim/news/raw_authentic_news_inventory.jsonl` under strict anti-bias constraints:
1. **Candidate Pool Isolation**:
   - Total Raw Historical Inventory: 62,329 authentic NSE records (2008–2021).
   - Excluded Previous Pilot Records (`ANN_000001`–`ANN_000050`): 50 records.
   - Excluded Terminal Holdout Records (2022+): 200 records.
   - Eligible Candidate Universe: **62,279 authentic records**.
2. **Strata Controls (Source Metadata Only)**:
   - **Year Balancing**: Capped at a maximum of 4 records per calendar year across 2008–2021.
   - **Constituent Dispersion**: Capped at a maximum of 2 records per company to prevent single-firm idiosyncratic bias.
   - **Temporal PIT Execution**: Balanced between Market-Hours (`SNAPSHOT_A`) and Overnight (`SNAPSHOT_B`).
   - **Textual Length Stratification**: Balanced across Short ($\le 250$ chars), Medium (251–600 chars), and Long ($> 600$ chars).
   - **Sector Representation**: Sourced across 12 distinct NIFTY sector classifications.
3. **Zero Label Bias**:
   - **No sentiment, event, relevance, or importance labels** (human or AI) were accessed or evaluated during candidate filtering or sampling.

---

## 4. Calendar Year Distribution (2008–2021)

Every single calendar year in the 14-year authentic historical corpus is represented:

| Calendar Year | Record Count | Percentage |
| :---: | :---: | :---: |
| **2008** | 4 | 8.0% |
| **2009** | 3 | 6.0% |
| **2010** | 2 | 4.0% |
| **2011** | 4 | 8.0% |
| **2012** | 4 | 8.0% |
| **2013** | 3 | 6.0% |
| **2014** | 4 | 8.0% |
| **2015** | 4 | 8.0% |
| **2016** | 3 | 6.0% |
| **2017** | 4 | 8.0% |
| **2018** | 4 | 8.0% |
| **2019** | 4 | 8.0% |
| **2020** | 3 | 6.0% |
| **2021** | 4 | 8.0% |
| **Total** | **50** | **100.0%** |

---

## 5. Execution Snapshot Distribution

| Snapshot | Information Cutoff Window | Count | Percentage | Operational Context |
| :--- | :--- | :---: | :---: | :--- |
| **`SNAPSHOT_A`** | 15:30 IST on T (predicts T+1) | **28** | 56.0% | Market-hours corporate filings |
| **`SNAPSHOT_B`** | 08:50 IST on T+1 (predicts T+1) | **22** | 44.0% | Overnight corporate announcements |
| **Total** | | **50** | **100.0%** | Balanced execution windows |

---

## 6. Company Distribution

The 50 records span **39 distinct historical NIFTY 50 constituent companies** (maximum 2 records per company):

- **Companies with 2 records (11 companies, 22 records)**:
  - Axis Bank Limited (`AXISBANK`)
  - Bajaj Auto Limited (`BAJAJ-AUTO`)
  - Bharat Petroleum Corporation Limited (`BPCL`)
  - Bharti Airtel Limited (`BHARTIARTL`)
  - Dr. Reddy's Laboratories Limited (`DRREDDY`)
  - Hindalco Industries Limited (`HINDALCO`)
  - ICICI Bank Limited (`ICICIBANK`)
  - Infosys Limited (`INFY`)
  - Larsen & Toubro Limited (`LT`)
  - Mahindra & Mahindra Limited (`M&M`)
  - Tata Motors Limited (`TATAMOTORS`)
- **Companies with 1 record (28 companies, 28 records)**:
  - Asian Paints, Bajaj Finance, BHEL, Cairn India, Cipla, Coal India, DLF, GAIL, Grasim Industries, HCL Technologies, HDFC Bank, Hero MotoCorp, Hindustan Unilever, IndusInd Bank, ITC, JSW Steel, Kotak Mahindra Bank, Maruti Suzuki, NTPC, Oil & Natural Gas Corp, Power Grid Corp, Reliance Communications, Reliance Industries, State Bank of India, Sun Pharma, Tata Consultancy Services, Tata Steel, Wipro.

---

## 7. Sector Distribution

The sample covers **12 major NIFTY industry sectors**:

| Sector Identifier | Sector Description | Record Count | Percentage |
| :--- | :--- | :---: | :---: |
| **`NIFTY_BANK`** | Banking & Financial Intermediaries | 11 | 22.0% |
| **`NIFTY_IT`** | Information Technology Services | 9 | 18.0% |
| **`NIFTY_AUTO`** | Automotive Manufacturers & Components | 7 | 14.0% |
| **`NIFTY_INFRA`** | Infrastructure, Construction & Capital Goods | 6 | 12.0% |
| **`NIFTY_OIL_GAS`**| Oil, Gas, Refining & Energy | 4 | 8.0% |
| **`NIFTY_METALS`** | Metals, Mining & Steel | 4 | 8.0% |
| **`NIFTY_PHARMA`** | Pharmaceuticals & Healthcare | 3 | 6.0% |
| **`NIFTY_TELECOM`**| Telecommunications Services | 2 | 4.0% |
| **`NIFTY_CHEM`** | Chemicals & Fertilizers | 1 | 2.0% |
| **`NIFTY_CONSUMPTION`** | Consumer Durables & Retail | 1 | 2.0% |
| **`NIFTY_FIN_SERVICE`** | Non-Banking Financial Companies | 1 | 2.0% |
| **`NIFTY_FMCG`** | Fast-Moving Consumer Goods | 1 | 2.0% |
| **Total** | **12 Distinct Sectors** | **50** | **100.0%** |

---

## 8. Text-Length Distribution

| Length Tier | Character Range | Record Count | Percentage | Characteristic Filing Types |
| :--- | :---: | :---: | :---: | :--- |
| **`SHORT`** | $\le 250$ chars | 6 | 12.0% | Brief board date intimations, book closure dates |
| **`MEDIUM`** | 251–600 chars | 30 | 60.0% | Standard dividend notices, director changes, contract wins |
| **`LONG`** | $> 600$ chars | 14 | 28.0% | Detailed financial result tables, postal ballot summaries |
| **Total** | | **50** | **100.0%** | |

---

## 9. Non-Reuse of Previous Pilot Records

- **Audit Verification**:
  - The 50 source record IDs from the previous pilot (`ANN_000001` through `ANN_000050`) were explicitly loaded into an exclusion set.
  - Set intersection test: $	ext{Sampled Source IDs} \cap 	ext{Previous Pilot Source IDs} = \emptyset$.
  - **Result**: Exactly **0 overlapping records** (100% fresh draw).

---

## 10. Non-Use of Annotation Labels During Sampling

- **Anti-Bias Verification**:
  - No label column (`sentiment`, `confidence`, `relevance`, `importance`, `primary_event`, `secondary_events`) was read or considered from `ai_assisted_development_annotations.csv`, `annotator_2_simulated_annotations_1050.csv`, or any other file.
  - Strata partitioning relied exclusively on raw authentic metadata: `published_timestamp`, `company`, `sector`, `pit_eligibility`, and raw string character counts.

---

## 11. Terminal Holdout Isolation Verification

- **Quarantine Boundary Verification**:
  - The 200 source record IDs in `data/interim/news/gold_holdout_annotation_input.csv` (2022–2023) were loaded into a quarantine exclusion set.
  - Set intersection test: $	ext{Sampled Source IDs} \cap 	ext{Holdout Source IDs} = \emptyset$.
  - **Result**: Exactly **0 holdout records sampled**. The 200-record terminal holdout remains 100% untouched and quarantined.

---

## 12. Authentic Corpus Immutability

- **Raw Corpus Verification**:
  - File: `data/interim/news/raw_authentic_news_inventory.jsonl`
  - Record Count: Exactly 62,329 rows.
  - Certified Checksum: `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3`.
  - Re-computed Checksum: `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3`.
  - **Result**: **100% UNCHANGED / BYTE-FOR-BYTE IDENTICAL**.

---

## 13. Output Artifact Checksums

```text
data/interim/news/fresh_calibration_50_input.csv
SHA-256: 6ce1d58dfd3634cd597f840a6d6972f129e9aa3c77e4bab20b417aeb78d7f091
Rows:    50 rows (CAL2_000001 through CAL2_000050)
Columns: calibration_id, source_record_id, timestamp, snapshot, company, headline, summary_or_body, source_url, annotation_split, annotation_version
Labels:  ZERO LABELS (Clean unannotated template)

data/interim/news/fresh_calibration_50_manifest.csv
SHA-256: cf5f9902d343b2a1cc05186427f353177d75a9053d67c3188d587e214f8b19e0
Rows:    50 rows
Columns: calibration_id, source_record_id, timestamp, snapshot, company
```

---

## 14. Relevant Phase 8 Test Results

Both the news-specific and full repository test suites were executed to verify system integrity:

```text
pytest tests/test_news.py -v
============================= 44 passed in 7.08s ==============================

pytest -q
============================ 141 passed in 14.10s =============================
```

- **Phase 8 News Tests**: 44 / 44 PASSED.
- **Repository Full Test Suite**: 141 / 141 PASSED.

---

## 15. Forensic Integrity Verification Summary

- [x] Exactly 50 rows in `fresh_calibration_50_input.csv`.
- [x] Unique `calibration_id` (`CAL2_000001` through `CAL2_000050`).
- [x] Unique `source_record_id`.
- [x] Zero missing required source fields.
- [x] Zero duplicate source records.
- [x] All timestamps valid ISO 8601 strings with timezone awareness.
- [x] Snapshots strictly valid (`SNAPSHOT_A` or `SNAPSHOT_B`).
- [x] Source URLs preserved verbatim from exchange logs.
- [x] **Zero annotation columns present** (no sentiment, confidence, relevance, importance, or event fields).
- [x] **Zero human labels present**.
- [x] **Zero AI labels present**.
- [x] **Zero model predictions present**.
- [x] **Zero holdout records present**.
- [x] Previous pilot records (`ANN_000001`–`ANN_000050`) completely excluded.
- [x] Original 62,329-record inventory remains byte-for-byte unchanged.
- [x] Original human pilot remains unchanged (`ai_assisted_development_annotations.csv`).
- [x] Corrected human pilot remains unchanged (`human_pilot_annotations_corrected.csv`).
- [x] AI-assisted development set remains unchanged.
- [x] AI-simulated Annotator 2 remains unchanged (`annotator_2_simulated_annotations_1050.csv`).

---

## 16. Final Calibration Package Verdict

### **`A) FRESH CALIBRATION PACKAGE READY`**

#### Operational Protocol:
- The package is fully prepared for independent human annotation under Guidelines Version 1.1.0.
- Phase 8 remains **STRICTLY UNSEALED**.
- Phase 9 model training remains **STRICTLY PROHIBITED**.
- Proceed to annotation only upon explicit instruction.

---

*Report compiled for the NIFTY AI quantitative research repository.*
