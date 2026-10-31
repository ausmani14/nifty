"""Tests for Phase 16 Workflow Hotfix: Security, Git Operations, and Pages Deployment."""

from datetime import datetime, time, timezone
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import MagicMock, patch
import pytest
from zoneinfo import ZoneInfo

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    CANONICAL_META_SHA256,
    CANONICAL_MODEL_SHA256,
    LedgerStatus,
    ProvenanceType,
    ValidationStatus,
)
from nifty_ai.shadow.inference import ShadowInferenceRunner
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector
from nifty_ai.shadow.input_validator import (
    SNAPSHOT_B_CUTOFF_TIME,
    SnapshotBInputValidator,
)
from nifty_ai.shadow.ledger import ShadowPredictionLedger
from nifty_ai.shadow.live_data import (
    CaptureStatus,
    attempt_live_feature_capture,
)
from nifty_ai.shadow.model_protection import assert_frozen_model_intact
from nifty_ai.shadow.reconciliation import ShadowOutcomeReconciler
from nifty_ai.shadow.website_exporter import WebsiteDataExporter
from scripts.git_commit_and_push import AUTHORIZED_STAGE_PATHS, perform_safe_commit_and_push
from scripts.validate_workflow_inputs import (
    ALLOWED_OPERATIONS,
    SCHEDULE_CRON_MAP,
    validate_and_classify_inputs,
    write_github_outputs,
)
from scripts.verify_web_artifacts import REQUIRED_JSON_CONTRACTS, verify_web_artifacts

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# 1. Safe Workflow Input Handling & 2. Operation Allowlist
# ---------------------------------------------------------------------------

def test_workflow_dispatch_valid_operations():
    """Verify that every allowed operation is accepted for workflow_dispatch."""
    for op in ALLOWED_OPERATIONS:
        res_op, res_date, res_file = validate_and_classify_inputs(
            event_name="workflow_dispatch",
            input_operation=op,
            input_session_date="",
            input_file="",
        )
        assert res_op == op
        assert res_date == ""
        assert res_file == ""


def test_workflow_dispatch_operation_allowlist_rejection():
    """Verify that unapproved operations are strictly rejected."""
    unapproved = ["train_model", "delete_all", "eval", "arbitrary_cmd", "snapshot_c"]
    for bad_op in unapproved:
        with pytest.raises(ValueError, match="Invalid operation"):
            validate_and_classify_inputs(
                event_name="workflow_dispatch",
                input_operation=bad_op,
            )


# ---------------------------------------------------------------------------
# 3. Malicious Input Rejection (Metacharacters & Newlines)
# ---------------------------------------------------------------------------

def test_rejects_shell_metacharacters_in_session_date():
    """Verify that shell injection tokens in session_date are rejected."""
    malicious_dates = [
        "2026-11-02; rm -rf /",
        "2026-11-02 | echo hacked",
        "2026-11-02 && touch pwned",
        "2026-11-02`reboot`",
        "2026-11-02$(whoami)",
        "2026-11-02\nOP=malicious",
        "2026-11-02\r\n",
    ]
    for bad_date in malicious_dates:
        with pytest.raises(ValueError):
            validate_and_classify_inputs(
                event_name="workflow_dispatch",
                input_operation="snapshot_b",
                input_session_date=bad_date,
            )


def test_rejects_malformed_calendar_dates():
    """Verify that invalid calendar dates (e.g. Feb 31, Month 13) are rejected."""
    bad_dates = ["2026-02-31", "2026-13-01", "2026-00-10", "not-a-date", "2026/11/02"]
    for bad_date in bad_dates:
        with pytest.raises(ValueError):
            validate_and_classify_inputs(
                event_name="workflow_dispatch",
                input_operation="snapshot_b",
                input_session_date=bad_date,
            )


# ---------------------------------------------------------------------------
# 4. Path Traversal & Absolute Path Rejection
# ---------------------------------------------------------------------------

def test_rejects_path_traversal_and_absolute_paths(tmp_path: Path):
    """Verify that directory traversal and absolute paths are rejected for input_file."""
    bad_files = [
        "../secret.key",
        "../../etc/passwd",
        "/etc/shadow",
        "C:\\Windows\\system32\\cmd.exe",
        "scripts/../../outside.json",
        "data/test.json; rm -rf /",
        "data/test.json\nOP=hacked",
    ]
    for bad_file in bad_files:
        with pytest.raises(ValueError):
            validate_and_classify_inputs(
                event_name="workflow_dispatch",
                input_operation="snapshot_b",
                input_file=bad_file,
                repo_root=tmp_path,
            )


def test_accepts_valid_repo_relative_existing_file(tmp_path: Path):
    """Verify that a legitimate repository-relative existing file is accepted."""
    sub_dir = tmp_path / "data" / "inputs"
    sub_dir.mkdir(parents=True)
    sample_file = sub_dir / "test_vector.json"
    sample_file.write_text('{"test": true}', encoding="utf-8")

    op, date_arg, file_arg = validate_and_classify_inputs(
        event_name="workflow_dispatch",
        input_operation="snapshot_b",
        input_file="data/inputs/test_vector.json",
        repo_root=tmp_path,
    )
    assert op == "snapshot_b"
    assert file_arg == "data/inputs/test_vector.json"


# ---------------------------------------------------------------------------
# 5. Correct Scheduled Cron Identification & 6. Delayed Morning Run Handling
# ---------------------------------------------------------------------------

def test_scheduled_cron_mapping():
    """Verify schedule cron strings map precisely to expected operations."""
    # Morning Snapshot B
    op1, _, _ = validate_and_classify_inputs(event_name="schedule", schedule_cron="5 3 * * 1-5")
    assert op1 == "snapshot_b"

    # Afternoon Reconcile
    op2, _, _ = validate_and_classify_inputs(event_name="schedule", schedule_cron="10 10 * * 1-5")
    assert op2 == "reconcile_outcomes"


def test_rejects_unknown_schedule_cron():
    """Verify unknown or unmapped cron expressions are rejected."""
    with pytest.raises(ValueError, match="Unrecognized schedule cron"):
        validate_and_classify_inputs(event_name="schedule", schedule_cron="0 0 * * *")


def test_delayed_morning_cron_never_becomes_reconcile():
    """Verify that morning cron classification is immutable regardless of runner wall-clock time."""
    # The classification depends purely on schedule_cron, NOT on datetime.now()
    op, _, _ = validate_and_classify_inputs(event_name="schedule", schedule_cron="5 3 * * 1-5")
    assert op == "snapshot_b"
    assert op != "reconcile_outcomes"


# ---------------------------------------------------------------------------
# 7. Missed 08:50 Cutoff Gate
# ---------------------------------------------------------------------------

def test_missed_cutoff_fails_closed():
    """Verify attempt_live_feature_capture returns MISSED_CUTOFF at or after 09:15 IST for today."""
    session_date = "2026-11-02"  # Monday
    # Simulate time at 09:20:00 IST (past 09:15 market open deadline)
    simulated_late_time = datetime(2026, 11, 2, 9, 20, 0, tzinfo=MARKET_TIMEZONE)

    res = attempt_live_feature_capture(
        session_date=session_date,
        current_time=simulated_late_time,
    )
    assert res.status == CaptureStatus.MISSED_CUTOFF
    assert "at or after 09:15:00 IST" in res.reason


def test_premature_evaluation_fails_closed():
    """Verify attempt_live_feature_capture returns PREMATURE_EVALUATION before 08:50 IST for today."""
    session_date = "2026-11-02"  # Monday
    simulated_early_time = datetime(2026, 11, 2, 8, 35, 0, tzinfo=MARKET_TIMEZONE)

    res = attempt_live_feature_capture(
        session_date=session_date,
        current_time=simulated_early_time,
    )
    assert res.status == CaptureStatus.PREMATURE_EVALUATION
    assert "before 08:50:00 IST" in res.reason


# ---------------------------------------------------------------------------
# 8. Git Staging, 9. Rebase Conflict, 10. Push Retries
# ---------------------------------------------------------------------------

def test_git_script_authorized_stage_paths():
    """Verify the exact authorized files staged by git_commit_and_push."""
    expected = [
        "data/interim/phase14_shadow/shadow_predictions_ledger.jsonl",
        "data/interim/phase14_shadow/shadow_outcomes_ledger.jsonl",
        "website_data",
        "web/data",
        "index.html",
    ]
    assert AUTHORIZED_STAGE_PATHS == expected


@patch("scripts.git_commit_and_push.run_git")
def test_git_push_aborts_on_unexpected_branch(mock_git):
    """Verify perform_safe_commit_and_push exits non-zero if branch is not master."""
    mock_git.return_value = MagicMock(returncode=0, stdout="feature-branch\n")
    ret = perform_safe_commit_and_push()
    assert ret == 1


@patch("scripts.git_commit_and_push.run_git")
def test_git_push_handles_rebase_conflict(mock_git):
    """Verify perform_safe_commit_and_push aborts rebase and exits non-zero on conflict."""
    # 1. branch rev-parse: master
    # 2. add paths: success
    # 3. diff staged: changes exist (returncode 1)
    # 4. commit: success
    # 5. fetch: success
    # 6. rebase: conflict (returncode 1)
    def git_side_effect(args, check=True):
        cmd = args[0]
        if cmd == "rev-parse":
            return MagicMock(returncode=0, stdout="master\n")
        if cmd == "add":
            return MagicMock(returncode=0, stdout="", stderr="")
        if cmd == "diff":
            return MagicMock(returncode=1, stdout="", stderr="")
        if cmd == "commit":
            return MagicMock(returncode=0, stdout="", stderr="")
        if cmd == "fetch":
            return MagicMock(returncode=0, stdout="", stderr="")
        if cmd == "rebase" and args[1] == "origin/master":
            return MagicMock(returncode=1, stderr="CONFLICT (content): Merge conflict in file")
        if cmd == "rebase" and args[1] == "--abort":
            return MagicMock(returncode=0, stdout="", stderr="")
        return MagicMock(returncode=0, stdout="", stderr="")

    mock_git.side_effect = git_side_effect
    ret = perform_safe_commit_and_push(max_retries=1)
    assert ret == 1
    # Verify git rebase --abort was executed
    abort_calls = [c for c in mock_git.call_args_list if c[0][0] == ["rebase", "--abort"]]
    assert len(abort_calls) >= 1


@patch("scripts.git_commit_and_push.run_git")
def test_git_push_retries_exhausted_exits_nonzero(mock_git):
    """Verify perform_safe_commit_and_push exits non-zero when all push retries fail."""
    def git_side_effect(args, check=True):
        cmd = args[0]
        if cmd == "rev-parse":
            return MagicMock(returncode=0, stdout="master\n")
        if cmd == "add":
            return MagicMock(returncode=0)
        if cmd == "diff":
            return MagicMock(returncode=1)
        if cmd == "commit":
            return MagicMock(returncode=0)
        if cmd == "fetch":
            return MagicMock(returncode=0)
        if cmd == "rebase":
            return MagicMock(returncode=0)
        if cmd == "push":
            return MagicMock(returncode=1, stderr="fatal: remote rejected")
        return MagicMock(returncode=0)

    mock_git.side_effect = git_side_effect
    ret = perform_safe_commit_and_push(max_retries=3, retry_delay_seconds=0.01)
    assert ret == 1


# ---------------------------------------------------------------------------
# 11. Pages Artifact Contents & 12. Deployment Failure Reporting
# ---------------------------------------------------------------------------

def test_web_artifacts_verification_passes_on_current_repo():
    """Verify verify_web_artifacts passes on current repository web/ contents."""
    assert verify_web_artifacts() is True


def test_web_artifacts_verification_fails_if_json_missing(tmp_path: Path):
    """Verify verify_web_artifacts fails closed if any JSON contract is missing."""
    fake_web = tmp_path / "web"
    fake_web.mkdir()
    (fake_web / "index.html").write_text("<html></html>", encoding="utf-8")
    (fake_web / "style.css").write_text("body {}", encoding="utf-8")
    (fake_web / "app.js").write_text("console.log()", encoding="utf-8")
    (fake_web / "data").mkdir()
    # Write only 5 of 6 contracts
    for name in REQUIRED_JSON_CONTRACTS[:-1]:
        (fake_web / "data" / name).write_text("{}", encoding="utf-8")

    assert verify_web_artifacts(web_dir=fake_web) is False


def test_web_artifacts_verification_fails_if_json_invalid(tmp_path: Path):
    """Verify verify_web_artifacts fails closed if any JSON contract is corrupt."""
    fake_web = tmp_path / "web"
    fake_web.mkdir()
    (fake_web / "index.html").write_text("<html></html>", encoding="utf-8")
    (fake_web / "style.css").write_text("body {}", encoding="utf-8")
    (fake_web / "app.js").write_text("console.log()", encoding="utf-8")
    (fake_web / "data").mkdir()
    for name in REQUIRED_JSON_CONTRACTS:
        (fake_web / "data" / name).write_text("{}", encoding="utf-8")
    # Corrupt one contract
    (fake_web / "data" / "system_status.json").write_text("{corrupt json", encoding="utf-8")

    assert verify_web_artifacts(web_dir=fake_web) is False


# ---------------------------------------------------------------------------
# 13. Empty Dashboard State & 14. Relative JSON Paths
# ---------------------------------------------------------------------------

def test_empty_dashboard_state_integrity():
    """Verify that genesis/empty ledger exports display NO VALID PROSPECTIVE PREDICTION."""
    exporter = WebsiteDataExporter()
    exported = exporter.export_all()

    with open(exported["latest_prediction"], "r", encoding="utf-8") as f:
        lp = json.load(f)
    assert lp["has_prediction"] is False
    assert lp["prediction_status"] == "NO VALID PROSPECTIVE PREDICTION"
    assert lp["model_sha256"] == CANONICAL_MODEL_SHA256

    with open(exported["prediction_history"], "r", encoding="utf-8") as f:
        ph = json.load(f)
    assert ph["total_count"] == 0
    assert ph["predictions"] == []

    with open(exported["outcome_history"], "r", encoding="utf-8") as f:
        oh = json.load(f)
    assert oh["total_count"] == 0
    assert oh["outcomes"] == []


def test_web_app_uses_relative_asset_and_data_paths():
    """Verify that index.html and app.js use relative paths for subpath hosting."""
    index_html = (PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'href="style.css"' in index_html
    assert 'src="app.js"' in index_html
    assert not 'href="/style.css"' in index_html
    assert not 'src="/app.js"' in index_html

    app_js = (PROJECT_ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert "data/${filename}" in app_js
    assert "./data/${filename}" in app_js
    assert not '"/data/' in app_js


# ---------------------------------------------------------------------------
# Model Integrity & Invariants Guard
# ---------------------------------------------------------------------------

def test_frozen_model_and_metadata_invariants():
    """Re-verify frozen model hash, metadata hash, 43 trees, 63 features."""
    rep = assert_frozen_model_intact()
    assert rep.model_sha256 == CANONICAL_MODEL_SHA256
    assert rep.meta_sha256 == CANONICAL_META_SHA256
    assert rep.n_estimators == 43
    assert rep.feature_count == 63


# ---------------------------------------------------------------------------
# Final Hotfix Governance & Regression Tests (Issues 1-5)
# ---------------------------------------------------------------------------

def test_evaluation_time_future_availability_rejected():
    """ISSUE 3: Availability in future relative to evaluation time is rejected even if before cutoff."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 35, 0, tzinfo=MARKET_TIMEZONE)
    # Observation at 08:30, available at 08:45, cutoff at 08:50
    # Available at 08:45 is in the future relative to evaluation at 08:35!
    vec = build_synthetic_feature_vector(
        session_date="2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 30, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    report = validator.validate(vec, current_time=eval_time)
    assert report.status == ValidationStatus.FAILED
    assert "AVAILABILITY_PRIOR_TO_EVALUATION" in report.failed_checks
    assert any("in the future relative to evaluation time" in err for err in report.error_messages)


def test_regression_historical_date_plus_input_file_rejected(tmp_path: Path):
    """ISSUE 2 Regr 1: Past session date with input file is strictly rejected."""
    in_file = tmp_path / "past_vector.json"
    vec = build_synthetic_feature_vector(
        session_date="2024-01-05",
        observation_time=datetime(2024, 1, 5, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2024, 1, 5, 8, 48, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2024, 1, 5, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    in_file.write_text(json.dumps(vec.to_dict()), encoding="utf-8")

    # Current time is in 2026
    current_time = datetime(2026, 11, 2, 8, 35, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture(
        session_date="2024-01-05",
        input_file_path=in_file,
        current_time=current_time,
    )
    assert res.status == CaptureStatus.MISSED_CUTOFF
    assert "Backdating is strictly prohibited" in res.reason


def test_regression_historical_backfill_provenance_rejected(tmp_path: Path):
    """ISSUE 2 Regr 2: Input file with historical_backfill provenance is strictly rejected."""
    today_str = "2026-11-02"
    in_file = tmp_path / "backfill_vector.json"
    vec = build_synthetic_feature_vector(
        session_date=today_str,
        observation_time=datetime(2026, 11, 2, 8, 30, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 32, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.HISTORICAL_BACKFILL,
    )
    in_file.write_text(json.dumps(vec.to_dict()), encoding="utf-8")

    current_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture(
        session_date=today_str,
        input_file_path=in_file,
        current_time=current_time,
    )
    assert res.status == CaptureStatus.INVALID_POINT_IN_TIME_INPUT
    assert "strictly rejects non-prospective provenance" in res.reason


def test_regression_retrospective_reference_provenance_rejected(tmp_path: Path):
    """ISSUE 2 Regr 3: Input file with retrospective_reference provenance is rejected."""
    today_str = "2026-11-02"
    in_file = tmp_path / "retro_vector.json"
    vec = build_synthetic_feature_vector(
        session_date=today_str,
        observation_time=datetime(2026, 11, 2, 8, 30, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 32, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.RETROSPECTIVE_REFERENCE,
    )
    in_file.write_text(json.dumps(vec.to_dict()), encoding="utf-8")

    current_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture(
        session_date=today_str,
        input_file_path=in_file,
        current_time=current_time,
    )
    assert res.status == CaptureStatus.INVALID_POINT_IN_TIME_INPUT
    assert "strictly rejects non-prospective provenance" in res.reason


def test_regression_invalid_or_quarantined_provenance_rejected(tmp_path: Path):
    """ISSUE 2 Regr 4: Input file with invalid_or_quarantined provenance is rejected."""
    today_str = "2026-11-02"
    in_file = tmp_path / "quarantined_vector.json"
    vec = build_synthetic_feature_vector(
        session_date=today_str,
        observation_time=datetime(2026, 11, 2, 8, 30, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 32, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.INVALID_OR_QUARANTINED,
    )
    in_file.write_text(json.dumps(vec.to_dict()), encoding="utf-8")

    current_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture(
        session_date=today_str,
        input_file_path=in_file,
        current_time=current_time,
    )
    assert res.status == CaptureStatus.INVALID_POINT_IN_TIME_INPUT
    assert "strictly rejects non-prospective provenance" in res.reason


def test_regression_past_session_file_attempting_bypass_rejected(tmp_path: Path):
    """ISSUE 2 Regr 5: Past session date attempting bypass is caught by live_data."""
    in_file = tmp_path / "bypass_attempt.json"
    vec = build_synthetic_feature_vector(
        session_date="2026-10-30",
        observation_time=datetime(2026, 10, 30, 8, 30, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 10, 30, 8, 32, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 10, 30, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    in_file.write_text(json.dumps(vec.to_dict()), encoding="utf-8")

    # Runner at 2026-11-02
    current_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture(
        session_date="2026-10-30",
        input_file_path=in_file,
        current_time=current_time,
    )
    assert res.status == CaptureStatus.MISSED_CUTOFF
    assert "Backdating is strictly prohibited" in res.reason


def test_regression_valid_current_session_prospective_input(tmp_path: Path):
    """ISSUE 2 Regr 6: Valid current-session prospective input file is accepted and recorded in temp ledger."""
    today_str = "2026-11-02"
    in_file = tmp_path / "valid_vector.json"
    vec = build_synthetic_feature_vector(
        session_date=today_str,
        observation_time=datetime(2026, 11, 2, 8, 30, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 32, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    in_file.write_text(json.dumps(vec.to_dict()), encoding="utf-8")

    current_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture(
        session_date=today_str,
        input_file_path=in_file,
        current_time=current_time,
    )
    assert res.status == CaptureStatus.SUCCESS
    assert res.feature_vector is not None

    # Validate and append to isolated temp ledger
    validator = SnapshotBInputValidator()
    report = validator.validate(res.feature_vector, current_time=current_time)
    assert report.is_eligible_for_inference is True

    temp_ledger = ShadowPredictionLedger(ledger_path=tmp_path / "temp_regr_ledger.jsonl")
    runner = ShadowInferenceRunner()
    pred = runner.predict(res.feature_vector, report, prev_record_hash=temp_ledger.get_tip_hash())
    status, rec = temp_ledger.append_prediction(pred)
    assert status == LedgerStatus.RECORDED
    assert len(temp_ledger.get_all_records()) == 1


def test_regression_duplicate_prospective_prediction(tmp_path: Path):
    """ISSUE 2 Regr 7: Duplicate prospective prediction returns DUPLICATE_IGNORED."""
    temp_ledger = ShadowPredictionLedger(ledger_path=tmp_path / "temp_dup_ledger.jsonl")
    runner = ShadowInferenceRunner()
    validator = SnapshotBInputValidator()

    today_str = "2026-11-02"
    current_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        session_date=today_str,
        observation_time=datetime(2026, 11, 2, 8, 30, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 32, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    report = validator.validate(vec, current_time=current_time)
    pred = runner.predict(vec, report, prev_record_hash=temp_ledger.get_tip_hash())

    status1, _ = temp_ledger.append_prediction(pred)
    assert status1 == LedgerStatus.RECORDED

    # Duplicate call
    status2, existing = temp_ledger.append_prediction(pred)
    assert status2 == LedgerStatus.DUPLICATE_IGNORED
    assert existing["prediction_id"] == pred.prediction_id
    assert len(temp_ledger.get_all_records()) == 1


def test_artifact_handoff_architecture_in_workflow():
    """ISSUE 1: Verify daily-operations uploads web/ artifact and deploy-pages deploys without checkout."""
    wf_path = PROJECT_ROOT / ".github" / "workflows" / "daily_shadow_ops.yml"
    content = wf_path.read_text(encoding="utf-8")

    # In daily-operations:
    assert "upload-pages-artifact" in content
    # In deploy-pages:
    assert "deploy-pages:" in content
    assert "needs: daily-operations" in content
    assert "deploy-pages@" in content
    # deploy-pages does NOT do a git checkout:
    deploy_pages_section = content.split("deploy-pages:")[1]
    assert "actions/checkout" not in deploy_pages_section


def test_health_check_and_dry_run_never_modify_production_ledgers():
    """ISSUE 5: Verify health_check and dry_run never touch the production ledgers."""
    real_pred_ledger = ShadowPredictionLedger()
    real_out_reconciler = ShadowOutcomeReconciler(prediction_ledger=real_pred_ledger)

    # Initial state must be 0
    assert len(real_pred_ledger.get_all_records()) == 0
    assert len(real_out_reconciler.get_all_outcomes()) == 0

    from scripts.run_daily_ops import run_dry_run, run_health_check
    hc_ret = run_health_check()
    assert hc_ret == 0

    dr_ret = run_dry_run()
    assert dr_ret == 0

    # Production ledgers must STILL be at exactly zero
    assert len(real_pred_ledger.get_all_records()) == 0
    assert len(real_out_reconciler.get_all_outcomes()) == 0
    assert real_pred_ledger.get_tip_hash() == "0" * 64


# ---------------------------------------------------------------------------
# 14 Timing Boundary Conditions (Issue 5 Regression Test Suite)
# ---------------------------------------------------------------------------

def test_timing_boundary_condition_1_eval_at_0835_rejected():
    """1. Evaluation at 08:35 IST -> rejected (EVALUATION_AFTER_CUTOFF / PREMATURE_EVALUATION)."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 35, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "EVALUATION_AFTER_CUTOFF" in rep.failed_checks

    res = attempt_live_feature_capture("2026-11-02", current_time=eval_time)
    assert res.status == CaptureStatus.PREMATURE_EVALUATION


def test_timing_boundary_condition_2_eval_at_084959_rejected():
    """2. Evaluation at 08:49:59 IST -> rejected (EVALUATION_AFTER_CUTOFF / PREMATURE_EVALUATION)."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 49, 59, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "EVALUATION_AFTER_CUTOFF" in rep.failed_checks

    res = attempt_live_feature_capture("2026-11-02", current_time=eval_time)
    assert res.status == CaptureStatus.PREMATURE_EVALUATION


def test_timing_boundary_condition_3_eval_at_085000_accepted():
    """3. Evaluation at 08:50:00 IST -> accepted."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is True
    assert "EVALUATION_AFTER_CUTOFF" in rep.passed_checks


def test_timing_boundary_condition_4_eval_at_085001_accepted():
    """4. Evaluation at 08:50:01 IST -> accepted."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 50, 1, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is True
    assert "EVALUATION_AFTER_CUTOFF" in rep.passed_checks


def test_timing_boundary_condition_5_eval_at_091400_accepted():
    """5. Evaluation at 09:14:00 IST -> accepted."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 9, 14, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is True
    assert "PREMARKET_DEADLINE_ENFORCEMENT" in rep.passed_checks


def test_timing_boundary_condition_6_eval_at_091500_rejected():
    """6. Evaluation at 09:15:00 IST -> rejected (PREMARKET_DEADLINE_ENFORCEMENT)."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 9, 15, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector("2026-11-02", provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE)
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "PREMARKET_DEADLINE_ENFORCEMENT" in rep.failed_checks


def test_timing_boundary_condition_7_correct_date_and_cutoff_accepted():
    """7. Evaluation with correct date and 08:50 cutoff -> accepted."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is True
    assert "CUTOFF_DATE_MISMATCH" in rep.passed_checks
    assert "CUTOFF_TIME_ENFORCEMENT" in rep.passed_checks


def test_timing_boundary_condition_8_previous_day_cutoff_rejected():
    """8. Previous-day cutoff date with today's session date -> rejected (CUTOFF_DATE_MISMATCH)."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=datetime(2026, 11, 1, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "CUTOFF_DATE_MISMATCH" in rep.failed_checks


def test_timing_boundary_condition_9_future_day_cutoff_rejected():
    """9. Future-day cutoff date with today's session date -> rejected (CUTOFF_DATE_MISMATCH)."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=datetime(2026, 11, 3, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "CUTOFF_DATE_MISMATCH" in rep.failed_checks


def test_timing_boundary_condition_10_observation_later_than_cutoff_rejected():
    """10. Observation timestamp later than cutoff -> rejected (OBSERVATION_TIME_VALIDITY)."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 51, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 51, 30, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "OBSERVATION_TIME_VALIDITY" in rep.failed_checks


def test_timing_boundary_condition_11_availability_later_than_cutoff_rejected():
    """11. Availability timestamp later than cutoff -> rejected (AVAILABILITY_PRIOR_TO_CUTOFF)."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 51, 0, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "AVAILABILITY_PRIOR_TO_CUTOFF" in rep.failed_checks


def test_timing_boundary_condition_12_availability_later_than_eval_rejected():
    """12. Availability timestamp later than evaluation time -> rejected (AVAILABILITY_PRIOR_TO_EVALUATION)."""
    validator = SnapshotBInputValidator()
    # Evaluated at 08:50:10, but availability claimed at 08:50:30 (even though <= 08:50 cutoff)
    eval_time = datetime(2026, 11, 2, 8, 50, 10, tzinfo=MARKET_TIMEZONE)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        observation_time=datetime(2026, 11, 2, 8, 45, 0, tzinfo=MARKET_TIMEZONE),
        availability_time=datetime(2026, 11, 2, 8, 50, 30, tzinfo=MARKET_TIMEZONE),
        cutoff_time=datetime(2026, 11, 2, 8, 50, 0, tzinfo=MARKET_TIMEZONE),
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "AVAILABILITY_PRIOR_TO_EVALUATION" in rep.failed_checks


def test_timing_boundary_condition_13_missing_timezone_rejected():
    """13. Missing timezone on any timestamp -> rejected (TIMEZONE_AWARENESS)."""
    validator = SnapshotBInputValidator()
    eval_time = datetime(2026, 11, 2, 8, 52, 0, tzinfo=MARKET_TIMEZONE)
    # Naive cutoff_time without tzinfo
    naive_cutoff = datetime(2026, 11, 2, 8, 50, 0)
    vec = build_synthetic_feature_vector(
        "2026-11-02",
        cutoff_time=naive_cutoff,
        provenance_type=ProvenanceType.PROSPECTIVE_LIVE_CAPTURE,
    )
    rep = validator.validate(vec, current_time=eval_time)
    assert rep.is_eligible_for_inference is False
    assert "TIMEZONE_AWARENESS" in rep.failed_checks


def test_timing_boundary_condition_14_delayed_execution_past_0915_missed_cutoff():
    """14. Delayed workflow execution past 09:15 IST -> MISSED_CUTOFF."""
    eval_time = datetime(2026, 11, 2, 9, 25, 0, tzinfo=MARKET_TIMEZONE)
    res = attempt_live_feature_capture("2026-11-02", current_time=eval_time)
    assert res.status == CaptureStatus.MISSED_CUTOFF
    assert "at or after 09:15:00 IST" in res.reason
