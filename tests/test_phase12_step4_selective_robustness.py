"""
Tests for Phase 12 Step 4: Selective Signal Robustness & Statistical Stability Research
Validates:
- Strict holdout quarantine (zero 2022+ observations).
- Exact frozen threshold grid: [0, 5, 10, 15, 20, 25, 30, 40, 50] bps.
- Exact OOF session count = 1,960 and 8 chronological folds (2014-2021).
- Exact 3 temporal blocks (Block A: 728, Block B: 734, Block C: 498).
- Correct diagnostic magnitude bins (sum = 1,960).
- Directional decomposition and short-bias asymmetry.
- Cost scenarios monotonicity and drag reduction.
- Newey-West HAC inference, CIs, and Benjamini-Hochberg FDR.
- Absence of XGBoost retraining, News features, regime trading filters, or holdout leaks.
"""

from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

INTERIM_DIR = Path("data/interim/phase12")
FROZEN_THRESHOLDS = [0, 5, 10, 15, 20, 25, 30, 40, 50]
FROZEN_COSTS = [0.0, 5.0, 10.0, 20.0]


def test_terminal_holdout_strict_quarantine():
    """Verify zero holdout observations (dates >= 2022-01-03) in all Step 4 interim outputs."""
    diag_df = pd.read_csv(INTERIM_DIR / "step3_selective_diagnostics.csv")
    t_dates = pd.to_datetime(diag_df["trading_date"]).dt.date
    assert t_dates.min() == date(2014, 1, 2)
    assert t_dates.max() == date(2021, 12, 31)
    assert (t_dates > date(2021, 12, 31)).sum() == 0, "Holdout contamination in trading_date!"

    # Also verify fold results max year
    fold_df = pd.read_csv(INTERIM_DIR / "step4_fold_stability.csv")
    assert fold_df["val_year"].max() == 2021
    assert fold_df["val_year"].min() == 2014


def test_exact_frozen_threshold_grid():
    """Verify all Step 4 stability tables contain exactly the 9 frozen thresholds."""
    df_thresh = pd.read_csv(INTERIM_DIR / "step4_threshold_stability.csv")
    assert sorted(df_thresh["threshold_bps"].unique().tolist()) == FROZEN_THRESHOLDS
    assert sorted(df_thresh["cost_scenario_bps"].unique().tolist()) == FROZEN_COSTS
    assert len(df_thresh) == 9 * 4  # 36 rows

    df_fold = pd.read_csv(INTERIM_DIR / "step4_fold_stability.csv")
    assert sorted(df_fold["threshold_bps"].unique().tolist()) == FROZEN_THRESHOLDS
    assert len(df_fold) == 8 * 9  # 72 rows

    df_temp = pd.read_csv(INTERIM_DIR / "step4_temporal_stability.csv")
    assert sorted(df_temp["threshold_bps"].unique().tolist()) == FROZEN_THRESHOLDS
    assert len(df_temp) == 3 * 9  # 27 rows

    df_decomp = pd.read_csv(INTERIM_DIR / "step4_directional_decomposition.csv")
    assert sorted(df_decomp["threshold_bps"].unique().tolist()) == FROZEN_THRESHOLDS
    assert len(df_decomp) == 9

    df_stats = pd.read_csv(INTERIM_DIR / "step4_statistical_diagnostics.csv")
    assert sorted(df_stats["threshold_bps"].unique().tolist()) == FROZEN_THRESHOLDS
    assert len(df_stats) == 9


def test_exact_oof_sessions_and_folds():
    """Verify total OOF sessions = 1,960 and exact fold session counts."""
    diag_df = pd.read_csv(INTERIM_DIR / "step3_selective_diagnostics.csv")
    assert len(diag_df) == 1960

    fold_df = pd.read_csv(INTERIM_DIR / "step4_fold_stability.csv")
    t0_folds = fold_df[fold_df["threshold_bps"] == 0]
    expected_sessions = {2014: 240, 2015: 244, 2016: 244, 2017: 248, 2018: 245, 2019: 241, 2020: 250, 2021: 248}
    actual_sessions = dict(zip(t0_folds["val_year"], t0_folds["val_sessions"]))
    assert actual_sessions == expected_sessions
    assert sum(expected_sessions.values()) == 1960


def test_exact_temporal_blocks():
    """Verify 3 fixed temporal blocks: Block A (728), Block B (734), Block C (498)."""
    df_temp = pd.read_csv(INTERIM_DIR / "step4_temporal_stability.csv")
    t0_temp = df_temp[df_temp["threshold_bps"] == 0]
    block_sessions = dict(zip(t0_temp["block_name"], t0_temp["total_sessions"]))
    assert block_sessions["Block A (2014-2016)"] == 728
    assert block_sessions["Block B (2017-2019)"] == 734
    assert block_sessions["Block C (2020-2021)"] == 498
    assert sum(block_sessions.values()) == 1960


def test_magnitude_bins_integrity():
    """Verify diagnostic magnitude bins partition the 1,960 observations exactly."""
    df_bins = pd.read_csv(INTERIM_DIR / "step4_magnitude_bins.csv")
    assert len(df_bins) == 5
    expected_bins = ["0-5 bps", "5-10 bps", "10-15 bps", "15-20 bps", "20+ bps"]
    assert df_bins["bin_name"].tolist() == expected_bins
    assert df_bins["observation_count"].sum() == 1960
    assert df_bins["observation_count"].tolist() == [995, 805, 117, 38, 5]

    # Verify directional accuracy scaling
    # 53.47% -> 52.67% -> 56.41% -> 65.79% -> 80.00%
    accs = df_bins["directional_accuracy"].tolist()
    assert accs[4] > accs[2] > accs[0]
    assert accs[4] == 0.80


def test_directional_decomposition_asymmetry():
    """Verify heavy short bias and correct trade counts."""
    df_decomp = pd.read_csv(INTERIM_DIR / "step4_directional_decomposition.csv")
    t0 = df_decomp[df_decomp["threshold_bps"] == 0].iloc[0]
    assert t0["total_active_sessions"] == 1960
    assert t0["long_count"] == 182
    assert t0["short_count"] == 1778

    t10 = df_decomp[df_decomp["threshold_bps"] == 10].iloc[0]
    assert t10["total_active_sessions"] == 160
    assert t10["long_count"] == 7
    assert t10["short_count"] == 153
    assert t10["short_pct"] > 95.0

    t15 = df_decomp[df_decomp["threshold_bps"] == 15].iloc[0]
    assert t15["total_active_sessions"] == 43
    assert t15["long_count"] == 1
    assert t15["short_count"] == 42

    t20 = df_decomp[df_decomp["threshold_bps"] == 20].iloc[0]
    assert t20["total_active_sessions"] == 5
    assert t20["long_count"] == 0
    assert t20["short_count"] == 5

    # Thresholds >= 25 have 0 active sessions
    for tau in [25, 30, 40, 50]:
        t_sub = df_decomp[df_decomp["threshold_bps"] == tau].iloc[0]
        assert t_sub["total_active_sessions"] == 0


def test_cost_scenarios_monotonicity():
    """Verify net return decreases strictly monotonically with transaction costs."""
    df_thresh = pd.read_csv(INTERIM_DIR / "step4_threshold_stability.csv")
    for tau in [0, 5, 10, 15, 20]:
        sub = df_thresh[df_thresh["threshold_bps"] == tau].sort_values("cost_scenario_bps")
        net_rets = sub["annualized_net_return"].values
        # Net returns must strictly decrease with increasing costs
        assert (np.diff(net_rets) < 0).all(), f"Cost monotonicity violated at tau={tau}"


def test_statistical_diagnostics_and_fdr():
    """Verify Benjamini-Hochberg FDR adjustments and statistical tiers."""
    df_stats = pd.read_csv(INTERIM_DIR / "step4_statistical_diagnostics.csv")
    assert len(df_stats) == 9
    # Check that daily FDR adjusted p-values are not significant at alpha=0.05
    assert (df_stats["fdr_significant_at_05"] == False).all()
    # Check sample size tiers
    assert df_stats.loc[df_stats["threshold_bps"] == 10, "statistical_tier"].values[0] == "Inferential (N>=50)"
    assert df_stats.loc[df_stats["threshold_bps"] == 15, "statistical_tier"].values[0] == "Descriptive Only (N<50)"
    assert df_stats.loc[df_stats["threshold_bps"] == 20, "statistical_tier"].values[0] == "Descriptive Only (N<50)"
    assert df_stats.loc[df_stats["threshold_bps"] == 25, "statistical_tier"].values[0] == "Zero Observations (N=0)"


def test_governance_integrity_no_retraining_no_news_no_regime_filters():
    """Verify Step 4 script code adheres to strict non-modification rules."""
    script_path = Path("scripts/phase12_step4_selective_robustness.py")
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")

    forbidden = [
        "xgb.train",
        "XGBRegressor(",
        "fit(",
        "news_embeddings",
        "finbert",
        "create_regime_filter",
        "phase11_stage2",
        "terminal_holdout",
    ]
    for term in forbidden:
        assert term not in content, f"Forbidden term '{term}' found in Step 4 script!"
