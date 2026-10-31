"""Phase 13 Step 5 Model Promotion Decision & Research Disposition Test Suite.

Audits:
1. Presence and integrity of Step 5 decision artifacts.
2. Cryptographic integrity of Step 5 manifest and upstream manifests.
3. Strict adherence to decision governance:
   - Model disposition: RESEARCH BASELINE ONLY.
   - Production promotion: Strictly rejected.
   - Real-money trading: Strictly unauthorized.
   - Data classification: PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA.
4. Correct evaluation and verification of all 8 promotion criteria.
5. Invariance of sealed Phase 0-12 and Phase 13 Steps 1-4 artifacts.
"""

import hashlib
import json
from pathlib import Path
import pytest

from nifty_ai.config import PROJECT_ROOT

STEP5_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_step5"
STEP1_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_step1"
STEPS2_4_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_steps2_4"
DOCS_DIR = PROJECT_ROOT / "docs"


def compute_sha256(filepath: Path) -> str:
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


# 1. Step 5 artifact existence
def test_step5_artifacts_exist():
    assert (DOCS_DIR / "PHASE_13_STEP5_MODEL_PROMOTION_DECISION.md").exists(), "Step 5 decision doc missing"
    assert (STEP5_DIR / "phase13_step5_decision.json").exists(), "Step 5 decision json missing"
    assert (STEP5_DIR / "phase13_step5_integrity_manifest.json").exists(), "Step 5 integrity manifest missing"


# 2. Step 5 manifest integrity
def test_step5_manifest_integrity():
    manifest_path = STEP5_DIR / "phase13_step5_integrity_manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["step"] == "Phase 13 Step 5"
    assert manifest["model_disposition"] == "RESEARCH BASELINE ONLY"
    assert manifest["promotion_to_production_granted"] is False
    assert manifest["commercial_deployment_authorized"] is False
    assert manifest["real_money_trading_authorized"] is False
    assert manifest["partition_classification"] == "PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA"

    # Check hashes of Step 5 artifacts
    for rel_path, expected_hash in manifest["artifact_hashes"].items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"File {rel_path} does not exist"
        actual_hash = compute_sha256(full_path)
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}: {actual_hash} != {expected_hash}"

    # Check upstream manifest hashes
    for rel_path, expected_hash in manifest["upstream_manifest_verifications"].items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.exists(), f"Upstream manifest {rel_path} does not exist"
        actual_hash = compute_sha256(full_path)
        assert actual_hash == expected_hash, f"Upstream manifest hash mismatch for {rel_path}: {actual_hash} != {expected_hash}"


# 3. Decision schema and governance constraints
def test_step5_decision_schema_and_constraints():
    decision_path = STEP5_DIR / "phase13_step5_decision.json"
    with open(decision_path, "r", encoding="utf-8") as f:
        dec = json.load(f)

    assert dec["phase"] == "Phase 13 Step 5"
    assert dec["step_name"] == "Model Promotion Decision Gate & Research Disposition"
    assert dec["formal_decision"]["classification"] == "RESEARCH BASELINE ONLY"
    assert dec["formal_decision"]["is_promoted_to_production"] is False
    assert dec["formal_decision"]["is_eligible_for_real_money_trading"] is False
    assert dec["formal_decision"]["is_retired"] is False
    assert dec["evaluation_dataset"]["exposure_classification"] == "PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA"
    assert dec["evaluation_dataset"]["sample_size"] == 1154
    assert dec["evaluation_dataset"]["period_start"] == "2022-01-03"
    assert dec["evaluation_dataset"]["period_end"] == "2026-09-03"
    assert dec["evaluation_dataset"]["is_genuinely_untouched_confirmatory_holdout"] is False


# 4. Evaluation of all 8 promotion criteria
def test_all_eight_promotion_criteria():
    decision_path = STEP5_DIR / "phase13_step5_decision.json"
    with open(decision_path, "r", encoding="utf-8") as f:
        dec = json.load(f)

    criteria = dec["criteria_assessment"]

    # Criterion 1: Statistical significance
    c1 = criteria["1_statistical_significance"]
    assert c1["passed"] is False

    # Criterion 2: Absolute error vs Zero-return benchmark
    c2 = criteria["2_outperform_zero_return_benchmark"]
    assert c2["passed"] is False

    # Criterion 3: Incremental R2 vs Historical training mean
    c3 = criteria["3_incremental_value_over_training_mean"]
    assert c3["passed"] is False

    # Criterion 4: Directional accuracy vs Always-Short baseline
    c4 = criteria["4_directional_accuracy_over_always_short"]
    assert c4["passed"] is False

    # Criterion 5: Output balance / bias
    c5 = criteria["5_output_distribution_balance"]
    assert c5["passed"] is False

    # Criterion 6: Economic viability under costs
    c6 = criteria["6_economic_viability_under_costs"]
    assert c6["passed"] is False

    # Criterion 7: Prior holdout exposure
    c7 = criteria["7_data_exposure_limitations"]
    assert c7["passed"] is True

    # Criterion 8: Model disposition
    c8 = criteria["8_model_disposition_recommendation"]
    assert c8["recommendation"] == "RETAIN AS RESEARCH BASELINE ONLY"


# 5. Language and disclosure audit in report
def test_language_and_governance_disclosures():
    report_text = (DOCS_DIR / "PHASE_13_STEP5_MODEL_PROMOTION_DECISION.md").read_text(encoding="utf-8")

    assert "PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA" in report_text
    assert "RESEARCH BASELINE ONLY" in report_text
    assert "PRODUCTION PROMOTION:" in report_text and "REJECTED" in report_text
    assert "STRICTLY INELIGIBLE" in report_text or "INELIGIBLE FOR LIVE REAL-MONEY TRADING" in report_text
    assert "UNTOUCHED CONFIRMATORY HOLDOUT" not in report_text
    assert "pristine holdout" not in report_text.lower()
