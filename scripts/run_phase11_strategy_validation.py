"""Phase 11 Stage 1: Out-of-Sample Strategy Validation & Paper-Trading Readiness Runner.

Evaluates pre-registered trading strategies on Development Out-of-Fold (OOF) data
(2014-01-02 to 2021-12-31, N=1,960) under realistic execution conventions and
transaction cost scenarios (0, 5, 10, 20 bps).

Strict Rules:
- ZERO access to Terminal Holdout (2022-2026).
- Model 1 predictions loaded from frozen Phase 10 diagnostics.
- Primary execution convention: Next session OPEN -> same session CLOSE.
- Secondary diagnostic convention: Interday Close -> Close.
- Pre-registered thresholds and strategies only.
- Time-series robust statistical inference (Newey-West HAC, stationary bootstrap).
"""

from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from nifty_ai.config import PROJECT_ROOT

# Output paths
OUT_DIR = PROJECT_ROOT / "data" / "interim" / "strategy"
OUT_STRATEGY_RESULTS_CSV = OUT_DIR / "phase11_strategy_results.csv"
OUT_TRADE_LOG_CSV = OUT_DIR / "phase11_trade_log.csv"
OUT_EQUITY_CURVES_CSV = OUT_DIR / "phase11_equity_curves.csv"
OUT_DRAWDOWNS_CSV = OUT_DIR / "phase11_drawdowns.csv"
OUT_ROBUSTNESS_CSV = OUT_DIR / "phase11_robustness.csv"
OUT_REGIME_RESULTS_CSV = OUT_DIR / "phase11_regime_results.csv"
OUT_TEMPORAL_RESULTS_CSV = OUT_DIR / "phase11_temporal_results.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"


def verify_protected_checksums(cfg: Dict[str, Any]) -> None:
    """Ensure all protected artifacts remain unmodified before running."""
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        if not fp.is_file():
            raise FileNotFoundError(f"Missing protected file: {rel_path}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for {rel_path}!\nExpected: {exp_hash}\nActual:   {act_hash}")
    print("[CHECKSUMS] All 19 protected Phase 4-10 artifacts verified.")


def compute_newey_west_tstat(returns: np.ndarray, max_lags: Optional[int] = None) -> Tuple[float, float, float]:
    """Compute Newey-West HAC standard error, t-stat, and p-value for the mean daily return."""
    n = len(returns)
    if n < 2:
        return 0.0, 0.0, 1.0
    mean_val = float(np.mean(returns))
    e = returns - mean_val
    if max_lags is None:
        max_lags = int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0))))
        max_lags = max(1, min(max_lags, 20))

    gamma_0 = float(np.dot(e, e) / n)
    hac_var = gamma_0
    for lag in range(1, max_lags + 1):
        weight = 1.0 - (lag / (max_lags + 1.0))
        gamma_l = float(np.dot(e[lag:], e[:-lag]) / n)
        hac_var += 2.0 * weight * gamma_l

    hac_var = max(hac_var, 1e-16)
    hac_se = math.sqrt(hac_var / n)
    t_stat = mean_val / hac_se if hac_se > 0 else 0.0
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))
    return hac_se, t_stat, p_val


def stationary_bootstrap_ci(
    returns: np.ndarray,
    n_bootstrap: int = 1000,
    p_geom: float = 0.1,  # Mean block length = 10
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """Compute 95% stationary block bootstrap confidence intervals for annualized return and Sharpe."""
    n = len(returns)
    if n < 10:
        return (0.0, 0.0), (0.0, 0.0)

    rng = np.random.RandomState(seed)
    boot_ann_rets = np.empty(n_bootstrap)
    boot_sharpes = np.empty(n_bootstrap)

    for b in range(n_bootstrap):
        # Generate stationary block bootstrap indices
        idx = np.empty(n, dtype=int)
        cur = rng.randint(0, n)
        for i in range(n):
            if i > 0 and rng.rand() < p_geom:
                cur = rng.randint(0, n)
            else:
                cur = (cur + 1) % n if i > 0 else cur
            idx[i] = cur

        b_rets = returns[idx]
        cum_ret = float(np.prod(1.0 + b_rets) - 1.0)
        ann_ret = (1.0 + cum_ret) ** (252.0 / n) - 1.0 if (1.0 + cum_ret) > 0 else -1.0
        sd = float(np.std(b_rets, ddof=1))
        m = float(np.mean(b_rets))
        sh = (m / sd) * math.sqrt(252.0) if sd > 1e-9 else 0.0

        boot_ann_rets[b] = ann_ret
        boot_sharpes[b] = sh

    ann_ci = (
        float(np.percentile(boot_ann_rets, 100 * (alpha / 2.0))),
        float(np.percentile(boot_ann_rets, 100 * (1.0 - alpha / 2.0))),
    )
    sharpe_ci = (
        float(np.percentile(boot_sharpes, 100 * (alpha / 2.0))),
        float(np.percentile(boot_sharpes, 100 * (1.0 - alpha / 2.0))),
    )
    return ann_ci, sharpe_ci


def compute_drawdown_series(equity_curve: np.ndarray) -> np.ndarray:
    """Calculate the drawdown series from an equity curve."""
    peaks = np.maximum.accumulate(equity_curve)
    dd = (equity_curve - peaks) / peaks
    return dd


def extract_top_5_drawdowns(dates: List[str], equity_curve: np.ndarray) -> List[Dict[str, Any]]:
    """Extract the top 5 worst peak-to-trough drawdown episodes."""
    n = len(equity_curve)
    dd = compute_drawdown_series(equity_curve)
    peaks = np.maximum.accumulate(equity_curve)

    episodes = []
    in_dd = False
    start_idx = 0
    trough_idx = 0
    max_dd_val = 0.0

    for i in range(n):
        if dd[i] < -1e-6:
            if not in_dd:
                in_dd = True
                start_idx = i - 1 if i > 0 else 0
                trough_idx = i
                max_dd_val = dd[i]
            else:
                if dd[i] < max_dd_val:
                    max_dd_val = dd[i]
                    trough_idx = i
        else:
            if in_dd:
                in_dd = False
                end_idx = i
                episodes.append({
                    "peak_date": dates[start_idx],
                    "trough_date": dates[trough_idx],
                    "recovery_date": dates[end_idx],
                    "max_drawdown": float(max_dd_val),
                    "duration_sessions": end_idx - start_idx,
                })

    if in_dd:
        episodes.append({
            "peak_date": dates[start_idx],
            "trough_date": dates[trough_idx],
            "recovery_date": "UNRECOVERED",
            "max_drawdown": float(max_dd_val),
            "duration_sessions": n - start_idx,
        })

    episodes.sort(key=lambda x: x["max_drawdown"])
    return episodes[:5]


def evaluate_strategy_performance(
    dates: List[str],
    positions: np.ndarray,
    bar_returns: np.ndarray,
    cost_fraction: float,
    strategy_id: str,
    strategy_name: str,
    snapshot_label: str,
    execution_convention: str,
    cost_bps: float,
    pred_returns: np.ndarray,
) -> Dict[str, Any]:
    """Compute the complete suite of performance, risk, trading, and statistical metrics."""
    n = len(dates)
    active_mask = positions != 0
    n_active = int(np.sum(active_mask))
    active_pct = float(n_active / n) if n > 0 else 0.0

    # Number of trades: entries where position changes to/from active or sign flips
    pos_diff = np.diff(np.concatenate(([0], positions)))
    n_trades = int(np.sum(pos_diff != 0))

    # Daily gross returns
    daily_gross_ret = positions * bar_returns

    # Transaction cost application:
    # Under Primary Open-to-Close convention: round-trip cost on every active session
    if execution_convention == "Open-to-Close (Primary)":
        daily_cost = np.where(active_mask, cost_fraction, 0.0)
    else:
        # Interday Close-to-Close: cost paid on position changes
        daily_cost = np.abs(pos_diff) * (cost_fraction / 2.0)

    # Net daily returns
    daily_net_ret = daily_gross_ret - daily_cost

    # Equity curves (initial equity = 1.0)
    equity_gross = np.cumprod(1.0 + daily_gross_ret)
    equity_net = np.cumprod(1.0 + daily_net_ret)

    cum_gross_ret = float(equity_gross[-1] - 1.0)
    cum_net_ret = float(equity_net[-1] - 1.0)
    cost_degradation = float(cum_net_ret - cum_gross_ret)

    ann_gross_ret = float((1.0 + cum_gross_ret) ** (252.0 / n) - 1.0) if (1.0 + cum_gross_ret) > 0 else -1.0
    ann_net_ret = float((1.0 + cum_net_ret) ** (252.0 / n) - 1.0) if (1.0 + cum_net_ret) > 0 else -1.0

    mean_daily_net = float(np.mean(daily_net_ret))
    std_daily_net = float(np.std(daily_net_ret, ddof=1)) if n > 1 else 0.0
    ann_vol_net = std_daily_net * math.sqrt(252.0)

    # Sharpe Ratio
    sharpe_net = (mean_daily_net / std_daily_net) * math.sqrt(252.0) if std_daily_net > 1e-9 else 0.0

    # Sortino Ratio
    downside_rets = np.minimum(0.0, daily_net_ret)
    downside_dev = math.sqrt(float(np.mean(downside_rets ** 2)))
    sortino_net = (mean_daily_net / downside_dev) * math.sqrt(252.0) if downside_dev > 1e-9 else 0.0

    # Maximum Drawdown & Calmar
    dd_net = compute_drawdown_series(equity_net)
    max_dd_net = float(np.min(dd_net))
    calmar_net = (ann_net_ret / abs(max_dd_net)) if abs(max_dd_net) > 1e-6 else 0.0

    # Trade stats on active sessions
    active_net_rets = daily_net_ret[active_mask]
    if len(active_net_rets) > 0:
        win_mask = active_net_rets > 0
        win_rate = float(np.mean(win_mask))
        winners = active_net_rets[win_mask]
        losers = active_net_rets[active_net_rets < 0]
        avg_winner = float(np.mean(winners)) if len(winners) > 0 else 0.0
        avg_loser = float(np.mean(losers)) if len(losers) > 0 else 0.0
        sum_win = float(np.sum(winners)) if len(winners) > 0 else 0.0
        sum_loss = float(np.sum(np.abs(losers))) if len(losers) > 0 else 0.0
        profit_factor = (sum_win / sum_loss) if sum_loss > 1e-9 else (999.0 if sum_win > 0 else 0.0)
    else:
        win_rate = 0.0
        avg_winner = 0.0
        avg_loser = 0.0
        profit_factor = 0.0

    # Average holding period
    # Segment consecutive active blocks
    holding_lengths = []
    curr_len = 0
    for pos in positions:
        if pos != 0:
            curr_len += 1
        else:
            if curr_len > 0:
                holding_lengths.append(curr_len)
                curr_len = 0
    if curr_len > 0:
        holding_lengths.append(curr_len)
    avg_holding_period = float(np.mean(holding_lengths)) if len(holding_lengths) > 0 else 0.0

    # Prediction / Realized Correlation & Directional Agreement
    if len(pred_returns) == n and n_active >= 2 and np.std(pred_returns[active_mask]) > 1e-12 and np.std(bar_returns[active_mask]) > 1e-12:
        ic, _ = stats.pearsonr(pred_returns[active_mask], bar_returns[active_mask])
        ic = float(ic) if np.isfinite(ic) else 0.0
    else:
        ic = 0.0

    if n_active > 0:
        dir_agree = float(np.mean(np.sign(positions[active_mask]) == np.sign(bar_returns[active_mask])))
    else:
        dir_agree = 0.0

    # Newey-West HAC
    hac_se, hac_tstat, hac_pval = compute_newey_west_tstat(daily_net_ret)

    # Stationary Bootstrap CIs
    (ann_ret_ci_low, ann_ret_ci_high), (sharpe_ci_low, sharpe_ci_high) = stationary_bootstrap_ci(daily_net_ret)

    return {
        "snapshot": snapshot_label,
        "execution_convention": execution_convention,
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "cost_scenario_bps": cost_bps,
        "n_sessions": n,
        "active_sessions": n_active,
        "active_session_pct": active_pct,
        "trade_count": n_trades,
        "avg_holding_period_sessions": avg_holding_period,
        "cumulative_gross_return": cum_gross_ret,
        "cumulative_net_return": cum_net_ret,
        "annualized_gross_return": ann_gross_ret,
        "annualized_net_return": ann_net_ret,
        "cost_degradation": cost_degradation,
        "mean_daily_net_return": mean_daily_net,
        "annualized_volatility_net": ann_vol_net,
        "sharpe_ratio_net": sharpe_net,
        "sortino_ratio_net": sortino_net,
        "max_drawdown_net": max_dd_net,
        "calmar_ratio_net": calmar_net,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_winning_return": avg_winner,
        "avg_losing_return": avg_loser,
        "prediction_realized_ic": ic,
        "directional_agreement": dir_agree,
        "newey_west_hac_se": hac_se,
        "newey_west_tstat": hac_tstat,
        "newey_west_pvalue": hac_pval,
        "ann_net_return_ci_95_low": ann_ret_ci_low,
        "ann_net_return_ci_95_high": ann_ret_ci_high,
        "sharpe_ci_95_low": sharpe_ci_low,
        "sharpe_ci_95_high": sharpe_ci_high,
        "daily_net_returns": daily_net_ret,
        "daily_gross_returns": daily_gross_ret,
        "equity_curve_net": equity_net,
        "drawdown_series_net": dd_net,
    }


def main() -> None:
    print("=" * 90)
    print("PHASE 11 — STAGE 1: OOF STRATEGY VALIDATION & PAPER-TRADING READINESS")
    print("=" * 90)

    # 1. Load configuration and verify checksums
    print("\n--- Step 1: Config & Protected Artifact Verification ---")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    verify_protected_checksums(cfg)

    # 2. Load Price Data and OOF Diagnostics
    print("\n--- Step 2: Loading Price and OOF Data ---")
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv")
    price_map = price_df.set_index("trading_date")[["open", "close"]].to_dict(orient="index")

    target_a_df = pd.read_csv(PROJECT_ROOT / "data" / "targets" / "nifty50_targets_snapshot_a.csv")
    date_to_target_date = target_a_df.set_index("trading_date")["target_date"].to_dict()

    oof_df = pd.read_csv(PROJECT_ROOT / "data" / "interim" / "regime" / "phase10_oof_diagnostics.csv")
    oof_dates = sorted(oof_df["trading_date"].unique())
    print(f"OOF unique sessions: {len(oof_dates)} ({oof_dates[0]} to {oof_dates[-1]})")
    assert len(oof_dates) == 1960, f"Expected exactly 1,960 OOF dates, found {len(oof_dates)}"

    # 3. Construct Aligned Bar Returns for OOF
    # For every Session T in OOF:
    # Execution occurs on Session T+1 (target_date)
    # Open_{T+1} and Close_{T+1}, Close_T
    bar_data = []
    for d in oof_dates:
        t_plus_1 = date_to_target_date[d]
        p_t = price_map[d]
        p_t1 = price_map[t_plus_1]

        open_t1 = p_t1["open"]
        close_t1 = p_t1["close"]
        close_t = p_t["close"]

        # Open-to-Close bar return
        ret_open_to_close = (close_t1 - open_t1) / open_t1
        # Close-to-Close bar return
        ret_close_to_close = (close_t1 - close_t) / close_t

        bar_data.append({
            "prediction_date": d,
            "execution_date": t_plus_1,
            "close_t": close_t,
            "open_t1": open_t1,
            "close_t1": close_t1,
            "ret_open_to_close": ret_open_to_close,
            "ret_close_to_close": ret_close_to_close,
        })
    bar_df = pd.DataFrame(bar_data)
    ret_otc = bar_df["ret_open_to_close"].values
    ret_ctc = bar_df["ret_close_to_close"].values

    # 4. Strategy Definitions Generator
    def generate_positions(snap_df: pd.DataFrame) -> Dict[str, Tuple[str, np.ndarray]]:
        """Generate position series for all pre-registered strategy families."""
        strats: Dict[str, Tuple[str, np.ndarray]] = {}

        pred_reg = snap_df["pred_reg"].values
        pred_cls = snap_df["pred_class"].values
        conf = snap_df["confidence"].values
        regime_vol = snap_df["regime_volatility"].values

        # Strategy 0: Always Flat
        strats["Strategy 0"] = ("No-Signal Baseline (Always Flat)", np.zeros(len(snap_df), dtype=int))

        # Strategy 1: Regression Direction
        pos_s1 = np.zeros(len(snap_df), dtype=int)
        pos_s1[pred_reg > 0] = 1
        pos_s1[pred_reg < 0] = -1
        strats["Strategy 1"] = ("Regression Direction", pos_s1)

        # Strategy 2: Classifier Direction (UP: 2 -> +1, DOWN: 0 -> -1, SIDEWAYS: 1 -> 0)
        pos_s2 = np.zeros(len(snap_df), dtype=int)
        pos_s2[pred_cls == 2] = 1
        pos_s2[pred_cls == 0] = -1
        strats["Strategy 2"] = ("Classifier Direction", pos_s2)

        # Strategy 3: Classifier + Confidence Gate (0.40, 0.45, 0.50)
        for tau in [0.40, 0.45, 0.50]:
            pos_s3 = np.copy(pos_s2)
            pos_s3[conf < tau] = 0
            strats[f"Strategy 3 (tau={tau:.2f})"] = (f"Classifier + Conf Gate ({tau:.2f})", pos_s3)

        # Strategy 4: Regression Magnitude Gate (0.10%, 0.25%, 0.50%)
        for theta, label in [(0.0010, "0.10%"), (0.0025, "0.25%"), (0.0050, "0.50%")]:
            pos_s4 = np.copy(pos_s1)
            pos_s4[np.abs(pred_reg) < theta] = 0
            strats[f"Strategy 4 (mag={label})"] = (f"Regression Magnitude Gate ({label})", pos_s4)

        # Strategy 5: Phase 10 LOW-volatility diagnostic filter
        # LOW Volatility: volatility_ann_20d <= 0.114675
        is_low_vol = regime_vol == "LOW"

        pos_s5a = np.copy(pos_s1)
        pos_s5a[~is_low_vol] = 0
        strats["Strategy 5A (Reg + LowVol)"] = ("LOW-Vol Filtered Regression", pos_s5a)

        pos_s5b = np.copy(pos_s2)
        pos_s5b[~is_low_vol] = 0
        strats["Strategy 5B (Clf + LowVol)"] = ("LOW-Vol Filtered Classifier", pos_s5b)

        # Benchmarks
        strats["Benchmark 1"] = ("NIFTY 50 Buy-and-Hold", np.ones(len(snap_df), dtype=int))
        strats["Benchmark 2"] = ("Always-Long Open-to-Close", np.ones(len(snap_df), dtype=int))

        return strats

    # 5. Run Evaluations across Snapshots, Strategies, Costs, and Conventions
    print("\n--- Step 3: Evaluating Pre-Registered Strategy Families on OOF ---")
    results_rows = []
    trade_log_rows = []
    equity_curve_data = {"date": oof_dates}
    drawdown_rows = []
    robustness_rows = []

    cost_scenarios = [
        ("0 bps (Gross)", 0.0, 0.0),
        ("5 bps Round-Trip", 5.0, 0.0005),
        ("10 bps Round-Trip", 10.0, 0.0010),
        ("20 bps Round-Trip", 20.0, 0.0020),
    ]

    for snap_key in ["Snapshot A", "Snapshot B"]:
        snap_oof = oof_df[oof_df["snapshot"] == snap_key].sort_values("trading_date").reset_index(drop=True)
        assert len(snap_oof) == 1960
        strat_dict = generate_positions(snap_oof)

        for s_id, (s_name, positions) in strat_dict.items():
            # Evaluate under Primary Execution Convention (Open-to-Close)
            for cost_label, cost_bps, cost_frac in cost_scenarios:
                perf = evaluate_strategy_performance(
                    dates=oof_dates,
                    positions=positions,
                    bar_returns=ret_otc,
                    cost_fraction=cost_frac,
                    strategy_id=s_id,
                    strategy_name=s_name,
                    snapshot_label=snap_key,
                    execution_convention="Open-to-Close (Primary)",
                    cost_bps=cost_bps,
                    pred_returns=snap_oof["pred_reg"].values,
                )

                # Store result metrics
                row_copy = {k: v for k, v in perf.items() if not k.startswith("daily_") and not k.startswith("equity_") and not k.startswith("drawdown_")}
                results_rows.append(row_copy)

                # Record equity curve column
                eq_col = f"{snap_key}__{s_id}__{cost_bps}bps"
                equity_curve_data[eq_col] = perf["equity_curve_net"]

                # Extract top 5 drawdowns
                top_dds = extract_top_5_drawdowns(oof_dates, perf["equity_curve_net"])
                for rank, dd_info in enumerate(top_dds, 1):
                    drawdown_rows.append({
                        "snapshot": snap_key,
                        "execution_convention": "Open-to-Close (Primary)",
                        "strategy_id": s_id,
                        "strategy_name": s_name,
                        "cost_scenario_bps": cost_bps,
                        "drawdown_rank": rank,
                        **dd_info,
                    })

                # Detailed Trade Log for 10 bps realistic cost
                if cost_bps == 10.0 and s_id in ["Strategy 1", "Strategy 2", "Strategy 3 (tau=0.45)", "Strategy 4 (mag=0.25%)", "Strategy 5A (Reg + LowVol)"]:
                    for i in range(len(oof_dates)):
                        trade_log_rows.append({
                            "snapshot": snap_key,
                            "prediction_date": bar_df["prediction_date"].iloc[i],
                            "execution_date": bar_df["execution_date"].iloc[i],
                            "strategy_id": s_id,
                            "cost_scenario_bps": cost_bps,
                            "position": positions[i],
                            "predicted_return": snap_oof["pred_reg"].iloc[i],
                            "predicted_class": snap_oof["pred_class"].iloc[i],
                            "confidence": snap_oof["confidence"].iloc[i],
                            "regime_volatility": snap_oof["regime_volatility"].iloc[i],
                            "regime_trend": snap_oof["regime_trend"].iloc[i],
                            "regime_stress": snap_oof["regime_stress"].iloc[i],
                            "entry_price": bar_df["open_t1"].iloc[i],
                            "exit_price": bar_df["close_t1"].iloc[i],
                            "gross_return": perf["daily_gross_returns"][i],
                            "transaction_cost": cost_frac if positions[i] != 0 else 0.0,
                            "net_return": perf["daily_net_returns"][i],
                            "cumulative_equity": perf["equity_curve_net"][i],
                            "drawdown": perf["drawdown_series_net"][i],
                        })

            # Also evaluate Secondary Diagnostic (Close-to-Close) for 10 bps
            perf_ctc = evaluate_strategy_performance(
                dates=oof_dates,
                positions=positions,
                bar_returns=ret_ctc,
                cost_fraction=0.0010,
                strategy_id=s_id,
                strategy_name=s_name,
                snapshot_label=snap_key,
                execution_convention="Close-to-Close (Secondary Diagnostic)",
                cost_bps=10.0,
                pred_returns=snap_oof["pred_reg"].values,
            )
            row_ctc = {k: v for k, v in perf_ctc.items() if not k.startswith("daily_") and not k.startswith("equity_") and not k.startswith("drawdown_")}
            results_rows.append(row_ctc)

    results_df = pd.DataFrame(results_rows)
    print(f"Total strategy evaluation scenarios generated: {len(results_df)}")

    # 6. Robustness Grid Across Thresholds
    print("\n--- Step 4: Generating Parameter Robustness Table ---")
    # Confidence thresholds (Strategy 3) & Magnitude thresholds (Strategy 4)
    rob_strats = [
        ("Strategy 3 (tau=0.40)", "Confidence Gate", 0.40),
        ("Strategy 3 (tau=0.45)", "Confidence Gate", 0.45),
        ("Strategy 3 (tau=0.50)", "Confidence Gate", 0.50),
        ("Strategy 4 (mag=0.10%)", "Magnitude Gate", 0.0010),
        ("Strategy 4 (mag=0.25%)", "Magnitude Gate", 0.0025),
        ("Strategy 4 (mag=0.50%)", "Magnitude Gate", 0.0050),
    ]
    for snap_key in ["Snapshot A", "Snapshot B"]:
        for s_id, p_family, p_val in rob_strats:
            for _, cost_bps, _ in cost_scenarios:
                sub = results_df[
                    (results_df["snapshot"] == snap_key) &
                    (results_df["execution_convention"] == "Open-to-Close (Primary)") &
                    (results_df["strategy_id"] == s_id) &
                    (results_df["cost_scenario_bps"] == cost_bps)
                ]
                if len(sub) == 1:
                    r = sub.iloc[0]
                    robustness_rows.append({
                        "snapshot": snap_key,
                        "parameter_family": p_family,
                        "threshold_value": p_val,
                        "strategy_id": s_id,
                        "cost_scenario_bps": cost_bps,
                        "active_session_pct": r["active_session_pct"],
                        "annualized_net_return": r["annualized_net_return"],
                        "sharpe_ratio_net": r["sharpe_ratio_net"],
                        "max_drawdown_net": r["max_drawdown_net"],
                        "profit_factor": r["profit_factor"],
                        "calmar_ratio_net": r["calmar_ratio_net"],
                        "hac_pvalue": r["newey_west_pvalue"],
                    })
    robustness_df = pd.DataFrame(robustness_rows)

    # 7. Temporal Blocks Analysis (2014-2016, 2017-2019, 2020-2021)
    print("\n--- Step 5: Generating Temporal Stability Table ---")
    temporal_rows = []
    blocks = [
        ("2014-2016", "2014-01-02", "2016-12-31"),
        ("2017-2019", "2017-01-02", "2019-12-31"),
        ("2020-2021", "2020-01-01", "2021-12-31"),
    ]
    oof_dates_arr = np.array(oof_dates)

    for snap_key in ["Snapshot A", "Snapshot B"]:
        snap_oof = oof_df[oof_df["snapshot"] == snap_key].sort_values("trading_date").reset_index(drop=True)
        strat_dict = generate_positions(snap_oof)

        for b_name, b_start, b_end in blocks:
            b_mask = (oof_dates_arr >= b_start) & (oof_dates_arr <= b_end)
            b_dates = [oof_dates[i] for i in range(len(oof_dates)) if b_mask[i]]
            b_ret_otc = ret_otc[b_mask]

            for s_id, (s_name, positions) in strat_dict.items():
                b_pos = positions[b_mask]
                # Evaluate at 10 bps
                perf_b = evaluate_strategy_performance(
                    dates=b_dates,
                    positions=b_pos,
                    bar_returns=b_ret_otc,
                    cost_fraction=0.0010,
                    strategy_id=s_id,
                    strategy_name=s_name,
                    snapshot_label=snap_key,
                    execution_convention="Open-to-Close (Primary)",
                    cost_bps=10.0,
                    pred_returns=snap_oof["pred_reg"].values[b_mask],
                )
                temporal_rows.append({
                    "snapshot": snap_key,
                    "temporal_block": b_name,
                    "start_date": b_start,
                    "end_date": b_end,
                    "strategy_id": s_id,
                    "strategy_name": s_name,
                    "cost_scenario_bps": 10.0,
                    "n_sessions": len(b_dates),
                    "active_session_pct": perf_b["active_session_pct"],
                    "annualized_net_return": perf_b["annualized_net_return"],
                    "sharpe_ratio_net": perf_b["sharpe_ratio_net"],
                    "max_drawdown_net": perf_b["max_drawdown_net"],
                    "profit_factor": perf_b["profit_factor"],
                    "win_rate": perf_b["win_rate"],
                })
    temporal_df = pd.DataFrame(temporal_rows)

    # 8. Regime-Conditioned Performance Table
    print("\n--- Step 6: Generating Regime-Conditioned Performance Table ---")
    regime_rows = []
    regime_dims = [
        ("Volatility", "regime_volatility", ["LOW", "NORMAL", "HIGH", "EXTREME"]),
        ("Trend", "regime_trend", ["BEARISH", "NEUTRAL", "BULLISH"]),
        ("Stress", "regime_stress", ["CALM", "STRESSED"]),
    ]

    for snap_key in ["Snapshot A", "Snapshot B"]:
        snap_oof = oof_df[oof_df["snapshot"] == snap_key].sort_values("trading_date").reset_index(drop=True)
        strat_dict = generate_positions(snap_oof)

        for s_id in ["Strategy 1", "Strategy 2", "Strategy 3 (tau=0.45)", "Benchmark 2"]:
            s_name, positions = strat_dict[s_id]

            for r_dim, r_col, categories in regime_dims:
                for cat in categories:
                    c_mask = snap_oof[r_col].values == cat
                    n_c = int(np.sum(c_mask))
                    if n_c == 0:
                        continue

                    # Governance status
                    if n_c < 50:
                        gov_tag = "DESCRIPTIVE_ONLY"
                    elif n_c < 100:
                        gov_tag = "QUANTITATIVE_COMPARISON"
                    else:
                        gov_tag = "STRONG_STATISTICAL"

                    c_dates = [oof_dates[i] for i in range(len(oof_dates)) if c_mask[i]]
                    c_pos = positions[c_mask]
                    c_ret_otc = ret_otc[c_mask]

                    perf_c = evaluate_strategy_performance(
                        dates=c_dates,
                        positions=c_pos,
                        bar_returns=c_ret_otc,
                        cost_fraction=0.0010,
                        strategy_id=s_id,
                        strategy_name=s_name,
                        snapshot_label=snap_key,
                        execution_convention="Open-to-Close (Primary)",
                        cost_bps=10.0,
                        pred_returns=snap_oof["pred_reg"].values[c_mask],
                    )

                    regime_rows.append({
                        "snapshot": snap_key,
                        "strategy_id": s_id,
                        "regime_dimension": r_dim,
                        "regime_category": cat,
                        "governance_status": gov_tag,
                        "n_sessions": n_c,
                        "active_session_pct": perf_c["active_session_pct"],
                        "annualized_net_return": perf_c["annualized_net_return"],
                        "sharpe_ratio_net": perf_c["sharpe_ratio_net"],
                        "max_drawdown_net": perf_c["max_drawdown_net"],
                        "profit_factor": perf_c["profit_factor"],
                        "win_rate": perf_c["win_rate"],
                    })
    regime_df = pd.DataFrame(regime_rows)

    # 9. Save All Structured Artifacts
    print("\n--- Step 7: Saving Strategy Artifacts ---")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results_df.to_csv(OUT_STRATEGY_RESULTS_CSV, index=False)
    trade_log_df = pd.DataFrame(trade_log_rows)
    trade_log_df.to_csv(OUT_TRADE_LOG_CSV, index=False)
    equity_df = pd.DataFrame(equity_curve_data)
    equity_df.to_csv(OUT_EQUITY_CURVES_CSV, index=False)
    drawdown_df = pd.DataFrame(drawdown_rows)
    drawdown_df.to_csv(OUT_DRAWDOWNS_CSV, index=False)
    robustness_df.to_csv(OUT_ROBUSTNESS_CSV, index=False)
    regime_df.to_csv(OUT_REGIME_RESULTS_CSV, index=False)
    temporal_df.to_csv(OUT_TEMPORAL_RESULTS_CSV, index=False)

    print(f"  [SAVED] {OUT_STRATEGY_RESULTS_CSV}")
    print(f"  [SAVED] {OUT_TRADE_LOG_CSV}")
    print(f"  [SAVED] {OUT_EQUITY_CURVES_CSV}")
    print(f"  [SAVED] {OUT_DRAWDOWNS_CSV}")
    print(f"  [SAVED] {OUT_ROBUSTNESS_CSV}")
    print(f"  [SAVED] {OUT_REGIME_RESULTS_CSV}")
    print(f"  [SAVED] {OUT_TEMPORAL_RESULTS_CSV}")

    print("\n=======================================================")
    print("  PHASE 11 STAGE 1 OOF EVALUATION COMPLETE")
    print("=======================================================")


if __name__ == "__main__":
    main()
