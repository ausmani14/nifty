"""Validation rules for market context time series."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import numpy as np

from nifty_ai.data.context.schema import ContextObservation
from nifty_ai.data.validation import ValidationIssue, ValidationResult, ValidationSeverity


class ContextDataValidator:
    """Validator for series of ContextObservation objects."""

    def validate_series(
        self,
        variable_name: str,
        observations: List[ContextObservation],
    ) -> ValidationResult:
        """Run thorough data quality and consistency checks on context observations."""
        issues: List[ValidationIssue] = []

        if not observations:
            issues.append(
                ValidationIssue(
                    rule_name="NON_EMPTY_SERIES",
                    message=f"Series for {variable_name} is empty.",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return ValidationResult(is_valid=False, issues=issues)

        seen_dates = set()
        prev_obs_dt: Optional[datetime] = None

        for idx, obs in enumerate(observations):
            # Check variable name match
            if obs.variable_name != variable_name:
                issues.append(
                    ValidationIssue(
                        rule_name="VARIABLE_NAME_CONSISTENCY",
                        message=f"Observation variable {obs.variable_name} != {variable_name}",
                        severity=ValidationSeverity.ERROR,
                        record_index=idx,
                    )
                )

            # Check timezone awareness
            if obs.observation_timestamp.tzinfo is None or obs.availability_timestamp.tzinfo is None:
                issues.append(
                    ValidationIssue(
                        rule_name="TIMEZONE_AWARENESS",
                        message="Timestamps must be timezone-aware.",
                        severity=ValidationSeverity.ERROR,
                        record_index=idx,
                    )
                )

            # Check observation vs availability ordering
            if obs.observation_timestamp > obs.availability_timestamp:
                issues.append(
                    ValidationIssue(
                        rule_name="AVAILABILITY_PRECEDES_OBSERVATION",
                        message="Observation timestamp cannot be strictly after availability timestamp.",
                        severity=ValidationSeverity.ERROR,
                        record_index=idx,
                    )
                )

            # Duplicate dates check
            if obs.observation_date in seen_dates:
                issues.append(
                    ValidationIssue(
                        rule_name="DUPLICATE_OBSERVATION_DATE",
                        message=f"Duplicate observation date: {obs.observation_date}",
                        severity=ValidationSeverity.ERROR,
                        record_index=idx,
                    )
                )
            seen_dates.add(obs.observation_date)

            # Monotonicity check
            if prev_obs_dt is not None and obs.observation_timestamp <= prev_obs_dt:
                issues.append(
                    ValidationIssue(
                        rule_name="CHRONOLOGICAL_MONOTONICITY",
                        message=f"Non-monotonic timestamp order: {obs.observation_timestamp} <= {prev_obs_dt}",
                        severity=ValidationSeverity.ERROR,
                        record_index=idx,
                    )
                )
            prev_obs_dt = obs.observation_timestamp

            # Value sanity
            if obs.close <= 0.0 and variable_name not in {"US_10Y_YIELD", "INDIA_10Y_YIELD"}:
                # Negative oil or yield is theoretically possible in rare panics, but standard price indices must be > 0
                issues.append(
                    ValidationIssue(
                        rule_name="NON_POSITIVE_PRICE",
                        message=f"Non-positive closing price: {obs.close}",
                        severity=ValidationSeverity.ERROR,
                        record_index=idx,
                    )
                )

        is_valid = len([i for i in issues if i.severity == ValidationSeverity.ERROR]) == 0
        return ValidationResult(is_valid=is_valid, issues=issues)


__all__ = ["ContextDataValidator"]
