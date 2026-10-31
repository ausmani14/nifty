"""Evaluation and diagnostic reporting CLI for trained Phase 6 models.

Loads persisted XGBoost models from models/v1/, executes model verification,
and prints formatted diagnostic reports comparing performance against naive baselines
across development out-of-fold and final holdout periods.
"""

import json
from pathlib import Path
import sys
import numpy as np

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.classification_metrics import evaluate_classification_metrics
from nifty_ai.evaluation.regression_metrics import evaluate_regression_metrics
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.dataset import load_aligned_dataset
from nifty_ai.models.xgboost_classifier import XGBoostDirectionClassifier
from nifty_ai.models.xgboost_regressor import XGBoostReturnRegressor

FEATURES_CSV = PROJECT_ROOT / "data" / "features" / "nifty50_features_clean.csv"
TARGETS_A_CSV = PROJECT_ROOT / "data" / "targets" / "nifty50_targets_snapshot_a.csv"
MODELS_DIR = PROJECT_ROOT / "models" / "v1"
REPORT_JSON = PROJECT_ROOT / "data" / "models" / "phase6_training_report.json"


def main() -> None:
    if not REPORT_JSON.is_file():
        print(f"Error: Training report not found: {REPORT_JSON}. Please run train_models.py first.", file=sys.stderr)
        sys.exit(1)

    with open(REPORT_JSON, "r", encoding="utf-8") as f:
        report = json.load(f)

    clf_rep = report["classifier"]
    reg_rep = report["regressor"]

    print("=" * 90)
    print("NIFTY AI — PHASE 6 MODEL EVALUATION & BASELINE COMPARISON REPORT")
    print("=" * 90)
    print(f"Development Window: {report['development_period']['start']} to {report['development_period']['end']} (N={report['development_period']['samples']})")
    print(f"Final Holdout Window: {report['holdout_period']['start']} to {report['holdout_period']['end']} (N={report['holdout_period']['samples']})")

    # 1. Classifier Diagnostics Table
    print("\n" + "=" * 90)
    print("DIRECTIONAL CLASSIFIER DIAGNOSTICS (3-CLASS: DOWN / SIDEWAYS / UP)")
    print("=" * 90)
    print(f"Frozen Parameters: {clf_rep['frozen_parameters']} | Final Trees (Median): {clf_rep['final_n_estimators']}")

    c_dev_oof = clf_rep["development_oof_calibrated_metrics"]
    c_dev_maj = clf_rep["development_majority_baseline"]
    c_hld = clf_rep["holdout_metrics"]
    c_hld_maj = clf_rep["holdout_majority_baseline"]

    header_c = f"{'Metric':<25} {'Dev OOF XGB':<14} {'Dev Majority':<14} {'Holdout XGB':<14} {'Holdout Maj':<14}"
    print(header_c)
    print("-" * 85)
    print(f"{'Log Loss':<25} {c_dev_oof['log_loss']:<14.5f} {c_dev_maj['log_loss']:<14.5f} {c_hld['log_loss']:<14.5f} {c_hld_maj['log_loss']:<14.5f}")
    print(f"{'Brier Score':<25} {c_dev_oof['brier_score']:<14.5f} {c_dev_maj['brier_score']:<14.5f} {c_hld['brier_score']:<14.5f} {c_hld_maj['brier_score']:<14.5f}")
    print(f"{'Accuracy (%)':<25} {c_dev_oof['accuracy']*100:<14.2f} {c_dev_maj['accuracy']*100:<14.2f} {c_hld['accuracy']*100:<14.2f} {c_hld_maj['accuracy']*100:<14.2f}")
    print(f"{'Macro F1':<25} {c_dev_oof['macro_f1']:<14.4f} {c_dev_maj['macro_f1']:<14.4f} {c_hld['macro_f1']:<14.4f} {c_hld_maj['macro_f1']:<14.4f}")
    print(f"{'ECE (Calibration Error)':<25} {c_dev_oof['expected_calibration_error']:<14.4f} {'N/A':<14} {c_hld['expected_calibration_error']:<14.4f} {'N/A':<14}")

    print("\nHoldout Per-Class Precision / Recall / F1:")
    for cls_name, p_dict in c_hld["per_class"].items():
        print(f"  {cls_name:<10}: Precision={p_dict['precision']:.3f}, Recall={p_dict['recall']:.3f}, F1={p_dict['f1']:.3f}, Support={p_dict['support']}")

    print(f"\nStatistical Significance vs Majority Baseline (Stationary Block Bootstrap):")
    boot = clf_rep["statistical_test_vs_baseline"]
    print(f"  {boot['interpretation']}")
    print(f"  Mean Log-Loss Reduction: {boot['mean_loss_diff']:+.5f} | 95% CI: [{boot['ci_lower']:+.5f}, {boot['ci_upper']:+.5f}] | Cohen's d: {boot['cohens_d']:.3f}")

    # 2. Regressor Diagnostics Table
    print("\n" + "=" * 90)
    print("RETURN REGRESSOR DIAGNOSTICS (NEXT-SESSION CLOSE-TO-CLOSE RETURN)")
    print("=" * 90)
    print(f"Frozen Parameters: {reg_rep['frozen_parameters']} | Final Trees (Median): {reg_rep['final_n_estimators']}")

    r_dev_oof = reg_rep["development_oof_metrics"]
    r_dev_zero = reg_rep["development_zero_baseline"]
    r_hld = reg_rep["holdout_metrics"]
    r_hld_zero = reg_rep["holdout_zero_baseline"]

    header_r = f"{'Metric':<25} {'Dev OOF XGB':<14} {'Dev Zero-Ret':<14} {'Holdout XGB':<14} {'Holdout Zero':<14}"
    print(header_r)
    print("-" * 85)
    print(f"{'MAE (%)':<25} {r_dev_oof['mae']*100:<14.4f} {r_dev_zero['mae']*100:<14.4f} {r_hld['mae']*100:<14.4f} {r_hld_zero['mae']*100:<14.4f}")
    print(f"{'RMSE (%)':<25} {r_dev_oof['rmse']*100:<14.4f} {r_dev_zero['rmse']*100:<14.4f} {r_hld['rmse']*100:<14.4f} {r_hld_zero['rmse']*100:<14.4f}")
    print(f"{'R² Score':<25} {r_dev_oof['r2_score']:<14.5f} {r_dev_zero['r2_score']:<14.5f} {r_hld['r2_score']:<14.5f} {r_hld_zero['r2_score']:<14.5f}")
    print(f"{'Pearson IC':<25} {r_dev_oof['pearson_ic']:<+14.4f} {'0.0000':<14} {r_hld['pearson_ic']:<+14.4f} {'0.0000':<14}")
    print(f"{'Directional Acc (%)':<25} {r_dev_oof['directional_accuracy']*100:<14.2f} {'0.00':<14} {r_hld['directional_accuracy']*100:<14.2f} {'0.00':<14}")

    print(f"\nStatistical Significance vs Zero-Return Baseline (Diebold-Mariano HAC Test):")
    dm = reg_rep["diebold_mariano_test_vs_zero"]
    print(f"  {dm['interpretation']}")
    print(f"  DM Statistic: {dm['hln_corrected_statistic']:+.4f} | p-value: {dm['hln_p_value']:.4f}")
    print(f"  Mean Absolute Loss Diff: {dm['mean_loss_diff']:+.6f} | 95% CI: [{dm['confidence_interval_95'][0]:+.6f}, {dm['confidence_interval_95'][1]:+.6f}]")


if __name__ == "__main__":
    main()
