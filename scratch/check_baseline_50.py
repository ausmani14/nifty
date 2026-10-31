# Reconstruct all constituents active on 2022-01-01 based strictly on repository documentation

# 1. From PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md (77 table)
with open('docs/PHASE_8_HISTORICAL_CONSTITUENT_AND_PIT_AUDIT_REPORT.md', encoding='utf-8') as f:
    lines = f.readlines()

table_lines = [l.strip() for l in lines[43:121] if l.strip().startswith('|')]

p8_active_2022 = {}
for l in table_lines:
    parts = [p.strip() for p in l.split('|')[1:-1]]
    if len(parts) >= 6:
        sym = parts[0]
        name = parts[1]
        m_start = parts[3]
        m_end = parts[4]
        if m_end == 'Active' or m_end >= '2022-01-01':
            p8_active_2022[sym] = (name, m_start, m_end)

print(f"Count from 77-table active on 2022-01-01: {len(p8_active_2022)}")

# 2. Add HEROMOTOCO (documented in PHASE_8_COMPLETE_NIFTY_50_COVERAGE_REPORT.md and line 137 of audit report)
p8_active_2022['HEROMOTOCO'] = ('Hero MotoCorp Limited', '2000-01-01', 'Active')

# 3. Add HDFC (documented in src/nifty_ai/data/news/constituents.py and PHASE_9_PIT_REGISTRY_2022_2026_IMPLEMENTATION_REPORT.md)
p8_active_2022['HDFC'] = ('Housing Development Finance Corporation Limited', '2000-01-01', '2023-07-13')

print(f"Total documented active constituents on 2022-01-01: {len(p8_active_2022)}")
for idx, (sym, (name, s, e)) in enumerate(sorted(p8_active_2022.items()), 1):
    print(f"{idx:2d}. {sym:12s} | {name:40s} | {s} to {e}")
