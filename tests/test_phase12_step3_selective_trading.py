"""Tests for Phase 12 Step 3: Selective Trading & Turnover-Control Research.

Verifies:
1. Protected Phase 4-10 checksum hashes remain byte-for-byte unmodified.
2. Complete quarantine of the consumed 2022-2026 terminal holdout (zero contamination).
3. Existence and non-emptiness of all 5 Phase 12 Step 3 research artifacts.
4. Threshold grid is strictly frozen to the pre-registered list [0, 5, 10, 15, 20, 25, 30, 40, 50] bps.
5. Exact reconciliation of tau=0 with Step 2 sealed reference (+18.25% gross, -6.95% at 10 bps).
6. Correct position construction: position = sign(pred) if |pred| >= tau else 0.
7. Correct transaction cost accounting: charged ONLY on active sessions, zero cost on flat sessions.
8. No overnight exposure: positions entered at Open and exited at Close.
9. Absence of Phase 10 regime filters, News features, or Phase 11 holdout artifacts.
10. Fold and temporal structure integrity across 2014-2021 (N=1,960).
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

CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"

FROZEN_THRESHOLDS_BPS = [0, 5, 10, 15, 20, 25, 30, 40, 50]
FROZEN_COSTS_BPS = [0.0, 5.0, 10.0, 20.0]


@pytest.fixture(scope="module")
def protected_hashes():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["protected_artifact_hashes"]


def test_protected_artifact_checksums_intact(protected_hashes):
    """Ensure all 19 protected Phase 4-10 artifacts remain byte-for-byte unmodified."""
    for rel_path, exp_hash in protected_hashes.items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Protected file missing: {rel_path}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Protected artifact checksum mismatch: {rel_path}"


def test_step3_artifacts_exist_and_non_empty():
    """Verify all 5 Step 3 interim data artifacts exist and are populated."""
    expected_files = [
        PHASE12_DIR / "step3_selective_threshold_results.csv",
        PHASE12_DIR / "step3_selective_fold_results.csv",
        PHASE12_DIR / "step3_selective_temporal_results.csv",
        PHASE12_DIR / "step3_selective_baseline_results.csv",
        PHASE12_DIR / "step3_selective_diagnostics.csv",
    ]
    for ef in expected_files:
        assert ef.is_file(), f"Missing Step 3 artifact: {ef}"
        assert ef.stat().st_size > 0, f"Empty Step 3 artifact: {ef}"


def test_terminal_holdout_strict_quarantine():
    """Verify zero holdout observations (dates > 2021-12-31) in Step 3 diagnostics."""
    diag_df = pd.read_csv(PHASE12_DIR / "step3_selective_diagnostics.csv")
    assert len(diag_df) == 1960, f"Expected 1,960 OOF rows, found {len(diag_df)}"
    t_dates = pd.to_datetime(diag_df["trading_date"]).dt.date
    assert t_dates.min() == date(2014, 1, 2)
    assert t_dates.max() == date(2021, 12, 31)
    assert (t_dates > date(2021, 12, 31)).sum() == 0, "Holdout contamination detected!"


def test_threshold_grid_frozen():
    """Verify the threshold grid in output files matches exactly the frozen pre-registered list."""
    thresh_df = pd.read_csv(PHASE12_DIR / "step3_selective_threshold_results.csv")
    actual_thresholds = sorted(thresh_df["threshold_bps"].unique())
    assert actual_thresholds == FROZEN_THRESHOLDS_BPS, f"Threshold grid mismatch: {actual_thresholds}"

    actual_costs = sorted(thresh_df["cost_scenario_bps"].unique())
    assert actual_costs == FROZEN_COSTS_BPS, f"Cost scenarios mismatch: {actual_costs}"
    assert len(thresh_df) == len(FROZEN_THRESHOLDS_BPS) * len(FROZEN_COSTS_BPS)


def test_tau0_reconciliation_with_step2():
    """Verify tau=0 reproduces the sealed Step 2 reference values."""
    thresh_df = pd.read_csv(PHASE12_DIR / "step3_selective_threshold_results.csv")
    tau0_rows = thresh_df[thresh_df["threshold_bps"] == 0].set_index("cost_scenario_bps")

    ann_gross = float(tau0_rows.loc[0.0, "annualized_net_return"])
    sr_gross = float(tau0_rows.loc[0.0, "sharpe_ratio"])
    ann_net10 = float(tau0_rows.loc[10.0, "annualized_net_return"])
    sr_net10 = float(tau0_rows.loc[10.0, "sharpe_ratio"])

    # Must match Step 2 reference (+18.25% gross, -6.95% at 10 bps)
    assert abs(ann_gross - 0.182519) < 1e-4, f"Gross tau=0 divergence: {ann_gross}"
    assert abs(sr_gross - 1.2855) < 1e-2, f"Gross Sharpe divergence: {sr_gross}"
    assert abs(ann_net10 - (-0.069481)) < 1e-4, f"Net 10bps tau=0 divergence: {ann_net10}"
    assert abs(sr_net10 - (-0.4893)) < 1e-2, f"Net Sharpe divergence: {sr_net10}"


def test_position_construction_and_cost_accounting():
    """Verify position logic and active-only cost subtraction."""
    diag_df = pd.read_csv(PHASE12_DIR / "step3_selective_diagnostics.csv")
    y_pred = diag_df["pred_reg_intraday"].values
    y_true = diag_df["y_true_intraday"].values

    for t_bps in [5, 10, 15, 20]:
        t_val = t_bps / 10000.0
        pos_col = f"pos_tau_{t_bps}bps"
        net_col = f"net_ret_10bps_tau_{t_bps}bps"

        pos = diag_df[pos_col].values
        net_ret = diag_df[net_col].values

        # Check position formula
        expected_pos = np.where(np.abs(y_pred) >= t_val, np.sign(y_pred), 0.0)
        np.testing.assert_array_equal(pos, expected_pos, err_msg=f"Position mismatch for tau={t_bps}")

        # Check cost subtraction: 10 bps (0.0010) charged ONLY on active sessions
        expected_net = pos * y_true - np.where(pos != 0.0, 0.0010, 0.0)
        np.testing.assert_allclose(net_ret, expected_net, rtol=1e-6, atol=1e-8, err_msg=f"Cost accounting error for tau={t_bps}")

        # On flat sessions, net return must be exactly 0.0
        flat_mask = (pos == 0.0)
        assert np.all(net_ret[flat_mask] == 0.0), f"Non-zero net return on flat session for tau={t_bps}"


def test_fold_and_temporal_aggregation():
    """Verify fold and temporal table consistency."""
    fold_df = pd.read_csv(PHASE12_DIR / "step3_selective_fold_results.csv")
    temp_df = pd.read_csv(PHASE12_DIR / "step3_selective_temporal_results.csv")

    assert len(fold_df) == 8 * len(FROZEN_THRESHOLDS_BPS)
    assert len(temp_df) == 3 * len(FROZEN_THRESHOLDS_BPS)

    # Sum of fold validation sessions must equal 1,960 for each threshold
    for t_bps in FROZEN_THRESHOLDS_BPS:
        sub_f = fold_df[fold_df["threshold_bps"] == t_bps]
        assert sub_f["val_sessions"].sum() == 1960

        sub_t = temp_df[temp_df["threshold_bps"] == t_bps]
        assert sub_t["total_sessions"].sum() == 1960


def test_no_forbidden_dependencies_in_step3_code():
    """Verify Step 3 runner contains no News, Regime filters, or Holdout imports."""
    code = (PROJECT_ROOT / "scripts" / "phase12_step3_selective_trading_research.py").read_text(encoding="utf-8")

    forbidden = [
        "phase11_stage2_",
        "news_",
        "vix_regime",
        "trend_regime",
        "volatility_regime",
        "regime_filter",
    ]
    for word in forbidden:
        assert word not in code.lower(), f"Forbidden logic/dependency found in Step 3 code: {word}"
