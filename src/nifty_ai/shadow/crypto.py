"""Cryptographic primitives, Ed25519 signatures, and payload verification for NIFTY AI.

Implements RFC 8032 Ed25519 verification using standard cryptography library,
ensuring operator attestations and source payload hashes are cryptographically authentic
and tamper-evident.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    AuthorizedOperatorKey,
    CANONICAL_CONTEXT_MAPPING,
    OPERATOR_ATTESTATION_PROTOCOL_VERSION,
)


def ed25519_sign(message: bytes, private_key_bytes: bytes) -> bytes:
    """Generate RFC 8032 Ed25519 signature (64 bytes)."""
    if len(private_key_bytes) != 32:
        raise ValueError(f"Private key must be exactly 32 bytes, got {len(private_key_bytes)}")
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    return priv.sign(message)


def ed25519_verify(message: bytes, signature_bytes: bytes, public_key_bytes: bytes) -> bool:
    """Verify RFC 8032 Ed25519 signature."""
    if len(signature_bytes) != 64 or len(public_key_bytes) != 32:
        return False
    try:
        pub = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
        pub.verify(signature_bytes, message)
        return True
    except (InvalidSignature, Exception):
        return False


def generate_operator_keypair() -> Tuple[str, str]:
    """Generate a random Ed25519 keypair for testing or offline signing.
    
    Returns (private_key_hex, public_key_hex).
    The private key must NEVER be committed to version control.
    """
    priv = ed25519.Ed25519PrivateKey.generate()
    sk = priv.private_bytes_raw()
    pk = priv.public_key().public_bytes_raw()
    return sk.hex(), pk.hex()


def derive_public_key(private_key_hex: str) -> str:
    """Derive public key hex from 32-byte private key hex."""
    sk = bytes.fromhex(private_key_hex)
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(sk)
    return priv.public_key().public_bytes_raw().hex()


def compute_manifest_hash(source_manifest: List[Any]) -> str:
    """Compute deterministic SHA-256 hash across all security-relevant fields of source manifest records.
    
    Uses canonical JSON serialization (RFC 8785) with sorted keys and compact separators:
    source_id, instrument_symbol, feature_family, feature_names (sorted),
    observation_time (ISO), availability_time (ISO), ingestion_time (ISO), timezone,
    raw_payload_hash (lowercase hex), provenance_type, staleness_seconds, raw_payload_ref.
    """
    sorted_records = sorted(source_manifest, key=lambda s: (s.instrument_symbol, s.source_id))
    manifest_entries = []
    for s in sorted_records:
        prov_type = s.provenance_type.value if hasattr(s.provenance_type, "value") else str(s.provenance_type)
        staleness_val = round(float(getattr(s, "staleness_seconds", 0.0)), 4)
        ref_str = str(getattr(s, "raw_payload_ref", "") or "")
        entry = {
            "source_id": str(s.source_id),
            "instrument_symbol": str(s.instrument_symbol),
            "feature_family": str(s.feature_family),
            "feature_names": sorted(list(s.feature_names)),
            "observation_time": s.observation_time.isoformat(),
            "availability_time": s.availability_time.isoformat(),
            "ingestion_time": s.ingestion_time.isoformat(),
            "timezone": str(s.timezone),
            "raw_payload_hash": str(s.raw_payload_hash).lower(),
            "provenance_type": prov_type,
            "staleness_seconds": staleness_val,
            "raw_payload_ref": ref_str,
        }
        manifest_entries.append(entry)
    canonical_json = json.dumps(manifest_entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def compute_attestation_payload(
    session_date: str,
    cutoff_time_iso: str,
    feature_count: int,
    feature_hash: str,
    manifest_hash: str,
    signed_timestamp_iso: str,
    operator_id: str,
    key_id: str,
    public_key: str,
) -> bytes:
    """Construct canonical immutable byte payload for operator attestation signature.
    
    Includes protocol version, session date, cutoff, feature count, feature hash,
    manifest hash, signed timestamp, operator ID, key ID, and public key identity.
    """
    payload_str = (
        f"PROTOCOL={OPERATOR_ATTESTATION_PROTOCOL_VERSION}\n"
        f"SESSION_DATE={session_date}\n"
        f"CUTOFF_TIME={cutoff_time_iso}\n"
        f"FEATURE_COUNT={feature_count}\n"
        f"FEATURE_HASH={feature_hash}\n"
        f"MANIFEST_HASH={manifest_hash}\n"
        f"SIGNED_TIMESTAMP={signed_timestamp_iso}\n"
        f"OPERATOR_ID={operator_id}\n"
        f"KEY_ID={key_id}\n"
        f"PUBLIC_KEY={public_key.lower()}"
    )
    return payload_str.encode("utf-8")


def verify_raw_payload_sha256(raw_bytes: bytes, declared_hash: str) -> bool:
    """Verify that raw source payload bytes strictly match declared SHA-256 hash."""
    if not declared_hash or len(declared_hash) != 64:
        return False
    computed = hashlib.sha256(raw_bytes).hexdigest().lower()
    return computed == declared_hash.lower()


# ---------------------------------------------------------------------------
# Immutable Content-Addressed Raw Payload Store
# ---------------------------------------------------------------------------

DEFAULT_RAW_CAPTURE_DIR = PROJECT_ROOT / "data" / "shadow" / "raw_captures"


class RawPayloadStore:
    """Persistent, retrievable, immutable content-addressed store for raw market data capture artifacts.
    
    Storage format: data/shadow/raw_captures/{session_date}/{safe_sym}_{sha256}.bin
    Enforces:
    - Atomic exclusive creation (open with mode 'xb')
    - Content-addressed immutability (sha256 in filename and readback verification)
    - Path traversal and symlink guards
    - Session date validation (YYYY-MM-DD)
    - Canonical instrument allowlist validation
    - Portable repository-relative path resolution
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = (base_dir or DEFAULT_RAW_CAPTURE_DIR).resolve()

    def store_payload(
        self,
        session_date: str,
        instrument_symbol: str,
        payload_bytes: bytes,
    ) -> Tuple[str, str]:
        """Store raw binary payload and return (sha256_hash, retrievable_artifact_path)."""
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", session_date):
            raise ValueError(f"Invalid session_date format '{session_date}': must be YYYY-MM-DD")
        try:
            datetime.strptime(session_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid session_date '{session_date}': not a valid calendar date")

        allowed_instruments = {"^NSEI", "CALENDAR"} | set(CANONICAL_CONTEXT_MAPPING.keys())
        if instrument_symbol not in allowed_instruments:
            raise ValueError(f"Instrument '{instrument_symbol}' is not in canonical instrument allowlist.")

        if not payload_bytes:
            raise ValueError(f"Cannot store empty raw payload bytes for {instrument_symbol}")

        sha256_hash = hashlib.sha256(payload_bytes).hexdigest().lower()
        safe_sym = instrument_symbol.replace("^", "").replace("=", "_").replace(".", "_")

        target_dir = (self.base_dir / session_date).resolve()
        # Path traversal guard
        try:
            target_dir.relative_to(self.base_dir)
        except ValueError:
            raise ValueError(f"Path traversal detected: {target_dir} escapes {self.base_dir}")

        target_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = (target_dir / f"{safe_sym}_{sha256_hash}.bin").resolve()

        # Symlink guard
        if artifact_path.is_symlink() or target_dir.is_symlink():
            raise ValueError(f"Symlinks are prohibited in payload store: {artifact_path}")

        # Atomic exclusive write
        try:
            with open(artifact_path, "xb") as f:
                f.write(payload_bytes)
        except FileExistsError:
            # File already exists: verify SHA256 matches
            existing_bytes = artifact_path.read_bytes()
            existing_hash = hashlib.sha256(existing_bytes).hexdigest().lower()
            if existing_hash != sha256_hash:
                raise ValueError(
                    f"Hash collision / corruption at {artifact_path}: existing {existing_hash} != {sha256_hash}"
                )

        # Immediate readback verification
        readback_bytes = artifact_path.read_bytes()
        readback_hash = hashlib.sha256(readback_bytes).hexdigest().lower()
        if readback_hash != sha256_hash:
            raise IOError(f"Readback verification failed immediately after writing {artifact_path}")

        # Return repository-relative path if inside PROJECT_ROOT
        try:
            rel_path = artifact_path.relative_to(PROJECT_ROOT.resolve())
            return sha256_hash, str(rel_path.as_posix())
        except ValueError:
            return sha256_hash, str(artifact_path)

    def resolve_artifact_path(self, artifact_ref: str) -> Optional[Path]:
        """Resolve an artifact reference to a verified, safe Path within base_dir or PROJECT_ROOT."""
        if not artifact_ref or artifact_ref.startswith("payload_ref://"):
            return None
        p = Path(artifact_ref)
        if not p.is_absolute():
            p = (PROJECT_ROOT / p).resolve()
        else:
            p = p.resolve()
        if p.is_symlink():
            return None
        if not p.exists() or not p.is_file():
            return None
        return p

    def retrieve_payload(self, artifact_ref: str) -> Optional[bytes]:
        """Retrieve actual raw bytes from artifact reference."""
        p = self.resolve_artifact_path(artifact_ref)
        if p is None:
            return None
        return p.read_bytes()

    def verify_artifact(self, artifact_ref: str, expected_hash: str) -> Tuple[bool, Optional[str]]:
        """Verify that an artifact file exists, is readable, and matches expected SHA-256 hash."""
        if not artifact_ref:
            return False, "Artifact reference is empty or missing."
        if artifact_ref.startswith("payload_ref://"):
            return False, f"Fake payload URI scheme rejected: '{artifact_ref}'."
        data = self.retrieve_payload(artifact_ref)
        if data is None:
            return False, f"Raw payload artifact not found or unresolvable at '{artifact_ref}'."
        computed = hashlib.sha256(data).hexdigest().lower()
        if computed != expected_hash.lower():
            return False, f"Raw payload hash mismatch at '{artifact_ref}': computed {computed}, expected {expected_hash.lower()}."
        return True, None

    @staticmethod
    def compute_evidence_digest(source_manifest: List[Any]) -> str:
        """Compute aggregate digest over all raw payload hashes in canonical instrument order."""
        sorted_manifest = sorted(source_manifest, key=lambda s: s.instrument_symbol)
        hashes = [f"{s.instrument_symbol}:{s.raw_payload_hash.lower()}" for s in sorted_manifest]
        return hashlib.sha256("\n".join(hashes).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Mandatory Operator Key Registry
# ---------------------------------------------------------------------------

class OperatorKeyRegistry:
    """Authorized cryptographic public-key registry for prospective operators."""

    def __init__(self, authorized_keys: Optional[List[AuthorizedOperatorKey]] = None):
        self._keys: Dict[str, AuthorizedOperatorKey] = {}
        if authorized_keys:
            for k in authorized_keys:
                self.register_key(k)

    def register_key(self, key: AuthorizedOperatorKey) -> None:
        """Register an authorized operator key."""
        self._keys[key.key_id] = key

    def get_key(self, key_id: str) -> Optional[AuthorizedOperatorKey]:
        return self._keys.get(key_id)

    def is_empty(self) -> bool:
        return len(self._keys) == 0

    def validate_operator_authorization(
        self,
        operator_id: str,
        key_id: str,
        public_key_hex: str,
        evaluation_time: datetime,
    ) -> Tuple[bool, Optional[str]]:
        """Validate operator identity, key registration, expiration, and revocation status."""
        if self.is_empty():
            return False, "Trusted operator key registry is missing or empty."
        auth_key = self.get_key(key_id)
        if not auth_key:
            return False, f"Unknown key_id '{key_id}' in operator key registry."
        if auth_key.operator_id != operator_id:
            return False, f"Operator ID mismatch: key '{key_id}' belongs to '{auth_key.operator_id}', not '{operator_id}'."
        if auth_key.public_key_hex.lower() != public_key_hex.lower():
            return False, f"Public key mismatch for key_id '{key_id}'."
        if auth_key.is_revoked:
            return False, f"Operator key '{key_id}' is revoked."
        eval_utc = evaluation_time.astimezone(timezone.utc)
        valid_from_utc = auth_key.valid_from.astimezone(timezone.utc)
        if eval_utc < valid_from_utc:
            return False, f"Operator key '{key_id}' is not yet valid (valid_from: {auth_key.valid_from.isoformat()})."
        if auth_key.valid_until:
            valid_until_utc = auth_key.valid_until.astimezone(timezone.utc)
            if eval_utc > valid_until_utc:
                return False, f"Operator key '{key_id}' has expired (valid_until: {auth_key.valid_until.isoformat()})."
        return True, None


def load_operator_key_registry(config_path: Optional[Path] = None) -> OperatorKeyRegistry:
    """Load authorized operator keys from reviewed JSON configuration file.
    
    Default path: config/operator_keys.json
    Fails closed if the file is missing or contains invalid records.
    """
    target = (config_path or (PROJECT_ROOT / "config" / "operator_keys.json")).resolve()
    if not target.exists() or not target.is_file():
        return OperatorKeyRegistry([])
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError(f"operator_keys.json must contain a JSON list, got {type(data)}")
        keys: List[AuthorizedOperatorKey] = []
        for item in data:
            v_from = datetime.fromisoformat(item["valid_from"])
            if v_from.tzinfo is None:
                raise ValueError(f"valid_from for key '{item.get('key_id')}' must be timezone-aware")
            v_until = None
            if item.get("valid_until"):
                v_until = datetime.fromisoformat(item["valid_until"])
                if v_until.tzinfo is None:
                    raise ValueError(f"valid_until for key '{item.get('key_id')}' must be timezone-aware")
            keys.append(
                AuthorizedOperatorKey(
                    operator_id=item["operator_id"],
                    key_id=item["key_id"],
                    public_key_hex=item["public_key_hex"],
                    valid_from=v_from,
                    valid_until=v_until,
                    is_revoked=bool(item.get("is_revoked", False)),
                )
            )
        return OperatorKeyRegistry(keys)
    except Exception as e:
        raise ValueError(f"Failed to load operator key registry from {target}: {e}")


_DEFAULT_OPERATOR_REGISTRY: Optional[OperatorKeyRegistry] = None


def get_default_key_registry() -> OperatorKeyRegistry:
    global _DEFAULT_OPERATOR_REGISTRY
    if _DEFAULT_OPERATOR_REGISTRY is None:
        _DEFAULT_OPERATOR_REGISTRY = load_operator_key_registry()
    return _DEFAULT_OPERATOR_REGISTRY


def set_default_key_registry(registry: Optional[OperatorKeyRegistry]) -> None:
    global _DEFAULT_OPERATOR_REGISTRY
    _DEFAULT_OPERATOR_REGISTRY = registry


def verify_attestation(
    feature_vector: Any,
    attestation: Any,
    registry: Optional[OperatorKeyRegistry] = None,
    evaluation_time: Optional[datetime] = None,
) -> Tuple[bool, Optional[str]]:
    """Cryptographically verify an OperatorAttestation against the trusted key registry."""
    if not attestation:
        return False, "Attestation object is missing."

    if not attestation.operator_id or not attestation.operator_id.strip():
        return False, "Operator ID is missing."

    if not attestation.key_id or not attestation.key_id.strip():
        return False, "Key ID is missing."

    if not attestation.public_key or len(attestation.public_key) != 64:
        return False, f"Invalid public key length: expected 64 hex characters, got {len(attestation.public_key or '')}."

    if not attestation.signature or len(attestation.signature) != 128:
        return False, f"Invalid signature length: expected 128 hex characters, got {len(attestation.signature or '')}."

    if attestation.signed_timestamp is None or attestation.signed_timestamp.tzinfo is None:
        return False, "Attestation signed_timestamp must be timezone-aware."

    eval_time = evaluation_time or attestation.signed_timestamp
    active_registry = registry if registry is not None else get_default_key_registry()

    # 1. Mandatory registry verification
    is_authorized, auth_err = active_registry.validate_operator_authorization(
        operator_id=attestation.operator_id,
        key_id=attestation.key_id,
        public_key_hex=attestation.public_key,
        evaluation_time=eval_time,
    )
    if not is_authorized:
        return False, f"Operator authorization rejected: {auth_err}"

    # 2. Cryptographic signature verification over canonical payload
    try:
        pk_bytes = bytes.fromhex(attestation.public_key)
        sig_bytes = bytes.fromhex(attestation.signature)
    except ValueError as e:
        return False, f"Cryptographic decoding error: {e}"

    manifest = getattr(feature_vector.provenance, "source_manifest", [])
    manifest_hash = compute_manifest_hash(manifest)

    message = compute_attestation_payload(
        session_date=feature_vector.session_date,
        cutoff_time_iso=feature_vector.cutoff_time.isoformat(),
        feature_count=len(feature_vector.feature_names),
        feature_hash=feature_vector.feature_hash,
        manifest_hash=manifest_hash,
        signed_timestamp_iso=attestation.signed_timestamp.isoformat(),
        operator_id=attestation.operator_id,
        key_id=attestation.key_id,
        public_key=attestation.public_key,
    )

    is_valid = ed25519_verify(message, sig_bytes, pk_bytes)
    if not is_valid:
        return False, "Ed25519 signature verification failed. Message payload or signature has been altered."

    return True, None


def create_operator_attestation(
    feature_vector: Any,
    operator_id: str,
    key_id: str,
    private_key_hex: str,
    signed_timestamp: Optional[datetime] = None,
) -> Any:
    """Helper for authorized offline operators / test harnesses to sign a feature vector."""
    from nifty_ai.shadow.contracts import OperatorAttestation

    sk_bytes = bytes.fromhex(private_key_hex)
    pk_hex = derive_public_key(private_key_hex)

    if signed_timestamp is None:
        signed_timestamp = datetime.now(timezone.utc)
    elif signed_timestamp.tzinfo is None:
        raise ValueError("signed_timestamp must be timezone-aware.")

    manifest = getattr(feature_vector.provenance, "source_manifest", [])
    manifest_hash = compute_manifest_hash(manifest)

    message = compute_attestation_payload(
        session_date=feature_vector.session_date,
        cutoff_time_iso=feature_vector.cutoff_time.isoformat(),
        feature_count=len(feature_vector.feature_names),
        feature_hash=feature_vector.feature_hash,
        manifest_hash=manifest_hash,
        signed_timestamp_iso=signed_timestamp.isoformat(),
        operator_id=operator_id,
        key_id=key_id,
        public_key=pk_hex,
    )

    sig_bytes = ed25519_sign(message, sk_bytes)

    return OperatorAttestation(
        operator_id=operator_id,
        key_id=key_id,
        signature=sig_bytes.hex(),
        signed_timestamp=signed_timestamp,
        public_key=pk_hex,
    )
