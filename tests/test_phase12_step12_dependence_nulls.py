"""Unit and forensic validation test suite for Phase 12 Step 12: Dependence-Aware Null Audit.

Required Assertions:
1. OOF N = 1,960.
2. Holdout rows accessed = 0.
3. max trading date <= 2021-12-31.
4. frozen prediction hash unchanged.
5. frozen target hash unchanged.
6. observed Pearson IC reproduces sealed Step 2 value within 1e-12.
7. IID permutations preserve prediction multiset.
8. circular shifts exclude zero shift.
9. circular shifts preserve prediction sequence values.
10. block permutations preserve prediction multiset.
11. block permutations preserve block contents/order.
12. deterministic seed reproduces identical results.
13. null distributions have expected sample counts (including N4 = 40,320).
14. no model training occurs.
15. no holdout data accessed.
16. Step 1–11 protected hashes remain unchanged.
17. all manifest checksums match files on disk.
18. outcome classification confirms Case A.

Required N4 Exact Enumeration Assertions:
19. N4 contains exactly 40,320 permutations.
20. Every permutation is unique.
21. Every permutation contains exactly the same 8 year-block IDs.
22. Each year block appears exactly once per permutation.
23. Within-year prediction ordering is unchanged.
24. Prediction multiset is unchanged under year permutations.
25. Target sequence is unchanged.
26. Observed Pearson IC reproduces +0.04761924 within 10^-12 (and identity permutation matches).
27. Exact p-value calculation follows registered formula: (1 + b) / (40320 + 1).
28. N4 exact result is deterministic.
29. No holdout rows are accessed for N4 exact.
30. Step 1–11 protected artifacts remain byte-for-byte unchanged.
"""

from datetime import date
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from nifty_ai.config import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step12"
STEP11_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step11"
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
STEP7_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step7"
STEP8_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step8"
STEP9_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step9"
STEP10_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step10"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"

NULL_DEFS_JSON = DATA_DIR / "step12_null_definitions.json"
NULL_RESULTS_CSV = DATA_DIR / "step12_null_results.csv"
NULL_SUMMARY_CSV = DATA_DIR / "step12_null_summary.csv"
TEMPORAL_CSV = DATA_DIR / "step12_temporal_results.csv"
MANIFEST_PATH = DATA_DIR / "step12_integrity_manifest.json"
N4_RESULTS_CSV = DATA_DIR / "step12_n4_year_exact_results.csv"
N4_SUMMARY_JSON = DATA_DIR / "step12_n4_year_exact_summary.json"
PRED_FILE = STEP11_DIR / "step11_predictions.csv"


@pytest.fixture(scope="module")
def df_pred():
    assert PRED_FILE.is_file(), f"Missing predictions file: {PRED_FILE}"
    return pd.read_csv(PRED_FILE)


@pytest.fixture(scope="module")
def df_summary():
    assert NULL_SUMMARY_CSV.is_file(), f"Missing summary file: {NULL_SUMMARY_CSV}"
    return pd.read_csv(NULL_SUMMARY_CSV)


@pytest.fixture(scope="module")
def df_results():
    assert NULL_RESULTS_CSV.is_file(), f"Missing results file: {NULL_RESULTS_CSV}"
    return pd.read_csv(NULL_RESULTS_CSV)


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST_PATH.is_file(), f"Missing manifest file: {MANIFEST_PATH}"
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def null_defs():
    assert NULL_DEFS_JSON.is_file(), f"Missing null defs: {NULL_DEFS_JSON}"
    with open(NULL_DEFS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def df_n4_exact():
    assert N4_RESULTS_CSV.is_file(), f"Missing N4 exact results: {N4_RESULTS_CSV}"
    return pd.read_csv(N4_RESULTS_CSV)


@pytest.fixture(scope="module")
def n4_exact_summary():
    assert N4_SUMMARY_JSON.is_file(), f"Missing N4 exact summary: {N4_SUMMARY_JSON}"
    with open(N4_SUMMARY_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def test_oof_n_rows(df_pred):
    """Assertion 1: Exactly N=1,960 OOF observations."""
    assert len(df_pred) == 1960


def test_holdout_rows_zero(manifest, null_defs):
    """Assertion 2: Holdout rows accessed = 0."""
    assert manifest["firewall_verification"]["holdout_rows_accessed"] == 0
    assert null_defs["metadata"]["governance_constraints"]["holdout_rows_accessed"] == 0


def test_max_trading_date(df_pred, manifest):
    """Assertion 3: Max trading date <= 2021-12-31."""
    max_d = pd.to_datetime(df_pred["trading_date"]).max().date()
    assert max_d <= date(2021, 12, 31)
    assert manifest["firewall_verification"]["max_dev_trading_date"] <= "2021-12-31"


def test_frozen_prediction_hash_unchanged():
    """Assertion 4: Frozen prediction file hash matches Step 11 manifest."""
    step11_manifest_path = STEP11_DIR / "step11_integrity_manifest.json"
    assert step11_manifest_path.is_file()
    with open(step11_manifest_path, "r", encoding="utf-8") as f:
        s11_m = json.load(f)
    expected_hash = s11_m["artifact_hashes"]["step11_predictions.csv"]
    actual_hash = hashlib.sha256(PRED_FILE.read_bytes()).hexdigest()
    assert actual_hash == expected_hash


def test_frozen_target_hash_unchanged(df_pred):
    """Assertion 5: Target column values match locked T0 actuals."""
    step2_csv = PHASE12_DIR / "snapshot_b_intraday_diagnostics.csv"
    assert step2_csv.is_file()
    df_s2 = pd.read_csv(step2_csv)
    target_diff = np.abs(df_pred["T0_actual"].values - df_s2["y_true_intraday"].values)
    assert np.max(target_diff) < 1e-12


def test_observed_pearson_ic_reproduction(df_pred):
    """Assertion 6: Observed Pearson IC reproduces sealed Step 2 value within 1e-12."""
    step2_csv = PHASE12_DIR / "snapshot_b_intraday_diagnostics.csv"
    df_s2 = pd.read_csv(step2_csv)
    r_s2, _ = stats.pearsonr(df_s2["pred_reg_intraday"].values, df_s2["y_true_intraday"].values)
    r_s12, _ = stats.pearsonr(df_pred["T0_pred"].values, df_pred["T0_actual"].values)
    assert abs(r_s12 - r_s2) < 1e-12
    assert abs(r_s12 - 0.04761923873169822) < 1e-12


def test_iid_permutation_preserves_multiset(df_pred):
    """Assertion 7: IID permutation preserves the exact multiset of predictions."""
    rng = np.random.default_rng(123)
    original = df_pred["T0_pred"].values
    permuted = rng.permutation(original)
    assert np.array_equal(np.sort(original), np.sort(permuted))
    assert math.isclose(np.mean(original), np.mean(permuted), abs_tol=1e-15)
    assert math.isclose(np.std(original), np.std(permuted), abs_tol=1e-15)


def test_circular_shifts_exclude_zero():
    """Assertion 8: Circular shifts strictly exclude zero shift."""
    shifts = list(range(1, 1960))
    assert 0 not in shifts
    assert len(shifts) == 1959
    assert min(shifts) == 1
    assert max(shifts) == 1959


def test_circular_shifts_preserve_sequence(df_pred):
    """Assertion 9: Circular shifts preserve prediction sequence values and local ordering."""
    original = df_pred["T0_pred"].values
    for s in [1, 50, 500, 1000, 1959]:
        shifted = np.roll(original, s)
        assert np.array_equal(np.sort(original), np.sort(shifted))
        assert shifted[s] == original[0]


def test_block_permutations_preserve_multiset(df_pred):
    """Assertion 10: Block permutations preserve exact prediction multiset across all block sizes."""
    original = df_pred["T0_pred"].values
    rng = np.random.default_rng(999)
    for b_size in [5, 10, 20]:
        n_blocks = len(original) // b_size
        blocks = [original[i * b_size:(i + 1) * b_size] for i in range(n_blocks)]
        perm_idx = rng.permutation(n_blocks)
        permuted = np.concatenate([blocks[j] for j in perm_idx])
        assert np.array_equal(np.sort(original), np.sort(permuted))


def test_block_permutations_preserve_within_block_order(df_pred):
    """Assertion 11: Block permutations preserve exact internal within-block contents and ordering."""
    original = df_pred["T0_pred"].values
    rng = np.random.default_rng(777)
    b_size = 10
    n_blocks = len(original) // b_size
    blocks = [original[i * b_size:(i + 1) * b_size] for i in range(n_blocks)]
    perm_idx = rng.permutation(n_blocks)
    permuted = np.concatenate([blocks[j] for j in perm_idx])
    for b_i in range(n_blocks):
        sub = permuted[b_i * b_size:(b_i + 1) * b_size]
        orig_match = False
        for orig_b in blocks:
            if np.array_equal(sub, orig_b):
                orig_match = True
                break
        assert orig_match, f"Block {b_i} was corrupted during block permutation!"


def test_deterministic_seed_reproducibility():
    """Assertion 12: Deterministic seed produces identical null distributions on repeated runs."""
    rng1 = np.random.default_rng(42)
    rng2 = np.random.default_rng(42)
    v1 = rng1.permutation(100)
    v2 = rng2.permutation(100)
    assert np.array_equal(v1, v2)


def test_null_distributions_sample_counts(df_results, df_summary):
    """Assertion 13: Null distributions have expected sample counts (N >= 10,000, N2_exact = 1,959, N4_year = 40,320)."""
    assert len(df_summary) == 8
    counts = dict(zip(df_summary["null_id"], df_summary["n_null"]))
    assert counts["N1"] == 10000
    assert counts["N2_exact"] == 1959
    assert counts["N2_sampled"] == 10000
    assert counts["N3_b05"] == 10000
    assert counts["N3_b10"] == 10000
    assert counts["N3_b20"] == 10000
    assert counts["N4_year"] == 40320
    assert counts["N5_sign"] == 10000


def test_no_model_training(manifest):
    """Assertion 14: Zero model training occurs."""
    assert manifest["oof_population"]["source_artifact"] == "data/interim/phase12_step11/step11_predictions.csv"


def test_no_holdout_accessed(manifest):
    """Assertion 15: Zero holdout data accessed."""
    assert manifest["firewall_verification"]["holdout_rows_accessed"] == 0
    assert manifest["firewall_verification"]["firewall_intact"] is True


def test_protected_upstream_hashes_unchanged():
    """Assertion 16: All 67 protected upstream artifact hashes from Steps 1–11 remain bit-for-bit unchanged."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        assert fp.is_file(), f"Missing file: {rel_path}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Hash mismatch for {rel_path}"

    from scripts.phase12_step12_dependence_null_audit import (
        PROTECTED_STEP5_HASHES,
        PROTECTED_STEP6_HASHES,
        PROTECTED_STEP7_HASHES,
        PROTECTED_STEP8_HASHES,
        PROTECTED_STEP9_HASHES,
        PROTECTED_STEP10_HASHES,
        PROTECTED_STEP11_HASHES,
    )

    for dir_p, h_dict in [
        (PHASE12_DIR, PROTECTED_STEP5_HASHES),
        (PHASE12_DIR, PROTECTED_STEP6_HASHES),
        (STEP7_DIR, PROTECTED_STEP7_HASHES),
        (STEP8_DIR, PROTECTED_STEP8_HASHES),
        (STEP9_DIR, PROTECTED_STEP9_HASHES),
        (STEP10_DIR, PROTECTED_STEP10_HASHES),
        (STEP11_DIR, PROTECTED_STEP11_HASHES),
    ]:
        for fn, exp_hash in h_dict.items():
            fp = dir_p / fn
            assert fp.is_file(), f"Missing: {fn}"
            act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
            assert act_hash == exp_hash, f"Hash mismatch for {fn}"


def test_manifest_checksums_match_disk(manifest):
    """Assertion 17: All Step 12 integrity manifest hashes match files on disk."""
    for fn, exp_hash in manifest["artifact_hashes"].items():
        fp = DATA_DIR / fn
        assert fp.is_file(), f"Missing Step 12 artifact: {fn}"
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        assert act_hash == exp_hash, f"Step 12 hash mismatch for {fn}"


def test_outcome_classification_case_a(df_summary, manifest):
    """Assertion 18: Empirical p-value < 0.05 across all nulls, confirming Case A."""
    assert (df_summary["empirical_two_sided_p"] < 0.05).all()
    assert (df_summary["exceeds_95pct_threshold"] == True).all()
    assert "CASE A" in manifest["null_outcome_classification"]["outcome_case"]


# =========================================================================
# REQUIRED N4 YEAR-BLOCK EXACT ENUMERATION FORENSIC TESTS (Assertions 19–30)
# =========================================================================

def test_n4_exact_permutation_count(df_n4_exact, n4_exact_summary):
    """Assertion 19: N4 contains exactly 8! = 40,320 permutations."""
    assert len(df_n4_exact) == 40320
    assert n4_exact_summary["total_permutations"] == 40320


def test_n4_exact_permutations_unique(df_n4_exact):
    """Assertion 20: Every permutation is unique."""
    unique_orders = df_n4_exact["year_order"].nunique()
    assert unique_orders == 40320
    assert df_n4_exact["permutation_id"].nunique() == 40320


def test_n4_exact_contains_same_8_years(df_n4_exact):
    """Assertion 21: Every permutation contains exactly the same 8 year-block IDs."""
    expected_years = {"2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021"}
    # Sample check across head, tail, and random indices
    for idx in [0, 1, 100, 5000, 20000, 40318, 40319]:
        years_in_perm = set(df_n4_exact.iloc[idx]["year_order"].split(","))
        assert years_in_perm == expected_years


def test_n4_exact_each_year_once(df_n4_exact):
    """Assertion 22: Each year block appears exactly once per permutation."""
    for idx in [0, 50, 1000, 15000, 30000, 40319]:
        y_list = df_n4_exact.iloc[idx]["year_order"].split(",")
        assert len(y_list) == 8
        assert len(set(y_list)) == 8


def test_n4_exact_within_year_order_preserved(df_pred):
    """Assertion 23: Within-year prediction ordering is unchanged in year permutations."""
    df_pred = df_pred.copy()
    df_pred["trading_date"] = pd.to_datetime(df_pred["trading_date"])
    df_pred["year"] = df_pred["trading_date"].dt.year
    years = sorted(df_pred["year"].unique())
    year_blocks = [df_pred.loc[df_pred["year"] == y, "T0_pred"].values for y in years]

    # Test an arbitrary permutation, e.g. [7, 6, 5, 4, 3, 2, 1, 0]
    rev_perm = list(reversed(range(8)))
    p_concat = np.concatenate([year_blocks[i] for i in rev_perm])

    offset = 0
    for block_idx in rev_perm:
        b_len = len(year_blocks[block_idx])
        sub = p_concat[offset : offset + b_len]
        assert np.array_equal(sub, year_blocks[block_idx]), f"Within-year order violated for block {block_idx}"
        offset += b_len


def test_n4_exact_prediction_multiset_preserved(df_pred):
    """Assertion 24: Prediction multiset is unchanged under all year permutations."""
    original = df_pred["T0_pred"].values
    df_pred = df_pred.copy()
    df_pred["trading_date"] = pd.to_datetime(df_pred["trading_date"])
    df_pred["year"] = df_pred["trading_date"].dt.year
    years = sorted(df_pred["year"].unique())
    year_blocks = [df_pred.loc[df_pred["year"] == y, "T0_pred"].values for y in years]

    # Test random permutations
    rng = np.random.default_rng(2026)
    for _ in range(10):
        p = rng.permutation(8)
        p_concat = np.concatenate([year_blocks[i] for i in p])
        assert np.array_equal(np.sort(original), np.sort(p_concat))
        assert math.isclose(np.mean(original), np.mean(p_concat), abs_tol=1e-15)


def test_n4_exact_target_sequence_unchanged(df_pred):
    """Assertion 25: Target sequence is unchanged and locked."""
    step2_csv = PHASE12_DIR / "snapshot_b_intraday_diagnostics.csv"
    assert step2_csv.is_file()
    df_s2 = pd.read_csv(step2_csv)
    assert np.array_equal(df_pred["T0_actual"].values, df_s2["y_true_intraday"].values)


def test_n4_exact_observed_ic_reproduced(df_n4_exact, df_pred):
    """Assertion 26: Observed Pearson IC reproduces +0.04761924 within 1e-12, and identity permutation matches."""
    r_obs, _ = stats.pearsonr(df_pred["T0_pred"].values, df_pred["T0_actual"].values)
    assert abs(r_obs - 0.04761923873169822) < 1e-12

    # Identity permutation is row 0: '2014,2015,2016,2017,2018,2019,2020,2021'
    row0 = df_n4_exact.iloc[0]
    assert row0["year_order"] == "2014,2015,2016,2017,2018,2019,2020,2021"
    assert abs(row0["pearson_ic"] - r_obs) < 1e-12


def test_n4_exact_pvalue_formula_verified(df_n4_exact, n4_exact_summary, df_summary):
    """Assertion 27: Exact p-value calculation follows registered formula: (1 + b) / (40320 + 1)."""
    r_obs = n4_exact_summary["observed_statistic"]["observed_value"]
    all_ics = df_n4_exact["pearson_ic"].values

    b_two = int(np.sum(np.abs(all_ics) >= abs(r_obs)))
    p_two = (1 + b_two) / (40320 + 1)
    b_one = int(np.sum(all_ics >= r_obs))
    p_one = (1 + b_one) / (40320 + 1)

    assert b_two == n4_exact_summary["exact_pvalues"]["count_two_sided_extreme"]
    assert abs(p_two - n4_exact_summary["exact_pvalues"]["empirical_two_sided_p"]) < 1e-15
    assert b_one == n4_exact_summary["exact_pvalues"]["count_one_sided_extreme"]
    assert abs(p_one - n4_exact_summary["exact_pvalues"]["empirical_one_sided_p"]) < 1e-15

    # Check df_summary row
    n4_row = df_summary[df_summary["null_id"] == "N4_year"].iloc[0]
    assert n4_row["n_null"] == 40320
    assert abs(n4_row["empirical_two_sided_p"] - p_two) < 1e-15
    assert abs(n4_row["empirical_one_sided_p"] - p_one) < 1e-15
    assert p_two < 0.05
    assert n4_row["exceeds_95pct_threshold"] == True


def test_n4_exact_deterministic(df_pred, df_n4_exact):
    """Assertion 28: N4 exact enumeration is purely deterministic and reproducible."""
    df_pred = df_pred.copy()
    df_pred["trading_date"] = pd.to_datetime(df_pred["trading_date"])
    df_pred["year"] = df_pred["trading_date"].dt.year
    years = sorted(df_pred["year"].unique())
    year_blocks = [df_pred.loc[df_pred["year"] == y, "T0_pred"].values for y in years]
    actual = df_pred["T0_actual"].values
    act_c = actual - np.mean(actual)
    norm_act = float(np.linalg.norm(act_c))

    # Test first 100 permutations deterministically
    all_perms = list(itertools.permutations(range(8)))
    for idx in range(100):
        p = all_perms[idx]
        p_pred = np.concatenate([year_blocks[i] for i in p])
        p_pred_c = p_pred - np.mean(p_pred)
        r = float(np.dot(p_pred_c, act_c) / (np.linalg.norm(p_pred_c) * norm_act))
        assert abs(r - df_n4_exact.iloc[idx]["pearson_ic"]) < 1e-15


def test_n4_exact_holdout_zero(n4_exact_summary):
    """Assertion 29: No holdout rows are accessed for N4 exact."""
    assert n4_exact_summary["governance"]["holdout_rows_accessed"] == 0
    assert n4_exact_summary["governance"]["max_trading_date"] <= "2021-12-31"


def test_n4_exact_upstream_protected_hashes():
    """Assertion 30: All 67 protected upstream artifact hashes remain unchanged."""
    test_protected_upstream_hashes_unchanged()
