from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.models.paper_account import PaperAccount
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService




@pytest.fixture
def test_account(db_session):
    account = PaperAccount(
        name="btc_crash_account",
        exchange=Exchange.MOCK.value,
        base_currency="USDT",
        initial_balance=10000.0,
        cash_balance=10000.0,
        equity=10000.0,
    )
    db_session.add(account)
    db_session.commit()
    return account


@pytest.mark.asyncio
async def test_btc_crash_shield_rejects_altcoin_longs(db_session, test_account):
    now_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_provider = FixedTimeProvider(fixed_time=now_time)
    
    provider = MagicMock()
    provider.exchange = Exchange.MOCK
    provider.fetch_ohlcv = AsyncMock(return_value=[])
    
    service = TradingCycleService(
        db=db_session,
        market_provider=provider,
        time_provider=time_provider,
    )
    
    service.feature_service = MagicMock()
    
    # Simulate a fresh snapshot for ETHUSDT
    fresh_time = now_time
    fresh_snapshot = FeatureSnapshot(
        exchange=Exchange.MOCK.value,
        symbol="ETHUSDT",
        timeframe=Timeframe.ONE_HOUR.value,
        timestamp=fresh_time,
        available_at=fresh_time,
        features_json={"close": 2000, "ema_20": 1900, "ema_50": 1800, "roc_14": 5.0, "atr_14": 50, "bb_upper": 2100, "bb_middle": 2000, "bb_lower": 1900}
    )
    
    service.feature_snapshot_repository = MagicMock()
    service.feature_snapshot_repository.list_by_symbol.return_value = [fresh_snapshot, fresh_snapshot, fresh_snapshot]
    service.strategy_orchestrator.feature_snapshot_repository = service.feature_snapshot_repository
    
    # Mock evaluate to return a LONG decision for ETHUSDT
    strategy_mock = MagicMock()
    from types import SimpleNamespace
    decision = SimpleNamespace(
        action=DecisionAction.CONSIDER_LONG,
        confidence=0.9,
        reason="Strong buy",
        score=SimpleNamespace(
            final_score=0.9,
            trend_score=0.5,
            momentum_score=0.4,
            volatility_penalty=0.0
        ),
        regime=None,
        metadata={}
    )
    strategy_mock.decide.return_value = decision
    
    service.multi_agent = MagicMock()
    service.multi_agent.evaluate = AsyncMock(return_value=decision) # Not used directly in _run_strategies_and_score
    
    cycle_mock = MagicMock()
    
    def log_mock(tag, msg, level="INFO", **kwargs):
        pass
        
    candidates, _ = await service.strategy_orchestrator.run_strategies_and_score(
        symbols=["ETHUSDT"],
        timeframe=Timeframe.ONE_HOUR,
        now=now_time,
        strategy=strategy_mock,
        strategy_name="test_strat",
        risk_level=1,
        cycle=cycle_mock,
        account_name=test_account.name,
        htf={"ETHUSDT": [fresh_snapshot]},
        btc_is_crashing=True, # THIS IS THE SHIELD TRIGGER
        _log=log_mock,
        use_htf_shield=False,
        use_regime_shield=False
    )
    
    # Since BTC is crashing, the CONSIDER_LONG should be rejected
    assert len(candidates) == 0


@pytest.mark.asyncio
async def test_btc_crash_shield_allows_altcoin_shorts(db_session, test_account):
    now_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    time_provider = FixedTimeProvider(fixed_time=now_time)
    
    provider = MagicMock()
    provider.exchange = Exchange.MOCK
    provider.fetch_ohlcv = AsyncMock(return_value=[])
    
    service = TradingCycleService(
        db=db_session,
        market_provider=provider,
        time_provider=time_provider,
    )
    
    service.feature_service = MagicMock()
    
    # Simulate a fresh snapshot for ETHUSDT
    fresh_time = now_time
    fresh_snapshot = FeatureSnapshot(
        exchange=Exchange.MOCK.value,
        symbol="ETHUSDT",
        timeframe=Timeframe.ONE_HOUR.value,
        timestamp=fresh_time,
        available_at=fresh_time,
        features_json={"close": 2000, "ema_20": 2100, "ema_50": 2200, "roc_14": -5.0, "atr_14": 50, "bb_upper": 2100, "bb_middle": 2000, "bb_lower": 1900}
    )
    
    service.feature_snapshot_repository = MagicMock()
    service.feature_snapshot_repository.list_by_symbol.return_value = [fresh_snapshot, fresh_snapshot, fresh_snapshot]
    service.strategy_orchestrator.feature_snapshot_repository = service.feature_snapshot_repository
    
    # Mock evaluate to return a SHORT decision for ETHUSDT
    strategy_mock = MagicMock()
    from types import SimpleNamespace
    decision = SimpleNamespace(
        action=DecisionAction.CONSIDER_SHORT,
        confidence=0.9,
        reason="Strong sell",
        score=SimpleNamespace(
            final_score=0.9,
            trend_score=0.5,
            momentum_score=0.4,
            volatility_penalty=0.0
        ),
        regime=None,
        metadata={}
    )
    strategy_mock.decide.return_value = decision
    
    cycle_mock = MagicMock()
    
    def log_mock(tag, msg, level="INFO", **kwargs):
        pass
        
    candidates, _ = await service.strategy_orchestrator.run_strategies_and_score(
        symbols=["ETHUSDT"],
        timeframe=Timeframe.ONE_HOUR,
        now=now_time,
        strategy=strategy_mock,
        strategy_name="test_strat",
        risk_level=1,
        cycle=cycle_mock,
        account_name=test_account.name,
        htf={"ETHUSDT": [fresh_snapshot]},
        btc_is_crashing=True, # SHIELD IS TRIGGERED
        _log=log_mock,
        use_htf_shield=False,
        use_regime_shield=False
    )
    
    # Shorting during a BTC crash is allowed!
    assert len(candidates) == 1
    assert candidates[0].action.value == "CONSIDER_SHORT"
    assert "REJECTED" not in candidates[0].reason
