"""Strict Point-in-Time input validator for Snapshot B features.

Enforces zero look-ahead bias, exact 63-feature ordering, Phase 7 availability contracts,
and fail-closed validation semantics.
"""

from datetime import datetime, time, timezone
import hashlib
import json
import math
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    ACTIVATION_BOUNDARY_UTC,
    CANONICAL_FEATURES_63,
    CANONICAL_PRICE_FEATURES_45,
    CANONICAL_CONTEXT_FEATURES_18,
    FeatureVector,
    ProvenanceType,
    ValidationReport,
    ValidationStatus,
)

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")
SNAPSHOT_B_CUTOFF_TIME = time(8, 50, 0)
PREMARKET_DEADLINE_TIME = time(9, 15, 0)


def compute_feature_vector_hash(feature_names: List[str], feature_values: List[float]) -> str:
    """Compute deterministic SHA-256 hash of ordered feature names and values."""
    data_repr = [
        f"{name}={val:.8e}" for name, val in zip(feature_names, feature_values)
    ]
    payload = "|".join(data_repr).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class SnapshotBInputValidator:
    """Validates Snapshot B (08:50 IST) point-in-time inputs against immutable research constraints."""

    def __init__(self, activation_boundary_utc: datetime = ACTIVATION_BOUNDARY_UTC):
        self.activation_boundary_utc = activation_boundary_utc

    def validate(
        self,
        feature_vector: FeatureVector,
        current_time: Optional[datetime] = None,
        allow_historical_research: bool = False,
    ) -> ValidationReport:
        """Execute strict fail-closed validation of a Snapshot B feature vector."""
        if current_time is not None:
            if not isinstance(current_time, datetime):
                raise ValueError(f"current_time must be a datetime, got {type(current_time)}")
            if current_time.tzinfo is None:
                raise ValueError("current_time must be timezone-aware. Naive datetime is strictly prohibited.")
            now_dt = current_time.astimezone(timezone.utc)
        else:
            now_dt = datetime.now(timezone.utc)

        report = ValidationReport(
            validation_id=f"val_{feature_vector.session_date}_{now_dt.strftime('%Y%m%d_%H%M%S')}",
            session_date=feature_vector.session_date,
            evaluated_at=now_dt,
            status=ValidationStatus.PASSED,
            passed_checks=[],
            failed_checks=[],
            error_messages=[],
            is_eligible_for_inference=False,
            feature_vector_hash=feature_vector.feature_hash,
        )

        # 1. Feature count & canonical ordering check
        if len(feature_vector.feature_names) != 63:
            report.failed_checks.append("FEATURE_COUNT_63")
            report.error_messages.append(
                f"Expected exactly 63 features, found {len(feature_vector.feature_names)}"
            )
        else:
            report.passed_checks.append("FEATURE_COUNT_63")

        if tuple(feature_vector.feature_names) != CANONICAL_FEATURES_63:
            report.failed_checks.append("CANONICAL_FEATURE_ORDERING")
            report.error_messages.append(
                "Feature vector names or sequence do not match registered 63-feature canonical contract."
            )
        else:
            report.passed_checks.append("CANONICAL_FEATURE_ORDERING")

        # 2. Check value count and finiteness
        if len(feature_vector.feature_values) != 63:
            report.failed_checks.append("VALUE_COUNT_63")
            report.error_messages.append(
                f"Expected 63 numerical values, found {len(feature_vector.feature_values)}"
            )
        else:
            report.passed_checks.append("VALUE_COUNT_63")

        nan_inf_features = []
        for name, val in zip(feature_vector.feature_names, feature_vector.feature_values):
            if val is None or not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                nan_inf_features.append(name)

        if nan_inf_features:
            report.failed_checks.append("FINITE_VALUES")
            report.error_messages.append(
                f"Invalid or non-finite values found in features: {nan_inf_features}"
            )
        else:
            report.passed_checks.append("FINITE_VALUES")

        # 3. Check for forbidden columns
        forbidden_detected = []
        forbidden_exact = {
            "open", "high", "low", "close", "target", "t0", "t0_return",
            "current_session_open", "current_session_high", "current_session_low",
            "current_session_close", "current_session_return", "same_day_return"
        }
        for name in feature_vector.feature_names:
            lower = name.lower()
            if any(forbidden in lower for forbidden in ["news", "sentiment", "volume", "flow", "fii", "dii"]):
                forbidden_detected.append(name)
            elif lower in forbidden_exact or lower.startswith("current_session_"):
                forbidden_detected.append(name)

        if forbidden_detected:
            report.failed_checks.append("FORBIDDEN_COLUMNS")
            report.error_messages.append(
                f"Forbidden feature families or current-session targets detected: {forbidden_detected}"
            )
        else:
            report.passed_checks.append("FORBIDDEN_COLUMNS")

        # 4. Timezone Awareness Check
        tz_errors = []
        if feature_vector.cutoff_time is None or feature_vector.cutoff_time.tzinfo is None:
            tz_errors.append("cutoff_time lacks timezone awareness")
        if feature_vector.provenance.observation_time is None or feature_vector.provenance.observation_time.tzinfo is None:
            tz_errors.append("observation_time lacks timezone awareness")
        if feature_vector.provenance.availability_time is None or feature_vector.provenance.availability_time.tzinfo is None:
            tz_errors.append("availability_time lacks timezone awareness")

        if tz_errors:
            report.failed_checks.append("TIMEZONE_AWARENESS")
            report.error_messages.append(f"Timezone-naive or missing timestamp detected: {tz_errors}")
            report.status = ValidationStatus.FAILED
            report.is_eligible_for_inference = False
            return report
        else:
            report.passed_checks.append("TIMEZONE_AWARENESS")

        # 5. Point-in-time Cutoff and Evaluation Window Checks
        try:
            target_session_dt = datetime.strptime(feature_vector.session_date, "%Y-%m-%d").date()
        except ValueError:
            report.failed_checks.append("SESSION_DATE_FORMAT")
            report.error_messages.append(f"Invalid session date format '{feature_vector.session_date}'.")
            report.status = ValidationStatus.FAILED
            report.is_eligible_for_inference = False
            return report

        expected_cutoff = datetime.combine(target_session_dt, SNAPSHOT_B_CUTOFF_TIME, tzinfo=MARKET_TIMEZONE)
        cutoff_ist = feature_vector.cutoff_time.astimezone(MARKET_TIMEZONE)

        # Invariant: Cutoff calendar date must match target session date (Issue 3)
        if cutoff_ist.date() != target_session_dt:
            report.failed_checks.append("CUTOFF_DATE_MISMATCH")
            report.error_messages.append(
                f"Cutoff calendar date '{cutoff_ist.date()}' does not match target session date '{target_session_dt}'."
            )
        else:
            report.passed_checks.append("CUTOFF_DATE_MISMATCH")

        # Invariant: Cutoff time must be exactly 08:50:00 IST
        if cutoff_ist.time() != SNAPSHOT_B_CUTOFF_TIME:
            report.failed_checks.append("CUTOFF_TIME_ENFORCEMENT")
            report.error_messages.append(
                f"Cutoff time '{cutoff_ist.time()}' does not match mandatory 08:50:00 IST Snapshot B boundary. "
                f"Pre-cutoff observations cannot substitute for the 08:50 information set."
            )
        else:
            report.passed_checks.append("CUTOFF_TIME_ENFORCEMENT")

        # Invariant: Evaluation time must be AT OR AFTER cutoff (Issue 1)
        eval_ist = now_dt.astimezone(MARKET_TIMEZONE)
        eval_date = eval_ist.date()

        # Invariant: Reject future session dates relative to effective evaluation date
        if target_session_dt > eval_date:
            report.failed_checks.append("FUTURE_SESSION_DATE")
            report.error_messages.append(
                f"Target session date '{target_session_dt}' is in the future relative to effective evaluation date '{eval_date}'. "
                f"Prospective Snapshot B predictions cannot be evaluated in advance."
            )
        else:
            report.passed_checks.append("FUTURE_SESSION_DATE")

        # Invariant: Reject past session dates relative to effective evaluation date (unless explicitly authorized for research)
        if target_session_dt < eval_date and not allow_historical_research:
            report.failed_checks.append("PAST_SESSION_DATE")
            report.error_messages.append(
                f"Target session date '{target_session_dt}' is in the past relative to effective evaluation date '{eval_date}'. "
                f"Backdating prospective predictions is strictly prohibited."
            )
        else:
            report.passed_checks.append("PAST_SESSION_DATE")

        if eval_ist < expected_cutoff:
            report.failed_checks.append("EVALUATION_AFTER_CUTOFF")
            report.error_messages.append(
                f"Evaluation time {eval_ist.strftime('%H:%M:%S IST')} is before 08:50:00 IST information cutoff. "
                f"Prospective Snapshot B predictions cannot be generated prematurely."
            )
        else:
            report.passed_checks.append("EVALUATION_AFTER_CUTOFF")

        # Invariant: Evaluation time must be BEFORE 09:15:00 IST market open deadline (Issue 1 & 2)
        premarket_deadline = datetime.combine(target_session_dt, PREMARKET_DEADLINE_TIME, tzinfo=MARKET_TIMEZONE)
        if eval_ist >= premarket_deadline:
            report.failed_checks.append("PREMARKET_DEADLINE_ENFORCEMENT")
            report.error_messages.append(
                f"Evaluation time {eval_ist.strftime('%H:%M:%S IST')} is at or after 09:15:00 IST market open deadline. "
                f"Pre-market prospective prediction window has closed."
            )
        else:
            report.passed_checks.append("PREMARKET_DEADLINE_ENFORCEMENT")

        # 6. Availability and Observation timestamp checks
        avail_ist = feature_vector.provenance.availability_time.astimezone(MARKET_TIMEZONE)
        if avail_ist > cutoff_ist:
            report.failed_checks.append("AVAILABILITY_PRIOR_TO_CUTOFF")
            report.error_messages.append(
                f"Input availability time {avail_ist.isoformat()} is after cutoff {cutoff_ist.isoformat()}."
            )
        else:
            report.passed_checks.append("AVAILABILITY_PRIOR_TO_CUTOFF")

        obs_utc = feature_vector.provenance.observation_time.astimezone(timezone.utc)
        avail_utc = feature_vector.provenance.availability_time.astimezone(timezone.utc)
        cutoff_utc = feature_vector.cutoff_time.astimezone(timezone.utc)

        # Verification against 08:50 cutoff boundary
        if obs_utc > cutoff_utc:
            report.failed_checks.append("OBSERVATION_TIME_VALIDITY")
            report.error_messages.append(
                f"Future observation timestamp detected: observation time {obs_utc.isoformat()} is after cutoff {cutoff_utc.isoformat()}."
            )
        else:
            report.passed_checks.append("OBSERVATION_TIME_VALIDITY")

        # Verification against actual pipeline evaluation time (Issue 3)
        if avail_utc > now_dt:
            report.failed_checks.append("AVAILABILITY_PRIOR_TO_EVALUATION")
            report.error_messages.append(
                f"Input availability time {avail_utc.isoformat()} is in the future relative to evaluation time {now_dt.isoformat()}."
            )
        else:
            report.passed_checks.append("AVAILABILITY_PRIOR_TO_EVALUATION")

        if obs_utc > now_dt:
            report.failed_checks.append("OBSERVATION_PRIOR_TO_EVALUATION")
            report.error_messages.append(
                f"Observation time {obs_utc.isoformat()} is in the future relative to evaluation time {now_dt.isoformat()}."
            )
        else:
            report.passed_checks.append("OBSERVATION_PRIOR_TO_EVALUATION")

        if obs_utc > avail_utc:
            report.failed_checks.append("OBSERVATION_BEFORE_AVAILABILITY")
            report.error_messages.append(
                f"Observation timestamp {obs_utc.isoformat()} post-dates availability timestamp {avail_utc.isoformat()}."
            )
        else:
            report.passed_checks.append("OBSERVATION_BEFORE_AVAILABILITY")

        # Stale Source Check (Max 7 calendar days before cutoff)
        staleness_delta = cutoff_utc - obs_utc
        if staleness_delta.total_seconds() > 7 * 86400:
            report.failed_checks.append("STALE_SOURCE_DATA")
            report.error_messages.append(
                f"Source observation is excessively stale ({staleness_delta.days} days old; maximum permitted is 7 days)."
            )
        else:
            report.passed_checks.append("STALE_SOURCE_DATA")

        # 6. Provenance & Activation Boundary check
        prov = feature_vector.provenance
        if prov.provenance_type == ProvenanceType.PROSPECTIVE_LIVE_CAPTURE:
            obs_utc = prov.observation_time.astimezone(timezone.utc)
            if obs_utc < self.activation_boundary_utc:
                report.failed_checks.append("ACTIVATION_BOUNDARY_PROSPECTIVE")
                report.error_messages.append(
                    f"Observation timestamp {obs_utc.isoformat()} is prior to system activation boundary "
                    f"{self.activation_boundary_utc.isoformat()}. Cannot classify as prospective_live_capture."
                )
            else:
                report.passed_checks.append("ACTIVATION_BOUNDARY_PROSPECTIVE")
        else:
            report.passed_checks.append("ACTIVATION_BOUNDARY_PROSPECTIVE")

        # 7. Hash integrity check
        expected_hash = compute_feature_vector_hash(
            feature_vector.feature_names, feature_vector.feature_values
        )
        if feature_vector.feature_hash != expected_hash:
            report.failed_checks.append("FEATURE_HASH_INTEGRITY")
            report.error_messages.append(
                f"Feature vector hash mismatch: declared {feature_vector.feature_hash} != computed {expected_hash}"
            )
        else:
            report.passed_checks.append("FEATURE_HASH_INTEGRITY")

        # 8. Source-Level Provenance Manifest Validation
        if prov and getattr(prov, "source_manifest", None):
            manifest_errors = []
            covered_features = set()

            for src in prov.source_manifest:
                covered_features.update(src.feature_names)

                # Timezone awareness
                if src.observation_time is None or src.observation_time.tzinfo is None:
                    manifest_errors.append(f"Source {src.instrument_symbol}: observation_time lacks timezone awareness.")
                if src.availability_time is None or src.availability_time.tzinfo is None:
                    manifest_errors.append(f"Source {src.instrument_symbol}: availability_time lacks timezone awareness.")
                if src.ingestion_time is None or src.ingestion_time.tzinfo is None:
                    manifest_errors.append(f"Source {src.instrument_symbol}: ingestion_time lacks timezone awareness.")

                if manifest_errors:
                    continue

                src_obs_utc = src.observation_time.astimezone(timezone.utc)
                src_avail_utc = src.availability_time.astimezone(timezone.utc)
                cutoff_utc = expected_cutoff.astimezone(timezone.utc)

                # 1. 08:50 IST information cutoff
                if src_obs_utc > cutoff_utc:
                    manifest_errors.append(
                        f"Source {src.instrument_symbol}: observation time {src_obs_utc.isoformat()} is after cutoff {cutoff_utc.isoformat()}."
                    )
                if src_avail_utc > cutoff_utc:
                    manifest_errors.append(
                        f"Source {src.instrument_symbol}: availability time {src_avail_utc.isoformat()} is after cutoff {cutoff_utc.isoformat()}."
                    )

                # 2. Actual inference evaluation time
                if src_avail_utc > now_dt:
                    manifest_errors.append(
                        f"Source {src.instrument_symbol}: availability time {src_avail_utc.isoformat()} is in future relative to evaluation time {now_dt.isoformat()}."
                    )
                if src_obs_utc > now_dt:
                    manifest_errors.append(
                        f"Source {src.instrument_symbol}: observation time {src_obs_utc.isoformat()} is in future relative to evaluation time {now_dt.isoformat()}."
                    )

                # 3. Maximum permitted staleness (7 calendar days = 604,800 seconds)
                MAX_PERMITTED_STALENESS = 7 * 86400.0
                src_staleness = (cutoff_utc - src_obs_utc).total_seconds()
                if src_staleness > MAX_PERMITTED_STALENESS:
                    manifest_errors.append(
                        f"Source {src.instrument_symbol}: staleness {src_staleness:.0f}s exceeds maximum permitted {MAX_PERMITTED_STALENESS:.0f}s."
                    )
                if src_staleness < 0:
                    manifest_errors.append(
                        f"Source {src.instrument_symbol}: negative staleness (observation in future relative to cutoff)."
                    )

                # 4. System activation boundary
                if src.provenance_type in {ProvenanceType.PROSPECTIVE_LIVE_CAPTURE, ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE}:
                    if src_obs_utc < self.activation_boundary_utc or src_avail_utc < self.activation_boundary_utc:
                        manifest_errors.append(
                            f"Source {src.instrument_symbol}: timestamp precedes system activation boundary {self.activation_boundary_utc.isoformat()}."
                        )

                # 5. Provenance classification
                if src.provenance_type not in {ProvenanceType.PROSPECTIVE_LIVE_CAPTURE, ProvenanceType.OPERATOR_ATTESTED_PROSPECTIVE}:
                    manifest_errors.append(
                        f"Source {src.instrument_symbol}: non-prospective provenance '{src.provenance_type.value}'."
                    )

            # Check coverage of canonical 63 features
            missing_manifest_features = set(CANONICAL_FEATURES_63) - covered_features
            if missing_manifest_features:
                manifest_errors.append(
                    f"Source manifest incomplete: {len(missing_manifest_features)} features lack source provenance."
                )

            if manifest_errors:
                report.failed_checks.append("SOURCE_PROVENANCE_MANIFEST")
                report.error_messages.extend(manifest_errors)
            else:
                report.passed_checks.append("SOURCE_PROVENANCE_MANIFEST")

        # Final determination
        if report.failed_checks:
            report.status = ValidationStatus.FAILED
            report.is_eligible_for_inference = False
        else:
            report.status = ValidationStatus.PASSED
            report.is_eligible_for_inference = True

        return report
