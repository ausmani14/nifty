"""Phase 12 Step 3: Selective Trading & Turnover-Control Research.

Research Question:
Can selective trading based on the already-generated Snapshot B intraday forecasts reduce turnover
and transaction-cost drag while preserving evidence of predictive value, WITHOUT introducing
post-hoc threshold optimization or data leakage?

Policy:
Position = sign(pred_reg_intraday) if abs(pred_reg_intraday) >= tau else 0
tau in [0, 5, 10, 15, 20, 25, 30, 40, 50] bps

Frictions:
0, 5, 10, 20 bps round-trip per active trade (zero cost on flat sessions).

Governance:
- Uses ONLY the sealed Step 2 development OOF predictions (2014-2021, N=1,960).
- ZERO model retraining, ZERO threshold tuning, ZERO access to 2022-2026 holdout.
"""

from datetime import date
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from nifty_ai.config import PROJECT_ROOT

# Paths
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
STEP2_DIAG_PATH = PHASE12_DIR / "snapshot_b_intraday_diagnostics.csv"
STEP2_FOLD_PATH = PHASE12_DIR / "snapshot_b_intraday_fold_results.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"

OUT_THRESHOLD_CSV = PHASE12_DIR / "step3_selective_threshold_results.csv"
OUT_FOLD_CSV = PHASE12_DIR / "step3_selective_fold_results.csv"
OUT_TEMPORAL_CSV = PHASE12_DIR / "step3_selective_temporal_results.csv"
OUT_BASELINE_CSV = PHASE12_DIR / "step3_selective_baseline_results.csv"
OUT_DIAGNOSTICS_CSV = PHASE12_DIR / "step3_selective_diagnostics.csv"

# Pre-registered threshold grid (in bps and decimal)
THRESHOLDS_BPS = [0, 5, 10, 15, 20, 25, 30, 40, 50]
COST_SCENARIOS_BPS = [0.0, 5.0, 10.0, 20.0]


def verify_protected_checksums() -> None:
    """Ensure all protected Phase 4-10 artifacts remain unmodified."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        if not fp.is_file():
            raise FileNotFoundError(f"Missing protected file: {rel_path}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for {rel_path}! Expected: {exp_hash}, Actual: {act_hash}")
    print("[CHECKSUMS] All 19 protected Phase 4-10 artifacts verified.")


def compute_newey_west_hac(returns: np.ndarray, max_lags: Optional[int] = None) -> Tuple[float, float, float]:
    """Compute Newey-West HAC standard error, t-statistic, and p-value for daily return series."""
    n = len(returns)
    if n < 2:
        return 0.0, 0.0, 1.0
    mean_val = float(np.mean(returns))
    e = returns - mean_val
    if np.all(returns == 0.0) or np.sum(np.abs(e)) < 1e-12:
        return 0.0, 0.0, 1.0

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
    return hac_se, t_stat, p_value


def compute_drawdowns(returns: np.ndarray) -> Tuple[float, np.ndarray]:
    """Compute maximum drawdown and drawdown series on cumulative compounded equity."""
    equity = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(np.min(dd)) if len(dd) > 0 else 0.0
    return max_dd, dd


def main() -> None:
    print("=" * 90)
    print("PHASE 12 STEP 3: SELECTIVE TRADING & TURNOVER-CONTROL RESEARCH")
    print("=" * 90)

    # 1. Verify protected inputs
    print("\n--- Step 1: Checksum Verification ---")
    verify_protected_checksums()

    # 2. Load Step 2 Diagnostics & Fold Results
    print("\n--- Step 2: Loading Step 2 Sealed Predictions ---")
    diag_df = pd.read_csv(STEP2_DIAG_PATH)
    fold_df = pd.read_csv(STEP2_FOLD_PATH)

    assert len(diag_df) == 1960, f"Expected 1,960 OOF sessions, found {len(diag_df)}"
    assert len(fold_df) == 8, f"Expected 8 folds, found {len(fold_df)}"

    # Check date boundaries (strictly <= 2021-12-31)
    t_dates = pd.to_datetime(diag_df["trading_date"]).dt.date
    assert t_dates.min() == date(2014, 1, 2)
    assert t_dates.max() == date(2021, 12, 31)
    assert (t_dates > date(2021, 12, 31)).sum() == 0, "Holdout contamination detected in trading dates!"
    print(f"Verified {len(diag_df)} development OOF sessions from {t_dates.min()} to {t_dates.max()}.")

    # Map fold_ids to diag_df
    fold_ids = []
    for f_id, n_s in zip(fold_df["fold_id"], fold_df["val_sessions"]):
        fold_ids.extend([int(f_id)] * int(n_s))
    diag_df["fold_id"] = fold_ids

    y_pred = diag_df["pred_reg_intraday"].values
    y_true = diag_df["y_true_intraday"].values
    abs_pred = np.abs(y_pred)
    n_total = len(y_pred)

    # 3. Reconcile tau = 0 with Step 2 Sealed Reference
    print("\n--- Step 3: Reconciling tau = 0 with Step 2 Reference ---")
    pos_tau0 = np.sign(y_pred)
    pos_tau0 = np.where(pos_tau0 == 0, 1.0, pos_tau0)
    daily_gross_tau0 = pos_tau0 * y_true
    ann_gross_tau0 = float(np.mean(daily_gross_tau0) * 252.0)
    vol_gross_tau0 = float(np.std(daily_gross_tau0, ddof=1) * math.sqrt(252.0))
    sharpe_gross_tau0 = ann_gross_tau0 / vol_gross_tau0

    daily_net10_tau0 = daily_gross_tau0 - 0.0010
    ann_net10_tau0 = float(np.mean(daily_net10_tau0) * 252.0)
    vol_net10_tau0 = float(np.std(daily_net10_tau0, ddof=1) * math.sqrt(252.0))
    sharpe_net10_tau0 = ann_net10_tau0 / vol_net10_tau0

    print(f"Step 3 tau=0 Gross:  Ann={ann_gross_tau0:+.4%} | Sharpe={sharpe_gross_tau0:+.2f}")
    print(f"Step 3 tau=0 10 bps: Ann={ann_net10_tau0:+.4%} | Sharpe={sharpe_net10_tau0:+.2f}")

    assert abs(ann_gross_tau0 - 0.182519) < 1e-4, f"Gross tau=0 divergence: {ann_gross_tau0}"
    assert abs(ann_net10_tau0 - (-0.069481)) < 1e-4, f"Net 10bps tau=0 divergence: {ann_net10_tau0}"
    assert abs(sharpe_gross_tau0 - 1.2855) < 1e-2, f"Gross Sharpe divergence: {sharpe_gross_tau0}"
    assert abs(sharpe_net10_tau0 - (-0.4893)) < 1e-2, f"Net Sharpe divergence: {sharpe_net10_tau0}"
    print("[PASS] Exact reconciliation with Step 2 reference confirmed.")

    # 4. Threshold Grid Evaluation across Cost Scenarios
    print("\n--- Step 4: Evaluating Pre-Registered Threshold Grid ---")
    threshold_results = []
    positions_by_tau: Dict[int, np.ndarray] = {}
    net_ret_10bps_by_tau: Dict[int, np.ndarray] = {}

    for t_bps in THRESHOLDS_BPS:
        t_val = t_bps / 10000.0

        if t_bps == 0:
            pos = np.sign(y_pred)
            pos = np.where(pos == 0, 1.0, pos)
        else:
            pos = np.where(abs_pred >= t_val, np.sign(y_pred), 0.0)

        positions_by_tau[t_bps] = pos

        active_mask = (pos != 0.0)
        active_cnt = int(np.sum(active_mask))
        inactive_cnt = n_total - active_cnt
        trades_per_year = float(active_cnt * (252.0 / n_total))
        exposure_pct = float(active_cnt / n_total * 100.0)
        long_cnt = int(np.sum(pos == 1.0))
        short_cnt = int(np.sum(pos == -1.0))
        long_pct = float(long_cnt / active_cnt * 100.0) if active_cnt > 0 else 0.0
        short_pct = float(short_cnt / active_cnt * 100.0) if active_cnt > 0 else 0.0

        # Predictive metrics on active subset
        if active_cnt > 0:
            y_true_active = y_true[active_mask]
            y_pred_active = y_pred[active_mask]
            pos_active = pos[active_mask]
            cond_mean_active = float(np.mean(y_true_active))
            cond_mean_long = float(np.mean(y_true[pos == 1.0])) if long_cnt > 0 else 0.0
            cond_mean_short = float(np.mean(y_true[pos == -1.0])) if short_cnt > 0 else 0.0
            active_dir_acc = float(np.mean(pos_active == np.where(y_true_active >= 0, 1.0, -1.0)))

            if active_cnt >= 10 and np.std(y_pred_active) > 0 and np.std(y_true_active) > 0:
                p_ic, p_pval = stats.pearsonr(y_pred_active, y_true_active)
                s_ic, s_pval = stats.spearmanr(y_pred_active, y_true_active)
            else:
                p_ic, p_pval, s_ic, s_pval = 0.0, 1.0, 0.0, 1.0
        else:
            cond_mean_active = 0.0
            cond_mean_long = 0.0
            cond_mean_short = 0.0
            active_dir_acc = 0.0
            p_ic, p_pval, s_ic, s_pval = 0.0, 1.0, 0.0, 1.0

        # Evaluate across cost scenarios
        for c_bps in COST_SCENARIOS_BPS:
            cost_frac = c_bps / 10000.0
            daily_net = pos * y_true - np.where(active_mask, cost_frac, 0.0)

            if c_bps == 10.0:
                net_ret_10bps_by_tau[t_bps] = daily_net

            cum_net = float(np.prod(1.0 + daily_net) - 1.0)
            ann_net = float(np.mean(daily_net) * 252.0)
            ann_vol = float(np.std(daily_net, ddof=1) * math.sqrt(252.0))
            sharpe = ann_net / ann_vol if ann_vol > 0 else 0.0
            max_dd, _ = compute_drawdowns(daily_net)

            if active_cnt > 0:
                active_trade_rets = daily_net[active_mask]
                mean_ret_per_trade = float(np.mean(active_trade_rets))
                median_ret_per_trade = float(np.median(active_trade_rets))
                win_rate = float(np.mean(active_trade_rets > 0.0))
                wins = active_trade_rets[active_trade_rets > 0.0]
                losses = active_trade_rets[active_trade_rets < 0.0]
                avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
                avg_loss = float(np.mean(losses)) if len(losses) > 0 else 0.0
                gross_win_sum = float(np.sum(wins)) if len(wins) > 0 else 0.0
                gross_loss_sum = float(np.sum(np.abs(losses))) if len(losses) > 0 else 0.0
                profit_factor = gross_win_sum / gross_loss_sum if gross_loss_sum > 0 else (999.0 if gross_win_sum > 0 else 0.0)
                payoff_ratio = abs(avg_win / avg_loss) if abs(avg_loss) > 0 else 0.0
            else:
                mean_ret_per_trade = 0.0
                median_ret_per_trade = 0.0
                win_rate = 0.0
                profit_factor = 0.0
                avg_win = 0.0
                avg_loss = 0.0
                payoff_ratio = 0.0

            _, hac_tstat, hac_pval = compute_newey_west_hac(daily_net)

            threshold_results.append({
                "threshold_bps": t_bps,
                "cost_scenario_bps": c_bps,
                "active_sessions": active_cnt,
                "inactive_sessions": inactive_cnt,
                "trades_per_year": trades_per_year,
                "exposure_pct": exposure_pct,
                "long_sessions": long_cnt,
                "short_sessions": short_cnt,
                "long_pct": long_pct,
                "short_pct": short_pct,
                "cumulative_net_return": cum_net,
                "annualized_net_return": ann_net,
                "annualized_volatility": ann_vol,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "mean_return_per_active_trade": mean_ret_per_trade,
                "median_return_per_active_trade": median_ret_per_trade,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "avg_winning_trade": avg_win,
                "avg_losing_trade": avg_loss,
                "payoff_ratio": payoff_ratio,
                "mean_daily_return": float(np.mean(daily_net)),
                "hac_tstat": hac_tstat,
                "hac_pvalue": hac_pval,
                "conditional_mean_active": cond_mean_active,
                "conditional_mean_long": cond_mean_long,
                "conditional_mean_short": cond_mean_short,
                "active_directional_accuracy": active_dir_acc,
                "active_pearson_ic": p_ic,
                "active_pearson_pvalue": p_pval,
                "active_spearman_ic": s_ic,
                "active_spearman_pvalue": s_pval,
            })

    threshold_df = pd.DataFrame(threshold_results)
    threshold_df.to_csv(OUT_THRESHOLD_CSV, index=False)
    print(f"  [SAVED] {OUT_THRESHOLD_CSV} ({len(threshold_df)} rows)")

    # Print summary table at 10 bps
    sub10 = threshold_df[threshold_df["cost_scenario_bps"] == 10.0]
    print("\nSummary at 10 bps institutional cost:")
    for _, r in sub10.iterrows():
        print(f"  tau={int(r['threshold_bps']):2d} bps: Active={int(r['active_sessions']):4d} ({r['exposure_pct']:5.1f}%) | Trades/Yr={r['trades_per_year']:5.1f} | Net Ann={r['annualized_net_return']:+6.2%} | Sharpe={r['sharpe_ratio']:+5.2f} | MaxDD={r['max_drawdown']:6.2%} | WinRate={r['win_rate']:5.1%}")

    # 5. Fold-by-Fold Analysis (8 Folds)
    print("\n--- Step 5: Fold-by-Fold Evaluation ---")
    fold_results = []
    for f_id in range(1, 9):
        f_row = fold_df[fold_df["fold_id"] == f_id].iloc[0]
        val_yr = int(f_row["val_year"])
        val_sess = int(f_row["val_sessions"])
        fold_mask = (diag_df["fold_id"] == f_id).values
        y_p_fold = y_pred[fold_mask]
        y_t_fold = y_true[fold_mask]

        for t_bps in THRESHOLDS_BPS:
            pos_f = positions_by_tau[t_bps][fold_mask]
            act_mask_f = (pos_f != 0.0)
            act_cnt_f = int(np.sum(act_mask_f))
            exp_pct_f = float(act_cnt_f / val_sess * 100.0)

            mean_act_ret = float(np.mean(y_t_fold[act_mask_f])) if act_cnt_f > 0 else 0.0
            hit_rate_f = float(np.mean(pos_f[act_mask_f] == np.where(y_t_fold[act_mask_f] >= 0, 1.0, -1.0))) if act_cnt_f > 0 else 0.0

            # Returns at 0 bps and 10 bps
            d_net0 = pos_f * y_t_fold
            d_net10 = pos_f * y_t_fold - np.where(act_mask_f, 0.0010, 0.0)

            ann0 = float(np.mean(d_net0) * 252.0)
            vol0 = float(np.std(d_net0, ddof=1) * math.sqrt(252.0))
            sr0 = ann0 / vol0 if vol0 > 0 else 0.0

            ann10 = float(np.mean(d_net10) * 252.0)
            vol10 = float(np.std(d_net10, ddof=1) * math.sqrt(252.0))
            sr10 = ann10 / vol10 if vol10 > 0 else 0.0
            mdd10, _ = compute_drawdowns(d_net10)

            fold_results.append({
                "fold_id": f_id,
                "val_year": val_yr,
                "val_sessions": val_sess,
                "threshold_bps": t_bps,
                "active_sessions": act_cnt_f,
                "exposure_pct": exp_pct_f,
                "mean_active_return": mean_act_ret,
                "ann_net_return_0bps": ann0,
                "sharpe_0bps": sr0,
                "ann_net_return_10bps": ann10,
                "sharpe_10bps": sr10,
                "max_drawdown_10bps": mdd10,
                "directional_accuracy": hit_rate_f,
            })

    fold_res_df = pd.DataFrame(fold_results)
    fold_res_df.to_csv(OUT_FOLD_CSV, index=False)
    print(f"  [SAVED] {OUT_FOLD_CSV} ({len(fold_res_df)} rows)")

    # 6. Temporal Stability Analysis (3 Periods)
    print("\n--- Step 6: Temporal Stability Analysis ---")
    periods = [
        ("2014-2016", [1, 2, 3]),
        ("2017-2019", [4, 5, 6]),
        ("2020-2021", [7, 8]),
    ]

    temporal_results = []
    for p_name, f_list in periods:
        p_mask = diag_df["fold_id"].isin(f_list).values
        n_p = int(np.sum(p_mask))
        y_p_p = y_pred[p_mask]
        y_t_p = y_true[p_mask]

        for t_bps in THRESHOLDS_BPS:
            pos_p = positions_by_tau[t_bps][p_mask]
            act_mask_p = (pos_p != 0.0)
            act_cnt_p = int(np.sum(act_mask_p))
            exp_pct_p = float(act_cnt_p / n_p * 100.0)

            hit_rate_p = float(np.mean(pos_p[act_mask_p] == np.where(y_t_p[act_mask_p] >= 0, 1.0, -1.0))) if act_cnt_p > 0 else 0.0

            d_net0 = pos_p * y_t_p
            d_net10 = pos_p * y_t_p - np.where(act_mask_p, 0.0010, 0.0)

            ann0 = float(np.mean(d_net0) * 252.0)
            vol0 = float(np.std(d_net0, ddof=1) * math.sqrt(252.0))
            sr0 = ann0 / vol0 if vol0 > 0 else 0.0

            ann10 = float(np.mean(d_net10) * 252.0)
            vol10 = float(np.std(d_net10, ddof=1) * math.sqrt(252.0))
            sr10 = ann10 / vol10 if vol10 > 0 else 0.0
            mdd10, _ = compute_drawdowns(d_net10)

            temporal_results.append({
                "period_name": p_name,
                "total_sessions": n_p,
                "threshold_bps": t_bps,
                "active_sessions": act_cnt_p,
                "exposure_pct": exp_pct_p,
                "ann_net_return_0bps": ann0,
                "sharpe_0bps": sr0,
                "ann_net_return_10bps": ann10,
                "sharpe_10bps": sr10,
                "max_drawdown_10bps": mdd10,
                "directional_accuracy": hit_rate_p,
            })

    temp_res_df = pd.DataFrame(temporal_results)
    temp_res_df.to_csv(OUT_TEMPORAL_CSV, index=False)
    print(f"  [SAVED] {OUT_TEMPORAL_CSV} ({len(temp_res_df)} rows)")

    # 7. Critical Baselines Evaluation
    print("\n--- Step 7: Critical Baselines Evaluation ---")
    baseline_results = []

    # Standard baselines
    standard_baselines = [
        ("Unrestricted Step 2 (tau=0)", pos_tau0),
        ("Always Short", np.full(n_total, -1.0)),
        ("Always Long", np.full(n_total, 1.0)),
        ("Zero-Position", np.zeros(n_total, dtype=np.float64)),
    ]

    for b_name, b_pos in standard_baselines:
        b_act = (b_pos != 0.0)
        act_cnt = int(np.sum(b_act))
        exp_pct = float(act_cnt / n_total * 100.0)

        for c_bps in COST_SCENARIOS_BPS:
            c_frac = c_bps / 10000.0
            d_net = b_pos * y_true - np.where(b_act, c_frac, 0.0)
            cum_net = float(np.prod(1.0 + d_net) - 1.0)
            ann_net = float(np.mean(d_net) * 252.0)
            ann_vol = float(np.std(d_net, ddof=1) * math.sqrt(252.0))
            sharpe = ann_net / ann_vol if ann_vol > 0 else 0.0
            max_dd, _ = compute_drawdowns(d_net)
            win_rate = float(np.mean(d_net[b_act] > 0.0)) if act_cnt > 0 else 0.0
            wins = d_net[b_act & (d_net > 0.0)]
            losses = d_net[b_act & (d_net < 0.0)]
            gross_w = float(np.sum(wins)) if len(wins) > 0 else 0.0
            gross_l = float(np.sum(np.abs(losses))) if len(losses) > 0 else 0.0
            profit_factor = gross_w / gross_l if gross_l > 0 else (999.0 if gross_w > 0 else 0.0)
            _, hac_t, hac_p = compute_newey_west_hac(d_net)

            baseline_results.append({
                "baseline_name": b_name,
                "threshold_bps": 0,
                "cost_scenario_bps": c_bps,
                "active_sessions": act_cnt,
                "exposure_pct": exp_pct,
                "cumulative_net_return": cum_net,
                "annualized_net_return": ann_net,
                "annualized_volatility": ann_vol,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "hac_tstat": hac_t,
                "hac_pvalue": hac_p,
            })

    # Matched-activity random baselines (deterministic seed=42)
    rng = np.random.RandomState(42)
    for t_bps in THRESHOLDS_BPS:
        act_cnt_target = int(np.sum(positions_by_tau[t_bps] != 0.0))
        if act_cnt_target == 0:
            rand_pos = np.zeros(n_total, dtype=np.float64)
        elif act_cnt_target == n_total:
            rand_pos = rng.choice([-1.0, 1.0], size=n_total)
        else:
            rand_pos = np.zeros(n_total, dtype=np.float64)
            chosen_indices = rng.choice(n_total, size=act_cnt_target, replace=False)
            rand_pos[chosen_indices] = rng.choice([-1.0, 1.0], size=act_cnt_target)

        rand_act = (rand_pos != 0.0)
        exp_pct = float(act_cnt_target / n_total * 100.0)

        for c_bps in COST_SCENARIOS_BPS:
            c_frac = c_bps / 10000.0
            d_net = rand_pos * y_true - np.where(rand_act, c_frac, 0.0)
            cum_net = float(np.prod(1.0 + d_net) - 1.0)
            ann_net = float(np.mean(d_net) * 252.0)
            ann_vol = float(np.std(d_net, ddof=1) * math.sqrt(252.0))
            sharpe = ann_net / ann_vol if ann_vol > 0 else 0.0
            max_dd, _ = compute_drawdowns(d_net)
            win_rate = float(np.mean(d_net[rand_act] > 0.0)) if act_cnt_target > 0 else 0.0
            wins = d_net[rand_act & (d_net > 0.0)]
            losses = d_net[rand_act & (d_net < 0.0)]
            gross_w = float(np.sum(wins)) if len(wins) > 0 else 0.0
            gross_l = float(np.sum(np.abs(losses))) if len(losses) > 0 else 0.0
            profit_factor = gross_w / gross_l if gross_l > 0 else (999.0 if gross_w > 0 else 0.0)
            _, hac_t, hac_p = compute_newey_west_hac(d_net)

            baseline_results.append({
                "baseline_name": f"Matched-Activity Random (tau={t_bps}bps)",
                "threshold_bps": t_bps,
                "cost_scenario_bps": c_bps,
                "active_sessions": act_cnt_target,
                "exposure_pct": exp_pct,
                "cumulative_net_return": cum_net,
                "annualized_net_return": ann_net,
                "annualized_volatility": ann_vol,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
                "win_rate": win_rate,
                "profit_factor": profit_factor,
                "hac_tstat": hac_t,
                "hac_pvalue": hac_p,
            })

    baseline_df = pd.DataFrame(baseline_results)
    baseline_df.to_csv(OUT_BASELINE_CSV, index=False)
    print(f"  [SAVED] {OUT_BASELINE_CSV} ({len(baseline_df)} rows)")

    # 8. Diagnostics Artifact (Session-Level Positions & Returns)
    print("\n--- Step 8: Generating Diagnostics Artifact ---")
    diag_out = pd.DataFrame({
        "trading_date": diag_df["trading_date"],
        "execution_date": diag_df["execution_date"],
        "fold_id": diag_df["fold_id"],
        "y_true_intraday": diag_df["y_true_intraday"],
        "pred_reg_intraday": diag_df["pred_reg_intraday"],
    })

    for t_bps in THRESHOLDS_BPS:
        diag_out[f"pos_tau_{t_bps}bps"] = positions_by_tau[t_bps]
        diag_out[f"net_ret_10bps_tau_{t_bps}bps"] = net_ret_10bps_by_tau[t_bps]

    diag_out.to_csv(OUT_DIAGNOSTICS_CSV, index=False)
    print(f"  [SAVED] {OUT_DIAGNOSTICS_CSV} ({len(diag_out)} rows)")

    print("\n=======================================================")
    print("  PHASE 12 STEP 3 EXPERIMENT COMPLETE")
    print("=======================================================")


if __name__ == "__main__":
    main()
