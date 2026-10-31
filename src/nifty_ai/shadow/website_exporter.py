"""Website Data Exporter for NIFTY AI.

Exports static, sanitized, machine-readable JSON artifacts into website_data/
for consumption by the frontend dashboard.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import CANONICAL_MODEL_SHA256
from nifty_ai.shadow.ledger import ShadowPredictionLedger
from nifty_ai.shadow.model_protection import audit_frozen_model_protection
from nifty_ai.shadow.reconciliation import ShadowOutcomeReconciler

DEFAULT_WEBSITE_DATA_DIR = PROJECT_ROOT / "website_data"
DEFAULT_WEB_MIRROR_DIR = PROJECT_ROOT / "web" / "data"
MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


class WebsiteDataExporter:
    """Generates standardized, presentation-ready JSON files for the website."""

    def __init__(
        self,
        output_dir: Path = DEFAULT_WEBSITE_DATA_DIR,
        mirror_dir: Optional[Path] = DEFAULT_WEB_MIRROR_DIR,
        prediction_ledger: Optional[ShadowPredictionLedger] = None,
        outcome_reconciler: Optional[ShadowOutcomeReconciler] = None,
    ):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.mirror_dir = mirror_dir
        if self.mirror_dir:
            self.mirror_dir.mkdir(parents=True, exist_ok=True)
        self.prediction_ledger = prediction_ledger or ShadowPredictionLedger()
        self.outcome_reconciler = outcome_reconciler or ShadowOutcomeReconciler(
            prediction_ledger=self.prediction_ledger
        )

    def _write_json(self, filename: str, payload: Dict[str, Any]) -> Path:
        """Write JSON payload to output directory and optional mirror directory."""
        primary_path = self.output_dir / filename
        with open(primary_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        if self.mirror_dir:
            mirror_path = self.mirror_dir / filename
            with open(mirror_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        return primary_path

    def export_all(
        self,
        current_system_state: str = "IMPLEMENTED — WAITING FOR LIVE INPUT",
        latest_error: Optional[str] = None,
    ) -> Dict[str, Path]:
        """Export all 6 standard website JSON artifacts."""
        paths = {}
        paths["latest_prediction"] = self.export_latest_prediction(latest_error=latest_error)
        paths["prediction_history"] = self.export_prediction_history()
        paths["outcome_history"] = self.export_outcome_history()
        paths["system_status"] = self.export_system_status(current_system_state=current_system_state, latest_error=latest_error)
        paths["model_info"] = self.export_model_info()
        paths["performance_summary"] = self.export_performance_summary()
        return paths

    def export_latest_prediction(self, latest_error: Optional[str] = None) -> Path:
        predictions = self.prediction_ledger.get_all_records()
        outcomes = {o["prediction_id"]: o for o in self.outcome_reconciler.get_all_outcomes()}
        now_utc = datetime.now(timezone.utc).isoformat()

        if not predictions:
            status_label = "NO VALID PROSPECTIVE PREDICTION"
            if latest_error:
                status_label = latest_error

            payload = {
                "has_prediction": False,
                "prediction_id": None,
                "prediction_date": None,
                "target_date": None,
                "snapshot": "SNAPSHOT_0850",
                "expected_return": None,
                "expected_return_bps": None,
                "directional_bias": "NEUTRAL",
                "prediction_status": status_label,
                "outcome_status": "N/A",
                "model_name": "Snapshot B T0 Full Development Production Model",
                "model_sha256": CANONICAL_MODEL_SHA256,
                "information_cutoff": "08:50:00 Asia/Kolkata",
                "last_updated_utc": now_utc,
                "message": "No prospective predictions recorded yet. Ledger is in genesis state.",
            }
        else:
            latest = predictions[-1]
            p_id = latest["prediction_id"]
            has_outcome = p_id in outcomes
            outcome_status = "RECONCILED" if has_outcome else "RECONCILIATION PENDING"
            pred_val = float(latest["predicted_return"])
            dir_bias = "POSITIVE" if pred_val > 0 else ("NEGATIVE" if pred_val < 0 else "NEUTRAL")

            payload = {
                "has_prediction": True,
                "prediction_id": p_id,
                "prediction_date": latest["session_date"],
                "target_date": latest["target_date"],
                "snapshot": latest.get("snapshot_type", "SNAPSHOT_0850"),
                "expected_return": pred_val,
                "expected_return_bps": float(latest.get("predicted_return_bps", pred_val * 10000.0)),
                "directional_bias": dir_bias,
                "prediction_status": "VALID",
                "outcome_status": outcome_status,
                "realized_outcome": outcomes[p_id] if has_outcome else None,
                "model_name": latest.get("model_name"),
                "model_sha256": latest.get("model_sha256"),
                "information_cutoff": "08:50:00 Asia/Kolkata",
                "last_updated_utc": now_utc,
                "message": "Prospective prediction active.",
            }

        return self._write_json("latest_prediction.json", payload)

    def export_prediction_history(self) -> Path:
        predictions = self.prediction_ledger.get_all_records()
        return self._write_json(
            "prediction_history.json",
            {"total_count": len(predictions), "predictions": predictions},
        )

    def export_outcome_history(self) -> Path:
        outcomes = self.outcome_reconciler.get_all_outcomes()
        return self._write_json(
            "outcome_history.json",
            {"total_count": len(outcomes), "outcomes": outcomes},
        )

    def export_system_status(
        self,
        current_system_state: str = "IMPLEMENTED — WAITING FOR LIVE INPUT",
        latest_error: Optional[str] = None,
    ) -> Path:
        now_utc = datetime.now(timezone.utc).isoformat()
        model_report = audit_frozen_model_protection()

        preds = self.prediction_ledger.get_all_records()
        outcomes = self.outcome_reconciler.get_all_outcomes()
        is_valid_chain, issues = self.prediction_ledger.verify_integrity()

        payload = {
            "current_system_state": current_system_state,
            "last_updated_utc": now_utc,
            "timezone": "Asia/Kolkata",
            "model_integrity": {
                "is_intact": model_report.is_intact,
                "status": "PASS" if model_report.is_intact else "MODEL_INTEGRITY_FAILURE",
                "model_sha256": model_report.model_sha256,
                "n_estimators": model_report.n_estimators,
                "feature_count": model_report.feature_count,
            },
            "ledger_integrity": {
                "is_valid": is_valid_chain,
                "prediction_count": len(preds),
                "outcome_count": len(outcomes),
                "tip_hash": self.prediction_ledger.get_tip_hash(),
                "chain_issues": issues,
            },
            "scheduler_status": "ENABLED",
            "latest_error": latest_error,
            "research_status": "RESEARCH_BASELINE_ONLY",
            "trading_authorized": False,
        }

        return self._write_json("system_status.json", payload)

    def export_model_info(self) -> Path:
        payload = {
            "model_name": "Snapshot B T0 Full Development Production Model",
            "algorithm": "xgboost.XGBRegressor",
            "model_classification": "RESEARCH BASELINE ONLY",
            "production_promotion_status": "REJECTED (Phase 13 Step 5 Decision Gate)",
            "live_trading_authorized": False,
            "target": "Snapshot B T0 (Intraday Return: Close / Open - 1)",
            "information_cutoff": "08:50:00 Asia/Kolkata",
            "training_boundary": "2008-07-08 to 2021-12-31 (N=3,299)",
            "frozen_tree_count": 43,
            "total_feature_count": 63,
            "price_feature_count": 45,
            "context_feature_count": 18,
            "forbidden_features": "News, Volume, and Flow features strictly excluded",
            "governance_disclaimer": (
                "NIFTY AI daytime return models operate strictly as research baselines. "
                "Retrospective out-of-sample evaluation demonstrated an unhedged Pearson IC of +0.0201 (p=0.4945) "
                "and negative net returns under realistic market frictions. "
                "Forecasts are observational research only and do not constitute trading signals or financial advice."
            ),
        }
        return self._write_json("model_info.json", payload)

    def export_performance_summary(self) -> Path:
        metrics = self.outcome_reconciler.compute_forward_metrics(filter_prospective_only=True)
        payload = {
            "prospective_metrics": metrics,
            "checkpoints": {
                "checkpoint_1_n60": {"target_n": 60, "scope": "Operational integrity review only (No promotion)"},
                "checkpoint_2_n120": {"target_n": 120, "scope": "Interim descriptive review (No promotion)"},
                "checkpoint_3_n252": {"target_n": 252, "scope": "Annual formal econometric evaluation"},
            },
            "last_evaluated_utc": datetime.now(timezone.utc).isoformat(),
        }
        return self._write_json("performance_summary.json", payload)
