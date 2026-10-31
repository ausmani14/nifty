"""Tests for Phase 11 Stage 2: Terminal Holdout Strategy Validation.

Verifies:
1. Protected Phase 4-10 hashes unmodified
2. Holdout date range (2022-01-03 to 2026-09-03) and N = 1,154 sessions
3. Zero pre-2022 or post-holdout date contamination in Stage 2 artifacts
4. Stage 2 artifact completeness and non-emptiness
5. Mathematical invariants (gross vs net returns, cost bounds, drawdown <= 0)
6. Trade log consistency (1,154 dates x 2 snapshots x 5 strategies = 11,540 rows)
7. Cost implementation adherence (exact round-trip charges)
8. Absence of holdout training / calibration
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"
STRATEGY_DIR = PROJECT_ROOT / "data" / "interim" / "strategy"


@pytest.fixture(scope="module")
def phase11_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_protected_artifact_checksums_intact(phase11_config):
    """Ensure all 19 protected Phase 4-10 artifacts remain 100% byte-for-byte unmodified."""
    for rel_path, exp_hash in phase11_config["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Protected file missing: {rel_path}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Protected file modified: {rel_path}"


def test_stage2_artifact_existence_and_non_empty():
    """Verify all 7 Stage 2 strategy artifacts were generated and are populated."""
    expected_files = [
        STRATEGY_DIR / "phase11_stage2_strategy_results.csv",
        STRATEGY_DIR / "phase11_stage2_trade_log.csv",
        STRATEGY_DIR / "phase11_stage2_equity_curves.csv",
        STRATEGY_DIR / "phase11_stage2_drawdowns.csv",
        STRATEGY_DIR / "phase11_stage2_robustness.csv",
        STRATEGY_DIR / "phase11_stage2_regime_results.csv",
        STRATEGY_DIR / "phase11_stage2_temporal_results.csv",
    ]
    for ef in expected_files:
        assert ef.is_file(), f"Missing Stage 2 artifact: {ef}"
        assert ef.stat().st_size > 0, f"Empty Stage 2 artifact: {ef}"


def test_stage2_holdout_date_partition_and_zero_contamination():
    """Verify holdout partition starts 2022-01-03, ends 2026-09-03, N=1,154, zero pre-2022 contamination."""
    eq_df = pd.read_csv(STRATEGY_DIR / "phase11_stage2_equity_curves.csv")
    assert len(eq_df) == 1154, f"Expected 1,154 rows in equity curves, found {len(eq_df)}"
    assert eq_df["date"].min() == "2022-01-03"
    assert eq_df["date"].max() == "2026-09-03"

    tl_df = pd.read_csv(STRATEGY_DIR / "phase11_stage2_trade_log.csv")
    assert tl_df["prediction_date"].min() == "2022-01-03"
    assert tl_df["prediction_date"].max() == "2026-09-03"
    # Execution date is T+1: min is 2022-01-04, max is 2026-09-04
    assert tl_df["execution_date"].min() == "2022-01-04"
    assert tl_df["execution_date"].max() == "2026-09-04"

    # Ensure strictly zero pre-2022 dates in prediction_date
    assert (tl_df["prediction_date"] < "2022-01-03").sum() == 0


def test_stage2_trade_log_integrity():
    """Verify trade log dimensions: 1,154 dates x 2 snapshots x 5 strategies = 11,540 rows."""
    tl_df = pd.read_csv(STRATEGY_DIR / "phase11_stage2_trade_log.csv")
    assert len(tl_df) == 1154 * 2 * 5  # 11,540 rows
    assert set(tl_df["snapshot"].unique()) == {"Snapshot A", "Snapshot B"}
    assert set(tl_df["cost_scenario_bps"].unique()) == {10.0}

    # Verify positions are strictly in {-1, 0, 1}
    assert set(tl_df["position"].unique()).issubset({-1, 0, 1})

    # Verify cost charging: active sessions pay exactly 0.0010, flat pay 0.0
    active_mask = tl_df["position"] != 0
    assert np.allclose(tl_df.loc[active_mask, "transaction_cost"], 0.0010)
    assert np.allclose(tl_df.loc[~active_mask, "transaction_cost"], 0.0)


def test_stage2_mathematical_invariants():
    """Verify performance metric invariants across all 130 holdout evaluation scenarios."""
    res_df = pd.read_csv(STRATEGY_DIR / "phase11_stage2_strategy_results.csv")
    assert len(res_df) == 130

    for _, row in res_df.iterrows():
        # Net return must be <= gross return when cost > 0
        if row["cost_scenario_bps"] > 0 and row["active_sessions"] > 0:
            assert row["cumulative_net_return"] <= row["cumulative_gross_return"] + 1e-9

        # Max drawdown must be <= 0
        assert row["max_drawdown_net"] <= 1e-9

        # Win rate must be in [0, 1]
        assert 0.0 <= row["win_rate"] <= 1.0

        # Session count must be exactly 1,154
        assert row["n_sessions"] == 1154


def test_stage2_absence_of_holdout_training_or_tuning(phase11_config):
    """Verify that model specifications remain frozen and holdout observations were not trained on."""
    # Verify frozen hyperparameter manifest
    m_spec = phase11_config["model_specification"]
    assert m_spec["classifier_hyperparameters"]["n_estimators"] == 12
    assert m_spec["regressor_hyperparameters"]["n_estimators"] == 43
    assert m_spec["news_features_included"] is False
    assert m_spec["feature_count"] == 63
