"""Frozen model inference runner for Phase 14 Shadow System.

Enforces model cryptographic authentication, immutable feature alignment,
full precision preservation, and fail-closed execution semantics.
"""

from datetime import datetime, time, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo
import numpy as np
import xgboost as xgb

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    CANONICAL_META_SHA256,
    CANONICAL_MODEL_SHA256,
    FeatureVector,
    ProvenanceType,
    ShadowPrediction,
    ValidationReport,
    ValidationStatus,
)
from nifty_ai.shadow.input_validator import (
    PREMARKET_DEADLINE_TIME,
    SNAPSHOT_B_CUTOFF_TIME,
    compute_feature_vector_hash,
)

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")

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
        operator_key_registry: Optional[Any] = None,
    ) -> ShadowPrediction:
        """Generate a single point-in-time Snapshot B prediction."""
        # 1. Validation report eligibility and status
        if not validation_report.is_eligible_for_inference:
            raise ValueError(
                f"Cannot generate prediction for session {feature_vector.session_date}: "
                f"Validation failed with errors: {validation_report.error_messages}"
            )
        if validation_report.status != ValidationStatus.PASSED:
            raise ValueError(
                f"Inference rejected: Validation report status is '{validation_report.status}', expected PASSED."
            )

        # 2. Session date match
        if validation_report.session_date != feature_vector.session_date:
            raise ValueError(
                f"Inference rejected: Validation report session date '{validation_report.session_date}' "
                f"does not match feature vector session date '{feature_vector.session_date}'."
            )

        # 3. Timezone awareness of evaluation timestamp
        if validation_report.evaluated_at is None or validation_report.evaluated_at.tzinfo is None:
            raise ValueError("Inference rejected: Validation report evaluated_at timestamp lacks timezone awareness.")

        # 4. Evaluation window verification ([08:50:00, 09:15:00) IST)
        target_session_dt = datetime.strptime(feature_vector.session_date, "%Y-%m-%d").date()
        expected_cutoff = datetime.combine(target_session_dt, SNAPSHOT_B_CUTOFF_TIME, tzinfo=MARKET_TIMEZONE)
        premarket_deadline = datetime.combine(target_session_dt, PREMARKET_DEADLINE_TIME, tzinfo=MARKET_TIMEZONE)
        eval_ist = validation_report.evaluated_at.astimezone(MARKET_TIMEZONE)
        if eval_ist < expected_cutoff:
            raise ValueError(
                f"Inference rejected: Evaluation time {eval_ist.strftime('%H:%M:%S IST')} is prior to 08:50:00 IST information cutoff."
            )
        if eval_ist >= premarket_deadline:
            raise ValueError(
                f"Inference rejected: Evaluation time {eval_ist.strftime('%H:%M:%S IST')} is at or after 09:15:00 IST market open deadline."
            )

        # Defense-in-depth architectural checks on feature vector structure
        if len(feature_vector.feature_names) != 63:
            raise ValueError(f"Inference requires exactly 63 features, found {len(feature_vector.feature_names)}")
        if len(set(feature_vector.feature_names)) != 63:
            raise ValueError("Inference rejected: duplicate feature names detected.")
        if tuple(feature_vector.feature_names) != CANONICAL_FEATURES_63:
            raise ValueError("Inference rejected: feature names or sequence do not match canonical 63 features.")
        if len(feature_vector.feature_values) != 63:
            raise ValueError(f"Inference requires exactly 63 feature values, found {len(feature_vector.feature_values)}")

        # 5. Validation report vector binding
        rep_hash = getattr(validation_report, "feature_vector_hash", "")
        if rep_hash != feature_vector.feature_hash:
            raise ValueError(
                f"Inference rejected: Validation report is not bound to supplied feature vector. "
                f"Report vector hash: '{rep_hash}', Vector hash: '{feature_vector.feature_hash}'."
            )

        # 6. Recomputed feature hash verification
        recomputed_hash = compute_feature_vector_hash(feature_vector.feature_names, feature_vector.feature_values)
        if feature_vector.feature_hash != recomputed_hash:
            raise ValueError(
                f"Inference rejected: Feature vector hash mismatch. "
                f"Declared: '{feature_vector.feature_hash}', Recomputed: '{recomputed_hash}'."
            )

        # 7. Exact cutoff date and time
        if feature_vector.cutoff_time is None or feature_vector.cutoff_time.tzinfo is None:
            raise ValueError("Inference rejected: Feature vector cutoff_time lacks timezone awareness.")
        cutoff_ist = feature_vector.cutoff_time.astimezone(MARKET_TIMEZONE)
        if cutoff_ist.date() != target_session_dt:
            raise ValueError(
                f"Inference rejected: Cutoff calendar date '{cutoff_ist.date()}' does not match session date '{target_session_dt}'."
            )
        if cutoff_ist.time() != SNAPSHOT_B_CUTOFF_TIME:
            raise ValueError(
                f"Inference rejected: Cutoff time '{cutoff_ist.time()}' does not match mandatory 08:50:00 IST boundary."
            )

        # 8. Allowed prospective provenance
        allowed_prospective = {
            ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
            ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE,
        }
        if feature_vector.provenance is None or feature_vector.provenance.provenance_type not in allowed_prospective:
            prov_str = str(feature_vector.provenance.provenance_type) if feature_vector.provenance else "None"
            raise ValueError(
                f"Inference rejected: Non-prospective provenance '{prov_str}'. "
                f"Only {[p.value for p in allowed_prospective]} are authorized for inference."
            )

        # 9. Source manifest defense-in-depth enforcement
        prov = feature_vector.provenance
        if not getattr(prov, "source_manifest", None) or len(prov.source_manifest) == 0:
            raise ValueError("Inference rejected: Prospective prediction requires non-empty source_manifest.")

        # Reject synthetic test providers
        if any(sub in (prov.source_id or "").lower() for sub in ["synthetic", "test", "mock", "dummy"]):
            raise ValueError(f"Inference rejected: Synthetic/test vector source_id '{prov.source_id}'.")
        for src in prov.source_manifest:
            if any(sub in (src.source_id or "").lower() for sub in ["synthetic", "test", "mock", "dummy"]):
                raise ValueError(f"Inference rejected: Synthetic/test source provider '{src.source_id}'.")
            if not src.raw_payload_hash or len(src.raw_payload_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in src.raw_payload_hash):
                raise ValueError(f"Inference rejected: Invalid raw_payload_hash for source {src.instrument_symbol}.")

        from nifty_ai.shadow.crypto import RawPayloadStore, compute_manifest_hash, verify_attestation
        store = RawPayloadStore()
        for src in prov.source_manifest:
            if src.raw_payload_ref:
                is_valid_art, art_err = store.verify_artifact(src.raw_payload_ref, src.raw_payload_hash)
                if not is_valid_art:
                    raise ValueError(f"Inference rejected: Raw payload artifact verification failed for {src.instrument_symbol}: {art_err}")

        recomputed_manifest_hash = compute_manifest_hash(prov.source_manifest)
        evidence_digest = RawPayloadStore.compute_evidence_digest(prov.source_manifest)

        # Operator attestation verification
        if prov.provenance_type == ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE:
            if getattr(prov, "attestation", None) is None:
                raise ValueError("Inference rejected: OPERATOR_ATTESTED_PROSPECTIVE requires cryptographic attestation.")
            is_valid, sig_err = verify_attestation(
                feature_vector,
                prov.attestation,
                registry=operator_key_registry,
                evaluation_time=eval_ist,
            )
            if not is_valid:
                raise ValueError(f"Inference rejected: Operator attestation signature verification failed: {sig_err}")

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
            "manifest_hash": recomputed_manifest_hash,
            "raw_evidence_digest": evidence_digest,
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
            manifest_hash=recomputed_manifest_hash,
            raw_evidence_digest=evidence_digest,
        )
