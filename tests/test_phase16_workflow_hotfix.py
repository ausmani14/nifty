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
    ProvenanceType,
)
from nifty_ai.shadow.input_capture import build_synthetic_feature_vector
from nifty_ai.shadow.input_validator import (
    SNAPSHOT_B_CUTOFF_TIME,
    SnapshotBInputValidator,
)
from nifty_ai.shadow.live_data import (
    CaptureStatus,
    attempt_live_feature_capture,
)
from nifty_ai.shadow.model_protection import assert_frozen_model_intact
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
    """Verify attempt_live_feature_capture returns MISSED_CUTOFF after 08:50 IST for today."""
    session_date = "2026-11-02"  # Monday
    # Simulate time at 09:05:00 IST (after 08:50 cutoff)
    simulated_late_time = datetime(2026, 11, 2, 9, 5, 0, tzinfo=MARKET_TIMEZONE)

    res = attempt_live_feature_capture(
        session_date=session_date,
        current_time=simulated_late_time,
    )
    assert res.status == CaptureStatus.MISSED_CUTOFF
    assert "after 08:50:00 IST cutoff" in res.reason


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
