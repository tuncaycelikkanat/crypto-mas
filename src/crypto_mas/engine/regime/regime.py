from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime import MarketRegime, RegimeSnapshot
from crypto_mas.engine.utils import get_float
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class RegimeEngine:
    def detect(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
    ) -> RegimeSnapshot | None:
        if not snapshots:
            return None

        latest = snapshots[-1]
        features = latest.features_json

        close = get_float(features, "close")
        ema_20 = get_float(features, "ema_20")
        ema_50 = get_float(features, "ema_50")
        atr_14 = get_float(features, "atr_14")
        roc_14 = get_float(features, "roc_14")
        bb_upper = get_float(features, "bb_upper")
        bb_middle = get_float(features, "bb_middle")
        bb_lower = get_float(features, "bb_lower")

        if None in {close, ema_20, ema_50, atr_14, roc_14, bb_upper, bb_middle, bb_lower}:
            return RegimeSnapshot(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                risk_multiplier=0.0,
                reason="Not enough feature data.",
                timestamp=latest.timestamp,
            )

        assert close is not None
        assert ema_20 is not None
        assert ema_50 is not None
        assert atr_14 is not None
        assert roc_14 is not None
        assert bb_upper is not None
        assert bb_middle is not None
        assert bb_lower is not None

        volatility_ratio = atr_14 / close if close > 0 else 0.0
        bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle > 0 else 0.0

        if volatility_ratio > 0.06 or bb_width > 0.12:
            confidence = max(min(volatility_ratio / 0.10, 1.0), min(bb_width / 0.20, 1.0))
            return RegimeSnapshot(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                regime=MarketRegime.HIGH_VOLATILITY,
                confidence=confidence,
                risk_multiplier=0.50,
                reason=f"ATR ratio ({volatility_ratio:.2f}) or BB width ({bb_width:.2f}) indicates high volatility.",
                timestamp=latest.timestamp,
            )

        bullish = close > ema_20 > ema_50 and roc_14 > 0
        bearish = close < ema_20 < ema_50 and roc_14 < 0

        if bullish:
            confidence = self._trend_confidence(
                close=close,
                ema_20=ema_20,
                ema_50=ema_50,
                roc_14=roc_14,
            )
            return RegimeSnapshot(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                regime=MarketRegime.BULL_TREND,
                confidence=confidence,
                risk_multiplier=1.0,
                reason="Close > EMA20 > EMA50 and ROC > 0.",
                timestamp=latest.timestamp,
            )

        if bearish:
            confidence = self._trend_confidence(
                close=close,
                ema_20=ema_20,
                ema_50=ema_50,
                roc_14=roc_14,
            )
            return RegimeSnapshot(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                regime=MarketRegime.BEAR_TREND,
                confidence=confidence,
                risk_multiplier=0.30,
                reason="Close < EMA20 < EMA50 and ROC < 0.",
                timestamp=latest.timestamp,
            )

        return RegimeSnapshot(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            regime=MarketRegime.SIDEWAYS,
            confidence=0.55,
            risk_multiplier=0.60,
            reason="Trend conditions are not clearly bullish or bearish.",
            timestamp=latest.timestamp,
        )


    @staticmethod
    def _trend_confidence(
        close: float,
        ema_20: float,
        ema_50: float,
        roc_14: float,
    ) -> float:
        if close <= 0:
            return 0.0

        ema_spread = abs(ema_20 - ema_50) / close
        price_distance = abs(close - ema_20) / close
        roc_component = abs(roc_14) / 10

        confidence = (ema_spread * 10) + (price_distance * 5) + (roc_component * 0.5)

        return max(0.0, min(confidence, 1.0))
