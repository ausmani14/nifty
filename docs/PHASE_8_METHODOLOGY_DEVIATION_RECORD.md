# Phase 8 — Methodology Deviation Record: AI-Assisted Annotation Validation

**Record ID**: `MDR-PHASE8-001`  
**Date**: September 16, 2026  
**Status**: APPROVED & ADOPTED  
**Document Owner**: Senior NLP Engineer & Quantitative Research Methodology Lead  
**Governing Phase**: Phase 8 — News & NLP Intelligence Layer  

---

## 1. Context & Original Design Target

The original research design for Phase 8 specified:
- A double-blind annotation study executed by **two independent human domain experts** across development and calibration samples.
- Evaluation of inter-annotator reliability using chance-corrected Cohen's kappa ($\kappa_{\text{human-human}} \ge 0.75$) prior to benchmark lock.
- Human-expert adjudication of all disputed records.

---

## 2. Methodology Deviation Specification

### A. Rationale
Due to project execution constraints (single available on-site human domain expert and resource allocation limits), executing a full second independent human annotation pass for all calibration and development records is unviable in the current project phase.

### B. Implemented V1 Architecture
To maintain scientific rigor without halting project progress, the Phase 8 annotation architecture is formally revised to an **AI-Assisted NLP Annotation Methodology**:

1. **Annotator 1 (Human Reference Annotation)**:
   - Evaluated by the project owner (domain expert).
   - Authoritative reference: `data/interim/news/fresh_calibration_50_human_annotations_corrected.csv`.
2. **Annotator 2 (Independent Blind AI Pass)**:
   - Evaluated by an independent AI pass operating strictly on raw metadata without access to Annotator 1 labels.
   - Authoritative reference: `data/interim/news/fresh_calibration_50_annotator_2_completed.csv`.
3. **Statistical Validation Mode**:
   - Concordance is evaluated strictly as an **AI-vs-Human QC / Sensitivity Analysis**.
   - Generic categorical Cohen's kappa and concordance percentages are computed between the two label streams.
   - These metrics must **NEVER** be described as human-human inter-annotator agreement or inter-rater reliability.
4. **Adjudication Procedure**:
   - Human adjudication procedure is defined in the methodology but has not been executed as a separate adjudication pass.

---

## 3. Operational Calibration Gate Adjustment

- **Previous Gate**: Blocked pending $\kappa_{\text{human-human}} \ge 0.75$.
- **Revised Operational Gate**:
  - **PASS Criteria**:
    1. Zero critical schema or source-record mapping defects.
    2. 100% 1-to-1 alignment between source records and annotation IDs.
    3. Human-vs-AI agreement / sensitivity analysis successfully completed and documented.
    4. No evidence of systematic catastrophic annotation failure.
    5. Guidelines and taxonomy internally consistent and verified.
    6. All automated domain and repository test suites pass (100%).
  - **Status under Revised Gate**: **PASSED**.

---

## 4. Academic & Research Disclosure Requirements

In any published paper, technical disclosure, or thesis deriving from this system, the following formal limitation statement must be included:

> *"Annotator 2 is an independent AI annotation pass. It is not a human expert and therefore cannot establish human inter-annotator reliability. The resulting agreement metrics are used for sensitivity/QC validation only."*
