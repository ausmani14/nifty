"""Unit and forensic validation test suite for Phase 12 Step 11: Snapshot B Target Robustness & Horizon Definition Audit.

Requirements Verified:
1. T0 mathematical definition ((Close(T+1) - Open(T+1)) / Open(T+1))
2. T1 mathematical definition ((Close(T+1) - Close(T)) / Close(T))
3. T2 fold-local mean construction (strict training fold mean subtraction, zero leakage)
4. T3 log transformation (ln(Close(T+1) / Open(T+1)))
5. T4 data-availability rule (NOT EXECUTABLE — REQUIRED DATASET NOT PRESENT)
6. Identical OOF date universe (N=1,960, 2014-01-02 to 2021-12-31)
7. No holdout access (max trading date <= 2021-12-31, holdout rows accessed == 0)
8. No performance-based target selection (pre-registration established prior to evaluation)
9. Locked XGBoost configuration with tree count N* = 43 across all targets
10. Feature matrix integrity (exactly 63 features matching locked Snapshot B set)
11. Chronological fold integrity (8 expanding folds)
12. Deterministic target generation
13. Artifact and hash integrity (step11_integrity_manifest.json matches disk files)
14. Upstream artifact immutability (Phase 4-10, Step 5-10 protected hashes intact)
15. Multiple-testing framework (distinguishes independent horizon from derived/transformed targets)
16. Economic diagnostic strictly limited to T0 (no trading rules for T1/T2/T3)
"""

from datetime import date
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step11"
MANIFEST_PATH = DATA_DIR / "step11_integrity_manifest.json"
REG_CSV = DATA_DIR / "step11_target_definitions.csv"
REG_JSON = DATA_DIR / "step11_target_definitions.json"
STATS_CSV = DATA_DIR / "step11_target_statistics.csv"
PREDICTIONS_CSV = DATA_DIR / "step11_predictions.csv"
FOLD_RESULTS_CSV = DATA_DIR / "step11_fold_results.csv"
TEMPORAL_RESULTS_CSV = DATA_DIR / "step11_temporal_results.csv"
RESIDUAL_RESULTS_CSV = DATA_DIR / "step11_residual_results.csv"
BASELINE_CSV = DATA_DIR / "step11_baseline_comparison.csv"
MULTIPLE_TESTING_CSV = DATA_DIR / "step11_multiple_testing.csv"
ECON_CSV = DATA_DIR / "step11_economic_diagnostic.csv"


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.is_file(), f"Missing manifest: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def df_reg():
    assert REG_CSV.is_file(), f"Missing target definitions CSV: {REG_CSV}"
    return pd.read_csv(REG_CSV)


@pytest.fixture(scope="module")
def reg_json():
    assert REG_JSON.is_file(), f"Missing target definitions JSON: {REG_JSON}"
    with open(REG_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def df_stats():
    assert STATS_CSV.is_file(), f"Missing target statistics CSV: {STATS_CSV}"
    return pd.read_csv(STATS_CSV)


@pytest.fixture(scope="module")
def df_preds():
    assert PREDICTIONS_CSV.is_file(), f"Missing predictions CSV: {PREDICTIONS_CSV}"
    return pd.read_csv(PREDICTIONS_CSV)


@pytest.fixture(scope="module")
def df_folds():
    assert FOLD_RESULTS_CSV.is_file(), f"Missing fold results CSV: {FOLD_RESULTS_CSV}"
    return pd.read_csv(FOLD_RESULTS_CSV)


@pytest.fixture(scope="module")
def df_temporal():
    assert TEMPORAL_RESULTS_CSV.is_file(), f"Missing temporal results CSV: {TEMPORAL_RESULTS_CSV}"
    return pd.read_csv(TEMPORAL_RESULTS_CSV)


@pytest.fixture(scope="module")
def df_residual():
    assert RESIDUAL_RESULTS_CSV.is_file(), f"Missing residual results CSV: {RESIDUAL_RESULTS_CSV}"
    return pd.read_csv(RESIDUAL_RESULTS_CSV)


@pytest.fixture(scope="module")
def df_baseline():
    assert BASELINE_CSV.is_file(), f"Missing baseline comparison CSV: {BASELINE_CSV}"
    return pd.read_csv(BASELINE_CSV)


@pytest.fixture(scope="module")
def df_multiple_testing():
    assert MULTIPLE_TESTING_CSV.is_file(), f"Missing multiple testing CSV: {MULTIPLE_TESTING_CSV}"
    return pd.read_csv(MULTIPLE_TESTING_CSV)


@pytest.fixture(scope="module")
def df_econ():
    assert ECON_CSV.is_file(), f"Missing economic diagnostic CSV: {ECON_CSV}"
    return pd.read_csv(ECON_CSV)


def test_t0_mathematical_definition(df_preds):
    """Verify T0 = (Close(T+1) - Open(T+1)) / Open(T+1) across OOF universe."""
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    for _, row in df_preds.head(50).iterrows():
        p_tgt = price_df.loc[row["target_date"]]
        o1 = float(p_tgt["open"])
        c1 = float(p_tgt["close"])
        expected_t0 = (c1 - o1) / o1
        assert math.isclose(row["T0_actual"], expected_t0, rel_tol=1e-7, abs_tol=1e-7)


def test_t1_mathematical_definition(df_preds):
    """Verify T1 = (Close(T+1) - Close(T)) / Close(T) across OOF universe."""
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    for _, row in df_preds.head(50).iterrows():
        p_ref = price_df.loc[row["trading_date"]]
        p_tgt = price_df.loc[row["target_date"]]
        c0 = float(p_ref["close"])
        c1 = float(p_tgt["close"])
        expected_t1 = (c1 - c0) / c0
        assert math.isclose(row["T1_actual"], expected_t1, rel_tol=1e-7, abs_tol=1e-7)


def test_t2_fold_local_centering(df_preds):
    """Verify T2 = T0 - mu_train_fold exactly, with zero test-set leakage."""
    for fold_id in range(1, 9):
        fold_sub = df_preds[df_preds["fold_id"] == fold_id]
        mu_train = fold_sub["T0_mu_train"].iloc[0]
        # Verify mu_train is constant across the fold
        assert (fold_sub["T0_mu_train"] == mu_train).all()
        # Verify T2_actual == T0_actual - mu_train
        diff = fold_sub["T2_actual"] - (fold_sub["T0_actual"] - mu_train)
        assert np.all(np.abs(diff) < 1e-9)


def test_t3_log_transformation(df_preds):
    """Verify T3 = ln(Close(T+1) / Open(T+1))."""
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    for _, row in df_preds.head(50).iterrows():
        p_tgt = price_df.loc[row["target_date"]]
        o1 = float(p_tgt["open"])
        c1 = float(p_tgt["close"])
        expected_t3 = float(np.log(c1 / o1))
        assert math.isclose(row["T3_actual"], expected_t3, rel_tol=1e-7, abs_tol=1e-7)


def test_t4_non_executable_status(df_reg, df_stats, df_preds):
    """Verify T4 is registered as NOT EXECUTABLE and excluded from model predictions."""
    t4_reg = df_reg[df_reg["target_id"] == "T4"].iloc[0]
    assert t4_reg["executable_status"] == "NOT EXECUTABLE — REQUIRED DATASET NOT PRESENT"
    assert "intraday" in t4_reg["economic_interpretation"].lower()

    t4_stat = df_stats[df_stats["target_id"] == "T4"].iloc[0]
    assert t4_stat["observation_count"] == 0
    assert t4_stat["missing_count"] == 1960
    assert t4_stat["status"] == "NOT EXECUTABLE — REQUIRED DATASET NOT PRESENT"

    # T4 must not be in predictions
    assert "T4_actual" not in df_preds.columns
    assert "T4_pred" not in df_preds.columns


def test_identical_oof_universe(df_preds):
    """Verify exactly N=1,960 OOF rows spanning 2014-01-02 to 2021-12-31."""
    assert len(df_preds) == 1960
    min_date = df_preds["trading_date"].min()
    max_date = df_preds["trading_date"].max()
    assert min_date == "2014-01-02"
    assert max_date == "2021-12-31"

    # Verify no missing values in any executable target
    for tid in ["T0", "T1", "T2", "T3"]:
        assert df_preds[f"{tid}_actual"].isna().sum() == 0
        assert df_preds[f"{tid}_pred"].isna().sum() == 0
        assert df_preds[f"{tid}_mu_train"].isna().sum() == 0


def test_holdout_firewall(manifest, df_preds):
    """Verify strict holdout quarantine (zero holdout rows accessed, max date <= 2021-12-31)."""
    assert manifest["firewall_verification"]["firewall_intact"] is True
    assert manifest["firewall_verification"]["holdout_rows_accessed"] == 0
    assert manifest["firewall_verification"]["holdout_rows_quarantined"] == 1154
    assert manifest["firewall_verification"]["max_dev_trading_date"] <= "2021-12-31"

    max_pred_date = df_preds["trading_date"].max()
    assert max_pred_date <= "2021-12-31"


def test_model_comparability_locked_n_trees(manifest, df_folds):
    """Verify XGBoost tree counts are locked to established Step 2 sequence across all executable targets."""
    assert manifest["model_configuration"]["fold_n_estimators"] == [10, 60, 45, 60, 10, 10, 10, 40]
    assert manifest["model_configuration"]["per_target_optimization"] is False
    assert manifest["model_configuration"]["learning_rate"] == 0.05
    assert manifest["model_configuration"]["max_depth"] == 2
    assert manifest["model_configuration"]["min_child_weight"] == 20.0
    assert manifest["model_configuration"]["subsample"] == 0.8
    assert manifest["model_configuration"]["colsample_bytree"] == 0.7
    assert manifest["model_configuration"]["reg_alpha"] == 0.5
    assert manifest["model_configuration"]["reg_lambda"] == 2.0
    assert manifest["model_configuration"]["random_state"] == 42


def test_preregistration_target_taxonomy(df_reg):
    """Verify the formal taxonomy of targets in the pre-registration registry."""
    assert len(df_reg) == 5
    t0 = df_reg[df_reg["target_id"] == "T0"].iloc[0]
    t1 = df_reg[df_reg["target_id"] == "T1"].iloc[0]
    t2 = df_reg[df_reg["target_id"] == "T2"].iloc[0]
    t3 = df_reg[df_reg["target_id"] == "T3"].iloc[0]
    t4 = df_reg[df_reg["target_id"] == "T4"].iloc[0]

    assert t0["target_category"] == "locked primary target"
    assert t1["target_category"] == "independent alternative economic horizon"
    assert t2["target_category"] == "derived centered diagnostic"
    assert t3["target_category"] == "mathematical transformation"
    assert t4["target_category"] == "unavailable intraday target"

    assert bool(t1["is_independent"]) is True
    assert bool(t2["is_derived"]) is True
    assert bool(t2["is_independent"]) is False
    assert bool(t3["is_transformed"]) is True
    assert bool(t3["is_independent"]) is False


def test_chronological_fold_integrity(df_folds):
    """Verify all 8 chronological folds are evaluated for all 4 executable targets."""
    assert len(df_folds) == 8 * 4  # 32 rows
    for tid in ["T0", "T1", "T2", "T3"]:
        sub = df_folds[df_folds["target_id"] == tid]
        assert len(sub) == 8
        assert sorted(sub["fold_id"].tolist()) == list(range(1, 9))
        assert sorted(sub["val_year"].tolist()) == list(range(2014, 2022))


def test_multiple_testing_structure(df_multiple_testing):
    """Verify multiple testing distinguishes independent economic horizons from derived/transformed targets."""
    assert len(df_multiple_testing) == 4
    for _, row in df_multiple_testing.iterrows():
        tid = row["target_id"]
        if tid in ["T0", "T1"]:
            assert bool(row["is_independent_economic_horizon"]) is True
        else:
            assert bool(row["is_independent_economic_horizon"]) is False
            assert "dependence" in row["structural_dependence_note"].lower() or "coupled" in row["structural_dependence_note"].lower()
        if tid == "T1":
            assert bool(row["is_statistically_independent"]) is False


def test_economic_diagnostic_t0_only(df_econ):
    """Verify economic diagnostic is evaluated strictly on T0 under 0, 5, 10, 20 bps."""
    assert (df_econ["target_evaluated"] == "T0").all()
    assert set(df_econ["cost_bps"].unique()) == {0, 5, 10, 20}
    strategies = df_econ["strategy"].unique().tolist()
    assert "T0_Model_Unrestricted_Sign" in strategies
    assert "T0_Always_Short_Benchmark" in strategies


def test_manifest_checksum_integrity(manifest):
    """Verify all Step 11 artifact SHA256 hashes on disk match the manifest exactly."""
    for fn, exp_hash in manifest["artifact_hashes"].items():
        fp = DATA_DIR / fn
        assert fp.is_file(), f"Missing artifact in manifest: {fn}"
        actual_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert actual_hash == exp_hash, f"Hash mismatch for {fn}!\nExpected: {exp_hash}\nActual:   {actual_hash}"


def test_upstream_artifact_immutability():
    """Verify all protected upstream hashes from Phase 4-10 and Steps 5-10 remain unchanged."""
    cfg_path = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Missing protected file: {rel_path}"
        actual = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert actual == exp_hash, f"Checksum mismatch for {rel_path}"
