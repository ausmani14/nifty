"""Comprehensive classification evaluation metrics and proper scoring rules for NIFTY AI.

Calculates:
- Multiclass Log Loss (Cross-Entropy)
- Multiclass Brier Score: (1/N) * sum_i sum_c (P_ic - y_ic)^2
- Expected Calibration Error (ECE)
- Accuracy, Macro F1, Weighted F1
- Per-class Precision, Recall, and F1 (DOWN, SIDEWAYS, UP)
- 3x3 Confusion Matrix
"""

from dataclasses import asdict, dataclass
import math
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_recall_fscore_support,
)

from nifty_ai.models.dataset import INV_CLASS_MAP


@dataclass
class ClassificationMetrics:
    """Comprehensive performance metrics for directional 3-class prediction."""
    total_samples: int
    log_loss: float
    brier_score: float
    expected_calibration_error: float
    accuracy: float
    macro_f1: float
    weighted_f1: float
    per_class: Dict[str, Dict[str, float]]
    confusion_matrix: List[List[int]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_expected_calibration_error(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> float:
    """Compute Expected Calibration Error (ECE) across maximum class confidence bins."""
    confidences = np.max(y_prob, axis=1)
    predictions = np.argmax(y_prob, axis=1)
    accuracies = (predictions == y_true).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(y_true)

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper) if i > 0 else (confidences >= bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if prop_in_bin > 0:
            accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_confidence_in_bin - accuracy_in_bin) * prop_in_bin

    return float(ece)


def evaluate_classification_metrics(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    y_pred: Optional[np.ndarray] = None,
) -> ClassificationMetrics:
    """Compute complete suite of classification metrics and proper scoring rules.

    Args:
        y_true: True integer class labels in {0, 1, 2}.
        y_prob: Predicted probability simplex of shape (N, 3).
        y_pred: Optional integer predictions. If None, derived as argmax(y_prob).

    Returns:
        ClassificationMetrics instance.
    """
    y_true = np.asarray(y_true, dtype=np.int64)
    y_prob = np.asarray(y_prob, dtype=np.float64)

    # Probability simplex normalization safeguard
    y_prob = y_prob / np.sum(y_prob, axis=1, keepdims=True)

    if y_pred is None:
        y_pred = np.argmax(y_prob, axis=1)
    else:
        y_pred = np.asarray(y_pred, dtype=np.int64)

    n = len(y_true)
    eps = 1e-15
    clipped_prob = np.clip(y_prob, eps, 1.0 - eps)

    # 1. Log Loss
    ll = float(log_loss(y_true, clipped_prob, labels=[0, 1, 2]))

    # 2. Multiclass Brier Score: (1/N) * sum_i sum_c (P_ic - y_ic)^2
    one_hot_true = np.zeros_like(y_prob)
    one_hot_true[np.arange(n), y_true] = 1.0
    brier = float(np.mean(np.sum((y_prob - one_hot_true) ** 2, axis=1)))

    # 3. Expected Calibration Error
    ece = compute_expected_calibration_error(y_true, y_prob, n_bins=10)

    # 4. Accuracy
    acc = float(accuracy_score(y_true, y_pred))

    # 5. Macro and Weighted F1
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, average="weighted", zero_division=0))

    # 6. Per-class metrics
    prec, rec, f1_vals, support = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2], zero_division=0
    )
    per_class = {}
    for c_id in [0, 1, 2]:
        name = INV_CLASS_MAP[c_id]
        per_class[name] = {
            "precision": float(round(prec[c_id], 4)),
            "recall": float(round(rec[c_id], 4)),
            "f1": float(round(f1_vals[c_id], 4)),
            "support": int(support[c_id]),
        }

    # 7. Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist()

    return ClassificationMetrics(
        total_samples=n,
        log_loss=round(ll, 5),
        brier_score=round(brier, 5),
        expected_calibration_error=round(ece, 5),
        accuracy=round(acc, 4),
        macro_f1=round(macro_f1, 4),
        weighted_f1=round(weighted_f1, 4),
        per_class=per_class,
        confusion_matrix=cm,
    )


__all__ = [
    "ClassificationMetrics",
    "compute_expected_calibration_error",
    "evaluate_classification_metrics",
]
