"""Unit and forensic validation test suite for Phase 12 Step 10: Information-Set Reconstruction & Signal Attribution Audit.

Requirements Verified:
1. Exact 63-feature registry
2. Exact P0/P1/P2/P3 membership
3. Deterministic R1/R2/R3 membership
4. Every feature has an inclusion and exclusion reason
5. No performance-based membership logic
6. XGBoost model family only
7. Zero LightGBM
8. Zero News features
9. Zero Volume features
10. Zero Flow proxy features
11. Exact OOF population (N=1,960, 2014-2021)
12. Chronological 8 folds
13. Fold-local training (mu_train computed on training fold only)
14. Frozen hyperparameters (depth=2, lr=0.05, min_child_weight=20, etc.)
15. Frozen target (open-to-close return)
16. Placebo test integrity (1,000 permutations, seed=42)
17. Economic diagnostic integrity (0, 5, 10, 15, 20 bps + Always Short)
18. Terminal holdout firewall strictly quarantined (no date >= 2022-01-03)
19. Upstream artifact immutability (Phase 4-10, Step 5, 6, 7, 8, 9 hashes verified)
20. Artifact checksum integrity (all Step 10 artifacts match manifest)
21. Macro context forensic audit (G8_MACRO_CTX completely excluded from R2 and R3)
22. Information-set delta consistency
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step10"
MANIFEST_PATH = DATA_DIR / "step10_integrity_manifest.json"
INFO_SETS_CSV = DATA_DIR / "step10_information_sets.csv"
INFO_SETS_JSON = DATA_DIR / "step10_information_sets.json"
PREDICTIONS_CSV = DATA_DIR / "step10_predictions.csv"
FOLD_RESULTS_CSV = DATA_DIR / "step10_fold_results.csv"
TEMPORAL_RESULTS_CSV = DATA_DIR / "step10_temporal_results.csv"
SUMMARY_CSV = DATA_DIR / "step10_summary.csv"
FAMILY_MAPPING_CSV = DATA_DIR / "step10_feature_family_mapping.csv"
MACRO_FORENSIC_CSV = DATA_DIR / "step10_macro_forensic.csv"
PLACEBO_CSV = DATA_DIR / "step10_placebo_results.csv"
ECON_DIAGNOSTIC_CSV = DATA_DIR / "step10_economic_diagnostic.csv"


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.is_file(), f"Missing manifest: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def df_info():
    assert INFO_SETS_CSV.is_file(), f"Missing info sets CSV: {INFO_SETS_CSV}"
    return pd.read_csv(INFO_SETS_CSV)


@pytest.fixture(scope="module")
def df_preds():
    assert PREDICTIONS_CSV.is_file(), f"Missing predictions CSV: {PREDICTIONS_CSV}"
    return pd.read_csv(PREDICTIONS_CSV)


@pytest.fixture(scope="module")
def df_folds():
    assert FOLD_RESULTS_CSV.is_file(), f"Missing fold results CSV: {FOLD_RESULTS_CSV}"
    return pd.read_csv(FOLD_RESULTS_CSV)


@pytest.fixture(scope="module")
def df_summary():
    assert SUMMARY_CSV.is_file(), f"Missing summary CSV: {SUMMARY_CSV}"
    return pd.read_csv(SUMMARY_CSV)


@pytest.fixture(scope="module")
def df_macro():
    assert MACRO_FORENSIC_CSV.is_file(), f"Missing macro forensic CSV: {MACRO_FORENSIC_CSV}"
    return pd.read_csv(MACRO_FORENSIC_CSV)


@pytest.fixture(scope="module")
def df_family():
    assert FAMILY_MAPPING_CSV.is_file(), f"Missing family mapping CSV: {FAMILY_MAPPING_CSV}"
    return pd.read_csv(FAMILY_MAPPING_CSV)


@pytest.fixture(scope="module")
def df_placebo():
    assert PLACEBO_CSV.is_file(), f"Missing placebo CSV: {PLACEBO_CSV}"
    return pd.read_csv(PLACEBO_CSV)


@pytest.fixture(scope="module")
def df_econ():
    assert ECON_DIAGNOSTIC_CSV.is_file(), f"Missing economic diagnostic CSV: {ECON_DIAGNOSTIC_CSV}"
    return pd.read_csv(ECON_DIAGNOSTIC_CSV)


# Test 1: Exact 63-Feature Registry
def test_exact_63_feature_registry(df_info):
    assert len(df_info) == 63
    assert df_info["feature_name"].nunique() == 63
    expected_cols = [
        "feature_name", "feature_family", "P0", "P1", "P2", "P3", "R1", "R2", "R3",
        "inclusion_reason", "exclusion_reason", "PIT_basis", "revision_status", "timestamp_basis"
    ]
    assert list(df_info.columns) == expected_cols


# Test 2: Exact P0/P1/P2/P3 Membership
def test_exact_p0_p1_p2_p3_membership(df_info):
    assert int(df_info["P0"].sum()) == 45
    assert int(df_info["P1"].sum()) == 63
    assert int(df_info["P2"].sum()) == 56
    assert int(df_info["P3"].sum()) == 53
    # P0 must have 0 context features
    assert not any(df_info[df_info["feature_name"].str.startswith("ctx_")]["P0"])


# Test 3: Deterministic R1/R2/R3 Membership
def test_deterministic_r1_r2_r3_membership(df_info):
    assert int(df_info["R1"].sum()) == 63
    assert int(df_info["R2"].sum()) == 56
    assert int(df_info["R3"].sum()) == 53
    # R1 includes all 18 context features based on timestamp cutoff (< 08:50 IST)
    assert int(df_info[df_info["feature_name"].str.startswith("ctx_")]["R1"].sum()) == 18
    # R2 includes only 11 cash exchange equity/volatility context features
    assert int(df_info[df_info["feature_name"].str.startswith("ctx_")]["R2"].sum()) == 11
    # R3 includes only 8 domestic + US overnight equity/volatility context features
    assert int(df_info[df_info["feature_name"].str.startswith("ctx_")]["R3"].sum()) == 8


# Test 4: Every Feature Has Inclusion and Exclusion Reason
def test_every_feature_has_reason(df_info):
    for _, row in df_info.iterrows():
        assert pd.notna(row["inclusion_reason"]) and len(str(row["inclusion_reason"]).strip()) > 0
        assert pd.notna(row["exclusion_reason"]) and len(str(row["exclusion_reason"]).strip()) > 0
        assert pd.notna(row["PIT_basis"]) and len(str(row["PIT_basis"]).strip()) > 0
        assert pd.notna(row["revision_status"]) and len(str(row["revision_status"]).strip()) > 0
        assert pd.notna(row["timestamp_basis"]) and len(str(row["timestamp_basis"]).strip()) > 0


# Test 5: No Performance-Based Membership Logic
def test_no_performance_based_membership_logic(df_info):
    forbidden_terms = ["ic", "sharpe", "p-value", "performance", "best", "optimal", "alpha", "edge", "profit"]
    for _, row in df_info.iterrows():
        inc = str(row["inclusion_reason"]).lower()
        exc = str(row["exclusion_reason"]).lower()
        for term in forbidden_terms:
            assert f" {term} " not in f" {inc} ", f"Performance term '{term}' found in inclusion reason: {inc}"
            assert f" {term} " not in f" {exc} ", f"Performance term '{term}' found in exclusion reason: {exc}"


# Test 6: XGBoost Model Family Only
def test_xgboost_model_family_only(manifest):
    assert manifest["model_family"] == "xgboost.XGBRegressor"
    models_eval = [m["code"] for m in manifest["models_evaluated"]]
    assert len(models_eval) == 7
    expected_models = [
        "P0_PRICE_ONLY", "P1_ORIGINAL_PIT", "P2_CONSERVATIVE_PIT", "P3_STRICT_PIT",
        "R1_OVERNIGHT_AVAILABLE", "R2_CONSERVATIVE_ECONOMIC", "R3_DOMESTIC_UNAMBIGUOUS"
    ]
    assert models_eval == expected_models


# Test 7: Zero LightGBM
def test_zero_lightgbm():
    script_content = (PROJECT_ROOT / "scripts" / "phase12_step10_reconstruction.py").read_text(encoding="utf-8")
    code_lines = [
        line.strip().lower()
        for line in script_content.splitlines()
        if not line.strip().startswith("#") and not line.strip().startswith('"') and not line.strip().startswith("*") and not line.strip().startswith("-")
    ]
    for l in code_lines:
        assert "import lightgbm" not in l
        assert "import lgb" not in l
        assert "lightgbm." not in l
        assert "lgb." not in l


# Test 8: Zero News
def test_zero_news(df_info):
    assert not any("news" in fn.lower() for fn in df_info["feature_name"])
    assert not any("sentiment" in fn.lower() for fn in df_info["feature_name"])


# Test 9: Zero Volume
def test_zero_volume(df_info):
    assert not any("volume" in fn.lower() for fn in df_info["feature_name"])
    assert not any("turnover" in fn.lower() for fn in df_info["feature_name"])


# Test 10: Zero Flow Proxies
def test_zero_flow(df_info):
    assert not any("fii" in fn.lower() for fn in df_info["feature_name"])
    assert not any("dii" in fn.lower() for fn in df_info["feature_name"])
    assert not any("flow" in fn.lower() for fn in df_info["feature_name"])


# Test 11: Exact OOF Population
def test_exact_oof_population(df_preds):
    assert len(df_preds) == 1960
    assert df_preds["trading_date"].min() == "2014-01-02"
    assert df_preds["trading_date"].max() == "2021-12-31"


# Test 12: Chronological Folds
def test_chronological_folds(df_folds):
    assert len(df_folds) == 56  # 8 folds x 7 models
    for m in df_folds["model_code"].unique():
        sub = df_folds[df_folds["model_code"] == m].sort_values("fold_id")
        assert len(sub) == 8
        years = list(sub["val_year"])
        assert years == list(range(2014, 2022))


# Test 13: Fold-Local Training
def test_fold_local_training(df_folds, df_preds):
    for f_id in range(1, 9):
        f_sub = df_folds[df_folds["fold_id"] == f_id]
        mu_folds = f_sub["mu_train_bps"].values
        assert np.allclose(mu_folds, mu_folds[0]), f"mu_train differs across models in fold {f_id}"
        p_sub = df_preds[df_preds["fold_id"] == f_id]
        assert np.allclose(p_sub["mu_train"].values * 10000.0, mu_folds[0])


# Test 14: Frozen Hyperparameters
def test_frozen_hyperparameters():
    script_content = (PROJECT_ROOT / "scripts" / "phase12_step10_reconstruction.py").read_text(encoding="utf-8")
    assert '"learning_rate": 0.05' in script_content
    assert '"max_depth": 2' in script_content
    assert '"min_child_weight": 20.0' in script_content
    assert '"subsample": 0.8' in script_content
    assert '"colsample_bytree": 0.7' in script_content
    assert '"reg_alpha": 0.5' in script_content
    assert '"reg_lambda": 2.0' in script_content


# Test 15: Frozen Target
def test_frozen_target(df_preds):
    assert "realized_intraday_return" in df_preds.columns
    assert "residual_realized_return" in df_preds.columns
    diff = df_preds["realized_intraday_return"] - df_preds["mu_train"]
    assert np.allclose(diff.values, df_preds["residual_realized_return"].values)


# Test 16: Placebo Integrity
def test_placebo_integrity(df_placebo):
    assert len(df_placebo) == 7
    assert (df_placebo["n_permutations"] == 1000).all()
    assert (df_placebo["seed"] == 42).all()
    assert (df_placebo["placebo_mean_ic"].abs() < 0.01).all()


# Test 17: Economic Diagnostic Integrity
def test_economic_diagnostic_integrity(df_econ):
    expected_models = [
        "P0_PRICE_ONLY", "P1_ORIGINAL_PIT", "P2_CONSERVATIVE_PIT", "P3_STRICT_PIT",
        "R1_OVERNIGHT_AVAILABLE", "R2_CONSERVATIVE_ECONOMIC", "R3_DOMESTIC_UNAMBIGUOUS",
        "ALWAYS_SHORT"
    ]
    assert set(df_econ["model_code"].unique()) == set(expected_models)
    assert set(df_econ["cost_bps"].unique()) == {0.0, 5.0, 10.0, 15.0, 20.0}
    assert len(df_econ) == 8 * 5  # 8 models x 5 costs = 40 rows


# Test 18: Terminal Holdout Firewall
def test_terminal_holdout_firewall(manifest, df_preds):
    assert manifest["holdout_firewall"]["terminal_holdout_quarantined"] is True
    assert manifest["holdout_firewall"]["holdout_sessions_accessed"] == 0
    max_d = df_preds["trading_date"].max()
    assert max_d <= "2021-12-31"
    assert not any(df_preds["trading_date"] >= "2022-01-03")


# Test 19: Upstream Artifact Immutability
def test_upstream_artifact_immutability():
    from scripts.phase12_step10_reconstruction import verify_protected_checksums
    verify_protected_checksums()


# Test 20: Artifact Checksum Integrity
def test_artifact_checksum_integrity(manifest):
    for fn, exp_hash in manifest["file_hashes"].items():
        fp = DATA_DIR / fn
        assert fp.is_file(), f"Missing Step 10 artifact: {fn}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for {fn}!\nExp: {exp_hash}\nAct: {act_hash}"


# Test 21: Macro Context Forensic Audit
def test_macro_context_forensic_audit(df_macro):
    assert len(df_macro) == 5
    expected_macro = [
        "ctx_ret_1d_brent_crude", "ctx_ret_1d_wti_crude", "ctx_ret_1d_gold",
        "ctx_ret_1d_dxy", "ctx_diff_1d_us_10y_yield"
    ]
    assert list(df_macro["feature_name"]) == expected_macro
    assert (df_macro["in_P1"] == True).all()
    assert (df_macro["survives_R1"] == True).all()
    assert (df_macro["survives_R2"] == False).all()
    assert (df_macro["survives_R3"] == False).all()


# Test 22: Information-Set Delta Consistency
def test_information_set_deltas(df_summary):
    assert len(df_summary) == 7
    p1_row = df_summary[df_summary["model_code"] == "P1_ORIGINAL_PIT"].iloc[0]
    r1_row = df_summary[df_summary["model_code"] == "R1_OVERNIGHT_AVAILABLE"].iloc[0]
    p2_row = df_summary[df_summary["model_code"] == "P2_CONSERVATIVE_PIT"].iloc[0]
    r2_row = df_summary[df_summary["model_code"] == "R2_CONSERVATIVE_ECONOMIC"].iloc[0]
    p3_row = df_summary[df_summary["model_code"] == "P3_STRICT_PIT"].iloc[0]
    r3_row = df_summary[df_summary["model_code"] == "R3_DOMESTIC_UNAMBIGUOUS"].iloc[0]

    # R1 and P1 share the exact same 63 features
    assert np.isclose(p1_row["residual_pearson_ic"], r1_row["residual_pearson_ic"])
    # R2 and P2 share the exact same 56 features
    assert np.isclose(p2_row["residual_pearson_ic"], r2_row["residual_pearson_ic"])
    # R3 and P3 share the exact same 53 features
    assert np.isclose(p3_row["residual_pearson_ic"], r3_row["residual_pearson_ic"])
