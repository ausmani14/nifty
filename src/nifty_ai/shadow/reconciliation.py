"""Outcome reconciliation and forward evaluation reporting for Phase 14 Shadow System.

Calculates realized intraday targets (T0), performs exact temporal alignment,
computes forward evaluation metrics on genuine prospective sessions, and generates
tamper-evident research reports.
"""

from datetime import datetime, time, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats
from zoneinfo import ZoneInfo

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    ProvenanceType,
    RealizedOutcome,
)
from nifty_ai.shadow.ledger import ShadowPredictionLedger

MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")
MARKET_CLOSE_TIME = time(15, 30, 0)
HISTORICAL_TRAINING_MEAN = -0.000556  # -5.56 bps (frozen Phase 12-13 baseline)

DEFAULT_OUTCOMES_PATH = (
    PROJECT_ROOT / "data" / "interim" / "phase14_shadow" / "shadow_outcomes_ledger.jsonl"
)


class ShadowOutcomeReconciler:
    """Acquires realized outcomes, reconciles against predictions, and audits metrics."""

    def __init__(
        self,
        prediction_ledger: Optional[ShadowPredictionLedger] = None,
        outcomes_path: Path = DEFAULT_OUTCOMES_PATH,
    ):
        self.prediction_ledger = prediction_ledger or ShadowPredictionLedger()
        self.outcomes_path = outcomes_path
        self.outcomes_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.outcomes_path.exists():
            self.outcomes_path.touch()

    def get_all_outcomes(self) -> List[Dict[str, Any]]:
        """Read all reconciled outcomes from the outcomes ledger."""
        records = []
        with open(self.outcomes_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def has_session_outcome(self, session_date: str) -> bool:
        """Check if an outcome has already been recorded for this session date."""
        for rec in self.get_all_outcomes():
            if rec.get("session_date") == session_date:
                return True
        return False

    def reconcile_session(
        self,
        session_date: str,
        open_price: float,
        close_price: float,
        acquisition_time: datetime,
        data_source: str = "NSE_OFFICIAL_CASH",
    ) -> RealizedOutcome:
        """Reconcile realized session prices with existing pre-market shadow prediction."""
        # 1. Verify timing: Realization must be at or after market close (15:30 IST)
        acq_ist = acquisition_time.astimezone(MARKET_TIMEZONE)
        if acq_ist.time() < MARKET_CLOSE_TIME:
            raise ValueError(
                f"Cannot reconcile outcome prior to market close (15:30 IST): "
                f"acquisition time was {acq_ist.time()}."
            )

        # 2. Check input price validity
        if open_price <= 0.0 or close_price <= 0.0:
            raise ValueError(f"Invalid non-positive price: Open={open_price}, Close={close_price}")
        if math.isnan(open_price) or math.isnan(close_price) or math.isinf(open_price) or math.isinf(close_price):
            raise ValueError("NaN or infinite price encountered during reconciliation.")

        # 3. Locate matching pre-market prediction
        predictions = [
            p for p in self.prediction_ledger.get_all_records()
            if p.get("session_date") == session_date and p.get("snapshot_type") == "SNAPSHOT_0850"
        ]
        if not predictions:
            raise ValueError(
                f"No pre-market prediction found for session {session_date}. "
                f"Cannot reconcile unpredicted session outcome."
            )
        prediction_rec = predictions[0]

        # 4. Check if already reconciled (Idempotency)
        if self.has_session_outcome(session_date):
            existing = next(
                r for r in self.get_all_outcomes() if r["session_date"] == session_date
            )
            # Recreate RealizedOutcome object
            return RealizedOutcome(**existing)

        # 5. Compute exact T0 realized return
        realized_t0 = (close_price / open_price) - 1.0
        realized_t0_bps = realized_t0 * 10000.0

        predicted_return = float(prediction_rec["predicted_return"])
        prediction_error = predicted_return - realized_t0
        abs_error_bps = abs(prediction_error) * 10000.0

        dir_match = (
            (predicted_return > 0 and realized_t0 > 0)
            or (predicted_return < 0 and realized_t0 < 0)
            or (predicted_return == 0 and realized_t0 == 0)
        )

        outcome_id = f"out_{session_date}_T0"
        now_utc = datetime.now(timezone.utc)

        payload = {
            "outcome_id": outcome_id,
            "prediction_id": prediction_rec["prediction_id"],
            "session_date": session_date,
            "realized_open": open_price,
            "realized_close": close_price,
            "realized_t0": realized_t0,
            "realized_t0_bps": realized_t0_bps,
            "prediction_error": prediction_error,
            "absolute_error_bps": abs_error_bps,
            "directional_match": bool(dir_match),
            "acquisition_timestamp": now_utc.isoformat(),
            "data_source": data_source,
            "status": "RECONCILED",
        }
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        record_hash = hashlib.sha256(serialized).hexdigest()

        outcome = RealizedOutcome(
            outcome_id=outcome_id,
            prediction_id=prediction_rec["prediction_id"],
            session_date=session_date,
            realized_open=open_price,
            realized_close=close_price,
            realized_t0=realized_t0,
            realized_t0_bps=realized_t0_bps,
            prediction_error=prediction_error,
            absolute_error_bps=abs_error_bps,
            directional_match=bool(dir_match),
            acquisition_timestamp=now_utc,
            data_source=data_source,
            status="RECONCILED",
            record_hash=record_hash,
        )

        # Append to outcomes ledger
        with open(self.outcomes_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(outcome.to_dict(), sort_keys=True) + "\n")

        return outcome

    def compute_forward_metrics(
        self,
        filter_prospective_only: bool = True,
    ) -> Dict[str, Any]:
        """Compute statistical and econometric metrics across reconciled forward sessions."""
        preds = {p["prediction_id"]: p for p in self.prediction_ledger.get_all_records()}
        outcomes = self.get_all_outcomes()

        if not outcomes:
            return {
                "sample_size": 0,
                "status": "NO_RECONCILED_OUTCOMES",
                "message": "No prospective outcomes have accumulated yet.",
            }

        matched_pairs = []
        for out in outcomes:
            pred_id = out.get("prediction_id")
            if pred_id in preds:
                p = preds[pred_id]
                # Filter by prospective only if required
                if filter_prospective_only and p.get("provenance_type") != ProvenanceType.PROSPECTIVE_LIVE_CAPTURE.value:
                    continue
                matched_pairs.append({
                    "session_date": out["session_date"],
                    "y_pred": p["predicted_return"],
                    "y_true": out["realized_t0"],
                    "provenance_type": p.get("provenance_type"),
                })

        n = len(matched_pairs)
        if n == 0:
            return {
                "sample_size": 0,
                "status": "ZERO_QUALIFIED_PROSPECTIVE_SESSIONS",
                "message": "Outcomes exist but none qualify as genuine prospective live captures.",
            }

        df = pd.DataFrame(matched_pairs)
        y_pred = df["y_pred"].to_numpy()
        y_true = df["y_true"].to_numpy()

        # Correlation IC
        if n >= 2 and np.std(y_pred) > 1e-12 and np.std(y_true) > 1e-12:
            r_p, p_two = stats.pearsonr(y_pred, y_true)
            r_s, s_p = stats.spearmanr(y_pred, y_true)
            p_one = p_two / 2.0 if r_p > 0 else 1.0 - (p_two / 2.0)
        else:
            r_p, p_two, p_one, r_s, s_p = 0.0, 1.0, 0.5, 0.0, 1.0

        # Regression Errors
        mae_model = float(np.mean(np.abs(y_pred - y_true))) * 10000.0
        rmse_model = float(np.sqrt(np.mean((y_pred - y_true) ** 2))) * 10000.0

        # Zero-Return Benchmark Errors
        mae_zero = float(np.mean(np.abs(y_true))) * 10000.0
        rmse_zero = float(np.sqrt(np.mean(y_true ** 2))) * 10000.0

        # Training Mean Benchmark Errors
        mse_mean_bench = float(np.mean((HISTORICAL_TRAINING_MEAN - y_true) ** 2))
        mse_model = float(np.mean((y_pred - y_true) ** 2))
        incremental_r2 = float(1.0 - (mse_model / mse_mean_bench)) if mse_mean_bench > 1e-12 else 0.0

        # Directional Metrics
        mda_model = float(np.mean(np.sign(y_pred) == np.sign(y_true))) * 100.0
        always_short_mda = float(np.mean(np.sign(-1.0) == np.sign(y_true))) * 100.0

        # Distribution
        pos_preds = int(np.sum(y_pred > 0))
        neg_preds = int(np.sum(y_pred < 0))
        flat_preds = int(np.sum(y_pred == 0))

        return {
            "sample_size": n,
            "period_start": df["session_date"].min(),
            "period_end": df["session_date"].max(),
            "pearson_ic": float(r_p),
            "pearson_p_twosided": float(p_two),
            "pearson_p_onesided": float(p_one),
            "spearman_ic": float(r_s),
            "spearman_p": float(s_p),
            "model_mae_bps": mae_model,
            "model_rmse_bps": rmse_model,
            "zero_benchmark_mae_bps": mae_zero,
            "zero_benchmark_rmse_bps": rmse_zero,
            "incremental_r2": incremental_r2,
            "model_mda_pct": mda_model,
            "always_short_mda_pct": always_short_mda,
            "long_prediction_count": pos_preds,
            "short_prediction_count": neg_preds,
            "flat_prediction_count": flat_preds,
        }
