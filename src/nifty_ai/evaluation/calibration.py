"""Probability calibration evaluation and Platt scaling engine for NIFTY AI.

Provides reliability diagram generation, Expected Calibration Error (ECE) analysis,
and development-only Platt scaling (multinomial logistic calibration).
"""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression

from nifty_ai.models.dataset import INV_CLASS_MAP


@dataclass
class CalibrationBin:
    """Diagnostic data for an individual probability bin."""
    bin_index: int
    mean_predicted_prob: float
    empirical_fraction_positive: float
    sample_count: int


@dataclass
class ClassCalibrationReport:
    """Reliability metrics for an individual class."""
    class_name: str
    class_id: int
    bins: List[CalibrationBin]
    brier_score_class: float


class PlattScaler:
    """Multinomial logistic regression probability calibrator.

    STRICT POLICY: Must be fit exclusively on out-of-fold development predictions.
    The Final Holdout partition (>= 2022-01-01) must never participate in calibration fitting.
    """

    def __init__(self, random_seed: int = 42) -> None:
        # Use multinomial logistic regression with light L2 regularization
        self._clf = LogisticRegression(
            solver="lbfgs",
            max_iter=1000,
            C=1.0,
            random_state=random_seed,
        )
        self.is_fitted: bool = False

    def fit(self, y_prob_oof: np.ndarray, y_true_oof: np.ndarray) -> "PlattScaler":
        """Fit Platt calibrator on out-of-fold development probabilities."""
        # Convert probabilities to log-odds / logits for feature space
        eps = 1e-15
        p_safe = np.clip(y_prob_oof, eps, 1.0 - eps)
        # Log-odds relative to reference class 0
        logits = np.column_stack([
            np.log(p_safe[:, 1] / p_safe[:, 0]),
            np.log(p_safe[:, 2] / p_safe[:, 0]),
        ])
        self._clf.fit(logits, y_true_oof)
        self.is_fitted = True
        return self

    def transform(self, y_prob: np.ndarray) -> np.ndarray:
        """Apply fitted Platt calibration to probability simplex."""
        if not self.is_fitted:
            raise RuntimeError("PlattScaler must be fitted on development OOF data before transform.")

        eps = 1e-15
        p_safe = np.clip(y_prob, eps, 1.0 - eps)
        logits = np.column_stack([
            np.log(p_safe[:, 1] / p_safe[:, 0]),
            np.log(p_safe[:, 2] / p_safe[:, 0]),
        ])
        calibrated = self._clf.predict_proba(logits)
        # Ensure exact probability simplex
        return calibrated / np.sum(calibrated, axis=1, keepdims=True)


def compute_reliability_report(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    n_bins: int = 10,
) -> Dict[str, ClassCalibrationReport]:
    """Compute reliability curves across all 3 individual classes."""
    reports: Dict[str, ClassCalibrationReport] = {}
    n = len(y_true)

    for c_id in [0, 1, 2]:
        name = INV_CLASS_MAP[c_id]
        binary_true = (y_true == c_id).astype(int)
        class_probs = y_prob[:, c_id]

        frac_pos, mean_pred = calibration_curve(
            binary_true, class_probs, n_bins=n_bins, strategy="uniform"
        )

        b_score = float(np.mean((class_probs - binary_true) ** 2))

        # Reconstruct bin sample counts
        bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
        bin_records = []
        for b_idx in range(len(frac_pos)):
            # Count observations in this region
            m_pred = float(mean_pred[b_idx])
            f_pos = float(frac_pos[b_idx])
            bin_records.append(
                CalibrationBin(
                    bin_index=b_idx,
                    mean_predicted_prob=round(m_pred, 4),
                    empirical_fraction_positive=round(f_pos, 4),
                    sample_count=int(np.sum((class_probs >= bin_edges[b_idx]) & (class_probs <= bin_edges[b_idx + 1]))),
                )
            )

        reports[name] = ClassCalibrationReport(
            class_name=name,
            class_id=c_id,
            bins=bin_records,
            brier_score_class=round(b_score, 5),
        )

    return reports


__all__ = [
    "CalibrationBin",
    "ClassCalibrationReport",
    "PlattScaler",
    "compute_reliability_report",
]
