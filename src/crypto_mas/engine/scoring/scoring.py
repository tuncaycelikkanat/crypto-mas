from math import tanh

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.signal import SignalDirection, TradingSignal
from crypto_mas.engine.utils import get_float
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class ScoringEngine:
    def __init__(
        self,
        trend_weight: float = 0.55,
        momentum_weight: float = 0.45,
    ) -> None:
        self.trend_weight = trend_weight
        self.momentum_weight = momentum_weight

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

        close = get_float(features, "close")
        ema_20 = get_float(features, "ema_20")
        ema_50 = get_float(features, "ema_50")
        rsi_14 = get_float(features, "rsi_14")
        roc_14 = get_float(features, "roc_14")
        atr_14 = get_float(features, "atr_14")
        macd = get_float(features, "macd")
        macd_signal = get_float(features, "macd_signal")

        if None in {close, ema_20, ema_50, rsi_14, roc_14, atr_14, macd, macd_signal}:
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
        assert macd is not None
        assert macd_signal is not None

        # RSI slope from last 3 snapshots
        rsi_slope = 0.0
        if len(snapshots) >= 3:
            rsi_values = []
            for snap in snapshots[-3:]:
                rsi_val = get_float(snap.features_json, "rsi_14")
                if rsi_val is not None:
                    rsi_values.append(rsi_val)
            if len(rsi_values) >= 2:
                rsi_slope = rsi_values[-1] - sum(rsi_values[:-1]) / len(rsi_values[:-1])

        trend_score = self._trend_score(
            close=close,
            ema_20=ema_20,
            ema_50=ema_50,
            direction=signal.direction,
        )
        momentum_score = self._momentum_score(
            rsi_14=rsi_14,
            roc_14=roc_14,
            macd=macd,
            macd_signal=macd_signal,
            atr_14=atr_14,
            close=close,
            direction=signal.direction,
        )
        volatility_penalty = self._volatility_penalty(
            close=close,
            atr_14=atr_14,
        )

        # RSI slope bonus: +0.08 extra momentum if slope confirms direction
        rsi_bonus = 0.0
        if signal.direction == SignalDirection.LONG and rsi_slope > 0:
            rsi_bonus = 0.08
        elif signal.direction == SignalDirection.SHORT and rsi_slope < 0:
            rsi_bonus = 0.08

        adjusted_momentum = min(momentum_score + rsi_bonus, 1.0)

        if signal.direction == SignalDirection.NEUTRAL:
            final_score = 0.0
        else:
            raw_score = (trend_score * self.trend_weight) + (adjusted_momentum * self.momentum_weight)
            final_score = max(0.0, min(raw_score - volatility_penalty, 1.0))

        return AssetScore(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            direction=signal.direction,
            final_score=final_score,
            trend_score=trend_score,
            momentum_score=adjusted_momentum,
            volatility_penalty=volatility_penalty,
            reason=(
                f"Score = trend*{self.trend_weight:.2f} + momentum*{self.momentum_weight:.2f} - volatility_penalty. "
                f"Signal direction: {signal.direction.value}."
            ),
            timestamp=latest.timestamp,
        )


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
        macd: float,
        macd_signal: float,
        atr_14: float,
        close: float,
        direction: SignalDirection,
    ) -> float:
        if close <= 0:
            return 0.0

        macd_hist = macd - macd_signal

        # ATR-normalized MACD score using tanh
        norm_denom = max(atr_14 * 0.1, 1e-9)

        if direction == SignalDirection.LONG:
            rsi_score = max((rsi_14 - 50) / 50, 0.0)
            roc_score = max(roc_14 / 10, 0.0)
            macd_score = max(tanh(macd_hist / norm_denom), 0.0)
        elif direction == SignalDirection.SHORT:
            rsi_score = max((50 - rsi_14) / 50, 0.0)
            roc_score = max((-roc_14) / 10, 0.0)
            macd_score = max(tanh(-macd_hist / norm_denom), 0.0)
        else:
            return 0.0

        return max(0.0, min((rsi_score * 0.3) + (roc_score * 0.3) + (macd_score * 0.4), 1.0))

    @staticmethod
    def _volatility_penalty(close: float, atr_14: float) -> float:
        if close <= 0:
            return 0.0

        atr_ratio = atr_14 / close

        # ATR / close %5 üstündeyse daha ciddi ceza üretir.
        return max(0.0, min(atr_ratio * 2, 0.35))
