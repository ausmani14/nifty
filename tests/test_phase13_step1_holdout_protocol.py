"""Forensic validation test suite for Phase 13 Step 1: Untouched Holdout Evaluation Protocol Freeze.

Pre-Registered Assertions:
1. Phase 12 sealed artifacts remain bitwise unchanged.
2. Primary target is exactly T0 Open-to-Close return.
3. 63-feature model specification is frozen (45 Price + 18 Context).
4. News features are strictly excluded.
5. Volume features are strictly excluded.
6. Flow features are strictly excluded.
7. XGBoost configuration matches sealed specification.
8. Primary metric is Pearson IC.
9. Holdout start remains 2022-01-01 (first trading date 2022-01-03).
10. Development/OOF cutoff remains 2021-12-31.
11. No holdout rows are loaded (holdout_rows_accessed == 0).
12. No holdout metrics exist in Step 1 artifacts.
13. No holdout-derived parameters exist in Step 1 artifacts.
14. No strategy optimization is performed.
15. Protocol is deterministic and structured.
16. Protocol hash is reproducible on disk.
17. All 67+ protected upstream hashes remain bitwise unchanged.
18. Training policy is explicitly locked to Option A (Frozen historical models).
19. Benchmarks are strictly pre-registered (Zero, Historical Mean, Always Short).
20. Interpretation framework strictly follows Outcomes A, B, C with negative constraints.
"""

from datetime import date
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.models.multimodal import CONTEXT_FEATURE_NAMES, PRICE_FEATURE_NAMES

STEP1_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_step1"
PROTOCOL_JSON = STEP1_DIR / "step1_holdout_protocol.json"
PROTOCOL_MD = STEP1_DIR / "step1_holdout_protocol.md"
FIREWALL_JSON = STEP1_DIR / "step1_holdout_firewall_audit.json"
MANIFEST_JSON = STEP1_DIR / "step1_integrity_manifest.json"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"


@pytest.fixture(scope="module")
def protocol_data() -> Dict[str, Any]:
    assert PROTOCOL_JSON.is_file(), f"Missing protocol JSON: {PROTOCOL_JSON}"
    with open(PROTOCOL_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def firewall_data() -> Dict[str, Any]:
    assert FIREWALL_JSON.is_file(), f"Missing firewall JSON: {FIREWALL_JSON}"
    with open(FIREWALL_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def manifest_data() -> Dict[str, Any]:
    assert MANIFEST_JSON.is_file(), f"Missing manifest JSON: {MANIFEST_JSON}"
    with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def test_phase12_artifacts_unchanged():
    """Assertion 1: Phase 12 sealed artifacts remain bitwise unchanged."""
    from scripts.phase13_step1_holdout_protocol_freeze import (
        PROTECTED_STEP12_HASHES,
        STEP12_DIR,
    )

    for fn, exp_hash in PROTECTED_STEP12_HASHES.items():
        fp = STEP12_DIR / fn
        assert fp.is_file(), f"Missing Step 12 artifact: {fn}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 12 artifact {fn}"


def test_primary_target_is_t0(protocol_data):
    """Assertion 2: Primary target is exactly T0 Open->Close."""
    tgt = protocol_data["target_specification"]
    assert tgt["primary_target_id"] == "T0"
    assert "Close(T+1) - Open(T+1)" in tgt["mathematical_formula"]
    assert tgt["is_primary"] is True
    assert tgt["information_cutoff_timestamp"] == "08:50 IST (Session T+1)"
    assert tgt["execution_entry_timestamp"] == "09:15 IST (Session T+1 Open)"
    assert tgt["execution_exit_timestamp"] == "15:30 IST (Session T+1 Close)"


def test_63_feature_model_specification_frozen(protocol_data):
    """Assertion 3: 63-feature model specification is frozen."""
    feats = protocol_data["feature_specification"]
    assert feats["total_feature_count"] == 63
    assert feats["price_feature_count"] == 45
    assert feats["context_feature_count"] == 18
    assert len(feats["price_features"]) == 45
    assert len(feats["context_features"]) == 18
    assert set(feats["price_features"]) == set(PRICE_FEATURE_NAMES)
    assert set(feats["context_features"]) == set(CONTEXT_FEATURE_NAMES)


def test_news_excluded(protocol_data):
    """Assertion 4: News features are excluded."""
    assert protocol_data["feature_specification"]["news_features_included"] is False


def test_volume_excluded(protocol_data):
    """Assertion 5: Volume features are excluded."""
    assert protocol_data["feature_specification"]["volume_features_included"] is False


def test_flow_excluded(protocol_data):
    """Assertion 6: Flow features are excluded."""
    assert protocol_data["feature_specification"]["flow_features_included"] is False


def test_xgboost_configuration_matches_sealed_spec(protocol_data):
    """Assertion 7: XGBoost configuration matches sealed specification."""
    model_spec = protocol_data["model_specification"]
    assert model_spec["architecture"] == "xgboost.XGBRegressor"
    hp = model_spec["hyperparameters"]
    assert hp["objective"] == "reg:squarederror"
    assert hp["learning_rate"] == 0.05
    assert hp["max_depth"] == 2
    assert hp["min_child_weight"] == 20.0
    assert hp["subsample"] == 0.8
    assert hp["colsample_bytree"] == 0.7
    assert hp["reg_alpha"] == 0.5
    assert hp["reg_lambda"] == 2.0
    assert hp["random_state"] == 42
    assert model_spec["primary_model"]["n_estimators"] == 43


def test_primary_metric_is_pearson_ic(protocol_data):
    """Assertion 8: Primary metric is Pearson IC."""
    primary_m = protocol_data["evaluation_metrics"]["primary_metric"]
    assert primary_m["name"] == "Pearson Correlation (IC)"
    assert primary_m["symbol"] == "r_p"
    assert protocol_data["multiple_testing_rule"]["sole_primary_endpoint"] == "Snapshot B T0 Pearson IC"


def test_holdout_start_remains_2022_01_01(protocol_data, firewall_data):
    """Assertion 9: Holdout start remains 2022-01-01 / 2022-01-03."""
    assert firewall_data["boundary_verification"]["holdout_start_date"] == "2022-01-01"
    assert protocol_data["governance"]["terminal_holdout_partition"]["start_date"] == "2022-01-03"


def test_oof_cutoff_remains_2021_12_31(protocol_data, firewall_data):
    """Assertion 10: OOF / Development cutoff remains 2021-12-31."""
    assert protocol_data["governance"]["max_development_cutoff"] == "2021-12-31"
    assert firewall_data["boundary_verification"]["development_max_date"] == "2021-12-31"


def test_no_holdout_rows_loaded(protocol_data, firewall_data, manifest_data):
    """Assertion 11: No holdout rows are loaded (holdout_rows_accessed == 0)."""
    assert protocol_data["governance"]["holdout_rows_accessed"] == 0
    assert firewall_data["boundary_verification"]["holdout_rows_accessed"] == 0
    assert manifest_data["firewall_verification"]["holdout_rows_accessed"] == 0
    assert firewall_data["checks"]["no_holdout_rows_loaded"] is True


def test_no_holdout_metrics_exist(protocol_data, firewall_data, manifest_data):
    """Assertion 12: No holdout metrics exist in Step 1 artifacts."""
    assert manifest_data["protocol_summary"]["holdout_metrics_computed"] == 0
    assert firewall_data["checks"]["no_holdout_metrics_computed"] is True
    assert firewall_data["code_access_audit"]["step1_artifacts_contain_holdout_metrics"] is False


def test_no_holdout_derived_parameters_exist(firewall_data):
    """Assertion 13: No holdout-derived parameters exist."""
    assert firewall_data["checks"]["no_holdout_derived_feature_statistics"] is True
    assert firewall_data["checks"]["no_holdout_derived_normalization"] is True
    assert firewall_data["checks"]["no_holdout_derived_threshold"] is True
    assert firewall_data["checks"]["no_holdout_derived_hyperparameters"] is True
    assert firewall_data["checks"]["no_holdout_derived_model_selection"] is True


def test_no_strategy_optimization_performed(protocol_data, firewall_data):
    """Assertion 14: No strategy optimization is performed."""
    assert firewall_data["checks"]["no_strategy_optimization_conducted"] is True
    econ = protocol_data["evaluation_metrics"]["secondary_economic_diagnostics"]
    assert "Strategy 1: Unrestricted Direction" in econ["strategy_rule"]
    assert "not optimization targets" in econ["role"].lower()
    assert "descriptive feasibility diagnostics" in econ["role"].lower()


def test_protocol_deterministic_and_structured(protocol_data):
    """Assertion 15: Protocol is deterministic, structured, and complete."""
    assert protocol_data["protocol_version"] == "1.0.0"
    assert "governance" in protocol_data
    assert "target_specification" in protocol_data
    assert "feature_specification" in protocol_data
    assert "model_specification" in protocol_data
    assert "evaluation_metrics" in protocol_data
    assert "benchmarks" in protocol_data
    assert "statistical_interpretation_framework" in protocol_data
    assert "multiple_testing_rule" in protocol_data
    assert "firewall_requirements" in protocol_data


def test_protocol_hash_reproducible(manifest_data):
    """Assertion 16: Protocol hash is reproducible on disk and matches manifest."""
    for fn, exp_hash in manifest_data["artifact_hashes"].items():
        fp = STEP1_DIR / fn
        assert fp.is_file(), f"Missing Step 1 artifact: {fn}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 1 artifact {fn}"


def test_protected_upstream_hashes_unchanged():
    """Assertion 17: All protected upstream hashes remain bitwise unchanged."""
    from scripts.phase13_step1_holdout_protocol_freeze import (
        PROTECTED_STEP5_HASHES,
        PROTECTED_STEP6_HASHES,
        PROTECTED_STEP7_HASHES,
        PROTECTED_STEP8_HASHES,
        PROTECTED_STEP9_HASHES,
        PROTECTED_STEP10_HASHES,
        PROTECTED_STEP11_HASHES,
        PROTECTED_STEP12_HASHES,
        PHASE12_DIR,
        STEP7_DIR,
        STEP8_DIR,
        STEP9_DIR,
        STEP10_DIR,
        STEP11_DIR,
        STEP12_DIR,
    )

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Missing file: {rel_path}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for {rel_path}"

    for dir_p, h_dict in [
        (PHASE12_DIR, PROTECTED_STEP5_HASHES),
        (PHASE12_DIR, PROTECTED_STEP6_HASHES),
        (STEP7_DIR, PROTECTED_STEP7_HASHES),
        (STEP8_DIR, PROTECTED_STEP8_HASHES),
        (STEP9_DIR, PROTECTED_STEP9_HASHES),
        (STEP10_DIR, PROTECTED_STEP10_HASHES),
        (STEP11_DIR, PROTECTED_STEP11_HASHES),
        (STEP12_DIR, PROTECTED_STEP12_HASHES),
    ]:
        for fn, exp_hash in h_dict.items():
            fp = dir_p / fn
            assert fp.is_file(), f"Missing: {fn}"
            act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
            assert act_hash == exp_hash, f"Hash mismatch for {fn}"


def test_training_policy_option_a(protocol_data):
    """Assertion 18: Training policy is explicitly locked to Option A."""
    policy = protocol_data["model_specification"]["training_policy"]
    assert "Option A" in policy
    assert "Frozen historical models" in policy
    assert protocol_data["model_specification"]["primary_model"]["training_sessions"] == 3299
    assert protocol_data["model_specification"]["primary_model"]["n_estimators"] == 43


def test_benchmarks_strictly_pre_registered(protocol_data):
    """Assertion 19: Benchmarks are strictly pre-registered."""
    bm = protocol_data["benchmarks"]
    assert "Benchmark 1" in bm
    assert "Zero-Return Predictor" in bm["Benchmark 1"]["name"]
    assert "Benchmark 2" in bm
    assert "Historical Training Mean Predictor" in bm["Benchmark 2"]["name"]
    assert "Benchmark 3" in bm
    assert "Always Short Benchmark" in bm["Benchmark 3"]["name"]


def test_interpretation_framework_outcomes(protocol_data):
    """Assertion 20: Interpretation framework strictly follows Outcomes A, B, C with negative constraints."""
    framework = protocol_data["statistical_interpretation_framework"]
    assert "Outcome A" in framework
    assert "directionally consistent with the historical OOF relationship" in framework["Outcome A"]["mandatory_statement"]
    assert "Outcome B" in framework
    assert "did not reproduce strongly in the untouched holdout" in framework["Outcome B"]["mandatory_statement"]
    assert "Outcome C" in framework
    assert "is inconsistent with the historical OOF relationship" in framework["Outcome C"]["mandatory_statement"]
    neg_rules = framework["negative_constraints"]
    assert any("proof of future persistence" in r for r in neg_rules)
    assert any("commercial trading viability" in r for r in neg_rules)
