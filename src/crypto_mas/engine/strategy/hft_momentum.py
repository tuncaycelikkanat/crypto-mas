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

        # ── Read realtime last price ─────────────────────────
        last_price = store.get_metric(symbol, "last_price", 0.0)

        # ── Feature snapshot for candle-based context ────────────
        if not snapshots:
            return None
            
        latest_features = sorted(snapshots, key=lambda s: s.timestamp)[-1].features_json
        
        # If RealtimeStore is empty (Backtesting), use candle close
        if last_price == 0.0:
            last_price = latest_features.get("close") or 0.0
            
        if last_price == 0.0:
            return None

        # Extract features
        ema_20 = latest_features.get("ema_20")
        ema_50 = latest_features.get("ema_50")
        adx_14 = latest_features.get("adx_14")
        rsi_14 = latest_features.get("rsi_14")
        stoch_k = latest_features.get("stoch_rsi_k")
        
        # Need all indicators to evaluate pullback
        if not all([ema_20, ema_50, adx_14, rsi_14]):
            return None

        action     = DecisionAction.HOLD
        direction  = SignalDirection.NEUTRAL
        confidence = 0.0
        factors    = []

        # ── Gate 1: Strong Uptrend (EMA & ADX) ──────────────────
        if ema_20 <= ema_50:
            return None  # Not in an uptrend
            
        if adx_14 < 25.0:
            return None  # Trend is too weak

        factors.append(f"TREND(ADX={adx_14:.1f})")

        # ── Gate 2: Micro-Pullback to EMA 20 ────────────────────
        # Price should be within 0.2% of EMA_20 (or slightly below)
        dist_to_ema = (last_price - ema_20) / ema_20
        
        if dist_to_ema > 0.003:
            # Price is too high above EMA 20 (still flying, not a pullback yet)
            return None
            
        if dist_to_ema < -0.005:
            # Price broke support too deeply
            return None

        factors.append(f"PULLBACK({dist_to_ema*100:.2f}%)")
        confidence += 0.50  # Base confidence for reaching pullback zone

        # ── Gate 3: Oversold Momentum ───────────────────────────
        # RSI should be cooling off (dropping below 50)
        if rsi_14 < 45.0:
            confidence += 0.20
            factors.append(f"RSI={rsi_14:.1f}")
        elif stoch_k is not None and stoch_k < 20.0:
            confidence += 0.20
            factors.append(f"STOCH={stoch_k:.1f}")
        else:
            # Not oversold enough on the micro scale
            return None

        # ── Bonus Factors ───────────────────────────────────────
        imbalance = store.get_metric(symbol, "imbalance", 0.5)
        if imbalance > 0.60:
            confidence += 0.15
            factors.append(f"TF_IMB={imbalance*100:.1f}%")
            
        depth_imbalance = store.get_metric(symbol, "depth_imbalance", 0.5)
        if depth_imbalance > 0.55:
            confidence += 0.10
            factors.append(f"DEPTH={depth_imbalance*100:.1f}%")

        # ── Decision ─────────────────────────────────────────────
        confidence = max(0.0, min(confidence, 0.99))

        # Dynamic confidence threshold based on risk_level (0-100)
        # Risk 0 -> 0.85, Risk 50 -> 0.775, Risk 100 -> 0.70
        dynamic_min_confidence = 0.85 - (risk_level / 100.0) * 0.15

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
                signal_type=SignalType.MEAN_REVERSION,  # Changed to Mean Reversion
                direction=direction,
                strength=confidence,
                indicators={
                    "ema_20_dist": round(dist_to_ema * 100, 4),
                    "rsi_14":      round(rsi_14, 2),
                    "adx_14":      round(adx_14, 2),
                    "imbalance":   round(imbalance, 4),
                },
                reason=reason,
                timestamp=datetime.now(UTC),
            ),
            score=AssetScore(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                trend_score=round(adx_14 / 100.0, 4),
                momentum_score=round((100 - rsi_14) / 100.0, 4), # Inverse RSI for pullback score
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
                regime=MarketRegime.BULL_TREND,
                confidence=confidence,
                risk_multiplier=1.0,
                reason="Micro Pullback Trigger",
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
