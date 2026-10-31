"""Comprehensive test suite for Phase 11 Stage 1: Out-of-Sample Strategy Validation.

Verifies:
1. Protected Phase 1-10 input hash preservation.
2. Generation and schema integrity of all 7 Phase 11 CSV artifacts.
3. Strict zero-contamination holdout isolation (no dates >= 2022-01-01).
4. Mathematical consistency of gross vs net returns and transaction cost degradation.
5. Strategy 0 baseline invariants (always flat, zero return, zero drawdown).
6. Trade log row counts, price positivity, and direction validity.
7. Parameter robustness and temporal stability completeness.
"""

from datetime import date
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT

STRATEGY_DIR = PROJECT_ROOT / "data" / "interim" / "strategy"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"


def test_protected_artifact_hashes() -> None:
    """Ensure all Phase 4-10 sealed artifacts remain completely untouched."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    for rel_path, expected_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Missing protected file: {rel_path}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == expected_hash, f"Hash mismatch for {rel_path}"


def test_all_phase11_strategy_artifacts_exist_and_nonempty() -> None:
    """Verify all 7 Strategy CSV artifacts exist and are non-empty."""
    expected_files = [
        STRATEGY_DIR / "phase11_strategy_results.csv",
        STRATEGY_DIR / "phase11_trade_log.csv",
        STRATEGY_DIR / "phase11_equity_curves.csv",
        STRATEGY_DIR / "phase11_drawdowns.csv",
        STRATEGY_DIR / "phase11_robustness.csv",
        STRATEGY_DIR / "phase11_regime_results.csv",
        STRATEGY_DIR / "phase11_temporal_results.csv",
    ]
    for p in expected_files:
        assert p.is_file(), f"Missing Phase 11 artifact: {p}"
        assert p.stat().st_size > 0, f"Artifact is empty: {p}"


def test_strategy_results_invariants() -> None:
    """Verify strategy results metrics and mathematical relationships."""
    df = pd.read_csv(STRATEGY_DIR / "phase11_strategy_results.csv")
    assert len(df) == 130

    for snap in ["Snapshot A", "Snapshot B"]:
        snap_df = df[df["snapshot"] == snap]
        assert len(snap_df) == 65

        # Strategy 0 invariants
        s0 = snap_df[snap_df["strategy_id"] == "Strategy 0"]
        assert len(s0) == 5  # 4 OTC cost scenarios + 1 CTC
        for _, r in s0.iterrows():
            assert r["cumulative_net_return"] == 0.0
            assert r["max_drawdown_net"] == 0.0
            assert r["active_sessions"] == 0
            assert r["trade_count"] == 0

        # Cost degradation must be non-positive (net <= gross)
        for _, r in snap_df.iterrows():
            assert r["cost_degradation"] <= 1e-9
            assert r["cumulative_net_return"] <= r["cumulative_gross_return"] + 1e-9
            assert 0.0 <= r["win_rate"] <= 1.0
            assert 0.0 <= r["active_session_pct"] <= 1.0


def test_trade_log_integrity() -> None:
    """Verify trade log dates, prices, and direction bounds."""
    df = pd.read_csv(STRATEGY_DIR / "phase11_trade_log.csv")
    assert len(df) == 19600  # 1960 dates * 2 snapshots * 5 tracked strategies

    # Verify no holdout dates exist in trade log
    assert df["prediction_date"].max() == "2021-12-31"
    assert df["prediction_date"].min() == "2014-01-02"

    # Prices and returns
    assert (df["entry_price"] > 0).all()
    assert (df["exit_price"] > 0).all()
    assert set(df["position"].unique()).issubset({-1, 0, 1})
    assert (df["cumulative_equity"] > 0).all()
    assert (df["drawdown"] <= 1e-6).all()
    assert (df["drawdown"] >= -1.0).all()


def test_zero_holdout_contamination_across_all_tables() -> None:
    """Verify strictly zero holdout dates (>= 2022-01-01) enter any Stage 1 output table."""
    eq_df = pd.read_csv(STRATEGY_DIR / "phase11_equity_curves.csv")
    assert eq_df["date"].max() == "2021-12-31"
    assert eq_df["date"].min() == "2014-01-02"
    assert len(eq_df) == 1960

    temp_df = pd.read_csv(STRATEGY_DIR / "phase11_temporal_results.csv")
    assert temp_df["end_date"].max() == "2021-12-31"


def test_robustness_grid_completeness() -> None:
    """Verify the parameter robustness grid covers all pre-registered thresholds and costs."""
    df = pd.read_csv(STRATEGY_DIR / "phase11_robustness.csv")
    assert len(df) == 48  # 2 snapshots * 6 strategies * 4 cost scenarios

    conf_sub = df[df["parameter_family"] == "Confidence Gate"]
    mag_sub = df[df["parameter_family"] == "Magnitude Gate"]

    assert set(conf_sub["threshold_value"].unique()) == {0.40, 0.45, 0.50}
    assert set(mag_sub["threshold_value"].unique()) == {0.0010, 0.0025, 0.0050}
    assert set(df["cost_scenario_bps"].unique()) == {0.0, 5.0, 10.0, 20.0}
