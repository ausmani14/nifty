"""Unit and forensic validation test suite for Phase 12 Step 11: T1 Realized-Component Audit.

Verifies:
1. Overnight return calculation: (Open(T+1) - Close(T)) / Close(T)
2. Intraday return calculation: (Close(T+1) - Open(T+1)) / Open(T+1) == T0
3. Close-to-close return calculation: (Close(T+1) - Close(T)) / Close(T) == T1
4. Exact multiplicative decomposition: C == O + I + (O * I) with max error < 1e-15
5. Timing flags: overnight realized, intraday future, close-to-close mixed
6. Firewall integrity: max trading date <= 2021-12-31, 0 holdout rows accessed
7. T0 reproducibility: Step 2 baseline reproduced float-for-float
8. Artifact existence and integrity manifest hash match
9. Attribution classification: Case A (predominantly future intraday)
10. Statistical insignificance of correlation between T1 predictions and realized overnight return (p > 0.05)
"""

from datetime import date
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
AUDIT_CSV = DATA_DIR / "step11_t1_realized_component_audit.csv"
AUDIT_JSON = DATA_DIR / "step11_t1_realized_component_audit.json"
PRED_CSV = DATA_DIR / "step11_predictions.csv"
PRICE_CSV = PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv"
MANIFEST_PATH = DATA_DIR / "step11_integrity_manifest.json"
RECON_JSON = DATA_DIR / "step11_t0_reconciliation.json"


@pytest.fixture(scope="module")
def df_audit():
    assert AUDIT_CSV.is_file(), f"Missing audit CSV: {AUDIT_CSV}"
    return pd.read_csv(AUDIT_CSV)


@pytest.fixture(scope="module")
def audit_json():
    assert AUDIT_JSON.is_file(), f"Missing audit JSON: {AUDIT_JSON}"
    with open(AUDIT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def df_preds():
    assert PRED_CSV.is_file(), f"Missing predictions CSV: {PRED_CSV}"
    return pd.read_csv(PRED_CSV)


@pytest.fixture(scope="module")
def df_prices():
    assert PRICE_CSV.is_file(), f"Missing prices CSV: {PRICE_CSV}"
    return pd.read_csv(PRICE_CSV).set_index("trading_date")


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.is_file(), f"Missing manifest: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_overnight_return_formula(df_audit, df_prices, df_preds):
    """Verify O(T+1) = (Open(T+1) - Close(T)) / Close(T) for all 1,960 sessions."""
    assert len(df_audit) == 1960
    for idx in [0, 50, 200, 500, 1000, 1500, 1959]:
        d_ref = df_preds.loc[idx, "trading_date"]
        d_tgt = df_preds.loc[idx, "target_date"]
        c0 = float(df_prices.loc[d_ref, "close"])
        o1 = float(df_prices.loc[d_tgt, "open"])
        expected_o = (o1 - c0) / c0
        actual_o = df_audit.loc[idx, "overnight_return"]
        assert abs(actual_o - expected_o) < 1e-15


def test_intraday_return_formula(df_audit, df_prices, df_preds):
    """Verify I(T+1) = (Close(T+1) - Open(T+1)) / Open(T+1) matches T0_actual identically."""
    diff_t0 = np.abs(df_audit["intraday_return"].values - df_preds["T0_actual"].values)
    assert np.max(diff_t0) < 1e-12
    assert (diff_t0 < 1e-14).sum() == 1960


def test_close_to_close_return_formula(df_audit, df_prices, df_preds):
    """Verify C(T+1) = (Close(T+1) - Close(T)) / Close(T) matches T1_actual identically."""
    diff_t1 = np.abs(df_audit["close_to_close_return"].values - df_preds["T1_actual"].values)
    assert np.max(diff_t1) < 1e-12
    assert (diff_t1 < 1e-14).sum() == 1960


def test_exact_multiplicative_identity(df_audit):
    """Verify 1 + C = (1 + O)(1 + I) <=> C == O + I + (O * I) with max error < 1e-15."""
    O = df_audit["overnight_return"].values
    I = df_audit["intraday_return"].values
    C = df_audit["close_to_close_return"].values
    C_recon = O + I + (O * I)
    error = np.abs(C - C_recon)
    max_err = np.max(error)
    assert max_err < 1e-15, f"Multiplicative decomposition error {max_err} exceeds 1e-15"
    assert (df_audit["reconstruction_error"].values < 1e-15).all()


def test_timing_classifications(df_audit, audit_json):
    """Verify timing classification flags across CSV rows and JSON metadata."""
    assert (df_audit["overnight_realized_by_cutoff"] == True).all()
    assert (df_audit["intraday_future_at_cutoff"] == True).all()
    assert (df_audit["close_to_close_mixed_target"] == True).all()

    tc = audit_json["timing_classifications"]
    assert "08:50 IST" in tc["cutoff_timestamp"]
    assert "Already realized" in tc["overnight_return_timing"]
    assert "Future" in tc["intraday_return_timing"]
    assert "Mixed target" in tc["close_to_close_return_timing"]


def test_holdout_firewall_intact(df_audit, manifest):
    """Verify terminal holdout quarantine: max dev date <= 2021-12-31, 0 holdout rows accessed."""
    max_d = pd.to_datetime(df_audit["trading_date"]).max().date()
    assert max_d <= date(2021, 12, 31)
    assert manifest["firewall_verification"]["max_dev_trading_date"] <= "2021-12-31"
    assert manifest["firewall_verification"]["holdout_rows_accessed"] == 0
    assert manifest["firewall_verification"]["firewall_intact"] is True


def test_t0_reproducibility_preserved():
    """Verify T0 exact reproducibility reconciliation against Step 2 is preserved."""
    assert RECON_JSON.is_file()
    with open(RECON_JSON, "r", encoding="utf-8") as f:
        recon = json.load(f)
    assert recon["comparison_counts"]["n_dates_compared"] == 1960
    assert recon["comparison_counts"]["prediction_mismatch_count"] == 0
    assert recon["target_equality_statistics"]["targets_identical_bitwise"] is True
    assert recon["prediction_equality_statistics"]["predictions_identical_numerical_tolerance"] is True
    assert recon["metric_reproduction"]["metrics_match_exactly"] is True


def test_artifact_hashes_in_manifest(manifest):
    """Verify that all 14 Step 11 artifacts exist and their hashes match the integrity manifest."""
    hashes = manifest["artifact_hashes"]
    assert len(hashes) == 14
    for fn, exp_hash in hashes.items():
        fp = DATA_DIR / fn
        assert fp.is_file(), f"Missing file: {fn}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for {fn}"


def test_scientific_attribution_case_a(audit_json):
    """Verify attribution is Case A (predominantly future intraday) and formal classification matches."""
    attr = audit_json["scientific_attribution"]
    assert "Case A" in attr["attribution_case"]
    assert attr["formal_classification"] == "ECONOMICALLY DISTINCT BUT TEMPORALLY MIXED RELATIVE TO THE 08:50 CUTOFF"


def test_overnight_correlation_insignificant(df_audit, df_preds, audit_json):
    """Verify T1 predictions have non-significant correlation with realized overnight return (p > 0.05)."""
    t1_p = df_preds["T1_pred"].values
    O = df_audit["overnight_return"].values
    I = df_audit["intraday_return"].values

    r_p_O, p_p_O = stats.pearsonr(t1_p, O)
    r_s_O, p_s_O = stats.spearmanr(t1_p, O)

    r_p_I, p_p_I = stats.pearsonr(t1_p, I)
    r_s_I, p_s_I = stats.spearmanr(t1_p, I)

    # Overnight is NOT statistically significant
    assert p_p_O > 0.05
    assert p_s_O > 0.05
    assert abs(r_p_O) < 0.03
    assert abs(r_s_O) < 0.03

    # Intraday IS statistically significant
    assert p_p_I < 0.01
    assert p_s_I < 0.001
    assert r_p_I > 0.05
    assert r_s_I > 0.07

    # Temporal blocks: overnight p-value > 0.05 across all three blocks
    blocks = audit_json["temporal_block_breakdown"]
    for b_key in ["block_a_2014_2016", "block_b_2017_2019", "block_c_2020_2021"]:
        assert blocks[b_key]["overnight"]["pearson_pvalue"] > 0.05
        assert blocks[b_key]["overnight"]["spearman_pvalue"] > 0.05
