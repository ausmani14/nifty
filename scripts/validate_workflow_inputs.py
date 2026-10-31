#!/usr/bin/env python3
"""Strict input validation and scheduled operation classifier for GitHub Actions workflows.

Enforces zero-trust validation on all workflow triggers, rejecting shell metacharacters,
directory traversal, malformed dates, and unapproved operations.
Safely maps scheduled crons to operations without relying on runner wall-clock time.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys
from typing import Dict, Optional, Set, Tuple
from zoneinfo import ZoneInfo

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")

ALLOWED_OPERATIONS: Set[str] = {
    "snapshot_b",
    "reconcile_outcomes",
    "health_check",
    "dry_run",
}

SCHEDULE_CRON_MAP: Dict[str, str] = {
    "22 3 * * 1-5": "snapshot_b",
    "5 3 * * 1-5": "snapshot_b",  # backward compatibility alias
    "10 10 * * 1-5": "reconcile_outcomes",
}

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FORBIDDEN_SHELL_CHARS = re.compile(r"[;|<>&`$(){}\\*?\[\]!~]")


def validate_and_classify_inputs(
    event_name: str,
    schedule_cron: Optional[str] = None,
    input_operation: Optional[str] = None,
    input_session_date: Optional[str] = None,
    input_file: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> Tuple[str, str, str]:
    """Validate and classify workflow inputs.

    Returns:
        (operation, session_date_arg, input_file_arg)
    Raises:
        ValueError on any validation failure.
    """
    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent

    event_name = (event_name or "").strip()
    if not event_name:
        raise ValueError("Missing or empty EVENT_NAME.")

    # 1. Scheduled event handling
    if event_name == "schedule":
        cron_str = (schedule_cron or "").strip()
        if not cron_str:
            raise ValueError("Scheduled trigger missing SCHEDULE_CRON expression.")
        if cron_str not in SCHEDULE_CRON_MAP:
            raise ValueError(
                f"Unrecognized schedule cron expression: '{cron_str}'. "
                f"Supported: {list(SCHEDULE_CRON_MAP.keys())}"
            )
        operation = SCHEDULE_CRON_MAP[cron_str]
        # Scheduled workflows do not accept external date or file overrides
        return operation, "", ""

    # 2. Workflow dispatch event handling
    if event_name == "workflow_dispatch":
        op_str = (input_operation or "").strip()
        if not op_str:
            raise ValueError("Workflow dispatch missing INPUT_OPERATION.")
        if op_str not in ALLOWED_OPERATIONS:
            raise ValueError(
                f"Invalid operation '{op_str}'. Allowed: {sorted(ALLOWED_OPERATIONS)}"
            )

        # Validate session_date if provided
        date_arg = ""
        if input_session_date and ("\n" in input_session_date or "\r" in input_session_date):
            raise ValueError("Session date contains forbidden newline characters.")
        raw_date = (input_session_date or "").strip()
        if raw_date:
            if FORBIDDEN_SHELL_CHARS.search(raw_date):
                raise ValueError(f"Session date contains forbidden shell metacharacters: '{raw_date}'")
            if not DATE_REGEX.match(raw_date):
                raise ValueError(f"Session date must strictly follow YYYY-MM-DD format. Got: '{raw_date}'")
            try:
                datetime.strptime(raw_date, "%Y-%m-%d")
            except ValueError as e:
                raise ValueError(f"Invalid calendar date '{raw_date}': {e}") from e

            # Reject past/future dates for prospective snapshot_b operations
            if op_str == "snapshot_b":
                today_ist_str = datetime.now(timezone.utc).astimezone(MARKET_TIMEZONE).strftime("%Y-%m-%d")
                if raw_date < today_ist_str:
                    raise ValueError(f"Snapshot B rejects past session date '{raw_date}'. Backdating prospective predictions is strictly prohibited.")
                if raw_date > today_ist_str:
                    raise ValueError(f"Snapshot B rejects future session date '{raw_date}'. Prospective predictions cannot be generated in advance.")

            date_arg = raw_date

        # Validate input_file if provided
        file_arg = ""
        if input_file and ("\n" in input_file or "\r" in input_file):
            raise ValueError("Input file path contains forbidden newline characters.")
        raw_file = (input_file or "").strip()
        if raw_file:
            if FORBIDDEN_SHELL_CHARS.search(raw_file):
                raise ValueError(f"Input file path contains forbidden shell metacharacters: '{raw_file}'")
            
            p = Path(raw_file)
            if p.is_absolute() or raw_file.startswith("/") or raw_file.startswith("\\") or re.match(r"^[a-zA-Z]:", raw_file):
                raise ValueError(f"Absolute paths are forbidden: '{raw_file}'")
            if ".." in p.parts:
                raise ValueError(f"Directory traversal ('..') is strictly forbidden: '{raw_file}'")

            resolved = (repo_root / p).resolve()
            try:
                resolved.relative_to(repo_root.resolve())
            except ValueError:
                raise ValueError(f"Input file resolves outside repository root: '{raw_file}'")

            if not resolved.is_file():
                raise ValueError(f"Input file does not exist or is not a regular file: '{raw_file}'")

            file_arg = str(p).replace("\\", "/")

        return op_str, date_arg, file_arg

    raise ValueError(f"Unsupported workflow event name: '{event_name}'. Only 'schedule' and 'workflow_dispatch' are supported.")


def write_github_outputs(op: str, date_arg: str, file_arg: str) -> None:
    """Safely append validated single-line parameters to $GITHUB_OUTPUT."""
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return

    # Extra invariant guard: ensure values contain no newlines
    for k, v in [("OP", op), ("DATE_ARG", date_arg), ("FILE_ARG", file_arg)]:
        if "\n" in v or "\r" in v:
            raise ValueError(f"Refusing to write multiline value for GITHUB_OUTPUT key '{k}'.")

    with open(output_path, "a", encoding="utf-8") as f:
        f.write(f"OP={op}\n")
        f.write(f"DATE_ARG={date_arg}\n")
        f.write(f"FILE_ARG={file_arg}\n")


def main() -> int:
    event_name = os.getenv("EVENT_NAME", "")
    schedule_cron = os.getenv("SCHEDULE_CRON", "")
    input_operation = os.getenv("INPUT_OPERATION", "")
    input_session_date = os.getenv("INPUT_SESSION_DATE", "")
    input_file = os.getenv("INPUT_FILE", "")

    try:
        op, date_arg, file_arg = validate_and_classify_inputs(
            event_name=event_name,
            schedule_cron=schedule_cron,
            input_operation=input_operation,
            input_session_date=input_session_date,
            input_file=input_file,
        )
    except Exception as e:
        print(f"[FATAL SECURITY ERROR] Workflow input validation rejected: {e}", file=sys.stderr)
        return 1

    write_github_outputs(op, date_arg, file_arg)

    print("================================================================================")
    print("NIFTY AI — WORKFLOW INPUT VALIDATION PASSED")
    print("================================================================================")
    print(f"Event:             {event_name}")
    print(f"Target Operation:  {op}")
    print(f"Session Date:      {date_arg or '(default to current IST session)'}")
    print(f"Input File:        {file_arg or '(none, automated PIT live feed)'}")
    print("================================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
