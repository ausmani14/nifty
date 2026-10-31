"""
Phase 12 Step 6: Residual Signal & Conditional Forecasting Research
Evaluates whether Snapshot B Model 1 contains incremental conditional information
about residual intraday returns after removing fold-local training baselines.

Strict Governance:
- DEVELOPMENT DATA ONLY: 2014-01-02 to 2021-12-31 (OOF N=1,960).
- ZERO access to consumed 2022-2026 Terminal Holdout.
- ZERO News features, volume, or flow proxies.
- Expanding 8-fold walk-forward cross-validation with fold-local training baselines.
- Preserves all Phase 12 Step 5 artifacts.
"""

from __future__ import annotations

import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import load_multimodal_dataset

INTERIM_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
INTERIM_DIR.mkdir(parents=True, exist_ok=True)

HOLDOUT_START_DATE = "2022-01-03"

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

COST_SCENARIOS = [0.0, 5.0, 10.0, 20.0]


def verify_holdout_firewall(df: pd.DataFrame) -> None:
    """Ensure no observation has trading_date beyond 2021-12-31."""
    if "trading_date" in df.columns:
        t_dates = pd.to_datetime(df["trading_date"]).dt.date
        max_date = str(t_dates.max())
        if max_date > "2021-12-31":
            raise ValueError(
                f"FATAL HOLDOUT BREACH: trading_date has date {max_date} > 2021-12-31."
            )


def compute_newey_west_hac(returns: np.ndarray, max_lags: int | None = None) -> Tuple[float, float, float]:
    """Compute Newey-West HAC standard error, t-stat, and p-value."""
    n = len(returns)
    if n < 2 or np.all(returns == 0.0):
        return 0.0, 0.0, 1.0
    mean_val = float(np.mean(returns))
    e = returns - mean_val
    if np.sum(np.abs(e)) < 1e-14:
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

    hac_se = math.sqrt(max(1e-16, hac_var / n))
    t_stat = mean_val / hac_se if hac_se > 0 else 0.0
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))
    return hac_se, t_stat, p_val


def compute_drawdowns(returns: np.ndarray) -> Tuple[float, np.ndarray]:
    """Compute maximum drawdown and drawdown series."""
    equity = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(np.min(dd)) if len(dd) > 0 else 0.0
    return max_dd, dd


def main() -> None:
    print("PHASE 12 STEP 6: RESIDUAL SIGNAL & CONDITIONAL FORECASTING RESEARCH")
    print("=" * 80)

    # 1. Load Step 3 Diagnostics (Contains frozen Step 2 OOF Predictions)
    print("\n[1/7] Loading Step 3 diagnostics dataset...")
    s3_path = INTERIM_DIR / "step3_selective_diagnostics.csv"
    if not s3_path.exists():
        raise FileNotFoundError(f"Missing required prerequisite: {s3_path}")
    s3 = pd.read_csv(s3_path)
    assert len(s3) == 1960, f"Expected 1,960 OOF rows, got {len(s3)}"
    verify_holdout_firewall(s3)

    # 2. Extract Fold-Local Training Means (Strictly training observations only)
    print("\n[2/7] Computing fold-local training baselines...")
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    dev_indices, _ = splitter.get_development_and_holdout_indices(ds_b.dates)
    folds = splitter.split_development(ds_b.dates)

    dev_dates = [ds_b.dates[i] for i in dev_indices]
    dev_target_dates = [ds_b.target_dates[i] for i in dev_indices]

    y_a_list = []
    for d_ref, d_tgt in zip(dev_dates, dev_target_dates):
        p_ref = price_df.loc[d_ref.isoformat()]
        p_tgt = price_df.loc[d_tgt.isoformat()]
        o1 = float(p_tgt["open"])
        c1 = float(p_tgt["close"])
        y_a_list.append((c1 - o1) / o1)
    y_a = np.array(y_a_list, dtype=np.float64)

    fold_baselines: Dict[int, float] = {}
    fold_info: Dict[int, Dict[str, Any]] = {}

    for fold in folds:
        tr_idx = fold.train_indices
        val_idx = fold.val_indices
        y_tr = y_a[tr_idx]
        base_mean = float(np.mean(y_tr))
        fold_baselines[fold.fold_id] = base_mean
        val_dates = [dev_dates[i] for i in val_idx]
        fold_info[fold.fold_id] = {
            "n_train": len(tr_idx),
            "n_val": len(val_idx),
            "baseline_mean": base_mean,
            "val_year": val_dates[0].year,
            "start_date": val_dates[0].isoformat(),
            "end_date": val_dates[-1].isoformat(),
        }
        print(f"  Fold {fold.fold_id} ({val_dates[0].year}): Train N={len(tr_idx)} | Baseline Mean = {base_mean * 10000.0:+.4f} bps")

    # 3. Construct Residual Target & Excess Prediction
    print("\n[3/7] Constructing residual target and excess prediction series...")
    s3["fold_baseline"] = s3["fold_id"].map(fold_baselines)
    s3["residual_return"] = s3["y_true_intraday"] - s3["fold_baseline"]
    s3["excess_prediction"] = s3["pred_reg_intraday"] - s3["fold_baseline"]

    # Verify Numerical Identities
    err_target_id = np.max(np.abs(s3["y_true_intraday"] - (s3["fold_baseline"] + s3["residual_return"])))
    err_pred_id = np.max(np.abs(s3["pred_reg_intraday"] - (s3["fold_baseline"] + s3["excess_prediction"])))
    assert err_target_id < 1e-15, f"Target decomposition identity violated: max error = {err_target_id}"
    assert err_pred_id < 1e-15, f"Prediction decomposition identity violated: max error = {err_pred_id}"
    print(f"  Numerical Identity 1 (Target): Max Error = {err_target_id:.2e} [VERIFIED]")
    print(f"  Numerical Identity 2 (Prediction): Max Error = {err_pred_id:.2e} [VERIFIED]")

    # Save Residual Predictions Dataset
    res_pred_df = s3[[
        "trading_date", "execution_date", "fold_id",
        "y_true_intraday", "pred_reg_intraday", "fold_baseline",
        "residual_return", "excess_prediction"
    ]].rename(columns={
        "y_true_intraday": "raw_target",
        "pred_reg_intraday": "raw_prediction"
    })
    res_pred_path = INTERIM_DIR / "phase12_step6_residual_predictions.csv"
    res_pred_df.to_csv(res_pred_path, index=False)
    print(f"  Saved {res_pred_path} ({len(res_pred_df)} rows)")

    # 4. Generate Walk-Forward Fold Results Table
    print("\n[4/7] Generating Walk-Forward Fold Results Table...")
    fold_rows = []
    for f_id in range(1, 9):
        sub = s3[s3["fold_id"] == f_id]
        f_meta = fold_info[f_id]
        y_raw = sub["y_true_intraday"].values
        p_raw = sub["pred_reg_intraday"].values
        y_res = sub["residual_return"].values
        p_exc = sub["excess_prediction"].values
        b_val = f_meta["baseline_mean"]

        r_p, p_p = stats.pearsonr(p_exc, y_res)
        r_s, p_s = stats.spearmanr(p_exc, y_res)

        mse_b = float(np.mean(y_res ** 2))
        mse_m = float(np.mean((y_raw - p_raw) ** 2))
        inc_r2 = 1.0 - (mse_m / mse_b) if mse_b > 0 else 0.0

        mae_b = float(np.mean(np.abs(y_res))) * 10000.0
        mae_m = float(np.mean(np.abs(y_raw - p_raw))) * 10000.0
        rmse_b = math.sqrt(mse_b) * 10000.0
        rmse_m = math.sqrt(mse_m) * 10000.0

        hit_res = float(np.mean(np.sign(p_exc) == np.sign(y_res)))

        fold_rows.append({
            "fold_id": f_id,
            "val_year": f_meta["val_year"],
            "start_date": f_meta["start_date"],
            "end_date": f_meta["end_date"],
            "n_train": f_meta["n_train"],
            "n_val": f_meta["n_val"],
            "training_baseline_bps": b_val * 10000.0,
            "realized_raw_mean_bps": float(np.mean(y_raw)) * 10000.0,
            "mean_raw_pred_bps": float(np.mean(p_raw)) * 10000.0,
            "mean_excess_pred_bps": float(np.mean(p_exc)) * 10000.0,
            "mean_residual_ret_bps": float(np.mean(y_res)) * 10000.0,
            "pearson_ic": r_p,
            "pearson_pvalue": p_p,
            "spearman_ic": r_s,
            "spearman_pvalue": p_s,
            "baseline_mae_bps": mae_b,
            "model_mae_bps": mae_m,
            "baseline_rmse_bps": rmse_b,
            "model_rmse_bps": rmse_m,
            "incremental_r2_pct": inc_r2 * 100.0,
            "residual_directional_accuracy_pct": hit_res * 100.0,
        })

    df_folds = pd.DataFrame(fold_rows)
    fold_path = INTERIM_DIR / "phase12_step6_fold_results.csv"
    df_folds.to_csv(fold_path, index=False)
    print(f"  Saved {fold_path} (8 folds)")

    # 5. Temporal Stability (Blocks & Annual)
    print("\n[5/7] Generating Temporal Stability Results Table...")
    s3["year"] = pd.to_datetime(s3["trading_date"]).dt.year
    def get_block(yr: int) -> str:
        if 2014 <= yr <= 2016:
            return "Block A (2014-2016)"
        elif 2017 <= yr <= 2019:
            return "Block B (2017-2019)"
        else:
            return "Block C (2020-2021)"
    s3["block"] = s3["year"].apply(get_block)

    temporal_rows = []
    # Blocks
    for blk_name, grp in s3.groupby("block"):
        y_raw = grp["y_true_intraday"].values
        p_raw = grp["pred_reg_intraday"].values
        y_res = grp["residual_return"].values
        p_exc = grp["excess_prediction"].values

        r_p, p_p = stats.pearsonr(p_exc, y_res)
        r_s, p_s = stats.spearmanr(p_exc, y_res)
        mse_b = float(np.mean(y_res ** 2))
        mse_m = float(np.mean((y_raw - p_raw) ** 2))
        inc_r2 = 1.0 - (mse_m / mse_b) if mse_b > 0 else 0.0
        hit_res = float(np.mean(np.sign(p_exc) == np.sign(y_res)))

        temporal_rows.append({
            "period_type": "Block",
            "period_name": blk_name,
            "n_sessions": len(grp),
            "pearson_ic": r_p,
            "pearson_pvalue": p_p,
            "spearman_ic": r_s,
            "spearman_pvalue": p_s,
            "incremental_r2_pct": inc_r2 * 100.0,
            "residual_directional_accuracy_pct": hit_res * 100.0,
            "baseline_mse": mse_b,
            "model_mse": mse_m,
        })

    # Annual
    for yr, grp in s3.groupby("year"):
        y_raw = grp["y_true_intraday"].values
        p_raw = grp["pred_reg_intraday"].values
        y_res = grp["residual_return"].values
        p_exc = grp["excess_prediction"].values

        r_p, p_p = stats.pearsonr(p_exc, y_res)
        r_s, p_s = stats.spearmanr(p_exc, y_res)
        mse_b = float(np.mean(y_res ** 2))
        mse_m = float(np.mean((y_raw - p_raw) ** 2))
        inc_r2 = 1.0 - (mse_m / mse_b) if mse_b > 0 else 0.0
        hit_res = float(np.mean(np.sign(p_exc) == np.sign(y_res)))

        temporal_rows.append({
            "period_type": "Year",
            "period_name": str(yr),
            "n_sessions": len(grp),
            "pearson_ic": r_p,
            "pearson_pvalue": p_p,
            "spearman_ic": r_s,
            "spearman_pvalue": p_s,
            "incremental_r2_pct": inc_r2 * 100.0,
            "residual_directional_accuracy_pct": hit_res * 100.0,
            "baseline_mse": mse_b,
            "model_mse": mse_m,
        })

    df_temp = pd.DataFrame(temporal_rows)
    temp_path = INTERIM_DIR / "phase12_step6_temporal_results.csv"
    df_temp.to_csv(temp_path, index=False)
    print(f"  Saved {temp_path} (11 rows)")

    # 6. Magnitude Calibration
    print("\n[6/7] Generating Magnitude Calibration Table...")
    p_exc_all = s3["excess_prediction"].values
    y_res_all = s3["residual_return"].values
    abs_exc = np.abs(p_exc_all)
    mag_rows = []

    for b_name, low, high in MAGNITUDE_BINS:
        mask = (abs_exc >= low) & (abs_exc < high)
        n_b = int(np.sum(mask))
        if n_b > 0:
            p_b = p_exc_all[mask]
            y_b = y_res_all[mask]
            mean_p_b = float(np.mean(p_b)) * 10000.0
            mean_y_b = float(np.mean(y_b)) * 10000.0
            med_y_b = float(np.median(y_b)) * 10000.0
            mae_b = float(np.mean(np.abs(p_b - y_b))) * 10000.0
            hit_b = float(np.mean(np.sign(p_b) == np.sign(y_b)))
            std_y_b = float(np.std(y_b, ddof=1)) * 10000.0 if n_b > 1 else 0.0
            se_b = std_y_b / math.sqrt(n_b) if n_b > 1 else 0.0

            mag_rows.append({
                "bin_name": b_name,
                "n_obs": n_b,
                "pct_total": n_b / len(s3) * 100.0,
                "mean_excess_pred_bps": mean_p_b,
                "mean_residual_ret_bps": mean_y_b,
                "median_residual_ret_bps": med_y_b,
                "mae_bps": mae_b,
                "directional_accuracy_pct": hit_b * 100.0,
                "ci_lower_95_bps": mean_y_b - 1.96 * se_b,
                "ci_upper_95_bps": mean_y_b + 1.96 * se_b,
                "tier": "Inferential (N>=50)" if n_b >= 50 else "Descriptive (N<50)",
            })

    df_mag = pd.DataFrame(mag_rows)
    mag_path = INTERIM_DIR / "phase12_step6_magnitude.csv"
    df_mag.to_csv(mag_path, index=False)
    print(f"  Saved {mag_path} (5 bins)")

    # 7. Placebo & Economic Diagnostics
    print("\n[7/7] Generating Placebo and Economic Diagnostic Tables...")
    # Placebo Test (fixed seed = 42, 1,000 permutations)
    np.random.seed(42)
    n_perm = 1000
    perm_ics = []
    for _ in range(n_perm):
        p_perm = np.random.permutation(p_exc_all)
        r_perm, _ = stats.pearsonr(p_perm, y_res_all)
        perm_ics.append(r_perm)

    perm_ics_arr = np.array(perm_ics)
    obs_ic, obs_p = stats.pearsonr(p_exc_all, y_res_all)
    placebo_mean = float(np.mean(perm_ics_arr))
    placebo_std = float(np.std(perm_ics_arr, ddof=1))
    emp_pval = float(np.mean(perm_ics_arr >= obs_ic))
    emp_pctile = float(stats.percentileofscore(perm_ics_arr, obs_ic))

    placebo_rows = [{
        "experiment": "Excess Prediction Permutation Null",
        "n_permutations": n_perm,
        "seed": 42,
        "observed_pearson_ic": obs_ic,
        "observed_pearson_pvalue": obs_p,
        "placebo_mean_ic": placebo_mean,
        "placebo_std_ic": placebo_std,
        "empirical_percentile": emp_pctile,
        "empirical_pvalue": emp_pval,
        "methodological_limitation": "Simple permutation ignores serial autocorrelation; evaluate alongside Newey-West HAC.",
    }]
    df_placebo = pd.DataFrame(placebo_rows)
    placebo_path = INTERIM_DIR / "phase12_step6_placebo.csv"
    df_placebo.to_csv(placebo_path, index=False)
    print(f"  Saved {placebo_path}")

    # Economic Diagnostic Table
    pos_exc = np.sign(p_exc_all)
    n_pos_exc = int(np.sum(pos_exc > 0))
    n_neg_exc = int(np.sum(pos_exc < 0))
    econ_rows = []

    for cost_bps in COST_SCENARIOS:
        cost = cost_bps / 10000.0
        r_net = pos_exc * y_res_all - cost
        cum_ret = float(np.prod(1.0 + r_net) - 1.0)
        ann_ret = float((np.prod(1.0 + r_net) ** (252.0 / len(r_net))) - 1.0)
        ann_vol = float(np.std(r_net, ddof=1) * math.sqrt(252.0))
        sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
        max_dd, _ = compute_drawdowns(r_net)

        econ_rows.append({
            "strategy": "Conditional Residual Sign",
            "cost_bps": cost_bps,
            "active_sessions": len(r_net),
            "long_sessions": n_pos_exc,
            "short_sessions": n_neg_exc,
            "exposure_pct": 100.0,
            "cumulative_net_return": cum_ret,
            "annualized_net_return": ann_ret,
            "annualized_volatility": ann_vol,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
        })

    for b_name, b_pos in [("Always Residual Long", 1.0), ("Always Residual Short", -1.0)]:
        for cost_bps in [0.0, 10.0]:
            cost = cost_bps / 10000.0
            r_net = b_pos * y_res_all - cost
            cum_ret = float(np.prod(1.0 + r_net) - 1.0)
            ann_ret = float((np.prod(1.0 + r_net) ** (252.0 / len(r_net))) - 1.0)
            ann_vol = float(np.std(r_net, ddof=1) * math.sqrt(252.0))
            sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
            max_dd, _ = compute_drawdowns(r_net)

            econ_rows.append({
                "strategy": b_name,
                "cost_bps": cost_bps,
                "active_sessions": len(r_net),
                "long_sessions": 1960 if b_pos == 1.0 else 0,
                "short_sessions": 1960 if b_pos == -1.0 else 0,
                "exposure_pct": 100.0,
                "cumulative_net_return": cum_ret,
                "annualized_net_return": ann_ret,
                "annualized_volatility": ann_vol,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
            })

    df_econ = pd.DataFrame(econ_rows)
    econ_path = INTERIM_DIR / "phase12_step6_economic_diagnostic.csv"
    df_econ.to_csv(econ_path, index=False)
    print(f"  Saved {econ_path}")

    # Manifest JSON
    manifest = {
        "step_name": "Phase 12 Step 6: Residual Signal & Conditional Forecasting Research",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sample_size_oof": len(s3),
        "oof_date_range": ["2014-01-02", "2021-12-31"],
        "model_features_count": 63,
        "fold_baselines_bps": {f: fold_baselines[f] * 10000.0 for f in fold_baselines},
        "overall_residual_pearson_ic": obs_ic,
        "overall_residual_spearman_ic": float(stats.spearmanr(p_exc_all, y_res_all)[0]),
        "overall_incremental_r2_pct": float((1.0 - np.mean((s3['y_true_intraday'] - s3['pred_reg_intraday'])**2) / np.mean(y_res_all**2)) * 100.0),
        "overall_residual_directional_accuracy_pct": float(np.mean(np.sign(p_exc_all) == np.sign(y_res_all)) * 100.0),
        "placebo_empirical_pvalue": emp_pval,
        "holdout_firewall_status": "PASS - ZERO OBSERVATIONS >= 2022-01-03 ACCESSED",
    }
    manifest_path = INTERIM_DIR / "phase12_step6_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"  Saved {manifest_path}")

    print("\nPhase 12 Step 6 quantitative data processing COMPLETE.")


if __name__ == "__main__":
    main()
