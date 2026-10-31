"""Phase 12 Step 8: Feature Information Stability & Information-Set Ablation Research.

Research Objective:
Determine whether the weak Snapshot B intraday predictive relationship is dependent
on particular feature families, or whether the apparent signal disappears when
individual information families are removed.

Pre-registered Configurations:
- Reference: G0_ALL (63 features: 45 Price + 18 Context)
- Standalone:
    G1_PRICE (45 features)
    G2_CONTEXT (18 features)
    G3_SHORT_PRICE (25 features)
    G4_MED_LONG_PRICE (10 features)
    G5_VOLATILITY (5 features)
    G6_DOMESTIC_CTX (5 features)
    G7_GLOBAL_CTX (8 features)
    G8_MACRO_CTX (5 features)
    G_CALENDAR (5 features)
- Leave-One-Out (LOO) Ablations:
    LOO_NO_PRICE (18 features, = G2_CONTEXT)
    LOO_NO_CONTEXT (45 features, = G1_PRICE)
    LOO_NO_SHORT_PRICE (38 features, G0 minus G3)
    LOO_NO_MED_LONG_PRICE (53 features, G0 minus G4)
    LOO_NO_VOLATILITY (58 features, G0 minus G5)
    LOO_NO_DOMESTIC_CTX (58 features, G0 minus G6)
    LOO_NO_GLOBAL_CTX (55 features, G0 minus G7)
    LOO_NO_MACRO_CTX (58 features, G0 minus G8)
    LOO_NO_CALENDAR (58 features, G0 minus Calendar)

Strict Governance:
- Zero terminal holdout access (2022-01-03 to 2026-09-03, N=1,154 is quarantined).
- Identical OOF evaluation population: 2014-01-02 to 2021-12-31, exactly N=1,960 sessions across 8 folds.
- Exactly 63 features (45 Price + 18 Context; ZERO News, ZERO Volume, ZERO Flow proxies).
- Expanding window W0 baseline for all configurations.
- Deterministic, chronological training-only inner validation (last 20%) for tree-count N* selection.
- Fold-local training baselines (mu_train) computed strictly from training observations.
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
OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step8"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
STEP7_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step7"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"

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

PROTECTED_STEP7_HASHES = {
    "step7_economic_diagnostic.csv": "2801997a874ee0eb1778a273430f47c5472343b8419b4ebed7f0cd993ad10c90",
    "step7_fold_results.csv": "230e90c3b7415e9d19d7c01714c72d6a779f6b40050ad4e547648eddbe3575f7",
    "step7_integrity_manifest.json": "d772c3714a2f79f1eb0520bf2ea0576eb4467d2cd2b8fdde9860e585b2866635",
    "step7_placebo_results.csv": "977397dd78737150e5bbac8a9f1b1e8e1545604697cb978bcc2db06606b01667",
    "step7_predictions.csv": "3a2ec99ed398f4cb1047326df2cee879a355712c98aa306f8e87d0680291013e",
    "step7_summary.csv": "de3b4c8adde8c2861c452e08ca0a5da5b901596bf0ad62de320770a11800ac6f",
    "step7_temporal_results.csv": "5953cdbd1bfa67d85c4a58e129fda337dcdea3ab0da330bc79647d524d441ed9",
    "step7_tree_counts.csv": "de78be51942b03d27af3a681c65c204aef090f8f948169d3fcfcd3f3be06f2ad",
}


def verify_protected_checksums() -> None:
    """Ensure all protected Phase 4-10, Step 5, Step 6, and Step 7 artifacts remain unmodified."""
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

    for fn, exp_hash in PROTECTED_STEP7_HASHES.items():
        fp = STEP7_DIR / fn
        if not fp.is_file():
            raise FileNotFoundError(f"Missing Step 7 file: {fn}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for Step 7 file {fn}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    print("[CHECKSUMS] All 44 protected Phase 4-10, Step 5, Step 6, and Step 7 artifacts verified.")


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
    print("PHASE 12 STEP 8: FEATURE INFORMATION STABILITY & ABLATION RESEARCH")
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

    # Extract all 63 features
    X_all, feat_names = ds_b.get_features("Model 1")
    assert len(feat_names) == 63
    X_dev = X_all[dev_indices]
    dev_date_arr = np.array(dev_dates)

    # Load Feature Registry
    reg_csv_path = OUT_DIR / "step8_feature_group_registry.csv"
    if not reg_csv_path.exists():
        raise FileNotFoundError(f"Missing registry: {reg_csv_path}")
    df_reg = pd.read_csv(reg_csv_path)

    # Feature groups
    feat_to_idx = {fn: i for i, fn in enumerate(feat_names)}

    configs = [
        # Code, Name, Category, Column In Registry
        ("G0_ALL", "All Features (Reference)", "Reference", "included_in_G0"),
        ("G1_PRICE", "Price Features Only", "Standalone", "included_in_G1"),
        ("G2_CONTEXT", "Context Features Only", "Standalone", "included_in_G2"),
        ("G3_SHORT_PRICE", "Short-Horizon Price Only", "Standalone", "included_in_G3"),
        ("G4_MED_LONG_PRICE", "Med/Long-Horizon Price Only", "Standalone", "included_in_G4"),
        ("G5_VOLATILITY", "Volatility/Risk Price Only", "Standalone", "included_in_G5"),
        ("G6_DOMESTIC_CTX", "Domestic Context Only", "Standalone", "included_in_G6"),
        ("G7_GLOBAL_CTX", "Global Context Only", "Standalone", "included_in_G7"),
        ("G8_MACRO_CTX", "Macro Context Only", "Standalone", "included_in_G8"),
        ("G_CALENDAR", "Calendar Features Only", "Standalone", "included_in_G_CALENDAR"),
        ("LOO_NO_PRICE", "Ablation: No Price (Context Only)", "Ablation", "included_in_LOO_NO_PRICE"),
        ("LOO_NO_CONTEXT", "Ablation: No Context (Price Only)", "Ablation", "included_in_LOO_NO_CONTEXT"),
        ("LOO_NO_SHORT_PRICE", "Ablation: No Short-Horizon Price", "Ablation", "included_in_LOO_NO_SHORT_PRICE"),
        ("LOO_NO_MED_LONG_PRICE", "Ablation: No Med/Long Price", "Ablation", "included_in_LOO_NO_MED_LONG_PRICE"),
        ("LOO_NO_VOLATILITY", "Ablation: No Volatility/Risk", "Ablation", "included_in_LOO_NO_VOLATILITY"),
        ("LOO_NO_DOMESTIC_CTX", "Ablation: No Domestic Context", "Ablation", "included_in_LOO_NO_DOMESTIC_CTX"),
        ("LOO_NO_GLOBAL_CTX", "Ablation: No Global Context", "Ablation", "included_in_LOO_NO_GLOBAL_CTX"),
        ("LOO_NO_MACRO_CTX", "Ablation: No Macro Context", "Ablation", "included_in_LOO_NO_MACRO_CTX"),
        ("LOO_NO_CALENDAR", "Ablation: No Calendar Features", "Ablation", "included_in_LOO_NO_CALENDAR"),
    ]

    config_feature_indices: Dict[str, List[int]] = {}
    for c_code, _, _, col in configs:
        selected_feats = df_reg[df_reg[col] == True]["feature_name"].tolist()
        indices = [feat_to_idx[fn] for fn in selected_feats]
        config_feature_indices[c_code] = sorted(indices)
        print(f"Config {c_code:<22}: {len(indices):2d} features")

    # XGBoost base params
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

    # Containers for predictions
    oof_predictions: Dict[str, np.ndarray] = {c[0]: np.zeros(len(dev_indices), dtype=np.float64) for c in configs}
    oof_baselines: np.ndarray = np.zeros(len(dev_indices), dtype=np.float64)

    fold_result_rows = []
    g0_feature_gains: List[Dict[str, float]] = []
    g0_feature_weights: List[Dict[str, float]] = []
    g0_feature_covers: List[Dict[str, float]] = []

    print("\n--- Step 3: Walk-Forward Training across 19 Configurations & 8 Folds ---")

    for c_idx, (c_code, c_name, c_cat, _) in enumerate(configs):
        feat_idx = config_feature_indices[c_code]
        print(f"\n>> [{c_idx+1}/19] Training Configuration {c_code} ({c_name}, n_feats={len(feat_idx)})...")

        for fold in folds:
            f_id = fold.fold_id
            val_idx = fold.val_indices
            val_year = fold.val_start_date.year

            # Expanding window training set (W0 baseline)
            train_end_date = date(val_year - 1, 12, 31)
            tr_mask = dev_date_arr <= train_end_date
            tr_idx = np.where(tr_mask)[0]

            assert len(tr_idx) > 0, f"Empty training set for {c_code} fold {f_id}"
            assert dev_date_arr[tr_idx[-1]] < fold.val_start_date, f"Leakage: train {dev_date_arr[tr_idx[-1]]} >= val {fold.val_start_date}"

            X_tr = X_dev[tr_idx][:, feat_idx]
            y_tr = y_dev[tr_idx]
            X_val = X_dev[val_idx][:, feat_idx]
            y_val = y_dev[val_idx]

            # Fold-local target baseline (mu_train)
            mu_train = float(np.mean(y_tr))
            oof_baselines[val_idx] = mu_train

            # Inner validation for tree selection
            best_trees, inner_rmse = select_optimal_tree_count(
                X_tr, y_tr, xgb_base_params, candidate_trees, val_ratio=0.20
            )

            # Refit on full training fold
            final_model = xgb.XGBRegressor(**xgb_base_params, n_estimators=best_trees)
            final_model.fit(X_tr, y_tr)

            preds = final_model.predict(X_val)
            oof_predictions[c_code][val_idx] = preds

            # For G0 reference model: extract booster feature scores for attribution
            if c_code == "G0_ALL":
                booster = final_model.get_booster()
                score_gain = booster.get_score(importance_type="gain")
                score_weight = booster.get_score(importance_type="weight")
                score_cover = booster.get_score(importance_type="cover")
                g0_feature_gains.append({feat_names[int(k[1:])]: v for k, v in score_gain.items()})
                g0_feature_weights.append({feat_names[int(k[1:])]: v for k, v in score_weight.items()})
                g0_feature_covers.append({feat_names[int(k[1:])]: v for k, v in score_cover.items()})

            # Fold metrics
            res_y = y_val - mu_train
            excess_p = preds - mu_train

            raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(preds, y_val)
            res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(excess_p, res_y)

            mse_b = float(np.mean(res_y ** 2))
            mse_m = float(np.mean((y_val - preds) ** 2))
            inc_r2 = 1.0 - (mse_m / mse_b) if mse_b > 0 else 0.0

            dir_acc = float(np.mean(np.sign(preds) == np.sign(y_val))) * 100.0
            res_dir_acc = float(np.mean(np.sign(excess_p) == np.sign(res_y))) * 100.0

            fold_result_rows.append({
                "config_code": c_code,
                "config_name": c_name,
                "config_category": c_cat,
                "n_features": len(feat_idx),
                "fold_id": f_id,
                "val_year": val_year,
                "n_train": len(tr_idx),
                "n_val": len(val_idx),
                "selected_n_trees": best_trees,
                "mu_train_bps": mu_train * 10000.0,
                "val_realized_bps": float(np.mean(y_val)) * 10000.0,
                "val_predicted_bps": float(np.mean(preds)) * 10000.0,
                "raw_mae_bps": float(np.mean(np.abs(y_val - preds))) * 10000.0,
                "raw_rmse_bps": math.sqrt(mse_m) * 10000.0,
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
                "pct_pred_short": float(np.mean(preds < 0)) * 100.0,
            })

    # Save Fold Results
    df_fold_results = pd.DataFrame(fold_result_rows)
    fold_csv_path = OUT_DIR / "step8_fold_results.csv"
    df_fold_results.to_csv(fold_csv_path, index=False)
    print(f"\nSaved {fold_csv_path} ({len(df_fold_results)} rows).")

    # Build OOF Predictions Dataframe
    print("\n--- Step 4: Building and Saving step8_predictions.csv ---")
    val_mask = np.zeros(len(dev_indices), dtype=bool)
    fold_ids_arr = np.zeros(len(dev_indices), dtype=int)
    for fold in folds:
        val_mask[fold.val_indices] = True
        fold_ids_arr[fold.val_indices] = fold.fold_id

    assert np.sum(val_mask) == 1960
    val_indices_all = np.where(val_mask)[0]

    pred_dict: Dict[str, Any] = {
        "trading_date": [dev_dates[i].isoformat() for i in val_indices_all],
        "target_date": [dev_target_dates[i].isoformat() for i in val_indices_all],
        "fold_id": fold_ids_arr[val_indices_all],
        "realized_intraday_return": y_dev[val_indices_all],
        "mu_train": oof_baselines[val_indices_all],
        "residual_realized_return": y_dev[val_indices_all] - oof_baselines[val_indices_all],
    }

    for c_code, _, _, _ in configs:
        p_c = oof_predictions[c_code][val_indices_all]
        exc_c = p_c - oof_baselines[val_indices_all]
        pred_dict[f"pred_{c_code}"] = p_c
        pred_dict[f"excess_{c_code}"] = exc_c
        pred_dict[f"sign_{c_code}"] = np.where(p_c >= 0, 1, -1)
        pred_dict[f"excess_sign_{c_code}"] = np.where(exc_c >= 0, 1, -1)

    df_predictions = pd.DataFrame(pred_dict)
    pred_csv_path = OUT_DIR / "step8_predictions.csv"
    df_predictions.to_csv(pred_csv_path, index=False)
    print(f"Saved {pred_csv_path} ({len(df_predictions)} rows).")

    # Temporal Results
    print("\n--- Step 5: Computing Temporal Results (Blocks & Forensic Years) ---")
    df_predictions["year"] = pd.to_datetime(df_predictions["trading_date"]).dt.year

    temporal_blocks = [
        ("Block_A", "Block A (2014-2016)", [2014, 2015, 2016]),
        ("Block_B", "Block B (2017-2019)", [2017, 2018, 2019]),
        ("Block_C", "Block C (2020-2021)", [2020, 2021]),
        ("Year_2021", "Year 2021 (Forensic Check)", [2021]),
        ("Years_2017_2019", "Years 2017-2019 (Forensic Check)", [2017, 2018, 2019]),
        ("Full_OOF", "Full OOF (2014-2021)", list(range(2014, 2022))),
    ]

    temporal_rows = []
    for c_code, c_name, c_cat, _ in configs:
        p_c = df_predictions[f"pred_{c_code}"].values
        exc_c = df_predictions[f"excess_{c_code}"].values
        y_real = df_predictions["realized_intraday_return"].values
        y_res = df_predictions["residual_realized_return"].values

        for b_code, b_name, years in temporal_blocks:
            mask = df_predictions["year"].isin(years).values
            p_sub = p_c[mask]
            exc_sub = exc_c[mask]
            y_sub = y_real[mask]
            y_res_sub = y_res[mask]

            raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(p_sub, y_sub)
            res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(exc_sub, y_res_sub)

            mse_b = float(np.mean(y_res_sub ** 2))
            mse_m = float(np.mean((y_sub - p_sub) ** 2))
            inc_r2 = 1.0 - (mse_m / mse_b) if mse_b > 0 else 0.0

            dir_acc = float(np.mean(np.sign(p_sub) == np.sign(y_sub))) * 100.0
            res_dir_acc = float(np.mean(np.sign(exc_sub) == np.sign(y_res_sub))) * 100.0

            temporal_rows.append({
                "config_code": c_code,
                "config_name": c_name,
                "config_category": c_cat,
                "period_code": b_code,
                "period_name": b_name,
                "n_sessions": int(np.sum(mask)),
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
                "mean_pred_bps": float(np.mean(p_sub)) * 10000.0,
                "pred_variance_bps2": float(np.var(p_sub * 10000.0, ddof=1)),
                "pct_pred_short": float(np.mean(p_sub < 0)) * 100.0,
            })

    df_temporal = pd.DataFrame(temporal_rows)
    temporal_csv_path = OUT_DIR / "step8_temporal_results.csv"
    df_temporal.to_csv(temporal_csv_path, index=False)
    print(f"Saved {temporal_csv_path} ({len(df_temporal)} rows).")

    # Step 8 Summary Table
    print("\n--- Step 6: Building Comprehensive step8_summary.csv ---")
    summary_rows = []
    y_raw_all = df_predictions["realized_intraday_return"].values
    y_res_all = df_predictions["residual_realized_return"].values

    # Reference G0 metrics
    p_g0 = df_predictions["pred_G0_ALL"].values
    exc_g0 = df_predictions["excess_G0_ALL"].values
    g0_raw_ic, _, g0_raw_s_ic, _ = safe_correlation(p_g0, y_raw_all)
    g0_res_ic, _, g0_res_s_ic, _ = safe_correlation(exc_g0, y_res_all)
    mse_b_g0 = float(np.mean(y_res_all ** 2))
    mse_m_g0 = float(np.mean((y_raw_all - p_g0) ** 2))
    g0_inc_r2 = (1.0 - (mse_m_g0 / mse_b_g0)) * 100.0

    always_short_gross_bps = float(np.mean(-y_raw_all)) * 10000.0

    for c_code, c_name, c_cat, _ in configs:
        p_c = df_predictions[f"pred_{c_code}"].values
        exc_c = df_predictions[f"excess_{c_code}"].values
        n_feats = len(config_feature_indices[c_code])

        raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(p_c, y_raw_all)
        res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(exc_c, y_res_all)

        mse_b = float(np.mean(y_res_all ** 2))
        mse_m = float(np.mean((y_raw_all - p_c) ** 2))
        inc_r2 = (1.0 - (mse_m / mse_b)) * 100.0 if mse_b > 0 else 0.0

        raw_mae = float(np.mean(np.abs(y_raw_all - p_c))) * 10000.0
        raw_rmse = math.sqrt(mse_m) * 10000.0
        res_mae = float(np.mean(np.abs(y_res_all - exc_c))) * 10000.0
        res_rmse = math.sqrt(float(np.mean((y_res_all - exc_c) ** 2))) * 10000.0

        dir_acc = float(np.mean(np.sign(p_c) == np.sign(y_raw_all))) * 100.0
        res_dir_acc = float(np.mean(np.sign(exc_c) == np.sign(y_res_all))) * 100.0

        delta_raw_ic = g0_raw_ic - raw_p_ic
        delta_raw_spearman_ic = g0_raw_s_ic - raw_s_ic
        delta_res_ic = g0_res_ic - res_p_ic
        delta_res_spearman_ic = g0_res_s_ic - res_s_ic
        delta_r2_pct = g0_inc_r2 - inc_r2

        t_sub = df_temporal[df_temporal["config_code"] == c_code]
        block_a_res_ic = float(t_sub[t_sub["period_code"] == "Block_A"]["residual_pearson_ic"].values[0])
        block_b_res_ic = float(t_sub[t_sub["period_code"] == "Block_B"]["residual_pearson_ic"].values[0])
        block_c_res_ic = float(t_sub[t_sub["period_code"] == "Block_C"]["residual_pearson_ic"].values[0])

        y2021_res_ic = float(t_sub[t_sub["period_code"] == "Year_2021"]["residual_pearson_ic"].values[0])
        y2021_inc_r2 = float(t_sub[t_sub["period_code"] == "Year_2021"]["incremental_r2_pct"].values[0])
        y2021_pred_var = float(t_sub[t_sub["period_code"] == "Year_2021"]["pred_variance_bps2"].values[0])

        y1719_res_ic = float(t_sub[t_sub["period_code"] == "Years_2017_2019"]["residual_pearson_ic"].values[0])
        y1719_inc_r2 = float(t_sub[t_sub["period_code"] == "Years_2017_2019"]["incremental_r2_pct"].values[0])

        pos = np.where(p_c > 0, 1.0, np.where(p_c < 0, -1.0, 0.0))
        pct_short = float(np.mean(pos < 0)) * 100.0
        pct_long = float(np.mean(pos > 0)) * 100.0
        r_gross = pos * y_raw_all
        model_gross_bps = float(np.mean(r_gross)) * 10000.0
        r_net_10 = pos * y_raw_all - (0.0010 * (pos != 0.0))
        model_net_10bps = float(np.mean(r_net_10)) * 10000.0

        diff_vs_short = r_gross - (-y_raw_all)
        hac_se, hac_t, hac_p = compute_newey_west_hac(diff_vs_short)

        summary_rows.append({
            "config_code": c_code,
            "config_name": c_name,
            "config_category": c_cat,
            "n_features": n_feats,
            "n_sessions": len(df_predictions),
            "raw_pearson_ic": raw_p_ic,
            "raw_pearson_pvalue": raw_p_pval,
            "raw_spearman_ic": raw_s_ic,
            "raw_spearman_pvalue": raw_s_pval,
            "residual_pearson_ic": res_p_ic,
            "residual_pearson_pvalue": res_p_pval,
            "residual_spearman_ic": res_s_ic,
            "residual_spearman_pvalue": res_s_pval,
            "incremental_r2_pct": inc_r2,
            "raw_directional_accuracy_pct": dir_acc,
            "residual_directional_accuracy_pct": res_dir_acc,
            "raw_mae_bps": raw_mae,
            "raw_rmse_bps": raw_rmse,
            "residual_mae_bps": res_mae,
            "residual_rmse_bps": res_rmse,
            "delta_raw_pearson_ic": delta_raw_ic,
            "delta_raw_spearman_ic": delta_raw_spearman_ic,
            "delta_residual_pearson_ic": delta_res_ic,
            "delta_residual_spearman_ic": delta_res_spearman_ic,
            "delta_incremental_r2_pct": delta_r2_pct,
            "block_a_res_ic": block_a_res_ic,
            "block_b_res_ic": block_b_res_ic,
            "block_c_res_ic": block_c_res_ic,
            "year_2021_res_ic": y2021_res_ic,
            "year_2021_incremental_r2_pct": y2021_inc_r2,
            "year_2021_pred_variance_bps2": y2021_pred_var,
            "years_2017_2019_res_ic": y1719_res_ic,
            "years_2017_2019_incremental_r2_pct": y1719_inc_r2,
            "pct_pred_short": pct_short,
            "pct_pred_long": pct_long,
            "always_short_gross_bps": always_short_gross_bps,
            "model_gross_bps": model_gross_bps,
            "model_net_10bps": model_net_10bps,
            "diff_vs_short_mean_bps": float(np.mean(diff_vs_short)) * 10000.0,
            "diff_vs_short_hac_se_bps": hac_se * 10000.0,
            "diff_vs_short_hac_t": hac_t,
            "diff_vs_short_hac_p": hac_p,
        })

    # FDR correction (Benjamini-Hochberg)
    df_summary = pd.DataFrame(summary_rows)
    p_vals = df_summary["residual_pearson_pvalue"].values
    n_tests = len(p_vals)
    sorted_idx = np.argsort(p_vals)
    sorted_p = p_vals[sorted_idx]
    fdr_p = np.zeros(n_tests)
    cum_min = 1.0
    for i in range(n_tests - 1, -1, -1):
        rank = i + 1
        adj = (sorted_p[i] * n_tests) / rank
        cum_min = min(cum_min, adj)
        fdr_p[sorted_idx[i]] = min(1.0, cum_min)
    df_summary["fdr_residual_pearson_pvalue"] = fdr_p

    summary_csv_path = OUT_DIR / "step8_summary.csv"
    df_summary.to_csv(summary_csv_path, index=False)
    print(f"Saved {summary_csv_path} ({len(df_summary)} rows).")

    # Feature Contribution / Attribution Table (Reference Model G0)
    print("\n--- Step 7: Feature Contribution / Attribution Analysis (G0) ---")
    feat_contrib_rows = []
    mean_gains = {}
    mean_weights = {}
    mean_covers = {}
    for fn in feat_names:
        gains = [fold_g.get(fn, 0.0) for fold_g in g0_feature_gains]
        weights = [fold_w.get(fn, 0.0) for fold_w in g0_feature_weights]
        covers = [fold_c.get(fn, 0.0) for fold_c in g0_feature_covers]
        mean_gains[fn] = float(np.mean(gains))
        mean_weights[fn] = float(np.mean(weights))
        mean_covers[fn] = float(np.mean(covers))

    tot_gain = sum(mean_gains.values())
    tot_weight = sum(mean_weights.values())

    for _, reg_row in df_reg.iterrows():
        fn = reg_row["feature_name"]
        g = mean_gains[fn]
        w = mean_weights[fn]
        c = mean_covers[fn]
        rel_gain_pct = (g / tot_gain) * 100.0 if tot_gain > 0 else 0.0
        rel_weight_pct = (w / tot_weight) * 100.0 if tot_weight > 0 else 0.0

        feat_contrib_rows.append({
            "feature_name": fn,
            "feature_family": reg_row["feature_family"],
            "feature_group": reg_row["feature_group"],
            "source_phase": reg_row["source_phase"],
            "Price_or_Context": reg_row["Price_or_Context"],
            "mean_gain": g,
            "relative_gain_pct": rel_gain_pct,
            "mean_weight": w,
            "relative_weight_pct": rel_weight_pct,
            "mean_cover": c,
        })

    df_feat_contrib = pd.DataFrame(feat_contrib_rows).sort_values("relative_gain_pct", ascending=False)
    contrib_csv_path = OUT_DIR / "step8_feature_contribution.csv"
    df_feat_contrib.to_csv(contrib_csv_path, index=False)
    print(f"Saved {contrib_csv_path} ({len(df_feat_contrib)} rows).")

    # Placebo / Permutation Test (1,000 permutations, seed 42)
    print("\n--- Step 8: Placebo / Permutation Test (1,000 Permutations, Seed 42) ---")
    placebo_configs = [
        "G0_ALL", "G1_PRICE", "G2_CONTEXT", "G3_SHORT_PRICE", "G4_MED_LONG_PRICE",
        "G5_VOLATILITY", "G6_DOMESTIC_CTX", "G7_GLOBAL_CTX", "G8_MACRO_CTX", "G_CALENDAR",
        "LOO_NO_SHORT_PRICE", "LOO_NO_MED_LONG_PRICE", "LOO_NO_VOLATILITY",
        "LOO_NO_DOMESTIC_CTX", "LOO_NO_GLOBAL_CTX", "LOO_NO_MACRO_CTX", "LOO_NO_CALENDAR"
    ]
    n_perm = 1000
    rng = np.random.default_rng(seed=42)
    perm_indices = [rng.permutation(len(df_predictions)) for _ in range(n_perm)]

    placebo_rows = []
    for c_code in placebo_configs:
        exc_c = df_predictions[f"excess_{c_code}"].values
        obs_ic, obs_pval, _, _ = safe_correlation(exc_c, y_res_all)

        perm_ics = []
        for p_idx in perm_indices:
            r_p, _, _, _ = safe_correlation(exc_c, y_res_all[p_idx])
            perm_ics.append(r_p)

        perm_arr = np.array(perm_ics, dtype=np.float64)
        mean_p_ic = float(np.mean(perm_arr))
        std_p_ic = float(np.std(perm_arr, ddof=1))
        emp_pct = float(stats.percentileofscore(perm_arr, obs_ic))
        emp_pval = float(np.mean(perm_arr >= obs_ic))

        placebo_rows.append({
            "config_code": c_code,
            "n_sessions": len(df_predictions),
            "n_permutations": n_perm,
            "seed": 42,
            "observed_residual_pearson_ic": obs_ic,
            "observed_residual_pearson_pvalue": obs_pval,
            "placebo_mean_ic": mean_p_ic,
            "placebo_std_ic": std_p_ic,
            "empirical_percentile": emp_pct,
            "empirical_pvalue": emp_pval,
        })
        print(f"  [{c_code:<20}] Obs IC={obs_ic:+.4f} | Placebo Mean={mean_p_ic:+.4f} (std={std_p_ic:.4f}) | Emp P-val={emp_pval:.4f}")

    df_placebo = pd.DataFrame(placebo_rows)
    placebo_csv_path = OUT_DIR / "step8_placebo_results.csv"
    df_placebo.to_csv(placebo_csv_path, index=False)
    print(f"Saved {placebo_csv_path} ({len(df_placebo)} rows).")

    # Economic Stress Test (Diagnostic Only)
    print("\n--- Step 9: Economic Diagnostic (0, 5, 10, 20 bps) ---")
    econ_rows = []
    cost_scenarios = [0.0, 5.0, 10.0, 20.0]

    for c_code, c_name, c_cat, _ in configs:
        p_c = df_predictions[f"pred_{c_code}"].values
        pos = np.where(p_c > 0, 1.0, np.where(p_c < 0, -1.0, 0.0))
        n_long = int(np.sum(pos > 0))
        n_short = int(np.sum(pos < 0))
        n_flat = int(np.sum(pos == 0))
        pct_short = (n_short / len(pos)) * 100.0

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
                "config_code": c_code,
                "config_name": c_name,
                "config_category": c_cat,
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
    econ_csv_path = OUT_DIR / "step8_economic_diagnostic.csv"
    df_econ.to_csv(econ_csv_path, index=False)
    print(f"Saved {econ_csv_path} ({len(df_econ)} rows).")

    # Step 8 Integrity Manifest
    print("\n--- Step 10: Generating Step 8 Integrity Manifest ---")
    manifest = {
        "step_name": "Phase 12 Step 8: Feature Information Stability & Ablation Research",
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
            "feature_set": "Snapshot B Model 1 (63 features)",
            "n_features": len(feat_names),
            "price_features": 45,
            "context_features": 18,
            "news_features": 0,
            "volume_features": 0,
            "flow_features": 0,
        },
        "configurations_evaluated": [
            {"code": c[0], "name": c[1], "category": c[2], "n_features": len(config_feature_indices[c[0]])}
            for c in configs
        ],
        "summary_metrics_g0": {
            "raw_pearson_ic": g0_raw_ic,
            "residual_pearson_ic": g0_res_ic,
            "incremental_r2_pct": g0_inc_r2,
        },
        "file_hashes": {},
    }

    # Hash all generated interim files
    for p in sorted(OUT_DIR.glob("step8_*.csv")):
        manifest["file_hashes"][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    reg_json_p = OUT_DIR / "step8_feature_group_registry.json"
    if reg_json_p.is_file():
        manifest["file_hashes"][reg_json_p.name] = hashlib.sha256(reg_json_p.read_bytes()).hexdigest()

    manifest_path = OUT_DIR / "step8_integrity_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Saved {manifest_path}.")

    print("\n" + "=" * 90)
    print("PHASE 12 STEP 8 EXPERIMENT EXECUTION COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
