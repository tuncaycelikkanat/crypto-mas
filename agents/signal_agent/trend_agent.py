from typing import Any

from agents.signal_agent.schemas import SignalDirection, SignalType, TradingSignal
from domain.models.feature_snapshot import FeatureSnapshot
from services.market_data_service.schemas import Exchange, Timeframe


class TrendSignalAgent:
    def generate(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
    ) -> TradingSignal | None:
        if not snapshots:
            return None

        latest = snapshots[-1]
        features = latest.features_json

        close = self._get_float(features, "close")
        ema_20 = self._get_float(features, "ema_20")
        ema_50 = self._get_float(features, "ema_50")
        rsi_14 = self._get_float(features, "rsi_14")
        roc_14 = self._get_float(features, "roc_14")

        if None in {close, ema_20, ema_50, rsi_14, roc_14}:
            return TradingSignal(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                signal_type=SignalType.TREND_FOLLOWING,
                direction=SignalDirection.NEUTRAL,
                strength=0.0,
                reason="Not enough feature data.",
                timestamp=latest.timestamp,
            )

        assert close is not None
        assert ema_20 is not None
        assert ema_50 is not None
        assert rsi_14 is not None
        assert roc_14 is not None

        bullish = close > ema_20 > ema_50 and rsi_14 > 50 and roc_14 > 0
        bearish = close < ema_20 < ema_50 and rsi_14 < 50 and roc_14 < 0

        if bullish:
            strength = self._calculate_strength(
                close=close,
                ema_20=ema_20,
                ema_50=ema_50,
                rsi_14=rsi_14,
                roc_14=roc_14,
                bullish=True,
            )
            return TradingSignal(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                signal_type=SignalType.TREND_FOLLOWING,
                direction=SignalDirection.LONG,
                strength=strength,
                reason="Close > EMA20 > EMA50, RSI > 50, ROC > 0.",
                timestamp=latest.timestamp,
            )

        if bearish:
            strength = self._calculate_strength(
                close=close,
                ema_20=ema_20,
                ema_50=ema_50,
                rsi_14=rsi_14,
                roc_14=roc_14,
                bullish=False,
            )
            return TradingSignal(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                signal_type=SignalType.TREND_FOLLOWING,
                direction=SignalDirection.SHORT,
                strength=strength,
                reason="Close < EMA20 < EMA50, RSI < 50, ROC < 0.",
                timestamp=latest.timestamp,
            )

        return TradingSignal(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            signal_type=SignalType.TREND_FOLLOWING,
            direction=SignalDirection.NEUTRAL,
            strength=0.0,
            reason="Trend conditions not met.",
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
    def _calculate_strength(
        close: float,
        ema_20: float,
        ema_50: float,
        rsi_14: float,
        roc_14: float,
        bullish: bool,
    ) -> float:
        ema_spread = abs(ema_20 - ema_50) / close
        rsi_component = abs(rsi_14 - 50) / 50
        roc_component = abs(roc_14) / 10

        raw_strength = (ema_spread * 2) + (rsi_component * 0.5) + (roc_component * 0.5)

        if not bullish:
            raw_strength *= 0.9

        return max(0.0, min(raw_strength, 1.0))
