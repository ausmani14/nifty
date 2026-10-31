"""Phase 8 News & NLP Intelligence Layer.

Provides standardized schemas, evidence hierarchy verification, point-in-time filtering,
causal deduplication, streaming semantic clustering, entity resolution, and snapshot aggregation.
"""

from nifty_ai.data.news.constituents import (
    CANONICAL_CONSTITUENTS,
    NSE_SECTOR_TAXONOMY,
    ConstituentRecord,
    get_active_nifty_constituents,
    get_constituent_sector,
    is_active_nifty_constituent,
)
from nifty_ai.data.news.datasets import (
    aggregate_snapshot_news,
    build_snapshot_news_datasets,
    compute_information_decay,
)
from nifty_ai.data.news.feature_generation import (
    aggregate_daily_snapshot_features,
    build_snapshot_delta_features,
    run_point_in_time_news_feature_pipeline,
)
from nifty_ai.data.news.deduplication import (
    CausalCluster,
    StreamingDeduplicator,
    compute_content_hash,
    compute_shingle_jaccard,
    normalize_text_for_dedup,
)
from nifty_ai.data.news.nlp_engine import (
    classify_events_multi_label,
    compute_ex_ante_importance,
    evaluate_market_relevance,
    extract_entities,
    map_sectors_from_entities,
)
from nifty_ai.data.news.point_in_time import (
    TIMEZONE_KOLKATA,
    TIMEZONE_UTC,
    evaluate_news_point_in_time,
    filter_news_for_snapshot,
)
from nifty_ai.data.news.schema import (
    AvailabilityEvidenceLevel,
    BodyAvailabilityTier,
    CanonicalNewsRecord,
    DataStatus,
    EntityMention,
    EventType,
    HistoricalCoverageTier,
    MarketRelevanceCategory,
    SourceAuthorityTier,
)
from nifty_ai.data.news.sentiment import (
    FinBERTStubSentiment,
    LoughranMcDonaldIndianSentiment,
    SentimentResult,
    VaderBaselineSentiment,
    benchmark_sentiment_models,
)
from nifty_ai.data.news.providers import (
    NEWS_PROVIDER_REGISTRY,
    NewsProviderAudit,
    RetrievalStatus,
    get_provider_audit_summary,
)
from nifty_ai.data.news.annotation import (
    AnnotationStatus,
    IndependentAnnotationRecord,
    SentimentLabel,
    validate_benchmark_batch,
)

__all__ = [
    "SourceAuthorityTier",
    "AvailabilityEvidenceLevel",
    "HistoricalCoverageTier",
    "MarketRelevanceCategory",
    "EventType",
    "BodyAvailabilityTier",
    "DataStatus",
    "EntityMention",
    "CanonicalNewsRecord",
    "ConstituentRecord",
    "CANONICAL_CONSTITUENTS",
    "NSE_SECTOR_TAXONOMY",
    "is_active_nifty_constituent",
    "get_active_nifty_constituents",
    "get_constituent_sector",
    "TIMEZONE_KOLKATA",
    "TIMEZONE_UTC",
    "evaluate_news_point_in_time",
    "filter_news_for_snapshot",
    "normalize_text_for_dedup",
    "compute_content_hash",
    "compute_shingle_jaccard",
    "CausalCluster",
    "StreamingDeduplicator",
    "extract_entities",
    "map_sectors_from_entities",
    "classify_events_multi_label",
    "evaluate_market_relevance",
    "compute_ex_ante_importance",
    "SentimentResult",
    "LoughranMcDonaldIndianSentiment",
    "FinBERTStubSentiment",
    "VaderBaselineSentiment",
    "benchmark_sentiment_models",
    "compute_information_decay",
    "aggregate_snapshot_news",
    "build_snapshot_news_datasets",
    "RetrievalStatus",
    "NewsProviderAudit",
    "NEWS_PROVIDER_REGISTRY",
    "get_provider_audit_summary",
    "AnnotationStatus",
    "IndependentAnnotationRecord",
    "SentimentLabel",
    "validate_benchmark_batch",
    "aggregate_daily_snapshot_features",
    "build_snapshot_delta_features",
    "run_point_in_time_news_feature_pipeline",
]
