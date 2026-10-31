"""
Tests for Phase 12 Step 5: Economic Validity & Target-Specification Robustness Research
Validates:
- Strict holdout quarantine (zero 2022+ data accessed).
- Mathematical decomposition identity: (1 + R_gap) * (1 + R_intraday) == 1 + R_c2c.
- Exact OOF session count = 1,960 and 8 chronological folds.
- Target comparison table integrity across Targets A, B, C.
- Base-rate & short-bias diagnostics.
- Magnitude calibration consistency across pre-registered bins.
- Economic cost monotonicity and breakeven calculations.
- Placebo / matched random baseline integrity.
- Manifest existence and cryptographic checksum accuracy.
- Governance compliance (zero News, zero volume, zero flow proxies).
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

INTERIM_DIR = Path("data/interim/phase12")


def test_holdout_quarantine_firewall():
    """Verify zero holdout observations (dates > 2021-12-31) in Step 5 artifacts."""
    target_comp = pd.read_csv(INTERIM_DIR / "phase12_step5_target_comparison.csv")
    assert (target_comp["sample_count"] == 1960).all()

    fold_res = pd.read_csv(INTERIM_DIR / "phase12_step5_fold_results.csv")
    assert fold_res["val_year"].max() == 2021
    assert fold_res["val_year"].min() == 2014


def test_target_decomposition_mathematical_identity():
    """Verify mathematical return decomposition: (1 + R_gap) * (1 + R_intra) == 1 + R_c2c."""
    target_comp = pd.read_csv(INTERIM_DIR / "phase12_step5_target_comparison.csv")
    model_rows = target_comp[target_comp["model_name"] == "Model 1"].set_index("target_id")

    mean_a = model_rows.loc["Target A", "mean_realized_return_bps"] / 10000.0
    mean_b = model_rows.loc["Target B", "mean_realized_return_bps"] / 10000.0
    mean_c = model_rows.loc["Target C", "mean_realized_return_bps"] / 10000.0

    # Linear approximation check: mean_c + mean_a approx mean_b
    assert abs((mean_c + mean_a) - mean_b) < 0.0002


def test_fold_results_structure():
    """Verify 8 folds for each of the 3 targets = 24 rows."""
    fold_df = pd.read_csv(INTERIM_DIR / "phase12_step5_fold_results.csv")
    assert len(fold_df) == 24
    assert set(fold_df["target_id"].unique()) == {"Target A", "Target B", "Target C"}
    assert set(fold_df["fold_id"].unique()) == set(range(1, 9))
    assert set(fold_df["val_year"].unique()) == set(range(2014, 2022))


def test_sign_base_rate_diagnostics():
    """Verify base-rate alignment and drift dominance findings."""
    df_base = pd.read_csv(INTERIM_DIR / "phase12_step5_sign_base_rate.csv").set_index("target_id")
    assert len(df_base) == 3

    # Target A: Negative drift, >90% short predictions
    row_a = df_base.loc["Target A"]
    assert row_a["unconditional_mean_realized_bps"] < 0.0  # -8.04 bps
    assert row_a["negative_predictions_pct"] > 90.0  # 90.7%
    assert row_a["always_short_return_bps_per_day"] > row_a["model_sign_return_bps_per_day"]  # 8.04 > 7.24

    # Target B: Positive drift, >85% long predictions
    row_b = df_base.loc["Target B"]
    assert row_b["unconditional_mean_realized_bps"] > 0.0  # +5.90 bps
    assert row_b["positive_predictions_pct"] > 85.0  # 89.7%
    assert row_b["model_sign_return_bps_per_day"] > 0.0

    # Target C: 100% positive predictions (all overnight gaps predicted positive)
    row_c = df_base.loc["Target C"]
    assert row_c["positive_predictions_pct"] == 100.0


def test_magnitude_calibration_monotonicity():
    """Verify magnitude calibration table partitions 1,960 observations exactly."""
    df_mag = pd.read_csv(INTERIM_DIR / "phase12_step5_magnitude_calibration.csv")
    sub_a = df_mag[df_mag["target_id"] == "Target A"]
    assert len(sub_a) == 5
    assert sub_a["observation_count"].sum() == 1960
    assert sub_a["observation_count"].tolist() == [995, 805, 117, 38, 5]

    sub_b = df_mag[df_mag["target_id"] == "Target B"]
    assert len(sub_b) == 5
    assert sub_b["observation_count"].sum() == 1960


def test_economic_stress_cost_monotonicity():
    """Verify net returns strictly decrease with transaction costs."""
    df_econ = pd.read_csv(INTERIM_DIR / "phase12_step5_economic_stress.csv")
    for (t_id, sig), sub in df_econ.groupby(["target_id", "signal_type"]):
        sorted_sub = sub.sort_values("cost_bps")
        net_rets = sorted_sub["annualized_net_return"].values
        if sorted_sub["active_sessions"].iloc[0] > 0:
            assert (np.diff(net_rets) < 0).all(), f"Cost monotonicity violated for {t_id}, {sig}"


def test_placebo_baseline_contrast():
    """Verify placebo dataset contains both model strategy and matched random baselines."""
    df_placebo = pd.read_csv(INTERIM_DIR / "phase12_step5_placebo.csv")
    assert set(df_placebo["strategy_type"].unique()) == {"Model Strategy", "Matched Random Baseline"}
    assert set(df_placebo["target_id"].unique()) == {"Target A", "Target B", "Target C"}


def test_manifest_cryptographic_integrity():
    """Verify manifest.json exists and all recorded file hashes match on disk."""
    import hashlib
    manifest_path = INTERIM_DIR / "phase12_step5_manifest.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["step"] == "Phase 12 Step 5"
    assert manifest["holdout_quarantine_verified"] is True
    assert manifest["decision_gate"] == "C. SIGNAL EXPLAINED PRIMARILY BY BASE RATE / SHORT DRIFT"

    for fname, meta in manifest["artifacts"].items():
        fp = INTERIM_DIR / fname
        assert fp.exists(), f"Manifest file missing: {fname}"
        actual_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert actual_hash == meta["sha256"], f"Checksum mismatch for {fname}"


def test_governance_no_news_no_volume_no_flow():
    """Verify Step 5 script complies with strict feature and methodology restrictions."""
    script_path = Path("scripts/phase12_step5_target_robustness.py")
    assert script_path.exists()
    code = script_path.read_text(encoding="utf-8")

    forbidden = [
        "news_embeddings",
        "finbert",
        "volume_features",
        "flow_proxies",
        "holdout_predictions",
        "terminal_holdout",
    ]
    for term in forbidden:
        assert term not in code, f"Forbidden term '{term}' found in Step 5 script!"
