from crypto_mas.engine.portfolio import PortfolioTarget, TargetPosition
from crypto_mas.engine.strategy.schemas import DecisionAction, TradingDecision
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.engine.regime import MarketRegime

# BTC-correlated asset group for concentration risk control
BTC_CORRELATED = {"BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT"}

# Asset groups for dynamic regime weighting
COIN_GROUPS = {
    "TOP10": {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "LINKUSDT", "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "DOTUSDT"},
    "MEMES": {"DOGEUSDT", "SHIBUSDT", "FLOKIUSDT", "PEPEUSDT", "BONKUSDT", "WIFUSDT"},
    "L1": {"SOLUSDT", "ADAUSDT", "AVAXUSDT", "NEARUSDT", "FTMUSDT", "APTUSDT", "SUIUSDT", "INJUSDT"},
    "AI_HYPE": {"INJUSDT", "RNDRUSDT", "FETUSDT", "OCEANUSDT", "AGIXUSDT", "TAOUSDT"}
}


class PortfolioEngine:
    def __init__(
        self,
        max_positions: int = 10,
        max_gross_exposure: float = 0.85,
        min_confidence: float = 0.5,
        max_correlated_group_weight: float = 0.40,
        time_provider: TimeProvider | None = None,
    ) -> None:
        self.max_positions = max_positions
        self.max_gross_exposure = max_gross_exposure
        self.min_confidence = min_confidence
        self.max_correlated_group_weight = max_correlated_group_weight
        self.time_provider = time_provider or SystemTimeProvider()

    def build_target_portfolio(
        self,
        exchange: Exchange,
        timeframe: Timeframe,
        decisions: list[TradingDecision],
        open_positions: list[str] | None = None,
        risk_level: int = 100,
    ) -> PortfolioTarget:
        open_symbols = set(open_positions) if open_positions else set()
        
        # 1. Process explicit CLOSE decisions
        close_decisions = {
            d.symbol: d
            for d in decisions
            if d.action in (DecisionAction.CLOSE_LONG, DecisionAction.CLOSE_SHORT)
        }
        
        # Remove symbols that have a CLOSE decision from the retained list
        retained_symbols = open_symbols - set(close_decisions.keys())
        
        # Apply Regime-Based Dynamic Adjustments
        for decision in decisions:
            if decision.regime:
                regime = decision.regime.regime
                
                # Filter BEAR Market Longs to only TOP10 (Flight to Quality)
                if regime == MarketRegime.BEAR_TREND and decision.action == DecisionAction.CONSIDER_LONG:
                    if decision.symbol not in COIN_GROUPS["TOP10"]:
                        decision.confidence = 0.0  # Reject non-TOP10 longs in Bear Market
                        decision.reason = f"[Filtered] Non-TOP10 Long in BEAR: {decision.reason}"
                
                # Boost MEMES in BULL Market (Risk On)
                if regime == MarketRegime.BULL_TREND and decision.symbol in COIN_GROUPS["MEMES"]:
                    decision.confidence = min(0.99, decision.confidence + 0.15)
                    decision.reason = f"[MEME Boost] {decision.reason}"
                    
                # Boost AI and L1 in SIDEWAYS Market (Idiosyncratic Alpha)
                if regime == MarketRegime.SIDEWAYS and (decision.symbol in COIN_GROUPS["AI_HYPE"] or decision.symbol in COIN_GROUPS["L1"]):
                    decision.confidence = min(0.99, decision.confidence + 0.10)
                    decision.reason = f"[Alpha Boost] {decision.reason}"

        # 2. Process NEW entry candidates
        new_candidates = [
            decision
            for decision in decisions
            if decision.action in (DecisionAction.CONSIDER_LONG, DecisionAction.CONSIDER_SHORT)
            and decision.confidence >= self.min_confidence
            and decision.score.final_score > 0
            and decision.symbol not in retained_symbols  # Don't add if already retained
        ]

        new_candidates = sorted(
            new_candidates,
            key=lambda decision: (decision.confidence, decision.score.final_score),
            reverse=True,
        )

        available_slots = max(0, self.max_positions - len(retained_symbols))
        selected_new = new_candidates[:available_slots]

        if not retained_symbols and not selected_new:
            return PortfolioTarget(
                exchange=exchange,
                timeframe=timeframe,
                target_positions=[],
                cash_weight=1.0,
                gross_exposure=0.0,
                reason="No eligible candidates found.",
                created_at=self.time_provider.now(),
            )


        positions = []
        
        # Add retained positions with a fixed weight (PaperBroker skips them anyway)
        for symbol in retained_symbols:
            positions.append(
                TargetPosition(
                    symbol=symbol,
                    side="LONG",  # Simplification, broker ignores side for existing
                    target_weight=0.10,
                    confidence=1.0,
                    final_score=1.0,
                    reason="Retained open position (no CLOSE signal received).",
                    metadata={}
                )
            )

        # Calculate available exposure for new positions
        retained_exposure = len(retained_symbols) * 0.10
        available_exposure = max(0.0, self.max_gross_exposure - retained_exposure)

        # Scale base A-Grade weight according to UI risk_level (0-200)
        risk_level_clamped = max(0, min(risk_level, 200))
        if risk_level_clamped <= 100:
            a_weight_base = 0.05 + (0.15 * (risk_level_clamped / 100.0))
        else:
            a_weight_base = 0.20 + (0.30 * ((risk_level_clamped - 100.0) / 100.0))

        for decision in selected_new:
            conf = decision.confidence
            
            # --- Dinamik Güven Skoru Kasa Yönetimi (Dynamic Position Sizing) ---
            if conf >= 0.85:
                # A-Grade: Highest conviction (MACD Surge, Deep RSI, Strong RVOL)
                raw_weight = a_weight_base
                grade = f"A-Grade ({raw_weight*100:.1f}%)"
            elif conf >= 0.70:
                # B-Grade: Standard conviction (RSI & Indicators align)
                raw_weight = a_weight_base / 2.0
                grade = f"B-Grade ({raw_weight*100:.1f}%)"
            else:
                # C-Grade: Minimum conviction (Base gates passed)
                raw_weight = a_weight_base / 4.0
                grade = f"C-Grade ({raw_weight*100:.1f}%)"

            # Check if we have enough available exposure for this requested weight
            target_weight = min(raw_weight, available_exposure)
            
            # Reduce available exposure for the next candidate
            available_exposure = max(0.0, available_exposure - target_weight)

            positions.append(
                self._to_target_position(
                    decision=decision,
                    target_weight=target_weight,
                    reason=f"Weight: Dynamic {grade} based on Confidence {conf:.2f}.",
                )
            )

        # Correlation group control: scale down BTC-correlated group if overweight
        corr_total = sum(
            p.target_weight for p in positions if p.symbol in BTC_CORRELATED
        )
        if corr_total > self.max_correlated_group_weight and corr_total > 0:
            scale = self.max_correlated_group_weight / corr_total
            scaled_new = [
                self._to_target_position(
                    decision=decision,
                    target_weight=p.target_weight * scale
                    if p.symbol in BTC_CORRELATED
                    else p.target_weight,
                    reason=(
                        f"Weight scaled by {scale:.3f} due to BTC-correlated group cap."
                        if p.symbol in BTC_CORRELATED
                        else p.reason
                    ),
                )
                for p, decision in zip(positions[len(retained_symbols):], selected_new, strict=False)
            ]
            # Prepend retained positions back
            positions = positions[:len(retained_symbols)] + scaled_new

        gross_exposure = round(sum(position.target_weight for position in positions), 6)
        
        # Ensure it doesn't slightly exceed 1.0 due to float rounding
        if gross_exposure > 1.0:
            scale_down = 1.0 / gross_exposure
            for pos in positions:
                pos.target_weight *= scale_down
            gross_exposure = 1.0
            
        cash_weight = round(max(0.0, 1.0 - gross_exposure), 10)

        return PortfolioTarget(
            exchange=exchange,
            timeframe=timeframe,
            target_positions=positions,
            cash_weight=cash_weight,
            gross_exposure=gross_exposure,
            reason=(
                f"Selected {len(positions)} positions from {len(decisions)} decisions. "
                f"Max gross exposure={self.max_gross_exposure:.2f}."
            ),
            created_at=self.time_provider.now(),
        )

    @staticmethod
    def _to_target_position(
        decision: TradingDecision,
        target_weight: float,
        reason: str,
    ) -> TargetPosition:
        side = "LONG" if decision.action == DecisionAction.CONSIDER_LONG else "SHORT"
        return TargetPosition(
            symbol=decision.symbol,
            side=side,
            target_weight=round(max(0.0, min(target_weight, 1.0)), 6),
            confidence=decision.confidence,
            final_score=decision.score.final_score,
            reason=reason,
            metadata=decision.metadata or {},
        )
