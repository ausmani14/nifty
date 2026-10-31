"""NLP Extraction Engine: Entity Resolution, Sector Mapping, Multi-Label Events,
Market Relevance, and Ex-Ante Importance.

Ensures strict point-in-time constituent membership and zero future lookahead.
"""

import re
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from nifty_ai.data.news.constituents import (
    CANONICAL_CONSTITUENTS,
    NSE_SECTOR_TAXONOMY,
    is_active_nifty_constituent,
)
from nifty_ai.data.news.schema import (
    EntityMention,
    EventType,
    MarketRelevanceCategory,
    SourceAuthorityTier,
)

# Macro & Regulatory Entity Recognition Patterns
REGULATOR_PATTERNS = {
    "RBI": [r"\brbi\b", r"reserve bank of india", r"monetary policy committee", r"\bmpc\b"],
    "SEBI": [r"\bsebi\b", r"securities and exchange board of india"],
    "FED": [r"\bfed\b", r"federal reserve", r"\bfomc\b", r"jerome powell"],
    "GOVT_INDIA": [r"ministry of finance", r"finmin", r"nirmala sitharaman", r"government of india"],
}

MACRO_ASSET_PATTERNS = {
    "BRENT_CRUDE": [r"brent crude", r"crude oil", r"\bopec\b", r"oil prices"],
    "USD_INR": [r"usd/?inr", r"rupee vs dollar", r"indian rupee", r"forex reserves"],
    "US_10Y_YIELD": [r"us 10-?year", r"treasury yield", r"bond yield"],
}

# Multi-label event taxonomy keyword patterns
EVENT_PATTERNS: Dict[EventType, List[str]] = {
    EventType.EARNINGS: [
        r"\bearnings\b", r"\bq[1-4]\b", r"quarterly (results|profit|loss|earnings)", r"net profit",
        r"revenue (rose|fell|up|down|grows|surges)", r"ebitda", r"pat (jumps|falls|beats)",
        r"earnings beat", r"financial results", r"operating margin"
    ],
    EventType.GUIDANCE: [
        r"guidance", r"revenue outlook", r"growth target", r"capex outlook", r"margin outlook",
        r"warns of muted", r"warning of slowdown", r"forecasts"
    ],
    EventType.CORPORATE_ACTION: [
        r"merger", r"acquisition", r"acquires", r"demerger", r"buyback", r"rights issue", r"dividend",
        r"spin-off", r"recommends final dividend", r"takeover", r"stake sale"
    ],
    EventType.MANAGEMENT_CHANGE: [
        r"ceo (resigns|steps down|appointed)", r"cfo (resigns|appointed)", r"managing director",
        r"auditor (resigns|quits)", r"board reshuffle", r"chief technology officer", r"cto resigns",
        r"denied extension", r"cuts tenure", r"appoints.*?as chief"
    ],
    EventType.REGULATORY_LEGAL: [
        r"sebi order", r"penalty", r"fine imposed", r"supreme court", r"investigation", r"tariff hike",
        r"export duty", r"windfall tax", r"antitrust", r"tax authorities", r"disallowing input credit",
        r"probe into", r"form 483", r"whistleblower", r"rbi imposes ban", r"rbi lifts restrictions",
        r"money laundering", r"enforcement directorate"
    ],
    EventType.ORDER_CONTRACT: [
        r"order win", r"bags order", r"secures contract", r"deal worth", r"commercial agreement",
        r"signs multi-year cloud", r"cloud migration deal", r"wins supply order", r"multi-billion order"
    ],
    EventType.CAPEX_INVESTMENT: [
        r"new plant", r"capacity expansion", r"invests cr", r"capex plan", r"manufacturing facility",
        r"capex investment", r"greenfield facility", r"giga factories", r"rolling mill expansion"
    ],
    EventType.CREDIT_DEBT: [
        r"credit rating", r"downgrade", r"upgrade", r"debt issuance", r"ncd", r"bond sale", r"default",
        r"commercial paper", r"net debt", r"bad loans", r"gross npa", r"deleveraging", r"rating affirmed",
        r"rating downgraded", r"crisil upgrades", r"fitch ratings"
    ],
    EventType.MACROECONOMIC: [
        r"cpi inflation", r"wpi inflation", r"gdp growth", r"gdp contracts", r"gdp rebounds",
        r"iip data", r"industrial output", r"pmi index", r"manufacturing pmi", r"trade deficit",
        r"gst collection", r"retail cpi"
    ],
    EventType.MONETARY_POLICY: [
        r"repo rate", r"rate hike", r"rate cut", r"monetary policy", r"mpc meeting", r"crr hike",
        r"reverse repo", r"g-sap"
    ],
    EventType.GEOPOLITICAL: [
        r"geopolitical", r"middle east conflict", r"sanctions", r"war", r"red sea attack", r"shipping disruption"
    ],
    EventType.COMMODITY: [
        r"crude oil", r"brent", r"natural gas", r"gold prices", r"metal prices", r"opec cut", r"opec\+"
    ],
    EventType.CURRENCY: [
        r"rupee hits", r"rupee falls", r"rupee gains", r"rupee plunges", r"dollar index", r"dxy",
        r"forex reserves"
    ],
    EventType.MARKET_STRUCTURE: [
        r"fii (buying|selling|inflow|outflow)", r"dii (buying|inflow)", r"msci rebalance", r"index rejig",
        r"mock trading session"
    ],
    EventType.ANALYST_RATING: [
        r"brokerage (upgrades|downgrades)", r"target price", r"overweight", r"underweight", r"buy call"
    ],
    EventType.ROUTINE_COMMENTARY: [
        r"closes for trading on account of", r"revises fixed deposit rates", r"schedules board meeting",
        r"confirms no material unannounced", r"corporate social responsibility"
    ],
}


def extract_entities(text: str, target_date: date) -> List[EntityMention]:
    """Extract equity constituents, regulators, and macro assets point-in-time."""
    text_lower = text.lower()
    entities: List[EntityMention] = []
    seen_symbols: Set[str] = set()

    # 1. Equity Constituents
    for c in CANONICAL_CONSTITUENTS:
        matched = False
        # Check aliases
        for alias in c.aliases:
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, text_lower):
                # Check disambiguation if required
                if c.disambiguation_tokens:
                    if any(re.search(r"\b" + re.escape(tok) + r"\b", text_lower) for tok in c.disambiguation_tokens):
                        matched = True
                        break
                else:
                    matched = True
                    break

        if matched and c.symbol not in seen_symbols:
            is_active = is_active_nifty_constituent(c.symbol, target_date)
            entities.append(
                EntityMention(
                    raw_text=c.company_name,
                    entity_type="EQUITY_NSE",
                    canonical_symbol=f"NSE:{c.symbol}",
                    is_active_constituent=is_active,
                    confidence=0.95,
                )
            )
            seen_symbols.add(c.symbol)

    # 2. Regulators / Central Banks
    for reg, pats in REGULATOR_PATTERNS.items():
        if any(re.search(p, text_lower) for p in pats):
            if reg not in seen_symbols:
                entities.append(
                    EntityMention(
                        raw_text=reg,
                        entity_type="REGULATOR",
                        canonical_symbol=reg,
                        is_active_constituent=False,
                        confidence=0.90,
                    )
                )
                seen_symbols.add(reg)

    # 3. Macro Assets
    for asset, pats in MACRO_ASSET_PATTERNS.items():
        if any(re.search(p, text_lower) for p in pats):
            if asset not in seen_symbols:
                entities.append(
                    EntityMention(
                        raw_text=asset,
                        entity_type="MACRO_ASSET",
                        canonical_symbol=asset,
                        is_active_constituent=False,
                        confidence=0.85,
                    )
                )
                seen_symbols.add(asset)

    return entities


def map_sectors_from_entities(entities: List[EntityMention]) -> List[str]:
    """Derive impacted NIFTY sector indices from recognized entities."""
    sectors = set()
    for ent in entities:
        if ent.canonical_symbol and ent.canonical_symbol.startswith("NSE:"):
            sym = ent.canonical_symbol.split(":", 1)[1]
            for c in CANONICAL_CONSTITUENTS:
                if c.symbol == sym:
                    sectors.add(c.primary_sector)
    return sorted(list(sectors))


def classify_events_multi_label(text: str) -> Tuple[EventType, List[EventType], float]:
    """Classify primary and secondary events using the controlled multi-label taxonomy."""
    text_lower = text.lower()
    matched_events: List[Tuple[EventType, int]] = []

    for evt_type, patterns in EVENT_PATTERNS.items():
        matches = sum(1 for p in patterns if re.search(p, text_lower))
        if matches > 0:
            matched_events.append((evt_type, matches))

    if not matched_events:
        return EventType.ROUTINE_COMMENTARY, [], 0.5

    # Sort by number of pattern matches descending
    matched_events.sort(key=lambda x: x[1], reverse=True)
    primary = matched_events[0][0]
    secondaries = [e[0] for e in matched_events[1:]]
    confidence = min(1.0, 0.6 + 0.15 * matched_events[0][1])

    return primary, secondaries, round(confidence, 2)


def evaluate_market_relevance(
    entities: List[EntityMention],
    primary_event: EventType,
    text: str,
) -> Tuple[MarketRelevanceCategory, float]:
    """Compute graded market relevance score and category without peeking at future price."""
    active_constituents = [e for e in entities if e.is_active_constituent and e.entity_type == "EQUITY_NSE"]
    has_regulator = any(e.entity_type == "REGULATOR" for e in entities)
    has_macro_asset = any(e.entity_type == "MACRO_ASSET" for e in entities)

    # Level 4: Direct High
    if active_constituents and primary_event in (
        EventType.EARNINGS, EventType.CORPORATE_ACTION, EventType.MANAGEMENT_CHANGE,
        EventType.REGULATORY_LEGAL, EventType.GUIDANCE
    ):
        return MarketRelevanceCategory.HIGH_DIRECT, 0.90
    elif active_constituents:
        return MarketRelevanceCategory.HIGH_DIRECT, 0.80

    # Level 3: Sector Material
    if has_regulator or primary_event in (EventType.REGULATORY_LEGAL, EventType.ORDER_CONTRACT, EventType.CAPEX_INVESTMENT):
        return MarketRelevanceCategory.MODERATE_SECTOR, 0.65

    # Level 2: Broad Macro
    if has_macro_asset or primary_event in (
        EventType.MONETARY_POLICY, EventType.MACROECONOMIC, EventType.GEOPOLITICAL, EventType.COMMODITY, EventType.CURRENCY
    ):
        return MarketRelevanceCategory.BROAD_MACRO, 0.45

    # Level 1: Low Incidental
    if entities or primary_event == EventType.ANALYST_RATING:
        return MarketRelevanceCategory.LOW_INCIDENTAL, 0.20

    # Level 0: Zero Irrelevant
    return MarketRelevanceCategory.ZERO_IRRELEVANT, 0.05


def compute_ex_ante_importance(
    source_type: SourceAuthorityTier,
    primary_event: EventType,
    relevance_category: MarketRelevanceCategory,
    headline_syndication_count: int = 1,
) -> Tuple[float, Dict[str, float]]:
    """Compute ex-ante importance score using provisional rubric parameters.

    Components:
    - S: Source authority (weight 0.35)
    - E: Event severity (weight 0.30)
    - M: Entity/Market scope (weight 0.20)
    - C: Syndication/persistence (weight 0.15)
    """
    # 1. Source Authority (0.2 to 1.0)
    source_scores = {
        SourceAuthorityTier.TIER_1_REGULATORY: 1.0,
        SourceAuthorityTier.TIER_2_PRIMARY_WIRE: 0.8,
        SourceAuthorityTier.TIER_3_FINANCIAL_PRESS: 0.5,
        SourceAuthorityTier.TIER_4_AGGREGATOR: 0.2,
    }
    s_score = source_scores.get(source_type, 0.3)

    # 2. Event Severity (0.2 to 1.0)
    if primary_event in (EventType.MONETARY_POLICY, EventType.GEOPOLITICAL):
        e_score = 1.0
    elif primary_event in (EventType.EARNINGS, EventType.CORPORATE_ACTION, EventType.MANAGEMENT_CHANGE, EventType.REGULATORY_LEGAL):
        e_score = 0.8
    elif primary_event in (EventType.MACROECONOMIC, EventType.COMMODITY, EventType.CURRENCY):
        e_score = 0.6
    elif primary_event in (EventType.ORDER_CONTRACT, EventType.CAPEX_INVESTMENT, EventType.CREDIT_DEBT):
        e_score = 0.5
    else:
        e_score = 0.2

    # 3. Market Relevance Scope (0.1 to 1.0)
    rel_scores = {
        MarketRelevanceCategory.HIGH_DIRECT: 0.9,
        MarketRelevanceCategory.MODERATE_SECTOR: 0.7,
        MarketRelevanceCategory.BROAD_MACRO: 0.5,
        MarketRelevanceCategory.LOW_INCIDENTAL: 0.2,
        MarketRelevanceCategory.ZERO_IRRELEVANT: 0.0,
    }
    m_score = rel_scores.get(relevance_category, 0.2)

    # 4. Syndication / Coverage Breadth (0.2 to 1.0)
    if headline_syndication_count >= 5:
        c_score = 1.0
    elif headline_syndication_count >= 2:
        c_score = 0.6
    else:
        c_score = 0.2

    # Provisional rubric formula
    total = round(0.35 * s_score + 0.30 * e_score + 0.20 * m_score + 0.15 * c_score, 4)
    components = {
        "source_score": s_score,
        "event_score": e_score,
        "market_scope_score": m_score,
        "syndication_score": c_score,
    }
    return total, components


__all__ = [
    "extract_entities",
    "map_sectors_from_entities",
    "classify_events_multi_label",
    "evaluate_market_relevance",
    "compute_ex_ante_importance",
]
