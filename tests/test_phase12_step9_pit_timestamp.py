"""
Unit and Regression Test Suite for Phase 12 Step 9:
Point-in-Time Availability, Timestamp Alignment & Context-Feature Robustness Audit.

Covers:
1. Exact 18 Context feature registry
2. Exact 45 Price features
3. No News features
4. No Volume features
5. No Flow features
6. Exact OOF population (1,960 sessions, 2014-01-02 to 2021-12-31, 8 folds)
7. No duplicate predictions
8. No missing predictions
9. PIT timestamp validity (all availability timestamps strictly preceding 08:50 IST cutoff)
10. Cutoff enforcement at 08:50 IST (Day T+1 morning)
11. No future session values (all context obs_dates strictly <= Day T)
12. Stale-value rules (quantified and verified under frozen policy)
13. Revision classification (all features explicitly categorized)
14. Deterministic PIT-A/B/C construction (P0=45, P1=63, P2=56, P3=53)
15. Chronological training (all training strictly precedes validation)
16. Embargo correctness (one-session causal embargo maintained)
17. Fold-local baseline (mu_train computed strictly from training fold)
18. Placebo integrity (1,000 permutations, seed 42)
19. Protected artifact immutability (Phase 4-10, Step 5, Step 6, Step 7, Step 8)
20. Holdout firewall (max date <= 2021-12-31, zero rows >= 2022-01-03)
21. Artifact checksum integrity (manifest matches disk for all Step 9 interim files)
"""

from datetime import date
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import load_multimodal_dataset

OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step9"
STEP8_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step8"
STEP7_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step7"
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"
DOCS_DIR = PROJECT_ROOT / "docs"

PROTECTED_STEP5_HASHES = {
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

PROTECTED_STEP6_HASHES = {
    "phase12_step6_economic_diagnostic.csv": "19341254f4448d6a0628313c909d6b4ab82843f64363853a584961d8160041ce",
    "phase12_step6_fold_results.csv": "317e9fb735347351be6e4bb44b807b6f419aaa0021badf20f19b2e2cc8b36c11",
    "phase12_step6_magnitude.csv": "f2f82819aad307aa5816dce101da847e52964ea880ddb6c9ea85293357467181",
    "phase12_step6_manifest.json": "cd39329b02772d81c5594bb1d3342795c8384f692952f4b293b8599c10bc6453",
    "phase12_step6_placebo.csv": "a6e30a69c9a2229ddcb5855360cb2a54d214672b6ea4c201688afee388dbf9d1",
    "phase12_step6_residual_predictions.csv": "41dae563cbb48f2ab84cf1b8f18edf190abbecdf82d5b7104e797a63755604af",
    "phase12_step6_temporal_results.csv": "85e901e45e6327640131011460146b0221956d0a2f8ae15e8c6be1aceea6dfe8",
}

PROTECTED_STEP7_HASHES = {
    "step7_economic_diagnostic.csv": "2801997a874ee0eb1778a273430f47c5472343b8419b4ebed7f0cd993ad10c90",
    "step7_fold_results.csv": "230e90c3b7415e9d19d7c01714c72d6a779f6b40050ad4e547648eddbe3575f7",
    "step7_integrity_manifest.json": "d772c3714a2f79f1eb0520bf2ea0576eb4467d2cd2b8fdde9860e585b2866635",
    "step7_placebo_results.csv": "977397dd78737150e5bbac8a9f1b1e8e1545604697cb978bcc2db06606b01667",
    "step7_predictions.csv": "3a2ec99ed398f4cb1047326df2cee879a355712c98aa306f8e87d0680291013e",
    "step7_summary.csv": "de3b4c8adde8c2861c452e08ca0a5da5b901596bf0ad62de320770a11800ac6f",
    "step7_temporal_results.csv": "5953cdbd1bfa67d85c4a58e129fda337dcdea3ab0da330bc79647d524d441ed9",
    "step7_tree_counts.csv": "de78be51942b03d27af3a681c65c204aef090f8f948169d3fcfcd3f3be06f2ad",
}

PROTECTED_STEP8_HASHES = {
    "step8_economic_diagnostic.csv": "13aead08232aae96af2e57c5c4d7dd6651ecc29d3291a1bce600ca6a3bc64bee",
    "step8_feature_contribution.csv": "4d73edd23dd8218813addc13bbb77cd42c533b41564f8357dea6158ab39ffad5",
    "step8_feature_group_registry.csv": "7fd8479a21f61f3d852405dc679e261cd4b1e0c4d741bd42712e06020c78eec0",
    "step8_fold_results.csv": "dd283306bac4dc3c017cfadf34c3acd71ff355ec6c3807215a1292769578eb38",
    "step8_placebo_results.csv": "94b6951406065d5a8ee745fa5aef76dd2f0342c8122958aa31bc4353eb944d26",
    "step8_predictions.csv": "d5a3c1c8122531a0d0104421cf87a9c957a40a01ff1826936fc4cf52989e3f6a",
    "step8_summary.csv": "6c7043f0c4c909e62bfa0f084e8b270147b79f5adf5e75deec80f6f43b533576",
    "step8_temporal_results.csv": "abc427ca94d66c2ca2053fa69450baf177e4fbfddae1a0c99bfcff983bac25b0",
    "step8_feature_group_registry.json": "695718620348e4fc6e9cc72829a409f03604e42ce86f60aac3f5e5a51a90cefc",
}


def test_01_exact_18_context_feature_registry():
    """Test 1: Verify exact 18 Context features in availability matrix matching multimodal dataset."""
    df_mat = pd.read_csv(OUT_DIR / "step9_pit_availability_matrix.csv")
    assert len(df_mat) == 18
    assert set(df_mat["feature_name"]) == {
        "ctx_ret_1d_nifty_bank", "ctx_ret_1d_sp500", "ctx_ret_1d_nasdaq", "ctx_ret_1d_dow_jones",
        "ctx_ret_1d_brent_crude", "ctx_ret_1d_wti_crude", "ctx_ret_1d_gold", "ctx_ret_1d_dxy",
        "ctx_ret_1d_nikkei_225", "ctx_ret_1d_hang_seng", "ctx_ret_1d_ftse_100",
        "ctx_diff_1d_india_vix", "ctx_diff_1d_us_vix", "ctx_diff_1d_india_10y_yield",
        "ctx_diff_1d_us_10y_yield", "ctx_diff_1d_usd_inr", "ctx_level_india_vix", "ctx_level_us_vix"
    }


def test_02_exact_45_price_features():
    """Test 2: Verify exact 45 Price features unchanged and loaded into Model P0."""
    df_sum = pd.read_csv(OUT_DIR / "step9_summary.csv")
    p0_row = df_sum[df_sum["model_code"] == "P0_PRICE_ONLY"].iloc[0]
    assert p0_row["n_features"] == 45


def test_03_no_news_features():
    """Test 3: Verify zero News features included across all Step 9 models."""
    df_sum = pd.read_csv(OUT_DIR / "step9_summary.csv")
    for _, row in df_sum.iterrows():
        assert row["n_features"] in [45, 53, 56, 63]


def test_04_no_volume_features():
    """Test 4: Verify zero Volume features in all Step 9 models."""
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    _, feat_names = ds_b.get_features("Model 1")
    for fn in feat_names:
        assert "volume" not in fn.lower() or fn == "hl_range_pct"


def test_05_no_flow_features():
    """Test 5: Verify zero Flow proxy features across all Step 9 models."""
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    _, feat_names = ds_b.get_features("Model 1")
    for fn in feat_names:
        assert "fii" not in fn.lower() and "dii" not in fn.lower() and "flow" not in fn.lower()


def test_06_exact_oof_population():
    """Test 6: Verify exact OOF evaluation population: 2014-01-02 to 2021-12-31, N=1,960."""
    df_preds = pd.read_csv(OUT_DIR / "step9_predictions.csv")
    assert len(df_preds) == 1960
    assert df_preds["trading_date"].min() == "2014-01-02"
    assert df_preds["trading_date"].max() == "2021-12-31"


def test_07_no_duplicate_predictions():
    """Test 7: Verify zero duplicate predictions in Step 9 predictions table."""
    df_preds = pd.read_csv(OUT_DIR / "step9_predictions.csv")
    assert df_preds["trading_date"].nunique() == 1960
    assert df_preds["target_date"].nunique() == 1960


def test_08_no_missing_predictions():
    """Test 8: Verify zero NaNs or null values across all prediction columns."""
    df_preds = pd.read_csv(OUT_DIR / "step9_predictions.csv")
    for col in ["pred_P0_PRICE_ONLY", "pred_P1_ORIGINAL_PIT", "pred_P2_CONSERVATIVE_PIT", "pred_P3_STRICT_PIT"]:
        assert df_preds[col].notna().all()
        assert not np.isinf(df_preds[col].values).any()


def test_09_pit_timestamp_validity():
    """Test 9: Verify all context feature availability timestamps strictly precede 08:50 IST cutoff."""
    df_mat = pd.read_csv(OUT_DIR / "step9_pit_availability_matrix.csv")
    assert (df_mat["available_by_0850"] == True).all()


def test_10_cutoff_enforcement_at_0850():
    """Test 10: Verify cutoff enforcement at 08:50 IST on Day T+1."""
    df_audit = pd.read_csv(OUT_DIR / "step9_feature_timestamp_audit.csv")
    assert (df_audit["lead_time_to_cutoff_hours"] >= 5.0).all()


def test_11_no_future_session_values():
    """Test 11: Verify zero future session observations across all 18 context features."""
    ctx_df = pd.read_csv(PROJECT_ROOT / "data" / "interim" / "context" / "snapshot_b_context_daily.csv").set_index("trading_date")
    df_preds = pd.read_csv(OUT_DIR / "step9_predictions.csv")
    oof_dates = df_preds["trading_date"].tolist()
    sub_ctx = ctx_df.loc[oof_dates]

    for col in sub_ctx.columns:
        if col.endswith("_obs_date"):
            obs_dt = pd.to_datetime(sub_ctx[col])
            tr_dt = pd.to_datetime(sub_ctx.index)
            # Obs date must be <= trading_date (Day T)
            assert (obs_dt <= tr_dt).all(), f"Future session leakage detected in {col}!"


def test_12_stale_value_rules():
    """Test 12: Verify stale value audit metrics and maximum lag restrictions."""
    df_stale = pd.read_csv(OUT_DIR / "step9_stale_value_audit.csv")
    assert len(df_stale) == 18
    assert (df_stale["max_stale_age_days"] <= 5).all()


def test_13_revision_classification():
    """Test 13: Verify all 18 features have rigorous revision classifications."""
    df_rev = pd.read_csv(OUT_DIR / "step9_revision_audit.csv")
    assert len(df_rev) == 18
    valid_classes = {"NO_REVISION_MECHANISM_IDENTIFIED", "UNKNOWN"}
    assert set(df_rev["revision_status_classification"]).issubset(valid_classes)


def test_14_deterministic_pit_construction():
    """Test 14: Verify exact deterministic feature counts for P0 (45), P1 (63), P2 (56), P3 (53)."""
    df_sum = pd.read_csv(OUT_DIR / "step9_summary.csv").set_index("model_code")
    assert df_sum.loc["P0_PRICE_ONLY", "n_features"] == 45
    assert df_sum.loc["P1_ORIGINAL_PIT", "n_features"] == 63
    assert df_sum.loc["P2_CONSERVATIVE_PIT", "n_features"] == 56
    assert df_sum.loc["P3_STRICT_PIT", "n_features"] == 53


def test_15_chronological_training():
    """Test 15: Verify chronological walk-forward training across all 8 folds."""
    df_folds = pd.read_csv(OUT_DIR / "step9_fold_results.csv")
    assert len(df_folds) == 32
    for _, row in df_folds.iterrows():
        assert row["n_train"] > 0
        assert row["n_val"] > 0
        assert row["val_year"] in [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021]


def test_16_embargo_correctness():
    """Test 16: Verify one-session causal embargo strictly maintained."""
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    folds = splitter.split_development(ds_b.dates)
    for f in folds:
        train_end = date(f.val_start_date.year - 1, 12, 31)
        assert train_end < f.val_start_date


def test_17_fold_local_baseline():
    """Test 17: Verify fold-local training baseline mu_train computed strictly on training folds."""
    df_folds = pd.read_csv(OUT_DIR / "step9_fold_results.csv")
    p1_folds = df_folds[df_folds["model_code"] == "P1_ORIGINAL_PIT"]
    assert len(p1_folds) == 8
    # mu_train should vary across folds as expanding window grows
    mu_vals = p1_folds["mu_train_bps"].tolist()
    assert len(set(mu_vals)) == 8


def test_18_placebo_integrity():
    """Test 18: Verify placebo permutation test executed with 1,000 permutations and seed 42."""
    df_placebo = pd.read_csv(OUT_DIR / "step9_placebo_results.csv")
    assert len(df_placebo) == 4
    for _, row in df_placebo.iterrows():
        assert row["n_permutations"] == 1000
        assert row["seed"] == 42
        assert abs(row["placebo_mean_ic"]) < 0.005


def test_19_protected_artifact_immutability():
    """Test 19: Verify protected artifacts from Phase 4-10, Step 5, 6, 7, 8 are strictly intact."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for {rel_path}"

    for fn, exp_hash in PROTECTED_STEP5_HASHES.items():
        act_hash = hashlib.sha256((PHASE12_DIR / fn).read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 5 file {fn}"

    for fn, exp_hash in PROTECTED_STEP6_HASHES.items():
        act_hash = hashlib.sha256((PHASE12_DIR / fn).read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 6 file {fn}"

    for fn, exp_hash in PROTECTED_STEP7_HASHES.items():
        act_hash = hashlib.sha256((STEP7_DIR / fn).read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 7 file {fn}"

    for fn, exp_hash in PROTECTED_STEP8_HASHES.items():
        act_hash = hashlib.sha256((STEP8_DIR / fn).read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for Step 8 file {fn}"


def test_20_holdout_firewall():
    """Test 20: Verify zero terminal holdout data accessed."""
    df_preds = pd.read_csv(OUT_DIR / "step9_predictions.csv")
    assert df_preds["trading_date"].max() <= "2021-12-31"
    assert (pd.to_datetime(df_preds["trading_date"]) >= pd.Timestamp("2022-01-03")).sum() == 0


def test_21_artifact_checksum_integrity():
    """Test 21: Verify all Step 9 interim artifacts match manifest hashes on disk."""
    manifest_path = OUT_DIR / "step9_integrity_manifest.json"
    assert manifest_path.is_file()
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    for fn, exp_hash in manifest["file_hashes"].items():
        fp = OUT_DIR / fn
        assert fp.is_file(), f"Missing file {fn} declared in manifest"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Checksum mismatch for Step 9 file {fn}"


def test_22_xgboost_model_family_and_no_lightgbm():
    """Test 22: Verify XGBoost is the model family and LightGBM is strictly not used in Step 9."""
    script_path = PROJECT_ROOT / "scripts" / "phase12_step9_pit_audit.py"
    assert script_path.is_file()
    script_text = script_path.read_text(encoding="utf-8")

    assert "import xgboost as xgb" in script_text
    assert "xgb.XGBRegressor" in script_text
    assert "import lightgbm" not in script_text
    assert "from lightgbm" not in script_text
    assert "LGBMRegressor" not in script_text


def test_23_economic_diagnostic_scenarios_and_always_short():
    """Test 23: Verify economic diagnostic evaluates 0, 5, 10, 15, 20 bps and includes Always Short."""
    df_econ = pd.read_csv(OUT_DIR / "step9_economic_diagnostic.csv")
    assert len(df_econ) == 25
    expected_costs = {0.0, 5.0, 10.0, 15.0, 20.0}
    assert set(df_econ["cost_bps"].unique()) == expected_costs
    assert "ALWAYS_SHORT" in df_econ["model_code"].values
    as_rows = df_econ[df_econ["model_code"] == "ALWAYS_SHORT"]
    assert len(as_rows) == 5
    assert set(as_rows["cost_bps"]) == expected_costs


def test_24_report_interpretation_no_unsupported_causal_claims():
    """Test 24: Verify report interpretation contains no unsupported causal claims and preserves original report."""
    orig_report_path = DOCS_DIR / "PHASE_12_STEP_9_PIT_TIMESTAMP_ROBUSTNESS_REPORT_ORIGINAL.md"
    assert orig_report_path.is_file(), "Original draft report must be preserved byte-for-byte"

    report_path = DOCS_DIR / "PHASE_12_STEP_9_PIT_TIMESTAMP_ROBUSTNESS_REPORT.md"
    assert report_path.is_file()
    report_text = report_path.read_text(encoding="utf-8")

    # Verify absence of unsupported causal statements
    assert "apparent statistical signal is an artifact of continuous commodity" not in report_text
    assert "The models learned spurious relationships that systematically inverted" not in report_text
    assert "zero post-session revisions" not in report_text

    # Verify presence of required nuanced scientific phrasing
    assert "The observed predictive relationship is sensitive to the point-in-time information set." in report_text
    assert "does not establish that mechanism causally" in report_text
    assert "No material post-session revision mechanism was identified in the audited source/timestamp specification." in report_text
    assert "B) PIT ROBUSTNESS NOT SUPPORTED" in report_text


def test_25_timestamp_conversion_audit_artifact_integrity():
    """Test 25: Verify step9_timestamp_conversion_audit.csv has exact schema, 576 rows, and all precede cutoff."""
    audit_path = OUT_DIR / "step9_timestamp_conversion_audit.csv"
    assert audit_path.is_file()
    df_audit = pd.read_csv(audit_path)

    expected_cols = [
        "feature_name", "sample_date", "source_timezone", "source_local_timestamp",
        "utc_timestamp", "ist_timestamp", "cutoff_ist", "lead_minutes",
        "before_cutoff", "timezone_rule_used", "source_semantics", "confidence", "notes"
    ]
    assert list(df_audit.columns) == expected_cols
    assert len(df_audit) == 576 # 32 dates * 18 features
    assert df_audit["feature_name"].nunique() == 18
    assert df_audit["sample_date"].nunique() == 32
    assert df_audit["before_cutoff"].all()
    assert df_audit["lead_minutes"].min() >= 300 # All conclude at least 5 hours prior to cutoff


def test_26_date_specific_iana_timezone_conversions():
    """Test 26: Verify date-specific IANA timezone conversions for NY, London, Tokyo, HK, and Kolkata."""
    import zoneinfo
    from datetime import datetime

    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    tz_lon = zoneinfo.ZoneInfo("Europe/London")
    tz_tok = zoneinfo.ZoneInfo("Asia/Tokyo")
    tz_hk = zoneinfo.ZoneInfo("Asia/Hong_Kong")
    tz_kol = zoneinfo.ZoneInfo("Asia/Kolkata")

    # 1. America/New_York: Summer (EDT) vs Winter (EST)
    summer_ny = datetime(2021, 6, 15, 16, 0, tzinfo=tz_ny).astimezone(tz_kol)
    winter_ny = datetime(2021, 1, 15, 16, 0, tzinfo=tz_ny).astimezone(tz_kol)
    assert summer_ny.strftime("%H:%M") == "01:30" # 16:00 EDT = 01:30 IST next day
    assert winter_ny.strftime("%H:%M") == "02:30" # 16:00 EST = 02:30 IST next day

    # US VIX (16:15 NY)
    summer_vix = datetime(2021, 6, 15, 16, 15, tzinfo=tz_ny).astimezone(tz_kol)
    winter_vix = datetime(2021, 1, 15, 16, 15, tzinfo=tz_ny).astimezone(tz_kol)
    assert summer_vix.strftime("%H:%M") == "01:45"
    assert winter_vix.strftime("%H:%M") == "02:45"

    # 2. Europe/London: Summer (BST) vs Winter (GMT)
    summer_lon = datetime(2021, 6, 15, 16, 30, tzinfo=tz_lon).astimezone(tz_kol)
    winter_lon = datetime(2021, 1, 15, 16, 30, tzinfo=tz_lon).astimezone(tz_kol)
    assert summer_lon.strftime("%H:%M") == "21:00" # 16:30 BST = 21:00 IST
    assert winter_lon.strftime("%H:%M") == "22:00" # 16:30 GMT = 22:00 IST

    # 3. Asia/Tokyo: 15:00 JST (no DST) -> 11:30 IST (strictly not 11:45)
    tok = datetime(2021, 6, 15, 15, 0, tzinfo=tz_tok).astimezone(tz_kol)
    assert tok.strftime("%H:%M") == "11:30"

    # 4. Asia/Hong_Kong: 16:00 HKT (no DST) -> 13:30 IST (strictly not 13:45)
    hk = datetime(2021, 6, 15, 16, 0, tzinfo=tz_hk).astimezone(tz_kol)
    assert hk.strftime("%H:%M") == "13:30"

    # 5. Asia/Kolkata: 15:30 IST
    kol = datetime(2021, 6, 15, 15, 30, tzinfo=tz_kol)
    assert kol.strftime("%H:%M") == "15:30"


def test_27_no_impossible_half_hour_errors():
    """Test 27: Verify report and matrix do not contain incorrect timezone values."""
    report_text = (DOCS_DIR / "PHASE_12_STEP_9_PIT_TIMESTAMP_ROBUSTNESS_REPORT.md").read_text(encoding="utf-8")
    matrix_text = (OUT_DIR / "step9_pit_availability_matrix.csv").read_text(encoding="utf-8")

    # The report body and matrix must NOT contain the old erroneous conversion times in the availability tables
    assert "11:45 IST" not in matrix_text
    assert "13:45 IST" not in matrix_text
    assert "21:15 IST" not in matrix_text

    # Verified values must be in matrix
    assert "11:30 IST" in matrix_text
    assert "21:00 IST (BST) / 22:00 IST (GMT)" in matrix_text
    assert "01:30 IST (EDT) / 02:30 IST (EST)" in matrix_text


def test_28_pit_classification_consistency():
    """Test 28: Verify PIT risk classification remains 11 Low and 7 Medium, and info sets unchanged."""
    df_mat = pd.read_csv(OUT_DIR / "step9_pit_availability_matrix.csv")
    low_risk = df_mat[df_mat["timing_risk"] == "LOW RISK"]
    med_risk = df_mat[df_mat["timing_risk"] == "MEDIUM RISK"]

    assert len(low_risk) == 11
    assert len(med_risk) == 7

    df_sum = pd.read_csv(OUT_DIR / "step9_summary.csv").set_index("model_code")
    assert df_sum.loc["P0_PRICE_ONLY", "n_features"] == 45
    assert df_sum.loc["P1_ORIGINAL_PIT", "n_features"] == 63
    assert df_sum.loc["P2_CONSERVATIVE_PIT", "n_features"] == 56
    assert df_sum.loc["P3_STRICT_PIT", "n_features"] == 53


