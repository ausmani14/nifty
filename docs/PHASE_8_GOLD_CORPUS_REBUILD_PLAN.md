# Phase 8 — Gold Corpus Rebuild Methodology & Implementation Plan
**NIFTY AI — Next-Trading-Day Return Forecasting Engine**  
**Component:** News & NLP Intelligence Layer  
**Document Version:** 1.0.0  
**Date:** 2026-09-15  
**Status:** APPROVED FOR REBUILD EXECUTION  

---

## 1. Executive Summary & Objective

Following the forensic audit that confirmed a critical data-integrity collision (identical SHA-256 hash `689d8046a73d22b1c1834e3c63e1e4bce7a8dfea95b44a224464914e0db14d7b` across `sentiment_gold_dataset.csv` and `event_gold_dataset.csv`, circular rule-based ground-truth assignment, absent provenance URLs/IDs, and 2 holdout-period date contaminations), all empirical benchmark claims based on the rejected 520-record dataset are **formally retracted**.

This document specifies the rigorous, scientific architecture for rebuilding the Phase 8 validation suite using **genuine, externally sourced historical financial documents and independently adjudicated ground-truth labels**.

### Core Constraints & Invariants:
1. **Phase 8 Remains Unsealed**: Phase 8 cannot be approved until genuine independent validation is established.
2. **Phase 9 Prohibited**: No Phase 9 modeling, feature concatenation, or return predictions may begin.
3. **Phase 5/6/7 Protected Artifacts Frozen**: All 17 baseline models, target sets, feature registries, and context datasets remain 100% byte-for-byte immutable.
4. **Permanent Reclassification of Legacy 520 Records**: The 520 legacy records are permanently reclassified as `SYNTHETIC / FIXTURE DATA` for software pipeline verification only and must never be cited as empirical evidence.
5. **Honest Ingestion Protocol**: If authentic historical documents cannot be sourced at scale without paid commercial feeds, the system must declare `PHASE 8 REBUILD BLOCKED — INSUFFICIENT AUTHENTIC HISTORICAL DATA` rather than fabricating data.

---

## 2. Source Hierarchy & Ingestion Standards

To guarantee point-in-time legitimacy and legal auditability, news and filings must be retrieved exclusively through a verified 5-tier Source Hierarchy:

```
====================================================================================================
APPROVED SOURCE HIERARCHY FOR BENCHMARK CORPORA
====================================================================================================
Tier / Category          Approved Source Types                         Timestamp & Provenance Semantics
----------------------------------------------------------------------------------------------------
Tier 1: Regulatory       - Official NSE/BSE Corporate Filings          Exchange server ingestion clock
                          (Form 33, Reg 30, Reg 33, Board meetings)    with legal audit log.
                         - RBI Monetary Policy Press Releases          Official RBI bulletin release timestamp.
                         - SEBI Enforcement / Adjudication Orders     Official SEBI web portal publication stamp.
                         - Government / Ministry of Finance Releases   PIB / Gazette official release timestamp.

Tier 2: Primary Wires    - Reuters Financial News Wire                 Commercial wire transmission timestamp
                         - Bloomberg Terminal News Feed                with verified broadcast millisecond tag.
                         - Press Trust of India (PTI) Business Wire    PTI wire release dispatch timestamp.

Tier 3: Press Archives   - The Economic Times Archive                  Archival web page with immutable
                         - LiveMint / Hindustan Times Archive          microdata publication timestamp (JSON-LD)
                         - Business Standard / Financial Express       and revision history log.

Tier 4: Public Aggregators- GDELT Project 2.0 Doc API                  Global event database with V2Tone;
                         - Academic News Archives (Kaggle/Zenodo)      Requires explicit publication URL & date.

Tier 5: Rejected Sources - Social media posts / forums (Twitter/Reddit) UNACCEPTABLE (Quarantined)
                         - Date-only web articles without time         UNACCEPTABLE (Quarantined)
                         - Post-hoc revised articles without log       UNACCEPTABLE (Quarantined)
                         - Parameterized / LLM-generated headlines     UNACCEPTABLE (Quarantined)
====================================================================================================
```

---

## 3. Required Per-Record Provenance Schema

Every candidate record considered for the gold benchmark must contain the following 21 standardized provenance attributes. If any field cannot be verified, it must be explicitly recorded as `"UNAVAILABLE"` or `null`—**fabrication of URLs, filing IDs, or timestamps is strictly prohibited**.

```json
{
  "gold_id": "STRING (e.g. AUTH_GOLD_0001)",
  "headline": "STRING (Exact original headline without synthetic alterations)",
  "summary_or_body_snippet": "STRING (First 1-2 paragraphs of lead text or disclosure snippet)",
  "published_date": "ISO-8601 DATE (YYYY-MM-DD)",
  "published_timestamp": "ISO-8601 UTC/IST DATETIME (YYYY-MM-DDTHH:MM:SS+05:30)",
  "published_timezone": "STRING (e.g. Asia/Kolkata or UTC)",
  "availability_timestamp": "ISO-8601 DATETIME (Point-in-time public availability)",
  "source": "STRING (e.g. NSE_FILING, BSE_ANNOUNCEMENT, RBI_PRESS, REUTERS)",
  "source_url": "STRING (Verifiable external URL; 'UNAVAILABLE' if offline archive)",
  "source_type": "STRING (tier_1_regulatory, tier_2_primary_wire, tier_3_financial_press)",
  "evidence_level": "STRING (level_a_realtime, level_b_documented_exchange, level_c_commercial_wire)",
  "document_id_or_external_id": "STRING (Exchange filing submission ID, NSE circular no., DOI)",
  "company_or_entities": "ARRAY OF STRINGS (Identified NIFTY 50 canonical constituent symbols)",
  "sector": "STRING (Mapped official NSE Sector Taxonomy index)",
  "ground_truth_sentiment": "ENUM (POSITIVE, NEGATIVE, NEUTRAL)",
  "ground_truth_event_labels": "ARRAY OF STRINGS (Multi-label from approved 16-class taxonomy)",
  "annotation_method": "STRING (INDEPENDENT_HUMAN_EXPERT, EXTERNAL_REGULATORY_SEMANTICS)",
  "annotator_id_or_annotation_batch": "STRING (Identifier of independent annotator/batch)",
  "annotation_timestamp": "ISO-8601 DATETIME (Timestamp when annotation was locked)",
  "annotation_status": "STRING (RAW, ANNOTATED, ADJUDICATED, REJECTED)",
  "is_pre_2022": "BOOLEAN (True iff published_date < 2022-01-01)"
}
```

---

## 4. Point-in-Time Cutoff Requirements

All records in the benchmark must strictly obey the project's non-overlapping snapshot contracts:

```
====================================================================================================
SNAPSHOT ELIGIBILITY CONTRACTS
====================================================================================================
Dimension                Snapshot A (Post-Market)                 Snapshot B (Pre-Market)
----------------------------------------------------------------------------------------------------
Reference Session        Day T                                    Day T+1
Execution Clock          15:40:00 IST on Day T                    08:50:00 IST on Day T+1
Strict Cutoff            <= 15:30:00 IST on Day T                 <= 08:50:00 IST on Day T+1
Eligible Window          Intraday: (15:30 T-1, 15:30 T]           Pure Overnight: (15:30 T, 08:50 T+1]
Point-in-Time Formula    availability_timestamp <= 15:30:00 IST  15:30:00 IST < availability_timestamp
                                                                  AND availability_timestamp <= 08:50:00 IST
Mutual Exclusivity       Omega_A(T) INTERSECT Omega_B(T+1) = EMPTY SET
====================================================================================================
```
**Leakage Invariant**: Any news record whose `availability_timestamp` cannot be proven to be <= the snapshot cutoff is disqualified and quarantined.

---

## 5. Holdout Partition Isolation Rules

1. **Development/Holdout Boundary**:
   - **Development Partition**: `2008-07-08` through `2021-12-31`.
   - **Terminal Holdout Partition**: `2022-01-01` through `2026-09-04`.
2. **Strict Quarantining**:
   - No benchmark record used for development, model calibration, rule evaluation, or metric reporting may have `published_date >= 2022-01-01`.
   - Any record with `published_date >= 2022-01-01` must be routed to `data/interim/news/holdout_news_records.jsonl` and kept sealed until the project-wide holdout evaluation phase.
   - The two contaminated records identified in the audit (`GOLD_0045` on 2022-04-04 and `GOLD_0051` on 2023-08-14) are permanently evicted from the development benchmark.

---

## 6. Annotation Independence Guarantee

To prevent circular benchmarking where model rules are tested against their own logic:

1. **Strict Prohibition**: Ground truth labels (`ground_truth_sentiment`, `ground_truth_event_labels`) **MUST NOT** be produced by:
   - `sentiment.py` (`LoughranMcDonaldIndianSentiment`)
   - `nlp_engine.py` (`classify_events_multi_label`)
   - Any keyword dictionary, regex pattern, or tokenizer from `nifty_ai`
   - Any parameterized template generation script
2. **Approved Ground-Truth Sources**:
   - **External Authoritative Semantics**: Official regulatory actions where direction is legally defined (e.g., SEBI penalty order is inherently negative; clean US FDA EIR inspection is inherently positive; RBI repo rate hike is monetary tightening).
   - **Independent Human Annotation Protocol**: Multi-annotator labeling following an explicit annotation rubric with recorded rationale, annotator ID, and adjudication of disagreements.
   - **Pre-existing Academic Datasets**: Financial phrasebanks or corporate filing benchmark sets independently curated prior to this study.

---

## 7. Benchmark Sizing & Diversity Specifications

Rather than mandating an arbitrary large number (e.g. 500+) that incentivizes synthetic data fabrication, the benchmark adopts an honest **dual-tier sizing standard**:

```
====================================================================================================
BENCHMARK SIZING AND COMPOSITION SPECIFICATION
====================================================================================================
Dimension                         Minimum Acceptable Benchmark     Target Production Benchmark
----------------------------------------------------------------------------------------------------
Total Validated Records           >= 100 authentic records         >= 300 authentic records
Time Span Coverage                >= 5 distinct calendar years     >= 8 distinct calendar years
Constituent Diversity             >= 10 NIFTY 50 constituents      >= 20 NIFTY 50 constituents
Sentiment Class Minimums          Positive: >= 30 records          Positive: >= 100 records
                                  Negative: >= 30 records          Negative: >= 100 records
                                  Neutral:  >= 20 records          Neutral:  >= 50 records
Populated Event Classes           >= 8 populated event classes     >= 12 populated event classes
Per-Class Event Minimum           >= 5 records per populated class >= 10 records per populated class
Unpopulated Event Classes         Reported as 0 (Never fabricated) Reported as 0 (Never fabricated)
====================================================================================================
```
**Principle**: A genuine, auditable benchmark of 120 authentic records is vastly superior and scientifically valid compared to a synthetic 520-record pseudo-benchmark.

---

## 8. Provider Technical Accessibility Audit

To establish whether genuine records can be fetched automatically or require offline archiving, every candidate provider must be documented honestly:

```
====================================================================================================
PROVIDER ACCESSIBILITY & CONSTRAINT MATRIX
====================================================================================================
Provider / Source        Coverage Span    API Status          Timestamp Quality   Legal / Access Constraints
----------------------------------------------------------------------------------------------------
NSE Corporate Filings    2008–Present     No public free API  Second-level clock  Public portal uses anti-bot
                                                                                  WAF; bulk historical requires
                                                                                  commercial NSE Data feed.
BSE Announcements        2008–Present     No public free API  Second-level clock  BSE API requires member login;
                                                                                  historical scraping restricted.
RBI Press Releases       2008–Present     Public web archive  Minute-level stamp  Accessible via official site
                                                                                  bulletin archives.
GDELT 2.0 Doc API        2015–Present     Rate-limited (429)  15-minute intervals Free tier strictly limits bulk
                                                                                  queries; frequent timeouts.
Yahoo Finance News       Current only     No historical news  Date-only           Historical news endpoint does
                                                                                  not exist on free tier.
Academic Corpora         Pre-2022         Open access         Varies (Need audit) Usable if Indian financial
(Kaggle / HuggingFace)                                                            text with verified metadata.
====================================================================================================
```

If automated programmatic acquisition fails due to rate limits or commercial paywalls, the system will construct an auditable, manually verified corpus of authentic historical corporate filings and regulatory releases, recording exact document references, and report the real coverage limitations transparently.
