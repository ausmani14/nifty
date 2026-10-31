# LIVE DATA SOURCE AUDIT
## Point-in-Time Availability, Licensing & Free-Tier Operational Constraints

**Phase**: Master Cloud Implementation — Phase 6  
**Date**: October 31, 2026  
**Auditor**: Financial Data Integrity Engineer & Senior ML Engineer  
**System**: NIFTY AI Snapshot B (08:50:00 IST Cutoff)  
**Governance Policy**: **Strict Fail-Closed (Zero Fabrication / Zero Lookahead)**  

---

## 1. Executive Summary

This audit assesses the data sources required to construct the canonical 63-feature input vector for the frozen Snapshot B $T0$ production model at **08:50:00 Asia/Kolkata** on each trading day.

Under strict research governance:
- **No data fabrication**: If any source is missing, stale, or unavailable by 08:50:00 IST, the pipeline reports `DATA_SOURCE_BLOCKED` or `INSUFFICIENT_ELIGIBLE_FEATURES`. It **never** fabricates proxy values.
- **No paid API dependency**: Operations rely on free public endpoints and exchange daily publications.
- **Point-in-Time Enforcement**: Only information finalized and available strictly before 08:50:00 IST is eligible.

---

## 2. Inventory of Required Instruments & Fields

The 63 canonical features require:
- **NIFTY 50 Daily Cash OHLC** (45 price features derived from historical sessions through Day $T-1$).
- **18 Market-Context Variables** (derived from 16 underlying instruments finalized prior to 08:50 IST).

### Context Instruments & Availability Timing

| Variable Name | Canonical Ticker | Market / Exchange | Close / Finalization Time (IST) | Availability Lag | 08:50 IST Usability |
|---|---|---|---|---|---|
| `NIFTY_BANK` | `^NSEBANK` | NSE (India) | Day $T-1$ 15:30 IST | +0 min | Finalized (Day $T-1$) |
| `SP500` | `^GSPC` | US (NYSE/Nasdaq) | Day $T-1$ 01:30–02:30 IST (Day $T$) | +30 min | Finalized prior to 08:50 IST |
| `NASDAQ` | `^IXIC` | US (Nasdaq) | Day $T-1$ 01:30–02:30 IST (Day $T$) | +30 min | Finalized prior to 08:50 IST |
| `DOW_JONES` | `^DJI` | US (NYSE) | Day $T-1$ 01:30–02:30 IST (Day $T$) | +30 min | Finalized prior to 08:50 IST |
| `BRENT_CRUDE` | `BZ=F` | ICE / NYMEX | Day $T-1$ 03:00 IST (Day $T$) | +15 min | Finalized prior to 08:50 IST |
| `WTI_CRUDE` | `CL=F` | NYMEX | Day $T-1$ 02:00 IST (Day $T$) | +15 min | Finalized prior to 08:50 IST |
| `GOLD` | `GC=F` | COMEX | Day $T-1$ 02:00 IST (Day $T$) | +15 min | Finalized prior to 08:50 IST |
| `DXY` | `DX-Y.NYB` | ICE | Day $T-1$ 02:30 IST (Day $T$) | +15 min | Finalized prior to 08:50 IST |
| `NIKKEI_225` | `^N225` | TSE (Tokyo) | Day $T$ Morning Session (opens 05:30 IST) | Day $T-1$ Close | Day $T-1$ Close finalized; Day $T$ AM level checkable |
| `HANG_SENG` | `^HSI` | HKEX (Hong Kong) | Opens 06:45 IST | Day $T-1$ Close | Day $T-1$ Close finalized |
| `FTSE_100` | `^FTSE` | LSE (London) | Day $T-1$ 21:00 IST | +15 min | Finalized (Day $T-1$) |
| `INDIA_VIX` | `^INDIAVIX` | NSE (India) | Day $T-1$ 15:30 IST | +0 min | Finalized (Day $T-1$) |
| `US_VIX` | `^VIX` | CBOE (US) | Day $T-1$ 01:45 IST (Day $T$) | +15 min | Finalized prior to 08:50 IST |
| `INDIA_10Y_YIELD` | `IN10YT=RR` | RBI / CCIL (India) | Day $T-1$ 17:00 IST | +30 min | Finalized (Day $T-1$) |
| `US_10Y_YIELD` | `^TNX` | CBOE / US Treasury | Day $T-1$ 02:30 IST (Day $T$) | +15 min | Finalized prior to 08:50 IST |
| `USD_INR` | `INR=X` | Forex (Interbank) | 24h continuous | Snapshot at 08:45 IST | Available |

---

## 3. Free Provider Evaluation & Licensing Limitations

### 1. Yahoo Finance Public Chart API
- **Tier**: Free / Unauthenticated.
- **Latency / Freshness**: 15–20 minute delayed quotes for live intraday sessions; finalized daily candles available after market close.
- **Reliability**: Reasonable for Day $T-1$ completed daily bars; rate limits apply under aggressive scraping.
- **Licensing**: For personal/research evaluation only. Redistribution prohibited.

### 2. NSE Daily Official Bhavcopy / Archives
- **Tier**: Free public files published after 18:30 IST daily.
- **Reliability**: 100% authoritative for realized settlement Open and Close.
- **Timing**: Available post-market for outcome reconciliation; not a real-time pre-market feed.

---

## 4. Operational Fallback Strategy (Fail-Closed)

If automated market data capture fails or is blocked during morning execution (e.g. rate limit, network timeout, holiday):
1. **Never fabricate proxy or average values**.
2. **Never backdate retrospective values**.
3. Output machine-readable status:
   `status = "DATA_SOURCE_BLOCKED"`
4. Record the blocking reason in `validation_reports/` and `website_data/system_status.json`.
5. Allow operator to supply verified point-in-time input via `--input-file <PATH>` before 08:50:00 IST.
