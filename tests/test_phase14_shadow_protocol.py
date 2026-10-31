"""Tests for Phase 14 Step 1: Prospective Research Protocol Freeze."""

import json
from pathlib import Path
import pytest
import yaml

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.shadow.contracts import (
    CANONICAL_FEATURES_63,
    CANONICAL_MODEL_SHA256,
    CANONICAL_META_SHA256,
)

CONFIG_PATH = PROJECT_ROOT / "configs" / "phase14_shadow_validation.yaml"
PROTOCOL_DOC = PROJECT_ROOT / "docs" / "PHASE_14_STEP1_PROSPECTIVE_PROTOCOL.md"
MANIFEST_PATH = PROJECT_ROOT / "data" / "interim" / "phase14_shadow" / "phase14_protocol_manifest.json"


def test_protocol_artifacts_exist():
    assert CONFIG_PATH.exists(), "Configuration file missing"
    assert PROTOCOL_DOC.exists(), "Protocol document missing"
    assert MANIFEST_PATH.exists(), "Protocol manifest missing"


def test_yaml_configuration_invariants():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    # Governance invariants
    assert cfg["system"]["phase"] == "Phase 14"
    assert cfg["system"]["research_status"] == "RESEARCH_BASELINE_ONLY"
    assert cfg["system"]["trading_authorized"] is False
    assert cfg["system"]["timezone"] == "Asia/Kolkata"

    # Frozen model invariants
    assert cfg["frozen_model"]["model_sha256"] == CANONICAL_MODEL_SHA256
    assert cfg["frozen_model"]["n_estimators"] == 43
    assert cfg["frozen_model"]["feature_count"] == 63

    # Information cutoff invariants
    assert cfg["information_contract"]["cutoff_time_ist"] == "08:50:00"
    assert cfg["information_contract"]["total_features"] == 63
    assert cfg["information_contract"]["price_features_count"] == 45
    assert cfg["information_contract"]["context_features_count"] == 18
    assert cfg["information_contract"]["forbidden_features"]["news_count"] == 0
    assert cfg["information_contract"]["forbidden_features"]["volume_count"] == 0
    assert cfg["information_contract"]["forbidden_features"]["flow_count"] == 0


def test_protocol_manifest_and_upstream_hashes():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["phase"] == "Phase 14 Step 1"
    assert manifest["frozen_model_sha256"] == CANONICAL_MODEL_SHA256
    assert manifest["frozen_meta_sha256"] == CANONICAL_META_SHA256
    assert manifest["feature_count"] == 63

    # Check upstream manifests exist
    assert (PROJECT_ROOT / "data" / "interim" / "phase13_step1" / "step1_integrity_manifest.json").exists()
    assert (PROJECT_ROOT / "data" / "interim" / "phase13_steps2_4" / "phase13_steps2_4_manifest.json").exists()
    assert (PROJECT_ROOT / "data" / "interim" / "phase13_step5" / "phase13_step5_integrity_manifest.json").exists()


def test_protocol_document_disclosures():
    text = PROTOCOL_DOC.read_text(encoding="utf-8")
    assert "RESEARCH_BASELINE_ONLY" in text
    assert "Zero Live Trading Authorization" in text
    assert "08:50:00 Asia/Kolkata" in text
    assert "T0" in text
    assert "xgboost.XGBRegressor" in text
