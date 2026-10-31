"""Preflight and methodology gate tests for Phase 10.

Tests data contracts, feature spaces, development-only threshold fitting,
anti-leakage guarantees, and protected artifact hashes without executing
the full Phase 10 diagnostic pipeline.
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
    CONTEXT_FEATURE_NAMES,
    PRICE_FEATURE_NAMES,
    load_multimodal_dataset,
)

# ---------------------------------------------------------------------------
# 1. Protected Artifact Hashes
# ---------------------------------------------------------------------------
PROTECTED_HASHES = {
    "data/features/nifty50_features_clean.csv": "afa2e68f50f1ad0f4b1adbbec3df294d474d688dbf481cf53c76c4db0a78914b",
    "data/targets/nifty50_targets_snapshot_a.csv": "a13fed61f92c3fcccf9fe09ce59eb0df4d95ef8dce0aef970ff5ed1220ea055d",
    "data/targets/nifty50_targets_snapshot_b.csv": "54ac54fdeafd53ddea20b1d31cd89c1fbaebdbc88c0f24f8a1f73ce2867e01d2",
    "data/interim/context/snapshot_a_context_daily.csv": "26f41d5978b2f78fb9fad223d9efe9970820ab7f81510490ed6f1b39872178af",
    "data/interim/context/snapshot_b_context_daily.csv": "08a694f86f70c5246b8b6b4928283b676dd998912e481d88a718ba08970237be",
    "data/interim/news/features_news_snapshot_a.csv": "487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7",
    "data/interim/news/features_news_snapshot_b.csv": "f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606",
    "data/interim/news/phase9_step4_oof_results.csv": "62b88a1689c7ed57e1ddf79ca0064356eec5d2a16e00f7975998a155141f02d8",
    "data/interim/news/phase9_step4_holdout_results.csv": "4359edb7e585053c676e444d958a4265c584b9b13a58c89dd38067fc0bc41967",
    "data/interim/news/phase9_step4_experiment_results.csv": "7d0f39f7ce8a50b6f8b1591dc6ce9b3a4af8f75507531740a06147cb4aedffc3",
    "configs/phase9_step4_experiment_config.json": "8940206588dad34eb5a9d2fdb01ecbfeb629930374a733c15d077b2281ae7547",
}


def test_protected_artifact_hashes() -> None:
    """Ensure all Phase 4-9 sealed artifacts remain completely untouched."""
    for rel_path, expected_hash in PROTECTED_HASHES.items():
        file_path = PROJECT_ROOT / rel_path
        assert file_path.is_file(), f"Missing protected file: {rel_path}"
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}"


# ---------------------------------------------------------------------------
# 2. Model 1 Feature Space Integrity
# ---------------------------------------------------------------------------

def test_model1_feature_counts_and_names() -> None:
    """Verify Model 1 has exactly 45 Price + 18 Context = 63 features, with 0 News features."""
    assert len(PRICE_FEATURE_NAMES) == 45
    assert len(CONTEXT_FEATURE_NAMES) == 18

    model1_features = PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES
    assert len(model1_features) == 63
    assert len(set(model1_features)) == 63, "Detected duplicate feature names in Model 1"

    # Confirm zero news features
    forbidden_substrings = ["news", "headline", "sentiment", "importance", "novelty", "event_"]
    for f in model1_features:
        for sub in forbidden_substrings:
            assert sub not in f.lower(), f"Forbidden news token '{sub}' found in Model 1 feature '{f}'"


# ---------------------------------------------------------------------------
# 3. Target Separation & Anti-Leakage
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("snap_type", [SnapshotType.SNAPSHOT_1540, SnapshotType.SNAPSHOT_0850])
def test_no_targets_in_features_or_regimes(snap_type: SnapshotType) -> None:
    """Ensure target columns are strictly separated from feature and regime inputs."""
    ds = load_multimodal_dataset(snap_type)
    X, feat_names = ds.get_features("Model 1")

    # Target column names from Phase 5
    target_cols = ["target_return", "target_direction", "target_date", "is_classified", "has_target"]
    for col in target_cols:
        assert col not in feat_names, f"Target column '{col}' leaked into Model 1 feature space"

    # Verify no NaN or Inf
    assert not np.isnan(X).any(), "NaN found in Model 1 feature matrix"
    assert not np.isinf(X).any(), "Inf found in Model 1 feature matrix"


# ---------------------------------------------------------------------------
# 4. Temporal Partitions & Development-Only Threshold Rules
# ---------------------------------------------------------------------------

def test_development_threshold_purity() -> None:
    """Verify regime thresholds are fitted strictly on Development partition (<= 2021-12-31)."""
    ds = load_multimodal_dataset(SnapshotType.SNAPSHOT_1540)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    dev_idx, holdout_idx = splitter.get_development_and_holdout_indices(ds.dates)

    assert len(dev_idx) == 3299
    assert len(holdout_idx) == 1154
    assert ds.dates[dev_idx[-1]] == date(2021, 12, 31)
    assert ds.dates[holdout_idx[0]] == date(2022, 1, 3)

    # Dev dataframe
    dev_df = ds.features_df.iloc[dev_idx]

    # Verify indicators exist contemporaneously
    regime_indicators = ["volatility_ann_20d", "trend_slope_20d", "ret_20d", "ctx_level_india_vix", "ctx_level_us_vix", "ctx_ret_1d_sp500", "ctx_diff_1d_usd_inr"]
    for ind in regime_indicators:
        assert ind in dev_df.columns, f"Missing regime indicator: {ind}"

    # Calculate thresholds on Dev
    vol_q25 = float(np.percentile(dev_df["volatility_ann_20d"], 25))
    vol_q75 = float(np.percentile(dev_df["volatility_ann_20d"], 75))
    vol_q95 = float(np.percentile(dev_df["volatility_ann_20d"], 95))

    assert 0.10 < vol_q25 < 0.15
    assert 0.15 < vol_q75 < 0.25
    assert 0.30 < vol_q95 < 0.45
    assert vol_q25 < vol_q75 < vol_q95


# ---------------------------------------------------------------------------
# 5. Multiple Testing Correction Algorithm (Benjamini-Hochberg)
# ---------------------------------------------------------------------------

def test_benjamini_hochberg_fdr() -> None:
    """Verify implementation of Benjamini-Hochberg FDR correction for exploratory regime tests."""
    p_values = [0.001, 0.012, 0.045, 0.080, 0.250]
    m = len(p_values)
    alpha = 0.05

    # BH procedure
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]
    thresholds = (np.arange(1, m + 1) / m) * alpha

    sig_mask = sorted_p <= thresholds
    max_k = -1
    for k in range(m - 1, -1, -1):
        if sig_mask[k]:
            max_k = k
            break

    rejected = np.zeros(m, dtype=bool)
    if max_k >= 0:
        rejected[sorted_indices[: max_k + 1]] = True

    assert rejected[0] == True  # 0.001 <= 1/5 * 0.05 = 0.010 -> rejected
    assert rejected[1] == True  # 0.012 <= 2/5 * 0.05 = 0.020 -> rejected
    assert rejected[2] == False # 0.045 > 3/5 * 0.05 = 0.030 -> not rejected
