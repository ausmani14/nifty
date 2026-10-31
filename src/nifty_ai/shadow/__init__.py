"""Phase 14 Prospective Shadow Prediction & Forward Validation System.

Modules:
- contracts: Schemas, canonical 63 features, and provenance definitions.
- input_validator: Point-in-time Snapshot B validator (08:50 IST cutoff, schema checks).
- input_capture: Pipeline helper to package feature vectors.
- inference: Cryptographically authenticated frozen XGBoost inference runner.
- ledger: Tamper-evident append-only prediction ledger with hash chaining.
- reconciliation: Outcome reconciliation, realized return calculation, and forward metrics.
"""

from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    CANONICAL_MODEL_SHA256,
    FeatureVector,
    LedgerStatus,
    ProvenanceType,
    RealizedOutcome,
    ShadowPrediction,
    SourceProvenance,
    ValidationReport,
    ValidationStatus,
)
from nifty_ai.shadow.inference import ShadowInferenceRunner, verify_frozen_model_artifacts
from nifty_ai.shadow.model_protection import (
    ModelIntegrityError,
    ModelProtectionReport,
    assert_frozen_model_intact,
    audit_frozen_model_protection,
)
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector, load_feature_vector_from_json
from nifty_ai.shadow.input_validator import (
    SnapshotBInputValidator,
    compute_feature_vector_hash,
)
from nifty_ai.shadow.ledger import ShadowPredictionLedger
from nifty_ai.shadow.reconciliation import ShadowOutcomeReconciler

__all__ = [
    "CANONICAL_FEATURES_63",
    "CANONICAL_MODEL_SHA256",
    "FeatureVector",
    "LedgerStatus",
    "ProvenanceType",
    "RealizedOutcome",
    "ShadowPrediction",
    "SourceProvenance",
    "ValidationReport",
    "ValidationStatus",
    "ShadowInferenceRunner",
    "verify_frozen_model_artifacts",
    "ModelIntegrityError",
    "ModelProtectionReport",
    "audit_frozen_model_protection",
    "assert_frozen_model_intact",
    "build_synthetic_feature_vector",
    "load_feature_vector_from_json",
    "SnapshotBInputValidator",
    "compute_feature_vector_hash",
    "ShadowPredictionLedger",
    "ShadowOutcomeReconciler",
]
