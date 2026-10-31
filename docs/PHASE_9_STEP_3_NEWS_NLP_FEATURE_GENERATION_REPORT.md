# Phase 9 — Step 3: Point-in-Time News NLP Feature Generation Report

**Document Date**: September 17, 2026  
**Auditor / ML Systems Lead**: Senior ML/Quant Software Engineer & Data Provenance Auditor  
**Governing Phase**: Phase 9 — Point-in-Time News NLP Feature Engineering & Model 2 Preparation  
**Status**: APPROVED & CRYPTOGRAPHICALLY LOCKED  
**Final Verdict**: **A) NEWS NLP FEATURES READY FOR INCREMENTAL PREDICTIVE-VALUE EXPERIMENT**

---

## 1. Objective

The primary objective of Phase 9 Step 3 was to generate deterministic, strictly Point-in-Time (PIT) daily news/NLP feature datasets for NIFTY 50 **Snapshot A** and **Snapshot B** across both the Development Window (`2008-07-08` through `2021-12-31`) and Terminal Out-of-Sample (OOS) Window (`2022-01-01` through `2026-09-04`).

The feature generation pipeline enforces:
1. Complete elimination of lookahead bias via second-level exchange dissemination cutoffs.
2. Anti-survivorship bias filtering via the Phase 9 Step 2D reconciled historical constituent registry.
3. Causal streaming deduplication and novelty tracking (strictly 7-day lookback).
4. Deterministic financial sentiment analysis (Loughran-McDonald adaptation for Indian corporate disclosures).
5. Canonical 18-category event classification.
6. Dynamic ex-ante importance and market relevance weighting without future price dependency.
7. Total isolation of the 200-record gold benchmark holdout.
8. Zero NaN / zero infinity guarantees across all 4,653 trading sessions.

---

## 2. Source Artifacts & Cryptographic Provenance

All underlying news records originate strictly from official National Stock Exchange of India (NSE) corporate announcements. Cryptographic integrity of inputs was verified prior to pipeline execution:

| Artifact | Temporal Span | Total Records | SHA-256 Checksum | Integrity Status |
| :--- | :---: | :---: | :--- | :---: |
| `data/interim/news/raw_authentic_news_inventory.jsonl` | 2008–2021 | 62,329 | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | **PASS (UNTOUCHED)** |
| `data/interim/news/raw_authentic_news_terminal_2022_2026_step2e.jsonl` | 2022–2026 | 41,371 | `5d5daf5ed7c844e86d45dc6a893f03b1d4f523183e29200d94b592329136f6fd` | **PASS (UNTOUCHED)** |
| `data/interim/news/gold_holdout_annotation_input.csv` | Protected Holdout | 200 | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | **PASS (ISOLATED)** |
| `data/processed/nifty_50_daily.csv` | Master Calendar | 4,654 | `88c67ce7a1f58b87ce38fcfe3a8264560ea3d085957d605c3d9a71a06900f983` | **MASTER INDEX** |

> **Total Ingested Raw Announcements**: **103,700 records** (62,329 historical + 41,371 terminal).  
> **Old 18,203-record Step 2 artifact** (`data/interim/news/raw_authentic_news_holdout_2022_2026.jsonl`): Quarantined and excluded.

---

## 3. Point-in-Time (PIT) Methodology & Execution Cutoffs

The pipeline relies on the validated `assign_record_pit()` calendar partition grounded in the official trading calendar:

$$\Omega_A(T) = \{ r \mid \text{availability}(r) \in (T-1\text{ 15:30:00 IST}, T\text{ 15:30:00 IST}] \}$$

$$\Omega_B(T) = \{ r \mid \text{availability}(r) \in (T\text{ 15:30:00 IST}, T+1\text{ 08:50:00 IST}] \}$$

### Invariants Enforced:
1. **Intraday Boundary (Snapshot A)**: Information cutoff is strictly `15:30:00.000 IST` on Session $T$. Disclosures published during trading hours ($08:50:00 < t \le 15:30:00$) are mapped to $A(T)$ predicting $T \to T+1$.
2. **Pure Overnight Boundary (Snapshot B)**: Lower bound strictly $> 15:30:00.000\text{ IST}$ on Session $T$; upper bound strictly $\le 08:50:00.000\text{ IST}$ on Session $T+1$. Captures post-close evening disclosures, midnight transitions, non-trading weekends/holidays, and early morning releases prior to the $09:00\text{ IST}$ pre-market open.
3. **Disjointness**: $\Omega_A(T) \cap \Omega_B(T) = \emptyset$ is mathematically guaranteed. Zero records are double-counted.
4. **Terminal Session Bound**: The 12 disclosures published on the final trading session (`2026-09-04`) after $08:50:00\text{ IST}$ are cleanly marked `TERMINAL_DATE` because no subsequent trading day ($T+1$) exists in the historical price series.

---

## 4. NLP Preprocessing Methodology

All 103,700 records were processed through deterministic, reproducible offline NLP transformations:
- **Text Normalization**: Headlines and summaries stripped of excessive whitespace, boilerplate exchange headers, and HTML tags while preserving financial punctuation and corporate acronyms.
- **Entity Resolution**: Point-in-time constituent ticker resolution mapping company names and trade aliases to canonical NIFTY symbols (including handling of DVR shares `TATAMTRDVR` $\to$ `TATAMOTORS`).
- **Reproducibility**: Identical text processed multiple times produces identical tokens, classifications, and scores. Zero stochastic LLM inference was permitted during feature generation.

---

## 5. Sentiment Methodology

Sentiment is evaluated at the individual article level prior to daily snapshot aggregation:
- **Engine**: `LoughranMcDonaldIndianSentiment`.
- **Lexicon**: The Loughran-McDonald financial sentiment dictionary adapted for Indian corporate English, accounting terminology, and disclosure semantics.
- **Negation Grammar**: Enforces multi-word accounting reversal patterns (e.g., *"not fail to declare"*, *"no adverse findings"*, *"decline in net losses"*).
- **Polarity Scale**: Continuous score in $[-1.0, +1.0]$:
  $$\text{polarity} = \frac{N_{\text{pos}} - N_{\text{neg}}}{N_{\text{pos}} + N_{\text{neg}} + 1}$$
- **Classification**:
  - Positive: $\text{polarity} > +0.05$
  - Negative: $\text{polarity} < -0.05$
  - Neutral: $-0.05 \le \text{polarity} \le +0.05$

---

## 6. Event Taxonomy Methodology

Classifies corporate disclosures into the canonical 18-category Phase 8 taxonomy:
1. `EARNINGS_RESULTS`
2. `DIVIDEND`
3. `BONUS_SPLIT`
4. `RIGHTS_ISSUE`
5. `BUYBACK`
6. `M_AND_A`
7. `CAPEX_BUSINESS_UPDATE`
8. `FINANCIAL_IRREGULARITY`
9. `SHAREHOLDING_CHANGE`
10. `OPERATIONAL_EVENT`
11. `STRATEGIC_PARTNERSHIP`
12. `CREDIT_RATING_DEBT`
13. `FUNDRAISING`
14. `REGULATORY_LEGAL`
15. `CORPORATE_ACTION`
16. `MANAGEMENT_CHANGE`
17. `ORDER_CONTRACT`
18. `OTHER`

Every announcement receives a primary event classification, secondary event tags where applicable, and a classification confidence score.

---

## 7. Importance Rubric Methodology

Implements the corrected Phase 8 ex-ante economic importance rubric:

$$\text{importance} = 0.35 \cdot S + 0.30 \cdot E + 0.20 \cdot M + 0.15 \cdot C$$

Where:
- **$S$ (Source Authority)**: Official NSE exchange regulatory filing = $1.0$.
- **$E$ (Event Severity)**: Dynamic component derived from the classified canonical event (e.g., Earnings / M&A = $0.90$, Dividend / Buyback = $0.75$, Capex = $0.65$, Routine commentary = $0.20$).
- **$M$ (Market Scope / Relevance)**: High direct constituent = $0.90$, sector impact = $0.65$, macro = $0.45$, incidental = $0.20$.
- **$C$ (Persistence / Syndication)**: Filing syndication and persistence proxy = $0.20$.

The previous hardcoding defect identified in Phase 9 Stage 4A (which locked $E = 0.20$) is completely absent. High-importance disclosures ($\text{importance} \ge 0.70$) are legitimately populated across earnings and material catalyst periods.

---

## 8. Novelty & Deduplication Methodology

Implemented via `StreamingDeduplicator`:
- **Lookback Window**: Exactly $168\text{ hours}$ ($7\text{ days}$) trailing causal history.
- **Deduplication Threshold**: Jaccard similarity $\ge 0.80$ on word $k$-shingles.
- **Entity Bonus**: $+0.25$ bonus awarded if a follow-up announcement introduces a new factual entity into an ongoing story cluster.
- **Causal Guarantee**: When evaluating record $r_i$ at time $t_i$, only records published at $t \le t_i$ are present in memory. Later articles never alter past cluster IDs or novelty scores.

---

## 9. Time-Decay Weighting

Information relevance decays exponentially relative to the snapshot execution cutoff $T_{\text{cutoff}}$:

$$w_i = 2^{-\frac{\Delta t_i}{24.0\text{ hours}}}$$

- Disclosures arriving at the exact cutoff timestamp ($\Delta t = 0$) receive full weight $w_i = 1.0$.
- Disclosures arriving 24 hours prior to cutoff receive weight $w_i = 0.50$.
- Disclosures arriving 48 hours prior receive weight $w_i = 0.25$.

---

## 10. Complete Daily Feature Catalogue (65 Columns)

For each trading session $T$ across Snapshot A and Snapshot B, the following 65 compact, interpretable features are computed:

### A. Metadata & Status Flags (7 columns)
- `trading_date`, `target_date`, `snapshot_type`, `cutoff_timestamp`
- `data_status`: `healthy_observed` vs `genuine_zero_news`
- `news_observed`: boolean flag indicating whether qualifying news was observed
- `has_news_flag`: binary indicator ($1$ if `news_count > 0`, else $0$)

### B. Volume & Breadth Features (9 columns)
- `news_count` / `news_volume_total`: total number of qualifying active constituent announcements
- `high_relevance_count`: count of disclosures with high market relevance
- `high_importance_count` / `news_volume_high_importance`: count of disclosures with importance $\ge 0.70$
- `unique_company_count` / `num_distinct_companies`: distinct active constituent companies filing in window
- `unique_event_type_count` / `num_distinct_event_types`: distinct primary event types observed in window

### C. Sentiment Features (12 columns)
- `mean_sentiment` / `mean_sentiment_polarity`: arithmetic average of article sentiment polarities
- `weighted_sentiment` / `importance_weighted_sentiment`: decay- and importance-weighted sentiment
- `novelty_weighted_sentiment`: decay-, importance-, and novelty-weighted sentiment
- `sentiment_dispersion`: sample standard deviation of sentiment polarities ($0.0$ on zero/single news)
- `positive_count`, `negative_count`, `neutral_count`: count of positive, negative, and neutral disclosures
- `positive_ratio`, `negative_ratio`: fraction of positive and negative disclosures
- `sentiment_balance`: normalized sentiment score $\frac{N_{\text{pos}} - N_{\text{neg}}}{N_{\text{pos}} + N_{\text{neg}} + 1}$

### D. Importance Features (5 columns)
- `mean_importance`: arithmetic average of ex-ante importance scores
- `max_importance` / `max_importance_score`: maximum importance score in window
- `weighted_importance`: decay-weighted average importance score
- `high_importance_ratio`: fraction of disclosures with importance $\ge 0.70$

### E. Canonical Event Counts (21 columns)
- `event_earnings_results_count`, `event_dividend_count`, `event_bonus_split_count`, `event_rights_issue_count`, `event_buyback_count`, `event_m_and_a_count`, `event_capex_business_update_count`, `event_financial_irregularity_count`, `event_shareholding_change_count`, `event_operational_event_count`, `event_strategic_partnership_count`, `event_credit_rating_debt_count`, `event_fundraising_count`, `event_regulatory_legal_count`, `event_corporate_action_count`, `event_management_change_count`, `event_order_contract_count`, `event_other_count`
- Legacy compatibility counts: `earnings_event_count`, `macro_event_count`, `monetary_event_count`

### F. Novelty Features (3 columns)
- `mean_novelty`: arithmetic average of article novelty scores
- `weighted_novelty`: decay- and importance-weighted novelty score
- `novel_news_count`: count of novel disclosures ($\text{is\_novel} = \text{True}$ or score $\ge 0.80$)

### G. Concentration & Diversity Features (4 columns)
- `top_company_share`: maximum fraction of disclosures originating from a single company
- `top_event_share`: maximum fraction of disclosures originating from a single event category
- `company_entropy`: normalized Shannon entropy across company disclosures
- `event_entropy`: normalized Shannon entropy across event categories

### H. Company-Level Aggregates to NIFTY Level (4 columns)
- `company_news_count_mean`: average number of filings per active reporting company
- `company_weighted_sentiment_mean`: mean of company-level weighted sentiments
- `company_weighted_importance_mean`: mean of company-level weighted importances
- `company_novelty_mean`: mean of company-level average novelties

---

## 11. Snapshot A Coverage Audit

Snapshot A captures disclosures during market hours up to `15:30:00 IST` on Session $T$:

| Metric | Development Period (2008–2021) | Terminal Holdout (2022–2026) | Full Dataset (2007–2026) |
| :--- | :---: | :---: | :---: |
| **Total Trading Sessions** | 3,499 | 1,154 | 4,653 |
| **Sessions with Authentic News** | 3,257 (**93.08%**) | 1,153 (**99.91%**) | 4,410 (**94.78%**) |
| **Zero-News Sessions** | 242 (6.92%) | 1 (0.09%) | 243 (5.22%) |
| **Total Qualifying Records** | 18,553 | 11,069 | **29,622** |
| **Average Filings per Active Day** | 5.70 | 9.60 | 6.72 |
| **Missing / NaN Values** | **0 (0.00%)** | **0 (0.00%)** | **0 (0.00%)** |

---

## 12. Snapshot B Coverage Audit

Snapshot B captures post-market disclosures ($> 15:30:00\text{ IST}$ Day $T$) through pre-open ($08:50:00\text{ IST}$ Day $T+1$):

| Metric | Development Period (2008–2021) | Terminal Holdout (2022–2026) | Full Dataset (2007–2026) |
| :--- | :---: | :---: | :---: |
| **Total Trading Sessions** | 3,499 | 1,154 | 4,653 |
| **Sessions with Authentic News** | 3,266 (**93.34%**) | 1,154 (**100.00%**) | 4,420 (**95.00%**) |
| **Zero-News Sessions** | 233 (6.66%) | 0 (0.00%) | 233 (5.00%) |
| **Total Qualifying Records** | 30,237 | 30,270 | **60,507** |
| **Average Filings per Active Day** | 9.26 | 26.23 | 13.69 |
| **Missing / NaN Values** | **0 (0.00%)** | **0 (0.00%)** | **0 (0.00%)** |

---

## 13. Terminal Out-of-Sample Coverage Audit (2022–2026)

Across the entire 1,154-trading-day terminal holdout period:
- **Snapshot A Coverage**: **99.91%** (1,153 / 1,154 sessions).
- **Snapshot B Coverage**: **100.00%** (1,154 / 1,154 sessions).
- **Total Active Terminal Disclosures**: **41,339 records** (11,069 in Snapshot A + 30,270 in Snapshot B).
- **Unassigned Records**: Exactly 12 records published on the final trading day `2026-09-04` after $08:50\text{ IST}$ (cleanly bounded by terminal horizon).

---

## 14. LTIM Limitation Audit

- **Tenure**: LTIMindtree Limited (`LTIM`) was an active member of NIFTY 50 from `2023-07-13` through `2024-09-30`.
- **Endpoint Reality**: The official NSE Corporate Announcements web endpoint returned 0 announcements for `LTIM` across 2022–2026.
- **Handling**: In strict adherence to scientific data-integrity principles, **no synthetic records were backfilled or fabricated**. During the active tenure of LTIM, the pipeline gracefully processes 0 records without throwing exceptions or generating NaNs.
- **Verification**: Dedicated test `test_14_ltim_zero_record_handling` verifies that zero-filing constituents do not corrupt index-level calculations.

---

## 15. Leakage & Lookahead Audit

An exhaustive forensic leakage audit verified:
1. **Timestamp Bounds**:
   - For all $r \in \Omega_A(T)$: $\text{timestamp}(r) \le T\text{ 15:30:00 IST}$ (**0 violations**).
   - For all $r \in \Omega_B(T)$: $\text{timestamp}(r) > T\text{ 15:30:00 IST}$ and $\le T+1\text{ 08:50:00 IST}$ (**0 violations**).
2. **Membership Invariant**: A company's disclosures contribute to Session $T$ features if and only if $\text{is\_active\_nifty\_constituent}(\text{symbol}, T) = \text{True}$. Exactly 13,559 historical pre-entry or post-exit filings were filtered out, eliminating survivorship bias.
3. **Future Mutation Invariance**: Deduplication and novelty clusters are formed strictly chronologically. Truncating future records produces byte-for-byte identical historical feature values.

---

## 16. Holdout Protection & Isolation Audit

The 200-record gold benchmark:
`data/interim/news/gold_holdout_annotation_input.csv`

Remains **100% byte-for-byte untouched**:
- Pre-execution SHA-256: `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199`
- Post-execution SHA-256: `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199`
- Human labels from the gold holdout were **never inspected, imported, or used** for any threshold tuning, lexicon calibration, or event classification.

---

## 17. Determinism Audit

- Deterministic chronological sorting by `(published_timestamp, article_id)`.
- Rerunning the entire feature generation pipeline twice produces identical outputs.
- Bitwise identical checksums are produced on repeated execution.

---

## 18. Feature Distributions Across 4,653 Trading Days

### Snapshot A Feature Summary ($N = 4,653$ Sessions)

| Feature Name | Mean | Std Dev | Min | 50% (Median) | Max |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `news_count` | 6.37 | 4.52 | 0.00 | 6.00 | 29.00 |
| `unique_company_count` | 5.03 | 3.24 | 0.00 | 5.00 | 18.00 |
| `mean_sentiment` | +0.1058 | 0.2722 | -1.0000 | 0.0000 | +1.0000 |
| `weighted_sentiment` | +0.1026 | 0.2840 | -1.0000 | 0.0000 | +1.0000 |
| `sentiment_dispersion` | 0.2973 | 0.2366 | 0.0000 | 0.3780 | 1.0000 |
| `mean_importance` | 0.6595 | 0.1622 | 0.0000 | 0.6920 | 0.8000 |
| `max_importance` | 0.7334 | 0.1828 | 0.0000 | 0.8000 | 0.8000 |
| `mean_novelty` | 0.4200 | 0.1523 | 0.0000 | 0.4269 | 0.8478 |
| `weighted_novelty` | 0.4185 | 0.1528 | 0.0000 | 0.4237 | 0.8478 |
| `top_company_share` | 0.3581 | 0.2505 | 0.0000 | 0.2857 | 1.0000 |
| `company_entropy` | 0.8325 | 0.3350 | 0.0000 | 0.9755 | 1.0000 |
| `event_entropy` | 0.6562 | 0.3698 | 0.0000 | 0.8129 | 1.0000 |

### Snapshot B Feature Summary ($N = 4,653$ Sessions)

| Feature Name | Mean | Std Dev | Min | 50% (Median) | Max |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `news_count` | 13.00 | 12.32 | 0.00 | 10.00 | 92.00 |
| `unique_company_count` | 8.79 | 6.99 | 0.00 | 7.00 | 41.00 |
| `mean_sentiment` | +0.0687 | 0.2511 | -1.0000 | 0.0000 | +1.0000 |
| `weighted_sentiment` | +0.0722 | 0.2646 | -1.0000 | 0.0000 | +1.0000 |
| `sentiment_dispersion` | 0.3152 | 0.2267 | 0.0000 | 0.3888 | 1.0000 |
| `mean_importance` | 0.6678 | 0.1600 | 0.0000 | 0.7018 | 0.8000 |
| `max_importance` | 0.7435 | 0.1786 | 0.0000 | 0.8000 | 0.8000 |
| `mean_novelty` | 0.4128 | 0.1561 | 0.0000 | 0.4056 | 1.0000 |
| `weighted_novelty` | 0.4161 | 0.1560 | 0.0000 | 0.4110 | 1.0000 |
| `top_company_share` | 0.3179 | 0.2604 | 0.0000 | 0.2308 | 1.0000 |
| `company_entropy` | 0.8254 | 0.3296 | 0.0000 | 0.9630 | 1.0000 |
| `event_entropy` | 0.6665 | 0.3295 | 0.0000 | 0.7823 | 1.0000 |

---

## 19. Test Results

Dedicated test suite `tests/test_news_feature_generation.py` verified all 14 mandatory invariants:

```
tests/test_news_feature_generation.py::test_1_point_in_time_correctness PASSED
tests/test_news_feature_generation.py::test_2_no_future_news_leakage PASSED
tests/test_news_feature_generation.py::test_3_snapshot_boundaries_disjoint PASSED
tests/test_news_feature_generation.py::test_4_membership_filtering PASSED
tests/test_news_feature_generation.py::test_5_novelty_lookback PASSED
tests/test_news_feature_generation.py::test_6_time_decay_half_life PASSED
tests/test_news_feature_generation.py::test_7_importance_formula_variance PASSED
tests/test_news_feature_generation.py::test_8_aggregation_correctness PASSED
tests/test_news_feature_generation.py::test_9_deterministic_output PASSED
tests/test_news_feature_generation.py::test_10_holdout_isolation PASSED
tests/test_news_feature_generation.py::test_11_no_nan_or_infinity_in_outputs PASSED
tests/test_news_feature_generation.py::test_12_terminal_coverage PASSED
tests/test_news_feature_generation.py::test_13_lici_exclusion PASSED
tests/test_news_feature_generation.py::test_14_ltim_zero_record_handling PASSED

============================== 14 passed in 0.97s ==============================
```

Full repository regression verification:
```
============================= 178 passed in 5.93s =============================
```

---

## 20. Output File Hashes & Deliverables

All deliverables have been generated, validated, and cryptographically hashed:

| Deliverable | File Path | Rows | Columns | SHA-256 Checksum |
| :--- | :--- | :---: | :---: | :--- |
| **Snapshot A Features** | `data/interim/news/features_news_snapshot_a.csv` | 4,653 | 65 | `487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7` |
| **Snapshot B Features** | `data/interim/news/features_news_snapshot_b.csv` | 4,653 | 65 | `f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606` |
| **Snapshot Delta (Diagnostic)** | `data/interim/news/features_news_snapshot_delta.csv` | 4,653 | 28 | `8923c11583fb87fe8458f00aaf714eadacb8a3d402a7143a5b2483549c8ece4c` |
| **Test Suite** | `tests/test_news_feature_generation.py` | 506 lines | N/A | 14 / 14 Unit & Integration Tests Passed |

---

## 21. Known Limitations

1. **LTIM Coverage Gap**: LTIMindtree has 0 authentic announcements due to exchange web endpoint properties; handled as authentic zero filings.
2. **Holiday Announcements**: Disclosures filed over long multi-day holidays are aggregated into the subsequent trading session's Snapshot B.
3. **Lexicon Specificity**: The Loughran-McDonald lexicon captures financial polarity with high fidelity but is conservative regarding domain-specific slang.
4. **Diagnostic Delta Isolation**: `features_news_snapshot_delta.csv` is strictly a diagnostic artifact and must not be used as an independent training vector without explicit approval.

---

## Final Verdict

$$\mathbf{A)\ NEWS\ NLP\ FEATURES\ READY\ FOR\ INCREMENTAL\ PREDICTIVE-VALUE\ EXPERIMENT}$$

> [!IMPORTANT]
> A verdict of **A** establishes that the point-in-time news NLP feature datasets are technically verified, leak-free, anti-survivorship bias filtered, and mathematically valid. **It does NOT assert that news features possess statistically significant predictive power over price and context.** The empirical evaluation of incremental predictive value must be determined in the subsequent modeling experiment.
