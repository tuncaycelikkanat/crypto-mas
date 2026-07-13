from decimal import Decimal
from math import isfinite, sqrt
from typing import Any

from crypto_mas.domain.models.candle import Candle


class FeatureCalculator:
    def calculate(self, candles: list[Candle]) -> list[dict[str, Any]]:
        if len(candles) < 60:
            return []

        closes  = [float(candle.close)  for candle in candles]
        highs   = [float(candle.high)   for candle in candles]
        lows    = [float(candle.low)    for candle in candles]
        opens   = [float(candle.open)   for candle in candles]
        volumes = [float(candle.volume) for candle in candles]

        # ── Price-based indicators ─────────────────────────────
        ema_20 = self._ema(closes, period=20)
        ema_50 = self._ema(closes, period=50)
        sma_20 = self._sma(closes, period=20)
        rsi_14 = self._rsi(closes, period=14)
        atr_14 = self._atr(highs, lows, closes, period=14)
        roc_14 = self._roc(closes, period=14)
        macd, macd_signal, macd_hist = self._macd(closes)
        bb_upper, bb_middle, bb_lower = self._bollinger_bands(closes, period=20, num_std=2.0)
        adx_14, plus_di, minus_di    = self._adx(highs, lows, closes, period=14)
        stoch_k, stoch_d             = self._stoch_rsi(closes, rsi_period=14, stoch_period=14, k_period=3, d_period=3)

        # ── Volume-based indicators ────────────────────────────
        volume_sma_20 = self._sma(volumes, period=20)
        rvol          = self._rvol(volumes, volume_sma_20)
        obv           = self._obv(closes, volumes)
        cmf_20        = self._cmf(highs, lows, closes, volumes, period=20)

        snapshots: list[dict[str, Any]] = []

        for index, candle in enumerate(candles):
            features = {
                # Price
                "open":           self._safe_float(opens[index]),
                "high":           self._safe_float(highs[index]),
                "low":            self._safe_float(lows[index]),
                "close":          self._safe_float(closes[index]),
                # Volume
                "volume":         self._safe_float(volumes[index]),
                "volume_sma_20":  self._safe_float(volume_sma_20[index]),
                "rvol":           self._safe_float(rvol[index]),
                "obv":            self._safe_float(obv[index]),
                "cmf_20":         self._safe_float(cmf_20[index]),
                # Trend
                "ema_20":         self._safe_float(ema_20[index]),
                "ema_50":         self._safe_float(ema_50[index]),
                "sma_20":         self._safe_float(sma_20[index]),
                "adx_14":         self._safe_float(adx_14[index]),
                "plus_di":        self._safe_float(plus_di[index]),
                "minus_di":       self._safe_float(minus_di[index]),
                # Momentum
                "rsi_14":         self._safe_float(rsi_14[index]),
                "stoch_rsi_k":    self._safe_float(stoch_k[index]),
                "stoch_rsi_d":    self._safe_float(stoch_d[index]),
                "roc_14":         self._safe_float(roc_14[index]),
                "macd":           self._safe_float(macd[index]),
                "macd_signal":    self._safe_float(macd_signal[index]),
                "macd_hist":      self._safe_float(macd_hist[index]),
                # Volatility
                "atr_14":         self._safe_float(atr_14[index]),
                "bb_upper":       self._safe_float(bb_upper[index]),
                "bb_middle":      self._safe_float(bb_middle[index]),
                "bb_lower":       self._safe_float(bb_lower[index]),
            }

            snapshots.append(
                {
                    "exchange":    candle.exchange,
                    "symbol":      candle.symbol,
                    "timeframe":   candle.timeframe,
                    "timestamp":   candle.open_time,
                    "available_at": candle.close_time,
                    "features_json": features,
                }
            )

        return snapshots

    # ── SMA ────────────────────────────────────────────────────
    def _sma(self, values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = []
        for index in range(len(values)):
            if index + 1 < period:
                result.append(None)
                continue
            window = values[index + 1 - period: index + 1]
            result.append(sum(window) / period)
        return result

    # ── EMA ────────────────────────────────────────────────────
    def _ema(self, values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = []
        multiplier = 2 / (period + 1)
        ema_value: float | None = None
        for index, value in enumerate(values):
            if index + 1 < period:
                result.append(None)
                continue
            if ema_value is None:
                window = values[index + 1 - period: index + 1]
                ema_value = sum(window) / period
            else:
                ema_value = (value - ema_value) * multiplier + ema_value
            result.append(ema_value)
        return result

    # ── RSI ────────────────────────────────────────────────────
    def _rsi(self, values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(values)
        if len(values) <= period:
            return result
        gains, losses = [], []
        for index in range(1, period + 1):
            delta = values[index] - values[index - 1]
            gains.append(max(delta, 0))
            losses.append(abs(min(delta, 0)))
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        result[period] = self._rsi_value(avg_gain, avg_loss)
        for index in range(period + 1, len(values)):
            delta = values[index] - values[index - 1]
            avg_gain = ((avg_gain * (period - 1)) + max(delta, 0)) / period
            avg_loss = ((avg_loss * (period - 1)) + abs(min(delta, 0))) / period
            result[index] = self._rsi_value(avg_gain, avg_loss)
        return result

    @staticmethod
    def _rsi_value(avg_gain: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 100.0
        return 100 - (100 / (1 + avg_gain / avg_loss))

    # ── Stochastic RSI ─────────────────────────────────────────
    def _stoch_rsi(
        self, closes: list[float],
        rsi_period: int = 14, stoch_period: int = 14,
        k_period: int = 3, d_period: int = 3
    ) -> tuple[list[float | None], list[float | None]]:
        rsi = self._rsi(closes, rsi_period)
        n = len(closes)
        raw_k: list[float | None] = [None] * n

        for i in range(n):
            if rsi[i] is None:
                continue
            window_start = max(0, i - stoch_period + 1)
            window = [r for r in rsi[window_start: i + 1] if r is not None]
            if len(window) < stoch_period:
                continue
            hi = max(window)
            lo = min(window)
            raw_k[i] = ((rsi[i] - lo) / (hi - lo) * 100) if hi != lo else 50.0

        raw_k_valid = [v for v in raw_k if v is not None]
        if not raw_k_valid:
            return [None] * n, [None] * n

        # Smooth %K with SMA(k_period)
        k_sma = self._sma(raw_k_valid, k_period)
        k_vals: list[float | None] = [None] * n
        valid_idx = [i for i, v in enumerate(raw_k) if v is not None]
        for offset, idx in enumerate(valid_idx):
            k_vals[idx] = k_sma[offset]

        # %D = SMA(k_period, %K)
        k_for_d = [v for v in k_vals if v is not None]
        d_sma = self._sma(k_for_d, d_period)
        d_vals: list[float | None] = [None] * n
        valid_k_idx = [i for i, v in enumerate(k_vals) if v is not None]
        for offset, idx in enumerate(valid_k_idx):
            d_vals[idx] = d_sma[offset]

        return k_vals, d_vals

    # ── ATR ────────────────────────────────────────────────────
    def _atr(self, highs: list[float], lows: list[float], closes: list[float], period: int) -> list[float | None]:
        result: list[float | None] = [None] * len(closes)
        true_ranges: list[float] = []
        for index in range(len(closes)):
            if index == 0:
                tr = highs[index] - lows[index]
            else:
                tr = max(highs[index] - lows[index], abs(highs[index] - closes[index - 1]), abs(lows[index] - closes[index - 1]))
            true_ranges.append(tr)
        for index in range(len(closes)):
            if index + 1 < period:
                continue
            result[index] = sum(true_ranges[index + 1 - period: index + 1]) / period
        return result

    # ── ADX ────────────────────────────────────────────────────
    def _adx(self, highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> tuple[list[float | None], list[float | None], list[float | None]]:
        n = len(closes)
        adx_out:    list[float | None] = [None] * n
        plus_di_out: list[float | None] = [None] * n
        minus_di_out:list[float | None] = [None] * n

        if n < period * 2:
            return adx_out, plus_di_out, minus_di_out

        plus_dm:  list[float] = []
        minus_dm: list[float] = []
        true_ranges: list[float] = []

        for i in range(1, n):
            h_diff = highs[i] - highs[i - 1]
            l_diff = lows[i - 1] - lows[i]
            plus_dm.append(h_diff if h_diff > l_diff and h_diff > 0 else 0.0)
            minus_dm.append(l_diff if l_diff > h_diff and l_diff > 0 else 0.0)
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
            true_ranges.append(tr)

        def _wilders_smooth(values: list[float], p: int) -> list[float]:
            result = [None] * len(values)  # type: ignore[assignment]
            if len(values) < p:
                return result  # type: ignore[return-value]
            result[p - 1] = sum(values[:p])
            for i in range(p, len(values)):
                result[i] = result[i - 1] - (result[i - 1] / p) + values[i]  # type: ignore[operator]
            return result  # type: ignore[return-value]

        sm_atr  = _wilders_smooth(true_ranges, period)
        sm_plus = _wilders_smooth(plus_dm, period)
        sm_minus= _wilders_smooth(minus_dm, period)

        dx_vals: list[float] = []
        for i in range(period - 1, len(true_ranges)):
            if sm_atr[i] is None or sm_atr[i] == 0:
                dx_vals.append(0.0)
                continue
            pdi = (sm_plus[i] / sm_atr[i]) * 100  # type: ignore[operator]
            mdi = (sm_minus[i] / sm_atr[i]) * 100  # type: ignore[operator]
            plus_di_out[i + 1] = pdi
            minus_di_out[i + 1] = mdi
            denom = pdi + mdi
            dx_vals.append(abs(pdi - mdi) / denom * 100 if denom else 0.0)

        # ADX = smoothed DX
        if len(dx_vals) >= period:
            adx_sm = _wilders_smooth(dx_vals, period)
            for i, v in enumerate(adx_sm):
                out_idx = i + period  # offset back to original array
                if out_idx < n and v is not None:
                    adx_out[out_idx] = v

        return adx_out, plus_di_out, minus_di_out

    # ── ROC ────────────────────────────────────────────────────
    def _roc(self, values: list[float], period: int) -> list[float | None]:
        result: list[float | None] = []
        for index, value in enumerate(values):
            if index < period:
                result.append(None)
                continue
            previous = values[index - period]
            result.append(((value - previous) / previous * 100) if previous != 0 else None)
        return result

    # ── MACD ───────────────────────────────────────────────────
    def _macd(self, values: list[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> tuple[list[float | None], list[float | None], list[float | None]]:
        macd_line:   list[float | None] = [None] * len(values)
        macd_signal: list[float | None] = [None] * len(values)
        macd_hist:   list[float | None] = [None] * len(values)

        ema_fast = self._ema(values, period=fast_period)
        ema_slow = self._ema(values, period=slow_period)

        for i in range(len(values)):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line[i] = ema_fast[i] - ema_slow[i]  # type: ignore[operator]

        valid_start = next((i for i, v in enumerate(macd_line) if v is not None), -1)
        if valid_start != -1:
            valid_macd = [v for v in macd_line if v is not None]
            sig_ema = self._ema(valid_macd, period=signal_period)
            for i, sig in enumerate(sig_ema):
                actual = valid_start + i
                macd_signal[actual] = sig
                if macd_line[actual] is not None and sig is not None:
                    macd_hist[actual] = macd_line[actual] - sig  # type: ignore[operator]

        return macd_line, macd_signal, macd_hist

    # ── Bollinger Bands ────────────────────────────────────────
    def _bollinger_bands(self, values: list[float], period: int = 20, num_std: float = 2.0) -> tuple[list[float | None], list[float | None], list[float | None]]:
        upper: list[float | None] = []
        middle: list[float | None] = []
        lower: list[float | None] = []
        for i in range(len(values)):
            if i + 1 < period:
                upper.append(None); middle.append(None); lower.append(None)
                continue
            window = values[i + 1 - period: i + 1]
            sma = sum(window) / period
            std = sqrt(sum((x - sma) ** 2 for x in window) / period)
            upper.append(sma + num_std * std)
            middle.append(sma)
            lower.append(sma - num_std * std)
        return upper, middle, lower

    # ── OBV (On-Balance Volume) ────────────────────────────────
    def _obv(self, closes: list[float], volumes: list[float]) -> list[float | None]:
        result: list[float | None] = [None] * len(closes)
        if not closes:
            return result
        cumulative = 0.0
        result[0] = 0.0
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                cumulative += volumes[i]
            elif closes[i] < closes[i - 1]:
                cumulative -= volumes[i]
            result[i] = cumulative
        return result

    # ── RVOL (Relative Volume) ─────────────────────────────────
    def _rvol(self, volumes: list[float], volume_sma: list[float | None]) -> list[float | None]:
        """Current volume / average volume. >2 = significant spike."""
        result: list[float | None] = []
        for vol, sma in zip(volumes, volume_sma):
            if sma is None or sma == 0:
                result.append(None)
            else:
                result.append(round(vol / sma, 4))
        return result

    # ── CMF (Chaikin Money Flow) ───────────────────────────────
    def _cmf(self, highs: list[float], lows: list[float], closes: list[float], volumes: list[float], period: int = 20) -> list[float | None]:
        """CMF = sum(MFV, period) / sum(volume, period)
        MFV = ((close - low) - (high - close)) / (high - low) * volume"""
        n = len(closes)
        mfv: list[float] = []
        for i in range(n):
            hl = highs[i] - lows[i]
            if hl == 0:
                mfv.append(0.0)
            else:
                mf_multiplier = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / hl
                mfv.append(mf_multiplier * volumes[i])

        result: list[float | None] = [None] * n
        for i in range(period - 1, n):
            vol_sum = sum(volumes[i + 1 - period: i + 1])
            if vol_sum == 0:
                result[i] = 0.0
            else:
                result[i] = sum(mfv[i + 1 - period: i + 1]) / vol_sum
        return result

    @staticmethod
    def _safe_float(value: float | None) -> float | None:
        if value is None:
            return None
        if not isfinite(value):
            return None
        return float(Decimal(str(round(value, 8))))
