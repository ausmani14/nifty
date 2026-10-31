"""Target creation, threshold selection, and labeling package for NIFTY AI."""

from nifty_ai.targets.analysis import (
    AnalysisReport,
    MethodEvaluation,
    PeriodDistribution,
    ThresholdAnalyzer,
    VolatilityRegimeAnalysis,
)
from nifty_ai.targets.classification import (
    ClassifiedTarget,
    DirectionLabel,
    classify_return,
    classify_targets,
)
from nifty_ai.targets.pipeline import (
    TARGETS_DIR,
    TargetPipeline,
)
from nifty_ai.targets.registry import (
    TargetDefinition,
    TargetRegistry,
    build_default_target_registry,
    default_target_registry,
)
from nifty_ai.targets.returns import (
    TargetReturn,
    compute_next_session_returns,
)
from nifty_ai.targets.thresholds import (
    EmpiricalDistributionThreshold,
    FixedThreshold,
    ThresholdMethod,
    ThresholdResult,
    VolatilityScaledThreshold,
    compute_rolling_thresholds,
)

__all__ = [
    # Returns
    "TargetReturn",
    "compute_next_session_returns",
    # Thresholds
    "ThresholdResult",
    "ThresholdMethod",
    "VolatilityScaledThreshold",
    "EmpiricalDistributionThreshold",
    "FixedThreshold",
    "compute_rolling_thresholds",
    # Classification
    "DirectionLabel",
    "classify_return",
    "ClassifiedTarget",
    "classify_targets",
    # Analysis
    "PeriodDistribution",
    "VolatilityRegimeAnalysis",
    "MethodEvaluation",
    "AnalysisReport",
    "ThresholdAnalyzer",
    # Pipeline
    "TARGETS_DIR",
    "TargetPipeline",
    # Registry
    "TargetDefinition",
    "TargetRegistry",
    "build_default_target_registry",
    "default_target_registry",
]
