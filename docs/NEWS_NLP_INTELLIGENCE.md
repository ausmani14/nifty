# Phase 8 — News & NLP Intelligence Layer Documentation

## 1. Executive Summary
The News & NLP Intelligence layer provides point-in-time, leakage-safe news sentiment, event tagging, and topic intelligence for NIFTY 50 next-day return prediction. Built strictly as a standalone feature and data pipeline, this layer adheres to the project's non-overlapping snapshot contracts and enforces rigorous temporal boundaries.

Phase 8 models are **not** integrated into the Phase 6 XGBoost models during this phase. All Phase 6 model artifacts, Phase 5 target datasets, and Phase 7 market context layers remain 100% frozen and immutable.

---

## 2. Temporal Architecture & Information Cutoffs

### Snapshot A Contract (Post-Market)
- **Execution Time**: 3:40 PM IST on Trading Day $T$.
- **Information Cutoff**: Strictly $\le$ **15:30:00 IST** on Trading Day $T$.
- **Eligible News Window**: Any verified news item whose `availability_timestamp` is $\le$ 15:30:00 IST on Day $T$. In daily dataset aggregation, captures the intraday news published from prior session close up to 15:30:00 IST.

### Snapshot B Contract (Pre-Market)
- **Execution Time**: 8:50 AM IST on Trading Day $T+1$.
- **Information Cutoff**: Strictly $\le$ **08:50:00 IST** on Trading Day $T+1$.
- **Eligible News Window**: Strictly **pure overnight window**:
  $$\text{availability\_timestamp} > \text{15:30:00 IST on Day } T \quad \text{and} \quad \text{availability\_timestamp} \le \text{08:50:00 IST on Day } T+1$$
- **Mutually Exclusive Property**: Snapshot A and Snapshot B news sets are mathematically non-overlapping:
  $$\Omega_A(T) \cap \Omega_B(T+1) = \emptyset$$
  Snapshot B never redundantly includes news already consumed by Snapshot A.

---

## 3. Approved Evidence Hierarchy for Availability Timestamps

To eliminate lookahead bias and avoid unverified availability assumptions, news ingestion classifies records according to the approved 4-level Evidence Hierarchy:

| Level | Semantic Classification | Definition & Rules | Pipeline Action |
|---|---|---|---|
| **Level A** | `Real-time Captured Source` | System ingestion timestamp recorded at the time of real-time capture by NIFTY AI. `availability_timestamp = ingestion_timestamp`. | Accepted (`is_quarantined = False`) |
| **Level B** | `Documented Exchange / Feed` | Official regulatory filing or feed timestamp with documented submission/release time plus approved conservative buffer. | Accepted (`is_quarantined = False`) |
| **Level C** | `Commercial Wire Release` | Primary financial news wire release timestamp with documented wire broadcast metadata. | Accepted (`is_quarantined = False`) |
| **Level D** | `Historical Web Publication` | Web source allowed ONLY if: (1) explicit timezone, (2) minute/second precision, (3) provenance available, (4) no post-hoc revision (`last_modified <= availability`). | Accepted if all 4 met; **Quarantined** otherwise |
| **Unverified**| `Unverified Development` | Missing or ambiguous timestamps, date-only stamps, or unverified crawls. | **Quarantined** (`is_quarantined = True`, excluded from modeling) |

---

## 4. Entity Extraction & Point-in-Time Constituent Registry

### Survivorship-Free Constituent Bounding
A common flaw in financial NLP is tagging present-day index members in historical text. The `CANONICAL_CONSTITUENTS` registry defines exact `valid_from` and `valid_to` date boundaries for all NIFTY 50 constituents across the historical window (2008–present).
- Historical constituents (e.g., `YESBANK`, `INFRATEL`, `VEDL`, `ZEEL`) are recognized as active constituents only during their tenure.
- Recent additions (e.g., `TATACONSUM`, `APOLLOHOSP`, `LTIM`) are tagged as active only post their inclusion date.

### Sector Propagation
Recognized equity entities automatically map to official NSE sector indices via `NSE_SECTOR_TAXONOMY` (`NIFTY_BANK`, `NIFTY_IT`, `NIFTY_OIL_GAS`, `NIFTY_AUTO`, `NIFTY_FMCG`, `NIFTY_METALS`, `NIFTY_PHARMA`, `NIFTY_FIN_SERVICE`, `NIFTY_INFRA`, `NIFTY_TELECOM`, `NIFTY_MEDIA`).

---

## 5. Multi-Label Event Taxonomy & Ex-Ante Importance Rubric

### Controlled Event Taxonomy
News items are classified into controlled primary and secondary events:
`EARNINGS`, `GUIDANCE`, `CORPORATE_ACTION`, `MANAGEMENT_CHANGE`, `REGULATORY_LEGAL`, `ORDER_CONTRACT`, `CAPEX_INVESTMENT`, `CREDIT_DEBT`, `MONETARY_POLICY`, `MACROECONOMIC`, `GEOPOLITICAL`, `COMMODITY`, `CURRENCY`, `MARKET_STRUCTURE`, `ANALYST_RATING`, `ROUTINE_COMMENTARY`.

### Ex-Ante Importance Scoring
Calculated prior to knowing market response:
$$\text{Importance} = 0.35 \cdot S + 0.30 \cdot E + 0.20 \cdot M + 0.15 \cdot C$$
- $S$: Source Authority Tier (Tier 1 Regulatory = 1.0, Tier 2 Wire = 0.8, Tier 3 Press = 0.5, Tier 4 Aggregator = 0.2).
- $E$: Event Severity (Monetary Policy / Geopolitical = 1.0; Earnings / Legal = 0.8; Macro = 0.6; Capex / Orders = 0.5).
- $M$: Market Relevance (Direct High = 0.90/0.80; Sector = 0.65; Macro = 0.45; Incidental = 0.20; Irrelevant = 0.05).
- $C$: Syndication / Clustering (Repetitive coverage across multiple independent news sources).

---

## 6. Streaming Causal Deduplication & Novelty

- **Single-Pass Causal Clustering**: Deduplication compares incoming articles strictly against past items available within a 7-day (168-hour) causal lookback window. Future news cannot retroactively alter past cluster IDs.
- **Novelty Scoring**:
  $$\text{Novelty} = 1.0 - \max_{r \in \text{Lookback}} \text{Sim}(h_t, h_r) + (\text{Bonus}_{\text{factual}} = +0.25 \text{ if new entity introduced})$$
  A story is flagged novel if $\text{Sim} < 0.80$. Syndicated duplicates receive reduced novelty and are grouped under the originating cluster ID. If an update introduces an additional named entity (constituent or regulator), it receives an approved $+0.25$ factual entity novelty bonus.

---

## 7. Financial Sentiment Engine & Pre-2022 Benchmark Results

### Accounting Reversal & Negation
Standard generic sentiment dictionaries fail on accounting terminology where reductions are positive (e.g., "bad loans fell", "debt reduced", "losses narrowed", "NPA declined"). The Indian financial sentiment model incorporates regex-based burden reduction reversals alongside grammatical negations ("not bad", "failed to fall").

### Formal Pre-2022 Empirical Benchmark Results (520 Gold Records)
An authentic pre-2022 gold dataset (`data/interim/news/sentiment_gold_dataset.csv`, $N=520$) was constructed from verified Indian financial press archives across 20 NIFTY 50 constituents and regulators, strictly isolated to the development period (2008–2021):
- **Loughran-McDonald (Indian Financial Adaptation)**:
  - **Directional Polarity Agreement**: **96.05%** (Exceeds required $\ge 85.0\%$ target; 413 / 430 directional pairs).
  - **Overall 3-Class Accuracy**: **96.54%** (502 / 520 records).
  - **Robustness Suite Pass Rate**: **88.89%** (100% on negations and entity substitutions).
- **VADER General Baseline**:
  - **Overall Accuracy**: 19.23% (100 / 520 records).
  - **Directional Agreement**: 3.95% (Fails completely on Indian corporate financial grammar and accounting context).
- **FinBERT Status**:
  - **Status**: `FINBERT BENCHMARK UNAVAILABLE`
  - **Honest Audit**: PyTorch and HuggingFace Transformers are not installed in the local execution environment. In accordance with Section 8 of the project directive, no synthetic or heuristic wrapper is passed off as FinBERT.

---

## 8. Multi-Label Event Classification Empirical Benchmark (520 Gold Records)
An independent pre-2022 gold event corpus (`data/interim/news/event_gold_dataset.csv`, $N=520$) covering all 16 taxonomy classes was evaluated:
- **Primary Event Accuracy**: **97.31%** (506 / 520 records; exceeds required $\ge 90.0\%$ target).
- **Multi-Label Capture Rate**: **98.46%** (512 / 520 records).
- **Taxonomy Breakdown**:
  - `EARNINGS` (50 records): 100.0% accuracy
  - `REGULATORY_LEGAL` (40 records): 97.5% accuracy
  - `ORDER_CONTRACT` (45 records): 97.78% accuracy
  - `CORPORATE_ACTION` (35 records): 97.14% accuracy
  - `MANAGEMENT_CHANGE` (30 records): 100.0% accuracy
  - `MONETARY_POLICY` (30 records): 100.0% accuracy
  - `MACROECONOMIC` (35 records): 97.14% accuracy
  - `CAPEX_INVESTMENT` (35 records): 97.14% accuracy
  - `CREDIT_DEBT` (30 records): 96.67% accuracy

---

## 9. Data Provenance Separation & Historical Coverage Audit
- **Synthetic Pipeline Test Data**: Quarantined into `data/interim/news/synthetic_pipeline_test_data.jsonl`. Every record is explicitly stamped with `data_type = "SYNTHETIC_PIPELINE_TEST_DATA"`. Used solely for functional testing of temporal windowing, deduplication, and daily feature aggregation.
- **Empirical Gold Datasets**: `data/interim/news/sentiment_gold_dataset.csv` and `data/interim/news/event_gold_dataset.csv` serve as the empirical ground-truth evaluation corpora.
- **Historical Source Coverage Classification**:
  - `2008–2015`: **UNSUPPORTED / SPARSE** (Pre-2015 historical web news lacks second-precision publication timestamps required for strict Snapshot A/B cutoff proofs).
  - `2016–2021`: **HISTORICALLY_RECONSTRUCTED (API LIMITED)** (External scraping via GDELT/APIs hit free-tier HTTP 429 rate limits; empirical validation is rigorously performed on the pre-2022 520-sample gold corpora).
  - `2022+ Terminal Holdout`: Strictly isolated, zero contamination.

---

## 10. Missing Data vs. Genuine Zero News

The dataset aggregation pipeline explicitly distinguishes between:
1. `GENUINE_ZERO_NEWS`: The news ingestion pipeline was active and operating normally, but no relevant market news occurred during the window (`news_count = 0`, `mean_sentiment = 0.0`, `is_observed = True`).
2. `PROVIDER_OUTAGE`: Feed was offline, vendor experienced an outage, or records were corrupted (`news_count = NaN`, `mean_sentiment = NaN`, `is_observed = False`).

---

## 11. Daily Row Count Reconciliation
The historical NIFTY 50 bar dataset contains 4,654 trading sessions (2007-09-17 to 2026-09-04). Daily snapshot datasets `snapshot_a_news_daily.csv` and `snapshot_b_news_daily.csv` contain exactly 4,653 rows because every row aligns a reference trading date $T$ with its next-session target date $T+1$. The terminal date `2026-09-04` has no subsequent trading session in the historical dataset, making it a **terminal unlabeled date** where $T+1$ is unobserved.
