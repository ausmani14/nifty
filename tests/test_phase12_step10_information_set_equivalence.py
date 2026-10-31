"""Forensic Information-Set Equivalence Test Suite for Phase 12 Step 10.

Verifies:
1. Exact 63-feature universe in step10_PR_equivalence_matrix.csv
2. P1 and R1 exact equality check (P1 == R1)
3. P2 and R2 exact equality check (P2 == R2)
4. P3 and R3 exact equality check (P3 == R3)
5. Jaccard similarity correctness (1.0 for all P/R pairs)
6. No missing feature rows (all 63 features present, zero null values)
7. Five Macro features explicitly audited (survival in R2/R3 = 0/5)
8. R-set construction independent of model performance (pure provenance/timing basis)
9. Zero IC-based membership logic
10. Zero p-value-based membership logic
11. Zero placebo-based membership logic
12. Zero return-based membership logic
13. Zero feature-importance-based membership logic
14. XGBoost model family only
15. Zero LightGBM in implementation
16. Terminal holdout firewall strictly maintained
17. Upstream artifact immutability (Phase 4-10, Step 5, 6, 7, 8, 9)
18. Artifact checksum integrity for step10_PR_equivalence_matrix.csv and all Step 10 artifacts
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step10"
EQUIV_CSV = DATA_DIR / "step10_PR_equivalence_matrix.csv"
INFO_CSV = DATA_DIR / "step10_information_sets.csv"
MANIFEST_PATH = DATA_DIR / "step10_integrity_manifest.json"
PREDICTIONS_CSV = DATA_DIR / "step10_predictions.csv"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "phase12_step10_reconstruction.py"


@pytest.fixture(scope="module")
def df_equiv():
    assert EQUIV_CSV.is_file(), f"Missing equivalence CSV: {EQUIV_CSV}"
    return pd.read_csv(EQUIV_CSV)


@pytest.fixture(scope="module")
def df_info():
    assert INFO_CSV.is_file(), f"Missing info CSV: {INFO_CSV}"
    return pd.read_csv(INFO_CSV)


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.is_file(), f"Missing manifest: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Test 1: Exact 63-Feature Universe
def test_exact_63_feature_universe(df_equiv):
    assert len(df_equiv) == 63
    assert df_equiv["feature_name"].nunique() == 63
    expected_cols = [
        "feature_name", "feature_family", "P1_included", "R1_included", "P1_equals_R1",
        "P2_included", "R2_included", "P2_equals_R2", "P3_included", "R3_included",
        "P3_equals_R3", "P1_R1_reason", "P2_R2_reason", "P3_R3_reason"
    ]
    assert list(df_equiv.columns) == expected_cols


# Test 2: P1 vs R1 Exact Equality Check
def test_p1_r1_exact_equality(df_equiv):
    p1_set = set(df_equiv[df_equiv["P1_included"] == True]["feature_name"])
    r1_set = set(df_equiv[df_equiv["R1_included"] == True]["feature_name"])
    assert len(p1_set) == 63
    assert len(r1_set) == 63
    assert p1_set == r1_set
    assert df_equiv["P1_equals_R1"].all()


# Test 3: P2 vs R2 Exact Equality Check
def test_p2_r2_exact_equality(df_equiv):
    p2_set = set(df_equiv[df_equiv["P2_included"] == True]["feature_name"])
    r2_set = set(df_equiv[df_equiv["R2_included"] == True]["feature_name"])
    assert len(p2_set) == 56
    assert len(r2_set) == 56
    assert p2_set == r2_set
    assert df_equiv["P2_equals_R2"].all()


# Test 4: P3 vs R3 Exact Equality Check
def test_p3_r3_exact_equality(df_equiv):
    p3_set = set(df_equiv[df_equiv["P3_included"] == True]["feature_name"])
    r3_set = set(df_equiv[df_equiv["R3_included"] == True]["feature_name"])
    assert len(p3_set) == 53
    assert len(r3_set) == 53
    assert p3_set == r3_set
    assert df_equiv["P3_equals_R3"].all()


# Test 5: Jaccard Similarity Correctness (1.0 for all pairs)
def test_jaccard_correctness(df_equiv):
    for pair, p_col, r_col in [("P1/R1", "P1_included", "R1_included"),
                                ("P2/R2", "P2_included", "R2_included"),
                                ("P3/R3", "P3_included", "R3_included")]:
        p = set(df_equiv[df_equiv[p_col] == True]["feature_name"])
        r = set(df_equiv[df_equiv[r_col] == True]["feature_name"])
        jaccard = len(p.intersection(r)) / len(p.union(r))
        assert np.isclose(jaccard, 1.0), f"Jaccard similarity for {pair} is {jaccard} != 1.0"


# Test 6: No Missing Feature Rows or Null Values
def test_no_missing_feature_rows(df_equiv):
    assert df_equiv.isna().sum().sum() == 0
    for col in ["P1_R1_reason", "P2_R2_reason", "P3_R3_reason"]:
        assert (df_equiv[col].str.len() > 10).all()


# Test 7: Five Macro Features Explicitly Audited
def test_five_macro_features_audited(df_equiv):
    macro_features = [
        "ctx_ret_1d_brent_crude", "ctx_ret_1d_wti_crude", "ctx_ret_1d_gold",
        "ctx_ret_1d_dxy", "ctx_diff_1d_us_10y_yield"
    ]
    df_macro = df_equiv[df_equiv["feature_name"].isin(macro_features)]
    assert len(df_macro) == 5
    # In P1 and R1: included
    assert (df_macro["P1_included"] == True).all()
    assert (df_macro["R1_included"] == True).all()
    # In P2, R2, P3, R3: completely excluded (0/5 survive)
    assert (df_macro["P2_included"] == False).all()
    assert (df_macro["R2_included"] == False).all()
    assert (df_macro["P3_included"] == False).all()
    assert (df_macro["R3_included"] == False).all()


# Test 8: R-Set Construction Independent of Model Performance
def test_r_set_construction_independent_of_performance(df_info):
    forbidden = ["ic", "sharpe", "p-value", "performance", "best", "optimal", "alpha", "edge", "profit"]
    for _, row in df_info.iterrows():
        inc = str(row["inclusion_reason"]).lower()
        exc = str(row["exclusion_reason"]).lower()
        for term in forbidden:
            assert f" {term} " not in f" {inc} "
            assert f" {term} " not in f" {exc} "


# Test 9: No IC-Based Membership Logic
def test_no_ic_based_membership():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "if ic >" not in script_text.lower()
    assert "if pearson >" not in script_text.lower()
    assert "if spearman >" not in script_text.lower()


# Test 10: No P-Value-Based Membership Logic
def test_no_pvalue_based_membership():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "if p_val <" not in script_text.lower()
    assert "if pval <" not in script_text.lower()
    assert "if p_value <" not in script_text.lower()


# Test 11: No Placebo-Based Membership Logic
def test_no_placebo_based_membership():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "if emp_pval" not in script_text.lower()
    assert "if placebo" not in script_text.lower()


# Test 12: No Return-Based Membership Logic
def test_no_return_based_membership():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "if return >" not in script_text.lower()
    assert "if ret >" not in script_text.lower()


# Test 13: No Feature-Importance-Based Membership Logic
def test_no_feature_importance_based_membership():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "feature_importances_" not in script_text.lower()
    assert "gain" not in script_text.lower() or "objective" in script_text.lower()


# Test 14: XGBoost Only
def test_xgboost_only(manifest):
    assert manifest["model_family"] == "xgboost.XGBRegressor"


# Test 15: Zero LightGBM in Script
def test_zero_lightgbm_in_script():
    script_text = SCRIPT_PATH.read_text(encoding="utf-8")
    code_lines = [
        line.strip().lower()
        for line in script_text.splitlines()
        if not line.strip().startswith("#") and not line.strip().startswith('"') and not line.strip().startswith("*") and not line.strip().startswith("-")
    ]
    for l in code_lines:
        assert "import lightgbm" not in l
        assert "import lgb" not in l
        assert "lightgbm." not in l
        assert "lgb." not in l


# Test 16: Holdout Firewall Integrity
def test_holdout_firewall(manifest):
    assert manifest["holdout_firewall"]["terminal_holdout_quarantined"] is True
    assert manifest["holdout_firewall"]["holdout_sessions_accessed"] == 0
    df_preds = pd.read_csv(PREDICTIONS_CSV)
    assert df_preds["trading_date"].max() <= "2021-12-31"
    assert not any(df_preds["trading_date"] >= "2022-01-03")


# Test 17: Upstream Artifact Immutability
def test_upstream_artifact_immutability():
    from scripts.phase12_step10_reconstruction import verify_protected_checksums
    verify_protected_checksums()


# Test 18: Artifact Integrity Manifest Hash Check
def test_artifact_integrity_manifest(manifest):
    for fn, exp_hash in manifest["file_hashes"].items():
        fp = DATA_DIR / fn
        assert fp.is_file(), f"Missing Step 10 artifact: {fn}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for {fn}!\nExp: {exp_hash}\nAct: {act_hash}"
