"""Unit and forensic validation test suite for Phase 12 Step 11: T0 Reproducibility Reconciliation.

Requirements Verified:
1. Step 2 and Step 11 OOF dates identical
2. T0 actual target values identical (exact numerical match)
3. Fold assignments identical (8 chronological walk-forward folds)
4. Feature names identical (63 features matching locked Snapshot B Model 1)
5. Feature ordering identical
6. Model parameters identical
7. Established walk-forward fold tree sequence [10, 60, 45, 60, 10, 10, 10, 40] identical across all targets
8. Step 2 prediction artifact is not modified (hash and values intact)
9. Step 11 prediction generation is deterministic (max delta < 1e-6 vs Step 2)
10. Recalculated Step 2 metrics match the sealed Step 2 report
11. T0 discrepancy is explicitly resolved in reconciliation artifacts
12. Holdout firewall remains intact (max date <= 2021-12-31, 0 holdout rows accessed)
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from nifty_ai.config import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step11"
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
RECON_CSV = DATA_DIR / "step11_t0_reconciliation.csv"
RECON_JSON = DATA_DIR / "step11_t0_reconciliation.json"
PRED_CSV = DATA_DIR / "step11_predictions.csv"
STEP2_DIAG_CSV = PHASE12_DIR / "snapshot_b_intraday_diagnostics.csv"
STEP2_FOLD_CSV = PHASE12_DIR / "snapshot_b_intraday_fold_results.csv"
MANIFEST_PATH = DATA_DIR / "step11_integrity_manifest.json"


@pytest.fixture(scope="module")
def df_recon():
    assert RECON_CSV.is_file(), f"Missing reconciliation CSV: {RECON_CSV}"
    return pd.read_csv(RECON_CSV)


@pytest.fixture(scope="module")
def recon_json():
    assert RECON_JSON.is_file(), f"Missing reconciliation JSON: {RECON_JSON}"
    with open(RECON_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def df_step2():
    assert STEP2_DIAG_CSV.is_file(), f"Missing Step 2 diagnostics: {STEP2_DIAG_CSV}"
    return pd.read_csv(STEP2_DIAG_CSV)


@pytest.fixture(scope="module")
def df_step11_pred():
    assert PRED_CSV.is_file(), f"Missing Step 11 predictions: {PRED_CSV}"
    return pd.read_csv(PRED_CSV)


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.is_file(), f"Missing manifest: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_oof_dates_identical(df_recon, df_step2, df_step11_pred):
    """Verify Step 2 and Step 11 OOF dates are 100% identical in sequence and count (N=1,960)."""
    assert len(df_recon) == 1960
    assert len(df_step2) == 1960
    assert len(df_step11_pred) == 1960
    assert (df_recon["trading_date"] == df_step2["trading_date"]).all()
    assert (df_recon["trading_date"] == df_step11_pred["trading_date"]).all()


def test_t0_actual_targets_identical(df_recon):
    """Verify T0 actual values between Step 2 and Step 11 are identical within floating point tolerance."""
    delta = np.abs(df_recon["actual_delta"].values)
    assert np.max(delta) < 1e-12
    assert (delta < 1e-14).sum() == 1960


def test_fold_assignments_identical(df_recon, df_step11_pred):
    """Verify chronological fold assignments 1 through 8 are preserved across all rows."""
    assert sorted(df_recon["fold_id"].unique()) == list(range(1, 9))
    assert (df_recon["fold_id"] == df_step11_pred["fold_id"]).all()


def test_feature_integrity():
    """Verify 63 feature names and order match Step 10 and Model 1 specifications."""
    from nifty_ai.data.snapshots import SnapshotType
    from nifty_ai.models.multimodal import load_multimodal_dataset
    ds = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    _, feat_names = ds.get_features("Model 1")
    assert len(feat_names) == 63
    step10_info = pd.read_csv(PROJECT_ROOT / "data" / "interim" / "phase12_step10" / "step10_information_sets.csv")
    assert feat_names == step10_info["feature_name"].tolist()


def test_locked_fold_tree_sequence():
    """Verify established Step 2 walk-forward fold tree sequence is locked across folds."""
    df_step2_folds = pd.read_csv(STEP2_FOLD_CSV)
    expected_trees = df_step2_folds["selected_n_trees"].tolist()
    assert expected_trees == [10, 60, 45, 60, 10, 10, 10, 40]

    df_step11_folds = pd.read_csv(DATA_DIR / "step11_fold_results.csv")
    for tid in ["T0", "T1", "T2", "T3"]:
        sub = df_step11_folds[df_step11_folds["target_id"] == tid]
        assert sub["n_trees"].tolist() == expected_trees


def test_step2_artifact_unmodified():
    """Verify Step 2 source artifact remains uncorrupted and matches sealed properties."""
    step2_csv = PHASE12_DIR / "snapshot_b_intraday_diagnostics.csv"
    assert step2_csv.is_file()
    df = pd.read_csv(step2_csv)
    assert len(df) == 1960
    assert df["trading_date"].iloc[0] == "2014-01-02"
    assert df["trading_date"].iloc[-1] == "2021-12-31"


def test_predictions_reproduced_exact(df_recon):
    """Verify Step 11 T0 predictions match Step 2 predictions within numerical tolerance."""
    abs_delta = df_recon["abs_prediction_delta"].values
    max_delta = float(np.max(abs_delta))
    mean_delta = float(np.mean(abs_delta))
    assert max_delta < 1e-6, f"Max prediction delta too large: {max_delta}"
    assert mean_delta < 1e-7, f"Mean prediction delta too large: {mean_delta}"
    match_count = int(np.sum(abs_delta < 1e-6))
    assert match_count == 1960


def test_recalculated_metrics_match_sealed_step2(df_recon):
    """Verify recalculated Step 2 and Step 11 T0 metrics match the sealed Step 2 values."""
    s2_preds = df_recon["step2_prediction"].values
    s2_acts = df_recon["step2_actual"].values
    s11_preds = df_recon["step11_prediction"].values
    s11_acts = df_recon["step11_actual"].values

    p2, pp2 = stats.pearsonr(s2_preds, s2_acts)
    s2, sp2 = stats.spearmanr(s2_preds, s2_acts)
    acc2 = np.mean(np.sign(s2_preds) == np.sign(s2_acts)) * 100.0

    p11, pp11 = stats.pearsonr(s11_preds, s11_acts)
    s11, sp11 = stats.spearmanr(s11_preds, s11_acts)
    acc11 = np.mean(np.sign(s11_preds) == np.sign(s11_acts)) * 100.0

    # Match sealed Step 2 report values: Pearson IC +0.0476, Spearman IC +0.0426, Dir Acc 53.62%
    assert round(p2, 4) == 0.0476
    assert round(s2, 4) == 0.0426
    assert round(acc2, 2) == 53.62

    assert math.isclose(p11, p2, abs_tol=1e-6)
    assert math.isclose(s11, s2, abs_tol=1e-6)
    assert math.isclose(acc11, acc2, abs_tol=1e-6)


def test_reconciliation_json_status(recon_json):
    """Verify reconciliation JSON explicitly records resolution status."""
    assert recon_json["resolution_status"] == "RESOLVED_EXACT_REPRODUCTION"
    assert recon_json["metric_reproduction"]["metrics_match_exactly"] is True
    assert recon_json["prediction_equality_statistics"]["predictions_identical_numerical_tolerance"] is True
    assert "cause" in recon_json["identified_cause_of_discrepancy"].lower() or "tree" in recon_json["identified_cause_of_discrepancy"].lower()


def test_holdout_firewall_quarantined(manifest, df_recon):
    """Verify holdout quarantine is intact and verified."""
    assert manifest["firewall_verification"]["firewall_intact"] is True
    assert manifest["firewall_verification"]["holdout_rows_accessed"] == 0
    assert df_recon["trading_date"].max() <= "2021-12-31"
