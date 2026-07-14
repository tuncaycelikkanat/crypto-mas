"""
engine/utils.py — Shared utility helpers for the engine layer.

Extracted from ScoringEngine, RegimeEngine and TrendSignalEngine to
eliminate the DRY violation where each class had its own identical
_get_float() implementation.
"""
from typing import Any


def get_float(features: dict[str, Any], key: str) -> float | None:
    """Safely extract and cast a feature value to float.

    Returns None if the key is missing, the value is None, or it cannot
    be cast to a finite float.
    """
    value = features.get(key)

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
