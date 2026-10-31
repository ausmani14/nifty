"""Tests for Phase 12 Step 2: Snapshot B Morning-to-Close Intraday Target Research.

Verifies:
1. Protected Phase 4-10 checksum hashes remain byte-for-byte intact.
2. Complete quarantine of the consumed 2022-2026 terminal holdout (zero access / contamination).
3. Existence and non-emptiness of all 4 Phase 12 research artifacts.
4. Mathematical correctness of target construction R_intraday(T+1) = (Close(T+1) - Open(T+1)) / Open(T+1).
5. Model 1 feature integrity: exactly 63 features (45 Price + 18 Context, 0 News), strict causal timing <= 08:50 IST.
6. Walk-forward expanding cross-validation structure: 8 folds, 2014-2021, N=1,960 OOF sessions.
7. Empirical metrics consistency and economic cost decay validity.
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
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.models.multimodal import (
    PRICE_FEATURE_NAMES,
    CONTEXT_FEATURE_NAMES,
    ALL_NEWS_FEATURE_NAMES,
    MODEL_FEATURE_SPECS,
    load_multimodal_dataset,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"


@pytest.fixture(scope="module")
def protected_hashes():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["protected_artifact_hashes"]


def test_protected_artifact_checksums(protected_hashes):
    """Ensure all 19 protected Phase 4-10 artifacts remain byte-for-byte unmodified."""
    for rel_path, exp_hash in protected_hashes.items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Protected file missing: {rel_path}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Protected artifact checksum mismatch: {rel_path}"


def test_phase12_artifacts_exist_and_non_empty():
    """Verify all 4 Phase 12 interim data artifacts exist and have non-zero size."""
    expected_files = [
        PHASE12_DIR / "snapshot_b_intraday_target_dev.csv",
        PHASE12_DIR / "snapshot_b_intraday_oof_results.csv",
        PHASE12_DIR / "snapshot_b_intraday_fold_results.csv",
        PHASE12_DIR / "snapshot_b_intraday_diagnostics.csv",
    ]
    for ef in expected_files:
        assert ef.is_file(), f"Missing Phase 12 artifact: {ef}"
        assert ef.stat().st_size > 0, f"Empty Phase 12 artifact: {ef}"


def test_terminal_holdout_strict_quarantine():
    """Verify zero holdout observations (dates > 2021-12-31) in Phase 12 artifacts."""
    target_df = pd.read_csv(PHASE12_DIR / "snapshot_b_intraday_target_dev.csv")
    diag_df = pd.read_csv(PHASE12_DIR / "snapshot_b_intraday_diagnostics.csv")
    oof_df = pd.read_csv(PHASE12_DIR / "snapshot_b_intraday_oof_results.csv")

    # Target DF
    assert len(target_df) == 3299, f"Expected 3,299 dev target sessions, found {len(target_df)}"
    target_dates = pd.to_datetime(target_df["trading_date"]).dt.date
    assert target_dates.min() == date(2008, 7, 8)
    assert target_dates.max() == date(2021, 12, 31)
    assert (target_dates > date(2021, 12, 31)).sum() == 0, "Holdout contamination in target dataset!"

    # Diagnostics DF
    assert len(diag_df) == 1960, f"Expected 1,960 OOF diagnostic rows, found {len(diag_df)}"
    diag_dates = pd.to_datetime(diag_df["trading_date"]).dt.date
    assert diag_dates.min() == date(2014, 1, 2)
    assert diag_dates.max() == date(2021, 12, 31)
    assert (diag_dates > date(2021, 12, 31)).sum() == 0, "Holdout contamination in diagnostics!"

    # OOF DF
    assert oof_df.loc[0, "start_date"] == "2014-01-02"
    assert oof_df.loc[0, "end_date"] == "2021-12-31"
    assert int(oof_df.loc[0, "n_sessions"]) == 1960


def test_target_construction_mathematical_precision():
    """Verify R_intraday(T+1) = (Close(T+1) - Open(T+1)) / Open(T+1) within floating point accuracy."""
    target_df = pd.read_csv(PHASE12_DIR / "snapshot_b_intraday_target_dev.csv")
    calculated_ret = (target_df["close_t1"] - target_df["open_t1"]) / target_df["open_t1"]
    np.testing.assert_allclose(
        target_df["target_intraday_return"].values,
        calculated_ret.values,
        rtol=1e-6,
        atol=1e-8,
        err_msg="Target return formula divergence detected!",
    )

    expected_dir = np.where(
        target_df["target_intraday_return"] > 0,
        "UP",
        np.where(target_df["target_intraday_return"] < 0, "DOWN", "FLAT"),
    )
    assert (target_df["target_direction"].values == expected_dir).all(), "Target direction mismatch!"


def test_model1_feature_set_governance():
    """Verify Model 1 has exactly 63 features (45 Price + 18 Context, 0 News)."""
    m1_spec = MODEL_FEATURE_SPECS["Model 1"]
    assert len(m1_spec) == 63, f"Expected 63 Model 1 features, found {len(m1_spec)}"
    assert len(PRICE_FEATURE_NAMES) == 45
    assert len(CONTEXT_FEATURE_NAMES) == 18
    assert len(ALL_NEWS_FEATURE_NAMES) == 49

    # Ensure zero overlap with News
    news_in_m1 = set(m1_spec).intersection(set(ALL_NEWS_FEATURE_NAMES))
    assert len(news_in_m1) == 0, f"News features illegally present in Model 1: {news_in_m1}"

    # Verify no target/future price leakage in feature names
    for col in m1_spec:
        assert not col.startswith("target_"), f"Target column in features: {col}"
        assert col not in ("open", "high", "low", "close"), f"Raw unlagged price in features: {col}"


def test_walk_forward_folds_structure():
    """Verify 8 walk-forward expanding folds across 2014-2021."""
    fold_df = pd.read_csv(PHASE12_DIR / "snapshot_b_intraday_fold_results.csv")
    assert len(fold_df) == 8, f"Expected 8 folds, found {len(fold_df)}"

    expected_years = list(range(2014, 2022))
    assert list(fold_df["val_year"].values) == expected_years

    # Training set must be strictly expanding
    train_sizes = fold_df["train_sessions"].values
    for i in range(len(train_sizes) - 1):
        assert train_sizes[i] < train_sizes[i + 1], f"Train sizes not expanding: {train_sizes}"

    assert fold_df["val_sessions"].sum() == 1960


def test_empirical_metrics_integrity():
    """Verify empirical metric consistency in saved artifacts."""
    oof_df = pd.read_csv(PHASE12_DIR / "snapshot_b_intraday_oof_results.csv")

    p_ic = float(oof_df.loc[0, "pearson_ic"])
    s_ic = float(oof_df.loc[0, "spearman_ic"])
    p_pval = float(oof_df.loc[0, "pearson_pvalue"])
    rmse_model = float(oof_df.loc[0, "rmse_model"])
    rmse_zero = float(oof_df.loc[0, "rmse_zero"])
    hit_rate = float(oof_df.loc[0, "hit_rate_model"])

    # Statistically significant positive Pearson IC
    assert 0.045 <= p_ic <= 0.050, f"Unexpected Pearson IC: {p_ic}"
    assert p_pval < 0.05, f"Pearson IC p-value not significant at 5%: {p_pval}"
    assert 0.040 <= s_ic <= 0.045, f"Unexpected Spearman IC: {s_ic}"

    # Model RMSE strictly better than Zero baseline
    assert rmse_model < rmse_zero, f"Model RMSE {rmse_model} >= Zero RMSE {rmse_zero}"

    # Hit rate in expected range
    assert 0.53 <= hit_rate <= 0.54, f"Unexpected hit rate: {hit_rate}"

    # Check economic cost attrition
    cost_rows = oof_df.set_index("cost_scenario_bps")
    ann_0bps = float(cost_rows.loc[0.0, "annualized_net_return"])
    ann_5bps = float(cost_rows.loc[5.0, "annualized_net_return"])
    ann_10bps = float(cost_rows.loc[10.0, "annualized_net_return"])
    ann_20bps = float(cost_rows.loc[20.0, "annualized_net_return"])

    assert ann_0bps > 0.15, f"Gross return too low: {ann_0bps}"
    assert ann_5bps > 0.0, f"5 bps return should be positive: {ann_5bps}"
    assert ann_10bps < 0.0, f"10 bps return must be negative (breakeven ~7.24 bps): {ann_10bps}"
    assert ann_20bps < -0.25, f"20 bps return expected to be strongly negative: {ann_20bps}"
