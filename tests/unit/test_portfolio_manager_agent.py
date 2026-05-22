from datetime import UTC, datetime

from pytest import approx

from crypto_mas.agents.portfolio_manager_agent.portfolio_manager import PortfolioManagerAgent
from crypto_mas.agents.regime_agent.schemas import MarketRegime, RegimeSnapshot
from crypto_mas.agents.scoring_agent.schemas import AssetScore
from crypto_mas.agents.signal_agent.schemas import SignalDirection, SignalType, TradingSignal
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.decision_orchestrator.schemas import DecisionAction, TradingDecision
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


def _make_decision(
    symbol: str,
    action: DecisionAction,
    confidence: float,
    final_score: float,
) -> TradingDecision:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)

    signal = TradingSignal(
        exchange=Exchange.MOCK,
        symbol=symbol,
        timeframe=Timeframe.FOUR_HOURS,
        signal_type=SignalType.TREND_FOLLOWING,
        direction=SignalDirection.LONG,
        strength=confidence,
        reason="test",
        timestamp=timestamp,
    )

    score = AssetScore(
        exchange=Exchange.MOCK,
        symbol=symbol,
        timeframe=Timeframe.FOUR_HOURS,
        direction=SignalDirection.LONG,
        final_score=final_score,
        trend_score=final_score,
        momentum_score=final_score,
        volatility_penalty=0.0,
        reason="test",
        timestamp=timestamp,
    )

    regime = RegimeSnapshot(
        exchange=Exchange.MOCK,
        symbol=symbol,
        timeframe=Timeframe.FOUR_HOURS,
        regime=MarketRegime.BULL_TREND,
        confidence=confidence,
        risk_multiplier=1.0,
        reason="test",
        timestamp=timestamp,
    )

    return TradingDecision(
        exchange=Exchange.MOCK,
        symbol=symbol,
        timeframe=Timeframe.FOUR_HOURS,
        action=action,
        confidence=confidence,
        signal=signal,
        score=score,
        regime=regime,
        reason="test",
        created_at=timestamp,
    )


def test_portfolio_manager_builds_target_portfolio() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=UTC)

    decisions = [
        _make_decision("BTCUSDT", DecisionAction.CONSIDER_LONG, 0.50, 0.50),
        _make_decision("ETHUSDT", DecisionAction.CONSIDER_LONG, 0.40, 0.40),
        _make_decision("SOLUSDT", DecisionAction.HOLD, 0.80, 0.80),
    ]

    target = PortfolioManagerAgent(
        max_positions=2,
        max_gross_exposure=0.90,
        min_confidence=0.35,
        time_provider=FixedTimeProvider(fixed_time),
    ).build_target_portfolio(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        decisions=decisions,
    )

    assert len(target.target_positions) == 2
    assert target.gross_exposure == approx(0.90)
    assert target.cash_weight == approx(0.10)
    assert target.created_at == fixed_time
    assert {position.symbol for position in target.target_positions} == {
        "BTCUSDT",
        "ETHUSDT",
    }


def test_portfolio_manager_returns_cash_when_no_candidates() -> None:
    fixed_time = datetime(2026, 1, 1, tzinfo=UTC)

    decisions = [
        _make_decision("BTCUSDT", DecisionAction.HOLD, 0.50, 0.50),
        _make_decision("ETHUSDT", DecisionAction.AVOID, 0.50, 0.50),
    ]

    target = PortfolioManagerAgent(
        max_positions=2,
        max_gross_exposure=0.90,
        min_confidence=0.35,
        time_provider=FixedTimeProvider(fixed_time),
    ).build_target_portfolio(
        exchange=Exchange.MOCK,
        timeframe=Timeframe.FOUR_HOURS,
        decisions=decisions,
    )

    assert target.target_positions == []
    assert target.gross_exposure == 0.0
    assert target.cash_weight == 1.0