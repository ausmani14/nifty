"""Standalone script to evaluate candidate SIDEWAYS threshold methodologies via multi-criteria diagnostics.

Evaluates Method A (volatility-scaled), Method B (empirical return distribution),
and Method C (fixed baseline) strictly on historical development data (<= 2021-12-31).

SIDEWAYS percentage is reported strictly as a post-hoc diagnostic, NOT an optimization target.

Outputs a comprehensive comparison table and saves a JSON report to data/targets/threshold_analysis.json.
"""

from datetime import date
from pathlib import Path
import sys

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.storage import load_processed_market_data
from nifty_ai.targets.analysis import ThresholdAnalyzer

DATA_PATH = PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv"
OUTPUT_JSON = PROJECT_ROOT / "data" / "targets" / "threshold_analysis.json"


def main() -> None:
    if not DATA_PATH.is_file():
        print(f"Error: Processed data file not found: {DATA_PATH}", file=sys.stderr)
        sys.exit(1)

    print("=" * 90)
    print("NIFTY AI — SIDEWAYS THRESHOLD MULTI-CRITERIA DIAGNOSTIC AUDIT")
    print("=" * 90)
    print(f"Dataset: {DATA_PATH.name}")
    print("Partition Boundary: Development <= 2021-12-31 | Holdout > 2021-12-31")
    print("Diagnostics evaluated strictly on development partition without target optimization...\n")

    records = load_processed_market_data(DATA_PATH)
    print(f"Total historical records: {len(records)} ({records[0].trading_date} to {records[-1].trading_date})")

    analyzer = ThresholdAnalyzer(development_end_date=date(2021, 12, 31))
    report = analyzer.run_full_comparison(records)

    print("\n" + "=" * 90)
    print("CANDIDATE THRESHOLD METHODOLOGIES (DEVELOPMENT PARTITION DIAGNOSTICS)")
    print("=" * 90)
    header = (
        f"{'#':<3} {'Method':<24} {'Parameters':<24} "
        f"{'MeanThresh':<12} {'StdThresh':<10} {'UP%':<6} {'Down%':<6} {'Side%*':<7} {'UP/DN'}"
    )
    print(header)
    print("-" * 96)

    for idx, ev in enumerate(report.evaluations, 1):
        params_str = str(ev.parameters)
        print(
            f"{idx:<3} {ev.method_name:<24} {params_str:<24} "
            f"{ev.threshold_mean * 100:>7.3f}%     "
            f"{ev.threshold_stdev * 100:>6.3f}%   "
            f"{ev.class_distribution['UP']:<6.1f} {ev.class_distribution['DOWN']:<6.1f} "
            f"{ev.sideways_pct:<7.1f} "
            f"{ev.up_down_ratio:<6.2f}"
        )
    print("(* Note: SIDEWAYS % is an observational post-hoc diagnostic, not an optimization target)")

    # Find the frozen Method A evaluation
    frozen_eval = next(
        (ev for ev in report.evaluations
         if ev.method_name == report.recommended_method and ev.parameters == report.recommended_parameters),
        report.evaluations[0]
    )

    print("\n" + "=" * 90)
    print(f"FROZEN V1 METHODOLOGY: {frozen_eval.method_name.upper()} {frozen_eval.parameters}")
    print("=" * 90)
    print(f"Economic & Statistical Justification:\n{report.recommendation_rationale}\n")

    print("Chronological Era Stability (Frozen Method A):")
    print(f"{'Era Name':<30} {'Range':<24} {'Total':<6} {'UP%':<6} {'Down%':<6} {'Side%':<7} {'UP/DN':<6} {'Thresh%'}")
    print("-" * 96)
    for p in frozen_eval.periods:
        date_range = f"{p.start_date[:4]} to {p.end_date[:4]}"
        print(
            f"{p.period_name:<30} {date_range:<24} {p.total_classified:<6} "
            f"{p.up_pct:<6.1f} {p.down_pct:<6.1f} {p.sideways_pct:<7.1f} "
            f"{p.up_down_ratio:<6.2f} {p.mean_threshold * 100:.3f}%"
        )

    if frozen_eval.volatility_regime:
        vr = frozen_eval.volatility_regime
        print("\nVolatility Regime Sensitivity (Frozen Method A):")
        print(f"Median Trailing 60d Volatility: {vr.median_volatility * 100:.2f}%")
        print(f"  Low Volatility Regime  (N={vr.low_vol_count}):  SIDEWAYS={vr.low_vol_sideways_pct:.1f}%, UP={vr.low_vol_up_pct:.1f}%, DOWN={vr.low_vol_down_pct:.1f}%")
        print(f"  High Volatility Regime (N={vr.high_vol_count}): SIDEWAYS={vr.high_vol_sideways_pct:.1f}%, UP={vr.high_vol_up_pct:.1f}%, DOWN={vr.high_vol_down_pct:.1f}%")
        print(f"  SIDEWAYS Spread (High Vol - Low Vol): {vr.sideways_pct_spread:+.1f}%")

    if report.holdout_validation:
        hv = report.holdout_validation
        print("\nOut-of-Sample Holdout Audit (>= 2022-01-01, Not Used for Parameter Selection):")
        print(f"  Holdout Window: {hv['period']} (N={hv['total_rows']})")
        print(f"  Distribution:   UP={hv['up_pct']}%, DOWN={hv['down_pct']}%, SIDEWAYS={hv['sideways_pct']}%")
        print(f"  UP/DOWN Ratio:  {hv['up_down_ratio']}")

    saved_path = report.save_json(OUTPUT_JSON)
    print(f"\nSaved detailed diagnostic analysis report to: {saved_path}")


if __name__ == "__main__":
    main()
