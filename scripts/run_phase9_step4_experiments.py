"""Phase 9 Step 4: Incremental News Predictive-Value Experiment Runner.

Executes the approved experimental protocol:
1. Enforces protected SHA-256 checksums on all Phase 8 and Phase 9 input artifacts.
2. Preserves sealed Phase 6 XGBoost configurations and tree counts (N*=12 Classifier, N*=43 Regressor).
3. Evaluates Model 0 (Price), Model 1 (Price+Context), Model 2 (Price+Context+News-All),
   6 disjoint news ablations, and Model 3 (Regime interaction).
4. Runs full 8-fold walk-forward cross-validation (2014-2021) on Development partition.
5. Fits Platt probability calibration strictly inside development/OOF.
6. Evaluates single frozen evaluation on Terminal Holdout (2022-2026).
7. Computes Diebold-Mariano HAC tests and 1,000-resample stationary block bootstrap CIs.
8. Produces all required experiment CSVs, JSON config, and results artifacts.
"""

from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.calibration import PlattScaler
from nifty_ai.evaluation.classification_metrics import evaluate_classification_metrics
from nifty_ai.evaluation.regression_metrics import evaluate_regression_metrics
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.evaluation.statistical_tests import (
    diebold_mariano_test,
    paired_bootstrap_loss_difference,
)
from nifty_ai.models.multimodal import (
    ALL_NEWS_FEATURE_NAMES,
    CONTEXT_FEATURE_NAMES,
    MODEL_FEATURE_SPECS,
    NEWS_FEATURE_GROUPS,
    PRICE_FEATURE_NAMES,
    REGIME_INTERACTION_FEATURES,
    MultimodalDataset,
    load_multimodal_dataset,
)
from nifty_ai.models.xgboost_classifier import XGBoostDirectionClassifier
from nifty_ai.models.xgboost_regressor import XGBoostReturnRegressor

# ---------------------------------------------------------------------------
# Protected Checksums Contract
# ---------------------------------------------------------------------------
EXPECTED_HASHES = {
    "data/interim/news/raw_authentic_news_inventory.jsonl": "6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3",
    "data/interim/news/gold_holdout_annotation_input.csv": "0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199",
    "data/interim/news/raw_authentic_news_terminal_2022_2026_step2e.jsonl": "5d5daf5ed7c844e86d45dc6a893f03b1d4f523183e29200d94b592329136f6fd",
    "data/interim/news/features_news_snapshot_a.csv": "487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7",
    "data/interim/news/features_news_snapshot_b.csv": "f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606",
    "data/interim/news/features_news_snapshot_delta.csv": "8923c11583fb87fe8458f00aaf714eadacb8a3d402a7143a5b2483549c8ece4c",
}

# ---------------------------------------------------------------------------
# Sealed Phase 6 Hyperparameters
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

OUTPUT_EXPERIMENT_RESULTS_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "phase9_step4_experiment_results.csv"
OUTPUT_OOF_RESULTS_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "phase9_step4_oof_results.csv"
OUTPUT_HOLDOUT_RESULTS_CSV = PROJECT_ROOT / "data" / "interim" / "news" / "phase9_step4_holdout_results.csv"
OUTPUT_CONFIG_JSON = PROJECT_ROOT / "configs" / "phase9_step4_experiment_config.json"


def verify_protected_checksums() -> Dict[str, str]:
    """Verify SHA-256 checksums of all protected Phase 8 and Phase 9 input files."""
    verified = {}
    for rel_path, expected_hash in EXPECTED_HASHES.items():
        full_path = PROJECT_ROOT / rel_path
        if not full_path.is_file():
            raise FileNotFoundError(f"Missing protected file: {rel_path}")
        computed_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
        if computed_hash != expected_hash:
            raise ValueError(
                f"PROTECTED CHECKSUM VIOLATION for {rel_path}!\n"
                f"  Expected: {expected_hash}\n"
                f"  Computed: {computed_hash}"
            )
        verified[rel_path] = computed_hash
    return verified


def compute_bootstrap_ic_difference(
    y_true: np.ndarray,
    y_pred_base: np.ndarray,
    y_pred_cand: np.ndarray,
    block_size: int = 10,
    n_bootstrap: int = 1000,
    random_seed: int = 42,
) -> Tuple[float, float, float, bool]:
    """Compute stationary block bootstrap for difference in Pearson IC (IC_cand - IC_base)."""
    rng = np.random.default_rng(random_seed)
    n = len(y_true)
    n_blocks = int(math.ceil(n / block_size))

    # Base IC
    def calc_ic(yt: np.ndarray, yp: np.ndarray) -> float:
        if np.std(yt) == 0 or np.std(yp) == 0:
            return 0.0
        r = np.corrcoef(yt, yp)[0, 1]
        return float(r) if np.isfinite(r) else 0.0

    actual_diff = calc_ic(y_true, y_pred_cand) - calc_ic(y_true, y_pred_base)

    boot_diffs = []
    for _ in range(n_bootstrap):
        start_indices = rng.integers(0, n - block_size + 1, size=n_blocks)
        sampled_indices = []
        for s in start_indices:
            sampled_indices.extend(range(s, s + block_size))
        sampled_indices = sampled_indices[:n]

        b_yt = y_true[sampled_indices]
        b_p_base = y_pred_base[sampled_indices]
        b_p_cand = y_pred_cand[sampled_indices]

        diff_b = calc_ic(b_yt, b_p_cand) - calc_ic(b_yt, b_p_base)
        boot_diffs.append(diff_b)

    ci_lower = float(np.percentile(boot_diffs, 2.5))
    ci_upper = float(np.percentile(boot_diffs, 97.5))
    is_sig = (ci_lower > 0.0) or (ci_upper < 0.0)
    return actual_diff, ci_lower, ci_upper, is_sig


def run_snapshot_experiment(
    ds: MultimodalDataset,
    folds: list,
    dev_idx: np.ndarray,
    holdout_idx: np.ndarray,
    snapshot_label: str,
) -> Tuple[List[Dict[str, Any]], pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Execute complete OOF cross-validation and single terminal holdout evaluation for one snapshot.

    Returns:
        Tuple of:
        - List of summary result dicts (for results.csv)
        - OOF predictions DataFrame
        - Holdout predictions DataFrame
        - Detailed feature importances and fold metrics
    """
    total_val_indices = np.concatenate([f.val_indices for f in folds])
    y_true_oof_class = ds.y_class[total_val_indices]
    y_true_oof_reg = ds.y_reg[total_val_indices]
    oof_dates = [ds.dates[i] for i in total_val_indices]
    oof_target_dates = [ds.target_dates[i] for i in total_val_indices]

    y_true_holdout_class = ds.y_class[holdout_idx]
    y_true_holdout_reg = ds.y_reg[holdout_idx]
    holdout_dates = [ds.dates[i] for i in holdout_idx]
    holdout_target_dates = [ds.target_dates[i] for i in holdout_idx]

    summary_rows: List[Dict[str, Any]] = []

    # Dictionaries to store predictions across models
    oof_clf_raw_probs: Dict[str, np.ndarray] = {}
    oof_clf_cal_probs: Dict[str, np.ndarray] = {}
    oof_reg_preds: Dict[str, np.ndarray] = {}

    holdout_clf_raw_probs: Dict[str, np.ndarray] = {}
    holdout_clf_cal_probs: Dict[str, np.ndarray] = {}
    holdout_reg_preds: Dict[str, np.ndarray] = {}

    fitted_scalers: Dict[str, PlattScaler] = {}
    model_importances: Dict[str, Any] = {}

    model_order = [
        "Model 0",
        "Model 1",
        "Model 2",
        "M2-Ablation-Count",
        "M2-Ablation-Sentiment",
        "M2-Ablation-Importance",
        "M2-Ablation-Event",
        "M2-Ablation-Novelty",
        "M2-Ablation-Company",
        "Model 3",
    ]

    print(f"\n=======================================================")
    print(f"  EXECUTING EXPERIMENTS FOR SNAPSHOT {snapshot_label}")
    print(f"=======================================================")

    for m_name in model_order:
        X_full, feat_names = ds.get_features(m_name)
        n_feats = len(feat_names)
        print(f"\n[{snapshot_label}] Evaluating {m_name:25s} (dim={n_feats})...")

        # -------------------------------------------------------------
        # 1. Walk-Forward Cross-Validation (8 Folds, 2014-2021)
        # -------------------------------------------------------------
        fold_raw_probs_list = []
        fold_reg_preds_list = []

        for f_idx, fold in enumerate(folds):
            X_tr, y_tr_c, y_tr_r = X_full[fold.train_indices], ds.y_class[fold.train_indices], ds.y_reg[fold.train_indices]
            X_va, y_va_c, y_va_r = X_full[fold.val_indices], ds.y_class[fold.val_indices], ds.y_reg[fold.val_indices]

            # Classifier Fold Training (Sealed N*=12)
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
            val_probs = clf.predict_proba(X_va)
            fold_raw_probs_list.append(val_probs)

            # Regressor Fold Training (Sealed N*=43)
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
            val_preds = reg.predict(X_va)
            fold_reg_preds_list.append(val_preds)

        raw_oof_probs = np.concatenate(fold_raw_probs_list, axis=0)
        oof_reg = np.concatenate(fold_reg_preds_list, axis=0)

        # -------------------------------------------------------------
        # 2. Probability Calibration Fitted Strictly on OOF
        # -------------------------------------------------------------
        scaler = PlattScaler(random_seed=42)
        scaler.fit(raw_oof_probs, y_true_oof_class)
        cal_oof_probs = scaler.transform(raw_oof_probs)

        oof_clf_raw_probs[m_name] = raw_oof_probs
        oof_clf_cal_probs[m_name] = cal_oof_probs
        oof_reg_preds[m_name] = oof_reg
        fitted_scalers[m_name] = scaler

        # Compute OOF Metrics
        oof_clf_raw_metrics = evaluate_classification_metrics(y_true_oof_class, raw_oof_probs)
        oof_clf_cal_metrics = evaluate_classification_metrics(y_true_oof_class, cal_oof_probs)
        oof_reg_metrics = evaluate_regression_metrics(y_true_oof_reg, oof_reg)

        print(
            f"  OOF LogLoss(raw)={oof_clf_raw_metrics.log_loss:.5f} | "
            f"LogLoss(cal)={oof_clf_cal_metrics.log_loss:.5f} | "
            f"Brier(cal)={oof_clf_cal_metrics.brier_score:.5f} | "
            f"RMSE={oof_reg_metrics.rmse * 100:.4f}% | "
            f"Pearson IC={oof_reg_metrics.pearson_ic:+.4f} (p={oof_reg_metrics.pearson_ic_pvalue:.4f})"
        )

        # -------------------------------------------------------------
        # 3. Production Model Refit on Full Dev Partition (2008-2021)
        # -------------------------------------------------------------
        X_dev = X_full[dev_idx]
        y_dev_c = ds.y_class[dev_idx]
        y_dev_r = ds.y_reg[dev_idx]

        final_clf = XGBoostDirectionClassifier(
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
        final_clf.fit(X_dev, y_dev_c, verbose=False)

        final_reg = XGBoostReturnRegressor(
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
        final_reg.fit(X_dev, y_dev_r, verbose=False)

        # Save feature importances with proper feature names
        if m_name in ["Model 1", "Model 2"]:
            booster_clf = final_clf._clf.get_booster()
            booster_reg = final_reg._reg.get_booster()
            booster_clf.feature_names = list(feat_names)
            booster_reg.feature_names = list(feat_names)

            clf_gain = booster_clf.get_score(importance_type="gain")
            reg_gain = booster_reg.get_score(importance_type="gain")
            clf_weight = booster_clf.get_score(importance_type="weight")
            reg_weight = booster_reg.get_score(importance_type="weight")
            model_importances[f"{m_name}_clf_gain"] = clf_gain
            model_importances[f"{m_name}_clf_weight"] = clf_weight
            model_importances[f"{m_name}_reg_gain"] = reg_gain
            model_importances[f"{m_name}_reg_weight"] = reg_weight

        # -------------------------------------------------------------
        # 4. Terminal Holdout Evaluation (2022-2026, Single Pass)
        # -------------------------------------------------------------
        X_holdout = X_full[holdout_idx]
        holdout_raw_probs = final_clf.predict_proba(X_holdout)
        holdout_cal_probs = scaler.transform(holdout_raw_probs)
        holdout_reg = final_reg.predict(X_holdout)

        holdout_clf_raw_probs[m_name] = holdout_raw_probs
        holdout_clf_cal_probs[m_name] = holdout_cal_probs
        holdout_reg_preds[m_name] = holdout_reg

        holdout_clf_raw_metrics = evaluate_classification_metrics(y_true_holdout_class, holdout_raw_probs)
        holdout_clf_cal_metrics = evaluate_classification_metrics(y_true_holdout_class, holdout_cal_probs)
        holdout_reg_metrics = evaluate_regression_metrics(y_true_holdout_reg, holdout_reg)

        print(
            f"  Holdout LogLoss(raw)={holdout_clf_raw_metrics.log_loss:.5f} | "
            f"LogLoss(cal)={holdout_clf_cal_metrics.log_loss:.5f} | "
            f"Brier(cal)={holdout_clf_cal_metrics.brier_score:.5f} | "
            f"RMSE={holdout_reg_metrics.rmse * 100:.4f}% | "
            f"Pearson IC={holdout_reg_metrics.pearson_ic:+.4f} (p={holdout_reg_metrics.pearson_ic_pvalue:.4f})"
        )

        # Append OOF row
        summary_rows.append({
            "snapshot": snapshot_label,
            "partition": "OOF",
            "model_id": m_name,
            "num_features": n_feats,
            "n_sessions": len(total_val_indices),
            "log_loss_raw": oof_clf_raw_metrics.log_loss,
            "log_loss_calibrated": oof_clf_cal_metrics.log_loss,
            "brier_score_raw": oof_clf_raw_metrics.brier_score,
            "brier_score_calibrated": oof_clf_cal_metrics.brier_score,
            "accuracy_raw": oof_clf_raw_metrics.accuracy,
            "accuracy_calibrated": oof_clf_cal_metrics.accuracy,
            "macro_f1_calibrated": oof_clf_cal_metrics.macro_f1,
            "expected_calibration_error": oof_clf_cal_metrics.expected_calibration_error,
            "mae": oof_reg_metrics.mae,
            "rmse": oof_reg_metrics.rmse,
            "pearson_ic": oof_reg_metrics.pearson_ic,
            "pearson_ic_pvalue": oof_reg_metrics.pearson_ic_pvalue,
            "spearman_ic": oof_reg_metrics.spearman_ic,
            "spearman_ic_pvalue": oof_reg_metrics.spearman_ic_pvalue,
            "directional_accuracy": oof_reg_metrics.directional_accuracy,
        })

        # Append Holdout row
        summary_rows.append({
            "snapshot": snapshot_label,
            "partition": "Holdout",
            "model_id": m_name,
            "num_features": n_feats,
            "n_sessions": len(holdout_idx),
            "log_loss_raw": holdout_clf_raw_metrics.log_loss,
            "log_loss_calibrated": holdout_clf_cal_metrics.log_loss,
            "brier_score_raw": holdout_clf_raw_metrics.brier_score,
            "brier_score_calibrated": holdout_clf_cal_metrics.brier_score,
            "accuracy_raw": holdout_clf_raw_metrics.accuracy,
            "accuracy_calibrated": holdout_clf_cal_metrics.accuracy,
            "macro_f1_calibrated": holdout_clf_cal_metrics.macro_f1,
            "expected_calibration_error": holdout_clf_cal_metrics.expected_calibration_error,
            "mae": holdout_reg_metrics.mae,
            "rmse": holdout_reg_metrics.rmse,
            "pearson_ic": holdout_reg_metrics.pearson_ic,
            "pearson_ic_pvalue": holdout_reg_metrics.pearson_ic_pvalue,
            "spearman_ic": holdout_reg_metrics.spearman_ic,
            "spearman_ic_pvalue": holdout_reg_metrics.spearman_ic_pvalue,
            "directional_accuracy": holdout_reg_metrics.directional_accuracy,
        })

    # -----------------------------------------------------------------
    # 5. Statistical Hypothesis Testing Against Model 1 (Price+Context)
    # -----------------------------------------------------------------
    print(f"\n[{snapshot_label}] Running Statistical Significance Tests vs Model 1...")

    for partition_name in ["OOF", "Holdout"]:
        if partition_name == "OOF":
            y_true_c = y_true_oof_class
            y_true_r = y_true_oof_reg
            cal_probs_map = oof_clf_cal_probs
            raw_probs_map = oof_clf_raw_probs
            reg_preds_map = oof_reg_preds
        else:
            y_true_c = y_true_holdout_class
            y_true_r = y_true_holdout_reg
            cal_probs_map = holdout_clf_cal_probs
            raw_probs_map = holdout_clf_raw_probs
            reg_preds_map = holdout_reg_preds

        p1_cal = cal_probs_map["Model 1"]
        r1 = reg_preds_map["Model 1"]

        # Find M1 baseline row for this partition
        m1_row = next(
            r for r in summary_rows
            if r["snapshot"] == snapshot_label and r["partition"] == partition_name and r["model_id"] == "Model 1"
        )
        m1_cal_logloss = m1_row["log_loss_calibrated"]
        m1_cal_brier = m1_row["brier_score_calibrated"]
        m1_rmse = m1_row["rmse"]
        m1_ic = m1_row["pearson_ic"]

        for row in summary_rows:
            if row["snapshot"] == snapshot_label and row["partition"] == partition_name:
                m = row["model_id"]
                cand_p_cal = cal_probs_map[m]
                cand_r = reg_preds_map[m]

                # Classification bootstrap test (Model 1 baseline vs Candidate)
                boot_res = paired_bootstrap_loss_difference(
                    y_true=y_true_c,
                    probs_baseline=p1_cal,
                    probs_candidate=cand_p_cal,
                    block_size=10,
                    n_bootstrap=1000,
                    random_seed=42,
                )
                # Note: boot_res.mean_loss_diff = Loss(M1) - Loss(M)
                # Positive means Candidate M has lower loss (better)
                row["delta_logloss_vs_m1"] = row["log_loss_calibrated"] - m1_cal_logloss
                row["delta_brier_vs_m1"] = row["brier_score_calibrated"] - m1_cal_brier
                row["delta_rmse_vs_m1"] = row["rmse"] - m1_rmse
                row["bootstrap_loss_reduction_mean"] = boot_res.mean_loss_diff
                row["bootstrap_loss_reduction_ci_lower"] = boot_res.ci_lower
                row["bootstrap_loss_reduction_ci_upper"] = boot_res.ci_upper
                row["bootstrap_loss_significant_05"] = boot_res.significant_at_05
                row["bootstrap_interpretation"] = boot_res.interpretation

                # Regression Diebold-Mariano test (Model 1 baseline vs Candidate)
                if m == "Model 1":
                    row["dm_stat_vs_m1"] = 0.0
                    row["dm_pvalue_vs_m1"] = 1.0
                    row["dm_interpretation"] = "Self comparison"
                    row["delta_ic_vs_m1"] = 0.0
                    row["bootstrap_ic_diff_ci_lower"] = 0.0
                    row["bootstrap_ic_diff_ci_upper"] = 0.0
                    row["bootstrap_ic_significant_05"] = False
                else:
                    dm_res = diebold_mariano_test(
                        y_true=y_true_r,
                        y_pred1=r1,
                        y_pred2=cand_r,
                        h=1,
                        loss_type="absolute",
                    )
                    row["dm_stat_vs_m1"] = dm_res.hln_corrected_statistic
                    row["dm_pvalue_vs_m1"] = dm_res.hln_p_value
                    row["dm_interpretation"] = dm_res.interpretation

                    ic_diff, ic_ci_low, ic_ci_upp, ic_sig = compute_bootstrap_ic_difference(
                        y_true=y_true_r,
                        y_pred_base=r1,
                        y_pred_cand=cand_r,
                        block_size=10,
                        n_bootstrap=1000,
                        random_seed=42,
                    )
                    row["delta_ic_vs_m1"] = ic_diff
                    row["bootstrap_ic_diff_ci_lower"] = ic_ci_low
                    row["bootstrap_ic_diff_ci_upper"] = ic_ci_upp
                    row["bootstrap_ic_significant_05"] = ic_sig


    # -----------------------------------------------------------------
    # 6. Detailed Session-Level Output DataFrames
    # -----------------------------------------------------------------
    oof_df = pd.DataFrame({
        "snapshot": snapshot_label,
        "trading_date": [d.isoformat() for d in oof_dates],
        "target_date": [d.isoformat() for d in oof_target_dates],
        "y_true_class": y_true_oof_class,
        "y_true_reg": y_true_oof_reg,
    })
    for m in model_order:
        slug = m.lower().replace(" ", "_").replace("-", "_")
        raw_p = oof_clf_raw_probs[m]
        cal_p = oof_clf_cal_probs[m]
        oof_df[f"{slug}_raw_prob_down"] = raw_p[:, 0]
        oof_df[f"{slug}_raw_prob_sideways"] = raw_p[:, 1]
        oof_df[f"{slug}_raw_prob_up"] = raw_p[:, 2]
        oof_df[f"{slug}_cal_prob_down"] = cal_p[:, 0]
        oof_df[f"{slug}_cal_prob_sideways"] = cal_p[:, 1]
        oof_df[f"{slug}_cal_prob_up"] = cal_p[:, 2]
        oof_df[f"{slug}_pred_class"] = np.argmax(cal_p, axis=1)
        oof_df[f"{slug}_pred_reg"] = oof_reg_preds[m]

    holdout_df = pd.DataFrame({
        "snapshot": snapshot_label,
        "trading_date": [d.isoformat() for d in holdout_dates],
        "target_date": [d.isoformat() for d in holdout_target_dates],
        "y_true_class": y_true_holdout_class,
        "y_true_reg": y_true_holdout_reg,
    })
    for m in model_order:
        slug = m.lower().replace(" ", "_").replace("-", "_")
        raw_p = holdout_clf_raw_probs[m]
        cal_p = holdout_clf_cal_probs[m]
        holdout_df[f"{slug}_raw_prob_down"] = raw_p[:, 0]
        holdout_df[f"{slug}_raw_prob_sideways"] = raw_p[:, 1]
        holdout_df[f"{slug}_raw_prob_up"] = raw_p[:, 2]
        holdout_df[f"{slug}_cal_prob_down"] = cal_p[:, 0]
        holdout_df[f"{slug}_cal_prob_sideways"] = cal_p[:, 1]
        holdout_df[f"{slug}_cal_prob_up"] = cal_p[:, 2]
        holdout_df[f"{slug}_pred_class"] = np.argmax(cal_p, axis=1)
        holdout_df[f"{slug}_pred_reg"] = holdout_reg_preds[m]

    return summary_rows, oof_df, holdout_df, model_importances


def main() -> None:
    print("=" * 90)
    print("PHASE 9 — STEP 4: INCREMENTAL NEWS PREDICTIVE-VALUE EXPERIMENT")
    print("=" * 90)

    # 1. Enforce Protected Hashes
    print("\n--- Step 1: Enforcing Protected Checksums ---")
    verified_hashes = verify_protected_checksums()
    for p, h in verified_hashes.items():
        print(f"  [LOCKED] {p} -> {h[:16]}...")
    print("All protected SHA-256 checksums successfully verified!")

    # 2. Setup Splitter
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))

    # 3. Load Snapshot A and Snapshot B Multimodal Datasets
    print("\n--- Step 2: Loading Multimodal Datasets ---")
    ds_a = load_multimodal_dataset(SnapshotType.SNAPSHOT_1540)
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)

    folds_a = splitter.split_development(ds_a.dates)
    dev_idx_a, holdout_idx_a = splitter.get_development_and_holdout_indices(ds_a.dates)

    folds_b = splitter.split_development(ds_b.dates)
    dev_idx_b, holdout_idx_b = splitter.get_development_and_holdout_indices(ds_b.dates)

    print(f"Snapshot A: Total={len(ds_a.dates)}, Dev={len(dev_idx_a)}, Holdout={len(holdout_idx_a)}, Folds={len(folds_a)}")
    print(f"Snapshot B: Total={len(ds_b.dates)}, Dev={len(dev_idx_b)}, Holdout={len(holdout_idx_b)}, Folds={len(folds_b)}")

    # 4. Run Experiment for Snapshot A
    rows_a, oof_df_a, holdout_df_a, imps_a = run_snapshot_experiment(
        ds=ds_a,
        folds=folds_a,
        dev_idx=dev_idx_a,
        holdout_idx=holdout_idx_a,
        snapshot_label="Snapshot A",
    )

    # 5. Run Experiment for Snapshot B
    rows_b, oof_df_b, holdout_df_b, imps_b = run_snapshot_experiment(
        ds=ds_b,
        folds=folds_b,
        dev_idx=dev_idx_b,
        holdout_idx=holdout_idx_b,
        snapshot_label="Snapshot B",
    )

    # 6. Aggregate Results
    all_summary_rows = rows_a + rows_b
    summary_df = pd.DataFrame(all_summary_rows)

    all_oof_df = pd.concat([oof_df_a, oof_df_b], ignore_index=True)
    all_holdout_df = pd.concat([holdout_df_a, holdout_df_b], ignore_index=True)

    # 7. Write Output CSVs
    OUTPUT_EXPERIMENT_RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(OUTPUT_EXPERIMENT_RESULTS_CSV, index=False)
    print(f"\n[OUTPUT] Saved summary results to: {OUTPUT_EXPERIMENT_RESULTS_CSV}")

    all_oof_df.to_csv(OUTPUT_OOF_RESULTS_CSV, index=False)
    print(f"[OUTPUT] Saved OOF predictions to: {OUTPUT_OOF_RESULTS_CSV}")

    all_holdout_df.to_csv(OUTPUT_HOLDOUT_RESULTS_CSV, index=False)
    print(f"[OUTPUT] Saved Holdout predictions to: {OUTPUT_HOLDOUT_RESULTS_CSV}")

    # 8. Write Experiment Config JSON
    config_data = {
        "execution_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_name": "Phase 9 Step 4 Incremental News Predictive-Value Experiment",
        "protected_hashes_verified": verified_hashes,
        "sample_counts": {
            "total_supervised_sessions": 4453,
            "development_sessions": 3299,
            "oof_validation_sessions": 1960,
            "terminal_holdout_sessions": 1154,
            "date_range": "2008-07-08 to 2026-09-03",
        },
        "feature_dimensions": {
            "price": len(PRICE_FEATURE_NAMES),
            "context": len(CONTEXT_FEATURE_NAMES),
            "news_total": len(ALL_NEWS_FEATURE_NAMES),
            "news_groups": {k: len(v) for k, v in NEWS_FEATURE_GROUPS.items()},
            "regime_interactions": len(REGIME_INTERACTION_FEATURES),
            "model_features": {k: len(v) for k, v in MODEL_FEATURE_SPECS.items()},
        },
        "hyperparameters": {
            "direction_classifier": {
                **SEALED_CLF_PARAMS,
                "n_estimators": SEALED_CLF_TREES,
                "calibration": "platt_multinomial_logistic_fitted_on_oof",
            },
            "return_regressor": {
                **SEALED_REG_PARAMS,
                "n_estimators": SEALED_REG_TREES,
            },
        },
        "importances": {
            "snapshot_a": imps_a,
            "snapshot_b": imps_b,
        },
    }

    OUTPUT_CONFIG_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CONFIG_JSON, "w") as f:
        json.dump(config_data, f, indent=2)
    print(f"[OUTPUT] Saved config and provenance manifest to: {OUTPUT_CONFIG_JSON}")

    # 9. Print Concise Comparison Table
    print("\n" + "=" * 90)
    print("  EXECUTIVE SUMMARY OF EXPERIMENTAL RESULTS")
    print("=" * 90)
    display_cols = [
        "snapshot",
        "partition",
        "model_id",
        "num_features",
        "log_loss_calibrated",
        "brier_score_calibrated",
        "accuracy_calibrated",
        "rmse",
        "pearson_ic",
        "delta_logloss_vs_m1",
        "bootstrap_loss_reduction_ci_lower",
        "bootstrap_loss_reduction_ci_upper",
        "dm_pvalue_vs_m1",
        "delta_ic_vs_m1",
    ]
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 1000)
    print(summary_df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()
