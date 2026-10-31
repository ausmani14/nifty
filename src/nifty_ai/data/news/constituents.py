"""Point-in-Time NIFTY 50 Constituent Registry and Sector Mapping.

Enforces strict temporal membership bounds to prevent survivorship bias
and forward-looking entity resolution.
"""

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class ConstituentRecord:
    """Historical record of an equity security in NIFTY 50."""
    symbol: str                              # e.g., "RELIANCE"
    company_name: str                        # e.g., "Reliance Industries Ltd"
    primary_sector: str                      # e.g., "NIFTY_OIL_GAS"
    valid_from: date                         # Effective start date in NIFTY 50
    valid_to: Optional[date]                 # Effective exit date, or None if currently active
    aliases: Tuple[str, ...]                 # Known aliases, ticker variants, trade names
    disambiguation_tokens: Tuple[str, ...]   # Required tokens if ambiguous conglomerate name


# Sector classification taxonomy mapping to official NSE sector indices
NSE_SECTOR_TAXONOMY: Dict[str, str] = {
    "NIFTY_BANK": "Indian Banking & Financial Intermediaries",
    "NIFTY_IT": "Information Technology & Software Services",
    "NIFTY_OIL_GAS": "Oil, Gas & Consumable Fuels",
    "NIFTY_AUTO": "Automobiles & Auto Ancillaries",
    "NIFTY_FMCG": "Fast Moving Consumer Goods",
    "NIFTY_METALS": "Metals, Mining & Steel",
    "NIFTY_PHARMA": "Pharmaceuticals & Healthcare",
    "NIFTY_FIN_SERVICE": "Non-Bank Financial Services & Insurance",
    "NIFTY_INFRA": "Infrastructure, Construction & Power",
    "NIFTY_TELECOM": "Telecommunications & Digital Infrastructure",
    "NIFTY_MEDIA": "Media, Entertainment & Publishing",
    "NIFTY_CHEM": "Chemicals, Petrochemicals & Agrochemicals",
    "NIFTY_CONSUMPTION": "Consumer Durables, Retail & Discretionary",
}


# Canonical Point-in-Time Registry of NIFTY 50 constituents across history
# Reconciled in Phase 9 Step 2D using official NSE Indices evidence
CANONICAL_CONSTITUENTS: List[ConstituentRecord] = [
    # =========================================================================
    # 50 Active Baseline Constituents on 2022-01-01
    # =========================================================================
    ConstituentRecord(
        symbol="ADANIPORTS",
        company_name="Adani Ports and Special Economic Zone Limited",
        primary_sector="NIFTY_INFRA",
        valid_from=date(2015, 9, 28),
        valid_to=None,
        aliases=("adani ports", "adani ports and sez", "adani port", "mundra port", "adaniports"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="ASIANPAINT",
        company_name="Asian Paints Limited",
        primary_sector="NIFTY_CONSUMPTION",
        valid_from=date(2012, 4, 27),
        valid_to=None,
        aliases=("asian paints", "asian paint", "asianpaint"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="AXISBANK",
        company_name="Axis Bank Limited",
        primary_sector="NIFTY_BANK",
        valid_from=date(2009, 3, 27),
        valid_to=None,
        aliases=("axis bank", "uti bank", "axisbank"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="BAJAJ-AUTO",
        company_name="Bajaj Auto Limited",
        primary_sector="NIFTY_AUTO",
        valid_from=date(2010, 10, 1),
        valid_to=None,
        aliases=("bajaj auto", "bajaj-auto", "bajaj auto limited"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="BAJAJFINSV",
        company_name="Bajaj Finserv Limited",
        primary_sector="NIFTY_FIN_SERVICE",
        valid_from=date(2018, 9, 28),
        valid_to=None,
        aliases=("bajaj finserv", "bajajfinsv", "bajaj finserv limited"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="BAJFINANCE",
        company_name="Bajaj Finance Limited",
        primary_sector="NIFTY_FIN_SERVICE",
        valid_from=date(2017, 9, 29),
        valid_to=None,
        aliases=("bajaj finance", "bajfinance", "bajaj finance limited"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="BHARTIARTL",
        company_name="Bharti Airtel Limited",
        primary_sector="NIFTY_TELECOM",
        valid_from=date(2004, 4, 1),
        valid_to=None,
        aliases=("bharti airtel", "airtel", "bharti"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="BPCL",
        company_name="Bharat Petroleum Corporation Limited",
        primary_sector="NIFTY_OIL_GAS",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("bharat petroleum", "bpcl", "bharat petroleum corporation"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="BRITANNIA",
        company_name="Britannia Industries Limited",
        primary_sector="NIFTY_FMCG",
        valid_from=date(2019, 4, 1),
        valid_to=None,
        aliases=("britannia", "britannia industries", "britannia industries limited"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="CIPLA",
        company_name="Cipla Limited",
        primary_sector="NIFTY_PHARMA",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("cipla", "cipla limited", "cipla ltd"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="COALINDIA",
        company_name="Coal India Limited",
        primary_sector="NIFTY_METALS",
        valid_from=date(2010, 11, 4),
        valid_to=None,
        aliases=("coal india", "coalindia", "coal india limited", "cil"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="DIVISLAB",
        company_name="Divi's Laboratories Limited",
        primary_sector="NIFTY_PHARMA",
        valid_from=date(2020, 9, 25),
        valid_to=date(2024, 9, 30),            # Exited Sept 30, 2024 (Replaced by BEL)
        aliases=("divis laboratories", "divislab", "divi's laboratories", "divis labs"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="DRREDDY",
        company_name="Dr. Reddy's Laboratories Limited",
        primary_sector="NIFTY_PHARMA",
        valid_from=date(2010, 10, 1),
        valid_to=None,
        aliases=("dr reddy", "dr reddy's", "dr reddys", "drreddy", "dr. reddy's laboratories"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="EICHERMOT",
        company_name="Eicher Motors Limited",
        primary_sector="NIFTY_AUTO",
        valid_from=date(2016, 4, 1),
        valid_to=None,
        aliases=("eicher motors", "eichermot", "royal enfield", "eicher"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="GRASIM",
        company_name="Grasim Industries Limited",
        primary_sector="NIFTY_METALS",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("grasim", "grasim industries", "aditya birla grasim"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="HCLTECH",
        company_name="HCL Technologies Limited",
        primary_sector="NIFTY_IT",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("hcl technologies", "hcl tech", "hcltech", "hcl software"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="HDFC",
        company_name="Housing Development Finance Corporation Limited",
        primary_sector="NIFTY_FIN_SERVICE",
        valid_from=date(2000, 1, 1),
        valid_to=date(2023, 7, 13),            # Exited July 13, 2023 (Amalgamated with HDFCBANK, replaced by LTIM)
        aliases=("housing development finance corporation", "hdfc ltd", "hdfc limited"),
        disambiguation_tokens=("mortgage", "housing development finance", "parent hdfc"),
    ),
    ConstituentRecord(
        symbol="HDFCBANK",
        company_name="HDFC Bank Limited",
        primary_sector="NIFTY_BANK",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("hdfc bank", "hdfcbank", "housing development finance corporation bank"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="HDFCLIFE",
        company_name="HDFC Life Insurance Company Limited",
        primary_sector="NIFTY_FIN_SERVICE",
        valid_from=date(2020, 7, 31),            # Entered July 31, 2020 (Replaced VEDL)
        valid_to=None,
        aliases=("hdfc life", "hdfclife", "hdfc standard life", "hdfc life insurance"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="HEROMOTOCO",
        company_name="Hero MotoCorp Limited",
        primary_sector="NIFTY_AUTO",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("hero motocorp", "heromotoco", "hero honda", "hero motorcorp"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="HINDALCO",
        company_name="Hindalco Industries Limited",
        primary_sector="NIFTY_METALS",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("hindalco", "hindalco industries", "novelis parent"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="HINDUNILVR",
        company_name="Hindustan Unilever Limited",
        primary_sector="NIFTY_FMCG",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("hindustan unilever", "hindunilvr", "hul", "unilever india"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="ICICIBANK",
        company_name="ICICI Bank Limited",
        primary_sector="NIFTY_BANK",
        valid_from=date(2002, 1, 1),
        valid_to=None,
        aliases=("icici bank", "icicibank", "industrial credit and investment corporation"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="INDUSINDBK",
        company_name="IndusInd Bank Limited",
        primary_sector="NIFTY_BANK",
        valid_from=date(2013, 4, 1),
        valid_to=None,
        aliases=("indusind bank", "indusind", "indusindbk", "hinduja bank"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="INFY",
        company_name="Infosys Limited",
        primary_sector="NIFTY_IT",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("infosys", "infy", "infosys technologies"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="IOC",
        company_name="Indian Oil Corporation Limited",
        primary_sector="NIFTY_OIL_GAS",
        valid_from=date(2000, 1, 1),
        valid_to=date(2022, 3, 31),            # Exited March 31, 2022 (Replaced by APOLLOHOSP)
        aliases=("indian oil", "ioc", "iocl", "indian oil corporation"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="ITC",
        company_name="ITC Limited",
        primary_sector="NIFTY_FMCG",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("itc", "itc limited", "imperial tobacco"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="JSWSTEEL",
        company_name="JSW Steel Limited",
        primary_sector="NIFTY_METALS",
        valid_from=date(2018, 9, 28),
        valid_to=None,
        aliases=("jsw steel", "jswsteel", "jindal south west steel"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="KOTAKBANK",
        company_name="Kotak Mahindra Bank Limited",
        primary_sector="NIFTY_BANK",
        valid_from=date(2010, 4, 1),
        valid_to=None,
        aliases=("kotak mahindra bank", "kotak bank", "kotak"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="LT",
        company_name="Larsen & Toubro Limited",
        primary_sector="NIFTY_INFRA",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("larsen & toubro", "l&t", "larsen and toubro", "lt"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="M&M",
        company_name="Mahindra & Mahindra Limited",
        primary_sector="NIFTY_AUTO",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("mahindra & mahindra", "mahindra and mahindra", "m&m", "mahindra automotive"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="MARUTI",
        company_name="Maruti Suzuki India Limited",
        primary_sector="NIFTY_AUTO",
        valid_from=date(2004, 4, 1),
        valid_to=None,
        aliases=("maruti suzuki", "maruti", "maruti udyog"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="NESTLEIND",
        company_name="Nestle India Limited",
        primary_sector="NIFTY_FMCG",
        valid_from=date(2019, 9, 27),
        valid_to=None,
        aliases=("nestle india", "nestleind", "nestle"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="NTPC",
        company_name="NTPC Limited",
        primary_sector="NIFTY_INFRA",
        valid_from=date(2004, 10, 1),
        valid_to=None,
        aliases=("ntpc", "ntpc limited", "national thermal power"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="ONGC",
        company_name="Oil and Natural Gas Corporation Limited",
        primary_sector="NIFTY_OIL_GAS",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("ongc", "oil and natural gas corporation", "oil & natural gas"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="POWERGRID",
        company_name="Power Grid Corporation of India Limited",
        primary_sector="NIFTY_INFRA",
        valid_from=date(2008, 3, 1),
        valid_to=None,
        aliases=("power grid", "powergrid", "pgcil", "power grid corp"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        primary_sector="NIFTY_OIL_GAS",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("reliance", "reliance industries", "ril", "mukesh ambani", "jio platforms"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="SBILIFE",
        company_name="SBI Life Insurance Company Limited",
        primary_sector="NIFTY_FIN_SERVICE",
        valid_from=date(2020, 9, 25),            # Entered Sept 25, 2020
        valid_to=None,
        aliases=("sbi life", "sbilife", "sbi life insurance"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="SBIN",
        company_name="State Bank of India",
        primary_sector="NIFTY_BANK",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("state bank of india", "sbi", "sbin"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="SHREECEM",
        company_name="Shree Cement Limited",
        primary_sector="NIFTY_INFRA",
        valid_from=date(2020, 3, 27),
        valid_to=date(2022, 9, 30),            # Exited Sept 30, 2022 (Replaced by ADANIENT)
        aliases=("shree cement", "shreecem", "shree cements"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="SUNPHARMA",
        company_name="Sun Pharmaceutical Industries Limited",
        primary_sector="NIFTY_PHARMA",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("sun pharma", "sunpharma", "sun pharmaceutical"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="TATACONSUM",
        company_name="Tata Consumer Products Limited",
        primary_sector="NIFTY_FMCG",
        valid_from=date(2021, 3, 31),            # Entered March 31, 2021 (Replaced GAIL)
        valid_to=None,
        aliases=("tata consumer", "tataconsum", "tata consumer products", "tata global beverages"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="TATAMOTORS",
        company_name="Tata Motors Limited",
        primary_sector="NIFTY_AUTO",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("tata motors", "tatamotors", "jlr parent", "tata commercial vehicles"),
        disambiguation_tokens=("motors", "vehicles", "cars", "jlr", "ev"),
    ),
    ConstituentRecord(
        symbol="TATASTEEL",
        company_name="Tata Steel Limited",
        primary_sector="NIFTY_METALS",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("tata steel", "tatasteel", "tisco"),
        disambiguation_tokens=("steel", "metals", "kalinganagar", "port talbot"),
    ),
    ConstituentRecord(
        symbol="TCS",
        company_name="Tata Consultancy Services Limited",
        primary_sector="NIFTY_IT",
        valid_from=date(2004, 8, 25),
        valid_to=None,
        aliases=("tcs", "tata consultancy services", "tata consultancy"),
        disambiguation_tokens=("consultancy", "software", "tcs"),
    ),
    ConstituentRecord(
        symbol="TECHM",
        company_name="Tech Mahindra Limited",
        primary_sector="NIFTY_IT",
        valid_from=date(2014, 3, 28),
        valid_to=None,
        aliases=("tech mahindra", "techm", "tech mahendra"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="TITAN",
        company_name="Titan Company Limited",
        primary_sector="NIFTY_CONSUMPTION",
        valid_from=date(2018, 4, 2),
        valid_to=None,
        aliases=("titan", "titan company", "titan industries", "tanishq"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="ULTRACEMCO",
        company_name="UltraTech Cement Limited",
        primary_sector="NIFTY_INFRA",
        valid_from=date(2012, 9, 28),
        valid_to=None,
        aliases=("ultratech cement", "ultracemco", "ultratech"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="UPL",
        company_name="UPL Limited",
        primary_sector="NIFTY_CHEM",
        valid_from=date(2019, 10, 11),
        valid_to=date(2024, 3, 28),            # Exited March 28, 2024 (Replaced by SHRIRAMFIN)
        aliases=("upl", "upl limited", "united phosphorus"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="WIPRO",
        company_name="Wipro Limited",
        primary_sector="NIFTY_IT",
        valid_from=date(2000, 1, 1),
        valid_to=None,
        aliases=("wipro", "wipro limited", "azim premji wipro"),
        disambiguation_tokens=(),
    ),

    # =========================================================================
    # Subsequent Terminal-Window Entrant Constituents (2022–2026)
    # =========================================================================
    ConstituentRecord(
        symbol="APOLLOHOSP",
        company_name="Apollo Hospitals Enterprise Limited",
        primary_sector="NIFTY_PHARMA",
        valid_from=date(2022, 3, 31),            # Entered March 31, 2022 (Replaced IOC)
        valid_to=None,
        aliases=("apollo hospitals", "apollohosp", "apollo hospitals enterprise"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="ADANIENT",
        company_name="Adani Enterprises Limited",
        primary_sector="NIFTY_METALS",
        valid_from=date(2022, 9, 30),            # Entered Sept 30, 2022 (Replaced SHREECEM)
        valid_to=None,
        aliases=("adani enterprises", "adanient", "adani enterprises limited"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="LTIM",
        company_name="LTIMindtree Limited",
        primary_sector="NIFTY_IT",
        valid_from=date(2023, 7, 13),            # Entered July 13, 2023 (Replaced HDFC post merger)
        valid_to=date(2024, 9, 30),            # Exited Sept 30, 2024 (Replaced by TRENT)
        aliases=("ltimindtree", "ltim", "lti mindtree"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="SHRIRAMFIN",
        company_name="Shriram Finance Limited",
        primary_sector="NIFTY_FIN_SERVICE",
        valid_from=date(2024, 3, 28),            # Entered March 28, 2024 (Replaced UPL)
        valid_to=None,
        aliases=("shriram finance", "shriramfin", "shriram transport finance"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="BEL",
        company_name="Bharat Electronics Limited",
        primary_sector="NIFTY_INFRA",
        valid_from=date(2024, 9, 30),            # Entered Sept 30, 2024 (Replaced DIVISLAB)
        valid_to=None,
        aliases=("bharat electronics", "bel", "bharat electronics limited"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="TRENT",
        company_name="Trent Limited",
        primary_sector="NIFTY_CONSUMPTION",
        valid_from=date(2024, 9, 30),            # Entered Sept 30, 2024 (Replaced LTIM)
        valid_to=None,
        aliases=("trent", "trent limited", "westside", "zudio"),
        disambiguation_tokens=(),
    ),

    # =========================================================================
    # Historical Pre-2022 Exited Constituents (Anti-Survivorship Bias)
    # =========================================================================
    ConstituentRecord(
        symbol="YESBANK",
        company_name="Yes Bank Limited",
        primary_sector="NIFTY_BANK",
        valid_from=date(2015, 3, 27),
        valid_to=date(2020, 3, 27),            # Exited March 27, 2020 (Replaced by SHREECEM)
        aliases=("yes bank", "yesbank", "rana kapoor bank"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="INFRATEL",
        company_name="Bharti Infratel Limited",
        primary_sector="NIFTY_TELECOM",
        valid_from=date(2016, 4, 1),
        valid_to=date(2020, 9, 25),            # Exited Sept 25, 2020 (Replaced by SBILIFE)
        aliases=("bharti infratel", "infratel", "indus towers"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="VEDL",
        company_name="Vedanta Limited",
        primary_sector="NIFTY_METALS",
        valid_from=date(2010, 10, 1),
        valid_to=date(2020, 7, 31),            # Exited July 31, 2020 (Voluntary delisting, replaced by HDFCLIFE)
        aliases=("vedanta", "vedl", "sesa goa", "sterlite industries"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="ZEEL",
        company_name="Zee Entertainment Enterprises Limited",
        primary_sector="NIFTY_MEDIA",
        valid_from=date(2015, 3, 27),
        valid_to=date(2020, 9, 25),            # Exited Sept 25, 2020 (Replaced by DIVISLAB)
        aliases=("zee entertainment", "zeel", "zee", "subhash chandra zee"),
        disambiguation_tokens=(),
    ),
    ConstituentRecord(
        symbol="GAIL",
        company_name="GAIL (India) Limited",
        primary_sector="NIFTY_OIL_GAS",
        valid_from=date(2000, 1, 1),
        valid_to=date(2021, 3, 31),            # Exited March 31, 2021 (Replaced by TATACONSUM)
        aliases=("gail", "gail india", "gas authority of india"),
        disambiguation_tokens=(),
    ),
]


def is_active_nifty_constituent(symbol: str, target_date: date) -> bool:
    """Check if an equity symbol was an active member of NIFTY 50 on target_date."""
    for c in CANONICAL_CONSTITUENTS:
        if c.symbol.upper() == symbol.upper():
            if c.valid_from <= target_date:
                if c.valid_to is None or target_date <= c.valid_to:
                    return True
    return False


def get_active_nifty_constituents(target_date: date) -> List[ConstituentRecord]:
    """Return all constituent records active on target_date."""
    active = []
    for c in CANONICAL_CONSTITUENTS:
        if c.valid_from <= target_date:
            if c.valid_to is None or target_date <= c.valid_to:
                active.append(c)
    return active


def get_constituent_sector(symbol: str) -> Optional[str]:
    """Retrieve primary sector for an equity symbol."""
    for c in CANONICAL_CONSTITUENTS:
        if c.symbol.upper() == symbol.upper():
            return c.primary_sector
    return None


__all__ = [
    "ConstituentRecord",
    "CANONICAL_CONSTITUENTS",
    "NSE_SECTOR_TAXONOMY",
    "is_active_nifty_constituent",
    "get_active_nifty_constituents",
    "get_constituent_sector",
]
