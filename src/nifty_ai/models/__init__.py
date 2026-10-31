"""Model architectures, base protocols, baselines, and persistence for NIFTY AI."""

from nifty_ai.models.base import (
    BaseDirectionClassifier,
    BaseReturnRegressor,
    ClassificationPrediction,
    RegressionPrediction,
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
from nifty_ai.models.persistence import (
    ModelProvenanceMetadata,
    get_current_environment_versions,
    save_model_artifact_with_manifest,
)
from nifty_ai.models.xgboost_classifier import XGBoostDirectionClassifier
from nifty_ai.models.xgboost_regressor import XGBoostReturnRegressor

__all__ = [
    # Base
    "BaseDirectionClassifier",
    "BaseReturnRegressor",
    "ClassificationPrediction",
    "RegressionPrediction",
    # Dataset
    "CLASS_MAP",
    "INV_CLASS_MAP",
    "EXPECTED_FEATURE_NAMES",
    "AlignedDataset",
    "load_aligned_dataset",
    # Baselines
    "ExpandingMajorityClassifier",
    "TrailingPersistenceClassifier",
    "UniformRandomClassifier",
    "ZeroReturnRegressor",
    "ExpandingMeanReturnRegressor",
    "TrailingPersistenceRegressor",
    # XGBoost
    "XGBoostDirectionClassifier",
    "XGBoostReturnRegressor",
    # Persistence
    "ModelProvenanceMetadata",
    "get_current_environment_versions",
    "save_model_artifact_with_manifest",
]
