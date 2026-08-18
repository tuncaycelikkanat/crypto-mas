import math
from dataclasses import dataclass
from datetime import UTC, datetime

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime import MarketRegime
from crypto_mas.engine.utils import get_float


@dataclass(frozen=True)
class ProbabilisticRegimeState:
    """
    Continuous probability distribution across all market regimes,
    along with transition entropy and primary detected state.
    """
    probabilities: dict[MarketRegime, float]
    primary_regime: MarketRegime
    regime_confidence: float
    entropy: float  # Shannon entropy (0 = certain, high = uncertain transition)
    is_transition_state: bool
    timestamp: datetime


class MarkovRegimeEngine:
    """
    Probabilistic regime detector that calculates continuous state transition
    probabilities and regime uncertainty entropy instead of hard discrete rules.
    """

    # Baseline empirical prior transition matrix P(next | current)
    DEFAULT_TRANSITION_PRIORS = {
        MarketRegime.BULL_TREND: {
            MarketRegime.BULL_TREND: 0.85,
            MarketRegime.SIDEWAYS: 0.10,
            MarketRegime.HIGH_VOLATILITY: 0.04,
            MarketRegime.BEAR_TREND: 0.01,
        },
        MarketRegime.BEAR_TREND: {
            MarketRegime.BEAR_TREND: 0.80,
            MarketRegime.SIDEWAYS: 0.12,
            MarketRegime.HIGH_VOLATILITY: 0.06,
            MarketRegime.BULL_TREND: 0.02,
        },
        MarketRegime.SIDEWAYS: {
            MarketRegime.SIDEWAYS: 0.75,
            MarketRegime.BULL_TREND: 0.12,
            MarketRegime.BEAR_TREND: 0.08,
            MarketRegime.HIGH_VOLATILITY: 0.05,
        },
        MarketRegime.HIGH_VOLATILITY: {
            MarketRegime.HIGH_VOLATILITY: 0.60,
            MarketRegime.SIDEWAYS: 0.20,
            MarketRegime.BEAR_TREND: 0.12,
            MarketRegime.BULL_TREND: 0.08,
        },
    }

    def __init__(self, entropy_threshold: float = 1.15):
        self.entropy_threshold = entropy_threshold

    def evaluate_probabilities(
        self,
        snapshots: list[FeatureSnapshot],
        previous_regime: MarketRegime = MarketRegime.SIDEWAYS,
    ) -> ProbabilisticRegimeState:
        if not snapshots:
            now = datetime.now(UTC)
            return ProbabilisticRegimeState(
                probabilities={r: 0.25 for r in [MarketRegime.BULL_TREND, MarketRegime.BEAR_TREND, MarketRegime.SIDEWAYS, MarketRegime.HIGH_VOLATILITY]},
                primary_regime=MarketRegime.UNKNOWN,
                regime_confidence=0.0,
                entropy=1.386,
                is_transition_state=True,
                timestamp=now,
            )

        features = snapshots[-1].features_json
        close = get_float(features, "close") or 1.0
        ema_20 = get_float(features, "ema_20") or close
        ema_50 = get_float(features, "ema_50") or close
        atr_14 = get_float(features, "atr_14") or 0.0
        bb_upper = get_float(features, "bb_upper") or close * 1.05
        bb_middle = get_float(features, "bb_middle") or close
        bb_lower = get_float(features, "bb_lower") or close * 0.95
        adx_14 = get_float(features, "adx_14") or 15.0

        # Likelihood Evidence Signals
        volatility_ratio = atr_14 / close if close > 0 else 0.0
        bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0.0

        # Evidence weights
        p_high_vol = min(1.0, max(0.0, (volatility_ratio - 0.03) / 0.05 * 0.5 + (bb_width - 0.10) / 0.15 * 0.5))
        
        # Bullish / Bearish momentum evidence
        ema_spread = (ema_20 - ema_50) / close
        trend_strength = min(1.0, adx_14 / 40.0)

        if ema_spread > 0:
            p_bull = max(0.05, min(0.90, (ema_spread * 20.0) * trend_strength))
            p_bear = max(0.02, 0.20 - p_bull * 0.5)
        else:
            p_bear = max(0.05, min(0.90, (-ema_spread * 20.0) * trend_strength))
            p_bull = max(0.02, 0.20 - p_bear * 0.5)

        # Sideways is strong when ADX is low and Bollinger Bands are narrow (suppressed during high volatility)
        p_sideways = max(0.02, min(0.85, (1.0 - trend_strength) * 0.6 + max(0.0, 0.15 - bb_width) * 2.0))
        if p_high_vol > 0.4:
            p_sideways *= max(0.05, 1.0 - p_high_vol)

        # Combine with Markov Prior Transition matrix (Bayesian Posterior Update)
        priors = self.DEFAULT_TRANSITION_PRIORS.get(
            previous_regime,
            self.DEFAULT_TRANSITION_PRIORS[MarketRegime.SIDEWAYS]
        )

        unnormalized = {
            MarketRegime.BULL_TREND: p_bull * priors.get(MarketRegime.BULL_TREND, 0.25),
            MarketRegime.BEAR_TREND: p_bear * priors.get(MarketRegime.BEAR_TREND, 0.25),
            MarketRegime.SIDEWAYS: p_sideways * priors.get(MarketRegime.SIDEWAYS, 0.25),
            MarketRegime.HIGH_VOLATILITY: p_high_vol * (priors.get(MarketRegime.HIGH_VOLATILITY, 0.25) + 0.5 * p_high_vol),
        }

        total_p = sum(unnormalized.values())
        if total_p <= 0:
            total_p = 1.0

        normalized = {r: round(val / total_p, 4) for r, val in unnormalized.items()}

        # Calculate Shannon Entropy: H = -sum(p * log(p))
        entropy = 0.0
        for p in normalized.values():
            if p > 1e-6:
                entropy -= p * math.log(p)

        primary_regime = max(normalized, key=normalized.get)  # type: ignore
        primary_confidence = normalized[primary_regime]
        is_transition = entropy >= self.entropy_threshold

        return ProbabilisticRegimeState(
            probabilities=normalized,
            primary_regime=primary_regime,
            regime_confidence=primary_confidence,
            entropy=round(entropy, 4),
            is_transition_state=is_transition,
            timestamp=snapshots[-1].timestamp if snapshots else datetime.now(UTC),
        )
