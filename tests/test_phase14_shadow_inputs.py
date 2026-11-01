"""Tests for Phase 14 Step 2: Point-in-Time Snapshot B Input Capture & Validation."""

from datetime import datetime, time, timezone
import pytest
from zoneinfo import ZoneInfo

from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    FeatureVector,
    ProvenanceType,
    SourceProvenance,
    ValidationStatus,
)
from nifty_ai.shadow.input_capture import (
    build_synthetic_feature_vector,
    build_verified_prospective_feature_vector,
)
from nifty_ai.shadow.input_validator import (
    ACTIVATION_BOUNDARY_UTC,
    SnapshotBInputValidator,
    compute_feature_vector_hash,
)

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def test_valid_synthetic_feature_vector_passes():
    validator = SnapshotBInputValidator()
    # Create valid prospective feature vector after activation boundary
    vec = build_verified_prospective_feature_vector(
        session_date="2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    report = validator.validate(vec, current_time=eval_time)
    assert report.status == ValidationStatus.PASSED
    assert report.is_eligible_for_inference is True
    assert len(report.failed_checks) == 0


def test_validator_rejects_future_session_date_without_current_time():
    validator = SnapshotBInputValidator()
    # Future session date evaluated at real clock time
    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    report = validator.validate(vec)  # current_time is None
    assert report.status == ValidationStatus.FAILED
    assert "FUTURE_SESSION_DATE" in report.failed_checks
    assert report.is_eligible_for_inference is False


def test_validator_rejects_naive_current_time():
    validator = SnapshotBInputValidator()
    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
    )
    naive_eval = datetime(2026, 11, 2, 8, 52, 0)
    with pytest.raises(ValueError, match="current_time must be timezone-aware"):
        validator.validate(vec, current_time=naive_eval)


def test_cutoff_exceeded_fails():
    validator = SnapshotBInputValidator()
    # Cutoff at 08:55 IST (exceeds 08:50:00 IST boundary)
    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        cutoff_time=datetime(2026, 11, 2, 8, 55, 0, tzinfo=MARKET_TIMEZONE),
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "CUTOFF_TIME_ENFORCEMENT" in report.failed_checks
    assert report.is_eligible_for_inference is False


def test_availability_after_cutoff_fails():
    validator = SnapshotBInputValidator()
    # Availability at 08:51 IST (after 08:50 cutoff)
    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        availability_time=datetime(2026, 11, 2, 8, 51, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "AVAILABILITY_PRIOR_TO_CUTOFF" in report.failed_checks


def test_invalid_feature_count_or_ordering_fails():
    validator = SnapshotBInputValidator()
    # 62 features instead of 63
    names_62 = list(CANONICAL_FEATURES_63[:-1])
    vals_62 = [0.01] * 62
    vec = FeatureVector(
        session_date="2026-11-02",
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        feature_names=names_62,
        feature_values=vals_62,
        feature_hash=compute_feature_vector_hash(names_62, vals_62),
        provenance=SourceProvenance(
            source_id="test",
            observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
            availability_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
            ingestion_time=datetime.now(timezone.utc),
            provenance_type=ProvenanceType.HISTORICAL_BACKFILL,
        ),
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "FEATURE_COUNT_63" in report.failed_checks


def test_forbidden_columns_rejected():
    validator = SnapshotBInputValidator()
    names = list(CANONICAL_FEATURES_63)
    names[0] = "current_session_close"  # Forbidden target column
    vals = [0.01] * 63
    vec = FeatureVector(
        session_date="2026-11-02",
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        feature_names=names,
        feature_values=vals,
        feature_hash=compute_feature_vector_hash(names, vals),
        provenance=SourceProvenance(
            source_id="test",
            observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
            availability_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
            ingestion_time=datetime.now(timezone.utc),
            provenance_type=ProvenanceType.HISTORICAL_BACKFILL,
        ),
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "FORBIDDEN_COLUMNS" in report.failed_checks


def test_nan_or_inf_values_rejected():
    validator = SnapshotBInputValidator()
    vals = [0.01] * 63
    vals[5] = float("nan")
    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        feature_values=vals,
        provenance_type=ProvenanceType.HISTORICAL_BACKFILL,
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "FINITE_VALUES" in report.failed_checks


def test_activation_boundary_enforcement():
    validator = SnapshotBInputValidator()
    # Observation before activation boundary (e.g. October 15, 2026) marked as prospective
    vec = build_synthetic_feature_vector(
        session_date="2026-10-15",
        observation_time=datetime(2026, 10, 15, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 10, 15, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 10, 15, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    report = validator.validate(vec)
    assert report.status == ValidationStatus.FAILED
    assert "ACTIVATION_BOUNDARY_PROSPECTIVE" in report.failed_checks


def test_load_feature_vector_from_json(tmp_path):
    from pathlib import Path
    import json
    from nifty_ai.shadow.input_capture import load_feature_vector_from_json

    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    json_path = tmp_path / "test_vec.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(vec.to_dict(), f)

    loaded = load_feature_vector_from_json(json_path)
    assert loaded.session_date == vec.session_date
    assert len(loaded.feature_values) == 63
    assert loaded.feature_hash == vec.feature_hash
    assert loaded.provenance.source_id == vec.provenance.source_id

