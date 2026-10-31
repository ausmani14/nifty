"""Test suite for Phase 9 Step 4 Incremental News Predictive-Value Experiment.

Validates:
1. Protected SHA-256 checksums across historical and terminal artifacts.
2. Exact sample counts (4,453 total, 3,299 dev, 1,960 OOF, 1,154 holdout).
3. Exact feature space definitions (45 Price, 18 Context, 49 News).
4. Mutual exclusivity and completeness of the 6 news ablation groups.
5. Zero NaNs and Infs across all multimodal matrices.
6. Integrity and schema of generated experiment result artifacts.
7. Statistical test properties (ordered CIs, valid p-values).
"""

from datetime import date
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import (
    ALL_NEWS_FEATURE_NAMES,
    CONTEXT_FEATURE_NAMES,
    MODEL_FEATURE_SPECS,
    NEWS_COUNT_FEATURES,
    NEWS_EVENT_FEATURES,
    NEWS_FEATURE_GROUPS,
    NEWS_IMPORTANCE_FEATURES,
    NEWS_NOVELTY_FEATURES,
    NEWS_SENTIMENT_FEATURES,
    NEWS_COMPANY_FEATURES,
    PRICE_FEATURE_NAMES,
    REGIME_INTERACTION_FEATURES,
    load_multimodal_dataset,
)

# ---------------------------------------------------------------------------
# 1. Protected Checksum Tests
# ---------------------------------------------------------------------------

PROTECTED_HASHES = {
    "data/interim/news/raw_authentic_news_inventory.jsonl": "6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3",
    "data/interim/news/gold_holdout_annotation_input.csv": "0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199",
    "data/interim/news/raw_authentic_news_terminal_2022_2026_step2e.jsonl": "5d5daf5ed7c844e86d45dc6a893f03b1d4f523183e29200d94b592329136f6fd",
    "data/interim/news/features_news_snapshot_a.csv": "487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7",
    "data/interim/news/features_news_snapshot_b.csv": "f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606",
    "data/interim/news/features_news_snapshot_delta.csv": "8923c11583fb87fe8458f00aaf714eadacb8a3d402a7143a5b2483549c8ece4c",
}


def test_protected_checksums_intact() -> None:
    """Assert 100% byte-for-byte SHA-256 match for all 6 protected Phase 8 and Phase 9 files."""
    for rel_path, expected_sha in PROTECTED_HASHES.items():
        file_path = PROJECT_ROOT / rel_path
        assert file_path.is_file(), f"Protected file missing: {rel_path}"
        actual_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_sha == expected_sha, f"Hash mismatch for {rel_path}: {actual_sha} != {expected_sha}"


# ---------------------------------------------------------------------------
# 2. Feature Space Dimension & Disjointness Tests
# ---------------------------------------------------------------------------

def test_feature_dimensions_exact() -> None:
    """Verify exact counts of features in each category."""
    assert len(PRICE_FEATURE_NAMES) == 45
    assert len(CONTEXT_FEATURE_NAMES) == 18
    assert len(ALL_NEWS_FEATURE_NAMES) == 49
    assert len(REGIME_INTERACTION_FEATURES) == 3

    assert len(NEWS_COUNT_FEATURES) == 6
    assert len(NEWS_SENTIMENT_FEATURES) == 10
    assert len(NEWS_IMPORTANCE_FEATURES) == 4
    assert len(NEWS_EVENT_FEATURES) == 18
    assert len(NEWS_NOVELTY_FEATURES) == 3
    assert len(NEWS_COMPANY_FEATURES) == 8


def test_news_ablation_groups_mutually_disjoint() -> None:
    """Verify that the 6 news ablation groups have pairwise zero overlap and sum to 49."""
    groups = list(NEWS_FEATURE_GROUPS.values())
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            intersection = set(groups[i]).intersection(set(groups[j]))
            assert len(intersection) == 0, f"Overlap between groups: {intersection}"

    all_union = set().union(*groups)
    assert len(all_union) == 49
    assert all_union == set(ALL_NEWS_FEATURE_NAMES)


def test_model_hierarchy_feature_dimensions() -> None:
    """Verify feature matrix dimensions for all models in the hierarchy."""
    expected_dims = {
        "Model 0": 45,
        "Model 1": 63,
        "Model 2": 112,
        "M2-Ablation-Count": 69,
        "M2-Ablation-Sentiment": 73,
        "M2-Ablation-Importance": 67,
        "M2-Ablation-Event": 81,
        "M2-Ablation-Novelty": 66,
        "M2-Ablation-Company": 71,
        "Model 3": 115,
    }
    for m_name, exp_len in expected_dims.items():
        assert len(MODEL_FEATURE_SPECS[m_name]) == exp_len, (
            f"{m_name} expected {exp_len} features, found {len(MODEL_FEATURE_SPECS[m_name])}"
        )


# ---------------------------------------------------------------------------
# 3. Multimodal Dataset Sample Count & Partition Tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("snap_type", [SnapshotType.SNAPSHOT_1540, SnapshotType.SNAPSHOT_0850])
def test_multimodal_dataset_sample_counts(snap_type: SnapshotType) -> None:
    """Verify 4-way join maintains exact sample counts without dropping rows."""
    ds = load_multimodal_dataset(snap_type)
    assert len(ds.dates) == 4453
    assert len(ds.target_dates) == 4453
    assert len(ds.y_class) == 4453
    assert len(ds.y_reg) == 4453

    # Dates range check
    assert ds.dates[0] == date(2008, 7, 8)
    assert ds.dates[-1] == date(2026, 9, 3)

    # Splitter check
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    folds = splitter.split_development(ds.dates)
    dev_idx, holdout_idx = splitter.get_development_and_holdout_indices(ds.dates)

    assert len(dev_idx) == 3299
    assert len(holdout_idx) == 1154
    assert len(folds) == 8

    total_val_indices = np.concatenate([f.val_indices for f in folds])
    assert len(total_val_indices) == 1960
    assert ds.dates[total_val_indices[0]] == date(2014, 1, 2)
    assert ds.dates[total_val_indices[-1]] == date(2021, 12, 31)

    assert ds.dates[holdout_idx[0]] == date(2022, 1, 3)
    assert ds.dates[holdout_idx[-1]] == date(2026, 9, 3)


@pytest.mark.parametrize("snap_type", [SnapshotType.SNAPSHOT_1540, SnapshotType.SNAPSHOT_0850])
def test_multimodal_matrices_no_nan_or_inf(snap_type: SnapshotType) -> None:
    """Verify that every feature matrix across all models contains zero NaN or Inf values."""
    ds = load_multimodal_dataset(snap_type)
    for m_name in MODEL_FEATURE_SPECS.keys():
        X, names = ds.get_features(m_name)
        assert not np.isnan(X).any(), f"NaN detected in {m_name} for {snap_type}"
        assert not np.isinf(X).any(), f"Inf detected in {m_name} for {snap_type}"
        assert X.shape[0] == 4453
        assert X.shape[1] == len(names)


# ---------------------------------------------------------------------------
# 4. Generated Output Artifacts Verification
# ---------------------------------------------------------------------------

def test_experiment_results_csv_structure() -> None:
    """Verify structure and contents of data/interim/news/phase9_step4_experiment_results.csv."""
    results_path = PROJECT_ROOT / "data" / "interim" / "news" / "phase9_step4_experiment_results.csv"
    assert results_path.is_file(), "phase9_step4_experiment_results.csv does not exist"

    df = pd.read_csv(results_path)
    # Exactly 40 rows: 2 snapshots * 2 partitions (OOF, Holdout) * 10 models
    assert len(df) == 40
    assert set(df["snapshot"].unique()) == {"Snapshot A", "Snapshot B"}
    assert set(df["partition"].unique()) == {"OOF", "Holdout"}
    assert len(df["model_id"].unique()) == 10

    # Ensure no NaNs in primary performance metrics
    required_cols = [
        "log_loss_calibrated",
        "brier_score_calibrated",
        "accuracy_calibrated",
        "rmse",
        "pearson_ic",
        "delta_logloss_vs_m1",
        "bootstrap_loss_reduction_ci_lower",
        "bootstrap_loss_reduction_ci_upper",
        "dm_pvalue_vs_m1",
        "delta_ic_vs_m1",
    ]
    for col in required_cols:
        assert col in df.columns, f"Missing required column: {col}"
        assert not df[col].isna().any(), f"NaN values found in column {col}"

    # Verify CI ordering
    assert (df["bootstrap_loss_reduction_ci_lower"] <= df["bootstrap_loss_reduction_ci_upper"]).all()
    assert (df["bootstrap_ic_diff_ci_lower"] <= df["bootstrap_ic_diff_ci_upper"]).all()


def test_session_level_results_csvs() -> None:
    """Verify session-level OOF and Holdout result CSVs."""
    oof_path = PROJECT_ROOT / "data" / "interim" / "news" / "phase9_step4_oof_results.csv"
    holdout_path = PROJECT_ROOT / "data" / "interim" / "news" / "phase9_step4_holdout_results.csv"

    assert oof_path.is_file(), "phase9_step4_oof_results.csv does not exist"
    assert holdout_path.is_file(), "phase9_step4_holdout_results.csv does not exist"

    df_oof = pd.read_csv(oof_path)
    df_holdout = pd.read_csv(holdout_path)

    # 1,960 sessions per snapshot for OOF -> 3,920 total rows
    assert len(df_oof) == 3920
    # 1,154 sessions per snapshot for Holdout -> 2,308 total rows
    assert len(df_holdout) == 2308

    # Check probabilities are in [0, 1]
    prob_cols_oof = [c for c in df_oof.columns if "prob" in c]
    assert len(prob_cols_oof) > 0
    assert (df_oof[prob_cols_oof].values >= 0.0).all()
    assert (df_oof[prob_cols_oof].values <= 1.0).all()


def test_experiment_config_json() -> None:
    """Verify configs/phase9_step4_experiment_config.json contains expected structure."""
    cfg_path = PROJECT_ROOT / "configs" / "phase9_step4_experiment_config.json"
    assert cfg_path.is_file(), "phase9_step4_experiment_config.json does not exist"

    with open(cfg_path) as f:
        cfg = json.load(f)

    assert cfg["sample_counts"]["total_supervised_sessions"] == 4453
    assert cfg["sample_counts"]["development_sessions"] == 3299
    assert cfg["sample_counts"]["oof_validation_sessions"] == 1960
    assert cfg["sample_counts"]["terminal_holdout_sessions"] == 1154

    assert cfg["hyperparameters"]["direction_classifier"]["n_estimators"] == 12
    assert cfg["hyperparameters"]["direction_classifier"]["learning_rate"] == 0.10
    assert cfg["hyperparameters"]["return_regressor"]["n_estimators"] == 43
    assert cfg["hyperparameters"]["return_regressor"]["learning_rate"] == 0.05
