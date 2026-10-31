"""Evaluation, validation, calibration, and statistical hypothesis testing for NIFTY AI."""

from nifty_ai.evaluation.calibration import (
    CalibrationBin,
    ClassCalibrationReport,
    PlattScaler,
    compute_reliability_report,
)
from nifty_ai.evaluation.classification_metrics import (
    ClassificationMetrics,
    compute_expected_calibration_error,
    evaluate_classification_metrics,
)
from nifty_ai.evaluation.regression_metrics import (
    RegressionMetrics,
    evaluate_regression_metrics,
)
from nifty_ai.evaluation.split import (
    WalkForwardFold,
    WalkForwardSplitter,
)
from nifty_ai.evaluation.statistical_tests import (
    BootstrapComparisonResult,
    DieboldMarianoResult,
    diebold_mariano_test,
    paired_bootstrap_loss_difference,
)

__all__ = [
    # Splitting
    "WalkForwardFold",
    "WalkForwardSplitter",
    # Classification Metrics
    "ClassificationMetrics",
    "compute_expected_calibration_error",
    "evaluate_classification_metrics",
    # Regression Metrics
    "RegressionMetrics",
    "evaluate_regression_metrics",
    # Calibration
    "CalibrationBin",
    "ClassCalibrationReport",
    "PlattScaler",
    "compute_reliability_report",
    # Statistical Tests
    "BootstrapComparisonResult",
    "DieboldMarianoResult",
    "diebold_mariano_test",
    "paired_bootstrap_loss_difference",
]
