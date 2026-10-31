"""Feature engineering pipeline for NIFTY AI.

Provides leakage-free historical price feature calculation, moving averages,
momentum, volatility, trend, and calendar feature extractions.
"""

from nifty_ai.features.registry import (
    FeatureDefinition,
    FeatureRegistry,
    build_default_feature_registry,
    default_feature_registry,
)
from nifty_ai.features.engine import (
    PriceFeatureEngine,
    linear_regression_slope,
)
from nifty_ai.features.pipeline import (
    FEATURES_DIR,
    FeaturePipeline,
)

__all__ = [
    "FeatureDefinition",
    "FeatureRegistry",
    "build_default_feature_registry",
    "default_feature_registry",
    "PriceFeatureEngine",
    "linear_regression_slope",
    "FEATURES_DIR",
    "FeaturePipeline",
]
