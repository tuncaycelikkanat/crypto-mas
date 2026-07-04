from typing import Any

from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.signal import SignalDirection, TradingSignal
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class ScoringEngine:
    def score(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        signal: TradingSignal,
        snapshots: list[FeatureSnapshot],
    ) -> AssetScore | None:
        if not snapshots:
            return None

        latest = snapshots[-1]
        features = latest.features_json

        close = self._get_float(features, "close")
        ema_20 = self._get_float(features, "ema_20")
        ema_50 = self._get_float(features, "ema_50")
        rsi_14 = self._get_float(features, "rsi_14")
        roc_14 = self._get_float(features, "roc_14")
        atr_14 = self._get_float(features, "atr_14")

        if None in {close, ema_20, ema_50, rsi_14, roc_14, atr_14}:
            return AssetScore(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                direction=signal.direction,
                final_score=0.0,
                trend_score=0.0,
                momentum_score=0.0,
                volatility_penalty=0.0,
                reason="Not enough feature data.",
                timestamp=latest.timestamp,
            )

        assert close is not None
        assert ema_20 is not None
        assert ema_50 is not None
        assert rsi_14 is not None
        assert roc_14 is not None
        assert atr_14 is not None

        trend_score = self._trend_score(
            close=close,
            ema_20=ema_20,
            ema_50=ema_50,
            direction=signal.direction,
        )
        momentum_score = self._momentum_score(
            rsi_14=rsi_14,
            roc_14=roc_14,
            direction=signal.direction,
        )
        volatility_penalty = self._volatility_penalty(
            close=close,
            atr_14=atr_14,
        )

        if signal.direction == SignalDirection.NEUTRAL:
            final_score = 0.0
        else:
            raw_score = (trend_score * 0.55) + (momentum_score * 0.45)
            final_score = max(0.0, min(raw_score - volatility_penalty, 1.0))

        return AssetScore(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            direction=signal.direction,
            final_score=final_score,
            trend_score=trend_score,
            momentum_score=momentum_score,
            volatility_penalty=volatility_penalty,
            reason=(
                "Score = trend*0.55 + momentum*0.45 - volatility_penalty. "
                f"Signal direction: {signal.direction.value}."
            ),
            timestamp=latest.timestamp,
        )

    @staticmethod
    def _get_float(features: dict[str, Any], key: str) -> float | None:
        value = features.get(key)

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _trend_score(
        close: float,
        ema_20: float,
        ema_50: float,
        direction: SignalDirection,
    ) -> float:
        if close <= 0:
            return 0.0

        if direction == SignalDirection.LONG:
            ema_spread = max((ema_20 - ema_50) / close, 0.0)
            price_distance = max((close - ema_20) / close, 0.0)
        elif direction == SignalDirection.SHORT:
            ema_spread = max((ema_50 - ema_20) / close, 0.0)
            price_distance = max((ema_20 - close) / close, 0.0)
        else:
            return 0.0

        return max(0.0, min((ema_spread * 20) + (price_distance * 10), 1.0))

    @staticmethod
    def _momentum_score(
        rsi_14: float,
        roc_14: float,
        direction: SignalDirection,
    ) -> float:
        if direction == SignalDirection.LONG:
            rsi_score = max((rsi_14 - 50) / 50, 0.0)
            roc_score = max(roc_14 / 10, 0.0)
        elif direction == SignalDirection.SHORT:
            rsi_score = max((50 - rsi_14) / 50, 0.0)
            roc_score = max((-roc_14) / 10, 0.0)
        else:
            return 0.0

        return max(0.0, min((rsi_score * 0.5) + (roc_score * 0.5), 1.0))

    @staticmethod
    def _volatility_penalty(close: float, atr_14: float) -> float:
        if close <= 0:
            return 0.0

        atr_ratio = atr_14 / close

        # ATR / close %5 üstündeyse daha ciddi ceza üretir.
        return max(0.0, min(atr_ratio * 2, 0.35))
