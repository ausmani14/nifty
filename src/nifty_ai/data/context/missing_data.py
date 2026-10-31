"""Calendar-aware point-in-time missing data handling for market context variables."""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd

from nifty_ai.data.context.schema import ContextObservation, MissingPolicy


@dataclass
class FillDiagnostics:
    """Diagnostics for forward-fill operations, reporting both calendar-day and
    target-session-day fill aging."""
    total_requested: int = 0
    same_day_matches: int = 0
    filled_rows: int = 0
    missing_rows: int = 0
    max_calendar_fill_days: int = 0
    max_target_session_fill_days: int = 0
    quarantined_rows: int = 0
    rejected_rows: int = 0
    fill_examples: List[Dict] = field(default_factory=list)


def align_and_fill_series(
    dates: List[date],
    date_to_obs: Dict[date, ContextObservation],
    missing_policy: MissingPolicy,
    max_fill_days: int = 3,
) -> List[Optional[ContextObservation]]:
    """Align a context observation series to target calendar dates with strict anti-leakage policy.

    Rules:
    - NO_FILL: Missing dates remain None.
    - FORWARD_FILL_CALENDAR: Missing dates are forward-filled using the latest historically
      available observation, up to max_fill_days (e.g. 3 days over a weekend/holiday).
    - QUARANTINE: If missing rate exceeds tolerance, the series is quarantined.
    - NEVER back-fill (backward filling introduces future leakage).
    """
    aligned_list: List[Optional[ContextObservation]] = []
    
    # Sort all known observations by date to allow seeding prior knowledge
    known_dates_sorted = sorted(date_to_obs.keys())
    
    # Find initial last_known observation prior to the first requested date
    first_target_date = dates[0] if dates else None
    last_known: Optional[ContextObservation] = None
    last_known_date: Optional[date] = None

    if first_target_date is not None:
        prior_dates = [kd for kd in known_dates_sorted if kd < first_target_date]
        if prior_dates:
            last_known_date = prior_dates[-1]
            last_known = date_to_obs[last_known_date]

    for d in dates:
        if d in date_to_obs:
            last_known = date_to_obs[d]
            last_known_date = d
            aligned_list.append(last_known)
        else:
            if missing_policy == MissingPolicy.NO_FILL:
                aligned_list.append(None)
            elif missing_policy in (MissingPolicy.FORWARD_FILL_1D, MissingPolicy.FORWARD_FILL_CALENDAR):
                limit = 1 if missing_policy == MissingPolicy.FORWARD_FILL_1D else max_fill_days
                if last_known is not None and last_known_date is not None:
                    gap_days = (d - last_known_date).days
                    if gap_days <= limit:
                        aligned_list.append(last_known)
                    else:
                        aligned_list.append(None)
                else:
                    aligned_list.append(None)
            else:
                aligned_list.append(None)

    return aligned_list


def align_and_fill_series_with_diagnostics(
    dates: List[date],
    date_to_obs: Dict[date, ContextObservation],
    missing_policy: MissingPolicy,
    max_fill_days: int = 3,
    nifty_trading_dates: Optional[Set[date]] = None,
) -> Tuple[List[Optional[ContextObservation]], FillDiagnostics]:
    """Like align_and_fill_series but also returns FillDiagnostics.

    Args:
        dates: Target calendar dates to align to.
        date_to_obs: Known observations keyed by date.
        missing_policy: Fill policy.
        max_fill_days: Maximum calendar days allowed for forward fill.
        nifty_trading_dates: Optional set of NIFTY 50 trading dates, used to
            compute target-session fill aging (how many NIFTY sessions elapsed
            between the source observation and the filled target date).

    Returns:
        Tuple of (aligned observations list, FillDiagnostics).
    """
    diag = FillDiagnostics(total_requested=len(dates))

    # Sort all known observations by date to allow seeding prior knowledge
    known_dates_sorted = sorted(date_to_obs.keys())

    # Find initial last_known observation prior to the first requested date
    first_target_date = dates[0] if dates else None
    last_known: Optional[ContextObservation] = None
    last_known_date: Optional[date] = None

    if first_target_date is not None:
        prior_dates = [kd for kd in known_dates_sorted if kd < first_target_date]
        if prior_dates:
            last_known_date = prior_dates[-1]
            last_known = date_to_obs[last_known_date]

    aligned_list: List[Optional[ContextObservation]] = []

    for d in dates:
        if d in date_to_obs:
            last_known = date_to_obs[d]
            last_known_date = d
            aligned_list.append(last_known)
            diag.same_day_matches += 1
        else:
            if missing_policy == MissingPolicy.NO_FILL:
                aligned_list.append(None)
                diag.missing_rows += 1
            elif missing_policy in (MissingPolicy.FORWARD_FILL_1D, MissingPolicy.FORWARD_FILL_CALENDAR):
                limit = 1 if missing_policy == MissingPolicy.FORWARD_FILL_1D else max_fill_days
                if last_known is not None and last_known_date is not None:
                    gap_days = (d - last_known_date).days
                    if gap_days <= limit:
                        aligned_list.append(last_known)
                        diag.filled_rows += 1
                        diag.max_calendar_fill_days = max(diag.max_calendar_fill_days, gap_days)

                        # Compute target-session aging if NIFTY trading dates provided
                        if nifty_trading_dates is not None:
                            session_gap = sum(
                                1 for td in nifty_trading_dates
                                if last_known_date < td <= d
                            )
                            diag.max_target_session_fill_days = max(
                                diag.max_target_session_fill_days, session_gap
                            )

                        # Record example for diagnostics (limit to first 5)
                        if len(diag.fill_examples) < 5:
                            session_gap_val = 0
                            if nifty_trading_dates is not None:
                                session_gap_val = sum(
                                    1 for td in nifty_trading_dates
                                    if last_known_date < td <= d
                                )
                            diag.fill_examples.append({
                                "target_date": d.isoformat(),
                                "source_date": last_known_date.isoformat(),
                                "calendar_gap_days": gap_days,
                                "nifty_session_gap": session_gap_val,
                            })
                    else:
                        aligned_list.append(None)
                        diag.rejected_rows += 1
                else:
                    aligned_list.append(None)
                    diag.missing_rows += 1
            else:
                aligned_list.append(None)
                diag.quarantined_rows += 1

    return aligned_list, diag


__all__ = ["align_and_fill_series", "align_and_fill_series_with_diagnostics", "FillDiagnostics"]

