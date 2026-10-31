"""Phase 12 Step 7: Signal Stability Under Alternative Training-Window Specifications.

Research Question:
Does the weak residual predictive relationship observed in Phase 12 Step 6 survive
when the model is trained under alternative but pre-specified chronological training-window
structures (W0, W1, W2, W3), or is the observed signal mainly an artifact of the
expanding-window history and temporal concentration?

Four Pre-registered Window Specifications:
- W0 (Expanding): Preceding development data from 2008-07-08 through fold k-1 (sealed Step 2 reference).
- W1 (5-Year Rolling): Preceding 5 calendar years of development data ([Y_k - 5, Y_k - 1]).
- W2 (3-Year Rolling): Preceding 3 calendar years of development data ([Y_k - 3, Y_k - 1]).
- W3 (2-Year Rolling): Preceding 2 calendar years of development data ([Y_k - 2, Y_k - 1]).

Strict Governance:
- Zero terminal holdout access (2022-01-03 to 2026-09-03, N=1,154 is quarantined).
- Identical OOF evaluation population: 2014-01-02 to 2021-12-31, exactly N=1,960 sessions across 8 folds.
- 63 Model 1 features (45 Price + 18 Context; ZERO News, ZERO Volume, ZERO Flow proxies).
- Deterministic, chronological training-only inner validation (last 20%) for tree-count N* selection.
- Fold-local training baselines (mu_train) computed strictly from the window's training observations.
- Placebo permutation test (seed=42, 1,000 permutations).
- Economic diagnostic at 0, 5, 10, 20 bps.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import xgboost as xgb

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import load_multimodal_dataset

# Directories
OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step7"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"

# Protected checksums
PROTECTED_STEP5_HASHES = {
    "phase12_step5_target_comparison.csv": "6ec7040f75d26c5b0f54ce33cded5e6baacaebdadea2b99968fcd2f2880de0d0",
    "phase12_step5_fold_results.csv": "041c75bce9cceb847850ffdc17069494e0c44795b4a78c853e9028859c6e1399",
    "phase12_step5_temporal_results.csv": "f14a859412b7e0ac841c9235f66849adb5ff521b675df698f26ee371d412e788",
    "phase12_step5_sign_base_rate.csv": "2344bcffabd0ea2129c70b4d140e9446836fc042f744089bd196c4d38922dd4d",
    "phase12_step5_magnitude_calibration.csv": "501fc01546929c97a847927f1e227e0e6a74c5e56dcf2abe067db5668f1154ae",
    "phase12_step5_economic_stress.csv": "e1c8f04d74c9ece80999e9dcd425a674b4e91da1bcbb4afb7cf6fe5465bffae6",
    "phase12_step5_placebo.csv": "084416736d8d13555576ee5858876ae59260b88bc452c847896e6aab49a424db",
    "phase12_step5_manifest.json": "acf3d7ce73919ddc8545e0c3a506abd44ef0b5aa8e29fb20865e6a85621db10b",
    "phase12_step5_corrected_sign_base_rate.csv": "ac42f0fe9f16f47da077b9a1e5d55d9b385646f54236bfe1b4e1c96c5d46276a",
    "phase12_step5_corrected_economic_stress.csv": "f1447629a6d6c142d960be0fc5b0c4f52484d02825954109118d9e4125d57f88",
}

PROTECTED_STEP6_HASHES = {
    "phase12_step6_economic_diagnostic.csv": "19341254f4448d6a0628313c909d6b4ab82843f64363853a584961d8160041ce",
    "phase12_step6_fold_results.csv": "317e9fb735347351be6e4bb44b807b6f419aaa0021badf20f19b2e2cc8b36c11",
    "phase12_step6_magnitude.csv": "f2f82819aad307aa5816dce101da847e52964ea880ddb6c9ea85293357467181",
    "phase12_step6_manifest.json": "cd39329b02772d81c5594bb1d3342795c8384f692952f4b293b8599c10bc6453",
    "phase12_step6_placebo.csv": "a6e30a69c9a2229ddcb5855360cb2a54d214672b6ea4c201688afee388dbf9d1",
    "phase12_step6_residual_predictions.csv": "41dae563cbb48f2ab84cf1b8f18edf190abbecdf82d5b7104e797a63755604af",
    "phase12_step6_temporal_results.csv": "85e901e45e6327640131011460146b0221956d0a2f8ae15e8c6be1aceea6dfe8",
}


def verify_protected_checksums() -> None:
    """Ensure all protected Phase 4-10, Step 5, and Step 6 artifacts remain unmodified."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        if not fp.is_file():
            raise FileNotFoundError(f"Missing protected file: {rel_path}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for {rel_path}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    for fn, exp_hash in PROTECTED_STEP5_HASHES.items():
        fp = PHASE12_DIR / fn
        if not fp.is_file():
            raise FileNotFoundError(f"Missing Step 5 file: {fn}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for Step 5 file {fn}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    for fn, exp_hash in PROTECTED_STEP6_HASHES.items():
        fp = PHASE12_DIR / fn
        if not fp.is_file():
            raise FileNotFoundError(f"Missing Step 6 file: {fn}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for Step 6 file {fn}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    print("[CHECKSUMS] All 36 protected Phase 4-10, Step 5, and Step 6 artifacts verified.")


def safe_correlation(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float, float]:
    """Compute Pearson and Spearman correlation safely, returning (0.0, 1.0, 0.0, 1.0) for constant arrays."""
    if len(np.unique(x)) <= 1 or np.std(x) < 1e-8:
        return 0.0, 1.0, 0.0, 1.0
    if len(np.unique(y)) <= 1 or np.std(y) < 1e-8:
        return 0.0, 1.0, 0.0, 1.0
    r_p, p_p = stats.pearsonr(x, y)
    r_s, p_s = stats.spearmanr(x, y)
    return float(r_p), float(p_p), float(r_s), float(p_s)


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


def select_optimal_tree_count(
    X_train: np.ndarray,
    y_train: np.ndarray,
    params: Dict[str, Any],
    candidate_trees: List[int],
    val_ratio: float = 0.20,
) -> Tuple[int, float]:
    """Chronological inner validation on training fold to select optimal tree count N*."""
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

    return best_trees, best_rmse


def main() -> None:
    print("=" * 90)
    print("PHASE 12 STEP 7: SIGNAL STABILITY UNDER ALTERNATIVE TRAINING-WINDOW SPECIFICATIONS")
    print("=" * 90)

    # 1. Checksums
    print("\n--- Step 1: Checksum Verification ---")
    verify_protected_checksums()

    # 2. Load Dataset
    print("\n--- Step 2: Loading Snapshot B Multimodal Dataset ---")
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    dev_indices, holdout_indices = splitter.get_development_and_holdout_indices(ds_b.dates)
    folds = splitter.split_development(ds_b.dates)

    assert len(dev_indices) == 3299
    assert len(holdout_indices) == 1154
    assert len(folds) == 8

    # Extract price target (intraday open-to-close)
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    dev_dates = [ds_b.dates[i] for i in dev_indices]
    dev_target_dates = [ds_b.target_dates[i] for i in dev_indices]

    intraday_returns_dev = []
    for d_ref, d_tgt in zip(dev_dates, dev_target_dates):
        p_tgt = price_df.loc[d_tgt.isoformat()]
        o1 = float(p_tgt["open"])
        c1 = float(p_tgt["close"])
        intraday_returns_dev.append((c1 - o1) / o1)

    y_dev = np.array(intraday_returns_dev, dtype=np.float64)

    # Extract features (Model 1: exactly 63 features)
    X_all, feat_names = ds_b.get_features("Model 1")
    assert len(feat_names) == 63
    X_dev = X_all[dev_indices]

    dev_date_arr = np.array(dev_dates)

    # Base XGBoost params
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

    # Windows definition
    windows = [
        ("W0", "Expanding Window", None),
        ("W1", "5-Year Rolling Window", 5),
        ("W2", "3-Year Rolling Window", 3),
        ("W3", "2-Year Rolling Window", 2),
    ]

    # Containers for outputs
    oof_predictions: Dict[str, np.ndarray] = {w[0]: np.zeros(len(dev_indices), dtype=np.float64) for w in windows}
    oof_baselines: Dict[str, np.ndarray] = {w[0]: np.zeros(len(dev_indices), dtype=np.float64) for w in windows}

    tree_count_rows = []
    fold_result_rows = []

    print("\n--- Step 3: Walk-Forward Training across 4 Windows & 8 Folds ---")

    for w_code, w_name, roll_years in windows:
        print(f"\n>> Executing Specification {w_code} ({w_name})...")

        for fold in folds:
            f_id = fold.fold_id
            val_idx = fold.val_indices
            val_year = fold.val_start_date.year

            # Determine training window start date
            if roll_years is None:
                train_start_date = dev_date_arr[0]
            else:
                train_start_date = date(val_year - roll_years, 1, 1)

            train_end_date = date(val_year - 1, 12, 31)

            tr_mask = (dev_date_arr >= train_start_date) & (dev_date_arr <= train_end_date)
            tr_idx = np.where(tr_mask)[0]

            assert len(tr_idx) > 0, f"Empty training set for {w_code} fold {f_id}"
            assert dev_date_arr[tr_idx[-1]] < fold.val_start_date, f"Leakage: train {dev_date_arr[tr_idx[-1]]} >= val {fold.val_start_date}"

            X_tr = X_dev[tr_idx]
            y_tr = y_dev[tr_idx]
            X_val = X_dev[val_idx]
            y_val = y_dev[val_idx]

            best_n_trees, best_rmse = select_optimal_tree_count(
                X_tr, y_tr, xgb_base_params, candidate_trees, val_ratio=0.20
            )

            n_inner_val = int(len(tr_idx) * 0.20)
            n_inner_train = len(tr_idx) - n_inner_val

            tree_count_rows.append({
                "fold_id": f_id,
                "val_year": val_year,
                "window_code": w_code,
                "window_name": w_name,
                "candidate_grid": str(candidate_trees),
                "inner_val_ratio": 0.20,
                "n_train": len(tr_idx),
                "n_inner_train": n_inner_train,
                "n_inner_val": n_inner_val,
                "selected_n_trees": best_n_trees,
                "inner_val_best_rmse": best_rmse,
            })

            model = xgb.XGBRegressor(**xgb_base_params, n_estimators=best_n_trees)
            model.fit(X_tr, y_tr)
            val_preds = model.predict(X_val)

            mu_tr = float(np.mean(y_tr))
            base_preds = np.full(len(val_idx), mu_tr)

            oof_predictions[w_code][val_idx] = val_preds
            oof_baselines[w_code][val_idx] = base_preds

            excess_pred = val_preds - mu_tr
            res_return = y_val - mu_tr

            # Fold Metrics
            mae_raw = float(np.mean(np.abs(y_val - val_preds)))
            rmse_raw = math.sqrt(float(np.mean((y_val - val_preds) ** 2)))
            raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(val_preds, y_val)
            dir_acc = float(np.mean(np.sign(val_preds) == np.sign(y_val)))

            mse_baseline = float(np.mean(res_return ** 2))
            mse_model = float(np.mean((y_val - val_preds) ** 2))
            inc_r2 = 1.0 - (mse_model / mse_baseline) if mse_baseline > 0 else 0.0

            res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(excess_pred, res_return)
            res_dir_acc = float(np.mean(np.sign(excess_pred) == np.sign(res_return)))

            mae_res_baseline = float(np.mean(np.abs(res_return)))
            rmse_res_baseline = math.sqrt(mse_baseline)

            fold_result_rows.append({
                "fold_id": f_id,
                "val_year": val_year,
                "window_code": w_code,
                "window_name": w_name,
                "train_start_date": dev_date_arr[tr_idx[0]].isoformat(),
                "train_end_date": dev_date_arr[tr_idx[-1]].isoformat(),
                "val_start_date": fold.val_start_date.isoformat(),
                "val_end_date": fold.val_end_date.isoformat(),
                "n_train": len(tr_idx),
                "n_val": len(val_idx),
                "selected_n_trees": best_n_trees,
                "training_baseline_bps": mu_tr * 10000.0,
                "realized_raw_mean_bps": float(np.mean(y_val)) * 10000.0,
                "mean_raw_pred_bps": float(np.mean(val_preds)) * 10000.0,
                "mean_excess_pred_bps": float(np.mean(excess_pred)) * 10000.0,
                "mean_residual_ret_bps": float(np.mean(res_return)) * 10000.0,
                "raw_pearson_ic": raw_p_ic,
                "raw_pearson_pvalue": raw_p_pval,
                "raw_spearman_ic": raw_s_ic,
                "raw_spearman_pvalue": raw_s_pval,
                "residual_pearson_ic": res_p_ic,
                "residual_pearson_pvalue": res_p_pval,
                "residual_spearman_ic": res_s_ic,
                "residual_spearman_pvalue": res_s_pval,
                "raw_mae_bps": mae_raw * 10000.0,
                "raw_rmse_bps": rmse_raw * 10000.0,
                "baseline_residual_mae_bps": mae_res_baseline * 10000.0,
                "baseline_residual_rmse_bps": rmse_res_baseline * 10000.0,
                "incremental_r2_pct": inc_r2 * 100.0,
                "raw_directional_accuracy_pct": dir_acc * 100.0,
                "residual_directional_accuracy_pct": res_dir_acc * 100.0,
            })

            print(f"  [{w_code}] Fold {f_id} ({val_year}): Train N={len(tr_idx):4d}, N*={best_n_trees:2d} | "
                  f"Raw IC={raw_p_ic:+.4f} | Res IC={res_p_ic:+.4f} (p={res_p_pval:.3f}) | Inc R2={inc_r2*100:+.2f}%")

    # 4. Construct OOF Predictions Dataset
    print("\n--- Step 4: Constructing OOF Predictions Dataset ---")
    oof_indices = np.concatenate([f.val_indices for f in folds])
    assert len(oof_indices) == 1960

    fold_id_arr = np.zeros(len(dev_indices), dtype=int)
    for f in folds:
        fold_id_arr[f.val_indices] = f.fold_id

    pred_rows = []
    for idx in oof_indices:
        d_tr = dev_dates[idx].isoformat()
        d_tgt = dev_target_dates[idx].isoformat()
        f_id = int(fold_id_arr[idx])
        y_val = float(y_dev[idx])

        row = {
            "trading_date": d_tr,
            "target_date": d_tgt,
            "fold_id": f_id,
            "realized_intraday_return": y_val,
        }

        for w_code, _, _ in windows:
            p_val = float(oof_predictions[w_code][idx])
            b_val = float(oof_baselines[w_code][idx])
            exc_val = p_val - b_val
            res_val = y_val - b_val

            row[f"pred_{w_code}"] = p_val
            row[f"baseline_{w_code}"] = b_val
            row[f"excess_pred_{w_code}"] = exc_val
            row[f"residual_ret_{w_code}"] = res_val

        pred_rows.append(row)

    df_predictions = pd.DataFrame(pred_rows)
    pred_csv_path = OUT_DIR / "step7_predictions.csv"
    df_predictions.to_csv(pred_csv_path, index=False)
    print(f"Saved {pred_csv_path} ({len(df_predictions)} rows).")

    # Verify W0 reproduction against Step 6
    s6_res = pd.read_csv(PHASE12_DIR / "phase12_step6_residual_predictions.csv")
    max_pred_diff = np.max(np.abs(df_predictions["pred_W0"].values - s6_res["raw_prediction"].values))
    max_base_diff = np.max(np.abs(df_predictions["baseline_W0"].values - s6_res["fold_baseline"].values))
    max_res_diff = np.max(np.abs(df_predictions["residual_ret_W0"].values - s6_res["residual_return"].values))
    print(f"W0 vs Step 6 Raw Prediction Max Diff: {max_pred_diff:.2e}")
    print(f"W0 vs Step 6 Baseline Max Diff:       {max_base_diff:.2e}")
    print(f"W0 vs Step 6 Residual Return Max Diff:{max_res_diff:.2e}")
    assert max_pred_diff < 1e-12, f"W0 does not match Step 6: max diff {max_pred_diff}"
    assert max_base_diff < 1e-12, f"W0 baseline does not match Step 6: max diff {max_base_diff}"

    # 5. Tree Counts Dataset
    df_tree_counts = pd.DataFrame(tree_count_rows)
    tree_csv_path = OUT_DIR / "step7_tree_counts.csv"
    df_tree_counts.to_csv(tree_csv_path, index=False)
    print(f"Saved {tree_csv_path} ({len(df_tree_counts)} rows).")

    # 6. Fold Results Dataset
    df_fold_results = pd.DataFrame(fold_result_rows)
    fold_csv_path = OUT_DIR / "step7_fold_results.csv"
    df_fold_results.to_csv(fold_csv_path, index=False)
    print(f"Saved {fold_csv_path} ({len(df_fold_results)} rows).")

    # 7. Temporal Results Dataset (Blocks & Annual)
    print("\n--- Step 5: Temporal Results (Blocks & Annual) ---")
    df_predictions["year"] = pd.to_datetime(df_predictions["trading_date"]).dt.year
    def get_block(yr: int) -> str:
        if 2014 <= yr <= 2016:
            return "Block A (2014-2016)"
        elif 2017 <= yr <= 2019:
            return "Block B (2017-2019)"
        else:
            return "Block C (2020-2021)"
    df_predictions["block"] = df_predictions["year"].apply(get_block)

    temporal_rows = []
    for w_code, w_name, _ in windows:
        # Blocks
        for blk_name, grp in df_predictions.groupby("block"):
            y_raw = grp["realized_intraday_return"].values
            p_raw = grp[f"pred_{w_code}"].values
            y_res = grp[f"residual_ret_{w_code}"].values
            p_exc = grp[f"excess_pred_{w_code}"].values

            raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(p_raw, y_raw)
            res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(p_exc, y_res)

            mse_b = float(np.mean(y_res ** 2))
            mse_m = float(np.mean((y_raw - p_raw) ** 2))
            inc_r2 = 1.0 - (mse_m / mse_b) if mse_b > 0 else 0.0

            dir_acc = float(np.mean(np.sign(p_raw) == np.sign(y_raw)))
            res_dir_acc = float(np.mean(np.sign(p_exc) == np.sign(y_res)))

            temporal_rows.append({
                "window_code": w_code,
                "window_name": w_name,
                "period_type": "Block",
                "period_name": blk_name,
                "n_sessions": len(grp),
                "raw_pearson_ic": raw_p_ic,
                "raw_pearson_pvalue": raw_p_pval,
                "raw_spearman_ic": raw_s_ic,
                "raw_spearman_pvalue": raw_s_pval,
                "residual_pearson_ic": res_p_ic,
                "residual_pearson_pvalue": res_p_pval,
                "residual_spearman_ic": res_s_ic,
                "residual_spearman_pvalue": res_s_pval,
                "incremental_r2_pct": inc_r2 * 100.0,
                "raw_directional_accuracy_pct": dir_acc * 100.0,
                "residual_directional_accuracy_pct": res_dir_acc * 100.0,
                "baseline_mse": mse_b,
                "model_mse": mse_m,
            })

        # Annual
        for yr, grp in df_predictions.groupby("year"):
            y_raw = grp["realized_intraday_return"].values
            p_raw = grp[f"pred_{w_code}"].values
            y_res = grp[f"residual_ret_{w_code}"].values
            p_exc = grp[f"excess_pred_{w_code}"].values

            raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(p_raw, y_raw)
            res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(p_exc, y_res)

            mse_b = float(np.mean(y_res ** 2))
            mse_m = float(np.mean((y_raw - p_raw) ** 2))
            inc_r2 = 1.0 - (mse_m / mse_b) if mse_b > 0 else 0.0

            dir_acc = float(np.mean(np.sign(p_raw) == np.sign(y_raw)))
            res_dir_acc = float(np.mean(np.sign(p_exc) == np.sign(y_res)))

            temporal_rows.append({
                "window_code": w_code,
                "window_name": w_name,
                "period_type": "Year",
                "period_name": str(yr),
                "n_sessions": len(grp),
                "raw_pearson_ic": raw_p_ic,
                "raw_pearson_pvalue": raw_p_pval,
                "raw_spearman_ic": raw_s_ic,
                "raw_spearman_pvalue": raw_s_pval,
                "residual_pearson_ic": res_p_ic,
                "residual_pearson_pvalue": res_p_pval,
                "residual_spearman_ic": res_s_ic,
                "residual_spearman_pvalue": res_s_pval,
                "incremental_r2_pct": inc_r2 * 100.0,
                "raw_directional_accuracy_pct": dir_acc * 100.0,
                "residual_directional_accuracy_pct": res_dir_acc * 100.0,
                "baseline_mse": mse_b,
                "model_mse": mse_m,
            })

    df_temporal = pd.DataFrame(temporal_rows)
    temporal_csv_path = OUT_DIR / "step7_temporal_results.csv"
    df_temporal.to_csv(temporal_csv_path, index=False)
    print(f"Saved {temporal_csv_path} ({len(df_temporal)} rows).")

    # 8. Summary / Direct Stability Comparison
    print("\n--- Step 6: Summary & Direct Stability Comparison ---")
    summary_rows = []
    y_raw_all = df_predictions["realized_intraday_return"].values

    p_raw_w0 = df_predictions["pred_W0"].values
    p_exc_w0 = df_predictions["excess_pred_W0"].values
    y_res_w0 = df_predictions["residual_ret_W0"].values
    w0_res_ic, _, _, _ = safe_correlation(p_exc_w0, y_res_w0)
    mse_b_w0 = float(np.mean(y_res_w0 ** 2))
    mse_m_w0 = float(np.mean((y_raw_all - p_raw_w0) ** 2))
    w0_inc_r2 = (1.0 - (mse_m_w0 / mse_b_w0)) * 100.0

    for w_code, w_name, _ in windows:
        p_raw = df_predictions[f"pred_{w_code}"].values
        b_raw = df_predictions[f"baseline_{w_code}"].values
        p_exc = df_predictions[f"excess_pred_{w_code}"].values
        y_res = df_predictions[f"residual_ret_{w_code}"].values

        raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(p_raw, y_raw_all)
        res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(p_exc, y_res)

        mse_b = float(np.mean(y_res ** 2))
        mse_m = float(np.mean((y_raw_all - p_raw) ** 2))
        inc_r2 = 1.0 - (mse_m / mse_b) if mse_b > 0 else 0.0

        raw_mae = float(np.mean(np.abs(y_raw_all - p_raw))) * 10000.0
        raw_rmse = math.sqrt(mse_m) * 10000.0
        res_mae = float(np.mean(np.abs(y_res))) * 10000.0
        res_rmse = math.sqrt(mse_b) * 10000.0

        dir_acc = float(np.mean(np.sign(p_raw) == np.sign(y_raw_all))) * 100.0
        res_dir_acc = float(np.mean(np.sign(p_exc) == np.sign(y_res))) * 100.0

        f_sub = df_fold_results[df_fold_results["window_code"] == w_code]
        mean_n_tr = float(f_sub["n_train"].mean())
        mean_trees = float(f_sub["selected_n_trees"].mean())

        mean_p = float(np.mean(p_raw)) * 10000.0
        mean_y = float(np.mean(y_raw_all)) * 10000.0
        mean_res = float(np.mean(y_res)) * 10000.0
        std_p = float(np.std(p_raw, ddof=1)) * 10000.0
        std_y = float(np.std(y_raw_all, ddof=1)) * 10000.0
        fc_bias = mean_p - mean_y

        pct_short = float(np.mean(p_raw < 0)) * 100.0
        pct_long = float(np.mean(p_raw > 0)) * 100.0
        ret_when_short = float(np.mean(y_raw_all[p_raw < 0])) * 10000.0 if np.sum(p_raw < 0) > 0 else 0.0
        ret_when_long = float(np.mean(y_raw_all[p_raw > 0])) * 10000.0 if np.sum(p_raw > 0) > 0 else 0.0

        summary_rows.append({
            "window_code": w_code,
            "window_name": w_name,
            "n_eval_sessions": len(df_predictions),
            "mean_n_train": mean_n_tr,
            "mean_n_trees": mean_trees,
            "raw_pearson_ic": raw_p_ic,
            "raw_pearson_pvalue": raw_p_pval,
            "raw_spearman_ic": raw_s_ic,
            "raw_spearman_pvalue": raw_s_pval,
            "residual_pearson_ic": res_p_ic,
            "residual_pearson_pvalue": res_p_pval,
            "residual_spearman_ic": res_s_ic,
            "residual_spearman_pvalue": res_s_pval,
            "incremental_r2_pct": inc_r2 * 100.0,
            "raw_directional_accuracy_pct": dir_acc,
            "residual_directional_accuracy_pct": res_dir_acc,
            "raw_mae_bps": raw_mae,
            "raw_rmse_bps": raw_rmse,
            "baseline_residual_mae_bps": res_mae,
            "baseline_residual_rmse_bps": res_rmse,
            "mean_pred_bps": mean_p,
            "mean_realized_bps": mean_y,
            "mean_residual_bps": mean_res,
            "std_pred_bps": std_p,
            "std_realized_bps": std_y,
            "forecast_bias_bps": fc_bias,
            "pct_pred_short": pct_short,
            "pct_pred_long": pct_long,
            "mean_ret_when_pred_short_bps": ret_when_short,
            "mean_ret_when_pred_long_bps": ret_when_long,
            "diff_residual_ic_vs_w0": res_p_ic - w0_res_ic,
            "diff_incremental_r2_vs_w0": inc_r2 * 100.0 - w0_inc_r2,
        })

    df_summary = pd.DataFrame(summary_rows)
    summary_csv_path = OUT_DIR / "step7_summary.csv"
    df_summary.to_csv(summary_csv_path, index=False)
    print(f"Saved {summary_csv_path} ({len(df_summary)} rows).")

    # 9. Placebo Permutation Results
    print("\n--- Step 7: Placebo Permutation Test (Seed 42, 1,000 permutations) ---")
    placebo_rows = []
    n_perm = 1000

    for w_code, w_name, _ in windows:
        p_exc = df_predictions[f"excess_pred_{w_code}"].values
        y_res = df_predictions[f"residual_ret_{w_code}"].values

        obs_ic, obs_pval, _, _ = safe_correlation(p_exc, y_res)
        np.random.seed(42)
        perm_ics = []
        for _ in range(n_perm):
            p_perm = np.random.permutation(p_exc)
            r_p, _, _, _ = safe_correlation(p_perm, y_res)
            perm_ics.append(r_p)

        perm_arr = np.array(perm_ics)
        mean_p_ic = float(np.mean(perm_arr))
        std_p_ic = float(np.std(perm_arr, ddof=1))
        emp_pct = float(stats.percentileofscore(perm_arr, obs_ic))
        emp_pval = float(np.mean(perm_arr >= obs_ic))

        placebo_rows.append({
            "window_code": w_code,
            "window_name": w_name,
            "n_eval_sessions": len(df_predictions),
            "n_permutations": n_perm,
            "seed": 42,
            "observed_residual_pearson_ic": obs_ic,
            "observed_residual_pearson_pvalue": obs_pval,
            "placebo_mean_ic": mean_p_ic,
            "placebo_std_ic": std_p_ic,
            "empirical_percentile": emp_pct,
            "empirical_pvalue": emp_pval,
        })
        print(f"  [{w_code}] Obs IC={obs_ic:+.4f} | Placebo Mean={mean_p_ic:+.4f} (std={std_p_ic:.4f}) | Emp P-val={emp_pval:.4f}")

    df_placebo = pd.DataFrame(placebo_rows)
    placebo_csv_path = OUT_DIR / "step7_placebo_results.csv"
    df_placebo.to_csv(placebo_csv_path, index=False)
    print(f"Saved {placebo_csv_path} ({len(df_placebo)} rows).")

    # 10. Economic Diagnostic (Not a Strategy)
    print("\n--- Step 8: Economic Diagnostic (0, 5, 10, 20 bps friction) ---")
    econ_rows = []
    cost_scenarios = [0.0, 5.0, 10.0, 20.0]

    for w_code, w_name, _ in windows:
        p_raw = df_predictions[f"pred_{w_code}"].values
        pos = np.where(p_raw > 0, 1.0, np.where(p_raw < 0, -1.0, 0.0))
        n_long = int(np.sum(pos > 0))
        n_short = int(np.sum(pos < 0))
        n_flat = int(np.sum(pos == 0))
        pct_short = n_short / len(pos) * 100.0

        for cost_bps in cost_scenarios:
            cost = cost_bps / 10000.0
            r_net = pos * y_raw_all - (cost * (pos != 0.0))

            mean_d_bps = float(np.mean(r_net)) * 10000.0
            hac_se, hac_t, hac_p = compute_newey_west_hac(r_net)
            hac_se_bps = hac_se * 10000.0

            cum_ret = float(np.prod(1.0 + r_net) - 1.0)
            ann_ret = float((np.prod(1.0 + r_net) ** (252.0 / len(r_net))) - 1.0) if np.all(1.0 + r_net > 0) else -1.0
            ann_vol = float(np.std(r_net, ddof=1) * math.sqrt(252.0))
            sharpe = ann_ret / ann_vol if ann_vol > 0 else 0.0
            max_dd, _ = compute_drawdowns(r_net)

            econ_rows.append({
                "window_code": w_code,
                "window_name": w_name,
                "cost_bps": cost_bps,
                "n_sessions": len(pos),
                "n_long": n_long,
                "n_short": n_short,
                "n_flat": n_flat,
                "pct_short": pct_short,
                "mean_daily_return_bps": mean_d_bps,
                "hac_se_bps": hac_se_bps,
                "hac_tstat": hac_t,
                "hac_pvalue": hac_p,
                "cum_return_pct": cum_ret * 100.0,
                "annualized_return_pct": ann_ret * 100.0,
                "annualized_volatility_pct": ann_vol * 100.0,
                "sharpe_ratio": sharpe,
                "max_drawdown_pct": max_dd * 100.0,
            })

    df_econ = pd.DataFrame(econ_rows)
    econ_csv_path = OUT_DIR / "step7_economic_diagnostic.csv"
    df_econ.to_csv(econ_csv_path, index=False)
    print(f"Saved {econ_csv_path} ({len(df_econ)} rows).")

    # 11. Create Integrity Manifest
    print("\n--- Step 9: Creating Step 7 Integrity Manifest ---")
    manifest = {
        "step_name": "Phase 12 Step 7: Training Window Stability Research",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_firewall": {
            "max_trading_date": str(df_predictions["trading_date"].max()),
            "holdout_start_date": "2022-01-03",
            "terminal_holdout_quarantined": True,
            "holdout_sessions_accessed": 0,
        },
        "oof_population": {
            "start_date": str(df_predictions["trading_date"].min()),
            "end_date": str(df_predictions["trading_date"].max()),
            "n_sessions": len(df_predictions),
            "n_folds": len(folds),
        },
        "feature_specification": {
            "feature_set": "Snapshot B Model 1",
            "n_features": len(feat_names),
            "price_features": 45,
            "context_features": 18,
            "news_features": 0,
            "volume_features": 0,
            "flow_features": 0,
        },
        "window_specifications": {
            "W0": "Expanding window from 2008-07-08",
            "W1": "5-year rolling window",
            "W2": "3-year rolling window",
            "W3": "2-year rolling window",
        },
        "summary_metrics": {
            row["window_code"]: {
                "raw_pearson_ic": row["raw_pearson_ic"],
                "residual_pearson_ic": row["residual_pearson_ic"],
                "incremental_r2_pct": row["incremental_r2_pct"],
                "residual_directional_accuracy_pct": row["residual_directional_accuracy_pct"],
                "pct_pred_short": row["pct_pred_short"],
            }
            for _, row in df_summary.iterrows()
        },
        "file_hashes": {},
    }

    # Hash all generated interim files
    for p in sorted(OUT_DIR.glob("step7_*.csv")):
        manifest["file_hashes"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()

    manifest_path = OUT_DIR / "step7_integrity_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved {manifest_path}.")

    print("\n" + "=" * 90)
    print("PHASE 12 STEP 7 EXPERIMENT EXECUTION COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
