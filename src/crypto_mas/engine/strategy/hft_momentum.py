"""
HFT Momentum Strategy — Multi-Factor Scoring

Signal sources (all from RealtimeMetricsStore):
  1. Trade flow imbalance (60s window buy/sell ratio)
  2. Order book depth imbalance (bid/ask depth ratio)
  3. CVD direction (is cumulative delta rising?)
  4. RVOL (relative volume — how unusual is this spike?)
  5. VWAP deviation (price above/below VWAP)

All 5 factors must agree for a HIGH-confidence trade.
Partial agreement → lower confidence → smaller position.
"""
from datetime import UTC, datetime

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime import MarketRegime, RegimeSnapshot
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.engine.signal import SignalDirection, SignalType, TradingSignal
from crypto_mas.engine.strategy.base import BaseStrategy
from crypto_mas.engine.strategy.realtime_metrics import RealtimeMetricsStore
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class HFTMomentumStrategy(BaseStrategy):
    """
    Event-driven HFT Momentum strategy.
    Requires multi-factor confirmation before entering a position.
    """

    # Minimum confidence to become CONSIDER_LONG
    MIN_CONFIDENCE = 0.55

    def decide(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        snapshots: list[FeatureSnapshot],
        risk_level: int = 50,
    ) -> TradingDecision | None:
        store = RealtimeMetricsStore()

        # ── Read all real-time signals ───────────────────────────
        imbalance       = store.get_metric(symbol, "imbalance", 0.5)
        depth_imbalance = store.get_metric(symbol, "depth_imbalance", 0.5)
        cvd             = store.get_metric(symbol, "cvd", 0.0)
        rvol_live       = store.get_metric(symbol, "rvol_live", 0.0)
        last_price      = store.get_metric(symbol, "last_price", 0.0)
        vwap            = store.get_metric(symbol, "vwap", 0.0)
        volume_spike    = store.get_metric(symbol, "volume_spike", False)
        window_notional = store.get_metric(symbol, "window_notional", 0.0)

        # Fallback for Backtesting (when RealtimeMetricsStore is empty)
        if last_price == 0.0 and snapshots:
            latest = sorted(snapshots, key=lambda s: s.timestamp)[-1].features_json
            last_price = latest.get("close") or 0.0
            vol = latest.get("volume") or 0.0
            vol_sma = latest.get("volume_sma_20") or 1.0
            rvol_live = vol / vol_sma if vol_sma > 0 else 1.0
            volume_spike = rvol_live >= 3.0
            vwap = latest.get("vwap") or last_price
            rsi = latest.get("rsi_14") or 50.0
            imbalance = 0.5 + (rsi - 50) / 100.0  # Proxy based on RSI
            cvd = 1000.0 if rsi > 50 else -1000.0

        # ── Gate: must have a real volume spike ──────────────────
        if not volume_spike or last_price == 0.0:
            return None

        # ── VWAP deviation ───────────────────────────────────────
        vwap_dev = ((last_price - vwap) / vwap) if vwap > 0 else 0.0

        # ── Feature snapshot for candle-based context ────────────
        candle_rsi = None
        candle_adx = None
        if snapshots:
            latest_features = sorted(snapshots, key=lambda s: s.timestamp)[-1].features_json
            candle_rsi = latest_features.get("rsi_14")
            candle_adx = latest_features.get("adx_14")

        # ── Multi-factor scoring (LONG side) ─────────────────────
        #
        # Each factor contributes a score component.
        # Base = 0.40, then bonuses stacked up to 0.99.

        action     = DecisionAction.HOLD
        direction  = SignalDirection.NEUTRAL
        confidence = 0.0
        factors    = []

        # Factor 1: Trade flow imbalance (primary signal)
        if imbalance > 0.60:
            base = 0.40 + (imbalance - 0.60) * 1.5   # 0.40 → 0.70 as imbalance 0.60→0.80
            confidence += base
            factors.append(f"TF_IMB={imbalance*100:.1f}%")
        elif imbalance < 0.40:
            # Bearish pressure — skip long
            return self._build_hold(exchange, symbol, timeframe, "Imbalance bearish")

        # Factor 2: Order book depth confirmation
        if depth_imbalance > 0.55:
            confidence += 0.08
            factors.append(f"DEPTH={depth_imbalance*100:.1f}%")
        elif depth_imbalance < 0.45:
            confidence -= 0.05  # Penalize: market makers leaning short
            factors.append("DEPTH_WARN")

        # Factor 3: CVD direction
        if cvd > 0:
            confidence += 0.07
            factors.append(f"CVD=+{cvd:,.0f}")
        else:
            confidence -= 0.03
            factors.append(f"CVD={cvd:,.0f}")

        # Factor 4: RVOL (relative volume — how big is this spike?)
        if rvol_live >= 3.0:
            confidence += 0.10   # Very unusual → high conviction
            factors.append(f"RVOL={rvol_live:.1f}x")
        elif rvol_live >= 2.0:
            confidence += 0.05
            factors.append(f"RVOL={rvol_live:.1f}x")

        # Factor 5: VWAP deviation
        if vwap_dev > 0.002:   # price ≥ 0.2% above VWAP → strong momentum
            confidence += 0.08
            factors.append(f"VWAP_DEV={vwap_dev*100:.2f}%")
        elif vwap_dev < -0.001:  # price below VWAP → momentum against us
            confidence -= 0.05
            factors.append("VWAP_NEG")

        # Factor 6: RSI context (from candle features)
        if candle_rsi is not None:
            if candle_rsi < 70:  # Not overbought → room to run
                confidence += 0.05
                factors.append(f"RSI={candle_rsi:.1f}")
            else:
                confidence -= 0.05  # Overbought — penalise
                factors.append(f"RSI_OB={candle_rsi:.1f}")

        # Factor 7: ADX trend strength (from candle features)
        if candle_adx is not None and candle_adx > 20:
            confidence += 0.05
            factors.append(f"ADX={candle_adx:.1f}")

        # ── Decision ─────────────────────────────────────────────
        confidence = max(0.0, min(confidence, 0.99))

        # Dynamic confidence threshold based on risk_level (0-100)
        # Risk 0 -> 0.70, Risk 50 -> 0.55, Risk 100 -> 0.40
        dynamic_min_confidence = 0.70 - (risk_level / 100.0) * 0.30

        if confidence >= dynamic_min_confidence:
            action    = DecisionAction.CONSIDER_LONG
            direction = SignalDirection.LONG

        reason = " | ".join(factors) if factors else "No factors"

        return TradingDecision(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            action=action,
            confidence=confidence,
            signal=TradingSignal(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                signal_type=SignalType.TREND_FOLLOWING,
                direction=direction,
                strength=confidence,
                indicators={
                    "imbalance":       round(imbalance, 4),
                    "depth_imbalance": round(depth_imbalance, 4),
                    "cvd":             round(cvd, 2),
                    "rvol_live":       round(rvol_live, 2),
                    "vwap_dev_pct":    round(vwap_dev * 100, 4),
                    "window_notional": round(window_notional, 0),
                },
                reason=reason,
                timestamp=datetime.now(UTC),
            ),
            score=AssetScore(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                trend_score=round(imbalance, 4),
                momentum_score=round(rvol_live / 5.0, 4),
                volatility_penalty=0.0,
                final_score=confidence,
                components={},
                reason=reason,
                timestamp=datetime.now(UTC),
            ),
            regime=RegimeSnapshot(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                regime=MarketRegime.HIGH_VOLATILITY,
                confidence=confidence,
                risk_multiplier=1.0,
                reason="HFT Event Trigger",
                timestamp=datetime.now(UTC),
            ),
            reason=reason,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def _build_hold(exchange: Exchange, symbol: str, timeframe: Timeframe, reason: str) -> TradingDecision:
        now = datetime.now(UTC)
        return TradingDecision(
            exchange=exchange, symbol=symbol, timeframe=timeframe,
            action=DecisionAction.HOLD, confidence=0.0,
            signal=TradingSignal(
                exchange=exchange, symbol=symbol, timeframe=timeframe,
                signal_type=SignalType.TREND_FOLLOWING, direction=SignalDirection.NEUTRAL,
                strength=0.0, indicators={}, reason=reason, timestamp=now,
            ),
            score=AssetScore(
                exchange=exchange, symbol=symbol, timeframe=timeframe,
                direction=SignalDirection.NEUTRAL, trend_score=0.0,
                momentum_score=0.0, volatility_penalty=0.0,
                final_score=0.0, components={}, reason=reason, timestamp=now,
            ),
            regime=RegimeSnapshot(
                exchange=exchange, symbol=symbol, timeframe=timeframe,
                regime=MarketRegime.SIDEWAYS, confidence=0.0,
                risk_multiplier=1.0, reason=reason, timestamp=now,
            ),
            reason=reason, created_at=now,
        )
