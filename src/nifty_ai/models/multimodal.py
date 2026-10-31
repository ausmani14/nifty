"""Multimodal dataset alignment and feature space definitions for Phase 9 Step 4.

Integrates Phase 4 Price (45), Phase 7 Context (18), and Phase 9 News (49) features
strictly point-in-time, ensuring zero lookahead leakage, zero dropped sessions across
the 4-way join, and disjoint feature ablation partitions.
"""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.snapshots import SnapshotType
from nifty_ai.models.dataset import (
    CLASS_MAP,
    EXPECTED_FEATURE_NAMES as PRICE_FEATURE_NAMES,
    INV_CLASS_MAP,
    load_aligned_dataset,
)

# ---------------------------------------------------------------------------
# 1. Feature Space Definitions
# ---------------------------------------------------------------------------

# 18 Phase 7 Context Features
CONTEXT_RETURN_ASSETS: List[Tuple[str, str]] = [
    ("ctx_ret_1d_nifty_bank", "nifty_bank_close"),
    ("ctx_ret_1d_sp500", "sp500_close"),
    ("ctx_ret_1d_nasdaq", "nasdaq_close"),
    ("ctx_ret_1d_dow_jones", "dow_jones_close"),
    ("ctx_ret_1d_brent_crude", "brent_crude_close"),
    ("ctx_ret_1d_wti_crude", "wti_crude_close"),
    ("ctx_ret_1d_gold", "gold_close"),
    ("ctx_ret_1d_dxy", "dxy_close"),
    ("ctx_ret_1d_nikkei_225", "nikkei_225_close"),
    ("ctx_ret_1d_hang_seng", "hang_seng_close"),
    ("ctx_ret_1d_ftse_100", "ftse_100_close"),
]

CONTEXT_DIFF_ASSETS: List[Tuple[str, str]] = [
    ("ctx_diff_1d_india_vix", "india_vix_close"),
    ("ctx_diff_1d_us_vix", "us_vix_close"),
    ("ctx_diff_1d_india_10y_yield", "india_10y_yield_close"),
    ("ctx_diff_1d_us_10y_yield", "us_10y_yield_close"),
    ("ctx_diff_1d_usd_inr", "usd_inr_close"),
]

CONTEXT_LEVEL_ASSETS: List[Tuple[str, str]] = [
    ("ctx_level_india_vix", "india_vix_close"),
    ("ctx_level_us_vix", "us_vix_close"),
]

CONTEXT_FEATURE_NAMES: List[str] = (
    [name for name, _ in CONTEXT_RETURN_ASSETS]
    + [name for name, _ in CONTEXT_DIFF_ASSETS]
    + [name for name, _ in CONTEXT_LEVEL_ASSETS]
)

# 49 Pre-Registered Phase 9 News Features (6 Disjoint Groups)
NEWS_COUNT_FEATURES: List[str] = [
    "news_count",
    "high_relevance_count",
    "high_importance_count",
    "unique_company_count",
    "unique_event_type_count",
    "has_news_flag",
]

NEWS_SENTIMENT_FEATURES: List[str] = [
    "mean_sentiment",
    "weighted_sentiment",
    "novelty_weighted_sentiment",
    "sentiment_dispersion",
    "positive_count",
    "negative_count",
    "neutral_count",
    "positive_ratio",
    "negative_ratio",
    "sentiment_balance",
]

NEWS_IMPORTANCE_FEATURES: List[str] = [
    "mean_importance",
    "max_importance",
    "weighted_importance",
    "high_importance_ratio",
]

NEWS_EVENT_FEATURES: List[str] = [
    "event_earnings_results_count",
    "event_dividend_count",
    "event_bonus_split_count",
    "event_rights_issue_count",
    "event_buyback_count",
    "event_m_and_a_count",
    "event_capex_business_update_count",
    "event_financial_irregularity_count",
    "event_shareholding_change_count",
    "event_operational_event_count",
    "event_strategic_partnership_count",
    "event_credit_rating_debt_count",
    "event_fundraising_count",
    "event_regulatory_legal_count",
    "event_corporate_action_count",
    "event_management_change_count",
    "event_order_contract_count",
    "event_other_count",
]

NEWS_NOVELTY_FEATURES: List[str] = [
    "mean_novelty",
    "weighted_novelty",
    "novel_news_count",
]

NEWS_COMPANY_FEATURES: List[str] = [
    "top_company_share",
    "top_event_share",
    "company_entropy",
    "event_entropy",
    "company_news_count_mean",
    "company_weighted_sentiment_mean",
    "company_weighted_importance_mean",
    "company_novelty_mean",
]

NEWS_FEATURE_GROUPS: Dict[str, List[str]] = {
    "count": NEWS_COUNT_FEATURES,
    "sentiment": NEWS_SENTIMENT_FEATURES,
    "importance": NEWS_IMPORTANCE_FEATURES,
    "event": NEWS_EVENT_FEATURES,
    "novelty": NEWS_NOVELTY_FEATURES,
    "company": NEWS_COMPANY_FEATURES,
}

ALL_NEWS_FEATURE_NAMES: List[str] = (
    NEWS_COUNT_FEATURES
    + NEWS_SENTIMENT_FEATURES
    + NEWS_IMPORTANCE_FEATURES
    + NEWS_EVENT_FEATURES
    + NEWS_NOVELTY_FEATURES
    + NEWS_COMPANY_FEATURES
)

REGIME_INTERACTION_FEATURES: List[str] = [
    "int_vix_news_count",
    "int_vix_weighted_sentiment",
    "int_vix_negative_count",
]

# Model Hierarchy Mapping
MODEL_FEATURE_SPECS: Dict[str, List[str]] = {
    "Model 0": PRICE_FEATURE_NAMES,
    "Model 1": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES,
    "Model 2": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES + ALL_NEWS_FEATURE_NAMES,
    "M2-Ablation-Count": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES + NEWS_COUNT_FEATURES,
    "M2-Ablation-Sentiment": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES + NEWS_SENTIMENT_FEATURES,
    "M2-Ablation-Importance": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES + NEWS_IMPORTANCE_FEATURES,
    "M2-Ablation-Event": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES + NEWS_EVENT_FEATURES,
    "M2-Ablation-Novelty": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES + NEWS_NOVELTY_FEATURES,
    "M2-Ablation-Company": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES + NEWS_COMPANY_FEATURES,
    "Model 3": PRICE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES + ALL_NEWS_FEATURE_NAMES + REGIME_INTERACTION_FEATURES,
}


# ---------------------------------------------------------------------------
# 2. Context Feature Derivation
# ---------------------------------------------------------------------------

def compute_context_features_dataframe(raw_ctx_df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw context daily series into 18 stationary returns, diffs, and levels."""
    df = raw_ctx_df.copy()
    df["trading_date"] = pd.to_datetime(df["trading_date"])
    df = df.sort_values("trading_date").reset_index(drop=True)

    feat_df = pd.DataFrame({"trading_date": df["trading_date"]})

    # 11 Log Returns
    for feat_name, raw_col in CONTEXT_RETURN_ASSETS:
        s = df[raw_col].ffill().bfill()
        feat_df[feat_name] = np.log(s / s.shift(1)).fillna(0.0).astype(np.float64)

    # 5 Absolute Changes
    for feat_name, raw_col in CONTEXT_DIFF_ASSETS:
        s = df[raw_col].ffill().bfill()
        feat_df[feat_name] = (s - s.shift(1)).fillna(0.0).astype(np.float64)

    # 2 Volatility Levels
    for feat_name, raw_col in CONTEXT_LEVEL_ASSETS:
        s = df[raw_col].ffill().bfill()
        feat_df[feat_name] = s.astype(np.float64)

    return feat_df


# ---------------------------------------------------------------------------
# 3. Multimodal Dataset Class
# ---------------------------------------------------------------------------

@dataclass
class MultimodalDataset:
    """Point-in-time multimodal dataset containing aligned Price, Context, and News features."""
    snapshot_type: SnapshotType
    dates: List[date]
    target_dates: List[date]
    close_prices: np.ndarray
    y_class: np.ndarray
    y_reg: np.ndarray
    features_df: pd.DataFrame

    def get_features(self, model_name: str) -> Tuple[np.ndarray, List[str]]:
        """Extract feature matrix X and names for a given model hierarchy level."""
        if model_name not in MODEL_FEATURE_SPECS:
            raise KeyError(f"Unknown model name '{model_name}'. Expected one of {list(MODEL_FEATURE_SPECS.keys())}")
        feat_names = MODEL_FEATURE_SPECS[model_name]
        missing = [f for f in feat_names if f not in self.features_df.columns]
        if missing:
            raise ValueError(f"Dataset missing requested features for {model_name}: {missing}")
        X = self.features_df[feat_names].values.astype(np.float64)
        if np.isnan(X).any() or np.isinf(X).any():
            raise ValueError(f"Found NaN or Inf in feature matrix for {model_name}")
        return X, feat_names


# ---------------------------------------------------------------------------
# 4. Loader Function
# ---------------------------------------------------------------------------

def load_multimodal_dataset(snapshot_type: SnapshotType = SnapshotType.SNAPSHOT_1540) -> MultimodalDataset:
    """Load, align, and construct multimodal dataset across Price, Targets, Context, and News.

    Strict Invariants:
    - Exactly 4,453 supervised sessions across 2008-07-08 to 2026-09-03
    - Exactly 3,299 Development sessions (<= 2021-12-31)
    - Exactly 1,154 Terminal Holdout sessions (>= 2022-01-03)
    - Zero dropped rows across the 4-way join
    - Zero NaNs or Infs across all features
    """
    snap_suffix = "snapshot_a" if snapshot_type == SnapshotType.SNAPSHOT_1540 else "snapshot_b"
    snap_char = "a" if snapshot_type == SnapshotType.SNAPSHOT_1540 else "b"

    features_csv = PROJECT_ROOT / "data" / "features" / "nifty50_features_clean.csv"
    targets_csv = PROJECT_ROOT / "data" / "targets" / f"nifty50_targets_{snap_suffix}.csv"
    context_csv = PROJECT_ROOT / "data" / "interim" / "context" / f"snapshot_{snap_char}_context_daily.csv"
    news_csv = PROJECT_ROOT / "data" / "interim" / "news" / f"features_news_{snap_suffix}.csv"

    # 1. Base Price + Target dataset from Phase 6
    aligned_base = load_aligned_dataset(features_csv, targets_csv, snapshot_type)
    n_sessions = len(aligned_base.dates)
    if n_sessions != 4453:
        raise ValueError(f"Expected 4453 supervised sessions, found {n_sessions}")

    # Create base dataframe aligned with aligned_base.dates
    base_df = pd.DataFrame(aligned_base.X, columns=PRICE_FEATURE_NAMES)
    base_df["trading_date"] = [d.isoformat() for d in aligned_base.dates]

    # 2. Context Features
    raw_ctx = pd.read_csv(context_csv)
    ctx_feat_df = compute_context_features_dataframe(raw_ctx)
    ctx_feat_df["trading_date"] = ctx_feat_df["trading_date"].dt.strftime("%Y-%m-%d")

    # 3. News Features
    raw_news = pd.read_csv(news_csv)
    news_feat_df = raw_news[["trading_date"] + ALL_NEWS_FEATURE_NAMES].copy()

    # 4. Merge all
    merged = pd.merge(base_df, ctx_feat_df, on="trading_date", how="inner")
    if len(merged) != 4453:
        raise ValueError(f"Context merge dropped rows: {len(merged)} != 4453")

    merged = pd.merge(merged, news_feat_df, on="trading_date", how="inner")
    if len(merged) != 4453:
        raise ValueError(f"News merge dropped rows: {len(merged)} != 4453")

    # 5. Add Regime Interaction Features (Model 3)
    merged["int_vix_news_count"] = (merged["ctx_level_india_vix"] * merged["news_count"]).astype(np.float64)
    merged["int_vix_weighted_sentiment"] = (merged["ctx_level_india_vix"] * merged["weighted_sentiment"]).astype(np.float64)
    merged["int_vix_negative_count"] = (merged["ctx_level_india_vix"] * merged["negative_count"]).astype(np.float64)

    # Sanity checks
    all_needed_cols = (
        PRICE_FEATURE_NAMES
        + CONTEXT_FEATURE_NAMES
        + ALL_NEWS_FEATURE_NAMES
        + REGIME_INTERACTION_FEATURES
    )
    if merged[all_needed_cols].isna().any().any():
        raise ValueError("Detected NaN values in multimodal feature dataframe")
    if np.isinf(merged[all_needed_cols].values).any():
        raise ValueError("Detected Inf values in multimodal feature dataframe")

    return MultimodalDataset(
        snapshot_type=snapshot_type,
        dates=aligned_base.dates,
        target_dates=aligned_base.target_dates,
        close_prices=aligned_base.close_prices,
        y_class=aligned_base.y_class,
        y_reg=aligned_base.y_reg,
        features_df=merged,
    )


__all__ = [
    "PRICE_FEATURE_NAMES",
    "CONTEXT_FEATURE_NAMES",
    "NEWS_COUNT_FEATURES",
    "NEWS_SENTIMENT_FEATURES",
    "NEWS_IMPORTANCE_FEATURES",
    "NEWS_EVENT_FEATURES",
    "NEWS_NOVELTY_FEATURES",
    "NEWS_COMPANY_FEATURES",
    "NEWS_FEATURE_GROUPS",
    "ALL_NEWS_FEATURE_NAMES",
    "REGIME_INTERACTION_FEATURES",
    "MODEL_FEATURE_SPECS",
    "MultimodalDataset",
    "compute_context_features_dataframe",
    "load_multimodal_dataset",
]
