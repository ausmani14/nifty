"""Target specification registry and metadata catalog for NIFTY AI.

Documents formal definitions, mathematical formulas, prediction horizons,
snapshot applicability, threshold parameters, and anti-leakage controls for targets.
"""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass(frozen=True)
class TargetDefinition:
    """Immutable specification of an individual prediction target."""
    name: str
    category: str  # "regression" or "classification"
    mathematical_definition: str
    horizon: str
    snapshot_applicability: List[str]
    information_cutoff: str
    threshold_methodology: Optional[str]
    parameters: Dict[str, Any]
    warmup_requirements: int
    version: str
    leakage_controls: List[str]
    description: str


class TargetRegistry:
    """Catalog of all registered prediction targets in NIFTY AI."""

    def __init__(self) -> None:
        self._targets: Dict[str, TargetDefinition] = {}

    def register(self, target: TargetDefinition) -> None:
        self._targets[target.name] = target

    def get(self, name: str) -> TargetDefinition:
        if name not in self._targets:
            raise KeyError(f"Target '{name}' not found in registry.")
        return self._targets[name]

    def list_all(self) -> List[TargetDefinition]:
        return list(self._targets.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_count": len(self._targets),
            "targets": {t.name: asdict(t) for t in self._targets.values()},
        }

    def save_yaml(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, sort_keys=False, indent=2)
        return path


def build_default_target_registry(
    method_name: str = "volatility_scaled",
    parameters: Optional[Dict[str, Any]] = None,
) -> TargetRegistry:
    """Construct standard V1 target registry documenting regression and classification targets."""
    registry = TargetRegistry()
    params = parameters or {"k": 0.35, "window": 20}

    # 1. Regression target: Next-session close-to-close return
    registry.register(
        TargetDefinition(
            name="target_return",
            category="regression",
            mathematical_definition="Close_(T+1) / Close_T - 1",
            horizon="next_trading_session (T+1)",
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            information_cutoff="Outcome finalized at 15:30 IST on Day T+1",
            threshold_methodology=None,
            parameters={},
            warmup_requirements=0,
            version="1.0.0",
            leakage_controls=[
                "Shifted strictly forward (+1 session)",
                "Last historical session target is None (never fabricated)",
                "Zero clipping or winsorization applied",
                "Completely inaccessible to feature generation on Day T",
            ],
            description="Continuous close-to-close percentage price return of next trading session.",
        )
    )

    # 2. Classification target: 3-class direction label (UP / DOWN / SIDEWAYS)
    registry.register(
        TargetDefinition(
            name="target_direction",
            category="classification",
            mathematical_definition=(
                "UP if target_return > +theta_T; "
                "DOWN if target_return < -theta_T; "
                "SIDEWAYS if -theta_T <= target_return <= +theta_T"
            ),
            horizon="next_trading_session (T+1)",
            snapshot_applicability=["SNAPSHOT_1540", "SNAPSHOT_0850"],
            information_cutoff="Outcome finalized at 15:30 IST on Day T+1; theta_T finalized by cutoff of T",
            threshold_methodology=method_name,
            parameters=params,
            warmup_requirements=int(params.get("window", 20)),
            version="1.0.0",
            leakage_controls=[
                "Dynamic threshold theta_T computed using strictly trailing returns available up to cutoff T",
                "No global future returns or holdout test returns used in threshold estimation",
                "Exact symmetric boundary assignment",
                "Unclassifiable during warm-up period (first window bars)",
                "Terminal row has None direction label",
            ],
            description="3-class directional movement label incorporating dynamic volatility-calibrated threshold.",
        )
    )

    return registry


default_target_registry = build_default_target_registry()

__all__ = [
    "TargetDefinition",
    "TargetRegistry",
    "build_default_target_registry",
    "default_target_registry",
]
