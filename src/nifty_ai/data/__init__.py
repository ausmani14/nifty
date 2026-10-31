"""Data ingestion, validation, and storage layer.

Designed to enforce:
- No look-ahead bias
- Strict timestamp-awareness
- Clear separation between raw, interim, and processed data
- Provider-agnostic abstractions and provenance tracking
- Rigorous data quality auditing and anomaly diagnostics
"""

from nifty_ai.data.schema import (
    DataFrequency,
    NormalizedMacroRecord,
    NormalizedMarketRecord,
    NormalizedNewsRecord,
    ProvenanceMetadata,
    ProviderStatus,
    ProviderTier,
)
from nifty_ai.data.snapshots import (
    MARKET_TIMEZONE,
    SnapshotCutoff,
    SnapshotType,
    create_snapshot_cutoff,
)
from nifty_ai.data.providers import (
    BaseDataProvider,
    BaseMacroDataProvider,
    BaseMarketDataProvider,
    BaseNewsDataProvider,
    FinancialNewsAdapter,
    GlobalMacroAdapter,
    NSEOfficialMarketProvider,
    ProviderError,
    ProviderNotAvailableError,
    ProviderRegistry,
    YahooFinanceMarketProvider,
    default_registry,
)
from nifty_ai.data.validation import (
    BaseDataValidator,
    MarketDataValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from nifty_ai.data.storage import (
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    compute_file_sha256,
    compute_sha256,
    load_processed_market_data,
    save_processed_market_data,
    save_raw_market_data,
)
from nifty_ai.data.pipeline import (
    HistoricalIngestionPipeline,
    IngestionResult,
)
from nifty_ai.data.quality import (
    CalendarGapItem,
    DataQualityAuditor,
    DataQualityReport,
    QualityCheckItem,
    ReturnStatistics,
    VolumeAuditSummary,
    save_quality_report,
)

__all__ = [
    # Schema & Provenance
    "ProviderStatus",
    "ProviderTier",
    "DataFrequency",
    "ProvenanceMetadata",
    "NormalizedMarketRecord",
    "NormalizedMacroRecord",
    "NormalizedNewsRecord",
    # Snapshots
    "MARKET_TIMEZONE",
    "SnapshotType",
    "SnapshotCutoff",
    "create_snapshot_cutoff",
    # Providers
    "BaseDataProvider",
    "BaseMarketDataProvider",
    "BaseMacroDataProvider",
    "BaseNewsDataProvider",
    "ProviderError",
    "ProviderNotAvailableError",
    "NSEOfficialMarketProvider",
    "YahooFinanceMarketProvider",
    "GlobalMacroAdapter",
    "FinancialNewsAdapter",
    "ProviderRegistry",
    "default_registry",
    # Validation
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationResult",
    "BaseDataValidator",
    "MarketDataValidator",
    # Storage
    "RAW_DATA_DIR",
    "PROCESSED_DATA_DIR",
    "compute_sha256",
    "compute_file_sha256",
    "save_raw_market_data",
    "save_processed_market_data",
    "load_processed_market_data",
    # Pipeline
    "HistoricalIngestionPipeline",
    "IngestionResult",
    # Quality & Anomaly Auditing
    "CalendarGapItem",
    "DataQualityAuditor",
    "DataQualityReport",
    "QualityCheckItem",
    "ReturnStatistics",
    "VolumeAuditSummary",
    "save_quality_report",
]
