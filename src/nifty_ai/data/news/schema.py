"""Canonical Schema Definitions for Phase 8 News & NLP Intelligence Layer.

Defines standardized data representations for market news, regulatory filings,
provenance tracking, point-in-time evidence levels, and multi-label event categorization.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from nifty_ai.data.schema import ProvenanceMetadata, ProviderTier


class SourceAuthorityTier(str, Enum):
    """Authority ranking of the source provider for ex-ante importance."""
    TIER_1_REGULATORY = "tier_1_regulatory"       # NSE/BSE announcements, RBI, SEBI, Ministry of Finance
    TIER_2_PRIMARY_WIRE = "tier_2_primary_wire"   # Reuters, Bloomberg, PTI Wire
    TIER_3_FINANCIAL_PRESS = "tier_3_financial_press" # Economic Times, LiveMint, Business Standard
    TIER_4_AGGREGATOR = "tier_4_aggregator"       # GDELT, RSS aggregators, web portals


class AvailabilityEvidenceLevel(str, Enum):
    """Evidence hierarchy level establishing point-in-time publication legitimacy."""
    LEVEL_A = "level_a_realtime_capture"          # Real-time ingestion by NIFTY AI; availability = ingestion_timestamp
    LEVEL_B = "level_b_documented_exchange"       # Documented exchange/feed timestamp + approved buffer
    LEVEL_C = "level_c_commercial_wire"           # Commercial wire release timestamp
    LEVEL_D = "level_d_historical_web"            # Historical web source with explicit timezone & second precision
    LEVEL_UNVERIFIED = "level_unverified"         # Missing/ambiguous timestamp; subject to quarantine


class HistoricalCoverageTier(str, Enum):
    """Classification of historical source coverage completeness."""
    REALTIME_CAPTURED = "realtime_captured"
    HISTORICALLY_VERIFIED = "historically_verified"
    HISTORICALLY_RECONSTRUCTED = "historically_reconstructed"
    INCOMPLETE = "incomplete"
    UNUSABLE = "unusable"


class MarketRelevanceCategory(str, Enum):
    """Graded relevance of news to NIFTY 50 price formation."""
    HIGH_DIRECT = "high_direct"             # Direct corporate catalyst for active NIFTY 50 constituent
    MODERATE_SECTOR = "moderate_sector"     # Sector-wide regulatory/economic catalyst impacting a NIFTY sector
    BROAD_MACRO = "broad_macro"             # Systemic macro catalyst (RBI, Fed, Crude, FX)
    LOW_INCIDENTAL = "low_incidental"       # Incidental passing reference without material operational focus
    ZERO_IRRELEVANT = "zero_irrelevant"     # Off-market / non-economic news


class EventType(str, Enum):
    """Controlled multi-label event taxonomy."""
    EARNINGS = "earnings"                   # Quarterly results, revenue/profit beats/misses, margins
    GUIDANCE = "guidance"                   # Forward guidance, revenue/capex outlook
    CORPORATE_ACTION = "corporate_action"   # M&A, demerger, spin-off, buyback, rights issue, dividend
    MANAGEMENT_CHANGE = "management_change" # CEO/CFO appointment/resignation, board/auditor dispute
    REGULATORY_LEGAL = "regulatory_legal"   # SEBI, ED, CCI actions, court rulings, tariff changes, fines
    ORDER_CONTRACT = "order_contract"       # Major order win, commercial contract, client deal
    CAPEX_INVESTMENT = "capex_investment"   # New plant, expansion, acquisition of physical assets
    CREDIT_DEBT = "credit_debt"             # Credit rating upgrade/downgrade, debt issuance, default
    MACROECONOMIC = "macroeconomic"         # CPI, WPI, GDP, IIP, PMI, trade deficit prints
    MONETARY_POLICY = "monetary_policy"     # RBI repo rate, MPC stance, liquidity, Fed FOMC decisions
    GEOPOLITICAL = "geopolitical"           # War, sanctions, international trade barriers, shipping attacks
    COMMODITY = "commodity"                 # Crude oil, natural gas, gold price shocks or OPEC cuts
    CURRENCY = "currency"                   # USD/INR, DXY sharp moves, forex reserves
    MARKET_STRUCTURE = "market_structure"   # FII/DII net flows, MSCI rebalancing, index inclusions
    ANALYST_RATING = "analyst_rating"       # Brokerage upgrades/downgrades, target price changes
    ROUTINE_COMMENTARY = "routine_commentary" # General market summaries, op-eds, noise


class BodyAvailabilityTier(str, Enum):
    """Completeness level of the textual payload."""
    HEADLINE_ONLY = "headline_only"
    SNIPPET_LEAD = "snippet_lead"
    FULL_TEXT = "full_text"


class DataStatus(str, Enum):
    """Status indicating healthy observation vs provider outage/missing."""
    HEALTHY_OBSERVED = "healthy_observed"
    GENUINE_ZERO_NEWS = "genuine_zero_news"
    PROVIDER_OUTAGE = "provider_outage"
    SPARSE_PERIOD = "sparse_period"


@dataclass(frozen=True)
class EntityMention:
    """Structured extraction of an entity mentioned in news."""
    raw_text: str
    entity_type: str                         # "EQUITY_NSE", "INDEX", "COMMODITY", "REGULATOR", "MACRO"
    canonical_symbol: Optional[str] = None   # e.g., "NSE:RELIANCE", "NIFTY_BANK", "RBI"
    is_active_constituent: bool = False      # Evaluated point-in-time on publication date
    confidence: float = 1.0


@dataclass(frozen=True)
class CanonicalNewsRecord:
    """Standardized representation of a validated, point-in-time financial news item."""
    news_id: str
    source: str
    source_type: SourceAuthorityTier
    headline: str
    published_timestamp: datetime
    availability_timestamp: datetime
    availability_evidence_level: AvailabilityEvidenceLevel
    timezone: str
    provenance: ProvenanceMetadata
    lead_text: Optional[str] = None
    url: Optional[str] = None
    body_availability: BodyAvailabilityTier = BodyAvailabilityTier.SNIPPET_LEAD
    last_modified_timestamp: Optional[datetime] = None
    ingestion_timestamp: Optional[datetime] = None
    
    # NLP extraction attributes
    entities: List[EntityMention] = field(default_factory=list)
    sectors: List[str] = field(default_factory=list)
    primary_event: Any = EventType.ROUTINE_COMMENTARY
    secondary_events: List[Any] = field(default_factory=list)
    event_confidence: float = 1.0
    
    # Market metrics
    market_relevance_category: MarketRelevanceCategory = MarketRelevanceCategory.LOW_INCIDENTAL
    market_relevance_score: float = 0.2
    importance_score: float = 0.2
    importance_components: Dict[str, float] = field(default_factory=dict)
    
    # Sentiment
    sentiment_polarity: float = 0.0          # [-1.0, +1.0]
    sentiment_confidence: float = 1.0        # [0.0, 1.0]
    sentiment_class: str = "NEUTRAL"         # POSITIVE, NEGATIVE, NEUTRAL
    sentiment_model_id: str = "lexicon_lm_baseline"
    
    # Novelty & Clustering
    novelty_score: float = 1.0               # [0.0, 1.0]
    cluster_id: Optional[str] = None
    is_novel: bool = True
    
    # Quality & Quarantine
    quarantine_flag: bool = False
    quarantine_reason: Optional[str] = None

    # Data Origin & Provenance Classification
    data_type: str = "HISTORICAL_GENUINE"    # "HISTORICAL_GENUINE" or "SYNTHETIC_PIPELINE_TEST_DATA"

    def __post_init__(self) -> None:
        if not self.news_id:
            raise ValueError("news_id cannot be empty.")
        if not self.headline:
            raise ValueError("headline cannot be empty.")
        if self.published_timestamp.tzinfo is None:
            raise ValueError("published_timestamp must be timezone-aware.")
        if self.availability_timestamp.tzinfo is None:
            raise ValueError("availability_timestamp must be timezone-aware.")
        if not (-1.0 <= self.sentiment_polarity <= 1.0):
            raise ValueError("sentiment_polarity must fall between -1.0 and +1.0.")
        if not (0.0 <= self.sentiment_confidence <= 1.0):
            raise ValueError("sentiment_confidence must fall between 0.0 and 1.0.")
        if not (0.0 <= self.importance_score <= 1.0):
            raise ValueError("importance_score must fall between 0.0 and 1.0.")
        if not (0.0 <= self.novelty_score <= 1.0):
            raise ValueError("novelty_score must fall between 0.0 and 1.0.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to JSON-serializable dictionary."""
        d = asdict(self)
        d["published_timestamp"] = self.published_timestamp.isoformat()
        d["availability_timestamp"] = self.availability_timestamp.isoformat()
        if self.last_modified_timestamp:
            d["last_modified_timestamp"] = self.last_modified_timestamp.isoformat()
        if self.ingestion_timestamp:
            d["ingestion_timestamp"] = self.ingestion_timestamp.isoformat()
        d["provenance"]["retrieval_timestamp"] = self.provenance.retrieval_timestamp.isoformat()
        if self.provenance.source_timestamp:
            d["provenance"]["source_timestamp"] = self.provenance.source_timestamp.isoformat()
        return d


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
]
