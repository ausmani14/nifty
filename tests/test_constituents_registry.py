"""Automated Verification and Integrity Tests for NIFTY 50 PIT Constituent Registry.

Phase 9 Reconstitution and Anti-Survivorship Bias Validation:
- Validates interval chronology (valid_from < valid_to).
- Validates non-overlapping intervals for identical symbols.
- Enforces strict point-in-time membership boundaries (entry/exit).
- Enforces exact 50-member baseline on 2022-01-01.
- Enforces exact 56 unique companies across 2022–2026 terminal out-of-sample window.
- Verifies complete absence of LICI from NIFTY 50 registry.
- Verifies exact historical exit dates (VEDL 2020-07-31, ZEEL 2020-09-25, GAIL 2021-03-31).
- Verifies zero backfill of modern constituents into pre-inclusion eras.
- Verifies sector taxonomy completeness.
"""

from datetime import date
from collections import defaultdict
import pytest

from nifty_ai.data.news.constituents import (
    CANONICAL_CONSTITUENTS,
    NSE_SECTOR_TAXONOMY,
    get_active_nifty_constituents,
    get_constituent_sector,
    is_active_nifty_constituent,
)

# Authoritative 50 baseline symbols active on 2022-01-01
AUTHORITATIVE_BASELINE_50 = {
    "ADANIPORTS", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV",
    "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA",
    "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM",
    "HCLTECH", "HDFC", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO",
    "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY",
    "IOC", "ITC", "JSWSTEEL", "KOTAKBANK", "LT",
    "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
    "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SHREECEM",
    "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS",
    "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"
}


def test_registry_interval_chronology():
    """Verify valid_from < valid_to for all bounded constituents."""
    for c in CANONICAL_CONSTITUENTS:
        if c.valid_to is not None:
            assert c.valid_from < c.valid_to, f"{c.symbol} has invalid interval: {c.valid_from} >= {c.valid_to}"


def test_registry_no_overlapping_intervals_per_symbol():
    """Verify that multiple records for the same symbol do not have overlapping active intervals."""
    symbol_intervals = defaultdict(list)
    for c in CANONICAL_CONSTITUENTS:
        symbol_intervals[c.symbol.upper()].append((c.valid_from, c.valid_to or date(9999, 12, 31)))

    for sym, intervals in symbol_intervals.items():
        if len(intervals) > 1:
            sorted_intervals = sorted(intervals, key=lambda x: x[0])
            for i in range(len(sorted_intervals) - 1):
                cur_start, cur_end = sorted_intervals[i]
                next_start, next_end = sorted_intervals[i + 1]
                assert cur_end < next_start, f"Overlap detected for {sym}: [{cur_start}, {cur_end}] and [{next_start}, {next_end}]"


def test_baseline_50_constituents_on_2022_01_01():
    """Verify exactly 50 constituents are active on 2022-01-01 and match authoritative set."""
    active_recs = get_active_nifty_constituents(date(2022, 1, 1))
    active_symbols = {c.symbol.upper() for c in active_recs}

    assert len(active_symbols) == 50, f"Expected 50 active symbols, found {len(active_symbols)}"
    assert active_symbols == AUTHORITATIVE_BASELINE_50, (
        f"Baseline symbols mismatch. Missing: {AUTHORITATIVE_BASELINE_50 - active_symbols}, "
        f"Extra: {active_symbols - AUTHORITATIVE_BASELINE_50}"
    )


def test_terminal_unique_universe_count_56():
    """Verify exactly 56 unique symbols occur in 2022-01-01 to 2026-09-04 PIT universe."""
    start_dt = date(2022, 1, 1)
    end_dt = date(2026, 9, 4)
    terminal_universe = set()
    for c in CANONICAL_CONSTITUENTS:
        if c.valid_from <= end_dt:
            if c.valid_to is None or c.valid_to >= start_dt:
                terminal_universe.add(c.symbol.upper())

    expected_56 = AUTHORITATIVE_BASELINE_50.union({
        "APOLLOHOSP", "ADANIENT", "LTIM", "SHRIRAMFIN", "BEL", "TRENT"
    })
    assert len(terminal_universe) == 56, f"Expected 56 terminal constituents, found {len(terminal_universe)}"
    assert terminal_universe == expected_56, (
        f"Terminal universe mismatch. Missing: {expected_56 - terminal_universe}, "
        f"Extra: {terminal_universe - expected_56}"
    )


def test_complete_absence_of_lici():
    """Verify LICI is completely absent from NIFTY 50 canonical registry."""
    all_symbols = {c.symbol.upper() for c in CANONICAL_CONSTITUENTS}
    assert "LICI" not in all_symbols, "Defect: LICI must not exist in NIFTY 50 registry!"


def test_hdfclife_and_vedl_reconstitution():
    """Verify HDFCLIFE inclusion and VEDL exclusion on 2020-07-31."""
    # VEDL exited 2020-07-31
    assert is_active_nifty_constituent("VEDL", date(2020, 7, 31)) is True
    assert is_active_nifty_constituent("VEDL", date(2020, 8, 1)) is False
    assert is_active_nifty_constituent("VEDL", date(2022, 1, 1)) is False

    # HDFCLIFE entered 2020-07-31
    assert is_active_nifty_constituent("HDFCLIFE", date(2020, 7, 30)) is False
    assert is_active_nifty_constituent("HDFCLIFE", date(2020, 7, 31)) is True
    assert is_active_nifty_constituent("HDFCLIFE", date(2022, 1, 1)) is True
    assert is_active_nifty_constituent("HDFCLIFE", date(2026, 9, 4)) is True


def test_zeel_and_gail_historical_exits():
    """Verify ZEEL and GAIL exit dates."""
    # ZEEL exited 2020-09-25
    assert is_active_nifty_constituent("ZEEL", date(2020, 9, 25)) is True
    assert is_active_nifty_constituent("ZEEL", date(2020, 9, 26)) is False
    assert is_active_nifty_constituent("ZEEL", date(2022, 1, 1)) is False

    # GAIL exited 2021-03-31
    assert is_active_nifty_constituent("GAIL", date(2021, 3, 31)) is True
    assert is_active_nifty_constituent("GAIL", date(2021, 4, 1)) is False
    assert is_active_nifty_constituent("GAIL", date(2022, 1, 1)) is False
    assert is_active_nifty_constituent("GAIL", date(2022, 3, 31)) is False

    # TATACONSUM entered 2021-03-31
    assert is_active_nifty_constituent("TATACONSUM", date(2021, 3, 30)) is False
    assert is_active_nifty_constituent("TATACONSUM", date(2021, 3, 31)) is True
    assert is_active_nifty_constituent("TATACONSUM", date(2022, 1, 1)) is True


def test_2022_2026_reconstitution_boundaries():
    """Verify exact entry and exit boundaries for 2022–2026 reconstitutions."""
    # 1. IOC: Exited 2022-03-31
    assert is_active_nifty_constituent("IOC", date(2021, 12, 31)) is True
    assert is_active_nifty_constituent("IOC", date(2022, 3, 31)) is True
    assert is_active_nifty_constituent("IOC", date(2022, 4, 1)) is False

    # 2. SHREECEM: Exited 2022-09-30
    assert is_active_nifty_constituent("SHREECEM", date(2021, 1, 1)) is True
    assert is_active_nifty_constituent("SHREECEM", date(2022, 9, 30)) is True
    assert is_active_nifty_constituent("SHREECEM", date(2022, 10, 1)) is False

    # 3. HDFC: Exited 2023-07-13
    assert is_active_nifty_constituent("HDFC", date(2022, 1, 1)) is True
    assert is_active_nifty_constituent("HDFC", date(2023, 7, 13)) is True
    assert is_active_nifty_constituent("HDFC", date(2023, 7, 14)) is False

    # 4. UPL: Exited 2024-03-28
    assert is_active_nifty_constituent("UPL", date(2023, 1, 1)) is True
    assert is_active_nifty_constituent("UPL", date(2024, 3, 28)) is True
    assert is_active_nifty_constituent("UPL", date(2024, 3, 29)) is False

    # 5. DIVISLAB: Exited 2024-09-30
    assert is_active_nifty_constituent("DIVISLAB", date(2022, 1, 1)) is True
    assert is_active_nifty_constituent("DIVISLAB", date(2024, 9, 30)) is True
    assert is_active_nifty_constituent("DIVISLAB", date(2024, 10, 1)) is False

    # 6. LTIM: Active 2023-07-13 to 2024-09-30
    assert is_active_nifty_constituent("LTIM", date(2023, 7, 12)) is False
    assert is_active_nifty_constituent("LTIM", date(2023, 7, 13)) is True
    assert is_active_nifty_constituent("LTIM", date(2024, 9, 30)) is True
    assert is_active_nifty_constituent("LTIM", date(2024, 10, 1)) is False

    # 7. APOLLOHOSP: Entered 2022-03-31
    assert is_active_nifty_constituent("APOLLOHOSP", date(2022, 3, 30)) is False
    assert is_active_nifty_constituent("APOLLOHOSP", date(2022, 3, 31)) is True
    assert is_active_nifty_constituent("APOLLOHOSP", date(2026, 9, 4)) is True

    # 8. ADANIENT: Entered 2022-09-30
    assert is_active_nifty_constituent("ADANIENT", date(2022, 9, 29)) is False
    assert is_active_nifty_constituent("ADANIENT", date(2022, 9, 30)) is True
    assert is_active_nifty_constituent("ADANIENT", date(2026, 9, 4)) is True

    # 9. SHRIRAMFIN: Entered 2024-03-28
    assert is_active_nifty_constituent("SHRIRAMFIN", date(2024, 3, 27)) is False
    assert is_active_nifty_constituent("SHRIRAMFIN", date(2024, 3, 28)) is True
    assert is_active_nifty_constituent("SHRIRAMFIN", date(2026, 9, 4)) is True

    # 10. BEL: Entered 2024-09-30
    assert is_active_nifty_constituent("BEL", date(2024, 9, 29)) is False
    assert is_active_nifty_constituent("BEL", date(2024, 9, 30)) is True
    assert is_active_nifty_constituent("BEL", date(2026, 9, 4)) is True

    # 11. TRENT: Entered 2024-09-30
    assert is_active_nifty_constituent("TRENT", date(2024, 9, 29)) is False
    assert is_active_nifty_constituent("TRENT", date(2024, 9, 30)) is True
    assert is_active_nifty_constituent("TRENT", date(2026, 9, 4)) is True


def test_no_pre_entry_backfill_into_historical_development_era():
    """Verify new entrants are strictly inactive on 2021-12-31 (development boundary)."""
    dev_boundary = date(2021, 12, 31)
    new_entrants = ["APOLLOHOSP", "ADANIENT", "LTIM", "SHRIRAMFIN", "BEL", "TRENT"]
    for sym in new_entrants:
        assert is_active_nifty_constituent(sym, dev_boundary) is False, (
            f"LEAKAGE/BACKFILL: {sym} evaluated as active during historical development era ({dev_boundary})!"
        )


def test_sector_taxonomy_completeness():
    """Verify all constituents map to a registered sector in NSE_SECTOR_TAXONOMY."""
    for c in CANONICAL_CONSTITUENTS:
        sec = get_constituent_sector(c.symbol)
        assert sec is not None, f"No sector returned for {c.symbol}"
        assert sec in NSE_SECTOR_TAXONOMY, f"Sector {sec} for {c.symbol} is not defined in NSE_SECTOR_TAXONOMY"
