"""Transparent reference baseline models for NIFTY AI.

Implements benchmark models against which XGBoost must demonstrate empirical improvement:
- Classification: Expanding Majority Class, Trailing Direction Persistence, Uniform Random
- Regression: Zero-Return Martingale, Expanding Mean Return, Trailing Persistence Return
"""

from typing import Any, Dict, List, Optional
import numpy as np

from nifty_ai.models.base import BaseDirectionClassifier, BaseReturnRegressor


class ExpandingMajorityClassifier(BaseDirectionClassifier):
    """Predicts the empirical majority class from training history with training class probabilities."""

    def __init__(self) -> None:
        self._majority_class: int = 2  # Default to UP
        self._class_probs: np.ndarray = np.array([1/3, 1/3, 1/3], dtype=np.float64)

    @property
    def model_type(self) -> str:
        return "baseline_majority_class"

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        return {}

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "ExpandingMajorityClassifier":
        counts = np.bincount(y, minlength=3)
        self._majority_class = int(np.argmax(counts))
        self._class_probs = (counts / np.sum(counts)).astype(np.float64)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full(X.shape[0], self._majority_class, dtype=np.int64)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.tile(self._class_probs, (X.shape[0], 1))


class TrailingPersistenceClassifier(BaseDirectionClassifier):
    """Predicts next-session direction continuing yesterday's realized direction.

    Uses feature ret_1d (index 0) compared against 0 to infer past session sign.
    """

    @property
    def model_type(self) -> str:
        return "baseline_direction_persistence"

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        return {}

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "TrailingPersistenceClassifier":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        # ret_1d is at index 0 of features
        ret_1d = X[:, 0]
        preds = np.full(X.shape[0], 1, dtype=np.int64)  # Default SIDEWAYS
        preds[ret_1d > 0.0035] = 2   # UP
        preds[ret_1d < -0.0035] = 0  # DOWN
        return preds

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        preds = self.predict(X)
        probs = np.full((X.shape[0], 3), 0.1, dtype=np.float64)
        for i, p in enumerate(preds):
            probs[i, p] = 0.8
        return probs / np.sum(probs, axis=1, keepdims=True)


class UniformRandomClassifier(BaseDirectionClassifier):
    """Naive maximum entropy baseline predicting uniform 1/3 probabilities."""

    @property
    def model_type(self) -> str:
        return "baseline_uniform_random"

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        return {}

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "UniformRandomClassifier":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full(X.shape[0], 1, dtype=np.int64)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.full((X.shape[0], 3), 1.0 / 3.0, dtype=np.float64)


class ZeroReturnRegressor(BaseReturnRegressor):
    """Martingale baseline predicting exactly zero return for every next trading session."""

    @property
    def model_type(self) -> str:
        return "baseline_zero_return"

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        return {}

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "ZeroReturnRegressor":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.zeros(X.shape[0], dtype=np.float64)


class ExpandingMeanReturnRegressor(BaseReturnRegressor):
    """Predicts the expanding historical average daily return."""

    def __init__(self) -> None:
        self._mean_return: float = 0.0

    @property
    def model_type(self) -> str:
        return "baseline_expanding_mean"

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        return {}

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "ExpandingMeanReturnRegressor":
        self._mean_return = float(np.mean(y))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.full(X.shape[0], self._mean_return, dtype=np.float64)


class TrailingPersistenceRegressor(BaseReturnRegressor):
    """Predicts yesterday's realized daily return as tomorrow's return."""

    @property
    def model_type(self) -> str:
        return "baseline_return_persistence"

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        return {}

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "TrailingPersistenceRegressor":
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        # ret_1d is at column index 0
        return X[:, 0].astype(np.float64)


__all__ = [
    "ExpandingMajorityClassifier",
    "TrailingPersistenceClassifier",
    "UniformRandomClassifier",
    "ZeroReturnRegressor",
    "ExpandingMeanReturnRegressor",
    "TrailingPersistenceRegressor",
]
