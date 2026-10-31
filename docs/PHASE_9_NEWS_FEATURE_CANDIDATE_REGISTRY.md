# Phase 9 — News Feature Candidate Registry & Provenance Audit

**Document Date**: September 16, 2026  
**Auditor / Lead ML Engineer**: Senior NLP Engineer & Quantitative Research Methodology Lead  
**Governing Phase**: Phase 9 — Point-in-Time News Feature Engineering & Incremental Predictive Evaluation  
**Status**: DRAFT FOR ARCHITECTURE REVIEW (Pre-Training Gate)  

---

## 1. Purpose & Provenance Architecture

This registry establishes the strict data provenance, point-in-time calculation rules, missing-value handling, and inclusion criteria for all candidate news features proposed for **Model 2 (Price + Context + News)**.

### Core Architectural Principle
Pursuant to the Phase 9 Architecture Sanity Review:
1. **Raw Inventory Reality**: The authentic historical news inventory (`data/interim/news/raw_authentic_news_inventory.jsonl`) contains **62,329 authentic corporate disclosures**, but contains **zero pre-existing manual annotation labels**.
2. **Phase 8 Annotation Boundaries**: Phase 8 produced only 50 Human Reference calibration annotations, 50 AI calibration annotations, and 1,000 AI-assisted development annotations. These 1,050 records represent only **1.68%** of the authentic historical corpus.
3. **No Silent Label Propagation**: Categorical annotations (`primary_event`, manual `sentiment`, `importance`) from the 1,050-record sample **must not be silently imputed or propagated** to the remaining 61,279 records.
4. **Deterministic Feature Derivation**: Any feature entering Model 2 must be derived deterministically from the authentic raw fields (`published_timestamp`, `headline`, `summary_or_body`, `company`, `historical_constituent_status`, `sector`) using reproducible, point-in-time algorithms.
5. **No Market Volume Re-Introduction**: News intensity must be normalized strictly by trailing historical **news counts**, never market trading volume (which remains quarantined from Phase 3).

---

## 2. Complete Candidate Feature Registry

The table below audits all proposed candidate features across the 6 methodological feature groups:

| Feature Name | Feature Group | Source Field(s) | Available for all 62,329? | Derivation Method | Phase 8 Annotation Dependent? | Point-in-Time (PIT) Rule | Missing / Zero-News Fallback | Leakage Risk | Inclusion Decision |
| :--- | :---: | :--- | :---: | :---: | :---: | :--- | :--- | :---: | :---: |
| `news_volume_total` | **A** (Raw Count) | `published_timestamp` | **Yes (100%)** | Count of valid records in snapshot window | **No** | $t_i \in 	ext{window}$ | $0$ | None | **APPROVED** |
| `num_distinct_companies` | **A** (Raw Count) | `company`, `published_timestamp` | **Yes (100%)** | Count of distinct company entities | **No** | $t_i \in 	ext{window}$ | $0$ | None | **APPROVED** |
| `active_constituent_news_count` | **A** (Raw Count) | `historical_constituent_status`, `published_timestamp` | **Yes (100%)** | Count where status = `ACTIVE_NIFTY_50_CONSTITUENT` | **No** | PIT constituent status at Session $T$ | $0$ | None | **APPROVED** |
| `has_news_flag` | **A** (Raw Count) | `published_timestamp` | **Yes (100%)** | $\mathbb{I}(	ext{news\_volume\_total} > 0)$ | **No** | $t_i \in 	ext{window}$ | $0$ | None | **APPROVED** |
| `news_intensity_20d` | **A** (Raw Count) | `published_timestamp` | **Yes (100%)** | $rac{N_T + 1}{	ext{SMA}_{20}(N) + 1}$ using trailing session news counts | **No** | Trailing 20 sessions strictly $< T$ | $1.0$ (neutral ratio) | None | **APPROVED** |
| `high_relevance_count` | **B** (Text/Rule) | `company_or_entities`, `headline` | **Yes (100%)** | Disclosures from top-10 historical NIFTY index heavyweights | **No** | Verified constituent membership at Session $T$ | $0$ | None | **APPROVED** |
| `corporate_action_rule_count` | **B** (Text/Rule) | `headline` | **Yes (100%)** | Deterministic regex on dividend, split, bonus, buyback, M&A | **No** | Evaluated on raw text $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `earnings_result_rule_count` | **B** (Text/Rule) | `headline` | **Yes (100%)** | Deterministic regex on quarterly/annual results, financial statements | **No** | Evaluated on raw text $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `order_contract_rule_count` | **B** (Text/Rule) | `headline` | **Yes (100%)** | Deterministic regex on contract win, order bags, commercial deal | **No** | Evaluated on raw text $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `management_change_rule_count` | **B** (Text/Rule) | `headline` | **Yes (100%)** | Deterministic regex on CEO, CFO, director resignation/appointment | **No** | Evaluated on raw text $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `regulatory_legal_rule_count` | **B** (Text/Rule) | `headline` | **Yes (100%)** | Deterministic regex on SEBI, court, tribunal, penalty, USFDA | **No** | Evaluated on raw text $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `annotator_primary_event_*` | **C** (Annotation) | `primary_event` (Phase 8 CSV) | **No (1.68%)** | Manual/AI-assisted categorical event labels | **YES** | Exists only for 1,050 records | N/A | High (Sparsity/Noise) | **PROHIBITED** |
| `annotator_economic_importance` | **C** (Annotation) | `importance` (Phase 8 CSV) | **No (1.68%)** | Manual/AI-assisted 1–5 ordinal score | **YES** | Exists only for 1,050 records | N/A | High (Sparsity/Noise) | **PROHIBITED** |
| `annotator_sentiment_class` | **C** (Annotation) | `sentiment` (Phase 8 CSV) | **No (1.68%)** | Manual/AI-assisted categorical polarity | **YES** | Exists only for 1,050 records | N/A | High (Sparsity/Noise) | **PROHIBITED** |
| `num_distinct_event_types` | **D** (Event Group) | `headline` | **Yes (100%)** | Count of distinct rule categories triggered in window | **No** | Deterministic regex $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `event_entropy` | **D** (Event Group) | `headline` | **Yes (100%)** | Normalized Shannon entropy of triggered rule categories | **No** | Deterministic regex $\le 	ext{cutoff}$ | $0.0$ | None | **APPROVED** |
| `positive_news_count` | **E** (Sentiment) | `headline`, `summary_or_body` | **Yes (100%)** | Count with Loughran-McDonald polarity $> +0.05$ | **No** | Lexicon + negation grammar $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `negative_news_count` | **E** (Sentiment) | `headline`, `summary_or_body` | **Yes (100%)** | Count with Loughran-McDonald polarity $< -0.05$ | **No** | Lexicon + negation grammar $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `neutral_news_count` | **E** (Sentiment) | `headline`, `summary_or_body` | **Yes (100%)** | Count with polarity in $[-0.05, +0.05]$ | **No** | Lexicon + negation grammar $\le 	ext{cutoff}$ | $0$ | None | **APPROVED** |
| `sentiment_balance` | **E** (Sentiment) | `headline`, `summary_or_body` | **Yes (100%)** | $rac{N_{\text{pos}} - N_{\text{neg}}}{N_{\text{pos}} + N_{\text{neg}} + 1}$ | **No** | Evaluated on polarity counts $\le 	ext{cutoff}$ | $0.0$ | None | **APPROVED** |
| `mean_sentiment_polarity` | **E** (Sentiment) | `headline`, `summary_or_body` | **Yes (100%)** | Mean continuous polarity across window items | **No** | Evaluated on polarity scores $\le 	ext{cutoff}$ | $0.0$ | None | **APPROVED** |
| `sentiment_dispersion` | **E** (Sentiment) | `headline`, `summary_or_body` | **Yes (100%)** | Sample standard deviation of polarity scores | **No** | Evaluated on polarity scores $\le 	ext{cutoff}$ | $0.0$ | None | **APPROVED** |
| `recency_weighted_sentiment` | **F** (Novelty/Decay) | `published_timestamp`, `headline` | **Yes (100%)** | Polarity weighted by $2^{-\Delta t / 24\text{h}}$ | **No** | Half-life = 24h at exact cutoff timestamp | $0.0$ | None | **APPROVED** |
| `news_novelty_score` | **F** (Novelty/Decay) | `company`, `published_timestamp` | **Yes (100%)** | Fraction of companies in window not active in trailing 7 days | **No** | Strictly trailing 7 calendar days before window | $0.0$ | None | **APPROVED** |

---

## 3. Analysis of Feature Eligibility & Exclusions

### A. Immediately Valid Features (Group A)
- **`news_volume_total`**, **`num_distinct_companies`**, **`active_constituent_news_count`**, **`has_news_flag`**, **`news_intensity_20d`**:
  - Derived strictly from metadata fields (`published_timestamp`, `company`, `historical_constituent_status`) populated for 100% of the 62,329 records.
  - Zero NLP ambiguity, zero subjective bias, zero leakage risk.
  - Denominator of `news_intensity_20d` uses strictly trailing 20-trading-session news volume, preserving the Phase 3 quarantine on market trading volume.

### B. Deterministic Text/Regex-Derived Features (Groups B & D)
- **`high_relevance_count`**:
  - Deterministically maps companies to the top-10 historical NIFTY 50 index heavyweights (Reliance, HDFC Bank, Infosys, ICICI Bank, TCS, ITC, L&T, SBI, HUL, Kotak Bank).
  - Eliminates subjective human/AI relevance labeling across 98.3% of the corpus.
- **Event Counts (`earnings_result_rule_count`, `corporate_action_rule_count`, `order_contract_rule_count`, `management_change_rule_count`, `regulatory_legal_rule_count`)**:
  - Extracted via high-precision keyword patterns on filing headlines.
  - Avoids relying on the noisy Phase 8 categorical primary event labels (which had only 14% Human-vs-AI concordance).

### C. Deterministic Sentiment Features (Group E)
- **`positive_news_count`**, **`negative_news_count`**, **`neutral_news_count`**, **`sentiment_balance`**, **`mean_sentiment_polarity`**, **`sentiment_dispersion`**:
  - Computed via `LoughranMcDonaldIndianSentiment`, an established deterministic financial domain dictionary adapted for Indian financial English and accounting negation rules.
  - 100% reproducible, completely independent of future prices, zero post-hoc parameter fitting.

### D. Time-Decay & Novelty Features (Group F)
- **`recency_weighted_sentiment`**:
  - Implements the Phase 8 locked 24-hour half-life exponential decay weight relative to snapshot cutoff: $w_i = 2^{-\Delta t_i / 24.0}$.
- **`news_novelty_score`**:
  - Implements the Phase 8 locked 7-day trailing lookback window for entity novelty.

### E. Excluded / Prohibited Features (Group C)
- **`annotator_primary_event_*`**, **`annotator_economic_importance`**, **`annotator_sentiment_class`**:
  - **REASON FOR PROHIBITION**: Available only on 1,050 records (1.68% of the authentic inventory). Propagating these labels would require synthetic imputation across 61,279 records, creating severe artificial noise and violating scientific integrity.
  - Furthermore, Phase 8 empirical agreement on primary event was low ($\kappa = 0.0636$), making categorical event labels unsuitable as a core dependency for Model 2.

---

## 4. Phase 7 Context Transformations for Model 1

To maintain strict parity with Phase 6 while avoiding rebuilding Phase 7 context datasets, the following point-in-time transformations are defined for **Model 1 (Price + Context)**:

1. **Daily Log Returns of Context Price Series**:
   $$r_{\text{asset}, t} = \ln\left(\frac{P_{\text{asset}, t}}{P_{\text{asset}, t-1}}\right)$$
   Computed for: `nifty_bank`, `sp500`, `nasdaq`, `dow_jones`, `brent_crude`, `wti_crude`, `gold`, `dxy`, `nikkei_225`, `hang_seng`, `ftse_100`.
2. **Daily Absolute Changes in Yields and Volatility**:
   $$\Delta V_t = V_t - V_{t-1}$$
   Computed for: `india_vix`, `us_vix`, `india_10y_yield`, `us_10y_yield`, `usd_inr`.
3. **Volatility Regime Levels**:
   - `india_vix_close` (raw level as stationary volatility regime feature).
   - `us_vix_close` (raw level).

All context inputs are sourced strictly from `data/interim/context/snapshot_a_context_daily.csv` and `snapshot_b_context_daily.csv` adhering to the locked Phase 7 availability timestamps (e.g., Snapshot A strictly uses Session $T-1$ US closes; Snapshot B incorporates overnight Session $T$ US closes).

---

## 5. Summary of Approved Model 2 Feature Set

The approved initial Model 2 feature set comprises **18 vetted news features**:

1. `news_volume_total` (Group A)
2. `num_distinct_companies` (Group A)
3. `active_constituent_news_count` (Group A)
4. `has_news_flag` (Group A)
5. `news_intensity_20d` (Group A - pure news denominator)
6. `high_relevance_count` (Group B - top-10 constituent heavyweights)
7. `corporate_action_rule_count` (Group B - regex)
8. `earnings_result_rule_count` (Group B - regex)
9. `order_contract_rule_count` (Group B - regex)
10. `management_change_rule_count` (Group B - regex)
11. `regulatory_legal_rule_count` (Group B - regex)
12. `num_distinct_event_types` (Group D)
13. `event_entropy` (Group D)
14. `sentiment_balance` (Group E - Loughran-McDonald)
15. `mean_sentiment_polarity` (Group E - Loughran-McDonald)
16. `sentiment_dispersion` (Group E - Loughran-McDonald)
17. `recency_weighted_sentiment` (Group F - 24h half-life)
18. `news_novelty_score` (Group F - 7-day lookback)

Every approved feature is 100% computable for all 62,329 records across 2008–2021, strictly point-in-time, independent of future prices, and free of manual annotation dependency.
