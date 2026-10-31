"""Configuration management module for NIFTY AI.

Handles environment variable loading, snapshot schedules, and system settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import yaml

# Automatically load .env if present
load_dotenv()

# Base project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "configs"

# Default snapshot and timezone settings
DEFAULT_TIMEZONE = "Asia/Kolkata"
SNAPSHOT_POST_CLOSE = "15:40:00"
SNAPSHOT_PRE_OPEN = "08:50:00"
CUTOFF_POST_CLOSE = "15:30:00"
CUTOFF_PRE_OPEN = "08:50:00"


def get_env_variable(var_name: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieve an environment variable safely without leaking credentials."""
    return os.getenv(var_name, default)


def load_yaml_config(file_path: Path) -> Dict[str, Any]:
    """Safely load and parse a YAML configuration file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config or {}


def get_providers_config() -> Dict[str, Any]:
    """Load provider registry configuration from configs/providers.yaml."""
    providers_path = CONFIG_DIR / "providers.yaml"
    if providers_path.is_file():
        return load_yaml_config(providers_path)
    return {}


__all__ = [
    "PROJECT_ROOT",
    "CONFIG_DIR",
    "DEFAULT_TIMEZONE",
    "SNAPSHOT_POST_CLOSE",
    "SNAPSHOT_PRE_OPEN",
    "CUTOFF_POST_CLOSE",
    "CUTOFF_PRE_OPEN",
    "get_env_variable",
    "load_yaml_config",
    "get_providers_config",
]
