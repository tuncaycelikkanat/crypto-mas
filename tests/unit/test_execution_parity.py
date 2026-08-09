from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.models.paper_account import PaperAccount
from crypto_mas.domain.models.position import Position
from crypto_mas.domain.models.trade import Trade
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService


def setup_fresh_db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory(), engine

async def run_simulation(trigger_name: str, account_name: str) -> dict:
    session, engine = setup_fresh_db()
    
    # Create account
    acc = PaperAccount(name=account_name, exchange=Exchange.MOCK.value, base_currency="USDT", initial_balance=10000.0, cash_balance=10000.0, equity=10000.0)
    session.add(acc)
    session.commit()
    
    now_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_provider = FixedTimeProvider(fixed_time=now_time)
    
    provider = MagicMock()
    provider.exchange = Exchange.MOCK
    # Mock order book so paper broker can execute
    provider.fetch_order_book = AsyncMock(return_value={"bids": [[2000, 1]], "asks": [[2005, 1]]})
    
    service = TradingCycleService(db=session, market_provider=provider, time_provider=time_provider)
    
    # Mock components that depend on network/external
    service.feature_service = MagicMock()
    service.feature_service.calculate_and_store = MagicMock()
    service.fetcher_service = MagicMock()
    service.fetcher_service.provider = provider
    service.fetcher_service.backfill_universe = AsyncMock()
    
    fresh_snapshot = FeatureSnapshot(
        exchange=Exchange.MOCK.value,
        symbol="ETHUSDT",
        timeframe=Timeframe.ONE_HOUR.value,
        timestamp=now_time,
        available_at=now_time,
        features_json={"close": 2000, "ema_20": 1900, "ema_50": 1800, "roc_14": 5.0, "atr_14": 50, "bb_upper": 2100, "bb_middle": 2000, "bb_lower": 1900}
    )
    
    service.feature_snapshot_repository = MagicMock()
    service.feature_snapshot_repository.list_by_symbol.return_value = [fresh_snapshot]
    
    # Fake HTF manager to allow everything
    service.htf_manager = MagicMock()  # type: ignore
    service.htf_manager.is_long_allowed.return_value = True  # type: ignore
    service.htf_manager.is_short_allowed.return_value = True  # type: ignore

    # 1. Step: LONG decision
    strategy_mock = MagicMock()
    from types import SimpleNamespace
    decision = SimpleNamespace(
        symbol="ETHUSDT",
        action=DecisionAction.CONSIDER_LONG,
        confidence=0.9,
        reason="Test buy",
        score=SimpleNamespace(final_score=0.9, trend_score=0.5, momentum_score=0.4, volatility_penalty=0.0),
        regime=None,
        metadata={}
    )
    strategy_mock.decide.return_value = decision
    
    # Run cycle using monkeypatch for StrategyFactory
    import crypto_mas.services.trading_cycle_service.cycle_orchestrator as orchestrator
    original_create = orchestrator.StrategyFactory.create
    orchestrator.StrategyFactory.create = MagicMock(return_value=strategy_mock)  # type: ignore

    try:
        await service.run_cycle(
            account_name=account_name,
            symbols=["ETHUSDT"],
            timeframe=Timeframe.ONE_HOUR,
            strategy_name="test_strat",
            trigger=trigger_name,
            risk_level=100,
            use_btc_shield=False,
            use_htf_shield=False,
            use_regime_shield=False
        )
        
        # 2. Step: Price drops and we decide to HOLD (so it hits Stop Loss or we just close)
        # Actually, let's explicitly issue AVOID to close it or let's issue CONSIDER_SHORT to flip
        time_provider.fixed_time = datetime(2026, 1, 1, 13, 0, 0, tzinfo=UTC)
        fresh_snapshot.timestamp = time_provider.fixed_time
        # Drop price significantly to trigger PNL calculation diffs
        provider.fetch_order_book = AsyncMock(return_value={"bids": [[1900, 1]], "asks": [[1905, 1]]})
        
        decision.action = DecisionAction.CONSIDER_SHORT
        strategy_mock.decide.return_value = decision

        await service.run_cycle(
            account_name=account_name,
            symbols=["ETHUSDT"],
            timeframe=Timeframe.ONE_HOUR,
            strategy_name="test_strat",
            trigger=trigger_name,
            risk_level=100,
            use_btc_shield=False,
            use_htf_shield=False,
            use_regime_shield=False
        )
    finally:
        orchestrator.StrategyFactory.create = original_create  # type: ignore
    
    # Collect results
    session.commit()
    positions = session.query(Position).all()
    trades = session.query(Trade).all()
    final_account = session.query(PaperAccount).filter_by(name=account_name).first()
    
    result = {
        "balance": float(final_account.cash_balance),
        "positions_count": len(positions),
        "trades_count": len(trades),
        "trades_pnl": [float(t.realized_pnl) for t in trades if t.realized_pnl is not None],
        "open_position_side": [p.side for p in positions if p.status == "OPEN"]
    }
    
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    
    return result


@pytest.mark.asyncio
async def test_execution_parity_backtest_vs_paper():
    """
    Ensures that the Paper Broker and Portfolio engine behave exactly identically 
    (same trades, same PnL, same open positions) regardless of whether the trigger 
    is a BACKTEST or a LIVE/PAPER run.
    """
    # Run the exact same market sequence under PAPER mode
    paper_result = await run_simulation(trigger_name="PAPER-123", account_name="paper_acc")
    
    # Run the exact same market sequence under BACKTEST mode
    backtest_result = await run_simulation(trigger_name="BACKTEST-123", account_name="backtest_acc")
    
    # Assert exact parity
    assert paper_result["balance"] == backtest_result["balance"], "Balance mismatch between Backtest and Paper"
    assert paper_result["positions_count"] == backtest_result["positions_count"], "Position counts differ"
    assert paper_result["trades_count"] == backtest_result["trades_count"], "Trade counts differ"
    assert paper_result["trades_pnl"] == backtest_result["trades_pnl"], "PnL calculations differ"
    assert paper_result["open_position_side"] == backtest_result["open_position_side"], "Open position state differs"

