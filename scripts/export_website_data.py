#!/usr/bin/env python3
"""CLI utility to generate and export static website JSON files into website_data/."""

import argparse
from pathlib import Path
import sys

from nifty_ai.shadow.website_exporter import WebsiteDataExporter


def main() -> int:
    parser = argparse.ArgumentParser(description="NIFTY AI Website Data Exporter")
    parser.add_argument("--output-dir", type=str, default="website_data", help="Output directory path")
    parser.add_argument("--status", type=str, default="IMPLEMENTED — WAITING FOR LIVE INPUT", help="System state string")
    parser.add_argument("--error", type=str, default=None, help="Latest error or failure status message")
    args = parser.parse_args()

    exporter = WebsiteDataExporter(output_dir=Path(args.output_dir))
    paths = exporter.export_all(current_system_state=args.status, latest_error=args.error)

    print("================================================================================")
    print("NIFTY AI — WEBSITE DATA EXPORTER")
    print("================================================================================")
    for name, p in paths.items():
        print(f"Exported: {name:20s} -> {p}")
    print("Successfully exported all website data files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
