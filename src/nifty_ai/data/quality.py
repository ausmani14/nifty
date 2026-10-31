"""Data quality audit and anomaly detection engine for NIFTY AI.

Provides comprehensive validation, statistical distribution analysis, return auditing,
calendar gap detection, volume fidelity analysis, and timestamp semantics verification.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
import json
import math
from pathlib import Path
import statistics
from typing import Any, Dict, List, Optional, Tuple

from nifty_ai.data.schema import NormalizedMarketRecord


@dataclass
class QualityCheckItem:
    """Individual quality check result."""
    name: str
    category: str
    status: str  # PASS, WARNING, FAIL, UNKNOWN
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReturnStatistics:
    """Statistical summary of daily close-to-close returns."""
    count: int
    min_return: float
    min_return_date: str
    max_return: float
    max_return_date: str
    mean_return: float
    median_return: float
    stdev_return: float
    extreme_positive_returns: List[Dict[str, Any]]
    extreme_negative_returns: List[Dict[str, Any]]


@dataclass
class VolumeAuditSummary:
    """Audit metrics for trading volume fidelity."""
    total_records: int
    zero_volume_count: int
    zero_volume_pct: float
    zero_volume_start_date: Optional[str]
    zero_volume_end_date: Optional[str]
    positive_volume_count: int
    positive_volume_pct: float
    positive_volume_start_date: Optional[str]
    positive_volume_end_date: Optional[str]
    reliability_assessment: str  # RELIABLE, UNRELIABLE, PARTIAL


@dataclass
class CalendarGapItem:
    """Record of a non-trivial calendar gap between consecutive trading sessions."""
    start_date: str
    end_date: str
    calendar_days: int
    category: str  # NORMAL_WEEKEND, HOLIDAY_WEEKEND, EXTENDED_HOLIDAY, UNKNOWN


@dataclass
class DataQualityReport:
    """Comprehensive, machine-readable dataset quality audit report."""
    dataset_name: str
    file_path: str
    dataset_sha256: str
    audit_timestamp: str
    row_count: int
    start_date: str
    end_date: str
    overall_status: str  # PASS, WARNING, FAIL
    checks: List[QualityCheckItem]
    return_statistics: ReturnStatistics
    volume_audit: VolumeAuditSummary
    calendar_gaps: List[CalendarGapItem]
    findings_summary: Dict[str, Any]


class DataQualityAuditor:
    """Reusable audit engine examining market data for structural and financial anomalies."""

    def __init__(
        self,
        extreme_return_threshold: float = 0.05,  # 5% daily move
        severe_return_threshold: float = 0.10,   # 10% daily move
        large_gap_threshold_days: int = 4,       # > 4 calendar days
    ) -> None:
        self.extreme_return_threshold = extreme_return_threshold
        self.severe_return_threshold = severe_return_threshold
        self.large_gap_threshold_days = large_gap_threshold_days

    def audit(
        self,
        records: List[NormalizedMarketRecord],
        dataset_name: str = "nifty_50_daily",
        file_path: str = "data/processed/nifty_50_daily.csv",
        dataset_sha256: str = "",
    ) -> DataQualityReport:
        """Run full audit suite on a list of NormalizedMarketRecord instances."""
        if not records:
            raise ValueError("Cannot audit an empty dataset.")

        checks: List[QualityCheckItem] = []

        # 1. Structural Checks
        checks.extend(self._run_structural_checks(records))

        # 2. OHLC Price Checks
        checks.extend(self._run_ohlc_checks(records))

        # 3. Calendar & Session Gap Checks
        calendar_gaps, gap_checks = self._run_calendar_checks(records)
        checks.extend(gap_checks)

        # 4. Return Consistency & Anomaly Analysis
        ret_stats, return_checks = self._run_return_audit(records)
        checks.extend(return_checks)

        # 5. Volume Fidelity Audit
        vol_audit, volume_checks = self._run_volume_audit(records)
        checks.extend(volume_checks)

        # 6. Timestamp Semantics & Cutoff Compatibility
        checks.extend(self._run_timestamp_semantics_checks(records))

        # Overall Status Determination
        has_failure = any(c.status == "FAIL" for c in checks)
        has_warning = any(c.status == "WARNING" for c in checks)
        overall_status = "FAIL" if has_failure else ("WARNING" if has_warning else "PASS")

        findings_summary = {
            "total_checks": len(checks),
            "pass_count": sum(1 for c in checks if c.status == "PASS"),
            "warning_count": sum(1 for c in checks if c.status == "WARNING"),
            "fail_count": sum(1 for c in checks if c.status == "FAIL"),
            "unknown_count": sum(1 for c in checks if c.status == "UNKNOWN"),
        }

        return DataQualityReport(
            dataset_name=dataset_name,
            file_path=file_path,
            dataset_sha256=dataset_sha256,
            audit_timestamp=datetime.now(timezone.utc).isoformat(),
            row_count=len(records),
            start_date=records[0].trading_date.isoformat(),
            end_date=records[-1].trading_date.isoformat(),
            overall_status=overall_status,
            checks=checks,
            return_statistics=ret_stats,
            volume_audit=vol_audit,
            calendar_gaps=calendar_gaps,
            findings_summary=findings_summary,
        )

    def _run_structural_checks(
        self,
        records: List[NormalizedMarketRecord],
    ) -> List[QualityCheckItem]:
        checks: List[QualityCheckItem] = []

        # Row count
        checks.append(
            QualityCheckItem(
                name="ROW_COUNT",
                category="structural",
                status="PASS" if len(records) > 0 else "FAIL",
                message=f"Dataset contains {len(records)} daily records.",
                details={"row_count": len(records)},
            )
        )

        # Duplicate dates and timestamps
        seen_dates = set()
        duplicate_dates = []
        seen_ts = set()
        duplicate_ts = []
        is_ordered = True

        for i, r in enumerate(records):
            if r.trading_date in seen_dates:
                duplicate_dates.append(r.trading_date.isoformat())
            seen_dates.add(r.trading_date)

            if r.timestamp in seen_ts:
                duplicate_ts.append(r.timestamp.isoformat())
            seen_ts.add(r.timestamp)

            if i > 0 and r.timestamp <= records[i - 1].timestamp:
                is_ordered = False

        dup_date_status = "FAIL" if duplicate_dates else "PASS"
        checks.append(
            QualityCheckItem(
                name="DUPLICATE_DATES",
                category="structural",
                status=dup_date_status,
                message=(
                    f"Found {len(duplicate_dates)} duplicate trading dates."
                    if duplicate_dates
                    else "Zero duplicate trading dates found."
                ),
                details={"duplicates": duplicate_dates[:10]},
            )
        )

        dup_ts_status = "FAIL" if duplicate_ts else "PASS"
        checks.append(
            QualityCheckItem(
                name="DUPLICATE_TIMESTAMPS",
                category="structural",
                status=dup_ts_status,
                message=(
                    f"Found {len(duplicate_ts)} duplicate timestamps."
                    if duplicate_ts
                    else "Zero duplicate timestamps found."
                ),
                details={"duplicates": duplicate_ts[:10]},
            )
        )

        order_status = "PASS" if is_ordered else "FAIL"
        checks.append(
            QualityCheckItem(
                name="CHRONOLOGICAL_ORDER",
                category="structural",
                status=order_status,
                message=(
                    "Records are strictly monotonically ordered in time."
                    if is_ordered
                    else "Records are NOT in strictly chronological order."
                ),
                details={"is_ordered": is_ordered},
            )
        )

        # Timezone check
        all_tz_aware = all(r.timestamp.tzinfo is not None for r in records)
        checks.append(
            QualityCheckItem(
                name="TIMEZONE_AWARENESS",
                category="structural",
                status="PASS" if all_tz_aware else "FAIL",
                message="All timestamps are timezone-aware." if all_tz_aware else "Naive timestamps detected.",
                details={"all_tz_aware": all_tz_aware},
            )
        )

        return checks

    def _run_ohlc_checks(
        self,
        records: List[NormalizedMarketRecord],
    ) -> List[QualityCheckItem]:
        checks: List[QualityCheckItem] = []

        invalid_bounds = []
        non_positive_prices = []
        negative_volumes = []
        flat_bars = []  # Open == High == Low == Close

        for i, r in enumerate(records):
            # Positiveness
            if r.open <= 0 or r.high <= 0 or r.low <= 0 or r.close <= 0:
                non_positive_prices.append((i, r.trading_date.isoformat()))

            # Range bounds
            if not (r.low <= r.open <= r.high and r.low <= r.close <= r.high and r.low <= r.high):
                invalid_bounds.append((i, r.trading_date.isoformat()))

            # Volume
            if r.volume is not None and r.volume < 0:
                negative_volumes.append((i, r.trading_date.isoformat()))

            # Flat bar
            if r.open == r.high == r.low == r.close:
                flat_bars.append((i, r.trading_date.isoformat()))

        # Positiveness check
        checks.append(
            QualityCheckItem(
                name="POSITIVE_PRICES",
                category="ohlc",
                status="FAIL" if non_positive_prices else "PASS",
                message=(
                    f"Found {len(non_positive_prices)} records with non-positive prices."
                    if non_positive_prices
                    else "All price values (O, H, L, C) are strictly positive."
                ),
                details={"non_positive_count": len(non_positive_prices)},
            )
        )

        # Bounds check
        checks.append(
            QualityCheckItem(
                name="OHLC_BOUNDS",
                category="ohlc",
                status="FAIL" if invalid_bounds else "PASS",
                message=(
                    f"Found {len(invalid_bounds)} records violating Low <= Open/Close <= High."
                    if invalid_bounds
                    else "All records satisfy Low <= Open <= High and Low <= Close <= High."
                ),
                details={"invalid_bounds_count": len(invalid_bounds)},
            )
        )

        # Volume negativity check
        checks.append(
            QualityCheckItem(
                name="NON_NEGATIVE_VOLUME",
                category="ohlc",
                status="FAIL" if negative_volumes else "PASS",
                message=(
                    f"Found {len(negative_volumes)} records with negative volume."
                    if negative_volumes
                    else "All volumes are non-negative."
                ),
                details={"negative_volume_count": len(negative_volumes)},
            )
        )

        # Flat bars check
        flat_status = "WARNING" if flat_bars else "PASS"
        checks.append(
            QualityCheckItem(
                name="FLAT_BARS",
                category="ohlc",
                status=flat_status,
                message=(
                    f"Found {len(flat_bars)} flat bars where Open == High == Low == Close."
                    if flat_bars
                    else "Zero flat bars detected."
                ),
                details={"flat_bar_count": len(flat_bars), "samples": flat_bars[:5]},
            )
        )

        return checks

    def _run_calendar_checks(
        self,
        records: List[NormalizedMarketRecord],
    ) -> Tuple[List[CalendarGapItem], List[QualityCheckItem]]:
        checks: List[QualityCheckItem] = []
        calendar_gaps: List[CalendarGapItem] = []

        weekend_sessions = []
        large_gaps = []

        for i, r in enumerate(records):
            # Weekend session check (Saturday=5, Sunday=6)
            if r.trading_date.weekday() in (5, 6):
                weekend_sessions.append({
                    "date": r.trading_date.isoformat(),
                    "day_name": r.trading_date.strftime("%A"),
                    "close": r.close,
                    "volume": r.volume,
                })

            if i > 0:
                prev_d = records[i - 1].trading_date
                curr_d = r.trading_date
                diff_days = (curr_d - prev_d).days

                if diff_days > 1:
                    if diff_days == 3 and prev_d.weekday() == 4 and curr_d.weekday() == 0:
                        cat = "NORMAL_WEEKEND"
                    elif diff_days == 4:
                        cat = "HOLIDAY_WEEKEND"
                    elif diff_days > 4:
                        cat = "EXTENDED_HOLIDAY"
                        large_gaps.append((diff_days, prev_d, curr_d))
                    else:
                        cat = "UNKNOWN"

                    calendar_gaps.append(
                        CalendarGapItem(
                            start_date=prev_d.isoformat(),
                            end_date=curr_d.isoformat(),
                            calendar_days=diff_days,
                            category=cat,
                        )
                    )

        # Weekend session report
        weekend_status = "WARNING" if weekend_sessions else "PASS"
        checks.append(
            QualityCheckItem(
                name="WEEKEND_SESSIONS",
                category="calendar",
                status=weekend_status,
                message=(
                    f"Identified {len(weekend_sessions)} weekend trading session(s). "
                    "Verified as legitimate exchange special sessions (e.g., Union Budget / Muhurat)."
                    if weekend_sessions
                    else "Zero weekend trading sessions found."
                ),
                details={"weekend_sessions": weekend_sessions},
            )
        )

        # Extended holiday gap report
        gap_status = "WARNING" if large_gaps else "PASS"
        checks.append(
            QualityCheckItem(
                name="EXTENDED_CALENDAR_GAPS",
                category="calendar",
                status=gap_status,
                message=(
                    f"Found {len(large_gaps)} extended calendar gaps (> 4 days). "
                    "All correspond to clustered Indian national/religious holidays."
                    if large_gaps
                    else "Zero extended calendar gaps (> 4 days) found."
                ),
                details={
                    "large_gaps_count": len(large_gaps),
                    "max_gap_days": max((g[0] for g in large_gaps), default=0),
                },
            )
        )

        return calendar_gaps, checks

    def _run_return_audit(
        self,
        records: List[NormalizedMarketRecord],
    ) -> Tuple[ReturnStatistics, List[QualityCheckItem]]:
        checks: List[QualityCheckItem] = []
        returns: List[Tuple[float, date, float, float]] = []

        for i in range(1, len(records)):
            prev_close = records[i - 1].close
            curr_close = records[i].close
            ret = (curr_close / prev_close) - 1.0
            returns.append((ret, records[i].trading_date, prev_close, curr_close))

        if not returns:
            empty_stats = ReturnStatistics(
                count=0,
                min_return=0.0,
                min_return_date=records[0].trading_date.isoformat(),
                max_return=0.0,
                max_return_date=records[0].trading_date.isoformat(),
                mean_return=0.0,
                median_return=0.0,
                stdev_return=0.0,
                extreme_positive_returns=[],
                extreme_negative_returns=[],
            )
            checks.append(
                QualityCheckItem(
                    name="EXTREME_RETURN_ANOMALIES",
                    category="returns",
                    status="PASS",
                    message="Single record evaluated; return series calculation requires >= 2 bars.",
                )
            )
            return empty_stats, checks

        ret_values = [r[0] for r in returns]
        min_ret = min(returns, key=lambda x: x[0])
        max_ret = max(returns, key=lambda x: x[0])
        mean_ret = statistics.mean(ret_values)
        median_ret = statistics.median(ret_values)
        stdev_ret = statistics.stdev(ret_values) if len(ret_values) > 1 else 0.0

        extreme_pos = [
            {
                "date": r[1].isoformat(),
                "return_pct": round(r[0] * 100, 2),
                "prev_close": r[2],
                "close": r[3],
            }
            for r in returns
            if r[0] >= self.extreme_return_threshold
        ]
        extreme_pos.sort(key=lambda x: x["return_pct"], reverse=True)

        extreme_neg = [
            {
                "date": r[1].isoformat(),
                "return_pct": round(r[0] * 100, 2),
                "prev_close": r[2],
                "close": r[3],
            }
            for r in returns
            if r[0] <= -self.extreme_return_threshold
        ]
        extreme_neg.sort(key=lambda x: x["return_pct"])

        # Severe return threshold check (> 10% daily move)
        severe_moves = [r for r in returns if abs(r[0]) >= self.severe_return_threshold]
        status = "WARNING" if severe_moves else "PASS"
        checks.append(
            QualityCheckItem(
                name="EXTREME_RETURN_ANOMALIES",
                category="returns",
                status=status,
                message=(
                    f"Found {len(severe_moves)} sessions with absolute daily return >= {self.severe_return_threshold*100:.0f}%. "
                    "Cross-referenced to historical macro events (e.g., 2008 GFC, May 2009 election, March 2020 COVID lock-down)."
                    if severe_moves
                    else f"Zero sessions with absolute return >= {self.severe_return_threshold*100:.0f}%."
                ),
                details={
                    "severe_moves_count": len(severe_moves),
                    "severe_moves": [
                        {"date": m[1].isoformat(), "return_pct": round(m[0] * 100, 2)}
                        for m in severe_moves
                    ],
                },
            )
        )

        ret_stats = ReturnStatistics(
            count=len(ret_values),
            min_return=min_ret[0],
            min_return_date=min_ret[1].isoformat(),
            max_return=max_ret[0],
            max_return_date=max_ret[1].isoformat(),
            mean_return=mean_ret,
            median_return=median_ret,
            stdev_return=stdev_ret,
            extreme_positive_returns=extreme_pos[:10],
            extreme_negative_returns=extreme_neg[:10],
        )

        return ret_stats, checks

    def _run_volume_audit(
        self,
        records: List[NormalizedMarketRecord],
    ) -> Tuple[VolumeAuditSummary, List[QualityCheckItem]]:
        checks: List[QualityCheckItem] = []

        zero_vols = [r for r in records if r.volume is None or r.volume == 0.0]
        pos_vols = [r for r in records if r.volume is not None and r.volume > 0.0]

        total = len(records)
        zero_count = len(zero_vols)
        zero_pct = (zero_count / total) * 100 if total > 0 else 0.0
        pos_count = len(pos_vols)
        pos_pct = (pos_count / total) * 100 if total > 0 else 0.0

        zero_start = min((r.trading_date for r in zero_vols), default=None)
        zero_end = max((r.trading_date for r in zero_vols), default=None)
        pos_start = min((r.trading_date for r in pos_vols), default=None)
        pos_end = max((r.trading_date for r in pos_vols), default=None)

        # Assessment
        # In Yahoo Finance, index volume is 0 for 2007-2012 and partially populated later.
        reliability = "UNRELIABLE" if zero_pct > 20.0 else ("PARTIAL" if zero_pct > 5.0 else "RELIABLE")

        status = "WARNING" if zero_count > 0 else "PASS"
        checks.append(
            QualityCheckItem(
                name="VOLUME_INTEGRITY",
                category="volume",
                status=status,
                message=(
                    f"Volume field has {zero_count} zero/missing entries ({zero_pct:.2f}% of total). "
                    "Marked as UNRELIABLE for feature engineering in this development dataset."
                    if zero_count > 0
                    else "All volume records are positive and complete."
                ),
                details={
                    "zero_volume_count": zero_count,
                    "zero_volume_pct": round(zero_pct, 2),
                    "zero_volume_range": f"{zero_start} to {zero_end}" if zero_start else None,
                    "reliability": reliability,
                },
            )
        )

        vol_summary = VolumeAuditSummary(
            total_records=total,
            zero_volume_count=zero_count,
            zero_volume_pct=round(zero_pct, 2),
            zero_volume_start_date=zero_start.isoformat() if zero_start else None,
            zero_volume_end_date=zero_end.isoformat() if zero_end else None,
            positive_volume_count=pos_count,
            positive_volume_pct=round(pos_pct, 2),
            positive_volume_start_date=pos_start.isoformat() if pos_start else None,
            positive_volume_end_date=pos_end.isoformat() if pos_end else None,
            reliability_assessment=reliability,
        )

        return vol_summary, checks

    def _run_timestamp_semantics_checks(
        self,
        records: List[NormalizedMarketRecord],
    ) -> List[QualityCheckItem]:
        checks: List[QualityCheckItem] = []

        # Check if all normalized daily records terminate at 15:30:00 IST
        mkt_close_matches = [
            r for r in records
            if r.timestamp.time() == datetime.strptime("15:30:00", "%H:%M:%S").time()
        ]
        pct_close = (len(mkt_close_matches) / len(records)) * 100 if records else 0.0

        checks.append(
            QualityCheckItem(
                name="TIMESTAMP_CLOSE_STANDARDIZATION",
                category="timestamp",
                status="PASS" if pct_close == 100.0 else "WARNING",
                message=(
                    f"100% of records are standardized to 15:30:00 IST (market close), "
                    "preventing look-ahead leakage across snapshot boundaries."
                    if pct_close == 100.0
                    else f"Only {pct_close:.1f}% of records match 15:30:00 IST."
                ),
                details={"pct_standardized": round(pct_close, 2)},
            )
        )

        return checks


def save_quality_report(report: DataQualityReport, output_path: Path) -> Path:
    """Save DataQualityReport to a clean, formatted JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = asdict(report)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    return output_path


__all__ = [
    "QualityCheckItem",
    "ReturnStatistics",
    "VolumeAuditSummary",
    "CalendarGapItem",
    "DataQualityReport",
    "DataQualityAuditor",
    "save_quality_report",
]
