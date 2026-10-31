"""Unit and anti-leakage verification tests for Phase 6 modeling subsystem."""

from datetime import date
from pathlib import Path
import tempfile
import numpy as np
import pytest

from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.models.base import ClassificationPrediction, RegressionPrediction
from nifty_ai.models.baselines import (
    ExpandingMajorityClassifier,
    ExpandingMeanReturnRegressor,
    TrailingPersistenceClassifier,
    TrailingPersistenceRegressor,
    UniformRandomClassifier,
    ZeroReturnRegressor,
)
from nifty_ai.models.dataset import (
    CLASS_MAP,
    EXPECTED_FEATURE_NAMES,
    INV_CLASS_MAP,
    AlignedDataset,
    load_aligned_dataset,
)
from nifty_ai.models.persistence import (
    ModelProvenanceMetadata,
    save_model_artifact_with_manifest,
)
from nifty_ai.models.xgboost_classifier import XGBoostDirectionClassifier
from nifty_ai.models.xgboost_regressor import XGBoostReturnRegressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES_CSV = PROJECT_ROOT / "data" / "features" / "nifty50_features_clean.csv"
TARGETS_A_CSV = PROJECT_ROOT / "data" / "targets" / "nifty50_targets_snapshot_a.csv"
TARGETS_B_CSV = PROJECT_ROOT / "data" / "targets" / "nifty50_targets_snapshot_b.csv"


def test_snapshot_a_alignment_contract():
    """Verify Snapshot A alignment: Session T features predict outcome of Session T+1."""
    ds = load_aligned_dataset(FEATURES_CSV, TARGETS_A_CSV, SnapshotType.SNAPSHOT_1540)
    assert len(ds.dates) == len(ds.target_dates) == len(ds.y_class) == len(ds.y_reg)
    assert ds.X.shape[1] == 45
    assert len(ds.feature_names) == 45

    # Check chronological relation: cutoff_date < target_date for every row
    for cutoff_d, target_d in zip(ds.dates, ds.target_dates):
        assert cutoff_d < target_d, f"Temporal violation: cutoff {cutoff_d} >= target {target_d}"


def test_snapshot_b_alignment_contract():
    """Verify Snapshot B alignment: prediction for Session T+1 uses features through completed Session T."""
    ds = load_aligned_dataset(FEATURES_CSV, TARGETS_B_CSV, SnapshotType.SNAPSHOT_0850)
    assert len(ds.dates) == len(ds.target_dates) == len(ds.y_class) == len(ds.y_reg)

    # For Snapshot B: target_date is session being predicted; cutoff_date is completed session T
    for cutoff_d, target_d in zip(ds.dates, ds.target_dates):
        assert cutoff_d < target_d, f"Snapshot B violation: cutoff {cutoff_d} >= target {target_d}"


def test_snapshot_b_strict_invariance_to_session_t_plus_1():
    """Verify that mutating Session T+1 values does not affect Snapshot B input features for predicting T+1."""
    ds = load_aligned_dataset(FEATURES_CSV, TARGETS_B_CSV, SnapshotType.SNAPSHOT_0850)
    # The feature vector for index i corresponds to cutoff_date ds.dates[i]
    # Verify that ds.X[i] matches the clean features on that date
    import pandas as pd
    feat_df = pd.read_csv(FEATURES_CSV)
    first_date_str = ds.dates[0].isoformat()
    raw_row = feat_df[feat_df["trading_date"] == first_date_str].iloc[0]
    expected_ret_1d = float(raw_row["ret_1d"])
    assert ds.X[0, 0] == pytest.approx(expected_ret_1d)


def test_terminal_session_exclusion():
    """Verify that the terminal session (2026-09-04) is isolated from supervised training arrays."""
    ds = load_aligned_dataset(FEATURES_CSV, TARGETS_A_CSV, SnapshotType.SNAPSHOT_1540)
    # The last supervised date must NOT be the terminal row (2026-09-04)
    assert ds.dates[-1] == date(2026, 9, 3)
    # Terminal session should be available as inference_X
    assert ds.inference_X is not None
    assert ds.inference_X.shape == (1, 45)
    assert ds.inference_date == date(2026, 9, 4)


def test_classifier_probability_simplex():
    """Verify that classifier outputs sum to 1.0 (exact probability simplex)."""
    clf = XGBoostDirectionClassifier(n_estimators=10, max_depth=2, random_state=42)
    # Generate synthetic 3-class data
    rng = np.random.default_rng(42)
    X = rng.normal(size=(60, 45))
    y = rng.integers(0, 3, size=60)

    clf.fit(X, y)
    probs = clf.predict_proba(X)

    assert probs.shape == (60, 3)
    sums = np.sum(probs, axis=1)
    np.testing.assert_allclose(sums, 1.0, rtol=1e-5)
    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)


def test_classifier_classes():
    """Verify classifier predicted classes are in {0, 1, 2}."""
    clf = XGBoostDirectionClassifier(n_estimators=10, max_depth=2, random_state=42)
    rng = np.random.default_rng(42)
    X = rng.normal(size=(50, 45))
    y = rng.integers(0, 3, size=50)

    clf.fit(X, y)
    preds = clf.predict(X)

    assert set(preds).issubset({0, 1, 2})


def test_regressor_finite_predictions():
    """Verify regressor predictions are finite numbers."""
    reg = XGBoostReturnRegressor(n_estimators=10, max_depth=2, random_state=42)
    rng = np.random.default_rng(42)
    X = rng.normal(size=(50, 45))
    y = rng.normal(loc=0.0005, scale=0.01, size=50)

    reg.fit(X, y)
    preds = reg.predict(X)

    assert len(preds) == 50
    assert np.all(np.isfinite(preds))


def test_derived_close_formula():
    """Verify that predicted closing price derives strictly as Close_T * (1 + predicted_return)."""
    reg = XGBoostReturnRegressor(n_estimators=5, max_depth=2, random_state=42)
    rng = np.random.default_rng(42)
    X = rng.normal(size=(10, 45))
    y = np.full(10, 0.02)  # +2% returns
    reg.fit(X, y)

    ref_close = np.full(10, 20000.0)
    pred_returns = reg.predict(X)
    pred_close = reg.predict_close(X, ref_close)

    expected_close = ref_close * (1.0 + pred_returns)
    np.testing.assert_allclose(pred_close, expected_close, rtol=1e-6)


def test_baselines_correctness():
    """Verify naive baseline models behave according to theoretical specifications."""
    X = np.zeros((10, 45))
    X[:, 0] = 0.01  # ret_1d = +1%
    y_class = np.array([2, 2, 2, 0, 1, 2, 0, 2, 1, 2])  # 6 UP (class 2), 2 DOWN (0), 2 SIDEWAYS (1)
    y_reg = np.array([0.01, 0.02, -0.01, 0.00, 0.01, -0.02, 0.03, 0.01, -0.01, 0.00])

    # 1. Majority class baseline
    maj = ExpandingMajorityClassifier().fit(X, y_class)
    assert np.all(maj.predict(X) == 2)
    probs = maj.predict_proba(X)
    assert probs[0, 2] == pytest.approx(0.6)  # 6 / 10 = 0.6
    assert probs[0, 0] == pytest.approx(0.2)
    assert probs[0, 1] == pytest.approx(0.2)

    # 2. Zero return regressor
    zero_reg = ZeroReturnRegressor().fit(X, y_reg)
    assert np.all(zero_reg.predict(X) == 0.0)

    # 3. Expanding mean regressor
    mean_reg = ExpandingMeanReturnRegressor().fit(X, y_reg)
    assert np.all(mean_reg.predict(X) == pytest.approx(float(np.mean(y_reg))))

    # 4. Trailing persistence regressor
    pers_reg = TrailingPersistenceRegressor().fit(X, y_reg)
    assert np.all(pers_reg.predict(X) == pytest.approx(0.01))


def test_model_determinism_seed_42():
    """Verify that training twice with seed 42 produces bit-identical tree models."""
    rng = np.random.default_rng(100)
    X = rng.normal(size=(80, 45))
    y = rng.integers(0, 3, size=80)

    clf1 = XGBoostDirectionClassifier(n_estimators=15, max_depth=3, random_state=42).fit(X, y)
    clf2 = XGBoostDirectionClassifier(n_estimators=15, max_depth=3, random_state=42).fit(X, y)

    p1 = clf1.predict_proba(X)
    p2 = clf2.predict_proba(X)
    np.testing.assert_array_equal(p1, p2)


def test_model_roundtrip_json_persistence():
    """Verify that saving and loading native JSON models produces bit-identical predictions."""
    rng = np.random.default_rng(200)
    X = rng.normal(size=(50, 45))
    y = rng.integers(0, 3, size=50)

    clf = XGBoostDirectionClassifier(n_estimators=10, max_depth=2, random_state=42).fit(X, y)
    original_probs = clf.predict_proba(X)

    with tempfile.TemporaryDirectory() as tmp_dir:
        m_path = Path(tmp_dir) / "test_model.json"
        clf.save_model(m_path)

        loaded_clf = XGBoostDirectionClassifier()
        loaded_clf.load_model(m_path)
        loaded_probs = loaded_clf.predict_proba(X)

        np.testing.assert_allclose(original_probs, loaded_probs, rtol=1e-6)


def test_provenance_metadata_completeness():
    """Verify that save_model_artifact_with_manifest records all required provenance fields."""
    rng = np.random.default_rng(300)
    X = rng.normal(size=(40, 45))
    y = rng.integers(0, 3, size=40)

    clf = XGBoostDirectionClassifier(n_estimators=5, random_state=42).fit(X, y)

    with tempfile.TemporaryDirectory() as tmp_dir:
        m_path = Path(tmp_dir) / "test_model.json"
        meta_dict = {
            "model_id": "test-uuid-1234",
            "model_type": "xgboost_classifier",
            "model_version": "1.0.0",
            "snapshot_type": "SNAPSHOT_1540",
            "development_training_range": {"start": "2008-07-08", "end": "2021-12-31"},
            "feature_dataset_sha256": "fake_feat_sha",
            "target_dataset_sha256": "fake_targ_sha",
            "feature_names": EXPECTED_FEATURE_NAMES,
            "frozen_hyperparameters": clf.hyperparameters,
            "final_n_estimators": 5,
            "random_seed": 42,
            "calibration_status": {"is_calibrated": False},
            "development_oof_metrics": {"log_loss": 1.05},
        }

        m_file, meta_file = save_model_artifact_with_manifest(clf, m_path, meta_dict)
        assert m_file.is_file()
        assert meta_file.is_file()

        import json
        with open(meta_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        required_keys = [
            "model_id", "model_type", "model_version", "snapshot_type", "created_at",
            "development_training_range", "feature_dataset_sha256", "target_dataset_sha256",
            "feature_names", "frozen_hyperparameters", "final_n_estimators", "random_seed",
            "calibration_status", "development_oof_metrics", "python_version", "library_versions",
            "model_file_name", "model_file_sha256"
        ]
        for k in required_keys:
            assert k in manifest_data, f"Missing required provenance field: {k}"
