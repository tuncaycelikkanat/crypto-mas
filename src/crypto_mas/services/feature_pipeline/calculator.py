from decimal import Decimal
from math import isfinite
from typing import Any

from crypto_mas.domain.models.candle import Candle


class FeatureCalculator:
    def calculate(self, candles: list[Candle]) -> list[dict[str, Any]]:
        if len(candles) < 60:
            return []

        closes = [float(candle.close) for candle in candles]
        highs = [float(candle.high) for candle in candles]
        lows = [float(candle.low) for candle in candles]

        ema_20 = self._ema(closes, period=20)
        ema_50 = self._ema(closes, period=50)
        sma_20 = self._sma(closes, period=20)
        rsi_14 = self._rsi(closes, period=14)
        atr_14 = self._atr(highs, lows, closes, period=14)
        roc_14 = self._roc(closes, period=14)
        macd, macd_signal, macd_hist = self._macd(closes)
        bb_upper, bb_middle, bb_lower = self._bollinger_bands(closes, period=20, num_std=2.0)

        snapshots: list[dict[str, Any]] = []

        for index, candle in enumerate(candles):
            features = {
                "close": self._safe_float(closes[index]),
                "ema_20": self._safe_float(ema_20[index]),
                "ema_50": self._safe_float(ema_50[index]),
                "sma_20": self._safe_float(sma_20[index]),
                "rsi_14": self._safe_float(rsi_14[index]),
                "atr_14": self._safe_float(atr_14[index]),
                "roc_14": self._safe_float(roc_14[index]),
                "macd": self._safe_float(macd[index]),
                "macd_signal": self._safe_float(macd_signal[index]),
                "macd_hist": self._safe_float(macd_hist[index]),
                "bb_upper": self._safe_float(bb_upper[index]),
                "bb_middle": self._safe_float(bb_middle[index]),
                "bb_lower": self._safe_float(bb_lower[index]),
            }

            snapshots.append(
                {
                    "exchange": candle.exchange,
                    "symbol": candle.symbol,
                    "timeframe": candle.timeframe,
                    "timestamp": candle.open_time,
                    "available_at": candle.close_time,
                    "features_json": features,
                }
            )

        return snapshots

    def _sma(self, values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = []

        for index in range(len(values)):
            if index + 1 < period:
                result.append(None)
                continue

            window = values[index + 1 - period : index + 1]
            result.append(sum(window) / period)

        return result

    def _ema(self, values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = []
        multiplier = 2 / (period + 1)
        ema_value: float | None = None

        for index, value in enumerate(values):
            if index + 1 < period:
                result.append(None)
                continue

            if ema_value is None:
                window = values[index + 1 - period : index + 1]
                ema_value = sum(window) / period
            else:
                ema_value = (value - ema_value) * multiplier + ema_value

            result.append(ema_value)

        return result

    def _rsi(self, values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(values)

        if len(values) <= period:
            return result

        gains: list[float] = []
        losses: list[float] = []

        for index in range(1, period + 1):
            delta = values[index] - values[index - 1]
            gains.append(max(delta, 0))
            losses.append(abs(min(delta, 0)))

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        result[period] = self._rsi_value(avg_gain, avg_loss)

        for index in range(period + 1, len(values)):
            delta = values[index] - values[index - 1]
            gain = max(delta, 0)
            loss = abs(min(delta, 0))

            avg_gain = ((avg_gain * (period - 1)) + gain) / period
            avg_loss = ((avg_loss * (period - 1)) + loss) / period

            result[index] = self._rsi_value(avg_gain, avg_loss)

        return result

    @staticmethod
    def _rsi_value(avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _atr(
        self,
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int,
    ) -> list[float | None]:
        result: list[float | None] = [None] * len(closes)
        true_ranges: list[float] = []

        for index in range(len(closes)):
            if index == 0:
                true_range = highs[index] - lows[index]
            else:
                true_range = max(
                    highs[index] - lows[index],
                    abs(highs[index] - closes[index - 1]),
                    abs(lows[index] - closes[index - 1]),
                )

            true_ranges.append(true_range)

        for index in range(len(closes)):
            if index + 1 < period:
                continue

            window = true_ranges[index + 1 - period : index + 1]
            result[index] = sum(window) / period

        return result

    def _roc(self, values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = []

        for index, value in enumerate(values):
            if index < period:
                result.append(None)
                continue

            previous = values[index - period]

            if previous == 0:
                result.append(None)
                continue

            result.append(((value - previous) / previous) * 100)

        return result

    def _macd(self, values: list[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> tuple[list[float | None], list[float | None], list[float | None]]:
        macd_line: list[float | None] = [None] * len(values)
        macd_signal: list[float | None] = [None] * len(values)
        macd_hist: list[float | None] = [None] * len(values)

        ema_fast = self._ema(values, period=fast_period)
        ema_slow = self._ema(values, period=slow_period)

        for i in range(len(values)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line[i] = ema_fast[i] - ema_slow[i]

        valid_macd_start = next((i for i, v in enumerate(macd_line) if v is not None), -1)
        if valid_macd_start != -1:
            valid_macd_values = [v for v in macd_line if v is not None]
            signal_ema = self._ema(valid_macd_values, period=signal_period)
            
            for i, sig_val in enumerate(signal_ema):
                actual_idx = valid_macd_start + i
                macd_signal[actual_idx] = sig_val
                
                if macd_line[actual_idx] is not None and sig_val is not None:
                    macd_hist[actual_idx] = macd_line[actual_idx] - sig_val

        return macd_line, macd_signal, macd_hist

    def _bollinger_bands(
        self, values: list[float], period: int = 20, num_std: float = 2.0
    ) -> tuple[list[float | None], list[float | None], list[float | None]]:
        import math
        upper: list[float | None] = []
        middle: list[float | None] = []
        lower: list[float | None] = []

        for i in range(len(values)):
            if i + 1 < period:
                upper.append(None)
                middle.append(None)
                lower.append(None)
                continue

            window = values[i + 1 - period: i + 1]
            sma = sum(window) / period
            variance = sum((x - sma) ** 2 for x in window) / period
            std = math.sqrt(variance)

            upper.append(sma + num_std * std)
            middle.append(sma)
            lower.append(sma - num_std * std)

        return upper, middle, lower

    @staticmethod
    def _safe_float(value: float | None) -> float | None:
        if value is None:
            return None

        if not isfinite(value):
            return None

        return float(Decimal(str(value)))
