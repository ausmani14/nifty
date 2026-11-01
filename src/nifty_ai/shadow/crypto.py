"""Cryptographic primitives, Ed25519 signatures, and payload verification for NIFTY AI.

Implements pure-Python RFC 8032 Ed25519 verification with zero external dependencies,
ensuring operator attestations and source payload hashes are cryptographically authentic
and tamper-evident.
"""

from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

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
    """Compute deterministic SHA-256 hash across all source manifest records."""
    sorted_records = sorted(source_manifest, key=lambda s: (s.instrument_symbol, s.source_id))
    serialized = []
    for s in sorted_records:
        serialized.append(
            f"{s.source_id}|{s.instrument_symbol}|{s.feature_family}|"
            f"{','.join(sorted(s.feature_names))}|{s.raw_payload_hash}|"
            f"{s.observation_time.isoformat()}|{s.availability_time.isoformat()}|"
            f"{s.ingestion_time.isoformat()}"
        )
    combined = "\n".join(serialized).encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def compute_attestation_payload(
    session_date: str,
    cutoff_time_iso: str,
    feature_hash: str,
    manifest_hash: str,
    signed_timestamp_iso: str,
) -> bytes:
    """Construct canonical immutable byte payload for operator attestation signature."""
    payload_str = (
        f"NIFTY_AI_OPERATOR_ATTESTATION\n"
        f"session_date={session_date}\n"
        f"cutoff_time={cutoff_time_iso}\n"
        f"feature_hash={feature_hash}\n"
        f"manifest_hash={manifest_hash}\n"
        f"signed_timestamp={signed_timestamp_iso}"
    )
    return payload_str.encode("utf-8")


def verify_raw_payload_sha256(raw_bytes: bytes, declared_hash: str) -> bool:
    """Verify that raw source payload bytes strictly match declared SHA-256 hash."""
    if not declared_hash or len(declared_hash) != 64:
        return False
    computed = hashlib.sha256(raw_bytes).hexdigest().lower()
    return computed == declared_hash.lower()


def verify_attestation(
    feature_vector: Any,
    attestation: Any,
    authorized_public_keys: Optional[List[str]] = None,
) -> Tuple[bool, Optional[str]]:
    """Cryptographically verify an OperatorAttestation over a FeatureVector and its manifest."""
    if not attestation:
        return False, "Attestation object is missing."

    if not attestation.operator_id or not attestation.operator_id.strip():
        return False, "Operator ID is missing."

    if not attestation.public_key or len(attestation.public_key) != 64:
        return False, f"Invalid public key length: expected 64 hex characters, got {len(attestation.public_key or '')}."

    if not attestation.signature or len(attestation.signature) != 128:
        return False, f"Invalid signature length: expected 128 hex characters, got {len(attestation.signature or '')}."

    if attestation.signed_timestamp is None or attestation.signed_timestamp.tzinfo is None:
        return False, "Attestation signed_timestamp must be timezone-aware."

    # Check authorized keys registry if configured
    configured_keys = authorized_public_keys
    if configured_keys is None:
        env_keys = os.environ.get("NIFTY_AI_OPERATOR_PUBLIC_KEYS", "")
        if env_keys.strip():
            configured_keys = [k.strip().lower() for k in env_keys.split(",") if k.strip()]

    if configured_keys and attestation.public_key.lower() not in configured_keys:
        return False, f"Public key '{attestation.public_key}' is not in authorized operator key registry."

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
        feature_hash=feature_vector.feature_hash,
        manifest_hash=manifest_hash,
        signed_timestamp_iso=attestation.signed_timestamp.isoformat(),
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
        feature_hash=feature_vector.feature_hash,
        manifest_hash=manifest_hash,
        signed_timestamp_iso=signed_timestamp.isoformat(),
    )

    sig_bytes = ed25519_sign(message, sk_bytes)

    return OperatorAttestation(
        operator_id=operator_id,
        key_id=key_id,
        signature=sig_bytes.hex(),
        signed_timestamp=signed_timestamp,
        public_key=pk_hex,
    )
