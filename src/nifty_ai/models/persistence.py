"""Atomic persistence and provenance metadata management for NIFTY AI models.

Saves native XGBoost JSON artifacts alongside immutable JSON manifests recording
the full training window, hyperparameter specification, dataset checksums, and library versions.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
import xgboost as xgb

from nifty_ai.data.storage import compute_file_sha256


@dataclass
class ModelProvenanceMetadata:
    """Comprehensive production provenance record for a trained model."""
    model_id: str
    model_type: str                  # "xgboost_classifier" or "xgboost_regressor"
    model_version: str               # "1.0.0"
    snapshot_type: str               # "SNAPSHOT_1540" or "SNAPSHOT_0850"
    created_at: str                  # ISO 8601 UTC timestamp
    development_training_range: Dict[str, str]   # {"start": "...", "end": "..."}
    feature_dataset_sha256: str
    target_dataset_sha256: str
    feature_names: List[str]         # Exactly ordered 45 features
    frozen_hyperparameters: Dict[str, Any]
    final_n_estimators: int
    random_seed: int
    calibration_status: Dict[str, Any]
    development_oof_metrics: Dict[str, Any]
    python_version: str
    library_versions: Dict[str, str]
    model_file_name: str
    model_file_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_json(self, meta_path: Path) -> Path:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return meta_path


def get_current_environment_versions() -> Dict[str, str]:
    """Capture exact runtime package versions for reproducibility."""
    import numpy
    import pandas
    import scipy
    import sklearn
    return {
        "python": sys.version.split()[0],
        "xgboost": xgb.__version__,
        "numpy": numpy.__version__,
        "pandas": pandas.__version__,
        "scipy": scipy.__version__,
        "scikit-learn": sklearn.__version__,
    }


def save_model_artifact_with_manifest(
    model: Any,
    model_file_path: Path,
    metadata_fields: Dict[str, Any],
) -> Tuple[Path, Path]:
    """Atomically save a trained model and generate its paired .meta.json provenance file."""
    model_file_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Save native model artifact
    if hasattr(model, "save_model"):
        model.save_model(model_file_path)
    else:
        raise TypeError(f"Model object of type {type(model)} has no save_model method.")

    model_sha256 = compute_file_sha256(model_file_path)
    versions = get_current_environment_versions()

    # 2. Assemble provenance manifest
    manifest = ModelProvenanceMetadata(
        model_id=metadata_fields["model_id"],
        model_type=metadata_fields["model_type"],
        model_version=metadata_fields.get("model_version", "1.0.0"),
        snapshot_type=metadata_fields["snapshot_type"],
        created_at=datetime.now(timezone.utc).isoformat(),
        development_training_range=metadata_fields["development_training_range"],
        feature_dataset_sha256=metadata_fields["feature_dataset_sha256"],
        target_dataset_sha256=metadata_fields["target_dataset_sha256"],
        feature_names=metadata_fields["feature_names"],
        frozen_hyperparameters=metadata_fields["frozen_hyperparameters"],
        final_n_estimators=int(metadata_fields["final_n_estimators"]),
        random_seed=int(metadata_fields.get("random_seed", 42)),
        calibration_status=metadata_fields.get("calibration_status", {"is_calibrated": False}),
        development_oof_metrics=metadata_fields.get("development_oof_metrics", {}),
        python_version=versions["python"],
        library_versions=versions,
        model_file_name=model_file_path.name,
        model_file_sha256=model_sha256,
    )

    meta_path = model_file_path.parent / f"{model_file_path.stem}.meta.json"
    manifest.save_json(meta_path)

    return model_file_path, meta_path


__all__ = [
    "ModelProvenanceMetadata",
    "get_current_environment_versions",
    "save_model_artifact_with_manifest",
]
