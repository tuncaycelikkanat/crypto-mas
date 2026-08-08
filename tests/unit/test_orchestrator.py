import pytest
from unittest.mock import AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from crypto_mas.infrastructure.db.base import Base
from crypto_mas.engine.llm_committee.orchestrator import LLMCommitteeOrchestrator
from crypto_mas.engine.llm_committee.provider import AgentVote
from crypto_mas.engine.strategy.schemas import TradingDecision, DecisionAction
from crypto_mas.engine.scoring import AssetScore
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.mark.asyncio
async def test_llm_orchestrator_shadow_mode(test_db):
    mock_provider = AsyncMock()
    mock_provider.complete_json.return_value = (
        AgentVote(vote="LONG", confidence=85, reasoning="Looks good"),
        {"latency_ms": 100, "cost_usd": 0.001, "model_version": "test", "prompt": "test prompt"}
    )
    
    mock_cost = AsyncMock()
    mock_cost.check_daily_limit.return_value = True
    
    orchestrator = LLMCommitteeOrchestrator(provider=mock_provider, cost_tracker=mock_cost)
    
    mock_signal = AsyncMock()
    
    from datetime import datetime
    from crypto_mas.engine.signal import TradingSignal, SignalType, SignalDirection
    original_decision = TradingDecision(
        exchange=Exchange.BINANCE,
        timeframe=Timeframe.FOUR_HOURS,
        symbol="BTCUSDT",
        action=DecisionAction.CONSIDER_LONG,
        confidence=0.8,
        reason="Test",
        score=AssetScore(
            exchange=Exchange.BINANCE,
            timeframe=Timeframe.FOUR_HOURS,
            symbol="BTCUSDT",
            direction="LONG",
            final_score=20.0,
            trend_score=10.0,
            momentum_score=10.0,
            volatility_penalty=0.0,
            components={},
            reason="test",
            timestamp=datetime.now()
        ),
        signal=TradingSignal(
            exchange=Exchange.BINANCE,
            timeframe=Timeframe.FOUR_HOURS,
            symbol="BTCUSDT",
            signal_type=SignalType.TREND_FOLLOWING,
            direction=SignalDirection.LONG,
            strength=0.8,
            reason="test",
            timestamp=datetime.now()
        )
    )
    
    result = await orchestrator.evaluate_decision(
        symbol="BTCUSDT",
        context={"market_regime": "BULL_TREND"},
        original_decision=original_decision,
        db=test_db
    )
    
    # Shadow Mode should return the original unmodified decision
    assert result == original_decision
    
    # Check if DB records were created
    from crypto_mas.domain.models.committee_decision import CommitteeDecision
    from crypto_mas.domain.models.shadow_mode_trade import ShadowModeTrade
    from crypto_mas.domain.models.llm_audit_log import LLMAuditLog
    
    decisions = test_db.query(CommitteeDecision).all()
    assert len(decisions) == 1
    assert decisions[0].final_decision == "LONG"
    
    shadow_trades = test_db.query(ShadowModeTrade).all()
    assert len(shadow_trades) == 1
    assert shadow_trades[0].rule_based_decision == "CONSIDER_LONG"
    
    logs = test_db.query(LLMAuditLog).all()
    assert len(logs) == 3  # One for each agent
