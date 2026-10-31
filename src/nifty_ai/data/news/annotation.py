"""Independent Annotation Pipeline and Protocol Schema.

Decouples human / ground-truth annotation from rule-based NLP predictions.
Enforces multi-annotator tracking, explicit rationale, dispute adjudication,
and strict holdout boundary filtering.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from zoneinfo import ZoneInfo

from nifty_ai.data.news.schema import EventType

TIMEZONE_KOLKATA = ZoneInfo("Asia/Kolkata")
HOLDOUT_START_DATE = date(2022, 1, 1)


class AnnotationStatus(str, Enum):
    """Lifecycle state of an independent ground-truth annotation."""
    PENDING_ANNOTATION = "pending_annotation"
    ANNOTATED = "annotated"
    DISPUTED = "disputed"
    ADJUDICATED = "adjudicated"
    REJECTED_UNVERIFIED = "rejected_unverified"


class SentimentLabel(str, Enum):
    """Controlled ground-truth sentiment labels."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class IndependentAnnotationRecord:
    """Standardized representation of an independently labeled benchmark record."""
    item_id: str
    headline: str
    source: str
    source_url: Optional[str]
    published_timestamp: datetime
    availability_timestamp: datetime
    document_id: Optional[str]
    
    # Primary Annotator
    annotator_id: str
    sentiment_label: SentimentLabel
    sentiment_rationale: str
    event_labels: List[EventType]
    event_rationale: str
    annotation_timestamp: datetime

    # Adjudication & Dispute Resolution
    adjudicator_id: Optional[str] = None
    adjudicated_sentiment: Optional[SentimentLabel] = None
    adjudicated_events: Optional[List[EventType]] = None
    disagreement_flag: bool = False
    final_status: AnnotationStatus = AnnotationStatus.ANNOTATED

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id cannot be empty.")
        if not self.headline:
            raise ValueError("headline cannot be empty.")
        if self.published_timestamp.tzinfo is None:
            raise ValueError("published_timestamp must be timezone-aware.")
        if self.availability_timestamp.tzinfo is None:
            raise ValueError("availability_timestamp must be timezone-aware.")
        if not self.annotator_id:
            raise ValueError("annotator_id must be specified to prove independent human authorship.")
        if not self.sentiment_rationale:
            raise ValueError("sentiment_rationale must document the rationale for the assigned polarity.")

    @property
    def is_pre_2022(self) -> bool:
        """Enforce strict holdout boundary check."""
        pub_dt = self.published_timestamp.astimezone(TIMEZONE_KOLKATA).date()
        return pub_dt < HOLDOUT_START_DATE

    def get_effective_sentiment(self) -> str:
        """Return adjudicated sentiment if present, otherwise primary annotator label."""
        if self.adjudicated_sentiment:
            return self.adjudicated_sentiment.value
        return self.sentiment_label.value

    def get_effective_events(self) -> List[str]:
        """Return adjudicated events if present, otherwise primary annotator labels."""
        if self.adjudicated_events is not None:
            return [e.value for e in self.adjudicated_events]
        return [e.value for e in self.event_labels]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["published_timestamp"] = self.published_timestamp.isoformat()
        d["availability_timestamp"] = self.availability_timestamp.isoformat()
        d["annotation_timestamp"] = self.annotation_timestamp.isoformat()
        d["sentiment_label"] = self.sentiment_label.value
        d["event_labels"] = [e.value for e in self.event_labels]
        d["final_status"] = self.final_status.value
        if self.adjudicated_sentiment:
            d["adjudicated_sentiment"] = self.adjudicated_sentiment.value
        if self.adjudicated_events is not None:
            d["adjudicated_events"] = [e.value for e in self.adjudicated_events]
        d["is_pre_2022"] = self.is_pre_2022
        return d


def validate_benchmark_batch(records: List[IndependentAnnotationRecord]) -> Dict[str, Any]:
    """Audit a proposed benchmark batch for independence, holdout leakage, and completeness."""
    total = len(records)
    holdout_violations = []
    missing_rationale = []
    missing_provenance = []

    for r in records:
        if not r.is_pre_2022:
            holdout_violations.append(r.item_id)
        if not r.sentiment_rationale or len(r.sentiment_rationale.strip()) < 5:
            missing_rationale.append(r.item_id)
        if not r.source or not r.document_id:
            missing_provenance.append(r.item_id)

    is_valid = (len(holdout_violations) == 0 and len(missing_rationale) == 0)

    return {
        "total_records": total,
        "is_valid_development_batch": is_valid,
        "holdout_violations_count": len(holdout_violations),
        "holdout_violation_ids": holdout_violations,
        "missing_rationale_count": len(missing_rationale),
        "missing_provenance_count": len(missing_provenance),
    }


__all__ = [
    "AnnotationStatus",
    "SentimentLabel",
    "IndependentAnnotationRecord",
    "validate_benchmark_batch",
    "HOLDOUT_START_DATE",
]
