from datetime import date
from nifty_ai.data.news.constituents import CANONICAL_CONSTITUENTS

WINDOW_START = date(2022, 1, 1)
WINDOW_END = date(2026, 9, 4)
YEARS = [2022, 2023, 2024, 2025, 2026]

queries = []
for c in CANONICAL_CONSTITUENTS:
    if c.valid_from > WINDOW_END:
        continue
    if c.valid_to is not None and c.valid_to < WINDOW_START:
        continue

    c_start = max(c.valid_from, WINDOW_START)
    c_end = min(c.valid_to or WINDOW_END, WINDOW_END)

    for y in YEARS:
        y_start = date(y, 1, 1)
        y_end = min(date(y, 12, 31), WINDOW_END)

        q_from = max(c_start, y_start)
        q_to = min(c_end, y_end)

        if q_from <= q_to:
            queries.append({
                'symbol': c.symbol,
                'year': y,
                'from_date': q_from,
                'to_date': q_to,
            })

unique_syms = sorted(list(set(q['symbol'] for q in queries)))
print(f"Total queries planned: {len(queries)}")
print(f"Unique constituents to query: {len(unique_syms)}")
print(f"Is LICI in queries? {'LICI' in unique_syms}")
print(f"Is HDFCLIFE in queries? {'HDFCLIFE' in unique_syms}")

# Check query breakdown per constituent
print("\nSample queries:")
for q in queries[:10]:
    print(f"  {q['symbol']} ({q['year']}): {q['from_date']} to {q['to_date']}")

# Check boundary constituents
for sym in ['IOC', 'SHREECEM', 'HDFC', 'UPL', 'DIVISLAB', 'LTIM', 'APOLLOHOSP', 'ADANIENT', 'SHRIRAMFIN', 'BEL', 'TRENT']:
    sym_qs = [q for q in queries if q['symbol'] == sym]
    print(f"{sym:12s}: {len(sym_qs)} queries -> {[(q['year'], str(q['from_date']), str(q['to_date'])) for q in sym_qs]}")
