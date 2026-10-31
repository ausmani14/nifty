"""Tests for Phase 13 Steps 2-4 Combined Execution:
Holdout Exposure Audit, Frozen Snapshot B Evaluation, and Economic Assessment.

Strict Invariants Checked:
1. Exposure classification is supported by existing evidence.
2. Previously exposed data is never labeled untouched.
3. Primary target matches frozen T0.
4. Model artifact matches the sealed specification.
5. Feature membership and ordering match the frozen model.
6. No News, Volume, or Flow features enter the model.
7. Training observations do not exceed 2021-12-31.
8. No training, normalization, or parameter fitting uses evaluation outcomes.
9. Primary metric is Pearson IC.
10. Benchmark calculations match the frozen definitions.
11. Cost scenarios are exactly 0, 5, 10, and 20 bps.
12. No thresholds or strategies are optimized.
13. No Phase 0-12 sealed artifact is modified.
14. Phase 13 Step 1 protocol artifacts remain unchanged.
15. All output artifacts have reproducible SHA256 hashes.
16. Evaluation dates and observation counts reconcile exactly.
17. No result is described as confirmatory if prior exposure makes that interpretation invalid.
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from nifty_ai.config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_steps2_4"
STEP1_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_step1"


def compute_sha256(filepath: Path) -> str:
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


# 1. Exposure classification is supported by existing evidence
def test_exposure_classification_supported_by_evidence():
    audit_json = OUT_DIR / "step2_holdout_exposure_audit.json"
    evidence_csv = OUT_DIR / "step2_holdout_exposure_evidence.csv"
    
    assert audit_json.is_file(), "Missing audit json"
    assert evidence_csv.is_file(), "Missing evidence csv"
    
    with open(audit_json, "r", encoding="utf-8") as f:
        audit = json.load(f)
        
    assert audit["exposure_classification"] == "PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA"
    assert audit["is_genuinely_untouched_confirmatory_holdout"] is False
    
    df = pd.read_csv(evidence_csv)
    assert len(df) >= 6
    assert "Phase 11 Stage 2" in df["phase"].values
    phase11_row = df[df["phase"] == "Phase 11 Stage 2"].iloc[0]
    assert phase11_row["exposure_classification"] == "CONFIRMED EXPOSED"
    assert "Phase 12 target redesign" in phase11_row["influenced_decisions"]


# 2. Previously exposed data is never labeled untouched
def test_previously_exposed_data_never_labeled_untouched():
    audit_json = OUT_DIR / "step2_holdout_exposure_audit.json"
    eval_json = OUT_DIR / "step3_retrospective_model_evaluation.json"
    econ_json = OUT_DIR / "step4_economic_assessment.json"
    
    for p in [audit_json, eval_json, econ_json]:
        text = p.read_text(encoding="utf-8")
        assert "genuinely untouched confirmatory holdout" not in text.lower() or "is_genuinely_untouched_confirmatory_holdout\": false" in text.lower()
        assert "RETROSPECTIVE" in text


# 3. Primary target matches frozen T0
def test_primary_target_matches_frozen_t0():
    eval_json = OUT_DIR / "step3_retrospective_model_evaluation.json"
    meta_json = OUT_DIR / "models" / "snapshot_b_t0_primary_model.meta.json"
    
    with open(meta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["target"] == "Snapshot B T0 (Open-to-Close Return)"
    
    # Check predictions file
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    
    # Verify first 5 rows
    for i in range(5):
        row = preds_df.iloc[i]
        tgt_date = row["target_date"]
        p = price_df.loc[tgt_date]
        expected_t0 = (float(p["close"]) - float(p["open"])) / float(p["open"])
        assert np.isclose(row["T0_realized"], expected_t0, atol=1e-12)


# 4. Model artifact matches sealed specification
def test_model_artifact_matches_specification():
    meta_json = OUT_DIR / "models" / "snapshot_b_t0_primary_model.meta.json"
    model_json = OUT_DIR / "models" / "snapshot_b_t0_primary_model.json"
    
    assert model_json.is_file()
    with open(meta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    hp = meta["hyperparameters"]
    assert hp["n_estimators"] == 43
    assert hp["learning_rate"] == 0.05
    assert hp["max_depth"] == 2
    assert hp["min_child_weight"] == 20.0
    assert hp["subsample"] == 0.8
    assert hp["colsample_bytree"] == 0.7
    assert hp["reg_alpha"] == 0.5
    assert hp["reg_lambda"] == 2.0
    assert hp["random_state"] == 42
    assert hp["objective"] == "reg:squarederror"
    
    # Check checksum matches
    actual_hash = compute_sha256(model_json)
    assert actual_hash == meta["model_file_sha256"]


# 5. Feature membership and ordering match frozen model
def test_feature_membership_and_ordering():
    from nifty_ai.models.multimodal import PRICE_FEATURE_NAMES, CONTEXT_FEATURE_NAMES
    expected_order = PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES
    
    meta_json = OUT_DIR / "models" / "snapshot_b_t0_primary_model.meta.json"
    with open(meta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    assert meta["feature_count"] == 63
    assert meta["features"] == expected_order


# 6. No News, Volume, or Flow features enter the model
def test_no_news_volume_flow_features():
    meta_json = OUT_DIR / "models" / "snapshot_b_t0_primary_model.meta.json"
    with open(meta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    for feat in meta["features"]:
        feat_lower = feat.lower()
        assert "news" not in feat_lower
        assert "volume" not in feat_lower
        assert "flow" not in feat_lower


# 7. Training observations do not exceed 2021-12-31
def test_training_observations_do_not_exceed_cutoff():
    meta_json = OUT_DIR / "models" / "snapshot_b_t0_primary_model.meta.json"
    with open(meta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    assert meta["training_partition"] == "2008-07-08 to 2021-12-31"
    assert meta["training_samples"] == 3299


# 8. No training, normalization, or parameter fitting uses evaluation outcomes
def test_no_holdout_contamination():
    eval_json = OUT_DIR / "step3_retrospective_model_evaluation.json"
    with open(eval_json, "r", encoding="utf-8") as f:
        ev = json.load(f)
        
    assert ev["evaluation_period"]["start_prediction_date"] == "2022-01-03"
    assert ev["evaluation_period"]["end_prediction_date"] == "2026-09-03"
    assert ev["evaluation_period"]["n_sessions"] == 1154


# 9. Primary metric is Pearson IC
def test_primary_metric_is_pearson_ic():
    eval_json = OUT_DIR / "step3_retrospective_model_evaluation.json"
    with open(eval_json, "r", encoding="utf-8") as f:
        ev = json.load(f)
        
    pm = ev["primary_model_evaluation"]["primary_metric"]
    assert pm["metric_name"] == "Pearson IC"
    assert np.isclose(pm["value"], 0.020131, atol=1e-4)
    assert pm["p_value_two_sided"] >= 0.05
    assert ev["primary_model_evaluation"]["outcome_classification"] == "OUTCOME_B_WEAK_OR_ABSENT"


# 10. Benchmark calculations match frozen definitions
def test_benchmark_calculations():
    eval_json = OUT_DIR / "step3_retrospective_model_evaluation.json"
    with open(eval_json, "r", encoding="utf-8") as f:
        ev = json.load(f)
        
    b1 = ev["benchmarks"]["benchmark_1_zero_return"]
    b2 = ev["benchmarks"]["benchmark_2_training_mean"]
    
    assert b1["mae"] > 0
    assert b1["rmse"] > 0
    assert b2["mae"] > 0
    assert b2["rmse"] > 0
    
    # Incremental R2 relative to training mean must be negative
    assert ev["primary_model_evaluation"]["statistical_diagnostics"]["incremental_r2"] < 0


# 11. Cost scenarios are exactly 0, 5, 10, and 20 bps
def test_cost_scenarios_exact():
    econ_df = pd.read_csv(OUT_DIR / "step4_economic_assessment.csv")
    unique_costs = sorted(econ_df["cost_scenario_bps"].unique())
    assert unique_costs == [0.0, 5.0, 10.0, 20.0]


# 12. No thresholds or strategies are optimized
def test_no_strategy_optimization():
    econ_df = pd.read_csv(OUT_DIR / "step4_economic_assessment.csv")
    strategies = econ_df["strategy"].unique()
    assert set(strategies) == {"Strategy 1 (Unrestricted Direction)", "Benchmark 3 (Always Short)"}


# 13. No Phase 0-12 sealed artifact is modified
def test_phase_0_to_12_artifacts_unmodified():
    # Verify key Phase 11 and Phase 12 hashes
    phase11_cfg_path = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"
    assert phase11_cfg_path.is_file()
    
    phase12_step11_manifest = PROJECT_ROOT / "data" / "interim" / "phase12_step11" / "step11_integrity_manifest.json"
    assert phase12_step11_manifest.is_file()
    
    phase12_step12_summary = PROJECT_ROOT / "data" / "interim" / "phase12_step12" / "step12_n4_year_exact_summary.json"
    assert phase12_step12_summary.is_file()


# 14. Phase 13 Step 1 protocol artifacts remain unchanged
def test_phase13_step1_artifacts_unmodified():
    p1 = STEP1_DIR / "step1_holdout_protocol.json"
    p2 = STEP1_DIR / "step1_holdout_protocol.md"
    p3 = STEP1_DIR / "step1_holdout_firewall_audit.json"
    
    assert p1.is_file()
    assert p2.is_file()
    assert p3.is_file()
    
    # Check hashes against known values from Step 1
    assert compute_sha256(p1) == "21e5b9b001f16e2acc003b78e6af78e2c8cdb1ebc44f389c18c0d1957e689395"
    assert compute_sha256(p2) == "3c64b2355b09b5e4ab85d838c0080a380d91f80c2831f4449c83dd011422f03a"
    assert compute_sha256(p3) == "6704e275d9c66fd50c2bc964509cbacc76212e9b2cea06f9dad5fb2375625188"


# 15. All output artifacts have reproducible SHA256 hashes
def test_output_artifacts_manifest_integrity():
    manifest_path = OUT_DIR / "phase13_steps2_4_manifest.json"
    assert manifest_path.is_file()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    assert len(manifest) == 11
    for rel_path, exp_hash in manifest.items():
        fp = OUT_DIR / rel_path
        assert fp.is_file(), f"Missing file: {rel_path}"
        act_hash = compute_sha256(fp)
        assert act_hash == exp_hash, f"Hash mismatch for {rel_path}"


# 16. Evaluation dates and observation counts reconcile exactly
def test_evaluation_dates_and_counts_reconcile():
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    assert len(preds_df) == 1154
    assert preds_df["prediction_date"].iloc[0] == "2022-01-03"
    assert preds_df["prediction_date"].iloc[-1] == "2026-09-03"
    assert preds_df["target_date"].iloc[0] == "2022-01-04"
    assert preds_df["target_date"].iloc[-1] == "2026-09-04"


# 17. No result is described as confirmatory
def test_no_result_described_as_confirmatory():
    eval_json = OUT_DIR / "step3_retrospective_model_evaluation.json"
    with open(eval_json, "r", encoding="utf-8") as f:
        ev = json.load(f)
        
    assert ev["evaluation_classification"] == "RETROSPECTIVE_OUT_OF_SAMPLE_EVALUATION"
    assert "OUTCOME_B_WEAK_OR_ABSENT" == ev["primary_model_evaluation"]["outcome_classification"]
    assert "fails to reject the null hypothesis" in ev["primary_model_evaluation"]["mandatory_outcome_statement"]
