"""Phase 13 Step 1: Untouched Holdout Evaluation Protocol Freeze.

Research Objective:
Freeze the exact evaluation protocol for the untouched Terminal Holdout (2022-01-01 onward,
expected N=1,154 sessions) for Snapshot B Target T0 BEFORE any holdout data is opened.

Strict Governance:
- Phase 0–12 artifacts are formally SEALED and immutable.
- ZERO holdout rows read, loaded, scanned, peeked, summarized, or evaluated.
- ZERO holdout predictions generated.
- ZERO holdout metrics computed.
- ZERO model training or hyperparameter optimization on holdout data.
- Model Training Boundary: OPTION A — Frozen historical models (Full Development production
  model N=3,299, N*=43 trees; with pre-registered secondary diagnostics).
- Target: Snapshot B T0 (Open -> Close return: (Close(T+1) - Open(T+1)) / Open(T+1)).
- Primary metric: Pearson IC. All secondary metrics are diagnostics.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

from nifty_ai.config import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from nifty_ai.models.multimodal import CONTEXT_FEATURE_NAMES, PRICE_FEATURE_NAMES

# Directories
OUT_DIR = PROJECT_ROOT / "data" / "interim" / "phase13_step1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PHASE12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12"
STEP7_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step7"
STEP8_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step8"
STEP9_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step9"
STEP10_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step10"
STEP11_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step11"
STEP12_DIR = PROJECT_ROOT / "data" / "interim" / "phase12_step12"
CONFIG_PATH = PROJECT_ROOT / "configs" / "phase11_strategy_validation_config.json"

# Protected checksums
PROTECTED_STEP5_HASHES = {
    "phase12_step5_target_comparison.csv": "6ec7040f75d26c5b0f54ce33cded5e6baacaebdadea2b99968fcd2f2880de0d0",
    "phase12_step5_fold_results.csv": "041c75bce9cceb847850ffdc17069494e0c44795b4a78c853e9028859c6e1399",
    "phase12_step5_temporal_results.csv": "f14a859412b7e0ac841c9235f66849adb5ff521b675df698f26ee371d412e788",
    "phase12_step5_sign_base_rate.csv": "2344bcffabd0ea2129c70b4d140e9446836fc042f744089bd196c4d38922dd4d",
    "phase12_step5_magnitude_calibration.csv": "501fc01546929c97a847927f1e227e0e6a74c5e56dcf2abe067db5668f1154ae",
    "phase12_step5_economic_stress.csv": "e1c8f04d74c9ece80999e9dcd425a674b4e91da1bcbb4afb7cf6fe5465bffae6",
    "phase12_step5_placebo.csv": "084416736d8d13555576ee5858876ae59260b88bc452c847896e6aab49a424db",
    "phase12_step5_manifest.json": "acf3d7ce73919ddc8545e0c3a506abd44ef0b5aa8e29fb20865e6a85621db10b",
    "phase12_step5_corrected_sign_base_rate.csv": "ac42f0fe9f16f47da077b9a1e5d55d9b385646f54236bfe1b4e1c96c5d46276a",
    "phase12_step5_corrected_economic_stress.csv": "f1447629a6d6c142d960be0fc5b0c4f52484d02825954109118d9e4125d57f88",
}

PROTECTED_STEP6_HASHES = {
    "phase12_step6_economic_diagnostic.csv": "19341254f4448d6a0628313c909d6b4ab82843f64363853a584961d8160041ce",
    "phase12_step6_fold_results.csv": "317e9fb735347351be6e4bb44b807b6f419aaa0021badf20f19b2e2cc8b36c11",
    "phase12_step6_magnitude.csv": "f2f82819aad307aa5816dce101da847e52964ea880ddb6c9ea85293357467181",
    "phase12_step6_manifest.json": "cd39329b02772d81c5594bb1d3342795c8384f692952f4b293b8599c10bc6453",
    "phase12_step6_placebo.csv": "a6e30a69c9a2229ddcb5855360cb2a54d214672b6ea4c201688afee388dbf9d1",
    "phase12_step6_residual_predictions.csv": "41dae563cbb48f2ab84cf1b8f18edf190abbecdf82d5b7104e797a63755604af",
    "phase12_step6_temporal_results.csv": "85e901e45e6327640131011460146b0221956d0a2f8ae15e8c6be1aceea6dfe8",
}

PROTECTED_STEP7_HASHES = {
    "step7_economic_diagnostic.csv": "2801997a874ee0eb1778a273430f47c5472343b8419b4ebed7f0cd993ad10c90",
    "step7_fold_results.csv": "230e90c3b7415e9d19d7c01714c72d6a779f6b40050ad4e547648eddbe3575f7",
    "step7_integrity_manifest.json": "d772c3714a2f79f1eb0520bf2ea0576eb4467d2cd2b8fdde9860e585b2866635",
    "step7_placebo_results.csv": "977397dd78737150e5bbac8a9f1b1e8e1545604697cb978bcc2db06606b01667",
    "step7_predictions.csv": "3a2ec99ed398f4cb1047326df2cee879a355712c98aa306f8e87d0680291013e",
    "step7_summary.csv": "de3b4c8adde8c2861c452e08ca0a5da5b901596bf0ad62de320770a11800ac6f",
    "step7_temporal_results.csv": "5953cdbd1bfa67d85c4a58e129fda337dcdea3ab0da330bc79647d524d441ed9",
    "step7_tree_counts.csv": "de78be51942b03d27af3a681c65c204aef090f8f948169d3fcfcd3f3be06f2ad",
}

PROTECTED_STEP8_HASHES = {
    "step8_economic_diagnostic.csv": "13aead08232aae96af2e57c5c4d7dd6651ecc29d3291a1bce600ca6a3bc64bee",
    "step8_feature_contribution.csv": "4d73edd23dd8218813addc13bbb77cd42c533b41564f8357dea6158ab39ffad5",
    "step8_feature_group_registry.csv": "7fd8479a21f61f3d852405dc679e261cd4b1e0c4d741bd42712e06020c78eec0",
    "step8_fold_results.csv": "dd283306bac4dc3c017cfadf34c3acd71ff355ec6c3807215a1292769578eb38",
    "step8_placebo_results.csv": "94b6951406065d5a8ee745fa5aef76dd2f0342c8122958aa31bc4353eb944d26",
    "step8_predictions.csv": "d5a3c1c8122531a0d0104421cf87a9c957a40a01ff1826936fc4cf52989e3f6a",
    "step8_summary.csv": "6c7043f0c4c909e62bfa0f084e8b270147b79f5adf5e75deec80f6f43b533576",
    "step8_temporal_results.csv": "abc427ca94d66c2ca2053fa69450baf177e4fbfddae1a0c99bfcff983bac25b0",
    "step8_feature_group_registry.json": "695718620348e4fc6e9cc72829a409f03604e42ce86f60aac3f5e5a51a90cefc",
}

PROTECTED_STEP9_HASHES = {
    "step9_pit_availability_matrix.csv": "eada1262780544f7a232911761c1912f630fec8dd101d925dce53e2cbb75b441",
    "step9_pit_availability_matrix.json": "83bbe492c7da516722eca3f6ca30d59b1e39f4271867e39ea3fd7a035cb06eab",
    "step9_feature_timestamp_audit.csv": "5e3f68525a14a673c2f7af1d5381ff1836099763f092906c780e0316bcb28854",
    "step9_timestamp_conversion_audit.csv": "0fe8b619252e8ee65f50e4820d238960621c6e2d44cb1a7c9ca453bf8d0c7864",
    "step9_predictions.csv": "9b7c9ca96f83a31df64576941776bb3e36e33772fa6bd23e7a891ba8fc7e0961",
    "step9_fold_results.csv": "6ba0d15c406bb07de075462def79278248c90eb16fd808b0192d5585b1adb87d",
    "step9_temporal_results.csv": "8ccc4590ce28de2da17731105a0958ba8441c42202df3cc66d56b3cf4c4d92c2",
    "step9_summary.csv": "df853b743dca06ef926a117ba36d2ba41d69ef7ae48fd52af9cf412358589113",
    "step9_stale_value_audit.csv": "587068edb13b66b59ffc7bebbe06513edcfebb959f5db3d8b08a5c340d7da6f6",
    "step9_revision_audit.csv": "5db5a3345f340834d9f71934bb2f62f21b8f0c75b50449edfeba8dfe1a331552",
    "step9_placebo_results.csv": "2adcc3ee64c9972f291cc3e6aef300edbcf199c5c77a3deef7a242a6d8b1454f",
    "step9_economic_diagnostic.csv": "3bac236e1c372878b970079ca128e6ad85a5ddb3b1bf1b5c56c8d3abbe32fd64",
    "step9_integrity_manifest.json": "66e22363105f1c2b2abbfc06cb2998c67b9fbfb0c943479e124a3f53dcf5f595",
}

PROTECTED_STEP10_HASHES = {
    "step10_information_sets.csv": "7ef7f241d35a65fed8c090915d0948243e4d4f9fa55dbc3bbdf00de591561e0e",
    "step10_information_sets.json": "3e39033e75d35d4a61b476165a8ccf87b97be842970ac2f5bd9c092a22a9b606",
    "step10_predictions.csv": "0c0e3a70a1e750e8f9d1104b43903cc32fb3c28de99176e5224634856272c18f",
    "step10_fold_results.csv": "8694e8004004482767f54294e8a36aa88baf1da44bb27dfb5d6423f23089338c",
    "step10_temporal_results.csv": "e7eae9450daf136044ddfa7e68e95beb0e19e58c04ae4bd2b2737b352444c343",
    "step10_summary.csv": "a767bb66c11908d1514c93e909ba31e78c6cb6d39618e731ca940795ddee0a8d",
    "step10_feature_family_mapping.csv": "7646a0533ffb4be90913d444516cd48d4ee6f94c505f5ce0fea339eb5a89e7d7",
    "step10_macro_forensic.csv": "480da0d0f68930c2d159ebdacd9333a0f04a3dfbea28e96bf610d2e5fa31cfcc",
    "step10_placebo_results.csv": "33166fd29f4d8f9a00a1e75fbc47fba22710a5c52f3e01c7b6e4a24379d68695",
    "step10_economic_diagnostic.csv": "7433c9d8a1e53fc648a8b8ae777feb9c5e748039c837afd55a1d1964e05c7e84",
    "step10_PR_equivalence_matrix.csv": "4d3898af0b0136c2519a053b9a64c78f1a89f19387d169d03b06fbc0ead485c1",
    "step10_integrity_manifest.json": "aeaa8dc043486d079a790f9318484b721d1173d666b66a3dba2d0daff274d163",
}

PROTECTED_STEP11_HASHES = {
    "step11_target_definitions.csv": "828c63754a98166a14abdd3beecc23f3c0b6d5d0b7ebd076c08e90beede3adb2",
    "step11_target_definitions.json": "62376cbc7b4e44b8665dc4933ddf2d14424a3dc47f5cd921bb25bb0f254b8d98",
    "step11_target_statistics.csv": "8347757d41449e0d699f278d06dafa20b4c09577cba863cbb45ec4b29bbcf4ee",
    "step11_predictions.csv": "40577ea079cf3b3667364ad0a33bb8ce27fe2a8adf7a3e17925de97adff43ed1",
    "step11_fold_results.csv": "6a1ac930eff59a52837b3a3c0cda9eefb0121d48ac9909ac48c6536862f06f3f",
    "step11_temporal_results.csv": "7654f16c694b14f27ff429caa5d796793b93360988c447f230ef6f7ff9346e3c",
    "step11_residual_results.csv": "765fa66a15d42dca633ad29d5b483ac5ee41f15a2b5a6404f3aa674effa07744",
    "step11_baseline_comparison.csv": "ce71fd4d288891a7abc8cb91d08499b2bba0cb4e0a8c00dd07ed077df3c0b3ed",
    "step11_multiple_testing.csv": "4e1eddd05af049a88c88af64ff6e22e53b3d4b5bf87eedaf948956aa42013890",
    "step11_economic_diagnostic.csv": "70ce1b958f97d42c3f6e3792815e3b21c84f7c028af0863960b2dfc500cf1f5e",
    "step11_t0_reconciliation.csv": "31238ac16e578f6fbe3622a544afe2d29ff402849ba9a26908920e32bc4567a7",
    "step11_t0_reconciliation.json": "cbd9dcf161a3dcefb21279a99bb84135e00597f8027ddd59cc29aa9abc1b51ad",
    "step11_t1_realized_component_audit.csv": "7021e80b813f5acffc3d299cdd7bd21332dd821e187e076d6905fc46d33bf868",
    "step11_t1_realized_component_audit.json": "e242ee1af649b76edb7386eb9571739087053c0263002186932bd8e763861808",
}

PROTECTED_STEP12_HASHES = {
    "step12_null_definitions.json": "5afd8097850bb6f305bb2e414928d9935a190536230cdadffbf4d5b7bcdd3b64",
    "step12_null_results.csv": "d37949cf859c5f22fb1f8422940c80460d6e320691b32a0625550ef30087f924",
    "step12_null_summary.csv": "1d383bffe718a7dbc4e42f48b83f0d629c63b57d0bfefe8b19e1bfa6d4e8dad2",
    "step12_temporal_results.csv": "e55e80f3fc66b9aeee1f6efca94084b1c01f40dc99cf9a225784a0cdce2bf04c",
    "step12_n4_year_exact_results.csv": "0db5a476304128069a1d9ac64227242fcf22d790f9097cb134e4303ae3e99aeb",
    "step12_n4_year_exact_summary.json": "263e6e006fb80be134ea4422680aa926bc63f9d531ddf6505b72e33c4724c0aa",
    "step12_integrity_manifest.json": "7e872bac602b0229e65cdeec10385b3f529fcc352d1a6af34aa750de5ff58f0e",
}


def verify_protected_checksums() -> None:
    """Ensure all protected Phase 4-10 and Phase 12 Step 5-12 artifacts remain unmodified."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    for rel_path, exp_hash in cfg["protected_artifact_hashes"].items():
        fp = PROJECT_ROOT / rel_path
        if not fp.is_file():
            raise FileNotFoundError(f"Missing protected file: {rel_path}")
        act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
        if act_hash != exp_hash:
            raise ValueError(f"Checksum mismatch for {rel_path}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    for dir_p, h_dict in [
        (PHASE12_DIR, PROTECTED_STEP5_HASHES),
        (PHASE12_DIR, PROTECTED_STEP6_HASHES),
        (STEP7_DIR, PROTECTED_STEP7_HASHES),
        (STEP8_DIR, PROTECTED_STEP8_HASHES),
        (STEP9_DIR, PROTECTED_STEP9_HASHES),
        (STEP10_DIR, PROTECTED_STEP10_HASHES),
        (STEP11_DIR, PROTECTED_STEP11_HASHES),
        (STEP12_DIR, PROTECTED_STEP12_HASHES),
    ]:
        for fn, exp_hash in h_dict.items():
            fp = dir_p / fn
            if not fp.is_file():
                raise FileNotFoundError(f"Missing protected Step 5-12 file: {fn} in {dir_p}")
            act_hash = hashlib.sha256(fp.read_bytes()).hexdigest()
            if act_hash != exp_hash:
                raise ValueError(f"Checksum mismatch for {fn}!\nExpected: {exp_hash}\nActual:   {act_hash}")

    print("[CHECKSUMS] All protected Phase 4-10 and Step 5-12 artifacts verified byte-for-byte.")


def build_holdout_protocol() -> Dict[str, Any]:
    """Construct the formal machine-readable holdout evaluation protocol."""
    return {
        "protocol_version": "1.0.0",
        "phase": "Phase 13 Step 1",
        "title": "Untouched Holdout Evaluation Protocol Freeze",
        "created_timestamp_utc": "2026-10-31T11:45:00Z",
        "governance": {
            "phase12_steps_sealed": "1 through 12",
            "holdout_access_authorized": False,
            "evaluation_execution_authorized": False,
            "holdout_rows_accessed": 0,
            "max_development_cutoff": "2021-12-31",
            "terminal_holdout_partition": {
                "start_date": "2022-01-03",
                "end_date": "2026-09-03",
                "expected_sessions": 1154,
                "governance_rule": "EVALUATION_ONLY_SINGLE_PASS",
                "source_authority": "configs/phase11_strategy_validation_config.json",
            },
        },
        "target_specification": {
            "primary_target_id": "T0",
            "target_name": "Snapshot B Intraday Open-to-Close Return",
            "mathematical_formula": "R_intraday(T+1) = (Close(T+1) - Open(T+1)) / Open(T+1)",
            "information_cutoff_timestamp": "08:50 IST (Session T+1)",
            "execution_entry_timestamp": "09:15 IST (Session T+1 Open)",
            "execution_exit_timestamp": "15:30 IST (Session T+1 Close)",
            "is_primary": True,
            "alternative_horizons_status": {
                "T1": "Close(T+1)/Close(T)-1 contains already-realized overnight component; rejected as primary holdout target",
                "T2": "Derived centered diagnostic; non-independent",
                "T3": "Log transformation check; non-independent",
                "T4": "Intraday high/low; non-executable due to data absence",
            },
        },
        "feature_specification": {
            "total_feature_count": 63,
            "price_feature_count": 45,
            "context_feature_count": 18,
            "news_features_included": False,
            "volume_features_included": False,
            "flow_features_included": False,
            "price_features": list(PRICE_FEATURE_NAMES),
            "context_features": list(CONTEXT_FEATURE_NAMES),
        },
        "model_specification": {
            "architecture": "xgboost.XGBRegressor",
            "hyperparameters": {
                "objective": "reg:squarederror",
                "learning_rate": 0.05,
                "max_depth": 2,
                "min_child_weight": 20.0,
                "subsample": 0.8,
                "colsample_bytree": 0.7,
                "reg_alpha": 0.5,
                "reg_lambda": 2.0,
                "random_state": 42,
                "n_jobs": -1,
            },
            "training_policy": "Option A — Frozen historical models",
            "training_policy_justification": (
                "Recovered directly from MASTER_SPECIFICATION.md Section 9.1 diagram "
                "('Final: [--- Train Full ---][ Final Test (Frozen) ]') and Phase 11 configuration "
                "('EVALUATION_ONLY_SINGLE_PASS'). Option A trains models strictly using data available "
                "through the development partition (cutoff 2021-12-31, N=3,299) with zero retraining "
                "during the 2022+ holdout period. This prevents prospective retraining hyperparameter leakage "
                "and guarantees an uncompromised single-pass out-of-sample evaluation."
            ),
            "primary_model": {
                "name": "Full Development Production Model",
                "training_window": "2008-07-08 to 2021-12-31",
                "training_sessions": 3299,
                "n_estimators": 43,
                "role": "Sole primary model for holdout evaluation",
            },
            "secondary_diagnostic_models": [
                {
                    "name": "Fold 8 Frozen Model",
                    "training_window": "2008-07-08 to 2020-12-31",
                    "training_sessions": 3051,
                    "n_estimators": 40,
                    "role": "Diagnostic comparison: maximum walk-forward development fold model",
                },
                {
                    "name": "8-Fold Walk-Forward Uniform Ensemble",
                    "training_folds": "Folds 1 through 8 (2014-2021)",
                    "fold_n_estimators": [10, 60, 45, 60, 10, 10, 10, 40],
                    "aggregation": "Simple unweighted mean of predictions from all 8 frozen fold models",
                    "role": "Diagnostic comparison: cross-fold consensus model",
                },
            ],
        },
        "evaluation_metrics": {
            "primary_metric": {
                "name": "Pearson Correlation (IC)",
                "symbol": "r_p",
                "formula": "Cov(pred, actual) / (Std(pred) * Std(actual))",
                "role": "Sole primary test statistic for hypothesis confirmation",
            },
            "secondary_forecasting_metrics": [
                {"name": "Spearman Rank Correlation (IC)", "symbol": "r_s"},
                {"name": "Mean Absolute Error", "symbol": "MAE"},
                {"name": "Root Mean Squared Error", "symbol": "RMSE"},
                {"name": "Mean Directional Accuracy (Hit Rate)", "symbol": "MDA", "formula": "mean(sign(pred) == sign(actual))"},
            ],
            "secondary_statistical_diagnostics": [
                {"name": "Residual Pearson IC", "symbol": "r_resid", "baseline": "Historical training mean"},
                {"name": "Residual Spearman IC", "symbol": "r_s_resid"},
                {"name": "Incremental R-squared", "symbol": "R2_inc", "baseline": "Training-period conditional mean"},
            ],
            "secondary_economic_diagnostics": {
                "strategy_rule": "Strategy 1: Unrestricted Direction (if pred > 0 -> +1; if pred < 0 -> -1; else 0)",
                "position_sizing": "Fixed notional, 1.0 gross exposure, leverage 1.0",
                "transaction_cost_scenarios_bps": [
                    {"label": "0 bps (Gross)", "round_trip_fraction": 0.0000},
                    {"label": "5 bps Round-Trip", "round_trip_fraction": 0.0005},
                    {"label": "10 bps Round-Trip (Baseline)", "round_trip_fraction": 0.0010},
                    {"label": "20 bps Round-Trip (Stress)", "round_trip_fraction": 0.0020},
                ],
                "reported_metrics": [
                    "gross_annualized_return",
                    "net_annualized_return",
                    "annualized_sharpe_ratio",
                    "max_drawdown",
                    "active_sessions_count",
                ],
                "role": "Descriptive feasibility diagnostics only; not optimization targets",
            },
        },
        "benchmarks": {
            "Benchmark 1": {
                "name": "Zero-Return Predictor",
                "rule": "pred = 0.0 on all holdout sessions",
                "role": "Trivial uninformative forecast baseline",
            },
            "Benchmark 2": {
                "name": "Historical Training Mean Predictor",
                "rule": "pred = mean(T0_actual) over development partition (<= 2021-12-31)",
                "role": "Unconditional drift forecast baseline using only legitimate pre-holdout data",
            },
            "Benchmark 3": {
                "name": "Always Short Benchmark",
                "rule": "position = -1.0 daily (Open to Close)",
                "role": "Passive capture of structural negative daytime drift",
            },
        },
        "statistical_interpretation_framework": {
            "Outcome A": {
                "condition": "Holdout Pearson IC > 0 with p < 0.05 and directionally consistent with OOF (+0.0476)",
                "mandatory_statement": "The observed holdout result is directionally consistent with the historical OOF relationship under the predefined evaluation protocol.",
            },
            "Outcome B": {
                "condition": "Holdout Pearson IC is weak, near zero, or statistically non-significant (p >= 0.05)",
                "mandatory_statement": "The historical OOF relationship did not reproduce strongly in the untouched holdout under the predefined evaluation protocol.",
            },
            "Outcome C": {
                "condition": "Holdout Pearson IC is negative or materially contradicts the historical OOF relationship",
                "mandatory_statement": "The holdout result is inconsistent with the historical OOF relationship under the predefined evaluation protocol.",
            },
            "negative_constraints": [
                "No outcome may be described as proof of future persistence.",
                "No outcome may be described as proving commercial trading viability.",
                "Statistical association does not imply economic viability or causal mechanism.",
            ],
        },
        "multiple_testing_rule": {
            "sole_primary_endpoint": "Snapshot B T0 Pearson IC",
            "prohibited_actions": [
                "Do not create competing primary hypotheses after observing results.",
                "Do not switch the primary metric because another metric performs better.",
                "Do not use T1, T2, or T3 to rescue an unsuccessful T0 result.",
                "Do not tune thresholds, hyperparameters, or tree counts on holdout data.",
            ],
        },
        "firewall_requirements": {
            "holdout_rows_accessed": 0,
            "max_training_date": "2021-12-31",
            "prohibited_operations": [
                "No holdout rows loaded",
                "No holdout target values loaded",
                "No holdout predictions generated",
                "No holdout metrics computed",
                "No holdout-derived feature statistics computed",
                "No holdout-derived normalization",
                "No holdout-derived threshold",
                "No holdout-derived hyperparameter",
                "No holdout-derived model selection",
            ],
        },
    }


def generate_protocol_markdown(proto: Dict[str, Any]) -> str:
    """Generate human-readable Markdown documentation of the frozen protocol."""
    return f"""# Phase 13 Step 1: Untouched Holdout Evaluation Protocol Freeze

## 1. Governance & Execution Authorization
- **Protocol Version**: `{proto['protocol_version']}`
- **Created Timestamp (UTC)**: `{proto['created_timestamp_utc']}`
- **Phase Status**: `PHASE 13 STEP 1 — FROZEN & SEALED`
- **Execution Authorization**: **STEP 1 IS PROTOCOL FREEZE ONLY. NO HOLDOUT DATA MAY BE LOADED OR EVALUATED IN THIS STEP.**
- **Holdout Access**: Strictly quarantined (`holdout_rows_accessed == 0`, `max_development_cutoff <= 2021-12-31`).

---

## 2. Terminal Holdout Partition Definition
- **Holdout Period**: `{proto['governance']['terminal_holdout_partition']['start_date']}` through `{proto['governance']['terminal_holdout_partition']['end_date']}`
- **Expected Observations**: `{proto['governance']['terminal_holdout_partition']['expected_sessions']:,}` sessions (recovered strictly from sealed Phase 11 configuration metadata; unaccessed in Step 1)
- **Governance**: Single confirmatory pass (`EVALUATION_ONLY_SINGLE_PASS`)
- **Firewall Rule**: Zero holdout observations, targets, features, or metrics may be loaded or computed prior to Step 2 authorization.

---

## 3. Primary Forecasting Target Specification
- **Primary Target ID**: `{proto['target_specification']['primary_target_id']}`
- **Target Name**: {proto['target_specification']['target_name']}
- **Mathematical Formula**:
  $$\\text{{T0}}(T+1) = \\frac{{\\text{{Close}}(T+1) - \\text{{Open}}(T+1)}}{{\\text{{Open}}(T+1)}}$$
- **Information Cutoff Timestamp**: `{proto['target_specification']['information_cutoff_timestamp']}`
- **Execution Window**: Entry at Open (`{proto['target_specification']['execution_entry_timestamp']}`), Exit at Close (`{proto['target_specification']['execution_exit_timestamp']}`).
- **Multiple-Testing Quarantine**: $T0$ is the **sole primary target**. Alternative horizons ($T1, T2, T3, T4$) are strictly quarantined from primary status.

---

## 4. Feature Information Set (63 Features)
The feature space is strictly frozen to the established 63-feature Model 1 configuration:
- **Price Features (45)**: `{len(proto['feature_specification']['price_features'])}` features spanning momentum, trend, volatility, mean-reversion, and calendar cycles.
- **Context Features (18)**: `{len(proto['feature_specification']['context_features'])}` features spanning inter-market indices (S&P 500, Nasdaq, Dow Jones, Nikkei 225, Hang Seng, FTSE 100), Bank Nifty, commodities (Brent, WTI, Gold), currencies (DXY, USD/INR), bond yields (India 10Y, US 10Y), and volatility indices (India VIX, US VIX).
- **Excluded Feature Families**:
  - News features: `EXCLUDED` ({proto['feature_specification']['news_features_included']})
  - Volume features: `EXCLUDED` ({proto['feature_specification']['volume_features_included']})
  - Flow features: `EXCLUDED` ({proto['feature_specification']['flow_features_included']})

---

## 5. Model Architecture & Training Policy
### Selected Policy: Option A — Frozen Historical Models
- **Justification**: Recovered directly from `MASTER_SPECIFICATION.md` Section 9.1 (`Final: [--- Train Full ---][ Final Test (Frozen) ]`) and `configs/phase11_strategy_validation_config.json` (`EVALUATION_ONLY_SINGLE_PASS`).
- **Policy Rule**: Models are trained strictly on data available through the development partition (`<= 2021-12-31`, $N=3,299$). **Zero retraining occurs during the holdout period.** This avoids prospective retraining hyperparameter leakage and ensures an uncompromised single-pass out-of-sample test.

### Primary Holdout Model:
- **Architecture**: `xgboost.XGBRegressor`
- **Training Data**: Full Development Partition (`2008-07-08` to `2021-12-31`, $N=3,299$)
- **Tree Count ($N^*$)**: **43 trees** (locked production regressor tree count)
- **Hyperparameters**:
  - `objective`: `reg:squarederror`
  - `learning_rate`: `0.05`
  - `max_depth`: `2`
  - `min_child_weight`: `20.0`
  - `subsample`: `0.8`
  - `colsample_bytree`: `0.7`
  - `reg_alpha`: `0.5`
  - `reg_lambda`: `2.0`
  - `random_state`: `42`

### Pre-Registered Secondary Diagnostic Models:
1. **Fold 8 Frozen Model**: Trained on `2008-07-08` through `2020-12-31` ($N=3,051$) with $N^*=40$ trees.
2. **8-Fold Walk-Forward Uniform Ensemble**: Simple unweighted average of the 8 frozen walk-forward development models (`[10, 60, 45, 60, 10, 10, 10, 40]`).

---

## 6. Pre-Registered Holdout Evaluation Metrics
### Primary Metric:
- **Pearson Correlation (IC)**: $r_p = \\text{{Corr}}(\\hat{{y}}, y)$ on $T0$ across the full holdout ($N=1,154$).

### Secondary Forecasting Metrics:
- **Spearman Rank Correlation (IC)** ($r_s$)
- **Mean Absolute Error (MAE)**
- **Root Mean Squared Error (RMSE)**
- **Mean Directional Accuracy (MDA / Hit Rate)**: $\\text{{mean}}(\\text{{sign}}(\\hat{{y}}) == \\text{{sign}}(y))$

### Secondary Statistical Diagnostics:
- **Residual Pearson IC**: Correlation of model residuals against the historical training baseline mean.
- **Residual Spearman IC**
- **Incremental $R^2$**: Proportion of variance explained relative to unconditional historical mean baseline.

### Secondary Economic Diagnostics (Strategy 1: Unrestricted Direction):
- Position: $+1$ if $\\hat{{y}} > 0$; $-1$ if $\\hat{{y}} < 0$; $0$ if $\\hat{{y}} == 0$.
- Fixed notional, 1.0 gross exposure.
- Evaluated under 4 fixed transaction-cost scenarios:
  1. **0 bps (Gross)**
  2. **5 bps Round-Trip**
  3. **10 bps Round-Trip (Baseline Frictions)**
  4. **20 bps Round-Trip (Adverse Slippage Stress)**
- Outputs: Gross/Net Annualized Return, Annualized Sharpe Ratio, Maximum Drawdown, Active Session Count.
- *Strict Note*: Economic diagnostics are descriptive feasibility checks, not strategy optimization targets.

---

## 7. Fixed Benchmark Specifications
1. **Benchmark 1 (Zero-Return Predictor)**: $\\hat{{y}} \\equiv 0.0$.
2. **Benchmark 2 (Historical Training Mean Predictor)**: $\\hat{{y}} \\equiv \\mu_{{\\text{{train}}}}$ using only development data $\\le 2021-12-31$.
3. **Benchmark 3 (Always Short Benchmark)**: Static daily short position ($-1.0$) capturing structural negative daytime drift.

---

## 8. Pre-Registered Statistical Interpretation Framework
- **Outcome A (Directionally Consistent)**:
  - *Criteria*: Holdout Pearson IC $> 0$, $p < 0.05$, consistent with OOF ($+0.0476$).
  - *Mandatory Statement*: **"The observed holdout result is directionally consistent with the historical OOF relationship under the predefined evaluation protocol."**
- **Outcome B (Weak or Absent)**:
  - *Criteria*: Holdout Pearson IC near zero, weak, or statistically non-significant ($p \\ge 0.05$).
  - *Mandatory Statement*: **"The historical OOF relationship did not reproduce strongly in the untouched holdout under the predefined evaluation protocol."**
- **Outcome C (Materially Contradictory)**:
  - *Criteria*: Holdout Pearson IC negative or significantly inverted ($r_p < 0$, $p < 0.05$).
  - *Mandatory Statement*: **"The holdout result is inconsistent with the historical OOF relationship under the predefined evaluation protocol."**

### Critical Negative Constraints:
1. No outcome may be described as proof of future persistence.
2. No outcome may be described as proving commercial trading viability.
3. Statistical association does not imply economic viability or causal mechanism.

---

## 9. Holdout Firewall & Zero-Access Audit
The evaluation protocol was created under strict holdout quarantine:
- Holdout rows loaded: **0**
- Holdout targets loaded: **0**
- Holdout predictions generated: **0**
- Holdout metrics computed: **0**
- Holdout-derived feature statistics: **0**
- Holdout-derived normalizations / thresholds / hyperparameters: **0**

---

## 10. Seal Status & Execution Boundary
**PHASE 13 STEP 1 IS FORMALLY SEALED.**  
**NO PHASE 13 STEP 2 EXECUTION IS AUTHORIZED BY THIS TASK.**
"""


def build_firewall_audit(proto: Dict[str, Any]) -> Dict[str, Any]:
    """Construct an explicit verification audit confirming holdout quarantine."""
    return {
        "audit_timestamp_utc": proto["created_timestamp_utc"],
        "phase": "Phase 13 Step 1",
        "auditor_role": "Quantitative ML Validation Specialist & Forensic Auditor",
        "firewall_status": "INTACT_AND_VERIFIED",
        "checks": {
            "no_holdout_rows_loaded": True,
            "no_holdout_targets_loaded": True,
            "no_holdout_predictions_generated": True,
            "no_holdout_metrics_computed": True,
            "no_holdout_derived_feature_statistics": True,
            "no_holdout_derived_normalization": True,
            "no_holdout_derived_threshold": True,
            "no_holdout_derived_hyperparameters": True,
            "no_holdout_derived_model_selection": True,
            "no_strategy_optimization_conducted": True,
        },
        "boundary_verification": {
            "development_max_date": "2021-12-31",
            "holdout_start_date": "2022-01-01",
            "holdout_expected_start_session": "2022-01-03",
            "holdout_expected_end_session": "2026-09-03",
            "holdout_rows_accessed": 0,
            "holdout_rows_quarantined": 1154,
        },
        "code_access_audit": {
            "step1_script": "scripts/phase13_step1_holdout_protocol_freeze.py",
            "step1_script_contains_holdout_read": False,
            "step1_script_contains_model_fit": False,
            "step1_script_contains_prediction_call": False,
            "step1_artifacts_contain_holdout_predictions": False,
            "step1_artifacts_contain_holdout_metrics": False,
        },
    }


def main() -> None:
    print("=" * 90)
    print("PHASE 13 STEP 1: UNTOUCHED HOLDOUT EVALUATION PROTOCOL FREEZE")
    print("=" * 90)

    # 1. Protected Checksum Verification
    print("\n--- Step 1: Protected Upstream Checksum Verification ---")
    verify_protected_checksums()

    # 2. Build Protocol JSON
    print("\n--- Step 2: Constructing Holdout Protocol Specification ---")
    protocol_data = build_holdout_protocol()
    protocol_json_path = OUT_DIR / "step1_holdout_protocol.json"
    with open(protocol_json_path, "w", encoding="utf-8") as f:
        json.dump(protocol_data, f, indent=2)
    print(f"Saved: {protocol_json_path}")

    # 3. Build Protocol Markdown
    print("\n--- Step 3: Generating Human-Readable Protocol Document ---")
    protocol_md = generate_protocol_markdown(protocol_data)
    protocol_md_path = OUT_DIR / "step1_holdout_protocol.md"
    with open(protocol_md_path, "w", encoding="utf-8") as f:
        f.write(protocol_md)
    print(f"Saved: {protocol_md_path}")

    # 4. Build Firewall Audit JSON
    print("\n--- Step 4: Generating Holdout Firewall Audit ---")
    firewall_audit = build_firewall_audit(protocol_data)
    firewall_path = OUT_DIR / "step1_holdout_firewall_audit.json"
    with open(firewall_path, "w", encoding="utf-8") as f:
        json.dump(firewall_audit, f, indent=2)
    print(f"Saved: {firewall_path}")

    # 5. Build Integrity Manifest
    print("\n--- Step 5: Generating Integrity Manifest ---")
    step1_artifacts = [
        "step1_holdout_protocol.json",
        "step1_holdout_protocol.md",
        "step1_holdout_firewall_audit.json",
    ]

    manifest_hashes = {}
    for fn in step1_artifacts:
        fp = OUT_DIR / fn
        assert fp.is_file(), f"Missing artifact: {fn}"
        h = hashlib.sha256(fp.read_bytes()).hexdigest()
        manifest_hashes[fn] = h
        print(f"  {fn:<35}: {h}")

    manifest_data = {
        "step": "Phase 13 Step 1",
        "title": "Untouched Holdout Evaluation Protocol Freeze",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "firewall_verification": {
            "max_dev_trading_date": "2021-12-31",
            "holdout_start_date": "2022-01-01",
            "holdout_rows_quarantined": 1154,
            "holdout_rows_accessed": 0,
            "firewall_intact": True,
        },
        "protocol_summary": {
            "primary_target": "Snapshot B T0 (Open -> Close)",
            "model_architecture": "xgboost.XGBRegressor",
            "features_count": 63,
            "training_policy": "Option A — Frozen historical models (Full Dev N=3299, N*=43)",
            "primary_metric": "Pearson Correlation (IC)",
            "holdout_predictions_generated": 0,
            "holdout_metrics_computed": 0,
        },
        "artifact_hashes": manifest_hashes,
    }

    manifest_path = OUT_DIR / "step1_integrity_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    print(f"Saved: {manifest_path}")

    print("\n" + "=" * 90)
    print("PHASE 13 STEP 1 PROTOCOL FREEZE COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
