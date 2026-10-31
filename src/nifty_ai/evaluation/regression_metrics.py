"""Comprehensive regression evaluation metrics for next-session return predictions.

Calculates:
- Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE)
- Coefficient of Determination (R^2)
- Pearson Information Coefficient (IC) & Spearman Rank IC
- Directional Agreement: sign(pred) == sign(true)
- Residual error distribution diagnostics (bias, variance, skewness, kurtosis)
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, Optional
import numpy as np
from scipy import stats
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


@dataclass
class RegressionMetrics:
    """Performance and residual distribution metrics for continuous return prediction."""
    total_samples: int
    mae: float
    rmse: float
    r2_score: float
    pearson_ic: float
    pearson_ic_pvalue: float
    spearman_ic: float
    spearman_ic_pvalue: float
    directional_accuracy: float
    mean_error: float
    error_stdev: float
    error_skewness: float
    error_kurtosis: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_regression_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> RegressionMetrics:
    """Compute full suite of statistical and financial regression metrics.

    Args:
        y_true: Realized next-session close-to-close returns.
        y_pred: Predicted next-session close-to-close returns.

    Returns:
        RegressionMetrics instance.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)

    n = len(y_true)
    if n == 0:
        raise ValueError("Cannot evaluate regression metrics on empty arrays.")

    # 1. Error metrics
    mae = float(mean_absolute_error(y_true, y_pred))
    mse = float(mean_squared_error(y_true, y_pred))
    rmse = float(math.sqrt(mse))

    # 2. R^2 score
    r2 = float(r2_score(y_true, y_pred))

    # 3. Information Coefficient (Pearson and Spearman)
    # Check for constant arrays before computing correlations
    if np.all(y_pred == y_pred[0]) or np.all(y_true == y_true[0]):
        pearson_ic = 0.0
        pearson_pval = 1.0
        spearman_ic = 0.0
        spearman_pval = 1.0
    else:
        p_res = stats.pearsonr(y_pred, y_true)
        pearson_ic = float(p_res.statistic)
        pearson_pval = float(p_res.pvalue)

        s_res = stats.spearmanr(y_pred, y_true)
        spearman_ic = float(s_res.statistic)
        spearman_pval = float(s_res.pvalue)

    # 4. Directional Accuracy
    # Both strictly positive or both strictly negative or both zero
    sign_true = np.sign(y_true)
    sign_pred = np.sign(y_pred)
    dir_acc = float(np.mean(sign_true == sign_pred))

    # 5. Residual Distribution Analysis (e = y_pred - y_true)
    errors = y_pred - y_true
    mean_err = float(np.mean(errors))
    stdev_err = float(np.std(errors, ddof=1)) if n > 1 else 0.0
    skew_err = float(stats.skew(errors)) if n > 2 else 0.0
    kurt_err = float(stats.kurtosis(errors)) if n > 3 else 0.0

    return RegressionMetrics(
        total_samples=n,
        mae=round(mae, 6),
        rmse=round(rmse, 6),
        r2_score=round(r2, 6),
        pearson_ic=round(pearson_ic, 5),
        pearson_ic_pvalue=round(pearson_pval, 6),
        spearman_ic=round(spearman_ic, 5),
        spearman_ic_pvalue=round(spearman_pval, 6),
        directional_accuracy=round(dir_acc, 4),
        mean_error=round(mean_err, 6),
        error_stdev=round(stdev_err, 6),
        error_skewness=round(skew_err, 4),
        error_kurtosis=round(kurt_err, 4),
    )


__all__ = ["RegressionMetrics", "evaluate_regression_metrics"]
