"""Scientific analysis and evaluation engine for candidate SIDEWAYS thresholds.

Analyzes candidate threshold methodologies using multi-criteria diagnostics:
- Statistical threshold distribution (mean, standard deviation, min, max)
- Chronological era stability across market cycles
- Volatility regime sensitivity (behavior in low vs. high volatility regimes)
- Directional class balance (UP / DOWN ratio)
- SIDEWAYS proportion as a post-hoc diagnostic only (NOT an optimization objective)

Enforces strict walk-forward discipline: methodology evaluation is conducted
exclusively on the development partition (<= 2021-12-31). The out-of-sample holdout
partition (>= 2022-01-01) is strictly audited post-hoc.
"""

from dataclasses import asdict, dataclass
from datetime import date
import json
import math
from pathlib import Path
import statistics
from typing import Any, Dict, List, Optional, Tuple

from nifty_ai.data.schema import NormalizedMarketRecord
from nifty_ai.targets.classification import ClassifiedTarget, classify_targets
from nifty_ai.targets.returns import TargetReturn, compute_next_session_returns
from nifty_ai.targets.thresholds import (
    EmpiricalDistributionThreshold,
    FixedThreshold,
    ThresholdMethod,
    VolatilityScaledThreshold,
    compute_rolling_thresholds,
)


@dataclass
class PeriodDistribution:
    """Class distribution metrics for a specific chronological window."""
    period_name: str
    start_date: str
    end_date: str
    total_classified: int
    up_count: int
    down_count: int
    sideways_count: int
    up_pct: float
    down_pct: float
    sideways_pct: float
    up_down_ratio: float
    mean_threshold: float


@dataclass
class VolatilityRegimeAnalysis:
    """Behavior of threshold under low vs high market volatility."""
    metric_name: str
    median_volatility: float
    low_vol_count: int
    low_vol_sideways_pct: float
    low_vol_up_pct: float
    low_vol_down_pct: float
    high_vol_count: int
    high_vol_sideways_pct: float
    high_vol_up_pct: float
    high_vol_down_pct: float
    sideways_pct_spread: float  # High vol sideways % - low vol sideways %


@dataclass
class MethodEvaluation:
    """Comprehensive diagnostic metrics for one candidate threshold configuration."""
    method_name: str
    parameters: Dict[str, Any]
    partition: str  # "development" or "full"
    total_rows: int
    classified_rows: int
    warmup_rows: int
    terminal_unlabeled_rows: int
    class_counts: Dict[str, int]
    class_distribution: Dict[str, float]  # Post-hoc diagnostic
    up_down_ratio: float
    sideways_pct: float  # Post-hoc diagnostic
    threshold_mean: float
    threshold_stdev: float
    threshold_min: float
    threshold_max: float
    periods: List[PeriodDistribution]
    volatility_regime: Optional[VolatilityRegimeAnalysis]
    statistical_rationale: str


@dataclass
class AnalysisReport:
    """Complete multi-method comparison report and final selection recommendation."""
    development_end_date: str
    total_methods_evaluated: int
    evaluations: List[MethodEvaluation]
    recommended_method: str
    recommended_parameters: Dict[str, Any]
    recommendation_rationale: str
    holdout_validation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_json(self, file_path: Path) -> Path:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return file_path


class ThresholdAnalyzer:
    """Evaluates candidate SIDEWAYS threshold methodologies on historical data."""

    def __init__(
        self,
        development_end_date: date = date(2021, 12, 31),
    ) -> None:
        self.development_end_date = development_end_date

    def evaluate_method(
        self,
        method: ThresholdMethod,
        records: List[NormalizedMarketRecord],
        target_returns: Optional[List[TargetReturn]] = None,
        use_development_only: bool = True,
    ) -> MethodEvaluation:
        """Evaluate a single threshold method using multi-criteria diagnostics."""
        if target_returns is None:
            target_returns = compute_next_session_returns(records)

        dates = [r.trading_date for r in records]
        daily_returns: List[Optional[float]] = [None] * len(records)
        for i in range(1, len(records)):
            daily_returns[i] = (records[i].close / records[i - 1].close) - 1.0

        # Compute rolling thresholds strictly point-in-time
        thresh_results = compute_rolling_thresholds(method, dates, daily_returns)
        classified_targets = classify_targets(target_returns, thresh_results)

        # Filter to development partition if requested
        if use_development_only:
            partition_name = "development"
            eval_targets = [
                ct for ct in classified_targets
                if ct.trading_date <= self.development_end_date
            ]
            eval_records = [
                r for r in records
                if r.trading_date <= self.development_end_date
            ]
        else:
            partition_name = "full"
            eval_targets = classified_targets
            eval_records = records

        total_rows = len(eval_targets)
        classified_rows_list = [ct for ct in eval_targets if ct.is_classified]
        classified_count = len(classified_rows_list)
        warmup_count = sum(1 for ct in eval_targets if not ct.has_threshold)
        terminal_count = sum(1 for ct in eval_targets if not ct.has_target)

        # Class counts (observed post-hoc)
        up_count = sum(1 for ct in classified_rows_list if ct.target_direction == "UP")
        down_count = sum(1 for ct in classified_rows_list if ct.target_direction == "DOWN")
        sideways_count = sum(1 for ct in classified_rows_list if ct.target_direction == "SIDEWAYS")

        up_pct = (up_count / classified_count) * 100 if classified_count > 0 else 0.0
        down_pct = (down_count / classified_count) * 100 if classified_count > 0 else 0.0
        sideways_pct = (sideways_count / classified_count) * 100 if classified_count > 0 else 0.0
        up_down_ratio = (up_count / down_count) if down_count > 0 else float("nan")

        # Threshold distribution statistics
        threshold_vals = [
            ct.threshold_value for ct in classified_rows_list
            if ct.threshold_value is not None
        ]
        thresh_mean = statistics.mean(threshold_vals) if threshold_vals else 0.0
        thresh_stdev = statistics.stdev(threshold_vals) if len(threshold_vals) > 1 else 0.0
        thresh_min = min(threshold_vals) if threshold_vals else 0.0
        thresh_max = max(threshold_vals) if threshold_vals else 0.0

        # Sub-period chronological stability analysis
        periods = self._analyze_periods(classified_rows_list)

        # Volatility regime sensitivity analysis
        vol_regime = self._analyze_volatility_regimes(eval_records, classified_rows_list)

        # Statistical rationale per method family
        if method.name == "volatility_scaled":
            k = method.parameters.get("k", 0.35)
            w = method.parameters.get("window", 20)
            rationale = (
                f"Econometrically grounded in realized return dispersion: theta_t = {k} * sigma_{w}(t). "
                f"Represents a {k:.2f} standard deviation band of trailing {w}-day daily returns. "
                "Dynamically expands in turbulent regimes and compresses in calm regimes."
            )
        elif method.name == "empirical_distribution":
            p = method.parameters.get("percentile", 25.0)
            w = method.parameters.get("window", 252)
            rationale = (
                f"Empirical quantile noise filter: theta_t = percentile_{p}(|r|_{w}). "
                f"Directly isolates the lowest {p:.1f}% of absolute price fluctuations over trailing {w} sessions."
            )
        else:
            v = method.parameters.get("value", 0.005)
            rationale = (
                f"Fixed baseline benchmark: theta_t = {v * 100:.2f}% constant. "
                "Rigid boundary without dynamic adjustment across market cycles."
            )

        return MethodEvaluation(
            method_name=method.name,
            parameters=method.parameters,
            partition=partition_name,
            total_rows=total_rows,
            classified_rows=classified_count,
            warmup_rows=warmup_count,
            terminal_unlabeled_rows=terminal_count,
            class_counts={"UP": up_count, "DOWN": down_count, "SIDEWAYS": sideways_count},
            class_distribution={"UP": round(up_pct, 2), "DOWN": round(down_pct, 2), "SIDEWAYS": round(sideways_pct, 2)},
            up_down_ratio=round(up_down_ratio, 3),
            sideways_pct=round(sideways_pct, 2),
            threshold_mean=round(thresh_mean, 6),
            threshold_stdev=round(thresh_stdev, 6),
            threshold_min=round(thresh_min, 6),
            threshold_max=round(thresh_max, 6),
            periods=periods,
            volatility_regime=vol_regime,
            statistical_rationale=rationale,
        )

    def _analyze_periods(
        self,
        classified_targets: List[ClassifiedTarget],
    ) -> List[PeriodDistribution]:
        """Examine class distribution stability across meaningful historical market eras."""
        era_definitions = [
            ("Early Period (2007-2013)", date(2007, 1, 1), date(2013, 12, 31)),
            ("Middle Period (2014-2018)", date(2014, 1, 1), date(2018, 12, 31)),
            ("Recent Dev Period (2019-2021)", date(2019, 1, 1), date(2021, 12, 31)),
        ]

        period_results: List[PeriodDistribution] = []

        for name, start_d, end_d in era_definitions:
            targets_in_era = [
                ct for ct in classified_targets
                if start_d <= ct.trading_date <= end_d and ct.is_classified
            ]
            count = len(targets_in_era)
            if count == 0:
                continue

            up = sum(1 for ct in targets_in_era if ct.target_direction == "UP")
            down = sum(1 for ct in targets_in_era if ct.target_direction == "DOWN")
            sideways = sum(1 for ct in targets_in_era if ct.target_direction == "SIDEWAYS")
            up_pct = (up / count) * 100.0
            down_pct = (down / count) * 100.0
            sideways_pct = (sideways / count) * 100.0
            ratio = (up / down) if down > 0 else float("nan")

            thresh_vals = [ct.threshold_value for ct in targets_in_era if ct.threshold_value is not None]
            m_thresh = statistics.mean(thresh_vals) if thresh_vals else 0.0

            period_results.append(
                PeriodDistribution(
                    period_name=name,
                    start_date=start_d.isoformat(),
                    end_date=end_d.isoformat(),
                    total_classified=count,
                    up_count=up,
                    down_count=down,
                    sideways_count=sideways,
                    up_pct=round(up_pct, 2),
                    down_pct=round(down_pct, 2),
                    sideways_pct=round(sideways_pct, 2),
                    up_down_ratio=round(ratio, 3),
                    mean_threshold=round(m_thresh, 6),
                )
            )

        return period_results

    def _analyze_volatility_regimes(
        self,
        records: List[NormalizedMarketRecord],
        classified_targets: List[ClassifiedTarget],
    ) -> Optional[VolatilityRegimeAnalysis]:
        """Evaluate threshold behavior under low vs high market volatility regimes."""
        if len(records) < 70 or not classified_targets:
            return None

        # Compute trailing 60d volatility for each record to proxy regime
        daily_returns = [0.0] * len(records)
        for i in range(1, len(records)):
            daily_returns[i] = (records[i].close / records[i - 1].close) - 1.0

        vol_by_date: Dict[date, float] = {}
        for i in range(60, len(records)):
            w = daily_returns[i - 59 : i + 1]
            vol_by_date[records[i].trading_date] = statistics.stdev(w)

        classified_with_vol = [
            (ct, vol_by_date[ct.trading_date])
            for ct in classified_targets
            if ct.trading_date in vol_by_date
        ]
        if len(classified_with_vol) < 50:
            return None

        all_vols = [item[1] for item in classified_with_vol]
        med_vol = statistics.median(all_vols)

        low_vol_items = [ct for ct, v in classified_with_vol if v <= med_vol]
        high_vol_items = [ct for ct, v in classified_with_vol if v > med_vol]

        def _calc_pcts(items: List[ClassifiedTarget]) -> Tuple[float, float, float]:
            n = len(items)
            if n == 0:
                return 0.0, 0.0, 0.0
            u = sum(1 for x in items if x.target_direction == "UP") / n * 100
            d = sum(1 for x in items if x.target_direction == "DOWN") / n * 100
            s = sum(1 for x in items if x.target_direction == "SIDEWAYS") / n * 100
            return round(u, 2), round(d, 2), round(s, 2)

        low_u, low_d, low_s = _calc_pcts(low_vol_items)
        high_u, high_d, high_s = _calc_pcts(high_vol_items)

        return VolatilityRegimeAnalysis(
            metric_name="trailing_60d_realized_volatility",
            median_volatility=round(med_vol, 6),
            low_vol_count=len(low_vol_items),
            low_vol_sideways_pct=low_s,
            low_vol_up_pct=low_u,
            low_vol_down_pct=low_d,
            high_vol_count=len(high_vol_items),
            high_vol_sideways_pct=high_s,
            high_vol_up_pct=high_u,
            high_vol_down_pct=high_d,
            sideways_pct_spread=round(high_s - low_s, 2),
        )

    def run_full_comparison(
        self,
        records: List[NormalizedMarketRecord],
    ) -> AnalysisReport:
        """Run multi-criteria diagnostic evaluation of candidate methods without artificial scoring."""
        target_returns = compute_next_session_returns(records)

        candidate_methods: List[ThresholdMethod] = [
            # Method A: Volatility-scaled (Primary Specification, MASTER_SPECIFICATION Section 5.2)
            VolatilityScaledThreshold(k=0.35, window=20),  # Frozen Baseline
            VolatilityScaledThreshold(k=0.30, window=20),
            VolatilityScaledThreshold(k=0.25, window=20),
            VolatilityScaledThreshold(k=0.40, window=20),
            VolatilityScaledThreshold(k=0.50, window=20),
            VolatilityScaledThreshold(k=0.35, window=60),
            # Method B: Empirical return-distribution (Alternative candidate)
            EmpiricalDistributionThreshold(percentile=25.0, window=252),
            EmpiricalDistributionThreshold(percentile=30.0, window=252),
            EmpiricalDistributionThreshold(percentile=35.0, window=252),
            EmpiricalDistributionThreshold(percentile=40.0, window=252),
            # Method C: Fixed baseline (Rigid comparison benchmark)
            FixedThreshold(value=0.0030),  # 0.30%
            FixedThreshold(value=0.0050),  # 0.50%
            FixedThreshold(value=0.0075),  # 0.75%
        ]

        evaluations: List[MethodEvaluation] = []
        for method in candidate_methods:
            eval_res = self.evaluate_method(
                method=method,
                records=records,
                target_returns=target_returns,
                use_development_only=True,
            )
            evaluations.append(eval_res)

        # Frozen methodology per MASTER_SPECIFICATION.md Section 5.2: Method A, k=0.35, window=20
        selected_method_name = "volatility_scaled"
        selected_parameters: Dict[str, Any] = {"k": 0.35, "window": 20}

        rationale = (
            "Grounded in financial econometric theory per MASTER_SPECIFICATION Section 5.2: "
            "the threshold represents a dynamic boundary scaled directly to trailing 20-day realized "
            "volatility (theta_t = 0.35 * sigma_20). This provides an economically interpretable, "
            "dimensionally consistent standard deviation unit (0.35 standard deviations of daily price variation), "
            "expanding during high-volatility turbulence and compressing during low-volatility regimes. "
            "Class proportions (such as SIDEWAYS percentage) are evaluated strictly as post-hoc diagnostics "
            "and were NOT used as an optimization target or selection score."
        )

        # Audit out-of-sample holdout partition (>= 2022-01-01) strictly post-hoc
        holdout_targets = [
            ct for ct in classify_targets(
                target_returns,
                compute_rolling_thresholds(
                    VolatilityScaledThreshold(**selected_parameters),
                    [r.trading_date for r in records],
                    [
                        ((records[i].close / records[i - 1].close) - 1.0) if i > 0 else None
                        for i in range(len(records))
                    ],
                ),
            )
            if ct.trading_date > self.development_end_date and ct.is_classified
        ]

        holdout_summary = None
        if holdout_targets:
            h_count = len(holdout_targets)
            h_up = sum(1 for x in holdout_targets if x.target_direction == "UP")
            h_down = sum(1 for x in holdout_targets if x.target_direction == "DOWN")
            h_side = sum(1 for x in holdout_targets if x.target_direction == "SIDEWAYS")
            holdout_summary = {
                "period": f"{self.development_end_date.isoformat()} to {records[-1].trading_date.isoformat()}",
                "total_rows": h_count,
                "up_pct": round(h_up / h_count * 100, 2),
                "down_pct": round(h_down / h_count * 100, 2),
                "sideways_pct": round(h_side / h_count * 100, 2),
                "up_down_ratio": round(h_up / h_down, 3) if h_down > 0 else float("nan"),
            }

        return AnalysisReport(
            development_end_date=self.development_end_date.isoformat(),
            total_methods_evaluated=len(candidate_methods),
            evaluations=evaluations,
            recommended_method=selected_method_name,
            recommended_parameters=selected_parameters,
            recommendation_rationale=rationale,
            holdout_validation=holdout_summary,
        )


__all__ = [
    "PeriodDistribution",
    "VolatilityRegimeAnalysis",
    "MethodEvaluation",
    "AnalysisReport",
    "ThresholdAnalyzer",
]
