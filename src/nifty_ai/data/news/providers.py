"""News and Corporate Filing Provider Architecture & Audit Registry.

Explicitly tracks provider availability, retrieval capabilities, timestamp quality,
provenance standards, and access constraints across all candidate news feeds.
Ensures no provider is falsely claimed to provide automated historical retrieval.
"""

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class RetrievalStatus(str, Enum):
    """Operational retrieval status of the news provider."""
    OPERATIONAL_VERIFIED = "operational_verified"
    RATE_LIMITED_429 = "rate_limited_429"
    COMMERCIAL_PAYWALL_REQUIRED = "commercial_paywall_required"
    NO_HISTORICAL_API = "no_historical_api"
    OFFLINE_ARCHIVE_ONLY = "offline_archive_only"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class NewsProviderAudit:
    """Standardized metadata audit for a news source / feed provider."""
    provider: str
    source: str
    coverage_start: Optional[str]
    coverage_end: Optional[str]
    retrieval_status: RetrievalStatus
    rate_limit_status: str
    timestamp_quality: str
    provenance_quality: str
    historical_availability: str
    legal_access_constraints: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["retrieval_status"] = self.retrieval_status.value
        return d


# Audited Provider Catalog for NIFTY 50 News Intelligence
NEWS_PROVIDER_REGISTRY: Dict[str, NewsProviderAudit] = {
    "nse_corporate_announcements": NewsProviderAudit(
        provider="National Stock Exchange of India (NSE)",
        source="NSE Corporate Announcements / Form 33 / Reg 30 Filings",
        coverage_start="2008-01-01",
        coverage_end="Present",
        retrieval_status=RetrievalStatus.COMMERCIAL_PAYWALL_REQUIRED,
        rate_limit_status="Strict Web Application Firewall (WAF) blocks automated bulk requests",
        timestamp_quality="High: Exchange server ingestion timestamp with second precision",
        provenance_quality="High: Auditable regulatory filing submission records with circular IDs",
        historical_availability="Restricted: Public portal shows recent 3 months; multi-year bulk access requires licensed NSE Data Feed or member terminal",
        legal_access_constraints="NSE Terms of Use prohibit automated scraping of public portal without commercial license",
    ),
    "bse_corporate_disclosures": NewsProviderAudit(
        provider="Bombay Stock Exchange (BSE)",
        source="BSE Corporate Disclosures / Announcements",
        coverage_start="2008-01-01",
        coverage_end="Present",
        retrieval_status=RetrievalStatus.COMMERCIAL_PAYWALL_REQUIRED,
        rate_limit_status="CAPTCHA and dynamic session tokens prevent direct programmatic scraping",
        timestamp_quality="High: Exchange broadcast timestamp with second precision",
        provenance_quality="High: Auditable corporate announcements with BSE script codes",
        historical_availability="Restricted: Public website search available but automated bulk downloads restricted without licensed feed",
        legal_access_constraints="BSE terms prohibit bulk programmatic extraction without formal redistribution agreement",
    ),
    "rbi_press_releases": NewsProviderAudit(
        provider="Reserve Bank of India (RBI)",
        source="RBI Monetary Policy Statements, Notifications, Enforcement Orders",
        coverage_start="2008-01-01",
        coverage_end="Present",
        retrieval_status=RetrievalStatus.OFFLINE_ARCHIVE_ONLY,
        rate_limit_status="No formal REST API; public HTML archive browsable with standard rate limits",
        timestamp_quality="High: Official release date and scheduled press release timing (usually 10:00 or 11:00 IST)",
        provenance_quality="High: Official sovereign central bank communications with press release serial numbers",
        historical_availability="Available: Complete historical press release archive maintained on rbi.org.in",
        legal_access_constraints="Public sovereign documentation under Government of India open data principles",
    ),
    "gdelt_doc_api": NewsProviderAudit(
        provider="GDELT Project 2.0 Doc API",
        source="Global Database of Events, Language, and Tone (GDELT)",
        coverage_start="2015-02-19",
        coverage_end="Present",
        retrieval_status=RetrievalStatus.RATE_LIMITED_429,
        rate_limit_status="HTTP 429 Too Many Requests: Free API aggressively rate-limits consecutive queries (max 1 req/5s, frequent 429 blocks)",
        timestamp_quality="Medium: 15-minute collection bin timestamps; occasionally diverges from publisher original time",
        provenance_quality="Medium: Provides source URLs and domain names, but many historical URLs suffer link rot or paywalls",
        historical_availability="Partial: Covers 2015 onward; pre-2015 Indian corporate filings are not covered by GDELT 2.0",
        legal_access_constraints="Open research database, but subject to strict free-tier query quotas",
    ),
    "yahoo_finance_news": NewsProviderAudit(
        provider="Yahoo Finance (Free Public Web Endpoint)",
        source="Syndicated Press Articles (Reuters, PR Newswire, Bloomberg, etc.)",
        coverage_start="Current Rolling Window Only (Past 7-30 days)",
        coverage_end="Present",
        retrieval_status=RetrievalStatus.NO_HISTORICAL_API,
        rate_limit_status="Accessible for live quotes, but historical news search endpoint does not exist on free tier",
        timestamp_quality="Low: Often date-only or rolling relative strings ('3 hours ago') on historical items",
        provenance_quality="Low: Aggregated syndicated stories without verifiable exchange filing links",
        historical_availability="Unavailable: Free tier provides zero multi-year historical news archives",
        legal_access_constraints="Yahoo Developer terms prohibit commercial redistribution of scraped news",
    ),
    "reuters_bloomberg_wires": NewsProviderAudit(
        provider="Commercial Financial News Wires (Reuters / Bloomberg)",
        source="Real-time Financial Wire Dispatches",
        coverage_start="1990s",
        coverage_end="Present",
        retrieval_status=RetrievalStatus.COMMERCIAL_PAYWALL_REQUIRED,
        rate_limit_status="Enterprise APIs (Bloomberg Server API, Refinitiv NewsScope) require active enterprise subscription",
        timestamp_quality="Ultra-High: Millisecond-precision wire transmission timestamps with global synchronized clocks",
        provenance_quality="Ultra-High: Regulated financial journalism with unique wire story codes and version history",
        historical_availability="Complete: Full historical machine-readable archive accessible with enterprise license",
        legal_access_constraints="Strict commercial licensing and per-seat subscription fees",
    ),
}


def get_provider_audit_summary() -> List[Dict[str, Any]]:
    """Return list of all audited provider dictionaries."""
    return [p.to_dict() for p in NEWS_PROVIDER_REGISTRY.values()]


__all__ = [
    "RetrievalStatus",
    "NewsProviderAudit",
    "NEWS_PROVIDER_REGISTRY",
    "get_provider_audit_summary",
]
