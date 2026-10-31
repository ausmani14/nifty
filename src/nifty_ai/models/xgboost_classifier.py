"""XGBoost 3-class directional classifier implementation for NIFTY AI.

Implements multi:softprob objective function predicting:
0: DOWN, 1: SIDEWAYS, 2: UP
with strict probability simplex normalization, deterministic seeding, and native JSON serialization.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import xgboost as xgb

from nifty_ai.models.base import BaseDirectionClassifier


class XGBoostDirectionClassifier(BaseDirectionClassifier):
    """Production 3-class XGBoost classifier for directional price prediction."""

    def __init__(
        self,
        learning_rate: float = 0.05,
        max_depth: int = 3,
        min_child_weight: float = 15.0,
        n_estimators: int = 150,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        early_stopping_rounds: Optional[int] = None,
        random_state: int = 42,
    ) -> None:
        self._params: Dict[str, Any] = {
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "min_child_weight": min_child_weight,
            "n_estimators": n_estimators,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "early_stopping_rounds": early_stopping_rounds,
            "random_state": random_state,
        }
        self._early_stopping_rounds = early_stopping_rounds
        self._random_state = random_state

        xgb_kwargs: Dict[str, Any] = {
            "objective": "multi:softprob",
            "num_class": 3,
            "eval_metric": "mlogloss",
            "learning_rate": learning_rate,
            "max_depth": max_depth,
            "min_child_weight": min_child_weight,
            "n_estimators": n_estimators,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "random_state": random_state,
            "tree_method": "hist",
            "n_jobs": 1,
        }
        if early_stopping_rounds is not None:
            xgb_kwargs["early_stopping_rounds"] = early_stopping_rounds

        self._clf = xgb.XGBClassifier(**xgb_kwargs)
        self.is_fitted: bool = False

    @property
    def model_type(self) -> str:
        return "xgboost_classifier"

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        return dict(self._params)

    @property
    def best_iteration(self) -> Optional[int]:
        if hasattr(self._clf, "best_iteration") and self._clf.best_iteration is not None:
            return int(self._clf.best_iteration)
        return None

    @property
    def num_trees(self) -> Optional[int]:
        """Return the exact number of boosting rounds in the fitted booster."""
        if hasattr(self._clf, "get_booster"):
            try:
                return int(self._clf.get_booster().num_boosted_rounds())
            except Exception:
                pass
        return None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "XGBoostDirectionClassifier":
        """Train the classifier on feature matrix X and labels y."""
        fit_kwargs: Dict[str, Any] = {"verbose": verbose}
        if sample_weight is not None:
            fit_kwargs["sample_weight"] = sample_weight
        if eval_set is not None:
            fit_kwargs["eval_set"] = eval_set

        self._clf.fit(X, y, **fit_kwargs)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels in {0: DOWN, 1: SIDEWAYS, 2: UP}."""
        probs = self.predict_proba(X)
        return np.argmax(probs, axis=1).astype(np.int64)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict calibrated 3-class probability simplex."""
        raw_probs = self._clf.predict_proba(X)
        # Enforce exact probability simplex (sum to 1.0)
        norm_probs = raw_probs / np.sum(raw_probs, axis=1, keepdims=True)
        return norm_probs.astype(np.float64)

    def save_model(self, file_path: Path) -> Path:
        """Save native XGBoost JSON model artifact."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self._clf.save_model(str(file_path))
        return file_path

    def load_model(self, file_path: Path) -> "XGBoostDirectionClassifier":
        """Load native XGBoost JSON model artifact."""
        self._clf.load_model(str(file_path))
        self.is_fitted = True
        return self


__all__ = ["XGBoostDirectionClassifier"]
