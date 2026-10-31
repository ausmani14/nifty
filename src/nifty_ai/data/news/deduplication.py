"""Causal Deduplication and Streaming Semantic Clustering.

Strict rule:
- Records may ONLY be compared against records that were already available
  at or before that point in time.
- Zero future lookahead: later articles cannot retroactively alter past cluster assignments.
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from nifty_ai.data.news.schema import CanonicalNewsRecord


def normalize_text_for_dedup(text: str) -> str:
    """Normalize headline/snippet for deduplication comparison."""
    # Lowercase, strip punctuation and excessive whitespace
    text = text.lower()
    # Normalize common abbreviations in business headlines
    text = re.sub(r"\bai\b", "artificial intelligence", text)
    text = re.sub(r"\bml\b", "machine learning", text)
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compute_content_hash(headline: str, published_date_str: str) -> str:
    """Compute deterministic SHA-256 hash for exact headline matching."""
    norm = normalize_text_for_dedup(headline)
    payload = f"{norm}|{published_date_str}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compute_shingle_jaccard(text1: str, text2: str, k: int = 1) -> float:
    """Compute Jaccard similarity over word k-shingles (defaults to k=1 for headlines)."""
    words1 = normalize_text_for_dedup(text1).split()
    words2 = normalize_text_for_dedup(text2).split()

    if len(words1) < k or len(words2) < k:
        set1 = set(words1)
        set2 = set(words2)
        if not set1 or not set2:
            return 0.0
        return len(set1.intersection(set2)) / len(set1.union(set2))

    shingles1 = set(" ".join(words1[i : i + k]) for i in range(len(words1) - k + 1))
    shingles2 = set(" ".join(words2[i : i + k]) for i in range(len(words2) - k + 1))

    if not shingles1 or not shingles2:
        return 0.0
    return len(shingles1.intersection(shingles2)) / len(shingles1.union(shingles2))


@dataclass
class CausalCluster:
    """Represents an evolving news story cluster."""
    cluster_id: str
    primary_record_id: str
    created_at: datetime
    canonical_headline: str
    record_ids: List[str] = field(default_factory=list)
    sources: Set[str] = field(default_factory=set)
    entities: Set[str] = field(default_factory=set)


class StreamingDeduplicator:
    """Causal, single-pass streaming deduplicator and clusterer."""

    def __init__(self, similarity_threshold: float = 0.80, lookback_window_hours: int = 168) -> None:
        self.similarity_threshold = similarity_threshold
        self.lookback_window = timedelta(hours=lookback_window_hours)  # 7-day causal lookback
        self.exact_hashes: Dict[str, str] = {}  # hash -> record_id
        self.url_map: Dict[str, str] = {}       # url -> record_id
        self.clusters: Dict[str, CausalCluster] = {} # cluster_id -> CausalCluster
        self.record_to_cluster: Dict[str, str] = {}  # record_id -> cluster_id
        self.history: List[CanonicalNewsRecord] = []

    def process_record(self, record: CanonicalNewsRecord) -> Tuple[bool, Optional[str], float, bool]:
        """Process an incoming record causally.

        Returns:
            Tuple of:
            - is_duplicate (bool)
            - cluster_id (str)
            - novelty_score (float, 0.0 to 1.0)
            - is_novel (bool)
        """
        pub_dt = record.availability_timestamp
        h_norm = normalize_text_for_dedup(record.headline)
        h_hash = compute_content_hash(record.headline, pub_dt.date().isoformat())

        record_entities = {e.canonical_symbol for e in record.entities if e.canonical_symbol}

        # 1. Exact URL match in lookback window
        if record.url and record.url in self.url_map:
            prior_id = self.url_map[record.url]
            c_id = self.record_to_cluster.get(prior_id)
            if c_id and c_id in self.clusters:
                c = self.clusters[c_id]
                c.record_ids.append(record.news_id)
                c.sources.add(record.source)
                c.entities.update(record_entities)
                self.record_to_cluster[record.news_id] = c_id
                return True, c_id, 0.0, False

        # 2. Exact Headline + Date Hash match
        if h_hash in self.exact_hashes:
            prior_id = self.exact_hashes[h_hash]
            c_id = self.record_to_cluster.get(prior_id)
            if c_id and c_id in self.clusters:
                c = self.clusters[c_id]
                c.record_ids.append(record.news_id)
                c.sources.add(record.source)
                c.entities.update(record_entities)
                self.record_to_cluster[record.news_id] = c_id
                return True, c_id, 0.0, False

        # 3. Near-duplicate / Syndication fuzzy search over causal lookback history (7-day window)
        max_sim = 0.0
        best_cluster_id: Optional[str] = None

        cutoff_time = pub_dt - self.lookback_window
        # Chronological streaming optimization: break as soon as we cross the 7-day lookback threshold
        for prior in reversed(self.history):
            if prior.availability_timestamp < cutoff_time:
                break
            if prior.availability_timestamp > pub_dt:
                continue
            sim = compute_shingle_jaccard(record.headline, prior.headline)
            if sim > max_sim:
                max_sim = sim
                best_cluster_id = self.record_to_cluster.get(prior.news_id)

        # Base semantic novelty: 1 - similarity
        base_novelty = max(0.0, min(1.0, 1.0 - max_sim))

        if max_sim >= self.similarity_threshold and best_cluster_id is not None:
            # Belongs to existing story cluster
            cluster = self.clusters[best_cluster_id]
            has_new_factual_entity = bool(record_entities - cluster.entities) if record_entities else False
            
            # Award +0.25 factual entity bonus if new entity introduced to an ongoing story
            if has_new_factual_entity:
                novelty_score = round(max(0.0, min(1.0, base_novelty + 0.25)), 4)
            else:
                novelty_score = round(base_novelty, 4)

            cluster.record_ids.append(record.news_id)
            cluster.sources.add(record.source)
            cluster.entities.update(record_entities)
            is_dup = True
            is_novel = False
            cid = best_cluster_id
        else:
            # Genuinely new story cluster
            cid = f"clust_{record.news_id[:12]}"
            new_clust = CausalCluster(
                cluster_id=cid,
                primary_record_id=record.news_id,
                created_at=pub_dt,
                canonical_headline=record.headline,
                record_ids=[record.news_id],
                sources={record.source},
                entities=set(record_entities),
            )
            self.clusters[cid] = new_clust
            novelty_score = round(base_novelty, 4)
            is_dup = False
            is_novel = True

        # Update lookup tables
        self.exact_hashes[h_hash] = record.news_id
        if record.url:
            self.url_map[record.url] = record.news_id
        self.record_to_cluster[record.news_id] = cid
        self.history.append(record)

        return is_dup, cid, novelty_score, is_novel


__all__ = [
    "normalize_text_for_dedup",
    "compute_content_hash",
    "compute_shingle_jaccard",
    "CausalCluster",
    "StreamingDeduplicator",
]
