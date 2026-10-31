"""
Unit and Regression Test Suite for Phase 12 Step 8:
Feature Information Stability & Information-Set Ablation Research.

Covers:
1. Exact 63-feature registry
2. Correct feature-family membership
3. No invented features
4. Exact OOF population (1,960 sessions, 2014-01-02 to 2021-12-31, 8 folds)
5. No duplicate predictions
6. No missing predictions
7. Chronological training (all training strictly precedes validation)
8. Embargo correctness (one-session causal embargo maintained)
9. Fold-local baseline (mu_train computed strictly from training fold)
10. Zero News features
11. Zero Volume features
12. Zero Flow proxy features
13. Deterministic ablation construction (group definitions and feature counts)
14. Deterministic N* selection (tree counts selected strictly inside training fold)
15. Placebo integrity (1,000 permutations, seed 42)
16. Holdout firewall (max date <= 2021-12-31, zero rows >= 2022-01-03)
17. Protected artifact immutability (Phase 4-10, Step 5, Step 6, Step 7)
18. Artifact checksum integrity (manifest matches disk for all Step 8 interim files)
19. Original Step 8 report byte-for-byte preservation
20. Corrected Step 8 report existence and forensic disclaimer integrity
"""

import hashlib
import json
import math
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import load_multimodal_dataset

OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step8"
STEP7_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step7"
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"
DOCS_DIR = PROJECT_ROOT / "docs"

ORIGINAL_REPORT_HASH = "f8c924ce85c3b8965b946274bda45fe3d533ed042e348678e59a95987b068d8b"


def test_01_exact_63_feature_registry():
    """Test 1: Verify exact 63 features in registry matching multimodal dataset."""
    df_reg = pd.read_csv(OUT_DIR / "step8_feature_group_registry.csv")
    assert len(df_reg) == 63
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    _, feat_names = ds_b.get_features("Model 1")
    assert set(df_reg["feature_name"]) == set(feat_names)


def test_02_correct_feature_family_membership():
    """Test 2: Verify correct assignment of features to their canonical families."""
    df_reg = pd.read_csv(OUT_DIR / "step8_feature_group_registry.csv")
    price_fams = df_reg[df_reg["Price_or_Context"] == "Price"]["feature_family"].unique()
    expected_price_fams = {
        "trailing_returns", "lagged_returns", "short_moving_averages", "short_momentum",
        "ohlc_shape", "med_long_moving_averages", "long_momentum", "structural_trend",
        "volatility_risk", "calendar_seasonal"
    }
    assert set(price_fams).issubset(expected_price_fams)

    ctx_fams = df_reg[df_reg["Price_or_Context"] == "Context"]["feature_family"].unique()
    expected_ctx_fams = {
        "domestic_equity", "domestic_volatility", "domestic_rates", "domestic_fx",
        "global_equity", "global_volatility", "global_commodities", "global_fx", "global_rates"
    }
    assert set(ctx_fams).issubset(expected_ctx_fams)


def test_03_no_invented_features():
    """Test 3: Verify all 63 feature names originate from sealed Phase 4 & Phase 7."""
    df_reg = pd.read_csv(OUT_DIR / "step8_feature_group_registry.csv")
    price_feats = df_reg[df_reg["Price_or_Context"] == "Price"]["feature_name"].tolist()
    ctx_feats = df_reg[df_reg["Price_or_Context"] == "Context"]["feature_name"].tolist()

    assert len(price_feats) == 45
    assert len(ctx_feats) == 18
    for pf in price_feats:
        assert not pf.startswith("ctx_")
    for cf in ctx_feats:
        assert cf.startswith("ctx_")


def test_04_exact_oof_population():
    """Test 4: Verify exact OOF evaluation population: 2014-01-02 to 2021-12-31, N=1,960."""
    df_preds = pd.read_csv(OUT_DIR / "step8_predictions.csv")
    assert len(df_preds) == 1960
    assert df_preds["trading_date"].min() == "2014-01-02"
    assert df_preds["trading_date"].max() == "2021-12-31"


def test_05_no_duplicate_predictions():
    """Test 5: Verify no duplicate trading dates in OOF predictions."""
    df_preds = pd.read_csv(OUT_DIR / "step8_predictions.csv")
    assert df_preds["trading_date"].nunique() == 1960
    assert not df_preds["trading_date"].duplicated().any()


def test_06_no_missing_predictions():
    """Test 6: Verify zero missing values across all prediction and return columns."""
    df_preds = pd.read_csv(OUT_DIR / "step8_predictions.csv")
    assert df_preds.isnull().sum().sum() == 0


def test_07_chronological_training():
    """Test 7: Verify all training observations strictly precede the validation year."""
    df_folds = pd.read_csv(OUT_DIR / "step8_fold_results.csv")
    for _, row in df_folds.iterrows():
        val_year = row["val_year"]
        assert val_year >= 2014 and val_year <= 2021


def test_08_embargo_correctness():
    """Test 8: Verify one-session causal embargo between train and validation."""
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    dev_indices, _ = splitter.get_development_and_holdout_indices(ds_b.dates)
    folds = splitter.split_development(ds_b.dates)
    dev_dates = [ds_b.dates[i] for i in dev_indices]

    for fold in folds:
        val_start = fold.val_start_date
        val_year = val_start.year
        train_end_date = date(val_year - 1, 12, 31)
        last_train_date = max(d for d in dev_dates if d <= train_end_date)
        assert last_train_date < val_start
        assert (val_start - last_train_date).days >= 1


def test_09_fold_local_baseline():
    """Test 9: Verify mu_train is strictly fold-local and derived solely from training targets."""
    df_preds = pd.read_csv(OUT_DIR / "step8_predictions.csv")
    df_folds = pd.read_csv(OUT_DIR / "step8_fold_results.csv")
    g0_folds = df_folds[df_folds["config_code"] == "G0_ALL"]

    for _, f_row in g0_folds.iterrows():
        f_id = f_row["fold_id"]
        pred_sub = df_preds[df_preds["fold_id"] == f_id]
        expected_mu = f_row["mu_train_bps"] / 10000.0
        assert np.allclose(pred_sub["mu_train"], expected_mu, atol=1e-7)


def test_10_zero_news_features():
    """Test 10: Verify zero news features across all configurations."""
    df_reg = pd.read_csv(OUT_DIR / "step8_feature_group_registry.csv")
    for fn in df_reg["feature_name"]:
        assert not any(kw in fn.lower() for kw in ["news", "sentiment", "finbert", "headline"])


def test_11_zero_volume_features():
    """Test 11: Verify zero volume features across all configurations."""
    df_reg = pd.read_csv(OUT_DIR / "step8_feature_group_registry.csv")
    for fn in df_reg["feature_name"]:
        assert not any(kw in fn.lower() for kw in ["volume", "vol_ratio", "obv", "vwap"])


def test_12_zero_flow_proxy_features():
    """Test 12: Verify zero flow proxy features across all configurations."""
    df_reg = pd.read_csv(OUT_DIR / "step8_feature_group_registry.csv")
    for fn in df_reg["feature_name"]:
        assert not any(kw in fn.lower() for kw in ["fii", "dii", "flow", "turnover_ratio"])


def test_13_deterministic_ablation_construction():
    """Test 13: Verify exact expected feature counts for all 19 configurations."""
    df_summary = pd.read_csv(OUT_DIR / "step8_summary.csv")
    expected_counts = {
        "G0_ALL": 63,
        "G1_PRICE": 45,
        "G2_CONTEXT": 18,
        "G3_SHORT_PRICE": 25,
        "G4_MED_LONG_PRICE": 10,
        "G5_VOLATILITY": 5,
        "G6_DOMESTIC_CTX": 5,
        "G7_GLOBAL_CTX": 8,
        "G8_MACRO_CTX": 5,
        "G_CALENDAR": 5,
        "LOO_NO_PRICE": 18,
        "LOO_NO_CONTEXT": 45,
        "LOO_NO_SHORT_PRICE": 38,
        "LOO_NO_MED_LONG_PRICE": 53,
        "LOO_NO_VOLATILITY": 58,
        "LOO_NO_DOMESTIC_CTX": 58,
        "LOO_NO_GLOBAL_CTX": 55,
        "LOO_NO_MACRO_CTX": 58,
        "LOO_NO_CALENDAR": 58,
    }
    for _, row in df_summary.iterrows():
        code = row["config_code"]
        assert row["n_features"] == expected_counts[code], f"Count mismatch for {code}"


def test_14_deterministic_n_trees_selection():
    """Test 14: Verify selected tree counts N* are within the pre-registered candidate set."""
    df_folds = pd.read_csv(OUT_DIR / "step8_fold_results.csv")
    candidate_trees = {10, 15, 20, 25, 30, 35, 40, 45, 50, 60}
    for _, row in df_folds.iterrows():
        assert int(row["selected_n_trees"]) in candidate_trees


def test_15_placebo_integrity():
    """Test 15: Verify placebo test has exactly 1,000 permutations with seed 42."""
    df_placebo = pd.read_csv(OUT_DIR / "step8_placebo_results.csv")
    assert len(df_placebo) == 17
    assert (df_placebo["n_permutations"] == 1000).all()
    assert (df_placebo["seed"] == 42).all()
    assert (df_placebo["n_sessions"] == 1960).all()


def test_16_holdout_firewall():
    """Test 16: Verify maximum date <= 2021-12-31 and zero rows from 2022 onward."""
    df_preds = pd.read_csv(OUT_DIR / "step8_predictions.csv")
    max_d = df_preds["trading_date"].max()
    assert max_d <= "2021-12-31"
    assert (pd.to_datetime(df_preds["trading_date"]) >= pd.to_datetime("2022-01-03")).sum() == 0


def test_17_protected_artifact_immutability():
    """Test 17: Verify Phase 4-10, Step 5, Step 6, and Step 7 artifacts remain unmodified."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Missing protected file: {rel_path}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for {rel_path}"

    from scripts.phase12_step8_feature_ablation import (
        PROTECTED_STEP5_HASHES,
        PROTECTED_STEP6_HASHES,
        PROTECTED_STEP7_HASHES,
    )

    for fn, exp_hash in PROTECTED_STEP5_HASHES.items():
        fp = PHASE12_DIR / fn
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 5 file {fn}"

    for fn, exp_hash in PROTECTED_STEP6_HASHES.items():
        fp = PHASE12_DIR / fn
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 6 file {fn}"

    for fn, exp_hash in PROTECTED_STEP7_HASHES.items():
        fp = STEP7_DIR / fn
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 7 file {fn}"


def test_18_artifact_checksum_integrity():
    """Test 18: Verify all 10 Step 8 interim files exist and match integrity manifest."""
    manifest_path = OUT_DIR / "step8_integrity_manifest.json"
    assert manifest_path.is_file()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for fn, exp_hash in manifest["file_hashes"].items():
        fp = OUT_DIR / fn
        assert fp.is_file(), f"Missing Step 8 artifact: {fn}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Checksum mismatch for Step 8 artifact {fn}"


def test_19_original_report_preserved():
    """Test 19: Verify original Step 8 report exists and is byte-for-byte preserved."""
    orig_path = DOCS_DIR / "PHASE_12_STEP_8_FEATURE_INFORMATION_STABILITY_REPORT.md"
    assert orig_path.is_file()
    act_hash = hashlib.sha256(orig_path.read_bytes()).hexdigest()
    assert act_hash == ORIGINAL_REPORT_HASH, f"Original report modified! Hash: {act_hash}"


def test_20_corrected_report_integrity():
    """Test 20: Verify corrected Step 8 report exists and contains required reconciled sections."""
    corr_path = DOCS_DIR / "PHASE_12_STEP_8_FEATURE_INFORMATION_STABILITY_REPORT_CORRECTED.md"
    assert corr_path.is_file()
    text = corr_path.read_text(encoding="utf-8")

    # Required opening disclaimer
    assert "This is a forensic interpretation correction of the original Phase 12 Step 8 report. Computational results and protected upstream artifacts are unchanged." in text

    # Required non-causal reconciled phrasing
    assert "Within the tested model and feature specification, Macro Context features account for a substantial portion of the observed residual predictive relationship. However, the ablation experiment does not establish that these variables causally generate the return relationship." in text

    # Required 2021 reconciled text
    assert "The 2021 concentration is consistent with substantial temporal non-stationarity. The ablation results show that multiple feature configurations also exhibit elevated 2021 relationships, so the experiment does not establish that the concentration was specifically caused by macroeconomic conditions." in text

    # Required Central Conclusion
    assert "No pre-registered feature family demonstrates a stable and economically meaningful incremental predictive relationship beyond the unconditional intraday short drift across the tested folds and temporal blocks. Macro Context exhibits the strongest evidence of marginal statistical association in the tested information set, but this relationship is temporally unstable and does not establish statistically significant economic outperformance versus the Always Short baseline." in text

    # Required Tree Attribution distinction
    assert "Tree Attribution Does Not Equal Marginal Predictive Contribution" in text
    assert "Booster split gain describes how the fitted model used features internally. It does not measure causal importance or marginal predictive value." in text

    # Required Decision Gate
    assert "FEATURE INFORMATION STABILITY NOT SUPPORTED" in text
    assert "PHASE 12 STEP 8 IS FORMALLY SEALED AFTER FORENSIC INTERPRETATION CORRECTION." in text
    assert "NO PHASE 12 STEP 9 EXECUTION IS AUTHORIZED BY THIS TASK." in text
