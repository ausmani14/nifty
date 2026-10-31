# DATA AVAILABILITY MATRIX

## Overview
This document defines the strict publication schedules, observation times, and Snapshot availability contracts
for all 16 Indian and Global market context variables in NIFTY AI.

### Provenance Classification Notice
> [!IMPORTANT]
> **ALL 16 variables are classified as `assumed_schedule`** because Yahoo Finance (free tier) does not
> provide historical publication timestamps. The availability timestamp represents an explicit conservative
> modeling assumption (`instrument_close_time + lag_minutes_to_availability`) used as a proxy for provider
> availability. Historical Yahoo publication timing is not empirically verified.
> For production deployment with direct exchange or institutional feeds, these assumptions should be replaced
> with verified provider-specific publication timestamps.

### Cutoff Timing Definitions
- **Snapshot A Cutoff:** `15:30 IST` on Session `T` (prediction emitted at `15:40 IST`).
- **Snapshot B Cutoff:** `08:50 IST` on Session `T+1` (prediction emitted at `08:50 IST`).

### Assumption-Dependent Boundary Cases
> [!WARNING]
> **INDIA_VIX, NIFTY_BANK, and USD_INR** finalize at/near `15:30 IST`, exactly matching the Snapshot A cutoff.
> Their Snapshot A eligibility is based on an **explicit conservative modeling assumption** that the provider
> value is accessible at instrument finalization. Because historical Yahoo publication timestamps are unobserved,
> this boundary condition is NOT empirically verified. It is classified as an assumption-dependent development-data rule.

| Variable | Symbol | Native TZ | Close Time | Avail Timestamp (IST) | Timestamp Type | Snap A Usable? | Snap B Usable? | Missing Policy | Known Assumptions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `INDIA_VIX` | `^INDIAVIX` | `Asia/Kolkata` | 15:30 local | 15:30 IST (Day T+0) | `assumed_schedule` | Yes* (Assumption-Dependent) | Yes (Day T Overnight) | `no_fill` | Instrument close 15:30 + 0m buffer as proxy for unobserved Yahoo publication |
| `NIFTY_BANK` | `^NSEBANK` | `Asia/Kolkata` | 15:30 local | 15:30 IST (Day T+0) | `assumed_schedule` | Yes* (Assumption-Dependent) | Yes (Day T Overnight) | `no_fill` | Instrument close 15:30 + 0m buffer as proxy for unobserved Yahoo publication |
| `USD_INR` | `USDINR=X` | `Asia/Kolkata` | 15:30 local | 15:30 IST (Day T+0) | `assumed_schedule` | Yes* (Assumption-Dependent) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 15:30 + 0m buffer as proxy for unobserved Yahoo publication |
| `INDIA_10Y_YIELD` | `IN10Y=RR` | `Asia/Kolkata` | 16:30 local | 16:45 IST (Day T+0) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 16:30 + 15m buffer as proxy for unobserved Yahoo publication |
| `SP500` | `^GSPC` | `America/New_York` | 16:00 local | 02:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 16:00 + 30m buffer as proxy for unobserved Yahoo publication |
| `NASDAQ` | `^IXIC` | `America/New_York` | 16:00 local | 02:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 16:00 + 30m buffer as proxy for unobserved Yahoo publication |
| `DOW_JONES` | `^DJI` | `America/New_York` | 16:00 local | 02:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 16:00 + 30m buffer as proxy for unobserved Yahoo publication |
| `US_VIX` | `^VIX` | `America/New_York` | 16:15 local | 02:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 16:15 + 15m buffer as proxy for unobserved Yahoo publication |
| `US_10Y_YIELD` | `^TNX` | `America/New_York` | 15:00 local | 01:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 15:00 + 30m buffer as proxy for unobserved Yahoo publication |
| `BRENT_CRUDE` | `BZ=F` | `America/New_York` | 17:00 local | 03:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 17:00 + 30m buffer as proxy for unobserved Yahoo publication |
| `WTI_CRUDE` | `CL=F` | `America/New_York` | 17:00 local | 03:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 17:00 + 30m buffer as proxy for unobserved Yahoo publication |
| `GOLD` | `GC=F` | `America/New_York` | 17:00 local | 03:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 17:00 + 30m buffer as proxy for unobserved Yahoo publication |
| `DXY` | `DX-Y.NYB` | `America/New_York` | 17:00 local | 03:00 IST (Day T+1) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 17:00 + 30m buffer as proxy for unobserved Yahoo publication |
| `NIKKEI_225` | `^N225` | `Asia/Tokyo` | 15:00 local | 11:45 IST (Day T+0) | `assumed_schedule` | Yes (Day T) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 15:00 + 15m buffer as proxy for unobserved Yahoo publication |
| `HANG_SENG` | `^HSI` | `Asia/Hong_Kong` | 16:00 local | 13:45 IST (Day T+0) | `assumed_schedule` | Yes (Day T) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 16:00 + 15m buffer as proxy for unobserved Yahoo publication |
| `FTSE_100` | `^FTSE` | `Europe/London` | 16:30 local | 21:15 IST (Day T+0) | `assumed_schedule` | No (Day T-1 only) | Yes (Day T Overnight) | `forward_fill_calendar` | Instrument close 16:30 + 15m buffer as proxy for unobserved Yahoo publication |

\* *Indicates assumption-dependent boundary condition: instrument finalization coincides with Snapshot A cutoff, but provider publication time is unobserved.*

## Methodological Guarantees
1. **Snapshot A** NEVER incorporates Day T US market closing prices, as US markets do not close until 01:30/02:30 IST on Day T+1.
2. **Snapshot B** legitimately incorporates Day T US market closing prices, but NEVER incorporates Day T+1 prices.
3. **Conservative Assumed Schedules**: Fixed publication buffers (15–30 min) for US markets place arrival between 01:30 and 03:30 IST on Day T+1, which is > 5 hours prior to Snapshot B cutoff (08:50 IST), guaranteeing zero look-ahead risk.
4. **No Backfilling**: Incomplete or missing series are forward-filled only up to 5 days over non-overlapping holidays.
5. **Provider Availability Separation**: Instrument finalization is strictly separated from provider availability across all 16 variables.
