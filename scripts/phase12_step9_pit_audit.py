"""Phase 12 Step 9: Point-in-Time Availability, Timestamp Alignment & Context-Feature Robustness Audit.

Research Objective:
Determine whether the weak Snapshot B intraday predictive relationship identified in
Phases 6-8 survives a rigorous audit of point-in-time availability, timestamp alignment,
market-session timing, close-definition differences, timezone conversion, and overnight
information availability.

Pre-registered Models:
- Model P0: 45 Price features only (0 Context features)
- Model P1: 45 Price + PIT-A Context (18 features, reproducing Step 8 G0_ALL reference, 63 total)
- Model P2: 45 Price + PIT-B Context (11 LOW RISK features, conservative timing, 56 total)
- Model P3: 45 Price + PIT-C Context (8 LOW RISK cash equities/VIX indices, strict timing, 53 total)

Strict Governance:
- Zero terminal holdout access (2022-01-03 to 2026-09-03, N=1,154 is quarantined).
- Identical OOF evaluation population: 2014-01-02 to 2021-12-31, exactly N=1,960 sessions across 8 folds.
- ZERO News, ZERO Volume, ZERO Flow proxies.
- Expanding window W0 baseline for all configurations.
- Deterministic, chronological training-only inner validation (last 20%) for tree-count N* selection.
- Fold-local training baselines (mu_train) computed strictly from training observations.
- Placebo permutation test (seed=42, 1,000 permutations).
- Economic diagnostic at 0, 5, 10, 20 bps.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import xgboost as xgb

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.evaluation.split import WalkForwardSplitter
from nifty_ai.models.multimodal import load_multimodal_dataset

# Directories
OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step9"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
STEP7_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step7"
STEP8_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step8"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"

PROTECTED_STEP5_HASHES = {
    "phase12_step5_target_comparison.csv": "6ec7040f75d26c5b0f54ce33cded5e6baacaebdadea2b99968fcd2f2880de0d0",
    "phase12_step5_fold_results.csv": "041c75bce9cceb847850ffdc17069494e0c44795b4a78c853e9028859c6e1399",
    "phase12_step5_temporal_results.csv": "f14a859412b7e0ac841c9235f66849adb5ff521b675df698f26ee371d412e788",
    "phase12_step5_sign_base_rate.csv": "2344bcffabd0ea2129c70b4d140e9446836fc042f744089bd196c4d38922dd4d",
    "phase12_step5_magnitude_calibration.csv": "501fc01546929c97a847927f1e227e0e6a74c5e56dcf2abe067db5668f1154ae",
    "phase12_step5_economic_stress.csv": "e1c8f04d74c9ece80999e9dcd425a674b4e91da1bcbb4afb7cf6fe5465bffae6",
    "phase12_step5_placebo.csv": "084416736d8d13555576ee5858876ae59260b88bc452c847896e6aab49a424db",
    "phase12_step5_manifest.json": "acf3d7ce73919ddc8545e0c3a506abd44ef0b5aa8e29fb20865e6a85621db10b",
    "phase12_step5_corrected_sign_base_rate.csv": "ac42f0fe9f16f47da077b9a1e5d55d9b385646f54236bfe1b4e1c96c5d46276a",
    "phase12_step5_corrected_economic_stress.csv": "f1447629a6d6c142d960be0fc5b0c4f52484d02825954109118d9e4125d57f88",
}

PROTECTED_STEP6_HASHES = {
    "phase12_step6_economic_diagnostic.csv": "19341254f4448d6a0628313c909d6b4ab82843f64363853a584961d8160041ce",
    "phase12_step6_fold_results.csv": "317e9fb735347351be6e4bb44b807b6f419aaa0021badf20f19b2e2cc8b36c11",
    "phase12_step6_magnitude.csv": "f2f82819aad307aa5816dce101da847e52964ea880ddb6c9ea85293357467181",
    "phase12_step6_manifest.json": "cd39329b02772d81c5594bb1d3342795c8384f692952f4b293b8599c10bc6453",
    "phase12_step6_placebo.csv": "a6e30a69c9a2229ddcb5855360cb2a54d214672b6ea4c201688afee388dbf9d1",
    "phase12_step6_residual_predictions.csv": "41dae563cbb48f2ab84cf1b8f18edf190abbecdf82d5b7104e797a63755604af",
    "phase12_step6_temporal_results.csv": "85e901e45e6327640131011460146b0221956d0a2f8ae15e8c6be1aceea6dfe8",
}

PROTECTED_STEP7_HASHES = {
    "step7_economic_diagnostic.csv": "2801997a874ee0eb1778a273430f47c5472343b8419b4ebed7f0cd993ad10c90",
    "step7_fold_results.csv": "230e90c3b7415e9d19d7c01714c72d6a779f6b40050ad4e547648eddbe3575f7",
    "step7_integrity_manifest.json": "d772c3714a2f79f1eb0520bf2ea0576eb4467d2cd2b8fdde9860e585b2866635",
    "step7_placebo_results.csv": "977397dd78737150e5bbac8a9f1b1e8e1545604697cb978bcc2db06606b01667",
    "step7_predictions.csv": "3a2ec99ed398f4cb1047326df2cee879a355712c98aa306f8e87d0680291013e",
    "step7_summary.csv": "de3b4c8adde8c2861c452e08ca0a5da5b901596bf0ad62de320770a11800ac6f",
    "step7_temporal_results.csv": "5953cdbd1bfa67d85c4a58e129fda337dcdea3ab0da330bc79647d524d441ed9",
    "step7_tree_counts.csv": "de78be51942b03d27af3a681c65c204aef090f8f948169d3fcfcd3f3be06f2ad",
}

PROTECTED_STEP8_HASHES = {
    "step8_economic_diagnostic.csv": "13aead08232aae96af2e57c5c4d7dd6651ecc29d3291a1bce600ca6a3bc64bee",
    "step8_feature_contribution.csv": "4d73edd23dd8218813addc13bbb77cd42c533b41564f8357dea6158ab39ffad5",
    "step8_feature_group_registry.csv": "7fd8479a21f61f3d852405dc679e261cd4b1e0c4d741bd42712e06020c78eec0",
    "step8_fold_results.csv": "dd283306bac4dc3c017cfadf34c3acd71ff355ec6c3807215a1292769578eb38",
    "step8_placebo_results.csv": "94b6951406065d5a8ee745fa5aef76dd2f0342c8122958aa31bc4353eb944d26",
    "step8_predictions.csv": "d5a3c1c8122531a0d0104421cf87a9c957a40a01ff1826936fc4cf52989e3f6a",
    "step8_summary.csv": "6c7043f0c4c909e62bfa0f084e8b270147b79f5adf5e75deec80f6f43b533576",
    "step8_temporal_results.csv": "abc427ca94d66c2ca2053fa69450baf177e4fbfddae1a0c99bfcff983bac25b0",
    "step8_feature_group_registry.json": "695718620348e4fc6e9cc72829a409f03604e42ce86f60aac3f5e5a51a90cefc",
}


def verify_protected_checksums() -> None:
    """Ensure all protected Phase 4-10, Step 5, Step 6, Step 7, and Step 8 artifacts remain unmodified."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        if not fp.is_file():
            raise FileNotFoundError(f"Missing protected file: {rel_path}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for {rel_path}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    for fn, exp_hash in PROTECTED_STEP5_HASHES.items():
        fp = PHASE12_DIR / fn
        if not fp.is_file():
            raise FileNotFoundError(f"Missing Step 5 file: {fn}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for Step 5 file {fn}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    for fn, exp_hash in PROTECTED_STEP6_HASHES.items():
        fp = PHASE12_DIR / fn
        if not fp.is_file():
            raise FileNotFoundError(f"Missing Step 6 file: {fn}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for Step 6 file {fn}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    for fn, exp_hash in PROTECTED_STEP7_HASHES.items():
        fp = STEP7_DIR / fn
        if not fp.is_file():
            raise FileNotFoundError(f"Missing Step 7 file: {fn}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for Step 7 file {fn}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    for fn, exp_hash in PROTECTED_STEP8_HASHES.items():
        fp = STEP8_DIR / fn
        if not fp.is_file():
            raise FileNotFoundError(f"Missing Step 8 file: {fn}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for Step 8 file {fn}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    print("[CHECKSUMS] All 53 protected Phase 4-10, Step 5, Step 6, Step 7, and Step 8 artifacts verified.")


def safe_correlation(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float, float]:
    """Compute Pearson and Spearman correlation safely, returning (0.0, 1.0, 0.0, 1.0) for constant arrays."""
    if len(np.unique(x)) <= 1 or np.std(x) < 1e-8:
        return 0.0, 1.0, 0.0, 1.0
    if len(np.unique(y)) <= 1 or np.std(y) < 1e-8:
        return 0.0, 1.0, 0.0, 1.0
    r_p, p_p = stats.pearsonr(x, y)
    r_s, p_s = stats.spearmanr(x, y)
    return float(r_p), float(p_p), float(r_s), float(p_s)


def compute_newey_west_hac(returns: np.ndarray, max_lags: int | None = None) -> Tuple[float, float, float]:
    """Compute Newey-West HAC standard error, t-stat, and p-value."""
    n = len(returns)
    if n < 2 or np.all(returns == 0.0):
        return 0.0, 0.0, 1.0
    mean_val = float(np.mean(returns))
    e = returns - mean_val
    if np.sum(np.abs(e)) < 1e-14:
        return 0.0, 0.0, 1.0

    if max_lags is None:
        max_lags = int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0))))
        max_lags = max(1, min(max_lags, 20))

    gamma_0 = float(np.dot(e, e) / n)
    hac_var = gamma_0
    for lag in range(1, max_lags + 1):
        weight = 1.0 - (lag / (max_lags + 1.0))
        gamma_l = float(np.dot(e[lag:], e[:-lag]) / n)
        hac_var += 2.0 * weight * gamma_l

    hac_se = math.sqrt(max(1e-16, hac_var / n))
    t_stat = mean_val / hac_se if hac_se > 0 else 0.0
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))
    return hac_se, t_stat, p_val


def compute_drawdowns(returns: np.ndarray) -> Tuple[float, np.ndarray]:
    """Compute maximum drawdown and drawdown series."""
    equity = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(equity)
    dd = (equity - peak) / peak
    max_dd = float(np.min(dd)) if len(dd) > 0 else 0.0
    return max_dd, dd


def select_optimal_tree_count(
    X_train: np.ndarray,
    y_train: np.ndarray,
    params: Dict[str, Any],
    candidate_trees: List[int],
    val_ratio: float = 0.20,
) -> Tuple[int, float]:
    """Chronological inner validation on training fold to select optimal tree count N*."""
    n_total = len(X_train)
    n_inner_val = int(n_total * val_ratio)
    n_inner_train = n_total - n_inner_val

    X_in_tr = X_train[:n_inner_train]
    y_in_tr = y_train[:n_inner_train]
    X_in_val = X_train[n_inner_train:]
    y_in_val = y_train[n_inner_train:]

    best_rmse = float("inf")
    best_trees = candidate_trees[0]

    for n_trees in candidate_trees:
        model = xgb.XGBRegressor(**params, n_estimators=n_trees)
        model.fit(X_in_tr, y_in_tr)
        preds = model.predict(X_in_val)
        rmse = math.sqrt(float(np.mean((y_in_val - preds) ** 2)))
        if rmse < best_rmse:
            best_rmse = rmse
            best_trees = n_trees

    return best_trees, best_rmse


# Context Feature Definitions and Detailed PIT Matrix Specifications
CONTEXT_SPECS_AUDIT = [
    {
        "feature_name": "ctx_ret_1d_nifty_bank",
        "feature_family": "domestic_equity",
        "source_instrument": "^NSEBANK",
        "source_timezone": "Asia/Kolkata",
        "source_session": "Day T Domestic Cash Regular Session (09:15-15:30 IST)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "15:30 IST",
        "estimated_available_time_utc": "10:00 UTC (Day T)",
        "estimated_available_time_ist": "15:30 IST (Day T)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "NSE India Exchange Trading Calendar; finalized 17.3h prior to 08:50 IST",
        "notes": "NSE Bank Nifty sector index. Finalizes at 15:30 IST yesterday; fully published and immutable overnight.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": True,
    },
    {
        "feature_name": "ctx_diff_1d_india_vix",
        "feature_family": "domestic_volatility",
        "source_instrument": "^INDIAVIX",
        "source_timezone": "Asia/Kolkata",
        "source_session": "Day T Domestic Derivatives Session (09:15-15:30 IST)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "15:30 IST",
        "estimated_available_time_utc": "10:00 UTC (Day T)",
        "estimated_available_time_ist": "15:30 IST (Day T)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "NSE India Implied Volatility Index; finalized 17.3h prior to 08:50 IST",
        "notes": "NSE India VIX implied volatility index. Finalizes at 15:30 IST yesterday; fully published and immutable overnight.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": True,
    },
    {
        "feature_name": "ctx_level_india_vix",
        "feature_family": "domestic_volatility",
        "source_instrument": "^INDIAVIX",
        "source_timezone": "Asia/Kolkata",
        "source_session": "Day T Domestic Derivatives Session (09:15-15:30 IST)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "15:30 IST",
        "estimated_available_time_utc": "10:00 UTC (Day T)",
        "estimated_available_time_ist": "15:30 IST (Day T)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "NSE India Implied Volatility Index; finalized 17.3h prior to 08:50 IST",
        "notes": "Level of NSE India VIX. Finalizes at 15:30 IST yesterday; fully published and immutable overnight.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": True,
    },
    {
        "feature_name": "ctx_diff_1d_india_10y_yield",
        "feature_family": "domestic_rates",
        "source_instrument": "IN10Y=RR",
        "source_timezone": "Asia/Kolkata",
        "source_session": "Day T Domestic Bond Market (CCIL/NDS-OM 09:00-17:00 IST)",
        "timestamp_semantics": "indicative_quote",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "16:30 IST",
        "estimated_available_time_utc": "11:00 UTC (Day T)",
        "estimated_available_time_ist": "16:30 IST (Day T)",
        "available_by_0850": True,
        "availability_confidence": "MEDIUM",
        "timing_risk": "MEDIUM RISK",
        "revision_risk": "LOW",
        "stale_value_possible": True,
        "treatment": "CONDITIONAL",
        "evidence_source": "Reuters Indicative Benchmark Bond Quote (IN10Y=RR); OTC composite yield",
        "notes": "Reuters indicative yield quote. Not exchange-cleared CCIL settlement fixing; OTC composite quote.",
        "in_pit_a": True,
        "in_pit_b": False,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_diff_1d_usd_inr",
        "feature_family": "domestic_fx",
        "source_instrument": "USDINR=X",
        "source_timezone": "Asia/Kolkata",
        "source_session": "Day T Domestic Interbank Spot Market (~09:00-15:30 IST)",
        "timestamp_semantics": "indicative_quote",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "15:30 IST",
        "estimated_available_time_utc": "10:00 UTC (Day T)",
        "estimated_available_time_ist": "15:30 IST (Day T)",
        "available_by_0850": True,
        "availability_confidence": "MEDIUM",
        "timing_risk": "MEDIUM RISK",
        "revision_risk": "LOW",
        "stale_value_possible": True,
        "treatment": "CONDITIONAL",
        "evidence_source": "Yahoo OTC Spot FX Aggregation (USDINR=X); differs from RBI/FBIL fixing (~13:30)",
        "notes": "OTC interbank aggregation. Differs from official RBI/FBIL benchmark reference rate.",
        "in_pit_a": True,
        "in_pit_b": False,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_ret_1d_sp500",
        "feature_family": "global_equity",
        "source_instrument": "^GSPC",
        "source_timezone": "America/New_York",
        "source_session": "Day T US Cash Regular Session (09:30-16:00 EST/EDT)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "16:00 EST/EDT",
        "estimated_available_time_utc": "20:00 UTC (EDT) / 21:00 UTC (EST)",
        "estimated_available_time_ist": "01:30 IST (EDT) / 02:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "S&P Dow Jones Indices Official Close; finalized 5.8h-6.8h prior to 08:50 IST",
        "notes": "US premier equity index. Official cash close finalized at 16:00 EST; available in India by 02:00-03:00 IST.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": True,
    },
    {
        "feature_name": "ctx_ret_1d_nasdaq",
        "feature_family": "global_equity",
        "source_instrument": "^IXIC",
        "source_timezone": "America/New_York",
        "source_session": "Day T US Cash Regular Session (09:30-16:00 EST/EDT)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "16:00 EST/EDT",
        "estimated_available_time_utc": "20:00 UTC (EDT) / 21:00 UTC (EST)",
        "estimated_available_time_ist": "01:30 IST (EDT) / 02:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "Nasdaq Stock Market Official Close; finalized 5.8h-6.8h prior to 08:50 IST",
        "notes": "Nasdaq Composite Index. Official cash close finalized at 16:00 EST; available in India by 02:00-03:00 IST.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": True,
    },
    {
        "feature_name": "ctx_ret_1d_dow_jones",
        "feature_family": "global_equity",
        "source_instrument": "^DJI",
        "source_timezone": "America/New_York",
        "source_session": "Day T US Cash Regular Session (09:30-16:00 EST/EDT)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "16:00 EST/EDT",
        "estimated_available_time_utc": "20:00 UTC (EDT) / 21:00 UTC (EST)",
        "estimated_available_time_ist": "01:30 IST (EDT) / 02:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "S&P Dow Jones Indices Official Close; finalized 5.8h-6.8h prior to 08:50 IST",
        "notes": "Dow Jones Industrial Average. Official cash close finalized at 16:00 EST; available in India by 02:00-03:00 IST.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": True,
    },
    {
        "feature_name": "ctx_diff_1d_us_vix",
        "feature_family": "global_volatility",
        "source_instrument": "^VIX",
        "source_timezone": "America/New_York",
        "source_session": "Day T US SPX Options Session (09:30-16:15 EST/EDT)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "16:15 EST/EDT",
        "estimated_available_time_utc": "20:00 UTC (EDT) / 21:00 UTC (EST)",
        "estimated_available_time_ist": "01:30 IST (EDT) / 02:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "CBOE Official Volatility Index Settlement; finalized 5.8h-6.8h prior to 08:50 IST",
        "notes": "CBOE Volatility Index. Options trading closes 16:15 EST; available in India by 02:00-03:00 IST.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": True,
    },
    {
        "feature_name": "ctx_level_us_vix",
        "feature_family": "global_volatility",
        "source_instrument": "^VIX",
        "source_timezone": "America/New_York",
        "source_session": "Day T US SPX Options Session (09:30-16:15 EST/EDT)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "16:15 EST/EDT",
        "estimated_available_time_utc": "20:00 UTC (EDT) / 21:00 UTC (EST)",
        "estimated_available_time_ist": "01:30 IST (EDT) / 02:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "CBOE Official Volatility Index Settlement; finalized 5.8h-6.8h prior to 08:50 IST",
        "notes": "Level of CBOE Volatility Index. Options trading closes 16:15 EST; available in India by 02:00-03:00 IST.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": True,
    },
    {
        "feature_name": "ctx_ret_1d_nikkei_225",
        "feature_family": "global_equity",
        "source_instrument": "^N225",
        "source_timezone": "Asia/Tokyo",
        "source_session": "Day T Asian Afternoon Session (12:30-15:00 JST = 09:00-11:30 IST)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "15:00 JST",
        "estimated_available_time_utc": "06:00 UTC (Day T)",
        "estimated_available_time_ist": "11:30 IST (Day T)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "Tokyo Stock Exchange Official Index Close; finalized 21.0h prior to 08:50 IST",
        "notes": "TSE Nikkei 225 official close. Finalizes 11:30 IST yesterday; fully finalized prior to 08:50 IST next day.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_ret_1d_hang_seng",
        "feature_family": "global_equity",
        "source_instrument": "^HSI",
        "source_timezone": "Asia/Hong_Kong",
        "source_session": "Day T Asian Afternoon Session (13:00-16:00 HKT = 10:30-13:30 IST)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "16:00 HKT",
        "estimated_available_time_utc": "08:00 UTC (Day T)",
        "estimated_available_time_ist": "13:30 IST (Day T)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "Hong Kong Exchanges and Clearing Official Close; finalized 19.0h prior to 08:50 IST",
        "notes": "HKEX Hang Seng Index official close. Finalizes 13:30 IST yesterday; fully finalized prior to 08:50 IST next day.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_ret_1d_ftse_100",
        "feature_family": "global_equity",
        "source_instrument": "^FTSE",
        "source_timezone": "Europe/London",
        "source_session": "Day T European Regular Session (08:00-16:30 GMT/BST)",
        "timestamp_semantics": "official_index_close",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "16:30 GMT/BST",
        "estimated_available_time_utc": "15:30 UTC (BST) / 16:30 UTC (GMT)",
        "estimated_available_time_ist": "21:00 IST (BST) / 22:00 IST (GMT) (Day T)",
        "available_by_0850": True,
        "availability_confidence": "HIGH",
        "timing_risk": "LOW RISK",
        "revision_risk": "NONE",
        "stale_value_possible": False,
        "treatment": "VALID",
        "evidence_source": "London Stock Exchange Official Index Close; finalized 11.5h prior to 08:50 IST",
        "notes": "LSE FTSE 100 official close. Finalizes ~21:00-22:00 IST yesterday; fully finalized prior to 08:50 IST next day.",
        "in_pit_a": True,
        "in_pit_b": True,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_ret_1d_brent_crude",
        "feature_family": "global_commodities",
        "source_instrument": "BZ=F",
        "source_timezone": "America/New_York",
        "source_session": "Day T ICE Futures Electronic Trading Session (closes 17:00 EST)",
        "timestamp_semantics": "daily_bar_endpoint",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "17:00 EST",
        "estimated_available_time_utc": "21:00 UTC (EDT) / 22:00 UTC (EST)",
        "estimated_available_time_ist": "02:30 IST (EDT) / 03:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "MEDIUM",
        "timing_risk": "MEDIUM RISK",
        "revision_risk": "LOW",
        "stale_value_possible": True,
        "treatment": "CONDITIONAL",
        "evidence_source": "ICE Brent Crude Continuous Contract (BZ=F); Yahoo daily bar close differs from settlement (~14:30 EST)",
        "notes": "Continuous front-month contract. Electronic bar close at 17:00 EST differs from official settlement at 14:30 EST; roll methodology unspecified.",
        "in_pit_a": True,
        "in_pit_b": False,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_ret_1d_wti_crude",
        "feature_family": "global_commodities",
        "source_instrument": "CL=F",
        "source_timezone": "America/New_York",
        "source_session": "Day T NYMEX Futures Electronic Trading Session (closes 17:00 EST)",
        "timestamp_semantics": "daily_bar_endpoint",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "17:00 EST",
        "estimated_available_time_utc": "21:00 UTC (EDT) / 22:00 UTC (EST)",
        "estimated_available_time_ist": "02:30 IST (EDT) / 03:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "MEDIUM",
        "timing_risk": "MEDIUM RISK",
        "revision_risk": "LOW",
        "stale_value_possible": True,
        "treatment": "CONDITIONAL",
        "evidence_source": "NYMEX WTI Crude Continuous Contract (CL=F); Yahoo daily bar close differs from settlement (14:30 EST)",
        "notes": "Continuous front-month contract. Electronic bar close at 17:00 EST differs from official settlement at 14:30 EST; roll methodology unspecified.",
        "in_pit_a": True,
        "in_pit_b": False,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_ret_1d_gold",
        "feature_family": "global_commodities",
        "source_instrument": "GC=F",
        "source_timezone": "America/New_York",
        "source_session": "Day T COMEX Futures Electronic Trading Session (closes 17:00 EST)",
        "timestamp_semantics": "daily_bar_endpoint",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "17:00 EST",
        "estimated_available_time_utc": "21:00 UTC (EDT) / 22:00 UTC (EST)",
        "estimated_available_time_ist": "02:30 IST (EDT) / 03:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "MEDIUM",
        "timing_risk": "MEDIUM RISK",
        "revision_risk": "LOW",
        "stale_value_possible": True,
        "treatment": "CONDITIONAL",
        "evidence_source": "COMEX Gold Continuous Contract (GC=F); Yahoo daily bar close differs from settlement (13:30 EST)",
        "notes": "Continuous front-month contract. Electronic bar close at 17:00 EST differs from official settlement at 13:30 EST; roll methodology unspecified.",
        "in_pit_a": True,
        "in_pit_b": False,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_ret_1d_dxy",
        "feature_family": "global_fx",
        "source_instrument": "DX-Y.NYB",
        "source_timezone": "America/New_York",
        "source_session": "Day T ICE Futures US Electronic Session (closes 17:00 EST)",
        "timestamp_semantics": "daily_bar_endpoint",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "17:00 EST",
        "estimated_available_time_utc": "21:00 UTC (EDT) / 22:00 UTC (EST)",
        "estimated_available_time_ist": "02:30 IST (EDT) / 03:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "MEDIUM",
        "timing_risk": "MEDIUM RISK",
        "revision_risk": "LOW",
        "stale_value_possible": True,
        "treatment": "CONDITIONAL",
        "evidence_source": "ICE US Dollar Index Futures Continuous Contract (DX-Y.NYB)",
        "notes": "ICE Dollar Index continuous futures contract. Bar close at 17:00 EST; roll methodology unspecified.",
        "in_pit_a": True,
        "in_pit_b": False,
        "in_pit_c": False,
    },
    {
        "feature_name": "ctx_diff_1d_us_10y_yield",
        "feature_family": "global_rates",
        "source_instrument": "^TNX",
        "source_timezone": "America/New_York",
        "source_session": "Day T CBOE Index Session (aligned to ~15:00 EST)",
        "timestamp_semantics": "cboe_yield_index",
        "nominal_bar_date": "Day T",
        "nominal_bar_end_time": "15:00 EST",
        "estimated_available_time_utc": "19:00 UTC (EDT) / 20:00 UTC (EST)",
        "estimated_available_time_ist": "00:30 IST (EDT) / 01:30 IST (EST) (Day T+1)",
        "available_by_0850": True,
        "availability_confidence": "MEDIUM",
        "timing_risk": "MEDIUM RISK",
        "revision_risk": "LOW",
        "stale_value_possible": True,
        "treatment": "CONDITIONAL",
        "evidence_source": "CBOE 10-Year Treasury Yield Index (^TNX); derived from CME futures, not cash Treasury",
        "notes": "CBOE computed yield index (yield x 10). Derived from CME T-Note futures, not direct cash Treasury bond.",
        "in_pit_a": True,
        "in_pit_b": False,
        "in_pit_c": False,
    },
]


def main() -> None:
    print("=" * 90)
    print("PHASE 12 STEP 9: POINT-IN-TIME AVAILABILITY & CONTEXT-FEATURE ROBUSTNESS AUDIT")
    print("=" * 90)

    # 1. Checksums
    print("\n--- Step 1: Checksum Verification ---")
    verify_protected_checksums()

    # 2. Build and Save step9_pit_availability_matrix.csv and .json
    print("\n--- Step 2: Creating Point-in-Time Availability Matrix (18 Features) ---")
    matrix_cols = [
        "feature_name", "feature_family", "source_instrument", "source_timezone",
        "source_session", "timestamp_semantics", "nominal_bar_date", "nominal_bar_end_time",
        "estimated_available_time_utc", "estimated_available_time_ist", "available_by_0850",
        "availability_confidence", "timing_risk", "revision_risk", "stale_value_possible",
        "treatment", "evidence_source", "notes"
    ]
    df_matrix = pd.DataFrame(CONTEXT_SPECS_AUDIT)[matrix_cols]
    matrix_csv_path = OUT_DIR / "step9_pit_availability_matrix.csv"
    df_matrix.to_csv(matrix_csv_path, index=False)
    print(f"Saved {matrix_csv_path} ({len(df_matrix)} features).")

    matrix_json_path = OUT_DIR / "step9_pit_availability_matrix.json"
    with open(matrix_json_path, "w", encoding="utf-8") as f:
        json.dump(CONTEXT_SPECS_AUDIT, f, indent=2)
    print(f"Saved {matrix_json_path}.")

    # 3. Load Multimodal Dataset and Target
    print("\n--- Step 3: Loading Dataset & Target Returns ---")
    ds_b = load_multimodal_dataset(SnapshotType.SNAPSHOT_0850)
    splitter = WalkForwardSplitter(development_end_date=date(2021, 12, 31))
    dev_indices, holdout_indices = splitter.get_development_and_holdout_indices(ds_b.dates)
    folds = splitter.split_development(ds_b.dates)

    assert len(dev_indices) == 3299
    assert len(holdout_indices) == 1154
    assert len(folds) == 8

    # Extract price target (intraday open-to-close)
    price_df = pd.read_csv(PROJECT_ROOT / "data" / "processed" / "nifty_50_daily.csv").set_index("trading_date")
    dev_dates = [ds_b.dates[i] for i in dev_indices]
    dev_target_dates = [ds_b.target_dates[i] for i in dev_indices]

    intraday_returns_dev = []
    for d_ref, d_tgt in zip(dev_dates, dev_target_dates):
        p_tgt = price_df.loc[d_tgt.isoformat()]
        o1 = float(p_tgt["open"])
        c1 = float(p_tgt["close"])
        intraday_returns_dev.append((c1 - o1) / o1)

    y_dev = np.array(intraday_returns_dev, dtype=np.float64)

    # Extract all 63 features
    X_all, feat_names = ds_b.get_features("Model 1")
    assert len(feat_names) == 63
    X_dev = X_all[dev_indices]
    dev_date_arr = np.array(dev_dates)

    feat_to_idx = {fn: i for i, fn in enumerate(feat_names)}

    # Define P0, P1, P2, P3
    price_45_indices = list(range(45))
    pit_a_indices = list(range(63))

    low_risk_feat_names = [item["feature_name"] for item in CONTEXT_SPECS_AUDIT if item["timing_risk"] == "LOW RISK"]
    assert len(low_risk_feat_names) == 11
    pit_b_indices = sorted(price_45_indices + [feat_to_idx[fn] for fn in low_risk_feat_names])
    assert len(pit_b_indices) == 56

    strict_feat_names = [item["feature_name"] for item in CONTEXT_SPECS_AUDIT if item["in_pit_c"]]
    assert len(strict_feat_names) == 8
    pit_c_indices = sorted(price_45_indices + [feat_to_idx[fn] for fn in strict_feat_names])
    assert len(pit_c_indices) == 53

    models = [
        ("P0_PRICE_ONLY", "Model P0: Price Only (Baseline)", "Baseline", price_45_indices),
        ("P1_ORIGINAL_PIT", "Model P1: 45 Price + 18 PIT-A Context (Reference)", "Reference", pit_a_indices),
        ("P2_CONSERVATIVE_PIT", "Model P2: 45 Price + 11 PIT-B Context (Conservative)", "Diagnostic", pit_b_indices),
        ("P3_STRICT_PIT", "Model P3: 45 Price + 8 PIT-C Context (Strict)", "Diagnostic", pit_c_indices),
    ]

    for m_code, m_name, _, m_idx in models:
        print(f"Model {m_code:<22}: {len(m_idx):2d} features")

    # 4. Feature Timestamp Audit, Stale Audit, and Revision Audit Tables
    print("\n--- Step 4: Building Feature Audits (Timestamp, Stale Value, Revision) ---")
    ctx_daily_path = PROJECT_ROOT / "data" / "interim" / "context" / "snapshot_b_context_daily.csv"
    ctx_df = pd.read_csv(ctx_daily_path).set_index("trading_date")

    # OOF session context slice
    oof_indices = []
    for f in folds:
        oof_indices.extend(f.val_indices)
    assert len(oof_indices) == 1960
    oof_dates_iso = [ds_b.dates[i].isoformat() for i in oof_indices]
    ctx_oof = ctx_df.loc[oof_dates_iso]

    ts_audit_rows = []
    stale_audit_rows = []
    revision_audit_rows = []

    # Map feature_name to raw close column in context df
    feat_to_raw = {
        "ctx_ret_1d_nifty_bank": ("nifty_bank_close", "nifty_bank_obs_date"),
        "ctx_diff_1d_india_vix": ("india_vix_close", "india_vix_obs_date"),
        "ctx_level_india_vix": ("india_vix_close", "india_vix_obs_date"),
        "ctx_diff_1d_india_10y_yield": ("india_10y_yield_close", "india_10y_yield_obs_date"),
        "ctx_diff_1d_usd_inr": ("usd_inr_close", "usd_inr_obs_date"),
        "ctx_ret_1d_sp500": ("sp500_close", "sp500_obs_date"),
        "ctx_ret_1d_nasdaq": ("nasdaq_close", "nasdaq_obs_date"),
        "ctx_ret_1d_dow_jones": ("dow_jones_close", "dow_jones_obs_date"),
        "ctx_diff_1d_us_vix": ("us_vix_close", "us_vix_obs_date"),
        "ctx_level_us_vix": ("us_vix_close", "us_vix_obs_date"),
        "ctx_ret_1d_nikkei_225": ("nikkei_225_close", "nikkei_225_obs_date"),
        "ctx_ret_1d_hang_seng": ("hang_seng_close", "hang_seng_obs_date"),
        "ctx_ret_1d_ftse_100": ("ftse_100_close", "ftse_100_obs_date"),
        "ctx_ret_1d_brent_crude": ("brent_crude_close", "brent_crude_obs_date"),
        "ctx_ret_1d_wti_crude": ("wti_crude_close", "wti_crude_obs_date"),
        "ctx_ret_1d_gold": ("gold_close", "gold_obs_date"),
        "ctx_ret_1d_dxy": ("dxy_close", "dxy_obs_date"),
        "ctx_diff_1d_us_10y_yield": ("us_10y_yield_close", "us_10y_yield_obs_date"),
    }

    # High volatility periods: 2020 (COVID) and 2018 (Emerging market taper / NBFC)
    is_high_vol = np.array([d.year in (2018, 2020) for d in [ds_b.dates[i] for i in oof_indices]])

    for item in CONTEXT_SPECS_AUDIT:
        fn = item["feature_name"]
        raw_col, obs_col = feat_to_raw[fn]
        vals = ctx_oof[raw_col].values
        obs_d = pd.to_datetime(ctx_oof[obs_col])
        tr_d = pd.to_datetime(ctx_oof.index)

        # Gap between Day T and obs_date
        gaps = (tr_d - obs_d).dt.days.values
        stale_mask = gaps > 0
        n_stale = int(np.sum(stale_mask))
        max_stale = int(np.max(gaps)) if len(gaps) > 0 else 0
        avg_stale = float(np.mean(gaps)) if len(gaps) > 0 else 0.0
        n_stale_high_vol = int(np.sum(stale_mask & is_high_vol))

        # First and last usable date in OOF
        first_d = oof_dates_iso[0]
        last_d = oof_dates_iso[-1]

        # Does value differ under conservative treatment?
        differs_under_cons = not item["in_pit_b"]

        lead_hours = 17.33 if "15:30" in item["nominal_bar_end_time"] and "Asia/Kolkata" in item["source_timezone"] else (6.33 if "16:00" in item["nominal_bar_end_time"] and "New_York" in item["source_timezone"] else (6.08 if "16:15" in item["nominal_bar_end_time"] else (21.33 if "Tokyo" in item["source_timezone"] else (19.33 if "Hong_Kong" in item["source_timezone"] else (10.83 if "London" in item["source_timezone"] else (7.33 if "15:00" in item["nominal_bar_end_time"] else (5.33 if "17:00" in item["nominal_bar_end_time"] else 16.33)))))))

        ts_audit_rows.append({
            "feature_name": fn,
            "feature_family": item["feature_family"],
            "timing_risk": item["timing_risk"],
            "original_value_count": int(np.sum(~np.isnan(vals))),
            "missing_count": int(np.sum(np.isnan(vals))),
            "stale_forward_filled_count": n_stale,
            "availability_classification": item["treatment"],
            "first_usable_date": first_d,
            "last_usable_date": last_d,
            "oof_observations_contributed": 1960 if item["in_pit_a"] else 0,
            "value_differs_under_conservative": differs_under_cons,
            "source_timezone": item["source_timezone"],
            "nominal_bar_end_time": item["nominal_bar_end_time"],
            "estimated_available_time_ist": item["estimated_available_time_ist"],
            "lead_time_to_cutoff_hours": lead_hours,
        })

        stale_audit_rows.append({
            "feature_name": fn,
            "feature_family": item["feature_family"],
            "timing_risk": item["timing_risk"],
            "total_oof_observations": 1960,
            "same_session_observations": 1960 - n_stale,
            "stale_observations": n_stale,
            "stale_pct": (n_stale / 1960.0) * 100.0,
            "max_stale_age_days": max_stale,
            "avg_stale_age_days": avg_stale,
            "stale_obs_high_volatility_periods": n_stale_high_vol,
            "stale_risk_evaluation": "NEGLIGIBLE" if n_stale == 0 else ("LOW" if n_stale < 50 else "MODERATE"),
        })

        rev_status = "NO_REVISION_MECHANISM_IDENTIFIED" if item["timing_risk"] == "LOW RISK" else "UNKNOWN"
        revision_audit_rows.append({
            "feature_name": fn,
            "source_instrument": item["source_instrument"],
            "source_timezone": item["source_timezone"],
            "revision_risk": item["revision_risk"],
            "timing_risk": item["timing_risk"],
            "historical_data_nature": "exchange_closing_index_no_revision_mechanism" if item["timing_risk"] == "LOW RISK" else "continuous_contract_or_indicative_unverified",
            "revision_status_classification": rev_status,
            "pit_clean_certified": item["timing_risk"] == "LOW RISK",
            "notes": item["notes"],
        })

    df_ts_audit = pd.DataFrame(ts_audit_rows)
    ts_audit_csv_path = OUT_DIR / "step9_feature_timestamp_audit.csv"
    df_ts_audit.to_csv(ts_audit_csv_path, index=False)
    print(f"Saved {ts_audit_csv_path} ({len(df_ts_audit)} rows).")

    df_stale_audit = pd.DataFrame(stale_audit_rows)
    stale_audit_csv_path = OUT_DIR / "step9_stale_value_audit.csv"
    df_stale_audit.to_csv(stale_audit_csv_path, index=False)
    print(f"Saved {stale_audit_csv_path} ({len(df_stale_audit)} rows).")

    df_revision_audit = pd.DataFrame(revision_audit_rows)
    revision_audit_csv_path = OUT_DIR / "step9_revision_audit.csv"
    df_revision_audit.to_csv(revision_audit_csv_path, index=False)
    print(f"Saved {revision_audit_csv_path} ({len(df_revision_audit)} rows).")

    # 5. Walk-Forward Training across P0, P1, P2, P3 across 8 Folds
    print("\n--- Step 5: Walk-Forward Training across Models P0, P1, P2, P3 (8 Folds) ---")
    xgb_base_params = {
        "objective": "reg:squarederror",
        "learning_rate": 0.05,
        "max_depth": 2,
        "min_child_weight": 20.0,
        "subsample": 0.8,
        "colsample_bytree": 0.7,
        "reg_alpha": 0.5,
        "reg_lambda": 2.0,
        "random_state": 42,
        "n_jobs": -1,
    }
    candidate_trees = [10, 15, 20, 25, 30, 35, 40, 45, 50, 60]

    oof_predictions: Dict[str, np.ndarray] = {m[0]: np.zeros(len(dev_indices), dtype=np.float64) for m in models}
    oof_baselines: np.ndarray = np.zeros(len(dev_indices), dtype=np.float64)
    fold_result_rows = []

    for m_idx, (m_code, m_name, m_cat, feat_idx) in enumerate(models):
        print(f"\n>> [{m_idx+1}/4] Training Configuration {m_code} ({m_name}, n_feats={len(feat_idx)})...")

        for fold in folds:
            f_id = fold.fold_id
            val_idx = fold.val_indices
            val_year = fold.val_start_date.year

            # Expanding window training set (W0 baseline)
            train_end_date = date(val_year - 1, 12, 31)
            tr_mask = dev_date_arr <= train_end_date
            tr_idx = np.where(tr_mask)[0]

            assert len(tr_idx) > 0, f"Empty training set for {m_code} fold {f_id}"
            assert dev_date_arr[tr_idx[-1]] < fold.val_start_date, f"Leakage: train {dev_date_arr[tr_idx[-1]]} >= val {fold.val_start_date}"

            X_tr = X_dev[tr_idx][:, feat_idx]
            y_tr = y_dev[tr_idx]
            X_val = X_dev[val_idx][:, feat_idx]
            y_val = y_dev[val_idx]

            # Fold-local target baseline (mu_train)
            mu_train = float(np.mean(y_tr))
            oof_baselines[val_idx] = mu_train

            # Select optimal tree count N* via chronological inner validation
            best_n_trees, best_in_rmse = select_optimal_tree_count(
                X_tr, y_tr, xgb_base_params, candidate_trees, val_ratio=0.20
            )

            # Fit on full training fold with selected N*
            final_model = xgb.XGBRegressor(**xgb_base_params, n_estimators=best_n_trees)
            final_model.fit(X_tr, y_tr)

            # Out-of-fold predictions
            val_preds = final_model.predict(X_val)
            oof_predictions[m_code][val_idx] = val_preds

            # Metrics for this fold
            val_res_realized = y_val - mu_train
            val_res_pred = val_preds - mu_train

            raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(val_preds, y_val)
            res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(val_res_pred, val_res_realized)

            mse_baseline = float(np.mean(val_res_realized ** 2))
            mse_model = float(np.mean((y_val - val_preds) ** 2))
            inc_r2 = (1.0 - (mse_model / mse_baseline)) * 100.0 if mse_baseline > 0 else 0.0

            raw_mae = float(np.mean(np.abs(y_val - val_preds))) * 10000.0
            raw_rmse = math.sqrt(mse_model) * 10000.0

            dir_acc = float(np.mean(np.sign(val_preds) == np.sign(y_val))) * 100.0
            res_dir_acc = float(np.mean(np.sign(val_res_pred) == np.sign(val_res_realized))) * 100.0
            pct_short = float(np.mean(val_preds < 0)) * 100.0

            fold_result_rows.append({
                "model_code": m_code,
                "model_name": m_name,
                "model_category": m_cat,
                "n_features": len(feat_idx),
                "fold_id": f_id,
                "val_year": val_year,
                "n_train": len(tr_idx),
                "n_val": len(val_idx),
                "selected_n_trees": best_n_trees,
                "mu_train_bps": mu_train * 10000.0,
                "val_realized_bps": float(np.mean(y_val)) * 10000.0,
                "val_predicted_bps": float(np.mean(val_preds)) * 10000.0,
                "raw_mae_bps": raw_mae,
                "raw_rmse_bps": raw_rmse,
                "raw_pearson_ic": raw_p_ic,
                "raw_pearson_pvalue": raw_p_pval,
                "raw_spearman_ic": raw_s_ic,
                "raw_spearman_pvalue": raw_s_pval,
                "residual_pearson_ic": res_p_ic,
                "residual_pearson_pvalue": res_p_pval,
                "residual_spearman_ic": res_s_ic,
                "residual_spearman_pvalue": res_s_pval,
                "incremental_r2_pct": inc_r2,
                "raw_directional_accuracy_pct": dir_acc,
                "residual_directional_accuracy_pct": res_dir_acc,
                "pct_pred_short": pct_short,
            })

            print(f"  Fold {f_id} ({val_year}): N*={best_n_trees:2d} | Raw IC={raw_p_ic:+.4f} | Res IC={res_p_ic:+.4f} | Inc R2={inc_r2:+.2f}% | %Short={pct_short:5.1f}%")

    df_folds = pd.DataFrame(fold_result_rows)
    folds_csv_path = OUT_DIR / "step9_fold_results.csv"
    df_folds.to_csv(folds_csv_path, index=False)
    print(f"\nSaved {folds_csv_path} ({len(df_folds)} rows).")

    # 6. Assemble step9_predictions.csv
    print("\n--- Step 6: Assembling step9_predictions.csv ---")
    pred_dict: Dict[str, Any] = {
        "trading_date": [ds_b.dates[i].isoformat() for i in oof_indices],
        "target_date": [ds_b.target_dates[i].isoformat() for i in oof_indices],
        "fold_id": [next(f.fold_id for f in folds if i in f.val_indices) for i in oof_indices],
        "realized_intraday_return": y_dev[oof_indices],
        "mu_train": oof_baselines[oof_indices],
        "residual_realized_return": y_dev[oof_indices] - oof_baselines[oof_indices],
    }

    for m_code, _, _, _ in models:
        p = oof_predictions[m_code][oof_indices]
        exc = p - oof_baselines[oof_indices]
        pred_dict[f"pred_{m_code}"] = p
        pred_dict[f"excess_{m_code}"] = exc
        pred_dict[f"sign_{m_code}"] = np.where(p > 0, 1, np.where(p < 0, -1, 0))
        pred_dict[f"excess_sign_{m_code}"] = np.where(exc > 0, 1, np.where(exc < 0, -1, 0))

    df_predictions = pd.DataFrame(pred_dict)
    preds_csv_path = OUT_DIR / "step9_predictions.csv"
    df_predictions.to_csv(preds_csv_path, index=False)
    print(f"Saved {preds_csv_path} ({len(df_predictions)} sessions).")

    # 7. Temporal Stability Analysis (Block A, B, C, Year 2021, Years 2017-2019)
    print("\n--- Step 7: Temporal Stability Analysis across Blocks ---")
    temporal_blocks = [
        ("Block_A", "Block A (2014-2016)", date(2014, 1, 1), date(2016, 12, 31)),
        ("Block_B", "Block B (2017-2019)", date(2017, 1, 1), date(2019, 12, 31)),
        ("Block_C", "Block C (2020-2021)", date(2020, 1, 1), date(2021, 12, 31)),
        ("Year_2021", "Year 2021 (Forensic Check)", date(2021, 1, 1), date(2021, 12, 31)),
        ("Years_2017_2019", "Years 2017-2019 (Forensic Check)", date(2017, 1, 1), date(2019, 12, 31)),
        ("Full_OOF", "Full OOF (2014-2021)", date(2014, 1, 1), date(2021, 12, 31)),
    ]

    temporal_rows = []
    df_preds_dates = pd.to_datetime(df_predictions["trading_date"]).dt.date

    for m_code, m_name, m_cat, _ in models:
        for p_code, p_name, p_start, p_end in temporal_blocks:
            mask = (df_preds_dates >= p_start) & (df_preds_dates <= p_end)
            sub = df_predictions[mask]
            n_sess = len(sub)
            if n_sess == 0:
                continue

            y_sub = sub["realized_intraday_return"].values
            mu_sub = sub["mu_train"].values
            y_res_sub = sub["residual_realized_return"].values
            p_sub = sub[f"pred_{m_code}"].values
            exc_sub = sub[f"excess_{m_code}"].values

            raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(p_sub, y_sub)
            res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(exc_sub, y_res_sub)

            mse_b = float(np.mean(y_res_sub ** 2))
            mse_m = float(np.mean((y_sub - p_sub) ** 2))
            inc_r2 = (1.0 - (mse_m / mse_b)) * 100.0 if mse_b > 0 else 0.0

            dir_acc = float(np.mean(np.sign(p_sub) == np.sign(y_sub))) * 100.0
            res_dir_acc = float(np.mean(np.sign(exc_sub) == np.sign(y_res_sub))) * 100.0

            temporal_rows.append({
                "model_code": m_code,
                "model_name": m_name,
                "model_category": m_cat,
                "period_code": p_code,
                "period_name": p_name,
                "n_sessions": n_sess,
                "raw_pearson_ic": raw_p_ic,
                "raw_pearson_pvalue": raw_p_pval,
                "raw_spearman_ic": raw_s_ic,
                "raw_spearman_pvalue": raw_s_pval,
                "residual_pearson_ic": res_p_ic,
                "residual_pearson_pvalue": res_p_pval,
                "residual_spearman_ic": res_s_ic,
                "residual_spearman_pvalue": res_s_pval,
                "incremental_r2_pct": inc_r2,
                "raw_directional_accuracy_pct": dir_acc,
                "residual_directional_accuracy_pct": res_dir_acc,
                "mean_pred_bps": float(np.mean(p_sub)) * 10000.0,
                "pred_variance_bps2": float(np.var(p_sub * 10000.0, ddof=1)),
                "pct_pred_short": float(np.mean(p_sub < 0)) * 100.0,
            })

    df_temporal = pd.DataFrame(temporal_rows)
    temporal_csv_path = OUT_DIR / "step9_temporal_results.csv"
    df_temporal.to_csv(temporal_csv_path, index=False)
    print(f"Saved {temporal_csv_path} ({len(df_temporal)} rows).")

    # 8. Build Summary Table comparing P0, P1, P2, P3
    print("\n--- Step 8: Building step9_summary.csv ---")
    summary_rows = []
    y_raw_all = df_predictions["realized_intraday_return"].values
    y_res_all = df_predictions["residual_realized_return"].values

    p1_pred = df_predictions["pred_P1_ORIGINAL_PIT"].values
    p1_exc = df_predictions["excess_P1_ORIGINAL_PIT"].values
    p1_raw_ic, _, p1_raw_s_ic, _ = safe_correlation(p1_pred, y_raw_all)
    p1_res_ic, _, p1_res_s_ic, _ = safe_correlation(p1_exc, y_res_all)
    mse_b_p1 = float(np.mean(y_res_all ** 2))
    mse_m_p1 = float(np.mean((y_raw_all - p1_pred) ** 2))
    p1_inc_r2 = (1.0 - (mse_m_p1 / mse_b_p1)) * 100.0

    always_short_gross_bps = float(np.mean(-y_raw_all)) * 10000.0

    for m_code, m_name, m_cat, feat_idx in models:
        p_m = df_predictions[f"pred_{m_code}"].values
        exc_m = df_predictions[f"excess_{m_code}"].values
        n_feats = len(feat_idx)

        raw_p_ic, raw_p_pval, raw_s_ic, raw_s_pval = safe_correlation(p_m, y_raw_all)
        res_p_ic, res_p_pval, res_s_ic, res_s_pval = safe_correlation(exc_m, y_res_all)

        mse_b = float(np.mean(y_res_all ** 2))
        mse_m = float(np.mean((y_raw_all - p_m) ** 2))
        inc_r2 = (1.0 - (mse_m / mse_b)) * 100.0 if mse_b > 0 else 0.0

        raw_mae = float(np.mean(np.abs(y_raw_all - p_m))) * 10000.0
        raw_rmse = math.sqrt(mse_m) * 10000.0
        res_mae = float(np.mean(np.abs(y_res_all - exc_m))) * 10000.0
        res_rmse = math.sqrt(float(np.mean((y_res_all - exc_m) ** 2))) * 10000.0

        dir_acc = float(np.mean(np.sign(p_m) == np.sign(y_raw_all))) * 100.0
        res_dir_acc = float(np.mean(np.sign(exc_m) == np.sign(y_res_all))) * 100.0

        delta_raw_ic = p1_raw_ic - raw_p_ic
        delta_raw_spearman_ic = p1_raw_s_ic - raw_s_ic
        delta_res_ic = p1_res_ic - res_p_ic
        delta_res_spearman_ic = p1_res_s_ic - res_s_ic
        delta_r2_pct = p1_inc_r2 - inc_r2

        t_sub = df_temporal[df_temporal["model_code"] == m_code]
        block_a_res_ic = float(t_sub[t_sub["period_code"] == "Block_A"]["residual_pearson_ic"].values[0])
        block_b_res_ic = float(t_sub[t_sub["period_code"] == "Block_B"]["residual_pearson_ic"].values[0])
        block_c_res_ic = float(t_sub[t_sub["period_code"] == "Block_C"]["residual_pearson_ic"].values[0])

        y2021_res_ic = float(t_sub[t_sub["period_code"] == "Year_2021"]["residual_pearson_ic"].values[0])
        y2021_inc_r2 = float(t_sub[t_sub["period_code"] == "Year_2021"]["incremental_r2_pct"].values[0])
        y2021_pred_var = float(t_sub[t_sub["period_code"] == "Year_2021"]["pred_variance_bps2"].values[0])

        y1719_res_ic = float(t_sub[t_sub["period_code"] == "Years_2017_2019"]["residual_pearson_ic"].values[0])
        y1719_inc_r2 = float(t_sub[t_sub["period_code"] == "Years_2017_2019"]["incremental_r2_pct"].values[0])

        pos = np.where(p_m > 0, 1.0, np.where(p_m < 0, -1.0, 0.0))
        pct_short = float(np.mean(pos < 0)) * 100.0
        pct_long = float(np.mean(pos > 0)) * 100.0
        r_gross = pos * y_raw_all
        model_gross_bps = float(np.mean(r_gross)) * 10000.0
        r_net_10 = pos * y_raw_all - (0.0010 * (pos != 0.0))
        model_net_10bps = float(np.mean(r_net_10)) * 10000.0

        diff_vs_short = r_gross - (-y_raw_all)
        hac_se, hac_t, hac_p = compute_newey_west_hac(diff_vs_short)

        summary_rows.append({
            "model_code": m_code,
            "model_name": m_name,
            "model_category": m_cat,
            "n_features": n_feats,
            "n_sessions": len(df_predictions),
            "raw_pearson_ic": raw_p_ic,
            "raw_pearson_pvalue": raw_p_pval,
            "raw_spearman_ic": raw_s_ic,
            "raw_spearman_pvalue": raw_s_pval,
            "residual_pearson_ic": res_p_ic,
            "residual_pearson_pvalue": res_p_pval,
            "residual_spearman_ic": res_s_ic,
            "residual_spearman_pvalue": res_s_pval,
            "incremental_r2_pct": inc_r2,
            "raw_directional_accuracy_pct": dir_acc,
            "residual_directional_accuracy_pct": res_dir_acc,
            "raw_mae_bps": raw_mae,
            "raw_rmse_bps": raw_rmse,
            "residual_mae_bps": res_mae,
            "residual_rmse_bps": res_rmse,
            "delta_raw_pearson_ic": delta_raw_ic,
            "delta_raw_spearman_ic": delta_raw_spearman_ic,
            "delta_residual_pearson_ic": delta_res_ic,
            "delta_residual_spearman_ic": delta_res_spearman_ic,
            "delta_incremental_r2_pct": delta_r2_pct,
            "block_a_res_ic": block_a_res_ic,
            "block_b_res_ic": block_b_res_ic,
            "block_c_res_ic": block_c_res_ic,
            "year_2021_res_ic": y2021_res_ic,
            "year_2021_incremental_r2_pct": y2021_inc_r2,
            "year_2021_pred_variance_bps2": y2021_pred_var,
            "years_2017_2019_res_ic": y1719_res_ic,
            "years_2017_2019_incremental_r2_pct": y1719_inc_r2,
            "pct_pred_short": pct_short,
            "pct_pred_long": pct_long,
            "always_short_gross_bps": always_short_gross_bps,
            "model_gross_bps": model_gross_bps,
            "model_net_10bps": model_net_10bps,
            "diff_vs_short_mean_bps": float(np.mean(diff_vs_short)) * 10000.0,
            "diff_vs_short_hac_se_bps": hac_se * 10000.0,
            "diff_vs_short_hac_t": hac_t,
            "diff_vs_short_hac_p": hac_p,
        })

    df_summary = pd.DataFrame(summary_rows)
    # FDR correction across the 4 models
    p_vals = df_summary["residual_pearson_pvalue"].values
    n_tests = len(p_vals)
    sorted_idx = np.argsort(p_vals)
    sorted_p = p_vals[sorted_idx]
    fdr_p = np.zeros(n_tests)
    cum_min = 1.0
    for i in range(n_tests - 1, -1, -1):
        rank = i + 1
        adj = (sorted_p[i] * n_tests) / rank
        cum_min = min(cum_min, adj)
        fdr_p[sorted_idx[i]] = min(1.0, cum_min)
    df_summary["fdr_residual_pearson_pvalue"] = fdr_p

    summary_csv_path = OUT_DIR / "step9_summary.csv"
    df_summary.to_csv(summary_csv_path, index=False)
    print(f"Saved {summary_csv_path} ({len(df_summary)} rows).")

    # 9. Placebo / Permutation Test (1,000 permutations, seed 42)
    print("\n--- Step 9: Placebo / Permutation Test (1,000 Permutations, Seed 42) ---")
    n_perm = 1000
    rng = np.random.default_rng(seed=42)
    perm_indices = [rng.permutation(len(df_predictions)) for _ in range(n_perm)]

    placebo_rows = []
    for m_code, _, _, _ in models:
        exc_m = df_predictions[f"excess_{m_code}"].values
        obs_ic, obs_pval, _, _ = safe_correlation(exc_m, y_res_all)

        perm_ics = []
        for p_idx in perm_indices:
            r_p, _, _, _ = safe_correlation(exc_m, y_res_all[p_idx])
            perm_ics.append(r_p)

        perm_arr = np.array(perm_ics, dtype=np.float64)
        mean_p_ic = float(np.mean(perm_arr))
        std_p_ic = float(np.std(perm_arr, ddof=1))
        emp_pct = float(stats.percentileofscore(perm_arr, obs_ic))
        emp_pval = float(np.mean(perm_arr >= obs_ic))

        placebo_rows.append({
            "model_code": m_code,
            "n_sessions": len(df_predictions),
            "n_permutations": n_perm,
            "seed": 42,
            "observed_residual_pearson_ic": obs_ic,
            "observed_residual_pearson_pvalue": obs_pval,
            "placebo_mean_ic": mean_p_ic,
            "placebo_std_ic": std_p_ic,
            "empirical_percentile": emp_pct,
            "empirical_pvalue": emp_pval,
        })
        print(f"  [{m_code:<20}] Obs IC={obs_ic:+.4f} | Placebo Mean={mean_p_ic:+.4f} (std={std_p_ic:.4f}) | Emp P-val={emp_pval:.4f}")

    df_placebo = pd.DataFrame(placebo_rows)
    placebo_csv_path = OUT_DIR / "step9_placebo_results.csv"
    df_placebo.to_csv(placebo_csv_path, index=False)
    print(f"Saved {placebo_csv_path} ({len(df_placebo)} rows).")

    # 10. Economic Stress Test (Diagnostic Only)
    print("\n--- Step 10: Economic Diagnostic (0, 5, 10, 15, 20 bps) ---")
    econ_rows = []
    cost_scenarios = [0.0, 5.0, 10.0, 15.0, 20.0]

    # Evaluate models P0, P1, P2, P3
    for m_code, m_name, m_cat, _ in models:
        p_m = df_predictions[f"pred_{m_code}"].values
        pos = np.where(p_m > 0, 1.0, np.where(p_m < 0, -1.0, 0.0))
        n_long = int(np.sum(pos > 0))
        n_short = int(np.sum(pos < 0))
        n_flat = int(np.sum(pos == 0))
        pct_short = (n_short / len(pos)) * 100.0

        for cost_bps in cost_scenarios:
            cost_decimal = cost_bps / 10000.0
            daily_gross = pos * y_raw_all
            trade_cost = cost_decimal * (pos != 0.0)
            daily_net = daily_gross - trade_cost

            mean_net_bps = float(np.mean(daily_net)) * 10000.0
            hac_se, hac_t, hac_p = compute_newey_west_hac(daily_net)

            cum_ret = float(np.prod(1.0 + daily_net) - 1.0)
            ann_ret = float((1.0 + np.mean(daily_net)) ** 252 - 1.0)
            ann_vol = float(np.std(daily_net, ddof=1) * math.sqrt(252))
            sharpe = (ann_ret / ann_vol) if ann_vol > 0 else 0.0
            max_dd, _ = compute_drawdowns(daily_net)

            econ_rows.append({
                "model_code": m_code,
                "model_name": m_name,
                "model_category": m_cat,
                "cost_bps": cost_bps,
                "n_sessions": len(pos),
                "n_long": n_long,
                "n_short": n_short,
                "n_flat": n_flat,
                "pct_short": pct_short,
                "mean_daily_return_bps": mean_net_bps,
                "hac_se_bps": hac_se * 10000.0,
                "hac_tstat": hac_t,
                "hac_pvalue": hac_p,
                "cum_return_pct": cum_ret * 100.0,
                "annualized_return_pct": ann_ret * 100.0,
                "annualized_volatility_pct": ann_vol * 100.0,
                "sharpe_ratio": sharpe,
                "max_drawdown_pct": max_dd * 100.0,
            })

    # Add Always Short Benchmark across the same cost scenarios
    pos_short = np.full(len(y_raw_all), -1.0)
    for cost_bps in cost_scenarios:
        cost_decimal = cost_bps / 10000.0
        daily_gross = pos_short * y_raw_all
        trade_cost = cost_decimal * (pos_short != 0.0)
        daily_net = daily_gross - trade_cost

        mean_net_bps = float(np.mean(daily_net)) * 10000.0
        hac_se, hac_t, hac_p = compute_newey_west_hac(daily_net)

        cum_ret = float(np.prod(1.0 + daily_net) - 1.0)
        ann_ret = float((1.0 + np.mean(daily_net)) ** 252 - 1.0)
        ann_vol = float(np.std(daily_net, ddof=1) * math.sqrt(252))
        sharpe = (ann_ret / ann_vol) if ann_vol > 0 else 0.0
        max_dd, _ = compute_drawdowns(daily_net)

        econ_rows.append({
            "model_code": "ALWAYS_SHORT",
            "model_name": "Always Short Benchmark",
            "model_category": "benchmark",
            "cost_bps": cost_bps,
            "n_sessions": len(pos_short),
            "n_long": 0,
            "n_short": len(pos_short),
            "n_flat": 0,
            "pct_short": 100.0,
            "mean_daily_return_bps": mean_net_bps,
            "hac_se_bps": hac_se * 10000.0,
            "hac_tstat": hac_t,
            "hac_pvalue": hac_p,
            "cum_return_pct": cum_ret * 100.0,
            "annualized_return_pct": ann_ret * 100.0,
            "annualized_volatility_pct": ann_vol * 100.0,
            "sharpe_ratio": sharpe,
            "max_drawdown_pct": max_dd * 100.0,
        })

    df_econ = pd.DataFrame(econ_rows)
    econ_csv_path = OUT_DIR / "step9_economic_diagnostic.csv"
    df_econ.to_csv(econ_csv_path, index=False)
    print(f"Saved {econ_csv_path} ({len(df_econ)} rows).")

    # 11. Generate Cryptographic Integrity Manifest
    print("\n--- Step 11: Generating Cryptographic Integrity Manifest ---")
    manifest_files = [
        "step9_pit_availability_matrix.csv",
        "step9_pit_availability_matrix.json",
        "step9_feature_timestamp_audit.csv",
        "step9_predictions.csv",
        "step9_fold_results.csv",
        "step9_temporal_results.csv",
        "step9_summary.csv",
        "step9_stale_value_audit.csv",
        "step9_revision_audit.csv",
        "step9_placebo_results.csv",
        "step9_economic_diagnostic.csv",
    ]

    manifest_hashes = {}
    for fn in manifest_files:
        fp = OUT_DIR / fn
        if not fp.is_file():
            raise FileNotFoundError(f"Missing Step 9 output file: {fn}")
        manifest_hashes[fn] = hashlib.sha256(fp.read_bytes()).hexdigest()

    manifest_data = {
        "step_name": "Phase 12 Step 9: Point-in-Time Availability & Context-Feature Robustness Audit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_firewall": {
            "max_trading_date": "2021-12-31",
            "holdout_start_date": "2022-01-03",
            "terminal_holdout_quarantined": True,
            "holdout_sessions_accessed": 0,
        },
        "oof_population": {
            "start_date": "2014-01-02",
            "end_date": "2021-12-31",
            "n_sessions": 1960,
            "n_folds": 8,
        },
        "models_evaluated": [
            {"code": "P0_PRICE_ONLY", "name": "Model P0: Price Only", "n_features": 45},
            {"code": "P1_ORIGINAL_PIT", "name": "Model P1: 45 Price + 18 PIT-A Context", "n_features": 63},
            {"code": "P2_CONSERVATIVE_PIT", "name": "Model P2: 45 Price + 11 PIT-B Context", "n_features": 56},
            {"code": "P3_STRICT_PIT", "name": "Model P3: 45 Price + 8 PIT-C Context", "n_features": 53},
        ],
        "summary_metrics": {
            "P0_res_ic": float(df_summary[df_summary["model_code"] == "P0_PRICE_ONLY"]["residual_pearson_ic"].values[0]),
            "P1_res_ic": float(df_summary[df_summary["model_code"] == "P1_ORIGINAL_PIT"]["residual_pearson_ic"].values[0]),
            "P2_res_ic": float(df_summary[df_summary["model_code"] == "P2_CONSERVATIVE_PIT"]["residual_pearson_ic"].values[0]),
            "P3_res_ic": float(df_summary[df_summary["model_code"] == "P3_STRICT_PIT"]["residual_pearson_ic"].values[0]),
        },
        "file_hashes": manifest_hashes,
    }

    manifest_path = OUT_DIR / "step9_integrity_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"Saved {manifest_path}.")

    print("\n" + "=" * 90)
    print("PHASE 12 STEP 9 COMPUTATION COMPLETED SUCCESSFULLY.")
    print("=" * 90)


if __name__ == "__main__":
    main()
