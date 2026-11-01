"""Point-in-Time live data capture and exchange calendar adapter for NIFTY AI.

Implements fail-closed capture logic, strict 08:50:00 IST cutoff evaluation,
NSE trading calendar verification, and safe error classification.
"""

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    ACTIVATION_BOUNDARY_UTC,
    CANONICAL_FEATURES_63,
    FeatureVector,
    ProvenanceType,
    SourceProvenance,
)
from nifty_ai.shadow.input_validator import (
    PREMARKET_DEADLINE_TIME,
    SNAPSHOT_B_CUTOFF_TIME,
    compute_feature_vector_hash,
)

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")

# Official NSE Equity Trading Holidays for 2026 (YYYY-MM-DD)
NSE_HOLIDAYS_2026: Set[str] = {
    "2026-01-26",  # Republic Day
    "2026-02-17",  # Mahashivratri
    "2026-03-03",  # Holi
    "2026-03-20",  # Id-Ul-Fitr
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-27",  # Bakri Id / Eid ul-Adha
    "2026-06-26",  # Muharram
    "2026-08-15",  # Independence Day (Saturday)
    "2026-10-02",  # Mahatma Gandhi Jayanti
    "2026-10-20",  # Dussehra
    "2026-11-09",  # Diwali Balipratipada (Note: Lakshmi Puja Muhurat is Sun 2026-11-08)
    "2026-11-24",  # Guru Nanak Jayanti
    "2026-12-25",  # Christmas
}


class CaptureStatus(str, Enum):
    SUCCESS = "SUCCESS"
    DATA_SOURCE_BLOCKED = "DATA_SOURCE_BLOCKED"
    INSUFFICIENT_ELIGIBLE_FEATURES = "INSUFFICIENT_ELIGIBLE_FEATURES"
    INVALID_POINT_IN_TIME_INPUT = "INVALID_POINT_IN_TIME_INPUT"
    HOLIDAY = "HOLIDAY"
    WEEKEND = "WEEKEND"
    MISSED_CUTOFF = "MISSED_CUTOFF"
    PREMATURE_EVALUATION = "PREMATURE_EVALUATION"
    INPUT_FILE_LOADED = "INPUT_FILE_LOADED"


@dataclass(frozen=True)
class DataCaptureResult:
    status: CaptureStatus
    session_date: str
    feature_vector: Optional[FeatureVector] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = None


def is_nse_trading_day(session_date_str: str) -> Tuple[bool, Optional[str]]:
    """Determine whether a given date is an official NSE trading day."""
    dt = datetime.strptime(session_date_str, "%Y-%m-%d").date()
    # 0 = Monday, 6 = Sunday
    if dt.weekday() == 5:
        return False, "Saturday (Weekend)"
    if dt.weekday() == 6:
        return False, "Sunday (Weekend)"
    if session_date_str in NSE_HOLIDAYS_2026:
        return False, f"Official NSE Holiday ({session_date_str})"
    return True, None


def attempt_live_feature_capture(
    session_date: str,
    input_file_path: Optional[Path] = None,
    current_time: Optional[datetime] = None,
) -> DataCaptureResult:
    """Attempt point-in-time Snapshot B feature capture with strict calendar and cutoff gates."""
    now_ist = (current_time or datetime.now(timezone.utc)).astimezone(MARKET_TIMEZONE)

    # 1. Trading Calendar Check
    is_trading, cal_reason = is_nse_trading_day(session_date)
    if not is_trading:
        status = CaptureStatus.WEEKEND if "Weekend" in (cal_reason or "") else CaptureStatus.HOLIDAY
        return DataCaptureResult(
            status=status,
            session_date=session_date,
            feature_vector=None,
            reason=cal_reason,
            metadata={"calendar_check": cal_reason},
        )

    # 2. Timing Cutoff and Backdating Check (08:50:00 Asia/Kolkata)
    today_ist_str = now_ist.strftime("%Y-%m-%d")
    cutoff_time = datetime.combine(
        datetime.strptime(session_date, "%Y-%m-%d").date(),
        SNAPSHOT_B_CUTOFF_TIME,
        tzinfo=MARKET_TIMEZONE,
    )

    # Disallow backdating: prospective predictions can NEVER be generated for past sessions
    if session_date < today_ist_str:
        return DataCaptureResult(
            status=CaptureStatus.MISSED_CUTOFF,
            session_date=session_date,
            feature_vector=None,
            reason=f"Cannot generate prospective prediction for past session date {session_date}. Backdating is strictly prohibited.",
            metadata={"session_date": session_date, "today_ist": today_ist_str, "cutoff_time": cutoff_time.isoformat()},
        )

    # Disallow future dating: prospective predictions cannot be generated in advance of the session
    if session_date > today_ist_str:
        return DataCaptureResult(
            status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
            session_date=session_date,
            feature_vector=None,
            reason=f"Cannot generate prospective prediction for future session date {session_date} in advance.",
            metadata={"session_date": session_date, "today_ist": today_ist_str, "cutoff_time": cutoff_time.isoformat()},
        )

    # Timing validation for current trading day (Snapshot B window: [08:50:00, 09:15:00) IST)
    if session_date == today_ist_str:
        if now_ist.time() < SNAPSHOT_B_CUTOFF_TIME:
            return DataCaptureResult(
                status=CaptureStatus.PREMATURE_EVALUATION,
                session_date=session_date,
                feature_vector=None,
                reason=f"Current time {now_ist.strftime('%H:%M:%S IST')} is before 08:50:00 IST Snapshot B cutoff. Premature prediction generation is strictly prohibited.",
                metadata={"current_time": now_ist.isoformat(), "cutoff_time": cutoff_time.isoformat()},
            )
        if now_ist.time() >= PREMARKET_DEADLINE_TIME:
            return DataCaptureResult(
                status=CaptureStatus.MISSED_CUTOFF,
                session_date=session_date,
                feature_vector=None,
                reason=f"Current time {now_ist.strftime('%H:%M:%S IST')} is at or after 09:15:00 IST market open. Pre-market prediction deadline has passed.",
                metadata={"current_time": now_ist.isoformat(), "deadline": PREMARKET_DEADLINE_TIME.isoformat()},
            )

    # 3. Input File Path provided (Manual / Verified Point-in-Time file)
    if input_file_path:
        if not input_file_path.exists():
            return DataCaptureResult(
                status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                session_date=session_date,
                feature_vector=None,
                reason=f"Supplied input file does not exist: {input_file_path}",
                metadata={"input_file": str(input_file_path)},
            )
        try:
            from nifty_ai.shadow.input_capture import load_feature_vector_from_json
            vec = load_feature_vector_from_json(input_file_path)

            # Invariant 1: Session date match
            if vec.session_date != session_date:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Input file session_date '{vec.session_date}' does not match target session '{session_date}'.",
                    metadata={"file_session_date": vec.session_date, "target_session": session_date},
                )

            # Invariant 2: Cutoff timestamp date and exact 08:50:00 IST time (Issue 3)
            if vec.cutoff_time is None or vec.cutoff_time.tzinfo is None:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason="Input file cutoff_time lacks timezone awareness.",
                    metadata={"source_file": str(input_file_path)},
                )
            file_cutoff_ist = vec.cutoff_time.astimezone(MARKET_TIMEZONE)
            target_dt = datetime.strptime(session_date, "%Y-%m-%d").date()
            if file_cutoff_ist.date() != target_dt:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Cutoff calendar date '{file_cutoff_ist.date()}' does not match target session date '{session_date}'.",
                    metadata={"file_cutoff_date": str(file_cutoff_ist.date()), "target_session": session_date},
                )
            if file_cutoff_ist.time() != SNAPSHOT_B_CUTOFF_TIME:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Cutoff time '{file_cutoff_ist.time()}' does not match mandatory 08:50:00 IST boundary.",
                    metadata={"file_cutoff_time": str(file_cutoff_ist.time())},
                )

            # Invariant 3: Provenance must be strictly PROSPECTIVE_LIVE_CAPTURE or OPERATOR_ATTESTED_PROSPECTIVE
            valid_provs = {
                ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
                ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE,
            }
            if vec.provenance is None or vec.provenance.provenance_type not in valid_provs:
                prov_str = str(vec.provenance.provenance_type) if vec.provenance else "None"
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Prospective pipeline strictly rejects non-prospective provenance '{prov_str}'. "
                           f"Only prospective capture types {sorted([p.value for p in valid_provs])} are authorized.",
                    metadata={"provenance_type": prov_str},
                )

            # Invariant 4: Activation boundary check
            cutoff_utc = vec.cutoff_time.astimezone(timezone.utc)
            obs_utc = vec.provenance.observation_time.astimezone(timezone.utc)
            if cutoff_utc < ACTIVATION_BOUNDARY_UTC or obs_utc < ACTIVATION_BOUNDARY_UTC:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Input file timestamps predate system activation boundary {ACTIVATION_BOUNDARY_UTC.isoformat()}.",
                    metadata={"cutoff_utc": cutoff_utc.isoformat(), "activation_boundary": ACTIVATION_BOUNDARY_UTC.isoformat()},
                )

            # Invariant 5: Observation and availability timestamps must not exceed cutoff
            avail_utc = vec.provenance.availability_time.astimezone(timezone.utc)
            if obs_utc > cutoff_utc:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Observation time {obs_utc.isoformat()} exceeds cutoff {cutoff_utc.isoformat()}.",
                    metadata={"obs_utc": obs_utc.isoformat(), "cutoff_utc": cutoff_utc.isoformat()},
                )
            if avail_utc > cutoff_utc:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Availability time {avail_utc.isoformat()} exceeds cutoff {cutoff_utc.isoformat()}.",
                    metadata={"avail_utc": avail_utc.isoformat(), "cutoff_utc": cutoff_utc.isoformat()},
                )

            # Invariant 6: Availability must not be in the future relative to evaluation time
            now_utc = now_ist.astimezone(timezone.utc)
            if avail_utc > now_utc:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Input availability time {avail_utc.isoformat()} is in the future relative to evaluation time {now_utc.isoformat()}.",
                    metadata={"avail_utc": avail_utc.isoformat(), "now_utc": now_utc.isoformat()},
                )

            # Invariant 7: Source-level provenance manifest validation (mandatory for prospective capture)
            if not vec.provenance.source_manifest or len(vec.provenance.source_manifest) == 0:
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason="Source provenance manifest is mandatory for prospective prediction. Found empty or missing source_manifest.",
                    metadata={"source_file": str(input_file_path)},
                )

            # Invariant 8: Reject synthetic/test providers from prospective capture
            if any(sub in (vec.provenance.source_id or "").lower() for sub in ["synthetic", "test", "mock", "dummy"]):
                return DataCaptureResult(
                    status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                    session_date=session_date,
                    feature_vector=None,
                    reason=f"Vector source_id '{vec.provenance.source_id}' is a synthetic/test identifier, rejected from prospective pipeline.",
                    metadata={"source_file": str(input_file_path)},
                )

            for src in vec.provenance.source_manifest:
                if any(sub in (src.source_id or "").lower() for sub in ["synthetic", "test", "mock", "dummy"]):
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol}: provider '{src.source_id}' is a synthetic/test identifier.",
                    )
                if not src.raw_payload_hash or len(src.raw_payload_hash) != 64 or not all(c in "0123456789abcdefABCDEF" for c in src.raw_payload_hash):
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol}: raw_payload_hash must be a valid 64-character hexadecimal SHA-256 hash.",
                    )
                if src.observation_time is None or src.observation_time.tzinfo is None:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol}: observation_time lacks timezone awareness.",
                    )
                if src.availability_time is None or src.availability_time.tzinfo is None:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol}: availability_time lacks timezone awareness.",
                    )
                if src.ingestion_time is None or src.ingestion_time.tzinfo is None:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol}: ingestion_time lacks timezone awareness.",
                    )
                s_obs_utc = src.observation_time.astimezone(timezone.utc)
                s_avail_utc = src.availability_time.astimezone(timezone.utc)
                s_ingest_utc = src.ingestion_time.astimezone(timezone.utc)

                # Ordering: obs <= avail <= ingest <= now_dt
                if s_obs_utc > s_avail_utc or s_avail_utc > s_ingest_utc or s_ingest_utc > now_utc:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol}: timestamp ordering violation (obs <= avail <= ingest <= eval).",
                    )
                if s_obs_utc > cutoff_utc or s_avail_utc > cutoff_utc:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol} timestamp exceeds cutoff {cutoff_utc.isoformat()}.",
                    )
                if s_avail_utc > now_utc or s_obs_utc > now_utc:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol} timestamp is in future relative to evaluation time {now_utc.isoformat()}.",
                    )
                if s_obs_utc < ACTIVATION_BOUNDARY_UTC or s_avail_utc < ACTIVATION_BOUNDARY_UTC or s_ingest_utc < ACTIVATION_BOUNDARY_UTC:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol} timestamp precedes activation boundary {ACTIVATION_BOUNDARY_UTC.isoformat()}.",
                    )
                if src.provenance_type != vec.provenance.provenance_type or src.provenance_type not in valid_provs:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Source {src.instrument_symbol} provenance mismatch or non-prospective type '{src.provenance_type.value}'.",
                    )

            # Invariant 9: Operator Attestation Verification
            if vec.provenance.provenance_type == ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE:
                if getattr(vec.provenance, "attestation", None) is None:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason="Operator attestation is required for OPERATOR_ATTESTED_PROSPECTIVE. Self-declared input without cryptographic signature is rejected.",
                    )
                from nifty_ai.shadow.crypto import verify_attestation
                is_valid, sig_err = verify_attestation(vec, vec.provenance.attestation)
                if not is_valid:
                    return DataCaptureResult(
                        status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                        session_date=session_date,
                        feature_vector=None,
                        reason=f"Operator attestation cryptographic verification failed: {sig_err}",
                    )

            attestation_tier = "OPERATOR_ATTESTED" if vec.provenance.provenance_type == ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE else "LIVE_CAPTURE"
            return DataCaptureResult(
                status=CaptureStatus.SUCCESS,
                session_date=session_date,
                feature_vector=vec,
                reason="Loaded verified point-in-time input vector from file.",
                metadata={"source_file": str(input_file_path), "attestation_tier": attestation_tier},
            )
        except Exception as e:
            return DataCaptureResult(
                status=CaptureStatus.INVALID_POINT_IN_TIME_INPUT,
                session_date=session_date,
                feature_vector=None,
                reason=f"Failed to parse input file: {e}",
                metadata={"input_file": str(input_file_path)},
            )

    # 4. In the absence of an authenticated live broker/feed feed connection:
    # Fail-closed with DATA_SOURCE_BLOCKED rather than fabricating data
    return DataCaptureResult(
        status=CaptureStatus.DATA_SOURCE_BLOCKED,
        session_date=session_date,
        feature_vector=None,
        reason=(
            "Live market-data feed is not connected or provider unavailable. "
            "Under zero-fabrication governance, automated vector synthesis without verified "
            "feed is blocked. Supply verified point-in-time input via --input-file."
        ),
        metadata={"session_date": session_date, "cutoff_time": cutoff_time.isoformat()},
    )
