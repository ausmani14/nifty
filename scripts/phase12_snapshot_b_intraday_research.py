"""Phase 12 Step 2: Snapshot B Morning-to-Close Intraday Target Research.

Research Question:
Does Snapshot B at 08:50 IST, after observing overnight/global context but before the 09:15 IST
market open, contain measurable incremental predictive information about the subsequent same-day
NIFTY Open-to-Close return?

Target:
R_intraday(T+1) = (Close(T+1) - Open(T+1)) / Open(T+1)

Strict Governance:
- DEVELOPMENT DATA ONLY: 2008-07-08 to 2021-12-31 (N=3,299).
- ZERO access to consumed 2022-2026 Terminal Holdout.
- Expanding 8-fold walk-forward validation (2014-2021, N=1,960).
- Inner walk-forward / chronological validation on training folds to select optimal tree count N*.
- 63 Model 1 features (45 Price + 18 Context, ZERO News).
- Comparison against pre-registered baselines (Always Long, Always Short, Zero, Historical Mean).
- Diagnostic economic evaluation at 0, 5, 10, 20 bps without strategy tuning.
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
import xgboost as xgb

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import (
    PRICE_FEATURE_NAMES,
    CONTEXT_FEATURE_NAMES,
    load_multimodal_dataset,
)

# Output Paths
OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
OUT_TARGET_CSV = OUT_DIR / "snapshot_b_intraday_target_dev.csv"
OUT_OOF_RESULTS_CSV = OUT_DIR / "snapshot_b_intraday_oof_results.csv"
OUT_FOLD_RESULTS_CSV = OUT_DIR / "snapshot_b_intraday_fold_results.csv"
OUT_DIAGNOSTICS_CSV = OUT_DIR / "snapshot_b_intraday_diagnostics.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"


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
            raise ValueError(f"Checksum mismatch for {rel_path}!\nExpected: {exp_hash}\nActual:   {act_hash}")
    print("[CHECKSUMS] All 19 protected Phase 4-10 artifacts verified.")


def compute_newey_west_tstat(returns: np.ndarray, max_lags: Optional[int] = None) -> Tuple[float, float, float]:
    """Compute Newey-West HAC standard error, t-stat, and p-value for mean daily series."""
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


def compute_drawdown_series(equity_curve: np.ndarray) -> np.ndarray:
    """Calculate the drawdown series from an equity curve."""
    peaks = np.maximum.accumulate(equity_curve)
    dd = (equity_curve - peaks) / peaks
    return dd


def select_optimal_tree_count(
    X_train: np.ndarray,
    y_train: np.ndarray,
    params: Dict[str, Any],
    candidate_trees: List[int],
    val_ratio: float = 0.20,
) -> int:
    """Select optimal tree count N* using chronological inner validation on training fold."""
    n_total = len(X_train)
    n_inner_val = int(n_total * val_ratio)
    n_inner_train = n_total - n_inner_val

    X_in_tr = X_train[:n_inner_train]
    y_in_tr = y_train[:n_inner_train]
    X_in_val = X_train[n_inner_train:]
    y_in_val = y_train[n_inner_train:]

    best_rmse = float("inf")
    best_trees = candidate_trees[0]

    for n_trees in candidate_trees:
        model = xgb.XGBRegressor(**params, n_estimators=n_trees)
        model.fit(X_in_tr, y_in_tr)
        preds = model.predict(X_in_val)
        rmse = math.sqrt(float(np.mean((y_in_val - preds) ** 2)))
        if rmse < best_rmse:
            best_rmse = rmse
            best_trees = n_trees

    return best_trees


def main() -> None:
    print("=" * 90)
    print("PHASE 12 STEP 2: SNAPSHOT B MORNING-TO-CLOSE INTRADAY TARGET RESEARCH")
    print("=" * 90)

    # 1. Verify protected inputs
    print("\n--- Step 1: Checksum & Protected Artifact Verification ---")
    verify_protected_checksums()

    # 2. Load Snapshot B Multimodal Dataset (Development Partition Only)
    print("\n--- Step 2: Loading Snapshot B Multimodal Dataset ---")
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    
    # Restrict strictly to development partition (dates <= 2021-12-31)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    dev_indices, holdout_indices = splitter.get_development_and_holdout_indices(ds_b.dates)
    folds = splitter.split_development(ds_b.dates)
    
    print(f"Total supervised sessions in dataset: {len(ds_b.dates)}")
    print(f"Development sessions (<= 2021-12-31): {len(dev_indices)}")
    print(f"Terminal Holdout sessions (quarantined): {len(holdout_indices)}")
    assert len(dev_indices) == 3299, f"Expected 3,299 dev sessions, found {len(dev_indices)}"
    assert len(folds) == 8, f"Expected 8 walk-forward folds, found {len(folds)}"

    # 3. Construct Aligned Intraday Target for Development
    print("\n--- Step 3: Constructing Intraday Target for Development Sessions ---")
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    
    target_rows = []
    dev_dates = [ds_b.dates[i] for i in dev_indices]
    dev_target_dates = [ds_b.target_dates[i] for i in dev_indices]

    intraday_returns_dev = []
    for d_ref, d_tgt in zip(dev_dates, dev_target_dates):
        d_ref_str = d_ref.isoformat()
        d_tgt_str = d_tgt.isoformat()

        p_tgt = price_df.loc[d_tgt_str]
        open_t1 = float(p_tgt["open"])
        close_t1 = float(p_tgt["close"])

        r_intraday = (close_t1 - open_t1) / open_t1
        intraday_returns_dev.append(r_intraday)

        target_rows.append({
            "trading_date": d_ref_str,
            "target_date": d_tgt_str,
            "open_t1": open_t1,
            "close_t1": close_t1,
            "target_intraday_return": r_intraday,
            "target_direction": "UP" if r_intraday > 0 else ("DOWN" if r_intraday < 0 else "FLAT"),
        })

    target_df = pd.DataFrame(target_rows)
    y_intraday_dev = np.array(intraday_returns_dev, dtype=np.float64)

    # 4. Extract Model 1 Features for Development (63 features: 45 Price + 18 Context)
    print("\n--- Step 4: Extracting Model 1 Features (63 Features, Zero News) ---")
    X_all, feat_names = ds_b.get_features("Model 1")
    assert len(feat_names) == 63
    X_dev = X_all[dev_indices]
    assert len(X_dev) == 3299

    # Verify no NaN or Inf
    assert not np.isnan(X_dev).any()
    assert not np.isnan(y_intraday_dev).any()

    # 5. Model Parameters and Walk-Forward Training
    print("\n--- Step 5: Walk-Forward Expanding Cross-Validation (8 Folds) ---")
    xgb_base_params = {
        "objective": "reg:squarederror",
        "learning_rate": 0.05,
        "max_depth": 2,
        "min_child_weight": 20.0,
        "subsample": 0.8,
        "colsample_bytree": 0.7,
        "reg_alpha": 0.5,
        "reg_lambda": 2.0,
        "random_state": 42,
        "n_jobs": -1,
    }
    candidate_trees = [10, 15, 20, 25, 30, 35, 40, 45, 50, 60]

    oof_preds = np.zeros(len(dev_indices), dtype=np.float64)
    oof_baseline_hist_mean = np.zeros(len(dev_indices), dtype=np.float64)
    oof_mask = np.zeros(len(dev_indices), dtype=bool)

    fold_summary_rows = []

    for fold in folds:
        f_id = fold.fold_id
        tr_idx = fold.train_indices
        val_idx = fold.val_indices

        X_tr = X_dev[tr_idx]
        y_tr = y_intraday_dev[tr_idx]
        X_val = X_dev[val_idx]
        y_val = y_intraday_dev[val_idx]

        # Inner chronological validation on training set to choose N*
        opt_n_trees = select_optimal_tree_count(
            X_tr, y_tr, xgb_base_params, candidate_trees, val_ratio=0.20
        )

        # Train model with optimal N*
        model = xgb.XGBRegressor(**xgb_base_params, n_estimators=opt_n_trees)
        model.fit(X_tr, y_tr)
        val_preds = model.predict(X_val)

        # Baseline: Historical conditional mean from training fold only
        hist_mean_tr = float(np.mean(y_tr))
        baseline_hist_mean_preds = np.full(len(val_idx), hist_mean_tr)

        # Store in OOF array
        oof_preds[val_idx] = val_preds
        oof_baseline_hist_mean[val_idx] = baseline_hist_mean_preds
        oof_mask[val_idx] = True

        # Compute Fold Predictive Metrics
        mae_model = float(np.mean(np.abs(y_val - val_preds)))
        rmse_model = math.sqrt(float(np.mean((y_val - val_preds) ** 2)))
        mae_zero = float(np.mean(np.abs(y_val)))
        rmse_zero = math.sqrt(float(np.mean(y_val ** 2)))
        mae_hist = float(np.mean(np.abs(y_val - hist_mean_tr)))
        rmse_hist = math.sqrt(float(np.mean((y_val - hist_mean_tr) ** 2)))

        # ICs
        if np.std(val_preds) > 1e-12:
            p_ic, p_pval = stats.pearsonr(val_preds, y_val)
            s_ic, s_pval = stats.spearmanr(val_preds, y_val)
        else:
            p_ic, p_pval = 0.0, 1.0
            s_ic, s_pval = 0.0, 1.0

        # Sign agreement (Hit Rate)
        hit_rate_model = float(np.mean(np.sign(val_preds) == np.sign(y_val)))
        hit_rate_long = float(np.mean(y_val > 0))
        hit_rate_short = float(np.mean(y_val < 0))

        # Diagnostic economic return (10 bps)
        pos_model = np.where(val_preds > 0, 1, np.where(val_preds < 0, -1, 0))
        cost_10bps = np.where(pos_model != 0, 0.0010, 0.0)
        net_ret_fold = pos_model * y_val - cost_10bps
        ann_net_fold = float(np.mean(net_ret_fold) * 252.0)
        sharpe_fold = (np.mean(net_ret_fold) / np.std(net_ret_fold, ddof=1) * math.sqrt(252.0)) if np.std(net_ret_fold, ddof=1) > 1e-9 else 0.0

        fold_summary_rows.append({
            "fold_id": f_id,
            "era_name": fold.era_name,
            "val_year": fold.val_start_date.year,
            "train_sessions": len(tr_idx),
            "val_sessions": len(val_idx),
            "selected_n_trees": opt_n_trees,
            "historical_mean_train": hist_mean_tr,
            "realized_intraday_mean": float(np.mean(y_val)),
            "rmse_model": rmse_model,
            "rmse_zero_baseline": rmse_zero,
            "rmse_hist_mean_baseline": rmse_hist,
            "mae_model": mae_model,
            "pearson_ic": p_ic,
            "pearson_pvalue": p_pval,
            "spearman_ic": s_ic,
            "spearman_pvalue": s_pval,
            "hit_rate_model": hit_rate_model,
            "hit_rate_always_long": hit_rate_long,
            "hit_rate_always_short": hit_rate_short,
            "ann_net_return_10bps": ann_net_fold,
            "sharpe_net_10bps": sharpe_fold,
        })
        print(f"  Fold {f_id} ({fold.val_start_date.year}): N*={opt_n_trees:2d} | Pearson IC={p_ic:+.4f} (p={p_pval:.3f}) | HitRate={hit_rate_model*100:.1f}% | Net Ann={ann_net_fold*100:+.2f}%")

    fold_df = pd.DataFrame(fold_summary_rows)

    # 6. Aggregate OOF Evaluation (2014-2021, N=1,960)
    print("\n--- Step 6: Aggregate OOF Performance & Statistical Tests ---")
    val_indices_total = np.where(oof_mask)[0]
    n_oof = len(val_indices_total)
    assert n_oof == 1960, f"Expected 1,960 OOF observations, found {n_oof}"

    y_oof = y_intraday_dev[val_indices_total]
    preds_oof = oof_preds[val_indices_total]
    hist_means_oof = oof_baseline_hist_mean[val_indices_total]

    # Predictive Metrics
    mae_oof_model = float(np.mean(np.abs(y_oof - preds_oof)))
    rmse_oof_model = math.sqrt(float(np.mean((y_oof - preds_oof) ** 2)))
    mae_oof_zero = float(np.mean(np.abs(y_oof)))
    rmse_oof_zero = math.sqrt(float(np.mean(y_oof ** 2)))
    mae_oof_hist = float(np.mean(np.abs(y_oof - hist_means_oof)))
    rmse_oof_hist = math.sqrt(float(np.mean((y_oof - hist_means_oof) ** 2)))

    p_ic_oof, p_pval_oof = stats.pearsonr(preds_oof, y_oof)
    s_ic_oof, s_pval_oof = stats.spearmanr(preds_oof, y_oof)

    hit_rate_oof_model = float(np.mean(np.sign(preds_oof) == np.sign(y_oof)))
    hit_rate_oof_long = float(np.mean(y_oof > 0))
    hit_rate_oof_short = float(np.mean(y_oof < 0))

    bias_oof = float(np.mean(preds_oof - y_oof))

    # Diebold-Mariano / Paired t-test on squared error vs Zero baseline
    sq_err_model = (y_oof - preds_oof) ** 2
    sq_err_zero = y_oof ** 2
    sq_err_diff = sq_err_model - sq_err_zero
    dm_se, dm_tstat, dm_pval = compute_newey_west_tstat(sq_err_diff)

    print(f"Aggregate OOF Pearson IC:  {p_ic_oof:+.4f} (p = {p_pval_oof:.4e})")
    print(f"Aggregate OOF Spearman IC: {s_ic_oof:+.4f} (p = {s_pval_oof:.4e})")
    print(f"Model RMSE vs Zero RMSE:   {rmse_oof_model:.6f} vs {rmse_oof_zero:.6f} (DM t-stat: {dm_tstat:+.2f}, p: {dm_pval:.4e})")
    print(f"Directional Hit Rate:      Model={hit_rate_oof_model*100:.2f}% | Always Long={hit_rate_oof_long*100:.2f}% | Always Short={hit_rate_oof_short*100:.2f}%")
    print(f"Forecast Bias:             {bias_oof:+.6f}")

    # 7. Diagnostic Economic Returns Across Cost Scenarios (0, 5, 10, 20 bps)
    print("\n--- Step 7: Diagnostic Economic Return Evaluation across Cost Scenarios ---")
    pos_oof = np.where(preds_oof > 0, 1, np.where(preds_oof < 0, -1, 0))
    n_trades = int(np.sum(pos_oof != 0))

    econ_rows = []
    for cost_bps, cost_frac in [(0.0, 0.0), (5.0, 0.0005), (10.0, 0.0010), (20.0, 0.0020)]:
        daily_cost = np.where(pos_oof != 0, cost_frac, 0.0)
        daily_gross = pos_oof * y_oof
        daily_net = daily_gross - daily_cost

        eq_net = np.cumprod(1.0 + daily_net)
        cum_net = float(eq_net[-1] - 1.0)
        ann_net = (1.0 + cum_net) ** (252.0 / n_oof) - 1.0 if (1.0 + cum_net) > 0 else -1.0
        ann_vol = float(np.std(daily_net, ddof=1) * math.sqrt(252.0))
        mean_d = float(np.mean(daily_net))
        std_d = float(np.std(daily_net, ddof=1))
        sharpe = (mean_d / std_d * math.sqrt(252.0)) if std_d > 1e-9 else 0.0

        dd = compute_drawdown_series(eq_net)
        max_dd = float(np.min(dd))
        calmar = ann_net / abs(max_dd) if abs(max_dd) > 1e-6 else 0.0

        win_mask = daily_net > 0
        win_rate = float(np.mean(win_mask))
        winners = daily_net[win_mask]
        losers = daily_net[daily_net < 0]
        pf = (float(np.sum(winners)) / float(np.sum(np.abs(losers)))) if len(losers) > 0 else 0.0

        hac_se, hac_tstat, hac_pval = compute_newey_west_tstat(daily_net)

        econ_rows.append({
            "model_target": "Snapshot B Intraday Return (Close_{T+1}/Open_{T+1} - 1)",
            "cost_scenario_bps": cost_bps,
            "cumulative_net_return": cum_net,
            "annualized_net_return": ann_net,
            "annualized_volatility": ann_vol,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "calmar_ratio": calmar,
            "win_rate": win_rate,
            "profit_factor": pf,
            "hac_tstat": hac_tstat,
            "hac_pvalue": hac_pval,
        })
        print(f"  Cost {cost_bps:4.1f} bps: Ann Net={ann_net*100:+6.2f}% | Sharpe={sharpe:+5.2f} | Max DD={max_dd*100:6.2f}% | Win Rate={win_rate*100:4.1f}% | HAC p={hac_pval:.4e}")

    econ_df = pd.DataFrame(econ_rows)

    # 8. Save All Research Artifacts
    print("\n--- Step 8: Saving Structured Research Artifacts ---")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save target file
    target_df.to_csv(OUT_TARGET_CSV, index=False)
    print(f"  [SAVED] {OUT_TARGET_CSV}")

    # Save OOF predictions and session diagnostics
    oof_dates = [ds_b.dates[i].isoformat() for i in val_indices_total]
    oof_target_dates = [ds_b.target_dates[i].isoformat() for i in val_indices_total]
    diag_df = pd.DataFrame({
        "trading_date": oof_dates,
        "execution_date": oof_target_dates,
        "y_true_intraday": y_oof,
        "pred_reg_intraday": preds_oof,
        "baseline_hist_mean": hist_means_oof,
        "pred_direction": np.where(preds_oof > 0, "UP", "DOWN"),
        "realized_direction": np.where(y_oof > 0, "UP", "DOWN"),
        "is_correct_sign": np.sign(preds_oof) == np.sign(y_oof),
        "daily_net_return_10bps": pos_oof * y_oof - np.where(pos_oof != 0, 0.0010, 0.0),
    })
    diag_df.to_csv(OUT_DIAGNOSTICS_CSV, index=False)
    print(f"  [SAVED] {OUT_DIAGNOSTICS_CSV}")

    # Save Fold Results
    fold_df.to_csv(OUT_FOLD_RESULTS_CSV, index=False)
    print(f"  [SAVED] {OUT_FOLD_RESULTS_CSV}")

    # Save OOF Results Summary
    oof_summary = pd.DataFrame([{
        "n_sessions": n_oof,
        "start_date": oof_dates[0],
        "end_date": oof_dates[-1],
        "pearson_ic": p_ic_oof,
        "pearson_pvalue": p_pval_oof,
        "spearman_ic": s_ic_oof,
        "spearman_pvalue": s_pval_oof,
        "rmse_model": rmse_oof_model,
        "rmse_zero": rmse_oof_zero,
        "rmse_hist_mean": rmse_oof_hist,
        "mae_model": mae_oof_model,
        "mae_zero": mae_oof_zero,
        "mae_hist_mean": mae_oof_hist,
        "hit_rate_model": hit_rate_oof_model,
        "hit_rate_always_long": hit_rate_oof_long,
        "hit_rate_always_short": hit_rate_oof_short,
        "forecast_bias": bias_oof,
        "diebold_mariano_tstat_vs_zero": dm_tstat,
        "diebold_mariano_pvalue_vs_zero": dm_pval,
    }])
    oof_combined = pd.concat([oof_summary, econ_df], axis=1)
    oof_combined.to_csv(OUT_OOF_RESULTS_CSV, index=False)
    print(f"  [SAVED] {OUT_OOF_RESULTS_CSV}")

    print("\n=======================================================")
    print("  PHASE 12 STEP 2 EXPERIMENT COMPLETE")
    print("=======================================================")


if __name__ == "__main__":
    main()
