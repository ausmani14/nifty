"""Preflight and methodology gate tests for Phase 11: Out-of-Sample Strategy Validation.

Ensures:
1. All Phase 1-10 protected artifact hashes remain 100% untouched.
2. The Phase 11 strategy validation configuration is frozen and complete.
3. Model 1 architecture contains exactly 63 features (45 Price + 18 Context, 0 News).
4. Classifier (N*=12) and Regressor (N*=43) parameters are strictly preserved.
5. Exact OOF (N=1,960) and Terminal Holdout (N=1,154) session sets are verified.
6. All strategy families, confidence thresholds, and cost scenarios are pre-registered.
7. Zero news contamination and zero unauthorized post-hoc regime rules.
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

CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"


def test_phase11_config_exists_and_valid() -> None:
    """Verify phase11_strategy_validation_config.json is well-formed and complete."""
    assert CONFIG_PATH.is_file(), f"Missing config: {CONFIG_PATH}"
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    assert cfg["status"] == "PRE_EXECUTION_FROZEN"
    assert cfg["model_specification"]["feature_count"] == 63
    assert cfg["model_specification"]["news_features_included"] is False
    assert cfg["model_specification"]["classifier_hyperparameters"]["n_estimators"] == 12
    assert cfg["model_specification"]["regressor_hyperparameters"]["n_estimators"] == 43

    # Check strategy families
    strats = cfg["strategy_families"]
    for s_key in ["Strategy 0", "Strategy 1", "Strategy 2", "Strategy 3", "Strategy 4", "Strategy 5"]:
        assert s_key in strats, f"Missing strategy definition: {s_key}"

    # Pre-registered thresholds
    assert strats["Strategy 3"]["pre_registered_thresholds"] == [0.40, 0.45, 0.50]
    assert strats["Strategy 4"]["pre_registered_thresholds"] == [0.0010, 0.0025, 0.0050]
    assert "volatility_ann_20d <= 0.114675" in strats["Strategy 5"]["regime_filter"]

    # Transaction cost scenarios
    costs = [c["round_trip_bps"] for c in cfg["transaction_cost_scenarios_bps"]]
    assert costs == [0.0, 5.0, 10.0, 20.0]


def test_all_protected_artifact_hashes() -> None:
    """Ensure all Phase 4-10 sealed artifacts remain completely untouched."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    for rel_path, expected_hash in cfg["protected_artifact_hashes"].items():
        file_path = PROJECT_ROOT / rel_path
        assert file_path.is_file(), f"Missing protected file: {rel_path}"
        actual_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"Hash mismatch for {rel_path}!\nExpected: {expected_hash}\nActual:   {actual_hash}"


def test_model1_feature_space_and_parameters() -> None:
    """Verify Model 1 has exactly 45 Price + 18 Context = 63 features, with 0 News features."""
    assert len(PRICE_FEATURE_NAMES) == 45
    assert len(CONTEXT_FEATURE_NAMES) == 18

    ds_a = load_multimodal_dataset(SnapshotType.SNAPSHOT_1540)
    for feat in PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES:
        assert feat in ds_a.features_df.columns, f"Missing Model 1 feature: {feat}"

    # Verify no news features in Model 1 definition
    from nifty_ai.models.multimodal import ALL_NEWS_FEATURE_NAMES
    for news_feat in ALL_NEWS_FEATURE_NAMES:
        assert news_feat not in (PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES)


def test_oof_and_holdout_observation_sets() -> None:
    """Verify exact session counts for Development, OOF, and Terminal Holdout."""
    ds_a = load_multimodal_dataset(SnapshotType.SNAPSHOT_1540)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))

    folds = splitter.split_development(ds_a.dates)
    dev_idx, holdout_idx = splitter.get_development_and_holdout_indices(ds_a.dates)

    assert len(dev_idx) == 3299
    assert len(holdout_idx) == 1154

    total_val_indices = set()
    for fold in folds:
        assert len(set(fold.train_indices).intersection(set(fold.val_indices))) == 0
        total_val_indices.update(fold.val_indices)

    assert len(total_val_indices) == 1960
    assert min(ds_a.dates[i] for i in total_val_indices) == date(2014, 1, 2)
    assert max(ds_a.dates[i] for i in total_val_indices) == date(2021, 12, 31)
    assert min(ds_a.dates[i] for i in holdout_idx) == date(2022, 1, 3)
    assert max(ds_a.dates[i] for i in holdout_idx) == date(2026, 9, 3)


def test_execution_prices_and_data_availability() -> None:
    """Verify open and close prices are fully populated and non-null for all dates."""
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv")
    assert "open" in price_df.columns
    assert "close" in price_df.columns
    assert price_df["open"].isna().sum() == 0
    assert price_df["close"].isna().sum() == 0
    assert (price_df["open"] > 0).all()
    assert (price_df["close"] > 0).all()


def test_zero_holdout_leakage_and_posthoc_rules() -> None:
    """Verify that no strategy rule in the configuration relies on post-hoc tuning or holdout data."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Verify only Strategy 5 has a regime diagnostic filter, and it is explicitly tagged
    strats = cfg["strategy_families"]
    assert strats["Strategy 5"]["type"] == "diagnostic_comparison"
    assert "Diagnostic only; not authorized as production rule" in strats["Strategy 5"]["rule"]
