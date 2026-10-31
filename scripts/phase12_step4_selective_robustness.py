"""
Phase 12 Step 4: Selective Signal Robustness & Statistical Stability Research
Snapshot B 08:50 IST -> Same-Day Open-to-Close Intraday Return

Strict Governance:
- FROZEN DATA ONLY: Uses sealed Step 3 and Step 2 interim outputs.
- ZERO MODEL RETRAINING: No XGBoost training, no new predictions.
- ABSOLUTE TERMINAL HOLDOUT FIREWALL: 2022-01-03 to 2026-09-03 remains untouched and sealed.
- ZERO THRESHOLD OPTIMIZATION: Uses the exact pre-registered grid:
  tau in [0, 5, 10, 15, 20, 25, 30, 40, 50] bps.
- ZERO NEW STRATEGIES / REGIME FILTERS: No stop-losses, leverage, or dynamic sizing.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import scipy.stats as stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
REGIME_DIR = PROJECT_ROOT / "data" / "interim" / "regime"

HOLDOUT_START_DATE = "2022-01-03"
PRED_THRESHOLDS_BPS = [0, 5, 10, 15, 20, 25, 30, 40, 50]
COST_SCENARIOS_BPS = [0.0, 5.0, 10.0, 20.0]

MAGNITUDE_BINS = [
    ("0-5 bps", 0.0, 0.0005),
    ("5-10 bps", 0.0005, 0.0010),
    ("10-15 bps", 0.0010, 0.0015),
    ("15-20 bps", 0.0015, 0.0020),
    ("20+ bps", 0.0020, float("inf")),
]

TEMPORAL_BLOCKS = [
    ("Block A (2014-2016)", 2014, 2016),
    ("Block B (2017-2019)", 2017, 2019),
    ("Block C (2020-2021)", 2020, 2021),
]


def verify_holdout_firewall(df: pd.DataFrame) -> None:
    """Ensure no observation has trading_date beyond 2021-12-31."""
    if "trading_date" in df.columns:
        t_dates = pd.to_datetime(df["trading_date"]).dt.date
        max_date = str(t_dates.max())
        if max_date > "2021-12-31":
            raise ValueError(
                f"FATAL HOLDOUT BREACH: trading_date has date {max_date} > 2021-12-31."
            )


def compute_newey_west_hac_ci(
    returns: np.ndarray, alpha: float = 0.05, max_lags: Optional[int] = None
) -> Tuple[float, float, float, float, float, float]:
    """
    Compute Newey-West HAC mean, standard error, t-statistic, p-value, and (1-alpha) CI.
    Returns: (mean_val, hac_se, t_stat, p_value, ci_lower, ci_upper)
    """
    n = len(returns)
    if n < 2 or np.all(returns == 0.0):
        return 0.0, 0.0, 0.0, 1.0, 0.0, 0.0

    mean_val = float(np.mean(returns))
    e = returns - mean_val
    if np.sum(np.abs(e)) < 1e-14:
        return mean_val, 0.0, 0.0, 1.0, mean_val, mean_val

    if max_lags is None:
        max_lags = int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0))))
        max_lags = max(1, min(max_lags, 20))

    gamma_0 = float(np.dot(e, e) / n)
    hac_var = gamma_0
    for lag in range(1, max_lags + 1):
        weight = 1.0 - (lag / (max_lags + 1.0))
        gamma_l = float(np.dot(e[lag:], e[:-lag]) / n)
        hac_var += 2.0 * weight * gamma_l

    hac_se = math.sqrt(max(1e-14, hac_var / n))
    t_stat = mean_val / hac_se if hac_se > 0 else 0.0
    p_value = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))
    z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
    ci_lower = mean_val - z_crit * hac_se
    ci_upper = mean_val + z_crit * hac_se
    return mean_val, hac_se, t_stat, p_value, ci_lower, ci_upper


def compute_drawdowns(returns: np.ndarray) -> Tuple[float, np.ndarray]:
    """Compute maximum drawdown and drawdown series on cumulative compounded equity."""
    equity = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(np.min(dd)) if len(dd) > 0 else 0.0
    return max_dd, dd


def benjamini_hochberg_fdr(p_values: List[float]) -> np.ndarray:
    """Compute Benjamini-Hochberg FDR-adjusted p-values for multiple comparisons."""
    p_vals = np.array(p_values, dtype=float)
    n = len(p_vals)
    if n == 0:
        return np.array([])
    sorted_indices = np.argsort(p_vals)
    sorted_p = p_vals[sorted_indices]

    adj_p = np.zeros(n)
    for i in range(n):
        rank = i + 1
        adj_p[i] = sorted_p[i] * n / rank

    for i in range(n - 2, -1, -1):
        adj_p[i] = min(adj_p[i], adj_p[i + 1])
    adj_p = np.minimum(adj_p, 1.0)

    orig_adj_p = np.zeros(n)
    orig_adj_p[sorted_indices] = adj_p
    return orig_adj_p


def generate_threshold_stability_table(df: pd.DataFrame) -> pd.DataFrame:
    """Generate threshold stability table across all 9 thresholds and 4 cost scenarios."""
    y_true = df["y_true_intraday"].values
    pred = df["pred_reg_intraday"].values
    n_total = len(df)
    n_years = n_total / 252.0

    rows = []
    for t in PRED_THRESHOLDS_BPS:
        tau = t / 10000.0
        active_mask = np.abs(pred) > tau
        n_act = int(np.sum(active_mask))
        n_inact = n_total - n_act
        pos = np.sign(pred) * active_mask

        # Active trade returns
        if n_act > 0:
            act_gross_rets = (pos * y_true)[active_mask]
            mean_act_gross_bps = float(np.mean(act_gross_rets)) * 10000.0
            med_act_gross_bps = float(np.median(act_gross_rets)) * 10000.0
            win_rate = float(np.mean(act_gross_rets > 0))
            wins = act_gross_rets[act_gross_rets > 0]
            losses = act_gross_rets[act_gross_rets < 0]
            gross_win = float(np.sum(wins)) if len(wins) > 0 else 0.0
            gross_loss = float(np.sum(np.abs(losses))) if len(losses) > 0 else 0.0
            profit_factor = gross_win / gross_loss if gross_loss > 0 else (np.nan if gross_win == 0 else 999.0)
            avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
            avg_loss = float(np.mean(np.abs(losses))) if len(losses) > 0 else 0.0
            payoff_ratio = avg_win / avg_loss if avg_loss > 0 else np.nan
        else:
            mean_act_gross_bps = np.nan
            med_act_gross_bps = np.nan
            win_rate = np.nan
            profit_factor = np.nan
            payoff_ratio = np.nan

        for cost_bps in COST_SCENARIOS_BPS:
            cost_rate = cost_bps / 10000.0
            daily_net_ret = pos * y_true - active_mask * cost_rate
            cum_net = float(np.prod(1.0 + daily_net_ret) - 1.0)
            ann_net = float((1.0 + cum_net) ** (1.0 / n_years) - 1.0) if cum_net > -1.0 else -1.0
            ann_vol = float(np.std(daily_net_ret, ddof=1) * math.sqrt(252.0)) if n_total > 1 else 0.0
            sharpe = (ann_net / ann_vol) if ann_vol > 1e-8 else 0.0
            max_dd, _ = compute_drawdowns(daily_net_ret)

            # Daily HAC CI
            mean_d, se_d, t_d, p_d, lo_d, hi_d = compute_newey_west_hac_ci(daily_net_ret)

            if n_act >= 50:
                tier = "Inferential (N>=50)"
            elif n_act > 0:
                tier = "Descriptive Only (N<50)"
            else:
                tier = "Zero Observations (N=0)"

            rows.append({
                "threshold_bps": t,
                "cost_scenario_bps": cost_bps,
                "active_sessions": n_act,
                "inactive_sessions": n_inact,
                "trades_per_year": float(n_act / n_years),
                "exposure_pct": float(n_act / n_total * 100.0),
                "cumulative_net_return": cum_net,
                "annualized_net_return": ann_net,
                "annualized_volatility": ann_vol,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "mean_return_per_active_trade_bps": mean_act_gross_bps,
                "median_return_per_active_trade_bps": med_act_gross_bps,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "payoff_ratio": payoff_ratio,
                "daily_mean_bps": mean_d * 10000.0,
                "daily_hac_se_bps": se_d * 10000.0,
                "daily_hac_tstat": t_d,
                "daily_hac_pvalue": p_d,
                "daily_ci_lower_95_bps": lo_d * 10000.0,
                "daily_ci_upper_95_bps": hi_d * 10000.0,
                "statistical_tier": tier,
            })

    return pd.DataFrame(rows)


def generate_fold_stability_table(
    df_diag: pd.DataFrame,
    df_step2_fold: pd.DataFrame,
) -> pd.DataFrame:
    """Generate fold stability table across all 8 folds for each threshold."""
    tree_map = dict(zip(df_step2_fold["fold_id"], df_step2_fold["selected_n_trees"]))
    y_true = df_diag["y_true_intraday"].values
    pred = df_diag["pred_reg_intraday"].values
    fold_ids = df_diag["fold_id"].values
    years = pd.to_datetime(df_diag["trading_date"]).dt.year.values

    rows = []
    for f_id in range(1, 9):
        fold_mask = (fold_ids == f_id)
        f_year = int(years[fold_mask][0])
        n_val = int(np.sum(fold_mask))
        n_trees = int(tree_map.get(f_id, -1))
        f_y = y_true[fold_mask]
        f_p = pred[fold_mask]

        for t in PRED_THRESHOLDS_BPS:
            tau = t / 10000.0
            act_mask = np.abs(f_p) > tau
            n_act = int(np.sum(act_mask))
            pos = np.sign(f_p) * act_mask

            if n_act > 0:
                act_gross = (pos * f_y)[act_mask]
                mean_act_ret_bps = float(np.mean(act_gross)) * 10000.0
                med_act_ret_bps = float(np.median(act_gross)) * 10000.0
                dir_acc = float(np.mean(act_gross > 0))
            else:
                mean_act_ret_bps = np.nan
                med_act_ret_bps = np.nan
                dir_acc = np.nan

            y_factor = 252.0 / n_val
            daily_0 = pos * f_y
            daily_5 = pos * f_y - act_mask * 0.0005
            daily_10 = pos * f_y - act_mask * 0.0010
            daily_20 = pos * f_y - act_mask * 0.0020

            ann_0 = float((np.prod(1.0 + daily_0) ** y_factor) - 1.0)
            ann_5 = float((np.prod(1.0 + daily_5) ** y_factor) - 1.0)
            ann_10 = float((np.prod(1.0 + daily_10) ** y_factor) - 1.0)
            ann_20 = float((np.prod(1.0 + daily_20) ** y_factor) - 1.0)

            vol_0 = float(np.std(daily_0, ddof=1) * math.sqrt(252.0)) if n_val > 1 else 0.0
            vol_10 = float(np.std(daily_10, ddof=1) * math.sqrt(252.0)) if n_val > 1 else 0.0
            sharpe_0 = (ann_0 / vol_0) if vol_0 > 1e-8 else 0.0
            sharpe_10 = (ann_10 / vol_10) if vol_10 > 1e-8 else 0.0

            max_dd_10, _ = compute_drawdowns(daily_10)

            rows.append({
                "fold_id": f_id,
                "val_year": f_year,
                "val_sessions": n_val,
                "selected_n_trees": n_trees,
                "threshold_bps": t,
                "active_sessions": n_act,
                "exposure_pct": float(n_act / n_val * 100.0),
                "mean_active_return_bps": mean_act_ret_bps,
                "median_active_return_bps": med_act_ret_bps,
                "directional_accuracy": dir_acc,
                "gross_return_ann": ann_0,
                "net_return_5bps_ann": ann_5,
                "net_return_10bps_ann": ann_10,
                "net_return_20bps_ann": ann_20,
                "sharpe_0bps": sharpe_0,
                "sharpe_10bps": sharpe_10,
                "max_drawdown_10bps": max_dd_10,
                "status": "Active" if n_act > 0 else "Dormant (0 trades)",
            })

    return pd.DataFrame(rows)


def generate_temporal_stability_table(df_diag: pd.DataFrame) -> pd.DataFrame:
    """Generate temporal stability table across the 3 fixed temporal blocks."""
    y_true = df_diag["y_true_intraday"].values
    pred = df_diag["pred_reg_intraday"].values
    years = pd.to_datetime(df_diag["trading_date"]).dt.year.values

    rows = []
    for b_name, start_yr, end_yr in TEMPORAL_BLOCKS:
        b_mask = (years >= start_yr) & (years <= end_yr)
        n_block = int(np.sum(b_mask))
        n_years = n_block / 252.0
        b_y = y_true[b_mask]
        b_p = pred[b_mask]

        for t in PRED_THRESHOLDS_BPS:
            tau = t / 10000.0
            act_mask = np.abs(b_p) > tau
            n_act = int(np.sum(act_mask))
            pos = np.sign(b_p) * act_mask

            if n_act > 0:
                act_gross = (pos * b_y)[act_mask]
                mean_act_ret_bps = float(np.mean(act_gross)) * 10000.0
                med_act_ret_bps = float(np.median(act_gross)) * 10000.0
                win_rate = float(np.mean(act_gross > 0))
                dir_acc = float(np.mean(act_gross > 0))
            else:
                mean_act_ret_bps = np.nan
                med_act_ret_bps = np.nan
                win_rate = np.nan
                dir_acc = np.nan

            daily_0 = pos * b_y
            daily_5 = pos * b_y - act_mask * 0.0005
            daily_10 = pos * b_y - act_mask * 0.0010
            daily_20 = pos * b_y - act_mask * 0.0020

            cum_0 = float(np.prod(1.0 + daily_0) - 1.0)
            cum_5 = float(np.prod(1.0 + daily_5) - 1.0)
            cum_10 = float(np.prod(1.0 + daily_10) - 1.0)
            cum_20 = float(np.prod(1.0 + daily_20) - 1.0)

            ann_0 = float((1.0 + cum_0) ** (1.0 / n_years) - 1.0) if cum_0 > -1.0 else -1.0
            ann_5 = float((1.0 + cum_5) ** (1.0 / n_years) - 1.0) if cum_5 > -1.0 else -1.0
            ann_10 = float((1.0 + cum_10) ** (1.0 / n_years) - 1.0) if cum_10 > -1.0 else -1.0
            ann_20 = float((1.0 + cum_20) ** (1.0 / n_years) - 1.0) if cum_20 > -1.0 else -1.0

            vol_0 = float(np.std(daily_0, ddof=1) * math.sqrt(252.0)) if n_block > 1 else 0.0
            vol_10 = float(np.std(daily_10, ddof=1) * math.sqrt(252.0)) if n_block > 1 else 0.0
            sharpe_0 = (ann_0 / vol_0) if vol_0 > 1e-8 else 0.0
            sharpe_10 = (ann_10 / vol_10) if vol_10 > 1e-8 else 0.0

            max_dd_10, _ = compute_drawdowns(daily_10)

            if n_act >= 50:
                tier = "Inferential (N>=50)"
            elif n_act > 0:
                tier = "Descriptive Only (N<50)"
            else:
                tier = "Zero Observations (N=0)"

            rows.append({
                "block_name": b_name,
                "total_sessions": n_block,
                "threshold_bps": t,
                "active_sessions": n_act,
                "exposure_pct": float(n_act / n_block * 100.0),
                "mean_active_return_bps": mean_act_ret_bps,
                "median_active_return_bps": med_act_ret_bps,
                "gross_return_ann": ann_0,
                "net_return_5bps_ann": ann_5,
                "net_return_10bps_ann": ann_10,
                "net_return_20bps_ann": ann_20,
                "sharpe_0bps": sharpe_0,
                "sharpe_10bps": sharpe_10,
                "max_drawdown_10bps": max_dd_10,
                "win_rate": win_rate,
                "directional_accuracy": dir_acc,
                "statistical_tier": tier,
            })

    return pd.DataFrame(rows)


def generate_magnitude_bins_table(df_diag: pd.DataFrame) -> pd.DataFrame:
    """Generate diagnostic forecast-magnitude monotonicity table."""
    y_true = df_diag["y_true_intraday"].values
    pred = df_diag["pred_reg_intraday"].values
    abs_pred = np.abs(pred)
    n_total = len(df_diag)

    rows = []
    for b_name, low, high in MAGNITUDE_BINS:
        mask = (abs_pred >= low) & (abs_pred < high)
        n_bin = int(np.sum(mask))

        if n_bin > 0:
            p_bin = pred[mask]
            y_bin = y_true[mask]
            long_cnt = int(np.sum(p_bin > 0))
            short_cnt = int(np.sum(p_bin < 0))
            mean_p_bps = float(np.mean(p_bin)) * 10000.0
            med_p_bps = float(np.median(p_bin)) * 10000.0
            mean_y_bps = float(np.mean(y_bin)) * 10000.0
            med_y_bps = float(np.median(y_bin)) * 10000.0
            std_y_bps = float(np.std(y_bin, ddof=1) * 10000.0) if n_bin > 1 else 0.0
            strat_ret_bps = float(np.mean(np.sign(p_bin) * y_bin)) * 10000.0
            dir_acc = float(np.mean(np.sign(p_bin) == np.sign(y_bin)))
            bias_bps = float(np.mean(p_bin - y_bin)) * 10000.0
            mae_bps = float(np.mean(np.abs(p_bin - y_bin))) * 10000.0
            rmse_bps = float(np.sqrt(np.mean((p_bin - y_bin) ** 2))) * 10000.0
        else:
            long_cnt = 0
            short_cnt = 0
            mean_p_bps = np.nan
            med_p_bps = np.nan
            mean_y_bps = np.nan
            med_y_bps = np.nan
            std_y_bps = np.nan
            strat_ret_bps = np.nan
            dir_acc = np.nan
            bias_bps = np.nan
            mae_bps = np.nan
            rmse_bps = np.nan

        if n_bin >= 50:
            tier = "Inferential (N>=50)"
        elif n_bin > 0:
            tier = "Descriptive Only (N<50)"
        else:
            tier = "Zero Observations (N=0)"

        rows.append({
            "bin_name": b_name,
            "min_pred_bps": low * 10000.0,
            "max_pred_bps": (high * 10000.0) if high != float("inf") else 999.0,
            "observation_count": n_bin,
            "pct_of_total": float(n_bin / n_total * 100.0),
            "mean_prediction_bps": mean_p_bps,
            "median_prediction_bps": med_p_bps,
            "mean_realized_return_bps": mean_y_bps,
            "median_realized_return_bps": med_y_bps,
            "std_realized_return_bps": std_y_bps,
            "mean_trade_return_bps": strat_ret_bps,
            "long_count": long_cnt,
            "short_count": short_cnt,
            "long_pct": float(long_cnt / n_bin * 100.0) if n_bin > 0 else 0.0,
            "short_pct": float(short_cnt / n_bin * 100.0) if n_bin > 0 else 0.0,
            "directional_accuracy": dir_acc,
            "mean_prediction_error_bps": bias_bps,
            "mae_bps": mae_bps,
            "rmse_bps": rmse_bps,
            "statistical_tier": tier,
        })

    return pd.DataFrame(rows)


def generate_directional_decomposition_table(df_diag: pd.DataFrame) -> pd.DataFrame:
    """Generate long vs short decomposition across all 9 thresholds."""
    y_true = df_diag["y_true_intraday"].values
    pred = df_diag["pred_reg_intraday"].values

    rows = []
    for t in PRED_THRESHOLDS_BPS:
        tau = t / 10000.0
        long_mask = pred > tau
        short_mask = pred < -tau
        active_mask = long_mask | short_mask

        n_act = int(np.sum(active_mask))
        n_long = int(np.sum(long_mask))
        n_short = int(np.sum(short_mask))

        pct_long = float(n_long / n_act * 100.0) if n_act > 0 else 0.0
        pct_short = float(n_short / n_act * 100.0) if n_act > 0 else 0.0

        mean_realized_long_bps = float(np.mean(y_true[long_mask])) * 10000.0 if n_long > 0 else np.nan
        mean_realized_short_bps = float(np.mean(y_true[short_mask])) * 10000.0 if n_short > 0 else np.nan

        strat_long_bps = mean_realized_long_bps if n_long > 0 else np.nan
        strat_short_bps = -mean_realized_short_bps if n_short > 0 else np.nan

        hit_long = float(np.mean(y_true[long_mask] > 0)) if n_long > 0 else np.nan
        hit_short = float(np.mean(y_true[short_mask] < 0)) if n_short > 0 else np.nan

        if n_act > 0:
            act_strat_rets = np.zeros(n_act)
            act_strat_rets[:n_long] = y_true[long_mask]
            act_strat_rets[n_long:] = -y_true[short_mask]
            total_mean_strat_bps = float(np.mean(act_strat_rets)) * 10000.0
            total_hit_rate = float(np.mean(act_strat_rets > 0))
        else:
            total_mean_strat_bps = np.nan
            total_hit_rate = np.nan

        if not np.isnan(strat_short_bps) and not np.isnan(strat_long_bps):
            asymmetry_spread_bps = strat_short_bps - strat_long_bps
        else:
            asymmetry_spread_bps = np.nan

        if n_act >= 50:
            tier = "Inferential (N>=50)"
        elif n_act > 0:
            tier = "Descriptive Only (N<50)"
        else:
            tier = "Zero Observations (N=0)"

        rows.append({
            "threshold_bps": t,
            "total_active_sessions": n_act,
            "long_count": n_long,
            "short_count": n_short,
            "long_pct": pct_long,
            "short_pct": pct_short,
            "long_mean_realized_return_bps": mean_realized_long_bps,
            "short_mean_realized_return_bps": mean_realized_short_bps,
            "long_trade_return_bps": strat_long_bps,
            "short_trade_return_bps": strat_short_bps,
            "long_hit_rate": hit_long,
            "short_hit_rate": hit_short,
            "active_trade_return_bps": total_mean_strat_bps,
            "active_hit_rate": total_hit_rate,
            "asymmetry_spread_bps": asymmetry_spread_bps,
            "statistical_tier": tier,
        })

    return pd.DataFrame(rows)


def generate_statistical_diagnostics_table(df_diag: pd.DataFrame) -> pd.DataFrame:
    """Generate rigorous Newey-West HAC inference and Benjamini-Hochberg FDR adjustments."""
    y_true = df_diag["y_true_intraday"].values
    pred = df_diag["pred_reg_intraday"].values
    n_total = len(df_diag)
    n_years = n_total / 252.0

    raw_daily_pvals = []
    raw_active_pvals = []
    temp_rows = []

    for t in PRED_THRESHOLDS_BPS:
        tau = t / 10000.0
        active_mask = np.abs(pred) > tau
        n_act = int(np.sum(active_mask))
        pos = np.sign(pred) * active_mask

        daily_net_10bps = pos * y_true - active_mask * 0.0010
        m_d, se_d, t_d, p_d, lo_d, hi_d = compute_newey_west_hac_ci(daily_net_10bps)
        raw_daily_pvals.append(p_d)

        if n_act > 0:
            act_net_10bps = daily_net_10bps[active_mask]
            m_a, se_a, t_a, p_a, lo_a, hi_a = compute_newey_west_hac_ci(act_net_10bps)
            raw_active_pvals.append(p_a)
        else:
            m_a, se_a, t_a, p_a, lo_a, hi_a = 0.0, 0.0, 0.0, 1.0, 0.0, 0.0
            raw_active_pvals.append(1.0)

        if n_act >= 50:
            tier = "Inferential (N>=50)"
        elif n_act > 0:
            tier = "Descriptive Only (N<50)"
        else:
            tier = "Zero Observations (N=0)"

        temp_rows.append({
            "threshold_bps": t,
            "active_sessions": n_act,
            "trades_per_year": float(n_act / n_years),
            "daily_mean_net_bps": m_d * 10000.0,
            "daily_hac_se_bps": se_d * 10000.0,
            "daily_hac_tstat": t_d,
            "daily_hac_pvalue": p_d,
            "daily_ci_lower_95_bps": lo_d * 10000.0,
            "daily_ci_upper_95_bps": hi_d * 10000.0,
            "active_mean_net_bps": m_a * 10000.0 if n_act > 0 else np.nan,
            "active_hac_se_bps": se_a * 10000.0 if n_act > 0 else np.nan,
            "active_hac_tstat": t_a if n_act > 0 else np.nan,
            "active_hac_pvalue": p_a if n_act > 0 else np.nan,
            "active_ci_lower_95_bps": lo_a * 10000.0 if n_act > 0 else np.nan,
            "active_ci_upper_95_bps": hi_a * 10000.0 if n_act > 0 else np.nan,
            "statistical_tier": tier,
        })

    adj_daily_pvals = benjamini_hochberg_fdr(raw_daily_pvals)
    adj_active_pvals = benjamini_hochberg_fdr(raw_active_pvals)

    for i, row in enumerate(temp_rows):
        row["daily_fdr_adjusted_pvalue"] = float(adj_daily_pvals[i])
        row["active_fdr_adjusted_pvalue"] = float(adj_active_pvals[i])
        row["fdr_significant_at_05"] = bool(adj_daily_pvals[i] < 0.05)

    return pd.DataFrame(temp_rows)


def run_phase12_step4_robustness() -> Dict[str, Any]:
    """Execute complete Phase 12 Step 4 robustness research workflow."""
    print("=" * 70)
    print("PHASE 12 STEP 4: SELECTIVE SIGNAL ROBUSTNESS RESEARCH")
    print("=" * 70)

    diag_path = INTERIM_DIR / "step3_selective_diagnostics.csv"
    if not diag_path.exists():
        raise FileNotFoundError(f"Missing required Step 3 input: {diag_path}")
    df_diag = pd.read_csv(diag_path)
    print(f"Loaded Step 3 diagnostics: N={len(df_diag)} rows.")

    verify_holdout_firewall(df_diag)
    print(f"Holdout firewall confirmed: Max trading_date={df_diag['trading_date'].max()} <= 2021-12-31.")

    s2_fold_path = INTERIM_DIR / "snapshot_b_intraday_fold_results.csv"
    if not s2_fold_path.exists():
        raise FileNotFoundError(f"Missing Step 2 fold results: {s2_fold_path}")
    df_s2_fold = pd.read_csv(s2_fold_path)

    print("\n1. Generating threshold stability table...")
    df_thresh = generate_threshold_stability_table(df_diag)
    thresh_out = INTERIM_DIR / "step4_threshold_stability.csv"
    df_thresh.to_csv(thresh_out, index=False)
    print(f"   Saved {thresh_out.name} ({len(df_thresh)} rows).")

    print("\n2. Generating fold stability table...")
    df_fold = generate_fold_stability_table(df_diag, df_s2_fold)
    fold_out = INTERIM_DIR / "step4_fold_stability.csv"
    df_fold.to_csv(fold_out, index=False)
    print(f"   Saved {fold_out.name} ({len(df_fold)} rows).")

    print("\n3. Generating temporal block stability table...")
    df_temp = generate_temporal_stability_table(df_diag)
    temp_out = INTERIM_DIR / "step4_temporal_stability.csv"
    df_temp.to_csv(temp_out, index=False)
    print(f"   Saved {temp_out.name} ({len(df_temp)} rows).")

    print("\n4. Generating magnitude bins table...")
    df_bins = generate_magnitude_bins_table(df_diag)
    bins_out = INTERIM_DIR / "step4_magnitude_bins.csv"
    df_bins.to_csv(bins_out, index=False)
    print(f"   Saved {bins_out.name} ({len(df_bins)} rows).")

    print("\n5. Generating directional decomposition table...")
    df_decomp = generate_directional_decomposition_table(df_diag)
    decomp_out = INTERIM_DIR / "step4_directional_decomposition.csv"
    df_decomp.to_csv(decomp_out, index=False)
    print(f"   Saved {decomp_out.name} ({len(df_decomp)} rows).")

    print("\n6. Generating statistical diagnostics table...")
    df_stats = generate_statistical_diagnostics_table(df_diag)
    stats_out = INTERIM_DIR / "step4_statistical_diagnostics.csv"
    df_stats.to_csv(stats_out, index=False)
    print(f"   Saved {stats_out.name} ({len(df_stats)} rows).")

    print("\nAll 6 Step 4 datasets generated successfully.")
    print("=" * 70)
    return {
        "df_thresh": df_thresh,
        "df_fold": df_fold,
        "df_temp": df_temp,
        "df_bins": df_bins,
        "df_decomp": df_decomp,
        "df_stats": df_stats,
    }


if __name__ == "__main__":
    run_phase12_step4_robustness()
