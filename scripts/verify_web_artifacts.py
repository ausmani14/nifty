#!/usr/bin/env python3
"""Pre-deployment verification tool for GitHub Pages static website artifacts.

Ensures that the web directory contains index.html, style.css, app.js, and
all six required prospective JSON data contracts before any deployment occurs.
Fails closed if any artifact is missing or invalid JSON.
"""

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"
WEB_DATA_DIR = WEB_DIR / "data"

REQUIRED_FILES = [
    WEB_DIR / "index.html",
    WEB_DIR / "style.css",
    WEB_DIR / "app.js",
]

REQUIRED_JSON_CONTRACTS = [
    "latest_prediction.json",
    "system_status.json",
    "model_info.json",
    "prediction_history.json",
    "outcome_history.json",
    "performance_summary.json",
]


def verify_web_artifacts(web_dir: Path = WEB_DIR) -> bool:
    """Verify that all static files and JSON contracts exist and are valid."""
    data_dir = web_dir / "data"
    errors = []

    # 1. Verify core static web files
    for p in [web_dir / "index.html", web_dir / "style.css", web_dir / "app.js"]:
        if not p.is_file():
            errors.append(f"Missing core web file: {p.name}")
        elif p.stat().st_size == 0:
            errors.append(f"Core web file is empty: {p.name}")

    # 2. Verify JSON contracts
    if not data_dir.is_dir():
        errors.append(f"Web data directory does not exist: {data_dir}")
    else:
        for contract_name in REQUIRED_JSON_CONTRACTS:
            contract_path = data_dir / contract_name
            if not contract_path.is_file():
                errors.append(f"Missing JSON contract: {contract_name}")
                continue

            if contract_path.stat().st_size == 0:
                errors.append(f"JSON contract is empty (0 bytes): {contract_name}")
                continue

            try:
                with open(contract_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    errors.append(f"Contract '{contract_name}' root element must be a JSON object.")
            except Exception as e:
                errors.append(f"Failed to parse JSON contract '{contract_name}': {e}")

    if errors:
        print("================================================================================", file=sys.stderr)
        print("WEB ARTIFACT VERIFICATION FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  [X] {err}", file=sys.stderr)
        print("================================================================================", file=sys.stderr)
        return False

    print("================================================================================")
    print("NIFTY AI — WEB ARTIFACT VERIFICATION PASSED")
    print(f"Verified web root:       {web_dir}")
    print(f"Core files checked:      index.html, style.css, app.js")
    print(f"JSON contracts checked:  {len(REQUIRED_JSON_CONTRACTS)} contracts in web/data/")
    print("All artifacts present and verified.")
    print("================================================================================")
    return True


def main() -> int:
    return 0 if verify_web_artifacts() else 1


if __name__ == "__main__":
    sys.exit(main())
