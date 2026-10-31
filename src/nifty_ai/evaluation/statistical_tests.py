"""Statistical hypothesis testing and confidence interval estimators for time series models.

Implements rigorous tests that account for time-series autocorrelation and heteroskedasticity:
- Diebold-Mariano Test with Newey-West HAC variance and Harvey-Leybourne-Newey correction
- Stationary Block Bootstrap for paired loss differences and Cohen's d effect sizes
"""

from dataclasses import dataclass
import math
from typing import Dict, Optional, Tuple
import numpy as np
from scipy import stats


@dataclass(frozen=True)
class DieboldMarianoResult:
    """Output results of the Diebold-Mariano test comparing two forecast models."""
    test_statistic: float
    p_value: float
    mean_loss_diff: float            # Positive indicates model 2 has lower loss (model 2 is better)
    hac_standard_error: float
    confidence_interval_95: Tuple[float, float]
    hln_corrected_statistic: float
    hln_p_value: float
    interpretation: str


@dataclass(frozen=True)
class BootstrapComparisonResult:
    """Output of stationary block bootstrap comparison between two classification models."""
    mean_loss_diff: float            # Positive indicates model 2 has lower loss
    ci_lower: float
    ci_upper: float
    cohens_d: float
    significant_at_05: bool
    interpretation: str


def diebold_mariano_test(
    y_true: np.ndarray,
    y_pred1: np.ndarray,
    y_pred2: np.ndarray,
    h: int = 1,
    loss_type: str = "absolute",
) -> DieboldMarianoResult:
    """Compute the Diebold-Mariano test with Newey-West HAC variance and HLN correction.

    Tests null hypothesis H0: E[d_t] = 0 (both models have equal forecast accuracy)
    against alternative H1: E[d_t] != 0.

    Args:
        y_true: Ground truth target return series.
        y_pred1: Baseline model predictions.
        y_pred2: Candidate model predictions (e.g. XGBoost).
        h: Forecast horizon (h=1 for next-session returns).
        loss_type: "absolute" for L1 loss |e| or "squared" for L2 loss e^2.

    Returns:
        DieboldMarianoResult containing HAC test statistics and confidence intervals.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred1 = np.asarray(y_pred1, dtype=np.float64)
    y_pred2 = np.asarray(y_pred2, dtype=np.float64)

    n = len(y_true)
    if n < 30:
        raise ValueError(f"Sample size too small for reliable asymptotic test: N={n}")

    e1 = y_true - y_pred1
    e2 = y_true - y_pred2

    if loss_type == "absolute":
        loss1 = np.abs(e1)
        loss2 = np.abs(e2)
    elif loss_type == "squared":
        loss1 = e1 ** 2
        loss2 = e2 ** 2
    else:
        raise ValueError(f"Unsupported loss_type: {loss_type}")

    # Loss differential d_t = Loss(Model 1) - Loss(Model 2)
    # Positive d_t means Model 2 has LOWER error (Model 2 is better)
    d = loss1 - loss2
    mean_d = float(np.mean(d))

    # Newey-West HAC variance estimator with Bartlett kernel
    # Lag truncation parameter K = floor(4 * (N/100)^(2/9))
    K = int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0))))
    K = max(1, K)

    d_centered = d - mean_d
    gamma_0 = float(np.dot(d_centered, d_centered) / n)
    gamma_sum = 0.0

    for k in range(1, K + 1):
        weight = 1.0 - (k / (K + 1.0))
        gamma_k = float(np.dot(d_centered[k:], d_centered[:-k]) / n)
        gamma_sum += 2.0 * weight * gamma_k

    long_run_var = max(1e-12, gamma_0 + gamma_sum)
    hac_se = float(math.sqrt(long_run_var / n))

    dm_stat = mean_d / hac_se if hac_se > 0 else 0.0
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(dm_stat))))

    # Harvey, Leybourne, and Newey (1997) finite sample correction
    # HLN factor = sqrt((n + 1 - 2*h + h*(h-1)/n) / n)
    hln_factor = math.sqrt((n + 1 - 2 * h + (h * (h - 1)) / n) / n)
    hln_stat = dm_stat * hln_factor
    hln_p_val = float(2.0 * (1.0 - stats.t.cdf(abs(hln_stat), df=n - 1)))

    ci_lower = mean_d - (1.96 * hac_se)
    ci_upper = mean_d + (1.96 * hac_se)

    if hln_p_val < 0.05:
        if mean_d > 0:
            interp = "Candidate model significantly outperforms baseline (p < 0.05, positive loss reduction)."
        else:
            interp = "Baseline significantly outperforms candidate model (p < 0.05, candidate has higher loss)."
    else:
        interp = "No statistically significant difference in forecast accuracy (p >= 0.05)."

    return DieboldMarianoResult(
        test_statistic=float(dm_stat),
        p_value=float(p_val),
        mean_loss_diff=mean_d,
        hac_standard_error=hac_se,
        confidence_interval_95=(float(ci_lower), float(ci_upper)),
        hln_corrected_statistic=float(hln_stat),
        hln_p_value=float(hln_p_val),
        interpretation=interp,
    )


def paired_bootstrap_loss_difference(
    y_true: np.ndarray,
    probs_baseline: np.ndarray,
    probs_candidate: np.ndarray,
    block_size: int = 10,
    n_bootstrap: int = 1000,
    random_seed: int = 42,
) -> BootstrapComparisonResult:
    """Stationary block bootstrap for multiclass log-loss difference.

    Computes paired loss differential: d_t = LogLoss(baseline)_t - LogLoss(candidate)_t
    Positive d_t indicates candidate model achieves lower cross-entropy error.
    """
    rng = np.random.default_rng(random_seed)
    n = len(y_true)
    eps = 1e-15

    # Clip probabilities to avoid log(0)
    p_base = np.clip(probs_baseline, eps, 1.0 - eps)
    p_cand = np.clip(probs_candidate, eps, 1.0 - eps)

    # Compute per-observation negative log likelihood
    loss_base = np.array([-math.log(p_base[i, y_true[i]]) for i in range(n)])
    loss_cand = np.array([-math.log(p_cand[i, y_true[i]]) for i in range(n)])

    diff_series = loss_base - loss_cand
    mean_diff = float(np.mean(diff_series))
    std_diff = float(np.std(diff_series, ddof=1)) if n > 1 else 1.0
    cohens_d = mean_diff / std_diff if std_diff > 0 else 0.0

    # Block bootstrap
    n_blocks = int(math.ceil(n / block_size))
    boot_means = []

    for _ in range(n_bootstrap):
        start_indices = rng.integers(0, n - block_size + 1, size=n_blocks)
        sampled_indices = []
        for s in start_indices:
            sampled_indices.extend(range(s, s + block_size))
        sampled_indices = sampled_indices[:n]

        boot_sample = diff_series[sampled_indices]
        boot_means.append(float(np.mean(boot_sample)))

    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))

    is_significant = (ci_lower > 0.0) or (ci_upper < 0.0)

    if is_significant:
        if mean_diff > 0:
            interp = f"Candidate achieves statistically significant log-loss reduction (95% CI: [{ci_lower:.5f}, {ci_upper:.5f}])."
        else:
            interp = f"Baseline achieves statistically significant lower log-loss (95% CI: [{ci_lower:.5f}, {ci_upper:.5f}])."
    else:
        interp = f"Difference not statistically significant; 95% CI spans zero: [{ci_lower:.5f}, {ci_upper:.5f}], Cohen's d = {cohens_d:.3f}."

    return BootstrapComparisonResult(
        mean_loss_diff=mean_diff,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        cohens_d=float(cohens_d),
        significant_at_05=bool(is_significant),
        interpretation=interp,
    )


__all__ = [
    "DieboldMarianoResult",
    "BootstrapComparisonResult",
    "diebold_mariano_test",
    "paired_bootstrap_loss_difference",
]
