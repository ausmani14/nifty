"""Frozen model inference runner for Phase 14 Shadow System.

Enforces model cryptographic authentication, immutable feature alignment,
full precision preservation, and fail-closed execution semantics.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np
import xgboost as xgb

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    CANONICAL_META_SHA256,
    CANONICAL_MODEL_SHA256,
    FeatureVector,
    ShadowPrediction,
    ValidationReport,
)

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "phase13_steps2_4"
    / "models"
    / "snapshot_b_t0_primary_model.json"
)
DEFAULT_META_PATH = (
    PROJECT_ROOT
    / "data"
    / "interim"
    / "phase13_steps2_4"
    / "models"
    / "snapshot_b_t0_primary_model.meta.json"
)


def compute_file_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_frozen_model_artifacts(
    model_path: Path = DEFAULT_MODEL_PATH,
    meta_path: Path = DEFAULT_META_PATH,
) -> Dict[str, Any]:
    """Verify cryptographic hash and configuration integrity of frozen model."""
    if not model_path.exists():
        raise FileNotFoundError(f"Frozen model artifact missing: {model_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Frozen model metadata missing: {meta_path}")

    actual_model_hash = compute_file_sha256(model_path)
    if actual_model_hash != CANONICAL_MODEL_SHA256:
        raise ValueError(
            f"Frozen model binary hash mismatch: {actual_model_hash} != {CANONICAL_MODEL_SHA256}"
        )

    actual_meta_hash = compute_file_sha256(meta_path)
    if actual_meta_hash != CANONICAL_META_SHA256:
        raise ValueError(
            f"Frozen model metadata hash mismatch: {actual_meta_hash} != {CANONICAL_META_SHA256}"
        )

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if meta.get("feature_count") != 63:
        raise ValueError(f"Expected 63 features in metadata, found {meta.get('feature_count')}")

    if tuple(meta.get("features", [])) != CANONICAL_FEATURES_63:
        raise ValueError("Metadata feature sequence does not match canonical 63 features.")

    if meta.get("hyperparameters", {}).get("n_estimators") != 43:
        raise ValueError("Model n_estimators is not frozen to N*=43.")

    return meta


class ShadowInferenceRunner:
    """Loads and executes the frozen Snapshot B T0 production model."""

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        meta_path: Path = DEFAULT_META_PATH,
    ):
        self.model_path = model_path
        self.meta_path = meta_path
        self.metadata = verify_frozen_model_artifacts(model_path, meta_path)
        self.model: Optional[xgb.XGBRegressor] = None
        self._load_model()

    def _load_model(self) -> None:
        self.model = xgb.XGBRegressor()
        self.model.load_model(str(self.model_path))

    def predict(
        self,
        feature_vector: FeatureVector,
        validation_report: ValidationReport,
        prev_record_hash: str = "0" * 64,
    ) -> ShadowPrediction:
        """Generate a single point-in-time Snapshot B prediction."""
        if not validation_report.is_eligible_for_inference:
            raise ValueError(
                f"Cannot generate prediction for session {feature_vector.session_date}: "
                f"Validation failed with errors: {validation_report.error_messages}"
            )

        # Defense-in-depth architectural checks on feature vector
        if len(feature_vector.feature_names) != 63:
            raise ValueError(f"Inference requires exactly 63 features, found {len(feature_vector.feature_names)}")
        if len(set(feature_vector.feature_names)) != 63:
            raise ValueError("Inference rejected: duplicate feature names detected.")
        if tuple(feature_vector.feature_names) != CANONICAL_FEATURES_63:
            raise ValueError("Inference rejected: feature names or sequence do not match canonical 63 features.")
        if len(feature_vector.feature_values) != 63:
            raise ValueError(f"Inference requires exactly 63 feature values, found {len(feature_vector.feature_values)}")

        if self.model is None:
            raise RuntimeError("Model is not initialized.")

        # Prepare feature matrix
        x_mat = np.array([feature_vector.feature_values], dtype=np.float32)
        raw_pred = float(self.model.predict(x_mat)[0])
        pred_bps = float(raw_pred * 10000.0)

        now_utc = datetime.now(timezone.utc)
        prediction_id = f"pred_{feature_vector.session_date}_0850"

        # Construct deterministic record payload for cryptographic hash
        record_payload = {
            "prediction_id": prediction_id,
            "session_date": feature_vector.session_date,
            "target_date": feature_vector.session_date,
            "prediction_timestamp": now_utc.isoformat(),
            "snapshot_type": "SNAPSHOT_0850",
            "cutoff_timestamp": feature_vector.cutoff_time.isoformat(),
            "target_id": "T0",
            "predicted_return": raw_pred,
            "predicted_return_bps": pred_bps,
            "model_name": self.metadata.get("model_name", "Snapshot B T0 Full Development Production Model"),
            "model_sha256": CANONICAL_MODEL_SHA256,
            "feature_hash": feature_vector.feature_hash,
            "feature_count": 63,
            "provenance_type": feature_vector.provenance.provenance_type.value,
            "research_status": "RESEARCH_BASELINE_ONLY",
            "trading_authorized": False,
            "prev_record_hash": prev_record_hash,
        }

        serialized = json.dumps(record_payload, sort_keys=True).encode("utf-8")
        record_hash = hashlib.sha256(serialized).hexdigest()

        return ShadowPrediction(
            prediction_id=prediction_id,
            session_date=feature_vector.session_date,
            target_date=feature_vector.session_date,
            prediction_timestamp=now_utc,
            snapshot_type="SNAPSHOT_0850",
            cutoff_timestamp=feature_vector.cutoff_time,
            target_id="T0",
            predicted_return=raw_pred,
            predicted_return_bps=pred_bps,
            model_name=self.metadata.get("model_name", "Snapshot B T0 Full Development Production Model"),
            model_sha256=CANONICAL_MODEL_SHA256,
            feature_hash=feature_vector.feature_hash,
            feature_count=63,
            provenance_type=feature_vector.provenance.provenance_type.value,
            research_status="RESEARCH_BASELINE_ONLY",
            trading_authorized=False,
            prev_record_hash=prev_record_hash,
            record_hash=record_hash,
        )
