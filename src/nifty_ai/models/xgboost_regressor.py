"""XGBoost continuous return regressor implementation for NIFTY AI.

Implements reg:squarederror objective function predicting:
next-session close-to-close percentage return r_{T+1},
with derived closing price calculation: Close_T * (1 + r_{T+1}).
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import xgboost as xgb

from nifty_ai.models.base import BaseReturnRegressor


class XGBoostReturnRegressor(BaseReturnRegressor):
    """Production XGBoost regressor for next-session close-to-close return prediction."""

    def __init__(
        self,
        learning_rate: float = 0.03,
        max_depth: int = 3,
        min_child_weight: float = 20.0,
        n_estimators: int = 150,
        subsample: float = 0.8,
        colsample_bytree: float = 0.7,
        reg_alpha: float = 0.5,
        reg_lambda: float = 2.0,
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
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
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

        self._reg = xgb.XGBRegressor(**xgb_kwargs)
        self.is_fitted: bool = False

    @property
    def model_type(self) -> str:
        return "xgboost_regressor"

    @property
    def hyperparameters(self) -> Dict[str, Any]:
        return dict(self._params)

    @property
    def best_iteration(self) -> Optional[int]:
        if hasattr(self._reg, "best_iteration") and self._reg.best_iteration is not None:
            return int(self._reg.best_iteration)
        return None

    @property
    def num_trees(self) -> Optional[int]:
        """Return the exact number of boosting rounds in the fitted booster."""
        if hasattr(self._reg, "get_booster"):
            try:
                return int(self._reg.get_booster().num_boosted_rounds())
            except Exception:
                pass
        return None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        eval_set: Optional[List[tuple]] = None,
        verbose: bool = False,
    ) -> "XGBoostReturnRegressor":
        """Train the regressor on feature matrix X and continuous returns y."""
        fit_kwargs: Dict[str, Any] = {"verbose": verbose}
        if eval_set is not None:
            fit_kwargs["eval_set"] = eval_set

        self._reg.fit(X, y, **fit_kwargs)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict continuous percentage returns."""
        preds = self._reg.predict(X)
        return preds.astype(np.float64)

    def predict_close(self, X: np.ndarray, reference_close: np.ndarray) -> np.ndarray:
        """Derive predicted next-session closing prices: Close_T * (1 + predicted_return)."""
        returns = self.predict(X)
        ref_c = np.asarray(reference_close, dtype=np.float64)
        return ref_c * (1.0 + returns)

    def save_model(self, file_path: Path) -> Path:
        """Save native XGBoost JSON model artifact."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        self._reg.save_model(str(file_path))
        return file_path

    def load_model(self, file_path: Path) -> "XGBoostReturnRegressor":
        """Load native XGBoost JSON model artifact."""
        self._reg.load_model(str(file_path))
        self.is_fitted = True
        return self


__all__ = ["XGBoostReturnRegressor"]
