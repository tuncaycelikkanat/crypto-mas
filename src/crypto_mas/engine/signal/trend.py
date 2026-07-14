from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.signal import SignalDirection, SignalType, TradingSignal
from crypto_mas.engine.utils import get_float
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class TrendSignalEngine:
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

        close = get_float(features, "close")
        ema_20 = get_float(features, "ema_20")
        ema_50 = get_float(features, "ema_50")
        rsi_14 = get_float(features, "rsi_14")
        roc_14 = get_float(features, "roc_14")
        macd = get_float(features, "macd")
        macd_signal = get_float(features, "macd_signal")

        if None in {close, ema_20, ema_50, rsi_14, roc_14, macd, macd_signal}:
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
        assert macd is not None
        assert macd_signal is not None

        macd_bullish = macd > macd_signal
        macd_bearish = macd < macd_signal

        bullish = close > ema_20 > ema_50 and rsi_14 > 50 and roc_14 > 0 and macd_bullish
        bearish = close < ema_20 < ema_50 and rsi_14 < 50 and roc_14 < 0 and macd_bearish

        if bullish:
            strength = self._calculate_strength(
                close=close,
                ema_20=ema_20,
                ema_50=ema_50,
                rsi_14=rsi_14,
                roc_14=roc_14,
                macd=macd,
                macd_signal=macd_signal,
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
                macd=macd,
                macd_signal=macd_signal,
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
    def _calculate_strength(
        close: float,
        ema_20: float,
        ema_50: float,
        rsi_14: float,
        roc_14: float,
        macd: float,
        macd_signal: float,
        bullish: bool,
    ) -> float:
        ema_spread = abs(ema_20 - ema_50) / close
        rsi_component = abs(rsi_14 - 50) / 50
        roc_component = abs(roc_14) / 10
        macd_component = abs(macd - macd_signal) / close if close > 0 else 0

        raw_strength = (ema_spread * 2) + (rsi_component * 0.4) + (roc_component * 0.3) + (macd_component * 10)

        if not bullish:
            raw_strength *= 0.9

        return max(0.0, min(raw_strength, 1.0))
