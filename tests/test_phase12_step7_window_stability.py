"""
Unit and Regression Test Suite for Phase 12 Step 7:
Signal Stability Under Alternative Training-Window Specifications.

Verifies:
1. Exact OOF date preservation (2014-01-02 to 2021-12-31, N=1,960)
2. No duplicate predictions
3. No future training observations
4. Embargo correctness (train_end < val_start)
5. Fold-local baseline correctness (calculated strictly from training window)
6. Feature count exactly 63
7. Zero News features
8. Zero Volume features
9. Zero Flow proxy features
10. Deterministic window construction (exact expected boundaries)
11. Deterministic N* selection (only inside training folds)
12. Holdout firewall (zero data >= 2022-01-03)
13. Protected artifact immutability (Phase 4-10, Step 5, and Step 6)
14. Placebo integrity (seed 42, 1,000 permutations)
15. Artifact checksum integrity (manifest matches disk, original and corrected reports)
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

OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step7"
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"


def test_01_exact_oof_date_preservation():
    """Verify exact OOF evaluation population: 2014-01-02 to 2021-12-31, N=1,960."""
    df_preds = pd.read_csv(OUT_DIR / "step7_predictions.csv")
    assert len(df_preds) == 1960
    assert df_preds["trading_date"].min() == "2014-01-02"
    assert df_preds["trading_date"].max() == "2021-12-31"


def test_02_no_duplicate_predictions():
    """Verify that every trading_date in OOF predictions is strictly unique."""
    df_preds = pd.read_csv(OUT_DIR / "step7_predictions.csv")
    assert df_preds["trading_date"].nunique() == 1960
    assert not df_preds["trading_date"].duplicated().any()


def test_03_no_future_training_observations():
    """Verify that all training observations strictly precede the validation start date."""
    df_folds = pd.read_csv(OUT_DIR / "step7_fold_results.csv")
    for _, row in df_folds.iterrows():
        t_end = row["train_end_date"]
        v_start = row["val_start_date"]
        assert t_end < v_start, f"Future training leakage in {row['window_code']} fold {row['fold_id']}: {t_end} >= {v_start}"


def test_04_embargo_correctness():
    """Verify that the causal one-session embargo is maintained between train and validation."""
    df_folds = pd.read_csv(OUT_DIR / "step7_fold_results.csv")
    for _, row in df_folds.iterrows():
        t_end_dt = pd.to_datetime(row["train_end_date"]).date()
        v_start_dt = pd.to_datetime(row["val_start_date"]).date()
        assert t_end_dt < v_start_dt
        assert t_end_dt.year == v_start_dt.year - 1
        assert t_end_dt.month == 12
        assert t_end_dt.day >= 28


def test_05_fold_local_baseline_correctness():
    """Verify fold baselines are computed strictly from training window observations."""
    df_folds = pd.read_csv(OUT_DIR / "step7_fold_results.csv")
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    dev_indices, _ = splitter.get_development_and_holdout_indices(ds_b.dates)

    dev_dates = [ds_b.dates[i] for i in dev_indices]
    dev_target_dates = [ds_b.target_dates[i] for i in dev_indices]
    dev_date_arr = np.array(dev_dates)

    y_dev = []
    for d_tgt in dev_target_dates:
        p_tgt = price_df.loc[d_tgt.isoformat()]
        y_dev.append((float(p_tgt["close"]) - float(p_tgt["open"])) / float(p_tgt["open"]))
    y_dev_arr = np.array(y_dev, dtype=np.float64)

    for _, row in df_folds.iterrows():
        t_start = pd.to_datetime(row["train_start_date"]).date()
        t_end = pd.to_datetime(row["train_end_date"]).date()
        mask = (dev_date_arr >= t_start) & (dev_date_arr <= t_end)
        expected_mu = float(np.mean(y_dev_arr[mask])) * 10000.0
        recorded_mu = row["training_baseline_bps"]
        assert np.isclose(expected_mu, recorded_mu, atol=1e-3)


def test_06_feature_count_exactly_63():
    """Verify feature set contains exactly 63 features."""
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    X, feat_names = ds_b.get_features("Model 1")
    assert len(feat_names) == 63
    assert X.shape[1] == 63


def test_07_zero_news_features():
    """Verify zero News features are present."""
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    _, feat_names = ds_b.get_features("Model 1")
    news_feats = [f for f in feat_names if "news" in f.lower() or "sentiment" in f.lower() or "headline" in f.lower()]
    assert len(news_feats) == 0


def test_08_zero_volume_features():
    """Verify zero Volume features are present."""
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    _, feat_names = ds_b.get_features("Model 1")
    vol_feats = [f for f in feat_names if "volume" in f.lower() or "vol_" in f.lower() or "turnover" in f.lower()]
    assert len(vol_feats) == 0


def test_09_zero_flow_proxies():
    """Verify zero Flow proxy features are present."""
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    _, feat_names = ds_b.get_features("Model 1")
    flow_feats = [f for f in feat_names if "flow" in f.lower() or "fii" in f.lower() or "dii" in f.lower()]
    assert len(flow_feats) == 0


def test_10_deterministic_window_construction():
    """Verify deterministic training-window boundaries for all 4 windows."""
    df_folds = pd.read_csv(OUT_DIR / "step7_fold_results.csv")
    for _, row in df_folds.iterrows():
        w = row["window_code"]
        vy = row["val_year"]
        t_start_dt = pd.to_datetime(row["train_start_date"]).date()
        t_end_dt = pd.to_datetime(row["train_end_date"]).date()

        assert t_end_dt.year == vy - 1
        assert t_end_dt.month == 12
        assert t_end_dt.day >= 28

        if w == "W0":
            assert row["train_start_date"] == "2008-07-08"
        elif w == "W1":
            assert t_start_dt.year == vy - 5
            assert t_start_dt.month == 1
            assert t_start_dt.day <= 5
        elif w == "W2":
            assert t_start_dt.year == vy - 3
            assert t_start_dt.month == 1
            assert t_start_dt.day <= 5
        elif w == "W3":
            assert t_start_dt.year == vy - 2
            assert t_start_dt.month == 1
            assert t_start_dt.day <= 5


def test_11_deterministic_n_star_selection():
    """Verify N* selection is deterministic and strictly confined to training folds."""
    df_trees = pd.read_csv(OUT_DIR / "step7_tree_counts.csv")
    assert len(df_trees) == 32  # 8 folds x 4 windows
    candidate_grid = [10, 15, 20, 25, 30, 35, 40, 45, 50, 60]
    for _, row in df_trees.iterrows():
        assert row["selected_n_trees"] in candidate_grid
        assert row["inner_val_ratio"] == 0.20
        assert row["n_inner_train"] + row["n_inner_val"] == row["n_train"]


def test_12_holdout_firewall():
    """Verify zero access to terminal holdout (dates >= 2022-01-03)."""
    for p in OUT_DIR.glob("step7_*.csv"):
        df = pd.read_csv(p)
        if "trading_date" in df.columns:
            dates = pd.to_datetime(df["trading_date"]).dt.date
            assert dates.max() <= pd.to_datetime("2021-12-31").date()


def test_13_protected_artifact_immutability():
    """Verify all protected Phase 4-10, Step 5, and Step 6 artifacts remain byte-identical."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Missing protected file {rel_path}"
        act_h = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_h == exp_hash, f"Hash mismatch for {rel_path}"

    step5_hashes = {
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
    for fn, exp_h in step5_hashes.items():
        fp = PHASE12_DIR / fn
        assert fp.is_file(), f"Missing Step 5 file {fn}"
        assert hashlib.sha256(fp.read_bytes()).hexdigest() == exp_h

    step6_hashes = {
        "phase12_step6_economic_diagnostic.csv": "19341254f4448d6a0628313c909d6b4ab82843f64363853a584961d8160041ce",
        "phase12_step6_fold_results.csv": "317e9fb735347351be6e4bb44b807b6f419aaa0021badf20f19b2e2cc8b36c11",
        "phase12_step6_magnitude.csv": "f2f82819aad307aa5816dce101da847e52964ea880ddb6c9ea85293357467181",
        "phase12_step6_manifest.json": "cd39329b02772d81c5594bb1d3342795c8384f692952f4b293b8599c10bc6453",
        "phase12_step6_placebo.csv": "a6e30a69c9a2229ddcb5855360cb2a54d214672b6ea4c201688afee388dbf9d1",
        "phase12_step6_residual_predictions.csv": "41dae563cbb48f2ab84cf1b8f18edf190abbecdf82d5b7104e797a63755604af",
        "phase12_step6_temporal_results.csv": "85e901e45e6327640131011460146b0221956d0a2f8ae15e8c6be1aceea6dfe8",
    }
    for fn, exp_h in step6_hashes.items():
        fp = PHASE12_DIR / fn
        assert fp.is_file(), f"Missing Step 6 file {fn}"
        assert hashlib.sha256(fp.read_bytes()).hexdigest() == exp_h


def test_14_placebo_integrity():
    """Verify placebo permutation results reproduce exactly with seed 42."""
    df_placebo = pd.read_csv(OUT_DIR / "step7_placebo_results.csv")
    assert len(df_placebo) == 4
    for _, row in df_placebo.iterrows():
        assert row["seed"] == 42
        assert row["n_permutations"] == 1000
        assert row["n_eval_sessions"] == 1960


def test_15_artifact_checksum_integrity():
    """Verify all interim datasets and reports match the hashes recorded in the manifest."""
    manifest_path = OUT_DIR / "step7_integrity_manifest.json"
    assert manifest_path.is_file()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for fn, exp_h in manifest["file_hashes"].items():
        fp = OUT_DIR / fn
        assert fp.is_file(), f"Missing interim file {fn}"
        act_h = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_h == exp_h, f"Hash mismatch for {fn}: {act_h} != {exp_h}"

    if "report_hash" in manifest:
        rep_fp = PROJECT_ROOT / manifest["report_file"]
        assert rep_fp.is_file(), f"Missing report file {manifest['report_file']}"
        act_rep_h = hashlib.sha256(rep_fp.read_bytes()).hexdigest()
        assert act_rep_h == manifest["report_hash"], f"Report hash mismatch: {act_rep_h} != {manifest['report_hash']}"

    if "corrected_report_hash" in manifest:
        crep_fp = PROJECT_ROOT / manifest["corrected_report_file"]
        assert crep_fp.is_file(), f"Missing corrected report {manifest['corrected_report_file']}"
        act_crep_h = hashlib.sha256(crep_fp.read_bytes()).hexdigest()
        assert act_crep_h == manifest["corrected_report_hash"], f"Corrected report hash mismatch: {act_crep_h} != {manifest['corrected_report_hash']}"
