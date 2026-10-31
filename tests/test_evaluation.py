"""Unit and anti-leakage verification tests for Phase 6 evaluation, splitting, and statistics."""

from datetime import date, timedelta
import numpy as np
import pytest

from nifty_ai.evaluation.calibration import (
    PlattScaler,
    compute_reliability_report,
)
from nifty_ai.evaluation.classification_metrics import (
    compute_expected_calibration_error,
    evaluate_classification_metrics,
)
from nifty_ai.evaluation.regression_metrics import evaluate_regression_metrics
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.evaluation.statistical_tests import (
    diebold_mariano_test,
    paired_bootstrap_loss_difference,
)


def _generate_synthetic_dates(start_year=2008, end_year=2026):
    """Generate business-day-like dates from 2008 to 2026."""
    dates = []
    curr = date(start_year, 7, 8)
    end = date(end_year, 9, 4)
    while curr <= end:
        if curr.weekday() < 5:  # Monday-Friday
            dates.append(curr)
        curr += timedelta(days=1)
    return dates


def test_expanding_window_strictly_monotonic():
    """Verify that walk-forward training windows strictly expand monotonically."""
    dates = _generate_synthetic_dates()
    splitter = WalkForwardSplitter()
    folds = splitter.split_development(dates)

    assert len(folds) == 8
    prev_train_len = 0
    for fold in folds:
        train_len = len(fold.train_indices)
        assert train_len > prev_train_len, f"Training window did not expand in Fold {fold.fold_id}"
        prev_train_len = train_len


def test_zero_train_val_overlap():
    """Verify zero overlap between training and validation indices across all folds."""
    dates = _generate_synthetic_dates()
    splitter = WalkForwardSplitter()
    folds = splitter.split_development(dates)

    for fold in folds:
        train_set = set(fold.train_indices)
        val_set = set(fold.val_indices)
        assert len(train_set.intersection(val_set)) == 0, f"Overlap detected in Fold {fold.fold_id}"
        assert fold.train_end_date < fold.val_start_date, (
            f"Leakage detected in Fold {fold.fold_id}: {fold.train_end_date} >= {fold.val_start_date}"
        )


def test_final_holdout_strict_isolation():
    """Verify that dates >= 2022-01-01 are completely isolated from all development folds."""
    dates = _generate_synthetic_dates()
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    folds = splitter.split_development(dates)

    cutoff = date(2021, 12, 31)
    for fold in folds:
        assert fold.train_end_date <= cutoff, f"Train date breached holdout in Fold {fold.fold_id}"
        assert fold.val_end_date <= cutoff, f"Validation date breached holdout in Fold {fold.fold_id}"

    dev_idx, holdout_idx = splitter.get_development_and_holdout_indices(dates)
    date_arr = np.array(dates)
    assert np.all(date_arr[dev_idx] <= cutoff)
    assert np.all(date_arr[holdout_idx] > cutoff)


def test_classification_metrics_computation():
    """Verify classification metrics on synthetic test arrays."""
    y_true = np.array([0, 1, 2, 0, 1, 2])
    y_prob = np.array([
        [0.8, 0.1, 0.1],
        [0.1, 0.8, 0.1],
        [0.1, 0.1, 0.8],
        [0.7, 0.2, 0.1],
        [0.2, 0.6, 0.2],
        [0.1, 0.2, 0.7],
    ])
    metrics = evaluate_classification_metrics(y_true, y_prob)

    assert metrics.total_samples == 6
    assert metrics.accuracy == 1.0
    assert metrics.macro_f1 == 1.0
    assert metrics.log_loss < 0.6
    assert metrics.brier_score < 0.2
    assert 0.0 <= metrics.expected_calibration_error <= 1.0


def test_regression_metrics_computation():
    """Verify regression metrics on known linear predictions."""
    y_true = np.array([0.01, 0.02, -0.01, 0.03, -0.02])
    y_pred = np.array([0.01, 0.02, -0.01, 0.03, -0.02])  # Perfect predictions
    metrics = evaluate_regression_metrics(y_true, y_pred)

    assert metrics.total_samples == 5
    assert metrics.mae == pytest.approx(0.0)
    assert metrics.rmse == pytest.approx(0.0)
    assert metrics.r2_score == pytest.approx(1.0)
    assert metrics.pearson_ic == pytest.approx(1.0)
    assert metrics.directional_accuracy == pytest.approx(1.0)


def test_diebold_mariano_hac_test():
    """Verify Diebold-Mariano test correctly identifies significant loss reduction."""
    rng = np.random.default_rng(42)
    n = 100
    y_true = rng.normal(0, 0.01, size=n)

    # Model 1 has high error, Model 2 has low error
    pred1 = y_true + rng.normal(0, 0.05, size=n)
    pred2 = y_true + rng.normal(0, 0.005, size=n)

    dm_res = diebold_mariano_test(y_true, pred1, pred2, h=1, loss_type="absolute")

    # Mean loss diff should be positive (Model 2 is significantly better)
    assert dm_res.mean_loss_diff > 0
    assert dm_res.hln_p_value < 0.01
    assert "significantly outperforms" in dm_res.interpretation


def test_paired_bootstrap_loss_difference():
    """Verify block bootstrap produces valid confidence intervals."""
    rng = np.random.default_rng(50)
    n = 100
    y_true = rng.integers(0, 3, size=n)

    # Good model probabilities vs uniform random
    p_good = np.full((n, 3), 0.1)
    for i, t in enumerate(y_true):
        p_good[i, t] = 0.8
    p_uniform = np.full((n, 3), 1/3)

    boot_res = paired_bootstrap_loss_difference(
        y_true, p_uniform, p_good, block_size=5, n_bootstrap=200, random_seed=42
    )

    # Good model has lower loss, so p_uniform - p_good > 0
    assert boot_res.mean_loss_diff > 0
    assert boot_res.ci_lower > 0
    assert boot_res.significant_at_05 is True


def test_platt_scaler_probability_simplex():
    """Verify PlattScaler preserves exact probability simplex."""
    rng = np.random.default_rng(60)
    n = 150
    y_true = rng.integers(0, 3, size=n)
    raw_probs = rng.uniform(0.1, 0.9, size=(n, 3))
    raw_probs = raw_probs / np.sum(raw_probs, axis=1, keepdims=True)

    scaler = PlattScaler(random_seed=42)
    scaler.fit(raw_probs, y_true)
    cal_probs = scaler.transform(raw_probs)

    assert cal_probs.shape == (n, 3)
    np.testing.assert_allclose(np.sum(cal_probs, axis=1), 1.0, rtol=1e-5)
    assert np.all(cal_probs >= 0.0)
    assert np.all(cal_probs <= 1.0)
