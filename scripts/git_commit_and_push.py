#!/usr/bin/env python3
"""Safe, audited Git commit and push script for GitHub Actions shadow operations.

Strictly stages only authorized ledger and website data artifacts, checks branch targets,
detects rebase conflicts without corrupting history, and enforces bounded push retries
with explicit non-zero failure handling.
"""

from pathlib import Path
import subprocess
import sys
import time
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent

AUTHORIZED_STAGE_PATHS: List[str] = [
    "data/interim/phase14_shadow/shadow_predictions_ledger.jsonl",
    "data/interim/phase14_shadow/shadow_outcomes_ledger.jsonl",
    "website_data",
    "web/data",
    "index.html",
]


def run_git(args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Execute a git command within the repository root."""
    cmd = ["git"] + args
    res = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if check and res.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(cmd)}\nSTDERR: {res.stderr}\nSTDOUT: {res.stdout}")
    return res


def perform_safe_commit_and_push(max_retries: int = 3, retry_delay_seconds: float = 5.0) -> int:
    """Stage authorized files, commit, rebase onto origin/master, and push."""
    print("================================================================================")
    print("NIFTY AI — SAFE GIT COMMIT & PUSH WORKFLOW")
    print("================================================================================")

    # 1. Verify checked-out branch is 'master'
    branch_res = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    current_branch = branch_res.stdout.strip()
    if current_branch != "master":
        print(f"[FATAL ERROR] Unexpected branch '{current_branch}'. Must be 'master'.", file=sys.stderr)
        return 1

    # 2. Stage authorized files
    print("Staging authorized files:")
    for path in AUTHORIZED_STAGE_PATHS:
        full_path = PROJECT_ROOT / path
        if full_path.exists():
            print(f"  + git add {path}")
            stage_res = run_git(["add", path], check=False)
            if stage_res.returncode != 0:
                print(f"[FATAL ERROR] Failed to stage '{path}': {stage_res.stderr}", file=sys.stderr)
                return 1
        else:
            print(f"  - (Path not present, skipping: {path})")

    # 3. Check if anything is staged
    staged_diff = run_git(["diff", "--staged", "--quiet"], check=False)
    if staged_diff.returncode == 0:
        print("[INFO] No ledger or website data changes to commit. Working tree is clean.")
        return 0

    # 4. Commit changes
    commit_msg = "Auto: Update shadow ledgers and website data [skip ci]"
    print(f"Committing changes: '{commit_msg}'")
    commit_res = run_git(["commit", "-m", commit_msg], check=False)
    if commit_res.returncode != 0:
        print(f"[FATAL ERROR] Git commit failed: {commit_res.stderr}", file=sys.stderr)
        return 1

    # 5. Bounded fetch, rebase, and push retry loop
    pushed = False
    for attempt in range(1, max_retries + 1):
        print(f"Push attempt {attempt} of {max_retries}...")

        # Fetch latest origin/master
        fetch_res = run_git(["fetch", "origin", "master"], check=False)
        if fetch_res.returncode != 0:
            print(f"[WARNING] git fetch failed: {fetch_res.stderr.strip()}", file=sys.stderr)

        # Rebase against origin/master
        rebase_res = run_git(["rebase", "origin/master"], check=False)
        if rebase_res.returncode != 0:
            print("[FATAL ERROR] Rebase conflict detected against origin/master! Aborting rebase.", file=sys.stderr)
            run_git(["rebase", "--abort"], check=False)
            return 1

        # Push to origin master
        push_res = run_git(["push", "origin", "master"], check=False)
        if push_res.returncode == 0:
            print("Successfully pushed updates to origin/master.")
            pushed = True
            break
        else:
            print(f"[WARNING] Push attempt {attempt} failed: {push_res.stderr.strip()}", file=sys.stderr)
            if attempt < max_retries:
                time.sleep(retry_delay_seconds)

    if not pushed:
        print("[FATAL ERROR] All push attempts to origin/master failed.", file=sys.stderr)
        return 1

    print("================================================================================")
    print("Safe git commit and push completed successfully.")
    print("================================================================================")
    return 0


def main() -> int:
    try:
        return perform_safe_commit_and_push()
    except Exception as e:
        print(f"[FATAL EXCEPTION] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
