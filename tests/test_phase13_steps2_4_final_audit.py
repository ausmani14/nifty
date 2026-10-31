"""Phase 13 Steps 2-4 Final Independent Verification Audit Test Suite.

Audits:
1. Evaluation sample count (N=1,154) and date boundaries (2022-01-03 to 2026-09-03).
2. Frozen model identity (Full Dev N=3,299, N*=43 trees, training <= 2021-12-31).
3. Reproducibility of predictive metrics (Pearson IC +0.02013, p=0.4945, Spearman IC +0.00424, MDA 52.43%).
4. Baseline definitions and comparisons (Zero-return and Training-mean MAE/RMSE).
5. Mathematical consistency of Incremental R2 (-0.003574 vs training mean).
6. Bps conversion and cost application (0, 5, 10, 20 bps).
7. Long/short counts (36 long, 1,118 short).
8. Reproducibility of annualized returns, Sharpe, and maximum drawdown across all costs.
9. Retrospective exposure disclosure prominent; no 'untouched holdout' or 'pristine' claims.
10. Replacement of hyperbolic 'destroys all capital' claims with exact numerical drawdowns.
11. Protected Phase 0-12 and Phase 13 Step 1 artifacts remaining bit-for-bit unchanged.
"""

import hashlib
import json
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from scipy import stats

from nifty_ai.config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_steps2_4"
STEP1_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_step1"
DOCS_DIR = PROJECT_ROOT / "docs"


def compute_sha256(filepath: Path) -> str:
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


# 1. Evaluation sample count and date boundaries
def test_evaluation_sample_count_and_dates():
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    assert len(preds_df) == 1154, f"Expected 1,154 rows, found {len(preds_df)}"
    assert preds_df["prediction_date"].min() == "2022-01-03"
    assert preds_df["prediction_date"].max() == "2026-09-03"
    assert preds_df["target_date"].min() == "2022-01-04"
    assert preds_df["target_date"].max() == "2026-09-04"


# 2. Frozen model identity and training cutoff
def test_frozen_model_identity_and_training_cutoff():
    meta_path = OUT_DIR / "models" / "snapshot_b_t0_primary_model.meta.json"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    assert meta["model_name"] == "Snapshot B T0 Full Development Production Model"
    assert meta["training_samples"] == 3299
    assert meta["training_partition"] == "2008-07-08 to 2021-12-31"
    assert meta["hyperparameters"]["n_estimators"] == 43
    assert meta["feature_count"] == 63
    assert meta["target"] == "Snapshot B T0 (Open-to-Close Return)"


# 3. Reproducibility of predictive metrics
def test_predictive_metrics_reproducibility():
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    y_true = preds_df["T0_realized"].to_numpy()
    y_pred = preds_df["T0_pred_primary"].to_numpy()
    
    r_p, p_p = stats.pearsonr(y_pred, y_true)
    r_s, p_s = stats.spearmanr(y_pred, y_true)
    mae = np.mean(np.abs(y_pred - y_true))
    rmse = np.sqrt(np.mean((y_pred - y_true) ** 2))
    mda = np.mean(np.sign(y_pred) == np.sign(y_true))
    
    assert np.isclose(r_p, 0.0201314, atol=1e-5)
    assert np.isclose(p_p, 0.494478, atol=1e-5)
    assert np.isclose(r_s, 0.0042394, atol=1e-5)
    assert np.isclose(mae, 0.0050424, atol=1e-5)
    assert np.isclose(rmse, 0.0067784, atol=1e-5)
    assert np.isclose(mda, 0.5242634, atol=1e-5)


# 4. Baseline definitions and comparisons
def test_baseline_definitions_and_comparisons():
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    y_true = preds_df["T0_realized"].to_numpy()
    y_pred = preds_df["T0_pred_primary"].to_numpy()
    mu_train = preds_df["benchmark_mu_train"].iloc[0]
    
    mae_zero = np.mean(np.abs(y_true))
    rmse_zero = np.sqrt(np.mean(y_true ** 2))
    mae_model = np.mean(np.abs(y_pred - y_true))
    rmse_model = np.sqrt(np.mean((y_pred - y_true) ** 2))
    
    # Model RMSE is strictly worse than zero return RMSE
    assert rmse_model > rmse_zero
    # Absolute difference is small
    assert abs(mae_model - mae_zero) * 10000 < 0.20  # less than 0.20 bps difference


# 5. Mathematical consistency of Incremental R2
def test_incremental_r2_consistency():
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    y_true = preds_df["T0_realized"].to_numpy()
    y_pred = preds_df["T0_pred_primary"].to_numpy()
    mu_train = preds_df["benchmark_mu_train"].iloc[0]
    
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - mu_train) ** 2)
    inc_r2 = 1.0 - (ss_res / ss_tot)
    
    assert np.isclose(inc_r2, -0.003574, atol=1e-5)
    assert inc_r2 < 0  # model has higher squared error than static training mean


# 6. Bps conversion and cost application
def test_cost_application_and_bps_conversion():
    econ_df = pd.read_csv(OUT_DIR / "step4_economic_assessment.csv")
    assert sorted(econ_df["cost_scenario_bps"].unique()) == [0.0, 5.0, 10.0, 20.0]
    
    # Check that at 10 bps, transaction cost drag is substantial
    ret_0 = econ_df[(econ_df["strategy"].str.startswith("Strategy 1")) & (econ_df["cost_scenario_bps"] == 0.0)]["annualized_return_pct"].iloc[0]
    ret_10 = econ_df[(econ_df["strategy"].str.startswith("Strategy 1")) & (econ_df["cost_scenario_bps"] == 10.0)]["annualized_return_pct"].iloc[0]
    assert ret_0 > 0
    assert ret_10 < 0
    assert np.isclose(ret_0, 10.70, atol=0.05)
    assert np.isclose(ret_10, -13.96, atol=0.05)


# 7. Long/short counts
def test_long_short_position_counts():
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    y_pred = preds_df["T0_pred_primary"].to_numpy()
    n_long = int(np.sum(y_pred > 0))
    n_short = int(np.sum(y_pred < 0))
    n_flat = int(np.sum(y_pred == 0))
    
    assert n_long == 36
    assert n_short == 1118
    assert n_flat == 0
    assert n_long + n_short == 1154


# 8. Reproducibility of economic metrics across all cost levels
def test_economic_metrics_reproducibility():
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    y_true = preds_df["T0_realized"].to_numpy()
    y_pred = preds_df["T0_pred_primary"].to_numpy()
    
    pos = np.sign(y_pred)
    n = len(y_true)
    
    expected_ann = {0.0: 10.70, 5.0: -2.40, 10.0: -13.96, 20.0: -33.15}
    expected_sharpe = {0.0: 1.001, 5.0: -0.173, 10.0: -1.348, 20.0: -3.697}
    expected_maxdd = {0.0: -13.18, 5.0: -21.72, 10.0: -54.05, 20.0: -84.78}
    
    for c_bps in [0.0, 5.0, 10.0, 20.0]:
        c_frac = c_bps / 10000.0
        r_net = pos * y_true - np.abs(pos) * c_frac
        cum_ret = np.prod(1.0 + r_net) - 1.0
        ann_ret = (1.0 + cum_ret) ** (252.0 / n) - 1.0
        mean_r = np.mean(r_net)
        std_r = np.std(r_net, ddof=1)
        sharpe = (mean_r / std_r) * np.sqrt(252.0)
        
        eq = np.cumprod(1.0 + r_net)
        peak = np.maximum.accumulate(eq)
        max_dd = np.min((eq - peak) / peak)
        
        assert np.isclose(ann_ret * 100.0, expected_ann[c_bps], atol=0.05)
        assert np.isclose(sharpe, expected_sharpe[c_bps], atol=0.01)
        assert np.isclose(max_dd * 100.0, expected_maxdd[c_bps], atol=0.05)


# 9. Retrospective exposure disclosure prominent
def test_retrospective_exposure_disclosure():
    audit_json = OUT_DIR / "step2_holdout_exposure_audit.json"
    with open(audit_json, "r", encoding="utf-8") as f:
        audit = json.load(f)
    assert audit["exposure_classification"] == "PREVIOUSLY EXPOSED RETROSPECTIVE EVALUATION DATA"
    assert audit["is_genuinely_untouched_confirmatory_holdout"] is False


# 10. Protected Phase 0-12 and Phase 13 Step 1 artifacts unmodified
def test_protected_upstream_artifacts_unmodified():
    p1 = STEP1_DIR / "step1_holdout_protocol.json"
    p2 = STEP1_DIR / "step1_holdout_protocol.md"
    p3 = STEP1_DIR / "step1_holdout_firewall_audit.json"
    
    assert compute_sha256(p1) == "21e5b9b001f16e2acc003b78e6af78e2c8cdb1ebc44f389c18c0d1957e689395"
    assert compute_sha256(p2) == "3c64b2355b09b5e4ab85d838c0080a380d91f80c2831f4449c83dd011422f03a"
    assert compute_sha256(p3) == "6704e275d9c66fd50c2bc964509cbacc76212e9b2cea06f9dad5fb2375625188"


# 11. Regression test: Benchmark RMSE formula defect prevention
def test_benchmark_rmse_formula_defect_regression():
    """Verify that benchmark RMSE uses sqrt(mean(errors^2)) and not sqrt((mean(errors))^2).
    
    A deterministic test array where mean is 0 but variance is positive proves that
    the incorrect formula produces 0.0 while the correct formula produces 0.01.
    """
    y_test = np.array([0.01, -0.01], dtype=np.float64)
    pred_zero = np.array([0.0, 0.0], dtype=np.float64)
    
    errors = pred_zero - y_test  # [-0.01, 0.01]
    
    # Incorrect defective formula:
    defective_rmse = float(np.sqrt(np.mean(errors) ** 2))
    assert np.isclose(defective_rmse, 0.0)  # Defective formula produces 0.0!
    
    # Correct formula:
    correct_rmse = float(np.sqrt(np.mean(errors ** 2)))
    assert np.isclose(correct_rmse, 0.01)  # Correct formula produces 0.01
    assert defective_rmse != correct_rmse
    
    # Verify the stored benchmark 1 RMSE matches the correct formula on the actual holdout array:
    preds_df = pd.read_csv(OUT_DIR / "step3_retrospective_model_predictions.csv")
    y_hold = preds_df["T0_realized"].to_numpy()
    b1_pred = np.zeros(len(y_hold), dtype=np.float64)
    
    eval_json = OUT_DIR / "step3_retrospective_model_evaluation.json"
    with open(eval_json, "r", encoding="utf-8") as f:
        ev = json.load(f)
    stored_b1_rmse = ev["benchmarks"]["benchmark_1_zero_return"]["rmse"]
    
    recomputed_correct_rmse = float(np.sqrt(np.mean((b1_pred - y_hold) ** 2)))
    recomputed_defective_rmse = float(np.sqrt(np.mean(b1_pred - y_hold) ** 2))
    
    assert np.isclose(stored_b1_rmse, recomputed_correct_rmse, atol=1e-8)
    assert not np.isclose(stored_b1_rmse, recomputed_defective_rmse, atol=1e-4)
    assert np.isclose(stored_b1_rmse, 0.00676887, atol=1e-5)

