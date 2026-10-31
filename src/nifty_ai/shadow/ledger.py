"""Append-only, tamper-evident prediction ledger for Phase 14 Shadow System.

Enforces cryptographic hash chaining, idempotency, duplicate prevention, and complete
isolation between predictions and subsequent realized outcomes.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    ACTIVATION_BOUNDARY_UTC,
    LedgerStatus,
    ProvenanceType,
    ShadowPrediction,
)

DEFAULT_LEDGER_PATH = (
    PROJECT_ROOT / "data" / "interim" / "phase14_shadow" / "shadow_predictions_ledger.jsonl"
)
GENESIS_HASH = "0" * 64


class ShadowPredictionLedger:
    """Manages append-only persistence and cryptographic auditing of shadow predictions."""

    def __init__(self, ledger_path: Path = DEFAULT_LEDGER_PATH):
        self.ledger_path = ledger_path
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self.ledger_path.touch()

    def get_all_records(self) -> List[Dict[str, Any]]:
        """Read all raw prediction records from the ledger."""
        records = []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def get_tip_hash(self) -> str:
        """Get the hash of the latest record in the ledger, or GENESIS_HASH if empty."""
        records = self.get_all_records()
        if not records:
            return GENESIS_HASH
        return records[-1]["record_hash"]

    def has_session_prediction(self, session_date: str, snapshot_type: str = "SNAPSHOT_0850") -> bool:
        """Check if a prediction already exists for the given session date and snapshot."""
        for rec in self.get_all_records():
            if rec.get("session_date") == session_date and rec.get("snapshot_type") == snapshot_type:
                return True
        return False

    def append_prediction(
        self,
        prediction: ShadowPrediction,
        enforce_prospective: Optional[bool] = None,
    ) -> Tuple[LedgerStatus, Optional[Dict[str, Any]]]:
        """Atomically append a prediction to the ledger if not already present."""
        # Enforce prospective live capture constraints on production ledger or when requested
        if enforce_prospective is None:
            try:
                enforce_prospective = (self.ledger_path.resolve() == DEFAULT_LEDGER_PATH.resolve())
            except Exception:
                enforce_prospective = True

        if enforce_prospective:
            if prediction.provenance_type != ProvenanceType.PROSPECTIVE_LIVE_CAPTURE.value:
                raise ValueError(
                    f"Prospective prediction ledger strictly rejects non-prospective provenance '{prediction.provenance_type}'. "
                    f"Only '{ProvenanceType.PROSPECTIVE_LIVE_CAPTURE.value}' is authorized."
                )
            pred_ts = prediction.prediction_timestamp
            if pred_ts.tzinfo is None:
                raise ValueError("Prediction timestamp must be timezone-aware.")
            if pred_ts.astimezone(timezone.utc) < ACTIVATION_BOUNDARY_UTC:
                raise ValueError(
                    f"Prediction timestamp {pred_ts.isoformat()} predates activation boundary {ACTIVATION_BOUNDARY_UTC.isoformat()}."
                )

            cutoff_ts = prediction.cutoff_timestamp
            if cutoff_ts.tzinfo is None:
                raise ValueError("Cutoff timestamp must be timezone-aware.")
            if cutoff_ts.astimezone(timezone.utc) < ACTIVATION_BOUNDARY_UTC:
                raise ValueError(
                    f"Cutoff timestamp {cutoff_ts.isoformat()} predates activation boundary {ACTIVATION_BOUNDARY_UTC.isoformat()}."
                )

        # 1. Idempotency / Duplicate Check
        if self.has_session_prediction(prediction.session_date, prediction.snapshot_type):
            existing_rec = next(
                rec for rec in self.get_all_records()
                if rec["session_date"] == prediction.session_date and rec["snapshot_type"] == prediction.snapshot_type
            )
            return LedgerStatus.DUPLICATE_IGNORED, existing_rec

        # 2. Verify hash chaining against current tip
        current_tip = self.get_tip_hash()
        if prediction.prev_record_hash != current_tip:
            raise ValueError(
                f"Ledger tip mismatch: prediction prev_record_hash {prediction.prev_record_hash} "
                f"does not match current tip {current_tip}."
            )

        # 3. Append to JSONL file
        record_dict = prediction.to_dict()
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_dict, sort_keys=True) + "\n")

        return LedgerStatus.RECORDED, record_dict

    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """Audit the entire ledger from genesis to tip for cryptographic consistency."""
        records = self.get_all_records()
        if not records:
            return True, ["Ledger is empty (intact at genesis)."]

        issues = []
        expected_prev_hash = GENESIS_HASH

        for idx, rec in enumerate(records):
            rec_id = rec.get("prediction_id", f"index_{idx}")

            # Check previous hash link
            if rec.get("prev_record_hash") != expected_prev_hash:
                issues.append(
                    f"Broken hash chain at record {rec_id} (index {idx}): "
                    f"prev_record_hash {rec.get('prev_record_hash')} != expected {expected_prev_hash}"
                )

            # Recompute record hash
            payload = {k: v for k, v in rec.items() if k != "record_hash"}
            serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
            computed_hash = hashlib.sha256(serialized).hexdigest()

            if rec.get("record_hash") != computed_hash:
                issues.append(
                    f"Record tamper detected at {rec_id} (index {idx}): "
                    f"stored {rec.get('record_hash')} != computed {computed_hash}"
                )

            # Advance expected previous hash
            expected_prev_hash = rec.get("record_hash", "")

        is_valid = len(issues) == 0
        return is_valid, issues
