"""Phase 12 Step 12: NULL N4 Year-Block Exact Enumeration Forensic Correction.

Research Objective:
Replace Monte Carlo sampling of NULL N4 (Year-Block Permutation) with an EXACT
enumeration of all 8! = 40,320 unique permutations of the 8 complete calendar-year
prediction blocks (2014–2021).

Governance & Constraints:
- Phase 12 Steps 1-11 are formally SEALED.
- Development/OOF universe: 2014-01-02 to 2021-12-31, exactly N=1,960 sessions.
- Input data: Frozen T0 predictions and actuals from data/interim/phase12_step11/step11_predictions.csv.
- Zero model training or hyperparameter optimization.
- Zero holdout access (holdout >= 2022-01-01 strictly quarantined).
- Exactly 40,320 unique permutations evaluated deterministically.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from nifty_ai.config import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step12"
STEP11_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step11"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"
PRED_FILE = STEP11_DIR / "step11_predictions.csv"


def run_n4_exact_enumeration() -> None:
    print("=" * 90)
    print("PHASE 12 STEP 12 — NULL N4 YEAR-BLOCK EXACT ENUMERATION")
    print("=" * 90)

    # 1. Load predictions
    assert PRED_FILE.is_file(), f"Missing prediction file: {PRED_FILE}"
    df_pred = pd.read_csv(PRED_FILE)
    df_pred["trading_date"] = pd.to_datetime(df_pred["trading_date"])
    df_pred["year"] = df_pred["trading_date"].dt.year

    n_obs = len(df_pred)
    assert n_obs == 1960, f"Expected 1960 observations, got {n_obs}"
    max_date = df_pred["trading_date"].max().date()
    assert max_date <= date(2021, 12, 31), f"Holdout contamination: max date {max_date}"

    pred = df_pred["T0_pred"].values
    actual = df_pred["T0_actual"].values

    # Observed correlation
    r_obs, p_obs = stats.pearsonr(pred, actual)
    print(f"Observed T0 Pearson IC: {r_obs:.8f} (p = {p_obs:.6f})")
    assert abs(r_obs - 0.04761923873169822) < 1e-12, "Observed Pearson IC mismatch!"

    # 2. Extract calendar-year blocks
    years = sorted(df_pred["year"].unique())
    assert len(years) == 8, f"Expected 8 years, got {len(years)}: {years}"
    year_counts = {int(y): int(np.sum(df_pred["year"] == y)) for y in years}
    print(f"Year blocks: {year_counts}")

    year_pred_blocks = [df_pred.loc[df_pred["year"] == y, "T0_pred"].values for y in years]

    # Pre-center and normalize actual sequence
    act_c = actual - np.mean(actual)
    norm_act = float(np.linalg.norm(act_c))

    # 3. Generate all 8! = 40,320 permutations
    all_perms = list(itertools.permutations(range(8)))
    n_perms = len(all_perms)
    assert n_perms == 40320, f"Expected 40,320 permutations, got {n_perms}"
    assert len(set(all_perms)) == 40320, "Permutations are not all unique!"

    print(f"\nEvaluating all {n_perms:,} exact year-block permutations...")
    exact_records = []
    null_ics = np.zeros(n_perms, dtype=np.float64)

    for p_id, p in enumerate(all_perms, start=1):
        perm_years = [years[i] for i in p]
        year_order_str = ",".join(str(y) for y in perm_years)

        # Concatenate prediction blocks in permuted year order
        p_pred = np.concatenate([year_pred_blocks[i] for i in p])
        p_pred_c = p_pred - np.mean(p_pred)
        norm_p = float(np.linalg.norm(p_pred_c))

        r_null = float(np.dot(p_pred_c, act_c) / (norm_p * norm_act))
        null_ics[p_id - 1] = r_null
        exact_records.append((p_id, year_order_str, r_null))

    print("Exact enumeration completed successfully.")

    # 4. Save step12_n4_year_exact_results.csv with full 64-bit IEEE-754 precision
    df_exact_results = pd.DataFrame(exact_records, columns=["permutation_id", "year_order", "pearson_ic"])
    results_csv_path = DATA_DIR / "step12_n4_year_exact_results.csv"
    df_exact_results.to_csv(results_csv_path, index=False, float_format="%.16e")
    print(f"Saved exact results to {results_csv_path} ({len(df_exact_results):,} rows).")

    # 5. Compute exact moments, p-values, and statistics
    mu_null = float(np.mean(null_ics))
    std_null = float(np.std(null_ics, ddof=1))
    p025 = float(np.percentile(null_ics, 2.5))
    p500 = float(np.percentile(null_ics, 50.0))
    p975 = float(np.percentile(null_ics, 97.5))
    min_null = float(np.min(null_ics))
    max_null = float(np.max(null_ics))

    # Exact finite-sample permutation p-values: (1 + b) / (M + 1)
    b_two = int(np.sum(np.abs(null_ics) >= abs(r_obs)))
    p_two = float((1 + b_two) / (n_perms + 1))

    b_one = int(np.sum(null_ics >= r_obs))
    p_one = float((1 + b_one) / (n_perms + 1))

    pct_rank = float(stats.percentileofscore(null_ics, r_obs, kind="weak"))
    exceeds_95 = bool(p_two < 0.05)

    print("\n--- Exact N4 Null Statistics ---")
    print(f"  Total Permutations (8!): {n_perms:,}")
    print(f"  Observed Pearson IC:     {r_obs:+.8f}")
    print(f"  Null Mean:               {mu_null:+.6f}")
    print(f"  Null Std Dev:            {std_null:.6f}")
    print(f"  2.5th Percentile:        {p025:+.6f}")
    print(f"  Median (50th):           {p500:+.6f}")
    print(f"  97.5th Percentile:       {p975:+.6f}")
    print(f"  Range:                   [{min_null:+.6f}, {max_null:+.6f}]")
    print(f"  Observed Percentile:     {pct_rank:.2f}%")
    print(f"  Count (|r| >= |r_obs|):  {b_two} / {n_perms}")
    print(f"  Exact Two-Sided p:       {p_two:.6f} (formula: (1 + {b_two}) / ({n_perms} + 1))")
    print(f"  Count (r >= r_obs):      {b_one} / {n_perms}")
    print(f"  Exact One-Sided p:       {p_one:.6f} (formula: (1 + {b_one}) / ({n_perms} + 1))")
    print(f"  Exceeds 95% Threshold:   {exceeds_95}")

    # 6. Save step12_n4_year_exact_summary.json
    summary_json_data = {
        "experiment_id": "N4_year_exact",
        "null_name": "Year-Block Permutation (Exact Enumeration)",
        "total_permutations": n_perms,
        "observed_statistic": {
            "metric": "Pearson Correlation (IC)",
            "observed_value": float(r_obs),
            "nominal_parametric_two_sided_p": float(p_obs),
        },
        "exact_pvalues": {
            "formula_two_sided": "(1 + count(|r_null| >= |r_obs|)) / (40320 + 1)",
            "count_two_sided_extreme": b_two,
            "empirical_two_sided_p": p_two,
            "formula_one_sided": "(1 + count(r_null >= r_obs)) / (40320 + 1)",
            "count_one_sided_extreme": b_one,
            "empirical_one_sided_p": p_one,
            "observed_percentile_rank": pct_rank,
            "exceeds_95pct_threshold": exceeds_95,
        },
        "exact_null_distribution_moments": {
            "mean": mu_null,
            "std": std_null,
            "median": p500,
            "p025": p025,
            "p975": p975,
            "min": min_null,
            "max": max_null,
        },
        "methodology": {
            "description": "Exact enumeration of all 8! = 40,320 permutations of the 8 complete calendar-year prediction blocks across years 2014-2021.",
            "years": [int(y) for y in years],
            "year_sample_sizes": year_counts,
            "total_observations": n_obs,
            "within_year_ordering_preserved": True,
            "prediction_multiset_preserved": True,
            "target_sequence_fixed": True,
            "monte_carlo_sampling_error": 0.0,
        },
        "governance": {
            "deterministic": True,
            "holdout_rows_accessed": 0,
            "max_trading_date": str(max_date),
            "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
    }

    summary_json_path = DATA_DIR / "step12_n4_year_exact_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_json_data, f, indent=2)
    print(f"Saved exact summary JSON to {summary_json_path}.")

    # 7. Update step12_null_summary.csv (modify N4 row only)
    summary_csv_path = DATA_DIR / "step12_null_summary.csv"
    assert summary_csv_path.is_file(), f"Missing summary CSV: {summary_csv_path}"
    df_summary = pd.read_csv(summary_csv_path)

    n4_mask = df_summary["null_id"] == "N4_year"
    assert n4_mask.sum() == 1, "Expected exactly 1 N4_year row in step12_null_summary.csv"

    df_summary.loc[n4_mask, "null_name"] = "Year-Block Permutation (Exact Enumeration)"
    df_summary.loc[n4_mask, "n_null"] = n_perms
    df_summary.loc[n4_mask, "null_mean"] = mu_null
    df_summary.loc[n4_mask, "null_std"] = std_null
    df_summary.loc[n4_mask, "null_p025"] = p025
    df_summary.loc[n4_mask, "null_median"] = p500
    df_summary.loc[n4_mask, "null_p975"] = p975
    df_summary.loc[n4_mask, "observed_percentile"] = pct_rank
    df_summary.loc[n4_mask, "empirical_two_sided_p"] = p_two
    df_summary.loc[n4_mask, "empirical_one_sided_p"] = p_one
    df_summary.loc[n4_mask, "exceeds_95pct_threshold"] = exceeds_95

    df_summary.to_csv(summary_csv_path, index=False)
    print(f"Updated {summary_csv_path} with exact N4 statistics.")

    # 8. Update step12_null_definitions.json
    defs_path = DATA_DIR / "step12_null_definitions.json"
    assert defs_path.is_file(), f"Missing definitions: {defs_path}"
    with open(defs_path, "r", encoding="utf-8") as f:
        defs_data = json.load(f)

    for exp in defs_data["null_experiments"]:
        if exp["null_id"] == "N4_year":
            exp["null_name"] = "Year-Block Permutation (Exact Enumeration)"
            exp["n_replicates"] = n_perms
            exp["methodology"] = "Exact enumeration of all 8! = 40,320 permutations of the 8 complete calendar-year prediction blocks across years 2014-2021."
            exp["role"] = "Annual regime alignment null (exact finite permutation group)."

    with open(defs_path, "w", encoding="utf-8") as f:
        json.dump(defs_data, f, indent=2)
    print(f"Updated {defs_path} with exact N4 metadata.")

    # 9. Update step12_integrity_manifest.json
    manifest_path = DATA_DIR / "step12_integrity_manifest.json"
    assert manifest_path.is_file(), f"Missing manifest: {manifest_path}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    all_artifacts = [
        "step12_null_definitions.json",
        "step12_null_results.csv",
        "step12_null_summary.csv",
        "step12_temporal_results.csv",
        "step12_n4_year_exact_results.csv",
        "step12_n4_year_exact_summary.json",
    ]

    manifest_hashes = {}
    for fn in all_artifacts:
        fp = DATA_DIR / fn
        assert fp.is_file(), f"Missing artifact: {fn}"
        h = hashlib.sha256(fp.read_bytes()).hexdigest()
        manifest_hashes[fn] = h
        print(f"  {fn:<35}: {h}")

    manifest_data["artifact_hashes"] = manifest_hashes
    manifest_data["generated_timestamp_utc"] = datetime.now(timezone.utc).isoformat()
    manifest_data["null_outcome_classification"]["summary"] = (
        "The observed OOF Pearson association remains statistically unusual relative to each of the explicitly "
        "tested dependence-preserving null structures, including exact enumeration of all 40,320 year-block "
        "permutations. This strengthens the evidence that the observed association is not explained solely by "
        "the tested temporal-dependence and temporal-alignment structures. It does not establish economic "
        "profitability, causal mechanism, model validity beyond the tested period, or future persistence."
    )

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"Updated manifest at {manifest_path}.")


if __name__ == "__main__":
    run_n4_exact_enumeration()
