"""Classification target generation engine for NIFTY AI.

Maps continuous next-session returns into 3-class categorical outcomes:
- UP: target_return > +theta
- DOWN: target_return < -theta
- SIDEWAYS: -theta <= target_return <= +theta
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import List, Optional

from nifty_ai.targets.returns import TargetReturn
from nifty_ai.targets.thresholds import ThresholdResult


class DirectionLabel(str, Enum):
    """3-class directional target categories."""
    UP = "UP"
    DOWN = "DOWN"
    SIDEWAYS = "SIDEWAYS"


def classify_return(target_return: float, threshold: float) -> DirectionLabel:
    """Classify a continuous return against a symmetric boundary threshold theta.

    Args:
        target_return: Next-session close-to-close return.
        threshold: Non-negative threshold value theta.

    Returns:
        DirectionLabel.UP, DirectionLabel.DOWN, or DirectionLabel.SIDEWAYS.
    """
    if threshold < 0:
        raise ValueError(f"Threshold must be non-negative, got {threshold}")

    if target_return > threshold:
        return DirectionLabel.UP
    elif target_return < -threshold:
        return DirectionLabel.DOWN
    else:
        return DirectionLabel.SIDEWAYS


@dataclass(frozen=True)
class ClassifiedTarget:
    """Fully reconciled target row combining regression and classification labels."""
    trading_date: date
    close: float
    target_date: Optional[date]
    target_close: Optional[float]
    target_return: Optional[float]
    threshold_method: str
    threshold_value: Optional[float]
    target_direction: Optional[DirectionLabel]
    has_target: bool
    has_threshold: bool
    is_classified: bool


def classify_targets(
    target_returns: List[TargetReturn],
    threshold_results: List[ThresholdResult],
) -> List[ClassifiedTarget]:
    """Join target returns with rolling thresholds to produce classified targets.

    Args:
        target_returns: Output of compute_next_session_returns.
        threshold_results: Output of compute_rolling_thresholds.

    Returns:
        List of ClassifiedTarget aligned 1:1 with input records.
    """
    if len(target_returns) != len(threshold_results):
        raise ValueError(
            f"Mismatched lengths: target_returns ({len(target_returns)}) vs threshold_results ({len(threshold_results)})"
        )

    classified: List[ClassifiedTarget] = []

    for tr, thr in zip(target_returns, threshold_results):
        if tr.trading_date != thr.trading_date:
            raise ValueError(
                f"Date alignment mismatch: return date {tr.trading_date} != threshold date {thr.trading_date}"
            )

        has_target = (tr.target_return is not None)
        has_threshold = (thr.threshold_value is not None)

        if has_target and has_threshold:
            direction = classify_return(tr.target_return, thr.threshold_value)  # type: ignore[arg-type]
            is_classified = True
        else:
            direction = None
            is_classified = False

        classified.append(
            ClassifiedTarget(
                trading_date=tr.trading_date,
                close=tr.close,
                target_date=tr.target_date,
                target_close=tr.target_close,
                target_return=tr.target_return,
                threshold_method=thr.method_name,
                threshold_value=thr.threshold_value,
                target_direction=direction,
                has_target=has_target,
                has_threshold=has_threshold,
                is_classified=is_classified,
            )
        )

    return classified


__all__ = [
    "DirectionLabel",
    "classify_return",
    "ClassifiedTarget",
    "classify_targets",
]
