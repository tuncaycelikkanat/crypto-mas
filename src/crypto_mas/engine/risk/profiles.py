"""
Risk profiles for different trading modes.

Each mode has its own RiskLimits tuned for the trading frequency
and expected position size of that mode.
"""
from crypto_mas.engine.risk import RiskLimits

RISK_PROFILES: dict[str, RiskLimits] = {
    "scalping": RiskLimits(
        max_positions=5,
        max_gross_exposure=0.60,
        max_position_weight=0.15,
        min_cash_weight=0.40,
    ),
    "swing": RiskLimits(
        max_positions=10,
        max_gross_exposure=0.85,
        max_position_weight=0.12,
        min_cash_weight=0.15,
    ),
    "hodl": RiskLimits(
        max_positions=3,
        max_gross_exposure=0.95,
        max_position_weight=0.40,
        min_cash_weight=0.05,
    ),
}

DEFAULT_PROFILE = RISK_PROFILES["swing"]


def get_risk_profile(mode: str) -> RiskLimits:
    """Return the RiskLimits for the given strategy mode.

    Falls back to 'swing' profile for unknown modes.
    """
    return RISK_PROFILES.get(mode.lower(), DEFAULT_PROFILE)
