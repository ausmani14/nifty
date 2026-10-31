"""Strict Model and Historical Data Protection Guard for NIFTY AI.

Enforces zero model drift, cryptographic checksum matching, exact 63-feature ordering,
and immediate abort with MODEL_INTEGRITY_FAILURE on any tampering.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import xgboost as xgb

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    CANONICAL_META_SHA256,
    CANONICAL_MODEL_SHA256,
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


class ModelIntegrityError(Exception):
    """Raised when frozen model fails any cryptographic or architectural check."""
    def __init__(self, message: str, code: str = "MODEL_INTEGRITY_FAILURE"):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ModelProtectionReport:
    verified_at: datetime
    is_intact: bool
    model_sha256: str
    meta_sha256: str
    n_estimators: int
    feature_count: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verified_at": self.verified_at.isoformat(),
            "is_intact": self.is_intact,
            "model_sha256": self.model_sha256,
            "meta_sha256": self.meta_sha256,
            "n_estimators": self.n_estimators,
            "feature_count": self.feature_count,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


def compute_file_sha256(filepath: Path) -> str:
    """Compute deterministic SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def audit_frozen_model_protection(
    model_path: Path = DEFAULT_MODEL_PATH,
    meta_path: Path = DEFAULT_META_PATH,
) -> ModelProtectionReport:
    """Execute complete cryptographic and architectural audit of the frozen model."""
    now_utc = datetime.now(timezone.utc)

    # 1. Check existence
    if not model_path.exists():
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256="",
            meta_sha256="",
            n_estimators=0,
            feature_count=0,
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message=f"Model artifact file does not exist: {model_path}",
        )
    if not meta_path.exists():
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256="",
            meta_sha256="",
            n_estimators=0,
            feature_count=0,
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message=f"Model metadata file does not exist: {meta_path}",
        )

    # 2. Check binary SHA-256
    actual_model_hash = compute_file_sha256(model_path)
    if actual_model_hash != CANONICAL_MODEL_SHA256:
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256=actual_model_hash,
            meta_sha256="",
            n_estimators=0,
            feature_count=0,
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message=f"Model binary SHA-256 mismatch: {actual_model_hash} != {CANONICAL_MODEL_SHA256}",
        )

    # 3. Check metadata SHA-256
    actual_meta_hash = compute_file_sha256(meta_path)
    if actual_meta_hash != CANONICAL_META_SHA256:
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256=actual_model_hash,
            meta_sha256=actual_meta_hash,
            n_estimators=0,
            feature_count=0,
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message=f"Metadata SHA-256 mismatch: {actual_meta_hash} != {CANONICAL_META_SHA256}",
        )

    # 4. Check JSON contents
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception as e:
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256=actual_model_hash,
            meta_sha256=actual_meta_hash,
            n_estimators=0,
            feature_count=0,
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message=f"Corrupted metadata JSON: {e}",
        )

    # 5. Check tree count (N*=43)
    n_estimators = meta.get("hyperparameters", {}).get("n_estimators")
    if n_estimators != 43:
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256=actual_model_hash,
            meta_sha256=actual_meta_hash,
            n_estimators=n_estimators or 0,
            feature_count=0,
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message=f"Frozen model tree count must be exactly 43, found {n_estimators}",
        )

    # 6. Check feature count (63) and sequence
    features = meta.get("features", [])
    if len(features) != 63:
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256=actual_model_hash,
            meta_sha256=actual_meta_hash,
            n_estimators=43,
            feature_count=len(features),
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message=f"Expected exactly 63 features, found {len(features)}",
        )

    if tuple(features) != CANONICAL_FEATURES_63:
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256=actual_model_hash,
            meta_sha256=actual_meta_hash,
            n_estimators=43,
            feature_count=len(features),
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message="Feature ordering or schema mismatch against canonical 63 features.",
        )

    # 7. Check XGBoost model loadability and structure (trees and feature count)
    try:
        booster = xgb.Booster()
        booster.load_model(str(model_path))
        num_trees = len(booster.get_dump())
        if num_trees != 43:
            return ModelProtectionReport(
                verified_at=now_utc,
                is_intact=False,
                model_sha256=actual_model_hash,
                meta_sha256=actual_meta_hash,
                n_estimators=num_trees,
                feature_count=booster.num_features(),
                error_code="MODEL_INTEGRITY_FAILURE",
                error_message=f"Frozen model loaded booster tree count must be exactly 43, found {num_trees}",
            )
        if booster.num_features() != 63:
            return ModelProtectionReport(
                verified_at=now_utc,
                is_intact=False,
                model_sha256=actual_model_hash,
                meta_sha256=actual_meta_hash,
                n_estimators=43,
                feature_count=booster.num_features(),
                error_code="MODEL_INTEGRITY_FAILURE",
                error_message=f"Frozen model loaded booster feature count must be exactly 63, found {booster.num_features()}",
            )
        # Verify file on disk was not mutated by loading
        post_load_hash = compute_file_sha256(model_path)
        if post_load_hash != actual_model_hash:
            return ModelProtectionReport(
                verified_at=now_utc,
                is_intact=False,
                model_sha256=post_load_hash,
                meta_sha256=actual_meta_hash,
                n_estimators=43,
                feature_count=63,
                error_code="MODEL_INTEGRITY_FAILURE",
                error_message="Model file was mutated during model loading.",
            )
    except Exception as e:
        return ModelProtectionReport(
            verified_at=now_utc,
            is_intact=False,
            model_sha256=actual_model_hash,
            meta_sha256=actual_meta_hash,
            n_estimators=43,
            feature_count=63,
            error_code="MODEL_INTEGRITY_FAILURE",
            error_message=f"XGBoost booster failed to load: {e}",
        )

    return ModelProtectionReport(
        verified_at=now_utc,
        is_intact=True,
        model_sha256=actual_model_hash,
        meta_sha256=actual_meta_hash,
        n_estimators=43,
        feature_count=63,
    )


def assert_frozen_model_intact(
    model_path: Path = DEFAULT_MODEL_PATH,
    meta_path: Path = DEFAULT_META_PATH,
) -> ModelProtectionReport:
    """Assert that the frozen model passes all protection checks; raise ModelIntegrityError otherwise."""
    report = audit_frozen_model_protection(model_path, meta_path)
    if not report.is_intact:
        raise ModelIntegrityError(report.error_message or "Unknown failure", code=report.error_code or "MODEL_INTEGRITY_FAILURE")
    return report
