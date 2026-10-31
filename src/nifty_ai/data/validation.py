"""Data validation architecture for NIFTY AI.

Provides modular validation interfaces and safe baseline schema validators to catch
OHLC anomalies, duplicate timestamps, inverted ranges, and timezone issues.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional
from nifty_ai.data.schema import NormalizedMarketRecord


class ValidationSeverity(str, Enum):
    """Severity levels for validation findings."""
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class ValidationIssue:
    """An individual validation diagnostic finding."""
    rule_name: str
    message: str
    severity: ValidationSeverity
    record_index: Optional[int] = None
    field_name: Optional[str] = None


@dataclass
class ValidationResult:
    """Consolidated outcome of a validation run."""
    is_valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


class BaseDataValidator(ABC):
    """Abstract validator interface for data series."""

    @abstractmethod
    def validate(self, records: List[Any]) -> ValidationResult:
        """Execute validation suite against a sequence of records."""
        pass


class MarketDataValidator(BaseDataValidator):
    """Baseline schema validator for NormalizedMarketRecord series.

    Checks:
    - OHLC relationship bounds (low <= open <= high, low <= close <= high, low <= high)
    - Positive price values (> 0)
    - Non-negative volume (>= 0)
    - Timezone awareness of timestamps
    - Chronological sequencing
    - Duplicate timestamp detection
    """

    def validate_record(
        self,
        record: NormalizedMarketRecord,
        index: Optional[int] = None,
    ) -> List[ValidationIssue]:
        """Validate a single market record for internal consistency."""
        issues: List[ValidationIssue] = []

        # Timezone check
        if record.timestamp.tzinfo is None:
            issues.append(
                ValidationIssue(
                    rule_name="TIMEZONE_AWARENESS",
                    message="Market record timestamp lacks timezone awareness.",
                    severity=ValidationSeverity.ERROR,
                    record_index=index,
                    field_name="timestamp",
                )
            )

        # Price positiveness
        for price_field, value in [
            ("open", record.open),
            ("high", record.high),
            ("low", record.low),
            ("close", record.close),
        ]:
            if value <= 0:
                issues.append(
                    ValidationIssue(
                        rule_name="POSITIVE_PRICE",
                        message=f"{price_field} price must be strictly positive, got {value}.",
                        severity=ValidationSeverity.ERROR,
                        record_index=index,
                        field_name=price_field,
                    )
                )

        # High >= Low
        if record.high < record.low:
            issues.append(
                ValidationIssue(
                    rule_name="HIGH_GTE_LOW",
                    message=f"High ({record.high}) cannot be strictly less than Low ({record.low}).",
                    severity=ValidationSeverity.ERROR,
                    record_index=index,
                    field_name="high",
                )
            )

        # Open in [Low, High]
        if not (record.low <= record.open <= record.high):
            issues.append(
                ValidationIssue(
                    rule_name="OPEN_WITHIN_RANGE",
                    message=f"Open ({record.open}) falls outside [Low: {record.low}, High: {record.high}].",
                    severity=ValidationSeverity.ERROR,
                    record_index=index,
                    field_name="open",
                )
            )

        # Close in [Low, High]
        if not (record.low <= record.close <= record.high):
            issues.append(
                ValidationIssue(
                    rule_name="CLOSE_WITHIN_RANGE",
                    message=f"Close ({record.close}) falls outside [Low: {record.low}, High: {record.high}].",
                    severity=ValidationSeverity.ERROR,
                    record_index=index,
                    field_name="close",
                )
            )

        # Non-negative volume
        if record.volume is not None and record.volume < 0:
            issues.append(
                ValidationIssue(
                    rule_name="NON_NEGATIVE_VOLUME",
                    message=f"Volume cannot be negative, got {record.volume}.",
                    severity=ValidationSeverity.ERROR,
                    record_index=index,
                    field_name="volume",
                )
            )

        return issues

    def validate(self, records: List[NormalizedMarketRecord]) -> ValidationResult:
        """Validate a full series of market records for record-level and series-level validity."""
        issues: List[ValidationIssue] = []

        if not records:
            return ValidationResult(is_valid=True, issues=[])

        seen_timestamps = set()

        for i, record in enumerate(records):
            # Record-level checks
            issues.extend(self.validate_record(record, index=i))

            # Duplicate check
            key = (record.symbol, record.timestamp)
            if key in seen_timestamps:
                issues.append(
                    ValidationIssue(
                        rule_name="DUPLICATE_TIMESTAMP",
                        message=f"Duplicate timestamp {record.timestamp} detected for symbol '{record.symbol}'.",
                        severity=ValidationSeverity.ERROR,
                        record_index=i,
                        field_name="timestamp",
                    )
                )
            seen_timestamps.add(key)

            # Chronological sequence check
            if i > 0:
                prev_record = records[i - 1]
                if record.timestamp <= prev_record.timestamp:
                    issues.append(
                        ValidationIssue(
                            rule_name="CHRONOLOGICAL_ORDER",
                            message=(
                                f"Record at index {i} ({record.timestamp}) is not strictly "
                                f"after index {i-1} ({prev_record.timestamp})."
                            ),
                            severity=ValidationSeverity.ERROR,
                            record_index=i,
                            field_name="timestamp",
                        )
                    )

        is_valid = not any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        return ValidationResult(is_valid=is_valid, issues=issues)


__all__ = [
    "ValidationSeverity",
    "ValidationIssue",
    "ValidationResult",
    "BaseDataValidator",
    "MarketDataValidator",
]
