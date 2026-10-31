# Phase 8 — Gold Corpus Rebuild & Forensic Resolution Report
**NIFTY AI — Next-Trading-Day Return Forecasting Engine**  
**Phase:** Phase 8 — News & NLP Intelligence Layer  
**Document Version:** 1.0.0  
**Date:** 2026-09-15  
**Canonical Project Status:** **PHASE 8 REBUILD BLOCKED — INSUFFICIENT AUTHENTIC HISTORICAL DATA**  
**Phase 8 Sealing Status:** **FAILED / UNSEALED**  
**Phase 9 Authorization:** **STRICTLY PROHIBITED**

---

## 1. Executive Summary & Forensic Audit Resolution

Following the identification of critical data-integrity failures in the initial Phase 8 validation artifacts, a comprehensive forensic audit was conducted. The audit confirmed the following non-negotiable failure conditions in the legacy benchmark artifacts:

1. **Critical SHA-256 Hash Collision**:  
   data/interim/news/sentiment_gold_dataset.csv and data/interim/news/event_gold_dataset.csv had identical SHA-256 hashes (689d8046a73d22b1c1834e3c63e1e4bce7a8dfea95b44a224464914e0db14d7b) and identical byte lengths (169,464 bytes). The event corpus was a byte-for-byte clone of the sentiment corpus, violating the requirement for independently constructed gold benchmarks.
2. **Circular Rule-Based Ground-Truth Generation**:  
   Forensic analysis revealed that 465 out of the 520 records were generated from 16 parameterized templates with hardcoded sentiment and event labels. The NLP engine rules and regex patterns were subsequently tailored to match these exact phrases, creating a circular benchmark where the system was evaluating its own rules rather than real-world text.
3. **Total Absence of Real-World Document Provenance**:  
   0 out of 520 records contained authentic, verifiable external URLs, NSE/BSE filing submission numbers, or legally auditable timestamps. All URLs followed synthetic placeholder patterns (https://reuters.com/business/...).
4. **Terminal Holdout Boundary Contamination**:  
   Two records directly violated the strict pre-2022 development boundary (2008-07-08 to 2021-12-31):
   - Record GOLD_0045: Dated 2022-04-04 (Holdout period)
   - Record GOLD_0051: Dated 2023-08-14 (Holdout period)  
   Both records were falsely flagged as is_pre_2022: True in the metadata, contaminating the development set with future holdout data.
5. **Taxonomy & Robustness Discrepancies**:  
   - In the legacy event benchmark, two approved taxonomy classes (geopolitical and nalyst_rating) had exactly 0 primary annotations, yet metrics were reported as complete.
   - The robustness suite implemented in code contained 18 deterministic tests (yielding 16/18 = 88.89%), while the previous audit prose claimed 120 tests with a 98.33% pass rate.

### Immediate Corrective Actions Taken:
- **Formal Retraction**: All empirical accuracy, macro-F1, and robustness claims based on the legacy 520 records are **formally and permanently retracted**.
- **Evidence Preservation & Quarantining**: The 520 records have been permanently moved out of empirical benchmark status into data/interim/news/synthetic_sentiment_fixture.csv and data/interim/news/synthetic_event_fixture.csv, cataloged under data/interim/news/synthetic_gold_rejected_manifest.json as software unit-test fixtures only.
- **Protected Boundaries Preserved**: All 17 Phase 5, Phase 6, and Phase 7 artifacts remain 100% byte-for-byte immutable. Zero models were retrained. Phase 9 has not commenced.

---

## 2. Definitive Corpus Classification Taxonomy

To prevent ambiguity between software test fixtures and genuine empirical data, all data assets in the NIFTY AI news layer are strictly categorized into five mutually exclusive classes:

`
====================================================================================================
NIFTY AI DATASET CLASSIFICATION TAXONOMY
====================================================================================================
Category                      Definition                                                  Current Status in Repo
----------------------------------------------------------------------------------------------------
1. Genuine Externally Sourced Documents fetched from authentic, legal primary archives    INSUFFICIENT HISTORICAL
                              (NSE/BSE filings, RBI press releases, audited wires) with  VOLUME (Blocked on
                              verifiable external document IDs and publication clocks.   commercial feeds)
----------------------------------------------------------------------------------------------------
2. Human-Labelled Gold        Documents annotated by human financial experts or direct   STANDARDIZED VIA
                              regulatory decree with independent adjudicator ID and      annotation.py;
                              documented reasoning, strictly independent from rules.     NO SYNTHESIS PERMITTED
----------------------------------------------------------------------------------------------------
3. Synthetic Fixtures         Synthetically generated or templated records used ONLY     PRESERVED AS FIXTURES
                              to verify code syntax, schema parsers, and data pipelines  (synthetic_*_fixture.csv)
                              in unit tests. Must NEVER be used for model benchmarking.  FOR PYTEST ONLY
----------------------------------------------------------------------------------------------------
4. Rejected Legacy Records    The 520 legacy records failed by the forensic audit due    QUARANTINED IN MANIFEST
                              to hash collision, circularity, and holdout contamination. (synthetic_gold_rejected_
                              Explicitly forbidden from any benchmark evaluation.        manifest.json)
----------------------------------------------------------------------------------------------------
5. Unsupported Periods        Any historical trading dates (especially 2008–2015) where  CLASSIFIED AS
                              free public APIs cannot provide second-level timestamps.   GENUINE ZERO COVERAGE
                              Must be recorded as missing data, never backfilled.        (No fabrication)
====================================================================================================
`

---

## 3. Technical Provider Accessibility & Feasibility Audit

A rigorous engineering investigation was conducted to determine whether genuine historical financial news from 2008 through 2021 can be programmatically acquired via free, open APIs. The results are summarized below:

`
====================================================================================================
NEWS PROVIDER FEASIBILITY & BOTTLENECK AUDIT
====================================================================================================
Provider / Platform      Access Status                Failure / Constraint Reason
----------------------------------------------------------------------------------------------------
1. NSE Corporate         COMMERCIAL_PAYWALL_REQUIRED  NSE public web portal is protected by Akamai anti-bot
   Filings (Reg 30/33)                                WAF. Bulk programmatic historical access requires an
                                                      enterprise subscription to NSE Historical Data Feed.
----------------------------------------------------------------------------------------------------
2. BSE Announcements     COMMERCIAL_PAYWALL_REQUIRED  BSE historical announcements API requires registered
                                                      brokerage / market participant credentials; web scraping
                                                      violates terms of service and triggers IP blacklisting.
----------------------------------------------------------------------------------------------------
3. RBI Press Releases    OFFLINE_ARCHIVE_ONLY         RBI official web bulletins provide verified minute-level
                                                      timestamps, but cover only macro/monetary policy; they
                                                      do not provide constituent-level corporate news.
----------------------------------------------------------------------------------------------------
4. GDELT 2.0 Doc API     RATE_LIMITED_429             Free public GDELT Doc API repeatedly returns HTTP 429
                                                      (Too Many Requests) when issuing iterative historical
                                                      queries for NIFTY 50 corporate tickers over multi-year windows.
----------------------------------------------------------------------------------------------------
5. Yahoo Finance News    NO_HISTORICAL_API            Yahoo Finance free API provides only current (real-time)
                                                      articles; historical news search is not supported.
----------------------------------------------------------------------------------------------------
6. Reuters / Bloomberg   COMMERCIAL_PAYWALL_REQUIRED  Historical tick-level news wires require Bloomberg
                                                      Terminal (B-PIPE) or Refinitiv/LSEG Tick History feeds.
====================================================================================================
`

### Engineering Conclusion on Data Availability:
Without paid commercial data licenses (such as NSE Corporate Filings Feed or Bloomberg/Refinitiv News Feeds), **it is technically impossible to programmatically assemble 14 years (2008–2021) of second-accurate, point-in-time timestamped news for all 50 NIFTY constituents**.

In strict accordance with scientific integrity guidelines:
> **The project refuses to fabricate, parameterize, or synthesize historical headlines to simulate data availability.**  
> Where authentic data cannot be obtained, the system formally declares the pipeline **BLOCKED** rather than presenting synthetic illusions.

---

## 4. Rebuilt Architectural Modules

To prepare the repository for future integration with licensed enterprise feeds, the news layer architecture has been rebuilt with rigorous software boundaries:

### A. Provider Audit Registry (src/nifty_ai/data/news/providers.py)
- Defines standard provider metadata, access status enums, and constraint descriptors.
- Encapsulates NewsProviderAudit and NEWS_PROVIDER_REGISTRY to ensure transparent tracking of source limitations.
- Enforces explicit reporting of COMMERCIAL_PAYWALL_REQUIRED, RATE_LIMITED_429, and OFFLINE_ARCHIVE_ONLY.

### B. Independent Annotation & Provenance Pipeline (src/nifty_ai/data/news/annotation.py)
- Standardizes the 21 per-record provenance fields defined in PHASE_8_GOLD_CORPUS_REBUILD_PLAN.md.
- Implements alidate_benchmark_batch:
  - Enforces independent human nnotator_id and non-empty sentiment_rationale.
  - Rejects circular automated rule labels.
  - Strictly catches holdout contamination (published_date >= 2022-01-01 must have is_pre_2022 == False).
  - Rejects unverified evidence levels.

### C. Quarantined Legacy Artifacts & Manifest
- Created data/interim/news/synthetic_gold_rejected_manifest.json containing complete forensic documentation of all 6 failure modes.
- Preserved legacy files as data/interim/news/synthetic_sentiment_fixture.csv and data/interim/news/synthetic_event_fixture.csv exclusively for pipeline regression testing.

---

## 5. Test Suite Verification & Robustness Reconciliation

The test suite in 	ests/test_news.py was completely refactored to remove all dependencies on the rejected gold datasets and align with empirical realities:

`
====================================================================================================
TEST SUITE EXECUTION SUMMARY
====================================================================================================
Test Suite Component                   Tests Run    Passed    Failed    Notes
----------------------------------------------------------------------------------------------------
News Schema & Point-in-Time Cutoffs    12           12        0         Snapshot A (<=15:30) & B ((15:30, 08:50])
Causal Deduplication (7-day lookback)   4            4        0         Historical novelty invariance verified
Entity Extraction & Disambiguation      4            4        0         Temporal membership & token mapping
Event Taxonomy (All 16 Classes)         2            2        0         Multi-label & 16-class integrity
Rejection Manifest & Collision Check    3            3        0         Catches duplicate corpora & invalid sources
Holdout Contamination Rejection         2            2        0         Rejects post-2022 dates in dev benchmark
Developer Robustness Suite              1            1        0         Canonical 16/18 = 88.89% verified
Provider Registry & FinBERT Honesty     8            8        0         Audit status & framework honesty checks
----------------------------------------------------------------------------------------------------
TOTAL NEWS TESTS IN tests/test_news.py 36           36        0         100% Pass Rate
TOTAL PROJECT TESTS (ALL SUITES)       133          133       0         100% Pass Rate
====================================================================================================
`

### Robustness Benchmark Reconciliation:
- The actual deterministic developer robustness suite in code evaluates **18 specific edge cases** (negation handling, accounting reversal, extreme returns, entity substitution, numerical context).
- **Canonical Robustness Score**: **16 / 18 = 88.89%**.
- The two failing edge cases are documented transparently:
  1. *Subtle sarcasm/irony without explicit negative financial keywords.*
  2. *Double-negative phrasing with ambiguous syntactic dependency.*
- The previous claim of 120 tests and 98.33% has been corrected in the test assertions and documentation.

---

## 6. Verification of Protected Artifacts

All 17 protected artifacts across Phase 5 (targets/features), Phase 6 (models), and Phase 7 (market context) have been cryptographically verified against their locked baseline SHA-256 hashes:

`
====================================================================================================
CRYPTOGRAPHIC AUDIT OF ALL 17 PROTECTED PROJECT ARTIFACTS
====================================================================================================
Artifact Path                                                       SHA-256 Digest                                                    Status
------------------------------------------------------------------------------------------------------------------------------------
data/processed/nifty_50_daily.csv                                   2d6512a878a68a01b56f7dd9193ac7419879949311cc8f338da52c1694771d95 INTACT
data/features/nifty50_features.meta.json                            6d4bc2c817159aca2df099ffc96bc75150e3a67abcc95f3cb627669e37a39a07 INTACT
data/targets/nifty50_targets.meta.json                              69e9bd78a800325ea7434ac214778e651fd43c278521c8443f86b9e02f7b78c6 INTACT
data/targets/nifty50_targets_snapshot_a.csv                         a13fed61f92c3fcccf9fe09ce59eb0df4d95ef8dce0aef970ff5ed1220ea055d INTACT
data/targets/nifty50_targets_snapshot_b.csv                         54ac54fdeafd53ddea20b1d31cd89c1fbaebdbc88c0f24f8a1f73ce2867e01d2 INTACT
models/v1/classifier/snapshot_a_xgboost_classifier.json             3bb447ad76d1294fff4e125499e0c461def89ec8f44073d98f6d556b9cbf6ce8 INTACT
models/v1/classifier/snapshot_a_xgboost_classifier.meta.json        e1e270b2d48b15389a1ff5cd87ea2a993ec013fa2de74488b6416d0886264c97 INTACT
models/v1/classifier/snapshot_b_xgboost_classifier.json             3bb447ad76d1294fff4e125499e0c461def89ec8f44073d98f6d556b9cbf6ce8 INTACT
models/v1/classifier/snapshot_b_xgboost_classifier.meta.json        efab866a10c56eb636e977a44b6de6a453bee080a01667a9f4a9e2be98fb8cb3 INTACT
models/v1/regressor/snapshot_a_xgboost_regressor.json               97513ca39817714da5fe6ff8a5d3bbdd5237eac772a3f40803cf166dbf6874e6 INTACT
models/v1/regressor/snapshot_a_xgboost_regressor.meta.json          d338290575cd13a0d00f2d973a250904ef66529154961722f996c75abd51f996 INTACT
models/v1/regressor/snapshot_b_xgboost_regressor.json               97513ca39817714da5fe6ff8a5d3bbdd5237eac772a3f40803cf166dbf6874e6 INTACT
models/v1/regressor/snapshot_b_xgboost_regressor.meta.json          1b1458b8e5574b00c427981324400743c8d065a92560c7bd1ee2509b94d444a8 INTACT
data/interim/context/snapshot_a_context_daily.csv                   26f41d5978b2f78fb9fad223d9efe9970820ab7f81510490ed6f1b39872178af INTACT
data/interim/context/snapshot_b_context_daily.csv                   08a694f86f70c5246b8b6b4928283b676dd998912e481d88a718ba08970237be INTACT
data/interim/context/availability_matrix.json                       2d3d6f8d4c8c5293da13613d2744fa304a8551edeb30365e71142707492400c1 INTACT
data/interim/context/context_manifest.json                          add1cd6a74d41e4eb66d34409ac0b09b6bb6b1ecde160ab00269185f07844535 INTACT
====================================================================================================
Result: 17 / 17 Protected Artifacts 100% Unchanged and Cryptographically Verified.
`

---

## 7. Project Boundaries & Next Phase Invariants

1. **Phase 8 Remains Unsealed**:
   - Phase 8 is **FAILED / UNSEALED**.
   - No claim of gold-standard empirical validation can be made until genuine, non-synthetic historical corpora are acquired.
2. **Canonical Project Status**:
   - **PHASE 8 REBUILD BLOCKED — INSUFFICIENT AUTHENTIC HISTORICAL DATA**.
3. **Phase 9 Prohibited**:
   - Phase 9 (Feature Engineering & Multimodal Model Integration) **MUST NOT START**.
   - No news features may be added to the Phase 6 baseline models.
4. **Resolution Path**:
   - Commercial data feeds (e.g. licensed NSE corporate filings or Bloomberg/Refinitiv tick history) or pre-existing public academic corpora with audited document IDs must be licensed/procured to unblock Phase 8 empirical benchmarking.
   - Until such feeds are connected, the codebase remains in a safe, fully verified, and transparently auditable state.
