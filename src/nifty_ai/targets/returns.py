"""Next-session return target computation engine for NIFTY AI.

Provides mathematically rigorous, chronological calculation of regression targets:
target_return_T = Close_(T+1) / Close_T - 1
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from nifty_ai.data.schema import NormalizedMarketRecord


@dataclass(frozen=True)
class TargetReturn:
    """Represents next-session return prediction target for session T."""
    trading_date: date               # Session T (feature date)
    close: float                     # Close_T
    target_date: Optional[date]      # Session T+1 (None for terminal row)
    target_close: Optional[float]    # Close_{T+1} (None for terminal row)
    target_return: Optional[float]   # Close_{T+1} / Close_T - 1 (None for terminal row)


def compute_next_session_returns(
    records: List[NormalizedMarketRecord],
) -> List[TargetReturn]:
    """Calculate next-session close-to-close returns from chronologically ordered records.

    For record i (date T):
        target_date = records[i+1].trading_date
        target_close = records[i+1].close
        target_return = (records[i+1].close / records[i].close) - 1.0

    For the terminal record (last row in historical dataset):
        target_date = None
        target_close = None
        target_return = None
        (Never fabricate or forward-fill future targets)

    Args:
        records: Monotonically increasing list of NormalizedMarketRecord instances.

    Returns:
        List of TargetReturn objects aligned 1:1 with input records.
    """
    if not records:
        return []

    n = len(records)
    results: List[TargetReturn] = []

    for i in range(n):
        curr_rec = records[i]
        curr_date = curr_rec.trading_date
        curr_close = curr_rec.close

        if curr_close <= 0:
            raise ValueError(f"Encountered non-positive close price on {curr_date}: {curr_close}")

        if i < n - 1:
            next_rec = records[i + 1]
            if next_rec.trading_date <= curr_date:
                raise ValueError(
                    f"Chronological violation detected: {curr_date} >= {next_rec.trading_date}"
                )
            if next_rec.close <= 0:
                raise ValueError(f"Encountered non-positive next close price on {next_rec.trading_date}: {next_rec.close}")

            ret = (next_rec.close / curr_close) - 1.0
            results.append(
                TargetReturn(
                    trading_date=curr_date,
                    close=curr_close,
                    target_date=next_rec.trading_date,
                    target_close=next_rec.close,
                    target_return=ret,
                )
            )
        else:
            # Last available session has no realized future target
            results.append(
                TargetReturn(
                    trading_date=curr_date,
                    close=curr_close,
                    target_date=None,
                    target_close=None,
                    target_return=None,
                )
            )

    return results


__all__ = ["TargetReturn", "compute_next_session_returns"]
