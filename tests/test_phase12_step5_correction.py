"""
Unit and Regression Test Suite for Phase 12 Step 5 Correction & Forensic Reconciliation.
Verifies:
1. Always Short identity
2. Always Long identity
3. Paired strategy difference calculation
4. Model return identity
5. Target A reconciliation
6. Target B reconciliation
7. Target C identity
8. Tau=10 reconciliation (active sessions = 160)
9. Breakeven reconciliation (arithmetic vs geometric)
10. Strict holdout quarantine (zero data >= 2022-01-03)
11. Protected artifact checksum integrity
12. Deterministic rerun
"""

import hashlib
import math
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from scipy import stats

INTERIM_DIR = Path("data/interim/phase12")


def test_01_always_short_identity():
    """Verify mean(Always Short) == -mean(R_intraday) exactly."""
    s3 = pd.read_csv(INTERIM_DIR / "step3_selective_diagnostics.csv")
    y_intra = s3["y_true_intraday"].values
    mean_y = np.mean(y_intra)
    mean_as = np.mean(-1.0 * y_intra)
    assert np.isclose(mean_as, -mean_y, atol=1e-15)
    assert np.isclose(mean_y * 10000.0, -8.0363, atol=1e-3)
    assert np.isclose(mean_as * 10000.0, 8.0363, atol=1e-3)


def test_02_always_long_identity():
    """Verify Always Long return equals the mean of the realized target return."""
    sbr_corr = pd.read_csv(INTERIM_DIR / "phase12_step5_corrected_sign_base_rate.csv")
    row_b = sbr_corr[sbr_corr["target_id"] == "Target B"].iloc[0]
    assert np.isclose(row_b["baseline_return_bps_per_day"], row_b["unconditional_mean_realized_bps"], atol=1e-6)
    assert np.isclose(row_b["baseline_return_bps_per_day"], 5.9005, atol=1e-3)


def test_03_paired_strategy_difference():
    """Verify mathematical formula for paired strategy difference."""
    s3 = pd.read_csv(INTERIM_DIR / "step3_selective_diagnostics.csv")
    y = s3["y_true_intraday"].values
    pos = s3["pos_tau_0bps"].values
    r_model = pos * y
    r_as = -1.0 * y
    diff = r_model - r_as

    # Paired diff should be 0 where pos == -1 and 2*y where pos == 1
    assert np.all(diff[pos == -1] == 0.0)
    assert np.all(np.isclose(diff[pos == 1], 2.0 * y[pos == 1], atol=1e-15))
    assert np.isclose(np.mean(diff) * 10000.0, -0.7935, atol=1e-3)


def test_04_model_return_identity():
    """Verify unrestricted model strategy return equals sign(prediction) * realized."""
    s3 = pd.read_csv(INTERIM_DIR / "step3_selective_diagnostics.csv")
    y = s3["y_true_intraday"].values
    p = s3["pred_reg_intraday"].values
    pos = np.sign(p)
    ret_unrestricted = pos * y
    assert np.array_equal(pos, s3["pos_tau_0bps"].values)
    assert np.isclose(np.mean(ret_unrestricted) * 10000.0, 7.2428, atol=1e-3)


def test_05_target_a_reconciliation():
    """Verify Target A paired comparison to Always Short shows zero significant edge."""
    sbr_corr = pd.read_csv(INTERIM_DIR / "phase12_step5_corrected_sign_base_rate.csv")
    row_a = sbr_corr[sbr_corr["target_id"] == "Target A"].iloc[0]
    assert row_a["economic_baseline_name"] == "Always Short"
    assert np.isclose(row_a["paired_difference_mean_bps"], -0.7935, atol=1e-3)
    assert np.isclose(row_a["student_tstat_vs_baseline"], -0.5033, atol=1e-3)
    assert row_a["student_pvalue_vs_baseline"] > 0.50
    assert np.isclose(row_a["hac_tstat_vs_baseline"], -0.5842, atol=1e-3)
    assert row_a["hac_pvalue_vs_baseline"] > 0.50


def test_06_target_b_reconciliation():
    """Verify Target B paired comparison to Always Long shows zero significant edge."""
    sbr_corr = pd.read_csv(INTERIM_DIR / "phase12_step5_corrected_sign_base_rate.csv")
    row_b = sbr_corr[sbr_corr["target_id"] == "Target B"].iloc[0]
    assert row_b["economic_baseline_name"] == "Always Long"
    assert np.isclose(row_b["paired_difference_mean_bps"], 0.8066, atol=1e-3)
    assert np.isclose(row_b["student_tstat_vs_baseline"], 0.6009, atol=1e-3)
    assert row_b["student_pvalue_vs_baseline"] > 0.50
    assert np.isclose(row_b["hac_tstat_vs_baseline"], 0.6519, atol=1e-3)
    assert row_b["hac_pvalue_vs_baseline"] > 0.50


def test_07_target_c_identity():
    """Verify Target C model predicts positive on 100% of sessions and is identical to Always Long."""
    sbr_corr = pd.read_csv(INTERIM_DIR / "phase12_step5_corrected_sign_base_rate.csv")
    row_c = sbr_corr[sbr_corr["target_id"] == "Target C"].iloc[0]
    assert row_c["positive_predictions_count"] == 1960
    assert row_c["negative_predictions_count"] == 0
    assert np.isclose(row_c["paired_difference_mean_bps"], 0.0, atol=1e-12)
    assert np.isclose(row_c["hac_tstat_vs_baseline"], 0.0, atol=1e-12)
    assert row_c["tradable_at_0850"] is False or row_c["tradable_at_0850"] == 0 or str(row_c["tradable_at_0850"]).lower() == "false"


def test_08_tau_10_reconciliation():
    """Verify tau=10 has exactly 160 active sessions (7 long, 153 short) matching Step 3 & 4."""
    s3 = pd.read_csv(INTERIM_DIR / "step3_selective_diagnostics.csv")
    pos_10 = s3["pos_tau_10bps"]
    n_active = int((pos_10 != 0).sum())
    n_long = int((pos_10 == 1).sum())
    n_short = int((pos_10 == -1).sum())
    assert n_active == 160
    assert n_long == 7
    assert n_short == 153
    assert np.isclose(n_short / n_active, 153.0 / 160.0, atol=1e-6)

    es = pd.read_csv(INTERIM_DIR / "phase12_step5_economic_stress.csv")
    es_tau10 = es[(es["target_id"] == "Target A") & (es["signal_type"] == "Diagnostic tau=10bps")]
    assert len(es_tau10) == 4
    for _, row in es_tau10.iterrows():
        assert row["active_sessions"] == 160


def test_09_breakeven_reconciliation():
    """Verify arithmetic and geometric breakeven costs for unrestricted and selective strategies."""
    es_corr = pd.read_csv(INTERIM_DIR / "phase12_step5_corrected_economic_stress.csv")
    row_u = es_corr[(es_corr["target_id"] == "Target A") & (es_corr["cost_bps"] == 0.0) & (es_corr["signal_type"].str.contains("Unrestricted"))].iloc[0]
    row_s = es_corr[(es_corr["target_id"] == "Target A") & (es_corr["cost_bps"] == 0.0) & (es_corr["signal_type"].str.contains("tau=10"))].iloc[0]

    assert np.isclose(row_u["arithmetic_breakeven_cost_bps"], 7.2428, atol=1e-3)
    assert np.isclose(row_u["geometric_breakeven_cost_bps"], 6.8423, atol=1e-3)
    assert np.isclose(row_s["arithmetic_breakeven_cost_bps"], 19.3368, atol=1e-3)
    assert np.isclose(row_s["geometric_breakeven_cost_bps"], 19.0411, atol=1e-3)


def test_10_no_holdout_access():
    """Ensure no Step 5 corrected or interim dataset contains trading dates >= 2022-01-03."""
    for p in INTERIM_DIR.glob("phase12_step5*"):
        if p.suffix == ".csv":
            df = pd.read_csv(p)
            for date_col in ["trading_date", "execution_date", "date"]:
                if date_col in df.columns:
                    dates = pd.to_datetime(df[date_col]).dt.date
                    assert dates.max() <= pd.to_datetime("2021-12-31").date()


def test_11_protected_artifact_checksum_integrity():
    """Verify original Phase 12 Step 5 artifacts exist and match expected SHA-256 hashes."""
    expected_hashes = {
        "phase12_step5_target_comparison.csv": "6ec7040f75d26c5b0f54ce33cded5e6baacaebdadea2b99968fcd2f2880de0d0",
        "phase12_step5_fold_results.csv": "041c75bce9cceb847850ffdc17069494e0c44795b4a78c853e9028859c6e1399",
        "phase12_step5_temporal_results.csv": "f14a859412b7e0ac841c9235f66849adb5ff521b675df698f26ee371d412e788",
        "phase12_step5_sign_base_rate.csv": "2344bcffabd0ea2129c70b4d140e9446836fc042f744089bd196c4d38922dd4d",
        "phase12_step5_magnitude_calibration.csv": "501fc01546929c97a847927f1e227e0e6a74c5e56dcf2abe067db5668f1154ae",
        "phase12_step5_economic_stress.csv": "e1c8f04d74c9ece80999e9dcd425a674b4e91da1bcbb4afb7cf6fe5465bffae6",
        "phase12_step5_placebo.csv": "084416736d8d13555576ee5858876ae59260b88bc452c847896e6aab49a424db",
        "phase12_step5_manifest.json": "acf3d7ce73919ddc8545e0c3a506abd44ef0b5aa8e29fb20865e6a85621db10b",
    }
    for filename, expected_hash in expected_hashes.items():
        filepath = INTERIM_DIR / filename
        assert filepath.exists(), f"Missing protected file: {filename}"
        actual_hash = hashlib.sha256(filepath.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {filename}: expected {expected_hash}, got {actual_hash}"


def test_12_deterministic_rerun():
    """Verify that recomputing paired difference on the data produces identical results."""
    sbr_corr = pd.read_csv(INTERIM_DIR / "phase12_step5_corrected_sign_base_rate.csv")
    s3 = pd.read_csv(INTERIM_DIR / "step3_selective_diagnostics.csv")
    y = s3["y_true_intraday"].values
    pos = s3["pos_tau_0bps"].values
    diff = (pos * y) - (-1.0 * y)
    mean_bps = np.mean(diff) * 10000.0
    recorded_mean = sbr_corr[sbr_corr["target_id"] == "Target A"]["paired_difference_mean_bps"].iloc[0]
    assert np.isclose(mean_bps, recorded_mean, atol=1e-12)
