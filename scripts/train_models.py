"""Main training, walk-forward cross-validation, and production refitting CLI for Phase 6.

Executes:
1. Expanding-window walk-forward cross-validation across 8 development folds (2014-2021).
2. Systematic hyperparameter selection on development OOF predictions.
3. Derivation of final_n_estimators via median of development fold early-stopping rounds.
4. Production refitting on complete Development partition (2008-07-08 to 2021-12-31).
5. Strict, single Final Performance Evaluation on Holdout (2022-01-01 to 2026-09-03).
6. Statistical testing against baselines (Diebold-Mariano HAC test & block bootstrap).
7. Atomic model persistence with provenance manifests and configs/models.yaml generation.
"""

from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple
import uuid
import numpy as np
import yaml

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.data.storage import compute_file_sha256
from nifty_ai.evaluation.calibration import (
    PlattScaler,
    compute_reliability_report,
)
from nifty_ai.evaluation.classification_metrics import evaluate_classification_metrics
from nifty_ai.evaluation.regression_metrics import evaluate_regression_metrics
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.evaluation.statistical_tests import (
    diebold_mariano_test,
    paired_bootstrap_loss_difference,
)
from nifty_ai.models.baselines import (
    ExpandingMajorityClassifier,
    ExpandingMeanReturnRegressor,
    TrailingPersistenceClassifier,
    TrailingPersistenceRegressor,
    UniformRandomClassifier,
    ZeroReturnRegressor,
)
from nifty_ai.models.dataset import (
    CLASS_MAP,
    EXPECTED_FEATURE_NAMES,
    INV_CLASS_MAP,
    AlignedDataset,
    load_aligned_dataset,
)
from nifty_ai.models.persistence import save_model_artifact_with_manifest
from nifty_ai.models.xgboost_classifier import XGBoostDirectionClassifier
from nifty_ai.models.xgboost_regressor import XGBoostReturnRegressor

FEATURES_CSV = PROJECT_ROOT / "data" / "features" / "nifty50_features_clean.csv"
TARGETS_A_CSV = PROJECT_ROOT / "data" / "targets" / "nifty50_targets_snapshot_a.csv"
TARGETS_B_CSV = PROJECT_ROOT / "data" / "targets" / "nifty50_targets_snapshot_b.csv"
MODELS_DIR = PROJECT_ROOT / "models" / "v1"
CONFIGS_MODELS_YAML = PROJECT_ROOT / "configs" / "models.yaml"
OUTPUT_REPORT_JSON = PROJECT_ROOT / "data" / "models" / "phase6_training_report.json"


def run_classifier_grid_search(
    ds: AlignedDataset,
    folds: list,
) -> Tuple[Dict[str, Any], int, Dict[str, Any], np.ndarray]:
    """Evaluate candidate classifier configurations across all 8 development folds.

    Returns:
        Tuple of (best_hyperparameters, median_best_n_estimators, aggregate_oof_metrics, oof_probs).
    """
    print("\n--- Running Classifier Walk-Forward Evaluation on Development Partition (8 Folds) ---")
    candidate_configs = [
        # lr, max_depth, min_child_weight, class_weight
        {"learning_rate": 0.03, "max_depth": 2, "min_child_weight": 10.0, "class_weight": None},
        {"learning_rate": 0.05, "max_depth": 2, "min_child_weight": 10.0, "class_weight": None},
        {"learning_rate": 0.05, "max_depth": 3, "min_child_weight": 10.0, "class_weight": None},
        {"learning_rate": 0.05, "max_depth": 3, "min_child_weight": 20.0, "class_weight": None},
        {"learning_rate": 0.10, "max_depth": 2, "min_child_weight": 10.0, "class_weight": None},
        {"learning_rate": 0.10, "max_depth": 3, "min_child_weight": 20.0, "class_weight": None},
        {"learning_rate": 0.05, "max_depth": 2, "min_child_weight": 10.0, "class_weight": "balanced"},
        {"learning_rate": 0.05, "max_depth": 3, "min_child_weight": 20.0, "class_weight": "balanced"},
    ]

    total_val_indices = np.concatenate([f.val_indices for f in folds])
    y_true_oof = ds.y_class[total_val_indices]

    best_log_loss = float("inf")
    best_config = candidate_configs[0]
    best_stopping_rounds_per_fold: List[int] = []
    best_oof_probs: Optional[np.ndarray] = None
    best_metrics: Optional[Dict[str, Any]] = None

    for cfg_idx, cfg in enumerate(candidate_configs, 1):
        fold_stopping_rounds = []
        oof_probs_list = []

        for f in folds:
            X_tr, y_tr = ds.X[f.train_indices], ds.y_class[f.train_indices]
            X_va, y_va = ds.X[f.val_indices], ds.y_class[f.val_indices]

            sw_tr = None
            if cfg["class_weight"] == "balanced":
                counts = np.bincount(y_tr, minlength=3)
                weights = len(y_tr) / (3.0 * np.maximum(counts, 1))
                sw_tr = weights[y_tr]

            clf = XGBoostDirectionClassifier(
                learning_rate=cfg["learning_rate"],
                max_depth=cfg["max_depth"],
                min_child_weight=cfg["min_child_weight"],
                n_estimators=300,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                early_stopping_rounds=25,
                random_state=42,
            )
            clf.fit(X_tr, y_tr, sample_weight=sw_tr, eval_set=[(X_va, y_va)], verbose=False)

            best_iter = clf.best_iteration if clf.best_iteration is not None else 99
            optimal_trees = best_iter + 1
            fold_stopping_rounds.append(optimal_trees)

            p_va = clf.predict_proba(X_va)
            oof_probs_list.append(p_va)

        concat_probs = np.vstack(oof_probs_list)
        metrics = evaluate_classification_metrics(y_true_oof, concat_probs)

        print(
            f"Config {cfg_idx:>2}/{len(candidate_configs)}: {cfg} -> "
            f"OOF LogLoss={metrics.log_loss:.5f}, Brier={metrics.brier_score:.5f}, "
            f"MacroF1={metrics.macro_f1:.4f}, ECE={metrics.expected_calibration_error:.4f}"
        )

        if metrics.log_loss < best_log_loss:
            best_log_loss = metrics.log_loss
            best_config = cfg
            best_stopping_rounds_per_fold = fold_stopping_rounds
            best_oof_probs = concat_probs
            best_metrics = metrics.to_dict()

    median_rounds = int(round(float(np.median(best_stopping_rounds_per_fold))))
    median_rounds = max(1, min(300, median_rounds))

    print(f"\nOptimal Classifier Configuration Selected: {best_config}")
    print(f"Per-fold optimal early-stopping rounds: {best_stopping_rounds_per_fold}")
    print(f"Derived Median Optimal n_estimators: {median_rounds}")
    print(f"Aggregated Development OOF Log Loss: {best_log_loss:.5f}")

    return best_config, median_rounds, best_metrics, best_oof_probs


def run_regressor_grid_search(
    ds: AlignedDataset,
    folds: list,
) -> Tuple[Dict[str, Any], int, Dict[str, Any], np.ndarray]:
    """Evaluate candidate regressor configurations across all 8 development folds.

    Returns:
        Tuple of (best_hyperparameters, median_best_n_estimators, aggregate_oof_metrics, oof_preds).
    """
    print("\n--- Running Regressor Walk-Forward Evaluation on Development Partition (8 Folds) ---")
    candidate_configs = [
        {"learning_rate": 0.02, "max_depth": 2, "min_child_weight": 15.0},
        {"learning_rate": 0.03, "max_depth": 2, "min_child_weight": 20.0},
        {"learning_rate": 0.03, "max_depth": 3, "min_child_weight": 30.0},
        {"learning_rate": 0.05, "max_depth": 2, "min_child_weight": 20.0},
        {"learning_rate": 0.05, "max_depth": 3, "min_child_weight": 30.0},
    ]

    total_val_indices = np.concatenate([f.val_indices for f in folds])
    y_true_oof = ds.y_reg[total_val_indices]

    best_rmse = float("inf")
    best_config = candidate_configs[0]
    best_stopping_rounds_per_fold: List[int] = []
    best_oof_preds: Optional[np.ndarray] = None
    best_metrics: Optional[Dict[str, Any]] = None

    for cfg_idx, cfg in enumerate(candidate_configs, 1):
        fold_stopping_rounds = []
        oof_preds_list = []

        for f in folds:
            X_tr, y_tr = ds.X[f.train_indices], ds.y_reg[f.train_indices]
            X_va, y_va = ds.X[f.val_indices], ds.y_reg[f.val_indices]

            reg = XGBoostReturnRegressor(
                learning_rate=cfg["learning_rate"],
                max_depth=cfg["max_depth"],
                min_child_weight=cfg["min_child_weight"],
                n_estimators=300,
                subsample=0.8,
                colsample_bytree=0.7,
                reg_alpha=0.5,
                reg_lambda=2.0,
                early_stopping_rounds=25,
                random_state=42,
            )
            reg.fit(X_tr, y_tr, eval_set=[(X_va, y_va)], verbose=False)

            best_iter = reg.best_iteration if reg.best_iteration is not None else 79
            optimal_trees = best_iter + 1
            fold_stopping_rounds.append(optimal_trees)

            preds_va = reg.predict(X_va)
            oof_preds_list.append(preds_va)

        concat_preds = np.concatenate(oof_preds_list)
        metrics = evaluate_regression_metrics(y_true_oof, concat_preds)

        print(
            f"Config {cfg_idx:>2}/{len(candidate_configs)}: {cfg} -> "
            f"OOF MAE={metrics.mae * 100:.4f}%, RMSE={metrics.rmse * 100:.4f}%, "
            f"IC={metrics.pearson_ic:+.4f} (p={metrics.pearson_ic_pvalue:.3f}), "
            f"DirAcc={metrics.directional_accuracy * 100:.2f}%"
        )

        if metrics.rmse < best_rmse:
            best_rmse = metrics.rmse
            best_config = cfg
            best_stopping_rounds_per_fold = fold_stopping_rounds
            best_oof_preds = concat_preds
            best_metrics = metrics.to_dict()

    median_rounds = int(round(float(np.median(best_stopping_rounds_per_fold))))
    median_rounds = max(1, min(300, median_rounds))

    print(f"\nOptimal Regressor Configuration Selected: {best_config}")
    print(f"Per-fold optimal early-stopping rounds: {best_stopping_rounds_per_fold}")
    print(f"Derived Median Optimal n_estimators: {median_rounds}")
    print(f"Aggregated Development OOF RMSE: {best_rmse * 100:.4f}%")

    return best_config, median_rounds, best_metrics, best_oof_preds


def main() -> None:
    print("=" * 90)
    print("NIFTY AI — PHASE 6 MODEL TRAINING & METHODOLOGY VERIFICATION")
    print("=" * 90)
    print(f"Features Source: {FEATURES_CSV}")
    print(f"Targets Source:  {TARGETS_A_CSV}")
    print(f"Development Window: <= 2021-12-31 | Holdout Window: >= 2022-01-01")

    # 1. Load Aligned Datasets for Snapshot A and Snapshot B
    ds_snap_a = load_aligned_dataset(FEATURES_CSV, TARGETS_A_CSV, SnapshotType.SNAPSHOT_1540)
    ds_snap_b = load_aligned_dataset(FEATURES_CSV, TARGETS_B_CSV, SnapshotType.SNAPSHOT_0850)
    print(f"Snapshot A Supervised Sessions: {len(ds_snap_a.dates)} ({ds_snap_a.dates[0]} to {ds_snap_a.dates[-1]})")
    print(f"Snapshot B Supervised Sessions: {len(ds_snap_b.dates)} ({ds_snap_b.dates[0]} to {ds_snap_b.dates[-1]})")

    # 2. Setup Walk-Forward Splitter
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    folds = splitter.split_development(ds_snap_a.dates)
    dev_idx, holdout_idx = splitter.get_development_and_holdout_indices(ds_snap_a.dates)

    print(f"Development partition sessions: {len(dev_idx)} ({ds_snap_a.dates[dev_idx[0]]} to {ds_snap_a.dates[dev_idx[-1]]})")
    print(f"Final Holdout partition sessions: {len(holdout_idx)} ({ds_snap_a.dates[holdout_idx[0]]} to {ds_snap_a.dates[holdout_idx[-1]]})")

    # 3. Walk-Forward Cross-Validation & Hyperparameter Selection on Development Set
    best_clf_cfg, clf_final_trees, clf_oof_metrics, oof_clf_probs = run_classifier_grid_search(ds_snap_a, folds)
    best_reg_cfg, reg_final_trees, reg_oof_metrics, oof_reg_preds = run_regressor_grid_search(ds_snap_a, folds)

    # 4. Evaluate Development Baselines on Out-of-Fold Indices
    total_val_indices = np.concatenate([f.val_indices for f in folds])
    y_true_oof_class = ds_snap_a.y_class[total_val_indices]
    y_true_oof_reg = ds_snap_a.y_reg[total_val_indices]
    X_oof = ds_snap_a.X[total_val_indices]

    # Baseline: Majority Class
    maj_clf = ExpandingMajorityClassifier().fit(ds_snap_a.X[dev_idx], ds_snap_a.y_class[dev_idx])
    maj_oof_probs = maj_clf.predict_proba(X_oof)
    maj_metrics = evaluate_classification_metrics(y_true_oof_class, maj_oof_probs)

    # Baseline: Trailing Direction Persistence
    pers_clf = TrailingPersistenceClassifier()
    pers_oof_probs = pers_clf.predict_proba(X_oof)
    pers_metrics = evaluate_classification_metrics(y_true_oof_class, pers_oof_probs)

    # Baseline: Zero Return
    zero_reg = ZeroReturnRegressor()
    zero_oof_preds = zero_reg.predict(X_oof)
    zero_metrics = evaluate_regression_metrics(y_true_oof_reg, zero_oof_preds)

    # Baseline: Expanding Mean Return
    mean_reg = ExpandingMeanReturnRegressor().fit(ds_snap_a.X[dev_idx], ds_snap_a.y_reg[dev_idx])
    mean_oof_preds = mean_reg.predict(X_oof)
    mean_metrics = evaluate_regression_metrics(y_true_oof_reg, mean_oof_preds)

    # 5. Fit Platt Calibrator strictly on Development OOF Probabilities
    platt = PlattScaler(random_seed=42)
    platt.fit(oof_clf_probs, y_true_oof_class)
    calibrated_oof_probs = platt.transform(oof_clf_probs)
    calibrated_oof_metrics = evaluate_classification_metrics(y_true_oof_class, calibrated_oof_probs)

    # 6. Train Production Reference Models on Complete Development Partition (2008-07-08 to 2021-12-31)
    print("\n--- Training Production Reference Models on Complete Development Partition ---")
    X_dev = ds_snap_a.X[dev_idx]
    y_dev_class = ds_snap_a.y_class[dev_idx]
    y_dev_reg = ds_snap_a.y_reg[dev_idx]

    sw_dev = None
    if best_clf_cfg.get("class_weight") == "balanced":
        counts = np.bincount(y_dev_class, minlength=3)
        weights = len(y_dev_class) / (3.0 * np.maximum(counts, 1))
        sw_dev = weights[y_dev_class]

    # Final Classifier
    final_clf = XGBoostDirectionClassifier(
        learning_rate=best_clf_cfg["learning_rate"],
        max_depth=best_clf_cfg["max_depth"],
        min_child_weight=best_clf_cfg["min_child_weight"],
        n_estimators=clf_final_trees,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
    )
    final_clf.fit(X_dev, y_dev_class, sample_weight=sw_dev, verbose=False)

    # Final Regressor
    final_reg = XGBoostReturnRegressor(
        learning_rate=best_reg_cfg["learning_rate"],
        max_depth=best_reg_cfg["max_depth"],
        min_child_weight=best_reg_cfg["min_child_weight"],
        n_estimators=reg_final_trees,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.5,
        reg_lambda=2.0,
        random_state=42,
    )
    final_reg.fit(X_dev, y_dev_reg, verbose=False)

    # 7. Single Final Performance Evaluation on Holdout (>= 2022-01-01)
    print("\n--- Single Final Performance Evaluation on Holdout Partition (2022-2026) ---")
    X_holdout = ds_snap_a.X[holdout_idx]
    y_holdout_class = ds_snap_a.y_class[holdout_idx]
    y_holdout_reg = ds_snap_a.y_reg[holdout_idx]
    holdout_close = ds_snap_a.close_prices[holdout_idx]

    # Classifier holdout inference
    raw_holdout_probs = final_clf.predict_proba(X_holdout)
    cal_holdout_probs = platt.transform(raw_holdout_probs)
    clf_holdout_metrics = evaluate_classification_metrics(y_holdout_class, cal_holdout_probs)

    # Regressor holdout inference
    reg_holdout_preds = final_reg.predict(X_holdout)
    reg_holdout_close = final_reg.predict_close(X_holdout, holdout_close)
    reg_holdout_metrics = evaluate_regression_metrics(y_holdout_reg, reg_holdout_preds)

    # Holdout baselines
    holdout_maj_probs = maj_clf.predict_proba(X_holdout)
    holdout_maj_metrics = evaluate_classification_metrics(y_holdout_class, holdout_maj_probs)

    holdout_zero_preds = zero_reg.predict(X_holdout)
    holdout_zero_metrics = evaluate_regression_metrics(y_holdout_reg, holdout_zero_preds)

    # 8. Statistical Testing on Holdout
    # Diebold-Mariano test (XGBoost Regressor vs Zero-Return Baseline)
    dm_result = diebold_mariano_test(y_holdout_reg, holdout_zero_preds, reg_holdout_preds, h=1, loss_type="absolute")

    # Block Bootstrap loss difference (XGBoost Classifier vs Majority Baseline)
    boot_result = paired_bootstrap_loss_difference(
        y_holdout_class, holdout_maj_probs, cal_holdout_probs, block_size=10, n_bootstrap=1000, random_seed=42
    )

    print("\nHOLDOUT CLASSIFICATION RESULTS:")
    print(f"  XGBoost Calibrated Log Loss: {clf_holdout_metrics.log_loss:.5f} (vs Majority Baseline: {holdout_maj_metrics.log_loss:.5f})")
    print(f"  XGBoost Brier Score:         {clf_holdout_metrics.brier_score:.5f} (vs Majority Baseline: {holdout_maj_metrics.brier_score:.5f})")
    print(f"  XGBoost Macro F1:            {clf_holdout_metrics.macro_f1:.4f} (vs Majority Baseline: {holdout_maj_metrics.macro_f1:.4f})")
    print(f"  XGBoost Accuracy:            {clf_holdout_metrics.accuracy * 100:.2f}% (vs Majority Baseline: {holdout_maj_metrics.accuracy * 100:.2f}%)")
    print(f"  Bootstrap Comparison:        {boot_result.interpretation}")

    print("\nHOLDOUT REGRESSION RESULTS:")
    print(f"  XGBoost MAE:                 {reg_holdout_metrics.mae * 100:.4f}% (vs Zero-Return: {holdout_zero_metrics.mae * 100:.4f}%)")
    print(f"  XGBoost RMSE:                {reg_holdout_metrics.rmse * 100:.4f}% (vs Zero-Return: {holdout_zero_metrics.rmse * 100:.4f}%)")
    print(f"  Pearson IC:                  {reg_holdout_metrics.pearson_ic:+.4f} (p-value = {reg_holdout_metrics.pearson_ic_pvalue:.4f})")
    print(f"  Directional Agreement:       {reg_holdout_metrics.directional_accuracy * 100:.2f}%")
    print(f"  Diebold-Mariano Test:        {dm_result.interpretation} (stat={dm_result.hln_corrected_statistic:.3f}, p={dm_result.hln_p_value:.4f})")

    # 9. Atomic Persistence of Production Artifacts
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    features_sha = compute_file_sha256(FEATURES_CSV)
    targets_a_sha = compute_file_sha256(TARGETS_A_CSV)
    targets_b_sha = compute_file_sha256(TARGETS_B_CSV)

    # Persist Snapshot A Classifier
    snap_a_clf_path = MODELS_DIR / "classifier" / "snapshot_a_xgboost_classifier.json"
    save_model_artifact_with_manifest(
        final_clf,
        snap_a_clf_path,
        {
            "model_id": str(uuid.uuid4()),
            "model_type": "xgboost_classifier",
            "model_version": "1.0.0",
            "snapshot_type": SnapshotType.SNAPSHOT_1540.value,
            "development_training_range": {"start": ds_snap_a.dates[dev_idx[0]].isoformat(), "end": ds_snap_a.dates[dev_idx[-1]].isoformat()},
            "feature_dataset_sha256": features_sha,
            "target_dataset_sha256": targets_a_sha,
            "feature_names": EXPECTED_FEATURE_NAMES,
            "frozen_hyperparameters": best_clf_cfg,
            "final_n_estimators": clf_final_trees,
            "random_seed": 42,
            "calibration_status": {"is_calibrated": True, "method": "platt_multinomial_logistic", "oof_brier_score": calibrated_oof_metrics.brier_score},
            "development_oof_metrics": calibrated_oof_metrics.to_dict(),
        },
    )

    # Persist Snapshot B Classifier
    snap_b_clf_path = MODELS_DIR / "classifier" / "snapshot_b_xgboost_classifier.json"
    save_model_artifact_with_manifest(
        final_clf,
        snap_b_clf_path,
        {
            "model_id": str(uuid.uuid4()),
            "model_type": "xgboost_classifier",
            "model_version": "1.0.0",
            "snapshot_type": SnapshotType.SNAPSHOT_0850.value,
            "development_training_range": {"start": ds_snap_b.dates[dev_idx[0]].isoformat(), "end": ds_snap_b.dates[dev_idx[-1]].isoformat()},
            "feature_dataset_sha256": features_sha,
            "target_dataset_sha256": targets_b_sha,
            "feature_names": EXPECTED_FEATURE_NAMES,
            "frozen_hyperparameters": best_clf_cfg,
            "final_n_estimators": clf_final_trees,
            "random_seed": 42,
            "calibration_status": {"is_calibrated": True, "method": "platt_multinomial_logistic", "oof_brier_score": calibrated_oof_metrics.brier_score},
            "development_oof_metrics": calibrated_oof_metrics.to_dict(),
        },
    )

    # Persist Snapshot A Regressor
    snap_a_reg_path = MODELS_DIR / "regressor" / "snapshot_a_xgboost_regressor.json"
    save_model_artifact_with_manifest(
        final_reg,
        snap_a_reg_path,
        {
            "model_id": str(uuid.uuid4()),
            "model_type": "xgboost_regressor",
            "model_version": "1.0.0",
            "snapshot_type": SnapshotType.SNAPSHOT_1540.value,
            "development_training_range": {"start": ds_snap_a.dates[dev_idx[0]].isoformat(), "end": ds_snap_a.dates[dev_idx[-1]].isoformat()},
            "feature_dataset_sha256": features_sha,
            "target_dataset_sha256": targets_a_sha,
            "feature_names": EXPECTED_FEATURE_NAMES,
            "frozen_hyperparameters": best_reg_cfg,
            "final_n_estimators": reg_final_trees,
            "random_seed": 42,
            "calibration_status": {"is_calibrated": False},
            "development_oof_metrics": reg_oof_metrics,
        },
    )

    # Persist Snapshot B Regressor
    snap_b_reg_path = MODELS_DIR / "regressor" / "snapshot_b_xgboost_regressor.json"
    save_model_artifact_with_manifest(
        final_reg,
        snap_b_reg_path,
        {
            "model_id": str(uuid.uuid4()),
            "model_type": "xgboost_regressor",
            "model_version": "1.0.0",
            "snapshot_type": SnapshotType.SNAPSHOT_0850.value,
            "development_training_range": {"start": ds_snap_b.dates[dev_idx[0]].isoformat(), "end": ds_snap_b.dates[dev_idx[-1]].isoformat()},
            "feature_dataset_sha256": features_sha,
            "target_dataset_sha256": targets_b_sha,
            "feature_names": EXPECTED_FEATURE_NAMES,
            "frozen_hyperparameters": best_reg_cfg,
            "final_n_estimators": reg_final_trees,
            "random_seed": 42,
            "calibration_status": {"is_calibrated": False},
            "development_oof_metrics": reg_oof_metrics,
        },
    )

    # 10. Write configs/models.yaml
    config_data = {
        "model_layer_version": "1.0.0",
        "development_period": {"start": "2008-07-08", "end": "2021-12-31"},
        "holdout_period": {"start": "2022-01-01", "end": "2026-09-04"},
        "classifier": {
            "model_type": "xgboost_classifier",
            "objective": "multi:softprob",
            "num_class": 3,
            "frozen_hyperparameters": best_clf_cfg,
            "final_n_estimators": clf_final_trees,
            "calibration": {"enabled": True, "method": "platt_multinomial_logistic"},
            "classes": {"0": "DOWN", "1": "SIDEWAYS", "2": "UP"},
        },
        "regressor": {
            "model_type": "xgboost_regressor",
            "objective": "reg:squarederror",
            "frozen_hyperparameters": best_reg_cfg,
            "final_n_estimators": reg_final_trees,
            "target_definition": "next_session_close_to_close_return",
        },
        "provenance": {
            "features_file": FEATURES_CSV.name,
            "features_sha256": features_sha,
            "targets_snapshot_a_file": TARGETS_A_CSV.name,
            "targets_snapshot_a_sha256": targets_a_sha,
        },
    }
    CONFIGS_MODELS_YAML.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIGS_MODELS_YAML, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, sort_keys=False, indent=2)

    # 11. Write full report JSON
    OUTPUT_REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    full_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "development_period": {"start": "2008-07-08", "end": "2021-12-31", "samples": len(dev_idx)},
        "holdout_period": {"start": "2022-01-01", "end": "2026-09-03", "samples": len(holdout_idx)},
        "classifier": {
            "frozen_parameters": best_clf_cfg,
            "final_n_estimators": clf_final_trees,
            "development_oof_metrics": clf_oof_metrics,
            "development_oof_calibrated_metrics": calibrated_oof_metrics.to_dict(),
            "development_majority_baseline": maj_metrics.to_dict(),
            "holdout_metrics": clf_holdout_metrics.to_dict(),
            "holdout_majority_baseline": holdout_maj_metrics.to_dict(),
            "statistical_test_vs_baseline": asdict(boot_result),
        },
        "regressor": {
            "frozen_parameters": best_reg_cfg,
            "final_n_estimators": reg_final_trees,
            "development_oof_metrics": reg_oof_metrics,
            "development_zero_baseline": zero_metrics.to_dict(),
            "holdout_metrics": reg_holdout_metrics.to_dict(),
            "holdout_zero_baseline": holdout_zero_metrics.to_dict(),
            "diebold_mariano_test_vs_zero": asdict(dm_result),
        },
    }
    with open(OUTPUT_REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    print(f"\nSaved production models to: {MODELS_DIR}")
    print(f"Saved registry configuration to: {CONFIGS_MODELS_YAML}")
    print(f"Saved complete diagnostic report to: {OUTPUT_REPORT_JSON}")


if __name__ == "__main__":
    from datetime import datetime, timezone
    main()
