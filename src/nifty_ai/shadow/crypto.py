"""Cryptographic primitives, Ed25519 signatures, and payload verification for NIFTY AI.

Implements pure-Python RFC 8032 Ed25519 verification with zero external dependencies,
ensuring operator attestations and source payload hashes are cryptographically authentic
and tamper-evident.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    AuthorizedOperatorKey,
    OPERATOR_ATTESTATION_PROTOCOL_VERSION,
)

# RFC 8032 Curve25519 / Ed25519 Parameters
_B = 256
_Q = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493


def _H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _inv(x: int) -> int:
    return pow(x, _Q - 2, _Q)


_D = -121665 * _inv(121666) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_D * y * y + 1)
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


_By = 4 * _inv(5) % _Q
_Bx = _xrecover(_By)
_BasePoint = [_Bx, _By]


def _edwards(P: List[int], Q: List[int]) -> List[int]:
    x1, y1 = P[0], P[1]
    x2, y2 = Q[0], Q[1]
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + _D * x1 * x2 * y1 * y2) % _Q
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - _D * x1 * x2 * y1 * y2) % _Q
    return [x3, y3]


def _scalarmult(P: List[int], e: int) -> List[int]:
    if e == 0:
        return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q


def _encodeint(y: int) -> bytes:
    return int(y).to_bytes(32, "little")


def _encodepoint(P: List[int]) -> bytes:
    x, y = P[0], P[1]
    bits = [(y >> i) & 1 for i in range(_B - 1)] + [x & 1]
    return bytes(sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(_B // 8))


def _bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1


def _publickey(sk: bytes) -> bytes:
    h = _H(sk)
    a = 2 ** (_B - 2) + sum(2**i * _bit(h, i) for i in range(3, _B - 2))
    A = _scalarmult(_BasePoint, a)
    return _encodepoint(A)


def _Hint(m: bytes) -> int:
    h = _H(m)
    return int.from_bytes(h, "little")


def _signature(m: bytes, sk: bytes, pk: bytes) -> bytes:
    h = _H(sk)
    a = 2 ** (_B - 2) + sum(2**i * _bit(h, i) for i in range(3, _B - 2))
    r = _Hint(bytes(h[_B // 8 :]) + m)
    R = _scalarmult(_BasePoint, r)
    S = (r + _Hint(_encodepoint(R) + pk + m) * a) % _L
    return _encodepoint(R) + _encodeint(S)


def _isoncurve(P: List[int]) -> bool:
    x, y = P[0], P[1]
    return (-x * x + y * y - 1 - _D * x * x * y * y) % _Q == 0


def _decodeint(s: bytes) -> int:
    return int.from_bytes(s, "little")


def _decodepoint(s: bytes) -> List[int]:
    y = sum(2**i * _bit(s, i) for i in range(0, _B - 1))
    x = _xrecover(y)
    if (x & 1) != _bit(s, _B - 1):
        x = _Q - x
    P = [x, y]
    if not _isoncurve(P):
        raise ValueError("Decoding point that is not on curve")
    return P


def ed25519_sign(message: bytes, private_key_bytes: bytes) -> bytes:
    """Generate RFC 8032 Ed25519 signature (64 bytes)."""
    if len(private_key_bytes) != 32:
        raise ValueError(f"Private key must be exactly 32 bytes, got {len(private_key_bytes)}")
    pk = _publickey(private_key_bytes)
    return _signature(message, private_key_bytes, pk)


def ed25519_verify(message: bytes, signature_bytes: bytes, public_key_bytes: bytes) -> bool:
    """Verify RFC 8032 Ed25519 signature."""
    if len(signature_bytes) != 64 or len(public_key_bytes) != 32:
        return False
    try:
        R = _decodepoint(signature_bytes[:32])
        A = _decodepoint(public_key_bytes)
        S = _decodeint(signature_bytes[32:])
        if S >= _L:
            return False
        h = _Hint(_encodepoint(R) + public_key_bytes + message)
        v1 = _scalarmult(_BasePoint, S)
        v2 = _edwards(R, _scalarmult(A, h))
        return v1 == v2
    except Exception:
        return False


def generate_operator_keypair() -> Tuple[str, str]:
    """Generate a random Ed25519 keypair for testing or offline signing.
    
    Returns (private_key_hex, public_key_hex).
    The private key must NEVER be committed to version control.
    """
    sk = os.urandom(32)
    pk = _publickey(sk)
    return sk.hex(), pk.hex()


def derive_public_key(private_key_hex: str) -> str:
    """Derive public key hex from 32-byte private key hex."""
    sk = bytes.fromhex(private_key_hex)
    return _publickey(sk).hex()


def compute_manifest_hash(source_manifest: List[Any]) -> str:
    """Compute deterministic SHA-256 hash across all security-relevant fields of source manifest records.
    
    Covers: source_id, instrument_symbol, feature_family, sorted feature_names,
    observation_time, availability_time, ingestion_time, timezone, raw_payload_hash,
    provenance_type, staleness_seconds, and raw_payload_ref.
    """
    sorted_records = sorted(source_manifest, key=lambda s: (s.instrument_symbol, s.source_id))
    serialized = []
    for s in sorted_records:
        prov_type = s.provenance_type.value if hasattr(s.provenance_type, "value") else str(s.provenance_type)
        staleness_str = f"{float(getattr(s, 'staleness_seconds', 0.0)):.1f}"
        ref_str = str(getattr(s, "raw_payload_ref", "") or "")
        fields = [
            str(s.source_id),
            str(s.instrument_symbol),
            str(s.feature_family),
            ",".join(sorted(s.feature_names)),
            s.observation_time.isoformat(),
            s.availability_time.isoformat(),
            s.ingestion_time.isoformat(),
            str(s.timezone),
            str(s.raw_payload_hash).lower(),
            prov_type,
            staleness_str,
            ref_str,
        ]
        serialized.append("|".join(fields))
    combined = "\n".join(serialized).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


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
# Raw Payload Capture Artifact Store
# ---------------------------------------------------------------------------

DEFAULT_RAW_CAPTURE_DIR = PROJECT_ROOT / "data" / "shadow" / "raw_captures"


class RawPayloadStore:
    """Persistent, retrievable content store for raw market data capture artifacts."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or DEFAULT_RAW_CAPTURE_DIR

    def store_payload(
        self,
        session_date: str,
        instrument_symbol: str,
        payload_bytes: bytes,
    ) -> Tuple[str, str]:
        """Store raw binary payload and return (sha256_hash, retrievable_artifact_path)."""
        if not payload_bytes:
            raise ValueError(f"Cannot store empty raw payload bytes for {instrument_symbol}")
        safe_sym = instrument_symbol.replace("^", "").replace("=", "_").replace(".", "_")
        target_dir = self.base_dir / session_date
        target_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = target_dir / f"{safe_sym}.bin"
        artifact_path.write_bytes(payload_bytes)
        sha256_hash = hashlib.sha256(payload_bytes).hexdigest()
        return sha256_hash, str(artifact_path.resolve())

    def retrieve_payload(self, artifact_ref: str) -> Optional[bytes]:
        """Retrieve actual raw bytes from artifact reference."""
        if not artifact_ref:
            return None
        # Reject fake URI schemes
        if artifact_ref.startswith("payload_ref://"):
            return None
        p = Path(artifact_ref)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if not p.exists() or not p.is_file():
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


_DEFAULT_OPERATOR_REGISTRY: OperatorKeyRegistry = OperatorKeyRegistry()


def get_default_key_registry() -> OperatorKeyRegistry:
    return _DEFAULT_OPERATOR_REGISTRY


def set_default_key_registry(registry: OperatorKeyRegistry) -> None:
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
    active_registry = registry or get_default_key_registry()

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
    pk_hex = _publickey(sk_bytes).hex()

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
