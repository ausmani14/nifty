"""Command-line script to generate leakage-safe target datasets for NIFTY AI.

Generates regression and classification target datasets for Snapshot A and Snapshot B,
and exports configs/targets.yaml specification and metadata manifests.
"""

import argparse
from pathlib import Path
import sys

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.targets.pipeline import TARGETS_DIR, TargetPipeline
from nifty_ai.targets.registry import build_default_target_registry
from nifty_ai.targets.thresholds import (
    EmpiricalDistributionThreshold,
    FixedThreshold,
    ThresholdMethod,
    VolatilityScaledThreshold,
)

CONFIG_TARGETS_PATH = PROJECT_ROOT / "configs" / "targets.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate leakage-safe next-session targets for NIFTY 50."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv",
        help="Path to processed market data CSV file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=TARGETS_DIR,
        help="Directory to save generated target datasets.",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["volatility_scaled", "empirical_distribution", "fixed_baseline"],
        default="volatility_scaled",
        help="Threshold calculation methodology (default: volatility_scaled).",
    )
    parser.add_argument(
        "--percentile",
        type=float,
        default=25.0,
        help="Percentile for empirical_distribution method (default: 25.0).",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=20,
        help="Lookback window for threshold calculation (default: 20 for volatility_scaled).",
    )
    parser.add_argument(
        "--k",
        type=float,
        default=0.35,
        help="Multiplier k for volatility_scaled method (default: 0.35).",
    )
    parser.add_argument(
        "--fixed-value",
        type=float,
        default=0.005,
        help="Constant threshold for fixed_baseline method (default: 0.005).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.input.is_file():
        print(f"Error: Input file does not exist: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Instantiate threshold method
    threshold_method: ThresholdMethod
    if args.method == "empirical_distribution":
        threshold_method = EmpiricalDistributionThreshold(
            percentile=args.percentile,
            window=args.window,
        )
    elif args.method == "volatility_scaled":
        vol_win = args.window if args.window != 252 else 20
        threshold_method = VolatilityScaledThreshold(
            k=args.k,
            window=vol_win,
        )
    elif args.method == "fixed_baseline":
        threshold_method = FixedThreshold(value=args.fixed_value)
    else:
        raise ValueError(f"Unsupported method: {args.method}")

    print("=" * 80)
    print("NIFTY AI — TARGET GENERATION PIPELINE")
    print("=" * 80)
    print(f"Input Dataset:       {args.input}")
    print(f"Output Directory:    {args.output_dir}")
    print(f"Threshold Method:    {threshold_method.name}")
    print(f"Parameters:          {threshold_method.parameters}")
    print("Computing leakage-safe targets for Snapshot A and Snapshot B...\n")

    pipeline = TargetPipeline(threshold_method=threshold_method)
    snap_a_path, snap_b_path, metadata = pipeline.run(
        input_csv_path=args.input,
        output_dir=args.output_dir,
    )

    # Save targets.yaml specification
    registry = build_default_target_registry(
        method_name=threshold_method.name,
        parameters=threshold_method.parameters,
    )
    registry.save_yaml(CONFIG_TARGETS_PATH)

    print("=" * 80)
    print("TARGET GENERATION COMPLETE")
    print("=" * 80)
    print(f"Total Market Sessions:    {metadata['total_rows']}")
    print(f"Classified Rows:          {metadata['classified_rows']}")
    print(f"Warm-Up Rows Excluded:    {metadata['warmup_rows_excluded']}")
    print(f"Terminal Unlabeled Rows:  {metadata['terminal_unlabeled_rows']}")
    print("\nClass Distribution:")
    for cls_name, count in metadata["class_counts"].items():
        pct = metadata["class_distribution_pct"][cls_name]
        print(f"  {cls_name:<10}: {count:>5} ({pct:>5.2f}%)")
    print(f"  UP/DOWN Ratio: {metadata['up_down_ratio']}")

    print(f"\nSnapshot A File: {snap_a_path} (SHA-256: {metadata['snapshot_a_sha256'][:16]}...)")
    print(f"Snapshot B File: {snap_b_path} (SHA-256: {metadata['snapshot_b_sha256'][:16]}...)")
    print(f"Manifest File:   {args.output_dir / 'nifty50_targets.meta.json'}")
    print(f"Registry Config: {CONFIG_TARGETS_PATH}")


if __name__ == "__main__":
    main()
