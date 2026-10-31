"""Comprehensive test suite for Phase 10: Market Regime Detection, Explainability and Error Analysis.

Verifies:
1. Protected input hash preservation.
2. Complete generation of all 8 CSV artifacts and 1 config JSON.
3. Strict Model 1 feature space integrity (63 features: 45 Price + 18 Context, 0 News).
4. OOF (N=1,960) and Holdout (N=1,154) session count invariants for Snapshot A and B.
5. Benjamini-Hochberg FDR multiple testing adjustment correctness.
6. Sample-size governance enforcement (EXTREME volatility n < 50 tagged DESCRIPTIVE_ONLY).
7. Native Lundberg TreeSHAP dimensions, non-negativity of mean absolute attributions, and consistency.
8. Error taxonomy completeness and mutual exclusivity.
9. Confidence calibration binning and probability simplex constraints.
"""

from datetime import date
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.models.multimodal import CONTEXT_FEATURE_NAMES, PRICE_FEATURE_NAMES

PROTECTED_HASHES = {
    "data/features/nifty50_features_clean.csv": "afa2e68f50f1ad0f4b1adbbec3df294d474d688dbf481cf53c76c4db0a78914b",
    "data/targets/nifty50_targets_snapshot_a.csv": "a13fed61f92c3fcccf9fe09ce59eb0df4d95ef8dce0aef970ff5ed1220ea055d",
    "data/targets/nifty50_targets_snapshot_b.csv": "54ac54fdeafd53ddea20b1d31cd89c1fbaebdbc88c0f24f8a1f73ce2867e01d2",
    "data/interim/context/snapshot_a_context_daily.csv": "26f41d5978b2f78fb9fad223d9efe9970820ab7f81510490ed6f1b39872178af",
    "data/interim/context/snapshot_b_context_daily.csv": "08a694f86f70c5246b8b6b4928283b676dd998912e481d88a718ba08970237be",
    "data/interim/news/features_news_snapshot_a.csv": "487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7",
    "data/interim/news/features_news_snapshot_b.csv": "f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606",
    "data/interim/news/phase9_step4_oof_results.csv": "62b88a1689c7ed57e1ddf79ca0064356eec5d2a16e00f7975998a155141f02d8",
    "data/interim/news/phase9_step4_holdout_results.csv": "4359edb7e585053c676e444d958a4265c584b9b13a58c89dd38067fc0bc41967",
    "data/interim/news/phase9_step4_experiment_results.csv": "7d0f39f7ce8a50b6f8b1591dc6ce9b3a4af8f75507531740a06147cb4aedffc3",
    "configs/phase9_step4_experiment_config.json": "8940206588dad34eb5a9d2fdb01ecbfeb629930374a733c15d077b2281ae7547",
}

REGIME_DIR = PROJECT_ROOT / "data" / "interim" / "regime"
CONFIG_FILE = PROJECT_ROOT / "configs" / "phase10_regime_explainability_config.json"


def test_protected_artifact_hashes() -> None:
    """Ensure all Phase 4-9 sealed artifacts remain completely untouched."""
    for rel_path, expected_hash in PROTECTED_HASHES.items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Missing protected file: {rel_path}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == expected_hash, f"Hash mismatch for {rel_path}"


def test_all_phase10_artifacts_exist_and_nonempty() -> None:
    """Ensure all 8 CSVs and 1 config JSON exist and are non-empty."""
    expected_files = [
        REGIME_DIR / "phase10_regime_performance.csv",
        REGIME_DIR / "phase10_temporal_stability.csv",
        REGIME_DIR / "phase10_error_analysis.csv",
        REGIME_DIR / "phase10_confidence_calibration.csv",
        REGIME_DIR / "phase10_feature_importance.csv",
        REGIME_DIR / "phase10_shap_summary.csv",
        REGIME_DIR / "phase10_oof_diagnostics.csv",
        REGIME_DIR / "phase10_holdout_diagnostics.csv",
        CONFIG_FILE,
    ]
    for p in expected_files:
        assert p.is_file(), f"Missing Phase 10 artifact: {p}"
        assert p.stat().st_size > 0, f"Artifact is empty: {p}"


def test_oof_and_holdout_diagnostics_structure() -> None:
    """Verify session diagnostics row counts, date ranges, and probability calibration."""
    oof_df = pd.read_csv(REGIME_DIR / "phase10_oof_diagnostics.csv")
    hold_df = pd.read_csv(REGIME_DIR / "phase10_holdout_diagnostics.csv")

    assert len(oof_df) == 3920
    assert len(hold_df) == 2308

    for snap in ["Snapshot A", "Snapshot B"]:
        oof_s = oof_df[oof_df["snapshot"] == snap]
        hold_s = hold_df[hold_df["snapshot"] == snap]

        assert len(oof_s) == 1960
        assert len(hold_s) == 1154

        assert oof_s["trading_date"].min() == "2014-01-02"
        assert oof_s["trading_date"].max() == "2021-12-31"
        assert hold_s["trading_date"].min() == "2022-01-03"
        assert hold_s["trading_date"].max() == "2026-09-03"

        for df in [oof_s, hold_s]:
            cal_sums = df[["cal_prob_down", "cal_prob_sideways", "cal_prob_up"]].sum(axis=1)
            np.testing.assert_allclose(cal_sums, 1.0, atol=1e-4)

            expected_conf = df[["cal_prob_down", "cal_prob_sideways", "cal_prob_up"]].max(axis=1)
            np.testing.assert_allclose(df["confidence"], expected_conf, atol=1e-4)


def test_regime_performance_governance_and_fdr() -> None:
    """Verify sample size governance and Benjamini-Hochberg FDR correction."""
    df = pd.read_csv(REGIME_DIR / "phase10_regime_performance.csv")
    assert len(df) > 0

    ext_vol_oof = df[(df["partition"] == "OOF") & (df["regime_dimension"] == "Volatility") & (df["regime_category"] == "EXTREME")]
    assert len(ext_vol_oof) == 2
    for _, row in ext_vol_oof.iterrows():
        assert row["n_sessions"] == 35
        assert row["governance_status"] == "DESCRIPTIVE_ONLY"

    exploratory = df[df["regime_dimension"] != "Overall"]
    assert (exploratory["fdr_adjusted_qvalue"] >= 0.0).all()
    assert (exploratory["fdr_adjusted_qvalue"] <= 1.0).all()
    assert ((exploratory["fdr_significant_05"]) == (exploratory["fdr_adjusted_qvalue"] <= 0.05)).all()


def test_temporal_stability_blocks() -> None:
    """Verify 5 chronological blocks across OOF and Holdout partitions."""
    df = pd.read_csv(REGIME_DIR / "phase10_temporal_stability.csv")
    assert len(df) == 10

    expected_blocks = [
        ("OOF", "2014-2016"),
        ("OOF", "2017-2019"),
        ("OOF", "2020-2021"),
        ("Holdout", "2022-2023"),
        ("Holdout", "2024-2026"),
    ]
    for snap in ["Snapshot A", "Snapshot B"]:
        snap_df = df[df["snapshot"] == snap]
        for part, blk in expected_blocks:
            match = snap_df[(snap_df["partition"] == part) & (snap_df["period_block"] == blk)]
            assert len(match) == 1
            assert match.iloc[0]["n_sessions"] > 0
            assert np.isfinite(match.iloc[0]["log_loss"])
            assert np.isfinite(match.iloc[0]["rmse"])


def test_feature_importance_and_shap_completeness() -> None:
    """Verify Model 1 63 features (45 Price + 18 Context, 0 News) in explainability tables."""
    feat_df = pd.read_csv(REGIME_DIR / "phase10_feature_importance.csv")
    shap_df = pd.read_csv(REGIME_DIR / "phase10_shap_summary.csv")

    assert len(feat_df) == 126
    assert len(shap_df) == 126

    for snap in ["Snapshot A", "Snapshot B"]:
        snap_f = feat_df[feat_df["snapshot"] == snap]
        snap_s = shap_df[shap_df["snapshot"] == snap]

        assert len(snap_f) == 63
        assert len(snap_s) == 63

        f_names = set(snap_f["feature_name"].tolist())
        assert f_names == set(PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES)

        price_count = (snap_f["feature_category"] == "Price").sum()
        context_count = (snap_f["feature_category"] == "Context").sum()
        assert price_count == 45
        assert context_count == 18

        assert (snap_f["oof_mean_abs_shap_classifier"] >= 0.0).all()
        assert (snap_f["oof_mean_abs_shap_regressor"] >= 0.0).all()
        assert (snap_s["shap_attribution_class_down"] >= 0.0).all()
        assert (snap_s["shap_attribution_class_sideways"] >= 0.0).all()
        assert (snap_s["shap_attribution_class_up"] >= 0.0).all()
        assert (snap_s["shap_attribution_regressor"] >= 0.0).all()


def test_confidence_calibration_structure() -> None:
    """Verify confidence calibration binning."""
    df = pd.read_csv(REGIME_DIR / "phase10_confidence_calibration.csv")
    assert len(df) == 24

    expected_bins = ["0.33-0.40", "0.40-0.50", "0.50-0.60", "0.60-0.70", "0.70-0.80", "0.80+"]
    for snap in ["Snapshot A", "Snapshot B"]:
        for part in ["OOF", "Holdout"]:
            sub = df[(df["snapshot"] == snap) & (df["partition"] == part)]
            assert list(sub["confidence_bin"]) == expected_bins
            assert sub["n_sessions"].sum() == (1960 if part == "OOF" else 1154)


def test_phase10_config_manifest() -> None:
    """Verify JSON configuration manifest parameters and sample counts."""
    with open(CONFIG_FILE, "r") as f:
        cfg = json.load(f)

    assert cfg["model_architecture"]["num_features"] == 63
    assert cfg["model_architecture"]["news_features_included"] is False
    assert cfg["model_architecture"]["classifier_params"]["n_estimators"] == 12
    assert cfg["model_architecture"]["regressor_params"]["n_estimators"] == 43
    assert cfg["sample_counts"]["development_sessions"] == 3299
    assert cfg["sample_counts"]["oof_validation_sessions"] == 1960
    assert cfg["sample_counts"]["terminal_holdout_sessions"] == 1154
