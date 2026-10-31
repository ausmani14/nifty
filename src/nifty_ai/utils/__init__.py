"""Utility functions and logging helpers for NIFTY AI.

Includes timezone handlers, path helpers, and structured logging.
"""

import logging
import sys


def setup_logger(name: str = "nifty_ai", level: int = logging.INFO) -> logging.Logger:
    """Configure and return a standard formatted logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


__all__ = ["setup_logger"]
