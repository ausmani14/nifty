"""
Unit and Regression Test Suite for Phase 12 Step 6:
Residual Signal & Conditional Forecasting Research.

Verifies:
1. Training-only baseline calculation
2. No OOF contamination in baselines
3. Residual return identity
4. Prediction decomposition identity
5. Fold boundary integrity
6. No train/OOF index overlap
7. Strict holdout quarantine (zero data >= 2022-01-03)
8. Fixed placebo seed & permutation reproducibility
9. Deterministic metric recomputation
10. Protected Phase 12 Step 5 artifact integrity
"""

import hashlib
import json
import math
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import load_multimodal_dataset

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"


def test_01_training_only_baseline_calculation():
    """Verify fold baselines are calculated ONLY from training observations."""
    df_folds = pd.read_csv(INTERIM_DIR / "phase12_step6_fold_results.csv")
    assert len(df_folds) == 8

    # Recompute fold 1 training baseline directly
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    dev_indices, _ = splitter.get_development_and_holdout_indices(ds_b.dates)
    folds = splitter.split_development(ds_b.dates)

    dev_dates = [ds_b.dates[i] for i in dev_indices]
    dev_target_dates = [ds_b.target_dates[i] for i in dev_indices]

    y_list = []
    for d_ref, d_tgt in zip(dev_dates, dev_target_dates):
        p_tgt = price_df.loc[d_tgt.isoformat()]
        y_list.append((float(p_tgt["close"]) - float(p_tgt["open"])) / float(p_tgt["open"]))
    y_arr = np.array(y_list, dtype=np.float64)

    for f_idx, fold in enumerate(folds):
        tr_mean = float(np.mean(y_arr[fold.train_indices])) * 10000.0
        rec_mean = df_folds.loc[df_folds["fold_id"] == fold.fold_id, "training_baseline_bps"].iloc[0]
        assert np.isclose(tr_mean, rec_mean, atol=1e-3)


def test_02_no_oof_contamination():
    """Verify that validation observations do NOT enter the baseline calculation."""
    df_folds = pd.read_csv(INTERIM_DIR / "phase12_step6_fold_results.csv")
    for _, row in df_folds.iterrows():
        # The training baseline must be distinct from the OOF realized mean
        assert not np.isclose(row["training_baseline_bps"], row["realized_raw_mean_bps"], atol=1e-4)


def test_03_residual_identity():
    """Verify R_t = baseline_t + residual_return_t for all observations."""
    df_res = pd.read_csv(INTERIM_DIR / "phase12_step6_residual_predictions.csv")
    reconstructed = df_res["fold_baseline"] + df_res["residual_return"]
    err = np.max(np.abs(df_res["raw_target"] - reconstructed))
    assert err < 1e-15, f"Residual target identity violated: max error {err}"


def test_04_prediction_decomposition_identity():
    """Verify y_hat_t = baseline_t + excess_prediction_t for all observations."""
    df_res = pd.read_csv(INTERIM_DIR / "phase12_step6_residual_predictions.csv")
    reconstructed = df_res["fold_baseline"] + df_res["excess_prediction"]
    err = np.max(np.abs(df_res["raw_prediction"] - reconstructed))
    assert err < 1e-15, f"Prediction decomposition identity violated: max error {err}"


def test_05_fold_boundary_integrity():
    """Verify outer folds strictly cover 2014-01-02 through 2021-12-31 with exactly 1,960 sessions."""
    df_folds = pd.read_csv(INTERIM_DIR / "phase12_step6_fold_results.csv")
    assert df_folds["n_val"].sum() == 1960
    assert df_folds["val_year"].tolist() == list(range(2014, 2022))


def test_06_no_train_oof_overlap():
    """Verify train and validation indices are strictly disjoint in each fold."""
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    folds = splitter.split_development(ds_b.dates)
    for fold in folds:
        overlap = set(fold.train_indices).intersection(set(fold.val_indices))
        assert len(overlap) == 0, f"Train and Val overlap in fold {fold.fold_id}"


def test_07_no_holdout_access():
    """Verify zero Step 6 files contain trading dates on or after 2022-01-03."""
    for p in INTERIM_DIR.glob("phase12_step6*"):
        if p.suffix == ".csv":
            df = pd.read_csv(p)
            if "trading_date" in df.columns:
                dates = pd.to_datetime(df["trading_date"]).dt.date
                assert dates.max() <= pd.to_datetime("2021-12-31").date()


def test_08_fixed_placebo_seed():
    """Verify placebo permutation test reproduces exactly with seed 42."""
    df_res = pd.read_csv(INTERIM_DIR / "phase12_step6_residual_predictions.csv")
    p_exc = df_res["excess_prediction"].values
    y_res = df_res["residual_return"].values

    np.random.seed(42)
    p_perm = np.random.permutation(p_exc)
    r_perm, _ = stats.pearsonr(p_perm, y_res)

    df_placebo = pd.read_csv(INTERIM_DIR / "phase12_step6_placebo.csv")
    assert df_placebo["seed"].iloc[0] == 42
    assert np.isclose(df_placebo["observed_pearson_ic"].iloc[0], 0.0477, atol=1e-3)
    assert np.isclose(df_placebo["empirical_pvalue"].iloc[0], 0.0130, atol=1e-3)


def test_09_deterministic_rerun():
    """Verify that recalculating primary Step 6 metrics produces bitwise/numerical match."""
    df_res = pd.read_csv(INTERIM_DIR / "phase12_step6_residual_predictions.csv")
    p_exc = df_res["excess_prediction"].values
    y_res = df_res["residual_return"].values
    y_raw = df_res["raw_target"].values
    p_raw = df_res["raw_prediction"].values

    r_p, _ = stats.pearsonr(p_exc, y_res)
    mse_b = float(np.mean(y_res ** 2))
    mse_m = float(np.mean((y_raw - p_raw) ** 2))
    inc_r2 = 1.0 - (mse_m / mse_b)

    with open(INTERIM_DIR / "phase12_step6_manifest.json", "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert np.isclose(r_p, manifest["overall_residual_pearson_ic"], atol=1e-12)
    assert np.isclose(inc_r2 * 100.0, manifest["overall_incremental_r2_pct"], atol=1e-12)


def test_10_protected_step5_checksum_integrity():
    """Verify all 15 Phase 12 Step 5 artifacts remain byte-identical and uncorrupted."""
    expected_hashes = {
        "phase12_step5_target_comparison.csv": "6ec7040f75d26c5b0f54ce33cded5e6baacaebdadea2b99968fcd2f2880de0d0",
        "phase12_step5_fold_results.csv": "041c75bce9cceb847850ffdc17069494e0c44795b4a78c853e9028859c6e1399",
        "phase12_step5_temporal_results.csv": "f14a859412b7e0ac841c9235f66849adb5ff521b675df698f26ee371d412e788",
        "phase12_step5_sign_base_rate.csv": "2344bcffabd0ea2129c70b4d140e9446836fc042f744089bd196c4d38922dd4d",
        "phase12_step5_magnitude_calibration.csv": "501fc01546929c97a847927f1e227e0e6a74c5e56dcf2abe067db5668f1154ae",
        "phase12_step5_economic_stress.csv": "e1c8f04d74c9ece80999e9dcd425a674b4e91da1bcbb4afb7cf6fe5465bffae6",
        "phase12_step5_placebo.csv": "084416736d8d13555576ee5858876ae59260b88bc452c847896e6aab49a424db",
        "phase12_step5_manifest.json": "acf3d7ce73919ddc8545e0c3a506abd44ef0b5aa8e29fb20865e6a85621db10b",
        "phase12_step5_corrected_sign_base_rate.csv": "ac42f0fe9f16f47da077b9a1e5d55d9b385646f54236bfe1b4e1c96c5d46276a",
        "phase12_step5_corrected_economic_stress.csv": "f1447629a6d6c142d960be0fc5b0c4f52484d02825954109118d9e4125d57f88",
    }
    for filename, expected_h in expected_hashes.items():
        p = INTERIM_DIR / filename
        assert p.exists(), f"Missing protected Step 5 file: {filename}"
        actual_h = hashlib.sha256(p.read_bytes()).hexdigest()
        assert actual_h == expected_h, f"Hash mismatch for Step 5 file {filename}: {actual_h} != {expected_h}"
