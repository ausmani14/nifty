"""Base protocols, abstractions, and prediction dataclasses for NIFTY AI models.

Defines decoupled interfaces for 3-class directional classification and continuous
return regression, ensuring estimators can be swapped or evaluated uniformly.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass(frozen=True)
class ClassificationPrediction:
    """Standardized output container for directional classification predictions."""
    prediction_date: date            # Target session T+1 (or T for morning)
    cutoff_date: date                # Feature cutoff session T
    predicted_class: str             # "UP", "DOWN", or "SIDEWAYS"
    predicted_class_id: int          # 0: DOWN, 1: SIDEWAYS, 2: UP
    probability_down: float          # P(DOWN)
    probability_sideways: float      # P(SIDEWAYS)
    probability_up: float            # P(UP)
    max_probability: float           # max(P) - confidence proxy
    model_version: str
    model_id: str


@dataclass(frozen=True)
class RegressionPrediction:
    """Standardized output container for continuous return regression predictions."""
    prediction_date: date            # Target session T+1 (or T for morning)
    cutoff_date: date                # Feature cutoff session T
    predicted_return: float          # Expected close-to-close return r_{T+1}
    predicted_close: float           # Close_T * (1 + predicted_return)
    reference_close: float           # Close_T
    model_version: str
    model_id: str


class BaseDirectionClassifier(ABC):
    """Abstract interface for next-session directional movement classifiers."""

    @property
    @abstractmethod
    def model_type(self) -> str:
        """Name/type of the model architecture."""
        pass

    @property
    @abstractmethod
    def hyperparameters(self) -> Dict[str, Any]:
        """Dictionary of model hyperparameters."""
        pass

    @abstractmethod
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "BaseDirectionClassifier":
        """Train classifier on feature matrix X and integer class labels y (0, 1, 2)."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict integer class labels (0: DOWN, 1: SIDEWAYS, 2: UP)."""
        pass

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict calibrated class probability simplex (N x 3)."""
        pass


class BaseReturnRegressor(ABC):
    """Abstract interface for next-session close-to-close return regressors."""

    @property
    @abstractmethod
    def model_type(self) -> str:
        """Name/type of the model architecture."""
        pass

    @property
    @abstractmethod
    def hyperparameters(self) -> Dict[str, Any]:
        """Dictionary of model hyperparameters."""
        pass

    @abstractmethod
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "BaseReturnRegressor":
        """Train regressor on feature matrix X and continuous percentage returns y."""
        pass

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict continuous percentage returns."""
        pass


__all__ = [
    "ClassificationPrediction",
    "RegressionPrediction",
    "BaseDirectionClassifier",
    "BaseReturnRegressor",
]
