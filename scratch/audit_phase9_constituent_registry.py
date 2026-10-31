"""Deterministic Verification and Audit for Reconciled NIFTY 50 PIT Constituent Registry.

Phase 9 Step 2D Audit Script.
Validates all 18 invariants specified by the quantitative audit mandate.
"""

import sys
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Set

from nifty_ai.data.news.constituents import (
    CANONICAL_CONSTITUENTS,
    NSE_SECTOR_TAXONOMY,
    get_active_nifty_constituents,
    get_constituent_sector,
    is_active_nifty_constituent,
)

# Authoritative 50 baseline symbols active on 2022-01-01
AUTHORITATIVE_BASELINE_50: Set[str] = {
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


def audit_registry() -> bool:
    all_passed = True
    print("=" * 80)
    print("NIFTY AI — PHASE 9 STEP 2D CONSTITUENT REGISTRY AUDIT")
    print("=" * 80)

    # 1. Exactly 50 symbols are active on 2022-01-01
    baseline_active = get_active_nifty_constituents(date(2022, 1, 1))
    baseline_symbols = {c.symbol.upper() for c in baseline_active}
    check1 = len(baseline_symbols) == 50
    print(f"[{'PASS' if check1 else 'FAIL'}] 1. Exactly 50 symbols active on 2022-01-01: count = {len(baseline_symbols)}")
    if not check1:
        all_passed = False

    # 2. Exactly 56 unique symbols occur anywhere in 2022-01-01 through 2026-09-04 PIT universe
    start_dt = date(2022, 1, 1)
    end_dt = date(2026, 9, 4)
    terminal_universe: Set[str] = set()
    for c in CANONICAL_CONSTITUENTS:
        if c.valid_from <= end_dt:
            if c.valid_to is None or c.valid_to >= start_dt:
                terminal_universe.add(c.symbol.upper())

    check2 = len(terminal_universe) == 56
    print(f"[{'PASS' if check2 else 'FAIL'}] 2. Exactly 56 unique symbols in 2022-2026 PIT universe: count = {len(terminal_universe)}")
    if not check2:
        all_passed = False

    # 3. HDFCLIFE is active on 2022-01-01
    check3 = is_active_nifty_constituent("HDFCLIFE", date(2022, 1, 1))
    print(f"[{'PASS' if check3 else 'FAIL'}] 3. HDFCLIFE is active on 2022-01-01: {check3}")
    if not check3:
        all_passed = False

    # 4. LICI is absent
    all_registry_symbols = {c.symbol.upper() for c in CANONICAL_CONSTITUENTS}
    check4 = "LICI" not in all_registry_symbols
    print(f"[{'PASS' if check4 else 'FAIL'}] 4. LICI is completely absent from registry: {check4}")
    if not check4:
        all_passed = False

    # 5. VEDL is inactive after 2020-07-31
    check5_active_on_exit = is_active_nifty_constituent("VEDL", date(2020, 7, 31))
    check5_inactive_after = not is_active_nifty_constituent("VEDL", date(2020, 8, 1))
    check5 = check5_active_on_exit and check5_inactive_after
    print(f"[{'PASS' if check5 else 'FAIL'}] 5. VEDL inactive after 2020-07-31: active on exit = {check5_active_on_exit}, inactive after = {check5_inactive_after}")
    if not check5:
        all_passed = False

    # 6. ZEEL is inactive after 2020-09-25
    check6_active_on_exit = is_active_nifty_constituent("ZEEL", date(2020, 9, 25))
    check6_inactive_after = not is_active_nifty_constituent("ZEEL", date(2020, 9, 26))
    check6 = check6_active_on_exit and check6_inactive_after
    print(f"[{'PASS' if check6 else 'FAIL'}] 6. ZEEL inactive after 2020-09-25: active on exit = {check6_active_on_exit}, inactive after = {check6_inactive_after}")
    if not check6:
        all_passed = False

    # 7. GAIL is inactive after 2022-03-31
    check7_2021 = not is_active_nifty_constituent("GAIL", date(2021, 4, 1))
    check7_2022 = not is_active_nifty_constituent("GAIL", date(2022, 4, 1))
    check7 = check7_2021 and check7_2022
    print(f"[{'PASS' if check7 else 'FAIL'}] 7. GAIL is inactive after 2022-03-31 (and 2021-03-31): {check7}")
    if not check7:
        all_passed = False

    # 8. TATACONSUM is active from 2021-03-31
    check8_before = not is_active_nifty_constituent("TATACONSUM", date(2021, 3, 30))
    check8_on = is_active_nifty_constituent("TATACONSUM", date(2021, 3, 31))
    check8 = check8_before and check8_on
    print(f"[{'PASS' if check8 else 'FAIL'}] 8. TATACONSUM active from 2021-03-31: before = {not check8_before}, on = {check8_on}")
    if not check8:
        all_passed = False

    # 9. APOLLOHOSP begins 2022-03-31
    check9_before = not is_active_nifty_constituent("APOLLOHOSP", date(2022, 3, 30))
    check9_on = is_active_nifty_constituent("APOLLOHOSP", date(2022, 3, 31))
    check9 = check9_before and check9_on
    print(f"[{'PASS' if check9 else 'FAIL'}] 9. APOLLOHOSP begins 2022-03-31: before = {not check9_before}, on = {check9_on}")
    if not check9:
        all_passed = False

    # 10. ADANIENT begins 2022-09-30
    check10_before = not is_active_nifty_constituent("ADANIENT", date(2022, 9, 29))
    check10_on = is_active_nifty_constituent("ADANIENT", date(2022, 9, 30))
    check10 = check10_before and check10_on
    print(f"[{'PASS' if check10 else 'FAIL'}] 10. ADANIENT begins 2022-09-30: before = {not check10_before}, on = {check10_on}")
    if not check10:
        all_passed = False

    # 11. LTIM begins 2023-07-13 and ends 2024-09-30
    check11_before = not is_active_nifty_constituent("LTIM", date(2023, 7, 12))
    check11_on_start = is_active_nifty_constituent("LTIM", date(2023, 7, 13))
    check11_on_end = is_active_nifty_constituent("LTIM", date(2024, 9, 30))
    check11_after = not is_active_nifty_constituent("LTIM", date(2024, 10, 1))
    check11 = check11_before and check11_on_start and check11_on_end and check11_after
    print(f"[{'PASS' if check11 else 'FAIL'}] 11. LTIM begins 2023-07-13 and ends 2024-09-30: {check11}")
    if not check11:
        all_passed = False

    # 12. SHRIRAMFIN begins 2024-03-28
    check12_before = not is_active_nifty_constituent("SHRIRAMFIN", date(2024, 3, 27))
    check12_on = is_active_nifty_constituent("SHRIRAMFIN", date(2024, 3, 28))
    check12 = check12_before and check12_on
    print(f"[{'PASS' if check12 else 'FAIL'}] 12. SHRIRAMFIN begins 2024-03-28: before = {not check12_before}, on = {check12_on}")
    if not check12:
        all_passed = False

    # 13. BEL begins 2024-09-30
    check13_before = not is_active_nifty_constituent("BEL", date(2024, 9, 29))
    check13_on = is_active_nifty_constituent("BEL", date(2024, 9, 30))
    check13 = check13_before and check13_on
    print(f"[{'PASS' if check13 else 'FAIL'}] 13. BEL begins 2024-09-30: before = {not check13_before}, on = {check13_on}")
    if not check13:
        all_passed = False

    # 14. TRENT begins 2024-09-30
    check14_before = not is_active_nifty_constituent("TRENT", date(2024, 9, 29))
    check14_on = is_active_nifty_constituent("TRENT", date(2024, 9, 30))
    check14 = check14_before and check14_on
    print(f"[{'PASS' if check14 else 'FAIL'}] 14. TRENT begins 2024-09-30: before = {not check14_before}, on = {check14_on}")
    if not check14:
        all_passed = False

    # 15. No symbol has overlapping validity intervals
    symbol_intervals = defaultdict(list)
    for c in CANONICAL_CONSTITUENTS:
        symbol_intervals[c.symbol.upper()].append((c.valid_from, c.valid_to or date(9999, 12, 31)))

    has_overlap = False
    for sym, intervals in symbol_intervals.items():
        if len(intervals) > 1:
            sorted_intervals = sorted(intervals, key=lambda x: x[0])
            for i in range(len(sorted_intervals) - 1):
                cur_start, cur_end = sorted_intervals[i]
                next_start, next_end = sorted_intervals[i + 1]
                if cur_end >= next_start:
                    has_overlap = True
                    print(f"    OVERLAP in {sym}: [{cur_start}, {cur_end}] and [{next_start}, {next_end}]")

    check15 = not has_overlap
    print(f"[{'PASS' if check15 else 'FAIL'}] 15. No symbol has overlapping validity intervals: {check15}")
    if not check15:
        all_passed = False

    # 16. No duplicate active symbols at the same PIT date
    # Check sample key dates across the full window
    sample_dates = [
        date(2020, 1, 1), date(2020, 7, 31), date(2020, 9, 25),
        date(2021, 3, 31), date(2022, 1, 1), date(2022, 3, 31),
        date(2022, 9, 30), date(2023, 7, 13), date(2024, 3, 28),
        date(2024, 9, 30), date(2026, 9, 4),
    ]
    duplicate_found = False
    for d in sample_dates:
        active = get_active_nifty_constituents(d)
        sym_list = [c.symbol.upper() for c in active]
        if len(sym_list) != len(set(sym_list)):
            duplicate_found = True
            print(f"    DUPLICATE symbols on {d}: {[s for s in sym_list if sym_list.count(s) > 1]}")

    check16 = not duplicate_found
    print(f"[{'PASS' if check16 else 'FAIL'}] 16. No duplicate active symbols at same PIT date: {check16}")
    if not check16:
        all_passed = False

    # 17. Baseline list matches the 50-symbol authoritative list exactly
    missing_baseline = AUTHORITATIVE_BASELINE_50 - baseline_symbols
    extra_baseline = baseline_symbols - AUTHORITATIVE_BASELINE_50
    check17 = len(missing_baseline) == 0 and len(extra_baseline) == 0
    print(f"[{'PASS' if check17 else 'FAIL'}] 17. Baseline list matches 50-symbol authoritative set exactly:")
    print(f"    Missing: {missing_baseline if missing_baseline else 'None'}")
    print(f"    Extra:   {extra_baseline if extra_baseline else 'None'}")
    if not check17:
        all_passed = False

    # 18. Terminal unique-company count is exactly 56
    expected_terminal_56 = AUTHORITATIVE_BASELINE_50.union({
        "APOLLOHOSP", "ADANIENT", "LTIM", "SHRIRAMFIN", "BEL", "TRENT"
    })
    missing_terminal = expected_terminal_56 - terminal_universe
    extra_terminal = terminal_universe - expected_terminal_56
    check18 = len(terminal_universe) == 56 and len(missing_terminal) == 0 and len(extra_terminal) == 0
    print(f"[{'PASS' if check18 else 'FAIL'}] 18. Terminal unique-company count is exactly 56 and matches expected set:")
    print(f"    Missing: {missing_terminal if missing_terminal else 'None'}")
    print(f"    Extra:   {extra_terminal if extra_terminal else 'None'}")
    if not check18:
        all_passed = False

    print("=" * 80)
    print(f"FINAL AUDIT RESULT: {'ALL 18 INVARIANTS PASSED' if all_passed else 'AUDIT FAILED'}")
    print("=" * 80)
    return all_passed


if __name__ == "__main__":
    success = audit_registry()
    sys.exit(0 if success else 1)
