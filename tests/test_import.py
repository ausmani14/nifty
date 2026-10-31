"""Sanity tests for NIFTY AI project foundation."""

import importlib
from pathlib import Path
import nifty_ai
from nifty_ai.config import (
    DEFAULT_TIMEZONE,
    PROJECT_ROOT,
    SNAPSHOT_POST_CLOSE,
    SNAPSHOT_PRE_OPEN,
)


def test_package_import():
    """Verify that nifty_ai package can be imported and has version metadata."""
    assert hasattr(nifty_ai, "__version__")
    assert isinstance(nifty_ai.__version__, str)
    assert len(nifty_ai.__version__) > 0


def test_subpackages_import():
    """Verify that all core modular subpackages are importable."""
    subpackages = [
        "nifty_ai.config",
        "nifty_ai.data",
        "nifty_ai.features",
        "nifty_ai.targets",
        "nifty_ai.models",
        "nifty_ai.evaluation",
        "nifty_ai.backtesting",
        "nifty_ai.trading",
        "nifty_ai.explainability",
        "nifty_ai.news",
        "nifty_ai.utils",
    ]
    for subpkg in subpackages:
        module = importlib.import_module(subpkg)
        assert module is not None


def test_config_constants():
    """Verify base snapshot schedule and market timezone defaults."""
    assert DEFAULT_TIMEZONE == "Asia/Kolkata"
    assert SNAPSHOT_POST_CLOSE == "15:40:00"
    assert SNAPSHOT_PRE_OPEN == "08:50:00"


def test_env_example_safety():
    """Ensure .env.example exists and contains no hard-coded secrets or live tokens."""
    env_example = PROJECT_ROOT / ".env.example"
    assert env_example.is_file(), f"Missing .env.example at {env_example}"

    content = env_example.read_text(encoding="utf-8")
    lines = content.splitlines()

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, val = stripped.partition("=")
            val = val.strip()
            # If key implies a credential/secret, ensure value is empty
            if any(secret_term in key.upper() for secret_term in ["KEY", "SECRET", "PASSWORD", "TOKEN"]):
                assert val == "", f"Potential secret found in .env.example for {key}: {val}"
