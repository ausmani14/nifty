"""Phase 10: Market Regime Detection, Explainability & Error Analysis Runner.

Evaluates Model 1 (Price + Context, 63 features, 0 News) across pre-registered
market regimes, temporal stability blocks, error taxonomy categories, confidence
calibration bins, and native Lundberg TreeSHAP attributions.
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
from nifty_ai.evaluation.calibration import PlattScaler
from nifty_ai.evaluation.classification_metrics import evaluate_classification_metrics
from nifty_ai.evaluation.regression_metrics import evaluate_regression_metrics
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import (
    CONTEXT_FEATURE_NAMES,
    PRICE_FEATURE_NAMES,
    MultimodalDataset,
    load_multimodal_dataset,
)
from nifty_ai.models.xgboost_classifier import XGBoostDirectionClassifier
from nifty_ai.models.xgboost_regressor import XGBoostReturnRegressor

# ---------------------------------------------------------------------------
# 1. Protected Checksum Manifest
# ---------------------------------------------------------------------------
PROTECTED_HASHES = {
    "data/features/nifty50_features_clean.csv": "afa2e68f50f1ad0f4b1adbbec3df294d474d688dbf481cf53c76c4db0a78914b",
    "data/targets/nifty50_targets_snapshot_a.csv": "a13fed61f92c3fcccf9fe09ce59eb0df4d95ef8dce0aef970ff5ed1220ea055d",
    "data/targets/nifty50_targets_snapshot_b.csv": "54ac54fdeafd53ddea20b1d31cd89c1fbaebdbc88c0f24f8a1f73ce2867e01d2",
    "data/interim/context/snapshot_a_context_daily.csv": "26f41d5978b2f78fb9fad223d9efe9970820ab7f81510490ed6f1b39872178af",
    "data/interim/context/snapshot_b_context_daily.csv": "08a694f86f70c5246b8b6b4928283b676dd998912e481d88a718ba08970237be",
    "data/interim/news/features_news_snapshot_a.csv": "487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7",
    "data/interim/news/features_news_snapshot_b.csv": "f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606",
    "data/interim/news/phase9_step4_oof_results.csv": "62b88a1689c7ed57e1ddf79ca0064356eec5d2a16e00f7975998a155141f02d8",
    "data/interim/news/phase9_step4_holdout_results.csv": "4359edb7e585053c676e444d958a4265c584b9b13a58c89dd38067fc0bc41967",
    "data/interim/news/phase9_step4_experiment_results.csv": "7d0f39f7ce8a50b6f8b1591dc6ce9b3a4af8f75507531740a06147cb4aedffc3",
    "configs/phase9_step4_experiment_config.json": "8940206588dad34eb5a9d2fdb01ecbfeb629930374a733c15d077b2281ae7547",
}

# ---------------------------------------------------------------------------
# 2. Frozen Sealed Phase 6 Model Settings
# ---------------------------------------------------------------------------
SEALED_CLF_PARAMS: Dict[str, Any] = {
    "learning_rate": 0.10,
    "max_depth": 2,
    "min_child_weight": 10.0,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "random_state": 42,
}
SEALED_CLF_TREES: int = 12

SEALED_REG_PARAMS: Dict[str, Any] = {
    "learning_rate": 0.05,
    "max_depth": 2,
    "min_child_weight": 20.0,
    "subsample": 0.8,
    "colsample_bytree": 0.7,
    "reg_alpha": 0.5,
    "reg_lambda": 2.0,
    "random_state": 42,
}
SEALED_REG_TREES: int = 43

# Output Paths
OUT_DIR = PROJECT_ROOT / "data" / "interim" / "regime"
OUT_REGIME_PERF_CSV = OUT_DIR / "phase10_regime_performance.csv"
OUT_TEMP_STAB_CSV = OUT_DIR / "phase10_temporal_stability.csv"
OUT_ERROR_ANALYSIS_CSV = OUT_DIR / "phase10_error_analysis.csv"
OUT_FEAT_IMPORTANCE_CSV = OUT_DIR / "phase10_feature_importance.csv"
OUT_SHAP_SUMMARY_CSV = OUT_DIR / "phase10_shap_summary.csv"
OUT_CONF_CALIB_CSV = OUT_DIR / "phase10_confidence_calibration.csv"
OUT_OOF_DIAG_CSV = OUT_DIR / "phase10_oof_diagnostics.csv"
OUT_HOLDOUT_DIAG_CSV = OUT_DIR / "phase10_holdout_diagnostics.csv"
OUT_CONFIG_JSON = PROJECT_ROOT / "configs" / "phase10_regime_explainability_config.json"


def verify_protected_checksums() -> None:
    """Ensure all protected artifacts remain unmodified."""
    for rel_path, exp_hash in PROTECTED_HASHES.items():
        fp = PROJECT_ROOT / rel_path
        if not fp.is_file():
            raise FileNotFoundError(f"Missing protected file: {rel_path}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for {rel_path}!\nExpected: {exp_hash}\nActual:   {act_hash}")
    print("[CHECKSUMS] All 11 protected Phase 4-9 artifacts verified.")


def benjamini_hochberg_correction(p_values: List[float], alpha: float = 0.05) -> Tuple[List[float], List[bool]]:
    """Apply Benjamini-Hochberg False Discovery Rate (FDR) multiple testing correction."""
    m = len(p_values)
    if m == 0:
        return [], []
    p_arr = np.array(p_values, dtype=np.float64)
    sorted_idx = np.argsort(p_arr)
    sorted_p = p_arr[sorted_idx]

    # Adjusted q-values: q_i = min_{k >= i} (p_k * m / k)
    q_values = np.zeros(m, dtype=np.float64)
    running_min = 1.0
    for i in range(m - 1, -1, -1):
        rank = i + 1
        val = (sorted_p[i] * m) / rank
        running_min = min(running_min, val)
        q_values[i] = min(1.0, max(0.0, running_min))

    # Re-order to original sequence
    orig_q = np.zeros(m, dtype=np.float64)
    orig_q[sorted_idx] = q_values

    # Determine significance
    sig_mask = orig_q <= alpha
    return orig_q.tolist(), sig_mask.tolist()


def calculate_frozen_thresholds(dev_df: pd.DataFrame) -> Dict[str, Any]:
    """Calculate and freeze all regime thresholds strictly from the Development partition."""
    vol_q25 = float(np.percentile(dev_df["volatility_ann_20d"], 25))
    vol_q75 = float(np.percentile(dev_df["volatility_ann_20d"], 75))
    vol_q95 = float(np.percentile(dev_df["volatility_ann_20d"], 95))

    trend_q33 = float(np.percentile(dev_df["trend_slope_20d"], 33.3333))
    trend_q67 = float(np.percentile(dev_df["trend_slope_20d"], 66.6667))

    mom_q33 = float(np.percentile(dev_df["ret_20d"], 33.3333))
    mom_q67 = float(np.percentile(dev_df["ret_20d"], 66.6667))

    india_vix_q75 = float(np.percentile(dev_df["ctx_level_india_vix"], 75))
    us_vix_q75 = float(np.percentile(dev_df["ctx_level_us_vix"], 75))
    sp500_ret_q20 = float(np.percentile(dev_df["ctx_ret_1d_sp500"], 20))
    usdinr_diff_q75 = float(np.percentile(dev_df["ctx_diff_1d_usd_inr"], 75))

    return {
        "volatility_ann_20d": {"q25": vol_q25, "q75": vol_q75, "q95": vol_q95},
        "trend_slope_20d": {"q33": trend_q33, "q67": trend_q67},
        "ret_20d": {"q33": mom_q33, "q67": mom_q67},
        "stress": {
            "india_vix_q75": india_vix_q75,
            "us_vix_q75": us_vix_q75,
            "sp500_ret_q20": sp500_ret_q20,
            "usdinr_diff_q75": usdinr_diff_q75,
        },
    }


def assign_market_regimes(df: pd.DataFrame, thresholds: Dict[str, Any]) -> pd.DataFrame:
    """Assign 4 pre-registered regime labels to each session using frozen thresholds."""
    res = df.copy()
    vt = thresholds["volatility_ann_20d"]
    tt = thresholds["trend_slope_20d"]
    mt = thresholds["ret_20d"]
    st = thresholds["stress"]

    # 1. Volatility Regime
    def vol_label(v):
        if v <= vt["q25"]:
            return "LOW"
        elif v <= vt["q75"]:
            return "NORMAL"
        elif v <= vt["q95"]:
            return "HIGH"
        else:
            return "EXTREME"

    res["regime_volatility"] = res["volatility_ann_20d"].apply(vol_label)

    # 2. Trend Regime
    def trend_label(t):
        if t <= tt["q33"]:
            return "BEARISH"
        elif t <= tt["q67"]:
            return "NEUTRAL"
        else:
            return "BULLISH"

    res["regime_trend"] = res["trend_slope_20d"].apply(trend_label)

    # 3. Momentum Regime
    def mom_label(m):
        if m <= mt["q33"]:
            return "NEGATIVE"
        elif m <= mt["q67"]:
            return "NEUTRAL"
        else:
            return "POSITIVE"

    res["regime_momentum"] = res["ret_20d"].apply(mom_label)

    # 4. Market Stress Regime
    def stress_label(row):
        high_vol = (row["ctx_level_india_vix"] > st["india_vix_q75"]) or (row["ctx_level_us_vix"] > st["us_vix_q75"])
        macro_distress = (row["ctx_ret_1d_sp500"] < st["sp500_ret_q20"]) or (row["ctx_diff_1d_usd_inr"] > st["usdinr_diff_q75"])
        return "STRESSED" if (high_vol and macro_distress) else "CALM"

    res["regime_stress"] = res.apply(stress_label, axis=1)
    return res


def assign_error_taxonomy(
    y_true_class: np.ndarray,
    pred_class: np.ndarray,
    cal_probs: np.ndarray,
) -> Tuple[List[str], List[bool], List[bool]]:
    """Assign classification error categories, low-confidence errors, and high-confidence errors."""
    categories: List[str] = []
    is_low_conf: List[bool] = []
    is_high_conf: List[bool] = []

    for yt, yp, probs in zip(y_true_class, pred_class, cal_probs):
        max_p = float(np.max(probs))
        is_err = (yt != yp)
        is_low = is_err and (max_p < 0.50)
        is_high = is_err and (max_p >= 0.50)
        is_low_conf.append(is_low)
        is_high_conf.append(is_high)

        if yt == yp:
            if yt == 0:
                cat = "CORRECT_DOWN"
            elif yt == 1:
                cat = "CORRECT_SIDEWAYS"
            else:
                cat = "CORRECT_UP"
        else:
            if yp == 2 and yt == 0:
                cat = "PRED_UP_TRUE_DOWN"
            elif yp == 0 and yt == 2:
                cat = "PRED_DOWN_TRUE_UP"
            elif yp == 1 and yt in [0, 2]:
                cat = "PRED_SIDEWAYS_TRUE_DIRECTIONAL"
            elif yp in [0, 2] and yt == 1:
                cat = "PRED_DIRECTIONAL_TRUE_SIDEWAYS"
            else:
                cat = "OTHER_MISCLASSIFICATION"
        categories.append(cat)

    return categories, is_low_conf, is_high_conf


def run_snapshot_phase10_pipeline(
    ds: MultimodalDataset,
    folds: list,
    dev_idx: np.ndarray,
    holdout_idx: np.ndarray,
    thresholds: Dict[str, Any],
    snapshot_label: str,
) -> Dict[str, Any]:
    """Execute complete Phase 10 diagnostics for one snapshot."""
    print(f"\n=======================================================")
    print(f"  EXECUTING PHASE 10 DIAGNOSTICS FOR {snapshot_label.upper()}")
    print(f"=======================================================")

    total_val_indices = np.concatenate([f.val_indices for f in folds])
    y_true_oof_c = ds.y_class[total_val_indices]
    y_true_oof_r = ds.y_reg[total_val_indices]
    oof_dates = [ds.dates[i] for i in total_val_indices]

    y_true_hold_c = ds.y_class[holdout_idx]
    y_true_hold_r = ds.y_reg[holdout_idx]
    hold_dates = [ds.dates[i] for i in holdout_idx]

    # Model 1 features
    X_m1, feat_names = ds.get_features("Model 1")
    n_feats = len(feat_names)
    assert n_feats == 63, f"Expected 63 Model 1 features, found {n_feats}"

    # 1. Walk-Forward Fold Training & Prediction
    print(f"[{snapshot_label}] Running 8-fold OOF cross-validation...")
    oof_raw_probs_list = []
    oof_reg_preds_list = []

    for f_idx, fold in enumerate(folds):
        X_tr, y_tr_c, y_tr_r = X_m1[fold.train_indices], ds.y_class[fold.train_indices], ds.y_reg[fold.train_indices]
        X_va, y_va_c, y_va_r = X_m1[fold.val_indices], ds.y_class[fold.val_indices], ds.y_reg[fold.val_indices]

        clf = XGBoostDirectionClassifier(
            learning_rate=SEALED_CLF_PARAMS["learning_rate"],
            max_depth=SEALED_CLF_PARAMS["max_depth"],
            min_child_weight=SEALED_CLF_PARAMS["min_child_weight"],
            n_estimators=SEALED_CLF_TREES,
            subsample=SEALED_CLF_PARAMS["subsample"],
            colsample_bytree=SEALED_CLF_PARAMS["colsample_bytree"],
            reg_alpha=SEALED_CLF_PARAMS["reg_alpha"],
            reg_lambda=SEALED_CLF_PARAMS["reg_lambda"],
            random_state=SEALED_CLF_PARAMS["random_state"] + f_idx,
        )
        clf.fit(X_tr, y_tr_c, verbose=False)
        oof_raw_probs_list.append(clf.predict_proba(X_va))

        reg = XGBoostReturnRegressor(
            learning_rate=SEALED_REG_PARAMS["learning_rate"],
            max_depth=SEALED_REG_PARAMS["max_depth"],
            min_child_weight=SEALED_REG_PARAMS["min_child_weight"],
            n_estimators=SEALED_REG_TREES,
            subsample=SEALED_REG_PARAMS["subsample"],
            colsample_bytree=SEALED_REG_PARAMS["colsample_bytree"],
            reg_alpha=SEALED_REG_PARAMS["reg_alpha"],
            reg_lambda=SEALED_REG_PARAMS["reg_lambda"],
            random_state=SEALED_REG_PARAMS["random_state"] + f_idx,
        )
        reg.fit(X_tr, y_tr_r, verbose=False)
        oof_reg_preds_list.append(reg.predict(X_va))

    oof_raw_probs = np.concatenate(oof_raw_probs_list, axis=0)
    oof_reg_preds = np.concatenate(oof_reg_preds_list, axis=0)

    # 2. Fit Platt Calibrator strictly on OOF
    scaler = PlattScaler(random_seed=42)
    scaler.fit(oof_raw_probs, y_true_oof_c)
    oof_cal_probs = scaler.transform(oof_raw_probs)
    oof_pred_class = np.argmax(oof_cal_probs, axis=1)

    # 3. Production Model Refit on Dev (2008-2021) for Native TreeSHAP & Holdout
    print(f"[{snapshot_label}] Refitting production models on Development partition...")
    X_dev = X_m1[dev_idx]
    y_dev_c = ds.y_class[dev_idx]
    y_dev_r = ds.y_reg[dev_idx]

    prod_clf = XGBoostDirectionClassifier(
        learning_rate=SEALED_CLF_PARAMS["learning_rate"],
        max_depth=SEALED_CLF_PARAMS["max_depth"],
        min_child_weight=SEALED_CLF_PARAMS["min_child_weight"],
        n_estimators=SEALED_CLF_TREES,
        subsample=SEALED_CLF_PARAMS["subsample"],
        colsample_bytree=SEALED_CLF_PARAMS["colsample_bytree"],
        reg_alpha=SEALED_CLF_PARAMS["reg_alpha"],
        reg_lambda=SEALED_CLF_PARAMS["reg_lambda"],
        random_state=SEALED_CLF_PARAMS["random_state"],
    )
    prod_clf.fit(X_dev, y_dev_c, verbose=False)

    prod_reg = XGBoostReturnRegressor(
        learning_rate=SEALED_REG_PARAMS["learning_rate"],
        max_depth=SEALED_REG_PARAMS["max_depth"],
        min_child_weight=SEALED_REG_PARAMS["min_child_weight"],
        n_estimators=SEALED_REG_TREES,
        subsample=SEALED_REG_PARAMS["subsample"],
        colsample_bytree=SEALED_REG_PARAMS["colsample_bytree"],
        reg_alpha=SEALED_REG_PARAMS["reg_alpha"],
        reg_lambda=SEALED_REG_PARAMS["reg_lambda"],
        random_state=SEALED_REG_PARAMS["random_state"],
    )
    prod_reg.fit(X_dev, y_dev_r, verbose=False)

    # 4. Native TreeSHAP on OOF observations
    print(f"[{snapshot_label}] Computing native Lundberg TreeSHAP attributions...")
    booster_clf = prod_clf._clf.get_booster()
    booster_reg = prod_reg._reg.get_booster()
    booster_clf.feature_names = list(feat_names)
    booster_reg.feature_names = list(feat_names)

    dmat_oof = xgb.DMatrix(X_m1[total_val_indices], feature_names=list(feat_names))
    # Shape: (1960, 3, 64) -> [sessions, classes, features + bias]
    shap_oof_clf = booster_clf.predict(dmat_oof, pred_contribs=True)
    # Shape: (1960, 64)
    shap_oof_reg = booster_reg.predict(dmat_oof, pred_contribs=True)

    # 5. Single Pass on Terminal Holdout (Confirmatory)
    print(f"[{snapshot_label}] Running single confirmatory holdout pass...")
    X_hold = X_m1[holdout_idx]
    hold_raw_probs = prod_clf.predict_proba(X_hold)
    hold_cal_probs = scaler.transform(hold_raw_probs)
    hold_pred_class = np.argmax(hold_cal_probs, axis=1)
    hold_reg_preds = prod_reg.predict(X_hold)

    dmat_hold = xgb.DMatrix(X_hold, feature_names=list(feat_names))
    shap_hold_clf = booster_clf.predict(dmat_hold, pred_contribs=True)
    shap_hold_reg = booster_reg.predict(dmat_hold, pred_contribs=True)

    # Assign market regimes
    df_oof_feats = assign_market_regimes(ds.features_df.iloc[total_val_indices].copy(), thresholds)
    df_hold_feats = assign_market_regimes(ds.features_df.iloc[holdout_idx].copy(), thresholds)

    # Assign error categories
    oof_err_cats, oof_low_conf, oof_high_conf = assign_error_taxonomy(y_true_oof_c, oof_pred_class, oof_cal_probs)
    hold_err_cats, hold_low_conf, hold_high_conf = assign_error_taxonomy(y_true_hold_c, hold_pred_class, hold_cal_probs)

    # Assemble diagnostics DataFrames
    oof_diag_df = pd.DataFrame({
        "snapshot": snapshot_label,
        "partition": "OOF",
        "trading_date": [d.isoformat() for d in oof_dates],
        "y_true_class": y_true_oof_c,
        "y_true_reg": y_true_oof_r,
        "pred_class": oof_pred_class,
        "pred_reg": oof_reg_preds,
        "cal_prob_down": oof_cal_probs[:, 0],
        "cal_prob_sideways": oof_cal_probs[:, 1],
        "cal_prob_up": oof_cal_probs[:, 2],
        "confidence": np.max(oof_cal_probs, axis=1),
        "error_category": oof_err_cats,
        "is_low_conf_error": oof_low_conf,
        "is_high_conf_error": oof_high_conf,
        "regime_volatility": df_oof_feats["regime_volatility"].values,
        "regime_trend": df_oof_feats["regime_trend"].values,
        "regime_momentum": df_oof_feats["regime_momentum"].values,
        "regime_stress": df_oof_feats["regime_stress"].values,
    })

    hold_diag_df = pd.DataFrame({
        "snapshot": snapshot_label,
        "partition": "Holdout",
        "trading_date": [d.isoformat() for d in hold_dates],
        "y_true_class": y_true_hold_c,
        "y_true_reg": y_true_hold_r,
        "pred_class": hold_pred_class,
        "pred_reg": hold_reg_preds,
        "cal_prob_down": hold_cal_probs[:, 0],
        "cal_prob_sideways": hold_cal_probs[:, 1],
        "cal_prob_up": hold_cal_probs[:, 2],
        "confidence": np.max(hold_cal_probs, axis=1),
        "error_category": hold_err_cats,
        "is_low_conf_error": hold_low_conf,
        "is_high_conf_error": hold_high_conf,
        "regime_volatility": df_hold_feats["regime_volatility"].values,
        "regime_trend": df_hold_feats["regime_trend"].values,
        "regime_momentum": df_hold_feats["regime_momentum"].values,
        "regime_stress": df_hold_feats["regime_stress"].values,
    })

    return {
        "snapshot_label": snapshot_label,
        "oof_diag": oof_diag_df,
        "hold_diag": hold_diag_df,
        "feat_names": feat_names,
        "prod_clf": prod_clf,
        "prod_reg": prod_reg,
        "shap_oof_clf": shap_oof_clf,
        "shap_oof_reg": shap_oof_reg,
        "shap_hold_clf": shap_hold_clf,
        "shap_hold_reg": shap_hold_reg,
        "total_val_indices": total_val_indices,
        "holdout_idx": holdout_idx,
    }


def compute_regime_performance_table(
    data_map: Dict[str, Any],
) -> pd.DataFrame:
    """Compute performance metrics conditioned on market regimes with Benjamini-Hochberg FDR correction."""
    perf_rows: List[Dict[str, Any]] = []

    regime_dims = [
        ("Volatility", "regime_volatility", ["LOW", "NORMAL", "HIGH", "EXTREME"]),
        ("Trend", "regime_trend", ["BEARISH", "NEUTRAL", "BULLISH"]),
        ("Momentum", "regime_momentum", ["NEGATIVE", "NEUTRAL", "POSITIVE"]),
        ("Stress", "regime_stress", ["CALM", "STRESSED"]),
    ]

    for snap_key in ["Snapshot A", "Snapshot B"]:
        d_obj = data_map[snap_key]
        for part in ["OOF", "Holdout"]:
            diag = d_obj["oof_diag"] if part == "OOF" else d_obj["hold_diag"]
            n_total = len(diag)

            # Overall partition baseline metrics
            base_clf_m = evaluate_classification_metrics(diag["y_true_class"].values, diag[["cal_prob_down", "cal_prob_sideways", "cal_prob_up"]].values)
            base_reg_m = evaluate_regression_metrics(diag["y_true_reg"].values, diag["pred_reg"].values)

            # Baseline overall row
            perf_rows.append({
                "snapshot": snap_key,
                "partition": part,
                "regime_dimension": "Overall",
                "regime_category": "ALL",
                "n_sessions": n_total,
                "pct_of_total": 1.0,
                "governance_status": "FULL_SAMPLE",
                "log_loss": base_clf_m.log_loss,
                "brier_score": base_clf_m.brier_score,
                "accuracy": base_clf_m.accuracy,
                "macro_f1": base_clf_m.macro_f1,
                "ece": base_clf_m.expected_calibration_error,
                "precision_down": base_clf_m.per_class["DOWN"]["precision"],
                "recall_down": base_clf_m.per_class["DOWN"]["recall"],
                "precision_sideways": base_clf_m.per_class["SIDEWAYS"]["precision"],
                "recall_sideways": base_clf_m.per_class["SIDEWAYS"]["recall"],
                "precision_up": base_clf_m.per_class["UP"]["precision"],
                "recall_up": base_clf_m.per_class["UP"]["recall"],
                "mae": base_reg_m.mae,
                "rmse": base_reg_m.rmse,
                "pearson_ic": base_reg_m.pearson_ic,
                "pearson_ic_pvalue": base_reg_m.pearson_ic_pvalue,
                "spearman_ic": base_reg_m.spearman_ic,
                "directional_accuracy": base_reg_m.directional_accuracy,
                "delta_logloss_vs_overall": 0.0,
                "delta_accuracy_vs_overall": 0.0,
                "delta_rmse_vs_overall": 0.0,
                "delta_ic_vs_overall": 0.0,
                "unadjusted_pvalue": 1.0,
            })

            # Sub-regimes
            for r_dim_name, col_name, categories in regime_dims:
                for cat in categories:
                    sub = diag[diag[col_name] == cat]
                    n_sub = len(sub)
                    if n_sub == 0:
                        continue

                    # Governance tag
                    if n_sub < 50:
                        gov_tag = "DESCRIPTIVE_ONLY"
                    elif n_sub < 100:
                        gov_tag = "QUANTITATIVE_COMPARISON"
                    else:
                        gov_tag = "STRONG_STATISTICAL"

                    clf_m = evaluate_classification_metrics(sub["y_true_class"].values, sub[["cal_prob_down", "cal_prob_sideways", "cal_prob_up"]].values)
                    reg_m = evaluate_regression_metrics(sub["y_true_reg"].values, sub["pred_reg"].values)

                    # Two-sample difference test against rest of partition
                    rest = diag[diag[col_name] != cat]
                    # T-test on squared error for regression
                    err_sub = (sub["y_true_reg"].values - sub["pred_reg"].values) ** 2
                    err_rest = (rest["y_true_reg"].values - rest["pred_reg"].values) ** 2
                    _, p_diff = stats.ttest_ind(err_sub, err_rest, equal_var=False)

                    perf_rows.append({
                        "snapshot": snap_key,
                        "partition": part,
                        "regime_dimension": r_dim_name,
                        "regime_category": cat,
                        "n_sessions": n_sub,
                        "pct_of_total": n_sub / n_total,
                        "governance_status": gov_tag,
                        "log_loss": clf_m.log_loss,
                        "brier_score": clf_m.brier_score,
                        "accuracy": clf_m.accuracy,
                        "macro_f1": clf_m.macro_f1,
                        "ece": clf_m.expected_calibration_error,
                        "precision_down": clf_m.per_class["DOWN"]["precision"],
                        "recall_down": clf_m.per_class["DOWN"]["recall"],
                        "precision_sideways": clf_m.per_class["SIDEWAYS"]["precision"],
                        "recall_sideways": clf_m.per_class["SIDEWAYS"]["recall"],
                        "precision_up": clf_m.per_class["UP"]["precision"],
                        "recall_up": clf_m.per_class["UP"]["recall"],
                        "mae": reg_m.mae,
                        "rmse": reg_m.rmse,
                        "pearson_ic": reg_m.pearson_ic,
                        "pearson_ic_pvalue": reg_m.pearson_ic_pvalue,
                        "spearman_ic": reg_m.spearman_ic,
                        "directional_accuracy": reg_m.directional_accuracy,
                        "delta_logloss_vs_overall": clf_m.log_loss - base_clf_m.log_loss,
                        "delta_accuracy_vs_overall": clf_m.accuracy - base_clf_m.accuracy,
                        "delta_rmse_vs_overall": reg_m.rmse - base_reg_m.rmse,
                        "delta_ic_vs_overall": reg_m.pearson_ic - base_reg_m.pearson_ic,
                        "unadjusted_pvalue": float(p_diff) if np.isfinite(p_diff) else 1.0,
                    })

    perf_df = pd.DataFrame(perf_rows)

    # Apply Benjamini-Hochberg FDR correction across exploratory sub-regimes
    exploratory_mask = perf_df["regime_dimension"] != "Overall"
    p_vals = perf_df.loc[exploratory_mask, "unadjusted_pvalue"].tolist()
    q_vals, sig_mask = benjamini_hochberg_correction(p_vals, alpha=0.05)

    perf_df["fdr_adjusted_qvalue"] = 1.0
    perf_df["fdr_significant_05"] = False
    perf_df.loc[exploratory_mask, "fdr_adjusted_qvalue"] = q_vals
    perf_df.loc[exploratory_mask, "fdr_significant_05"] = sig_mask

    return perf_df


def compute_temporal_stability_table(data_map: Dict[str, Any]) -> pd.DataFrame:
    """Evaluate performance across fixed chronological periods."""
    rows: List[Dict[str, Any]] = []

    blocks = [
        ("OOF", "2014-2016", "2014-01-01", "2016-12-31"),
        ("OOF", "2017-2019", "2017-01-01", "2019-12-31"),
        ("OOF", "2020-2021", "2020-01-01", "2021-12-31"),
        ("Holdout", "2022-2023", "2022-01-01", "2023-12-31"),
        ("Holdout", "2024-2026", "2024-01-01", "2026-09-04"),
    ]

    for snap_key in ["Snapshot A", "Snapshot B"]:
        d_obj = data_map[snap_key]
        for part, block_name, start_d, end_d in blocks:
            diag = d_obj["oof_diag"] if part == "OOF" else d_obj["hold_diag"]
            sub = diag[(diag["trading_date"] >= start_d) & (diag["trading_date"] <= end_d)]
            n_sub = len(sub)
            if n_sub == 0:
                continue

            clf_m = evaluate_classification_metrics(sub["y_true_class"].values, sub[["cal_prob_down", "cal_prob_sideways", "cal_prob_up"]].values)
            reg_m = evaluate_regression_metrics(sub["y_true_reg"].values, sub["pred_reg"].values)

            rows.append({
                "snapshot": snap_key,
                "partition": part,
                "period_block": block_name,
                "start_date": start_d,
                "end_date": end_d,
                "n_sessions": n_sub,
                "log_loss": clf_m.log_loss,
                "brier_score": clf_m.brier_score,
                "accuracy": clf_m.accuracy,
                "macro_f1": clf_m.macro_f1,
                "ece": clf_m.expected_calibration_error,
                "mae": reg_m.mae,
                "rmse": reg_m.rmse,
                "pearson_ic": reg_m.pearson_ic,
                "pearson_ic_pvalue": reg_m.pearson_ic_pvalue,
                "directional_accuracy": reg_m.directional_accuracy,
            })

    return pd.DataFrame(rows)


def compute_error_analysis_table(data_map: Dict[str, Any]) -> pd.DataFrame:
    """Analyze classification error modes and regression residuals."""
    rows: List[Dict[str, Any]] = []

    for snap_key in ["Snapshot A", "Snapshot B"]:
        d_obj = data_map[snap_key]
        for part in ["OOF", "Holdout"]:
            diag = d_obj["oof_diag"] if part == "OOF" else d_obj["hold_diag"]
            n_total = len(diag)

            for cat, grp in diag.groupby("error_category"):
                n_cat = len(grp)
                rows.append({
                    "snapshot": snap_key,
                    "partition": part,
                    "error_category": cat,
                    "count": n_cat,
                    "pct_of_total": n_cat / n_total,
                    "mean_confidence": float(grp["confidence"].mean()),
                    "mean_realized_return": float(grp["y_true_reg"].mean()),
                    "mean_predicted_return": float(grp["pred_reg"].mean()),
                    "pct_in_high_extreme_vol": float((grp["regime_volatility"].isin(["HIGH", "EXTREME"])).mean()),
                    "pct_in_stressed_regime": float((grp["regime_stress"] == "STRESSED").mean()),
                })

            # Also report Low-confidence and High-confidence error summary rows
            low_err = diag[diag["is_low_conf_error"]]
            high_err = diag[diag["is_high_conf_error"]]
            rows.append({
                "snapshot": snap_key,
                "partition": part,
                "error_category": "ALL_LOW_CONFIDENCE_ERRORS (<0.50)",
                "count": len(low_err),
                "pct_of_total": len(low_err) / n_total,
                "mean_confidence": float(low_err["confidence"].mean()) if len(low_err) > 0 else 0.0,
                "mean_realized_return": float(low_err["y_true_reg"].mean()) if len(low_err) > 0 else 0.0,
                "mean_predicted_return": float(low_err["pred_reg"].mean()) if len(low_err) > 0 else 0.0,
                "pct_in_high_extreme_vol": float((low_err["regime_volatility"].isin(["HIGH", "EXTREME"])).mean()) if len(low_err) > 0 else 0.0,
                "pct_in_stressed_regime": float((low_err["regime_stress"] == "STRESSED").mean()) if len(low_err) > 0 else 0.0,
            })
            rows.append({
                "snapshot": snap_key,
                "partition": part,
                "error_category": "ALL_HIGH_CONFIDENCE_ERRORS (>=0.50)",
                "count": len(high_err),
                "pct_of_total": len(high_err) / n_total,
                "mean_confidence": float(high_err["confidence"].mean()) if len(high_err) > 0 else 0.0,
                "mean_realized_return": float(high_err["y_true_reg"].mean()) if len(high_err) > 0 else 0.0,
                "mean_predicted_return": float(high_err["pred_reg"].mean()) if len(high_err) > 0 else 0.0,
                "pct_in_high_extreme_vol": float((high_err["regime_volatility"].isin(["HIGH", "EXTREME"])).mean()) if len(high_err) > 0 else 0.0,
                "pct_in_stressed_regime": float((high_err["regime_stress"] == "STRESSED").mean()) if len(high_err) > 0 else 0.0,
            })

    return pd.DataFrame(rows)


def compute_confidence_calibration_table(data_map: Dict[str, Any]) -> pd.DataFrame:
    """Analyze empirical accuracy vs predicted confidence bins."""
    bins = [
        ("0.33-0.40", 0.33, 0.40),
        ("0.40-0.50", 0.40, 0.50),
        ("0.50-0.60", 0.50, 0.60),
        ("0.60-0.70", 0.60, 0.70),
        ("0.70-0.80", 0.70, 0.80),
        ("0.80+", 0.80, 1.01),
    ]

    rows: List[Dict[str, Any]] = []

    for snap_key in ["Snapshot A", "Snapshot B"]:
        d_obj = data_map[snap_key]
        for part in ["OOF", "Holdout"]:
            diag = d_obj["oof_diag"] if part == "OOF" else d_obj["hold_diag"]
            n_total = len(diag)

            for b_label, low, high in bins:
                sub = diag[(diag["confidence"] >= low) & (diag["confidence"] < high)]
                n_b = len(sub)
                if n_b == 0:
                    rows.append({
                        "snapshot": snap_key,
                        "partition": part,
                        "confidence_bin": b_label,
                        "n_sessions": 0,
                        "pct_of_total": 0.0,
                        "mean_confidence": 0.0,
                        "empirical_accuracy": 0.0,
                        "calibration_gap": 0.0,
                        "log_loss": 0.0,
                    })
                    continue

                acc = float((sub["y_true_class"] == sub["pred_class"]).mean())
                mean_conf = float(sub["confidence"].mean())
                clf_m = evaluate_classification_metrics(sub["y_true_class"].values, sub[["cal_prob_down", "cal_prob_sideways", "cal_prob_up"]].values)

                rows.append({
                    "snapshot": snap_key,
                    "partition": part,
                    "confidence_bin": b_label,
                    "n_sessions": n_b,
                    "pct_of_total": n_b / n_total,
                    "mean_confidence": mean_conf,
                    "empirical_accuracy": acc,
                    "calibration_gap": abs(mean_conf - acc),
                    "log_loss": clf_m.log_loss,
                })

    return pd.DataFrame(rows)


def compute_feature_importance_and_shap_tables(
    data_map: Dict[str, Any],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Extract native XGBoost gain and Lundberg TreeSHAP attributions."""
    feat_rows: List[Dict[str, Any]] = []
    shap_rows: List[Dict[str, Any]] = []

    for snap_key in ["Snapshot A", "Snapshot B"]:
        d_obj = data_map[snap_key]
        feat_names = d_obj["feat_names"]

        # Booster gain scores
        booster_clf = d_obj["prod_clf"]._clf.get_booster()
        booster_reg = d_obj["prod_reg"]._reg.get_booster()
        gain_clf = booster_clf.get_score(importance_type="gain")
        gain_reg = booster_reg.get_score(importance_type="gain")
        weight_clf = booster_clf.get_score(importance_type="weight")
        weight_reg = booster_reg.get_score(importance_type="weight")

        # TreeSHAP matrices
        # shap_oof_clf shape: (1960, 3, 64) -> class 0, class 1, class 2
        shap_clf_oof = d_obj["shap_oof_clf"][:, :, :-1]  # Exclude bias
        shap_reg_oof = d_obj["shap_oof_reg"][:, :-1]     # Exclude bias

        mean_abs_shap_clf_oof = np.mean(np.abs(shap_clf_oof), axis=(0, 1))
        mean_abs_shap_reg_oof = np.mean(np.abs(shap_reg_oof), axis=0)

        # Class-specific mean absolute SHAP
        mean_abs_shap_down = np.mean(np.abs(shap_clf_oof[:, 0, :]), axis=0)
        mean_abs_shap_side = np.mean(np.abs(shap_clf_oof[:, 1, :]), axis=0)
        mean_abs_shap_up   = np.mean(np.abs(shap_clf_oof[:, 2, :]), axis=0)

        for i, fname in enumerate(feat_names):
            g_c = float(gain_clf.get(fname, 0.0))
            g_r = float(gain_reg.get(fname, 0.0))
            w_c = int(weight_clf.get(fname, 0))
            w_r = int(weight_reg.get(fname, 0))
            s_c = float(mean_abs_shap_clf_oof[i])
            s_r = float(mean_abs_shap_reg_oof[i])

            feat_rows.append({
                "snapshot": snap_key,
                "feature_name": fname,
                "feature_category": "Price" if fname in PRICE_FEATURE_NAMES else "Context",
                "classifier_gain": g_c,
                "classifier_weight": w_c,
                "regressor_gain": g_r,
                "regressor_weight": w_r,
                "oof_mean_abs_shap_classifier": s_c,
                "oof_mean_abs_shap_regressor": s_r,
            })

            shap_rows.append({
                "snapshot": snap_key,
                "feature_name": fname,
                "feature_category": "Price" if fname in PRICE_FEATURE_NAMES else "Context",
                "shap_attribution_class_down": float(mean_abs_shap_down[i]),
                "shap_attribution_class_sideways": float(mean_abs_shap_side[i]),
                "shap_attribution_class_up": float(mean_abs_shap_up[i]),
                "shap_attribution_regressor": s_r,
            })

    return pd.DataFrame(feat_rows), pd.DataFrame(shap_rows)


def main() -> None:
    print("=" * 90)
    print("PHASE 10: REGIME DETECTION, EXPLAINABILITY & ERROR ANALYSIS")
    print("=" * 90)

    # 1. Checksums
    print("\n--- Step 1: Checksum Verification ---")
    verify_protected_checksums()

    # 2. Splitter & Datasets
    print("\n--- Step 2: Loading Datasets ---")
    ds_a = load_multimodal_dataset(SnapshotType.SNAPSHOT_1540)
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)

    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    folds_a = splitter.split_development(ds_a.dates)
    dev_idx_a, holdout_idx_a = splitter.get_development_and_holdout_indices(ds_a.dates)

    folds_b = splitter.split_development(ds_b.dates)
    dev_idx_b, holdout_idx_b = splitter.get_development_and_holdout_indices(ds_b.dates)

    # 3. Calculate and Freeze Development-Only Thresholds
    print("\n--- Step 3: Calculating and Freezing Development Thresholds ---")
    dev_df_a = ds_a.features_df.iloc[dev_idx_a].copy()
    thresholds = calculate_frozen_thresholds(dev_df_a)
    print("Frozen Development Thresholds:")
    print(json.dumps(thresholds, indent=2))

    # 4. Run Pipelines
    data_map = {}
    data_map["Snapshot A"] = run_snapshot_phase10_pipeline(
        ds=ds_a,
        folds=folds_a,
        dev_idx=dev_idx_a,
        holdout_idx=holdout_idx_a,
        thresholds=thresholds,
        snapshot_label="Snapshot A",
    )
    data_map["Snapshot B"] = run_snapshot_phase10_pipeline(
        ds=ds_b,
        folds=folds_b,
        dev_idx=dev_idx_b,
        holdout_idx=holdout_idx_b,
        thresholds=thresholds,
        snapshot_label="Snapshot B",
    )

    # 5. Compute Output Tables
    print("\n--- Step 5: Generating Structured Output Tables ---")
    perf_df = compute_regime_performance_table(data_map)
    temp_df = compute_temporal_stability_table(data_map)
    err_df = compute_error_analysis_table(data_map)
    conf_df = compute_confidence_calibration_table(data_map)
    feat_df, shap_df = compute_feature_importance_and_shap_tables(data_map)

    # 6. Save Structured Output Artifacts
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    perf_df.to_csv(OUT_REGIME_PERF_CSV, index=False)
    temp_df.to_csv(OUT_TEMP_STAB_CSV, index=False)
    err_df.to_csv(OUT_ERROR_ANALYSIS_CSV, index=False)
    conf_df.to_csv(OUT_CONF_CALIB_CSV, index=False)
    feat_df.to_csv(OUT_FEAT_IMPORTANCE_CSV, index=False)
    shap_df.to_csv(OUT_SHAP_SUMMARY_CSV, index=False)

    # Save session diagnostics
    oof_combined = pd.concat([data_map["Snapshot A"]["oof_diag"], data_map["Snapshot B"]["oof_diag"]], ignore_index=True)
    hold_combined = pd.concat([data_map["Snapshot A"]["hold_diag"], data_map["Snapshot B"]["hold_diag"]], ignore_index=True)
    oof_combined.to_csv(OUT_OOF_DIAG_CSV, index=False)
    hold_combined.to_csv(OUT_HOLDOUT_DIAG_CSV, index=False)

    print(f"  [SAVED] {OUT_REGIME_PERF_CSV}")
    print(f"  [SAVED] {OUT_TEMP_STAB_CSV}")
    print(f"  [SAVED] {OUT_ERROR_ANALYSIS_CSV}")
    print(f"  [SAVED] {OUT_CONF_CALIB_CSV}")
    print(f"  [SAVED] {OUT_FEAT_IMPORTANCE_CSV}")
    print(f"  [SAVED] {OUT_SHAP_SUMMARY_CSV}")
    print(f"  [SAVED] {OUT_OOF_DIAG_CSV}")
    print(f"  [SAVED] {OUT_HOLDOUT_DIAG_CSV}")

    # 7. Save Config JSON
    config_manifest = {
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "phase": "Phase 10 — Market Regime Detection, Explainability & Error Analysis",
        "protected_input_hashes": PROTECTED_HASHES,
        "model_architecture": {
            "model_name": "Model 1 (Price + Context)",
            "num_features": 63,
            "feature_names": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES,
            "news_features_included": False,
            "classifier_params": {**SEALED_CLF_PARAMS, "n_estimators": SEALED_CLF_TREES},
            "regressor_params": {**SEALED_REG_PARAMS, "n_estimators": SEALED_REG_TREES},
        },
        "sample_counts": {
            "development_sessions": len(dev_idx_a),
            "oof_validation_sessions": len(data_map["Snapshot A"]["total_val_indices"]),
            "terminal_holdout_sessions": len(holdout_idx_a),
        },
        "frozen_regime_thresholds": thresholds,
        "sample_size_rules": {
            "descriptive_only_threshold": 50,
            "quantitative_comparison_threshold": 50,
            "strong_statistical_threshold": 100,
        },
        "multiple_comparison_correction": "Benjamini-Hochberg FDR at alpha=0.05",
    }
    OUT_CONFIG_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CONFIG_JSON, "w") as f:
        json.dump(config_manifest, f, indent=2)
    print(f"  [SAVED] {OUT_CONFIG_JSON}")

    print("\n=======================================================")
    print("  PHASE 10 PIPELINE EXECUTION COMPLETE")
    print("=======================================================")


if __name__ == "__main__":
    main()
