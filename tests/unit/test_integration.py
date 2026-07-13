from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from crypto_mas.domain.models.paper_account import PaperAccount
from crypto_mas.domain.models.position import Position
from crypto_mas.infrastructure.db.base import Base
from crypto_mas.infrastructure.time.time_provider import FixedTimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange, OHLCVCandle, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService


@pytest.fixture
def e2e_db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.mark.asyncio
async def test_end_to_end_trading_cycle_opens_position(e2e_db_session: Session):
    # Setup Paper Account
    account = PaperAccount(
        name="default-paper",
        exchange="BINANCE",
        base_currency="USDT",
        initial_balance=Decimal("10000.0"),
        cash_balance=Decimal("10000.0"),
        equity=Decimal("10000.0"),
    )
    e2e_db_session.add(account)
    e2e_db_session.commit()

    time_provider = FixedTimeProvider(fixed_time=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC))

    # Mock Market Data Provider
    mock_provider = MagicMock()
    mock_provider.exchange = Exchange.BINANCE

    # We need 60 candles to bypass warmup periods of RSI/MACD/EMA
    # We will engineer the last few candles to trigger an RSI oversold condition
    # RSI Oversold strategy: RSI < 30 and starts rising
    candles = []
    # Start far back so they end near the current time (2026-01-01 12:00:00)
    base_time = datetime(2025, 12, 31, 0, 0, 0, tzinfo=UTC)

    # 90 neutral candles
    for i in range(90):
        candles.append(
            OHLCVCandle(
                exchange=Exchange.BINANCE,
                symbol="BTCUSDT",
                timeframe=Timeframe.FIFTEEN_MINUTES,
                open_time=base_time,
                close_time=base_time + timedelta(minutes=15) - timedelta(milliseconds=1),
                open=Decimal("50000"),
                high=Decimal("50500"),
                low=Decimal("49500"),
                close=Decimal("50000"),
                volume=Decimal("100"),
                quote_volume=Decimal("5000000"),
                trade_count=1000,
                source="MOCK"
            )
        )
        base_time += timedelta(minutes=15)
        
    # 4 dumping candles to push RSI down
    dump_prices = [40000, 30000, 20000, 10000]
    for price in dump_prices:
        candles.append(
             OHLCVCandle(
                exchange=Exchange.BINANCE,
                symbol="BTCUSDT",
                timeframe=Timeframe.FIFTEEN_MINUTES,
                open_time=base_time,
                close_time=base_time + timedelta(minutes=15) - timedelta(milliseconds=1),
                open=Decimal(price+1000),
                high=Decimal(price+1000),
                low=Decimal(price),
                close=Decimal(price),
                volume=Decimal("500"),
                quote_volume=Decimal("20000000"),
                trade_count=5000,
                source="MOCK"
            )
        )
        base_time += timedelta(minutes=15)
        
    # 1 recovery candle to trigger RSI rising from oversold
    candles.append(
        OHLCVCandle(
            exchange=Exchange.BINANCE,
            symbol="BTCUSDT",
            timeframe=Timeframe.FIFTEEN_MINUTES,
            open_time=base_time,
            close_time=base_time + timedelta(minutes=15) - timedelta(milliseconds=1),
            open=Decimal("10000"),
            high=Decimal("15000"),
            low=Decimal("10000"),
            close=Decimal("12000"), # Price rises
            volume=Decimal("1000"),
            quote_volume=Decimal("41500000"),
            trade_count=10000,
            source="MOCK"
        )
    )

    async def mock_fetch_ohlcv(symbol, timeframe, start_time, end_time, limit=None):
        if timeframe == Timeframe.FOUR_HOURS:
            # Return dummy 4H candles to pass integrity and HTF checks
            htf_candles = []
            htf_base_time = datetime(2026, 1, 1, tzinfo=UTC) - timedelta(days=10)
            for i in range(10):
                htf_candles.append(
                    OHLCVCandle(
                        exchange=Exchange.BINANCE, symbol="BTCUSDT", timeframe=Timeframe.FOUR_HOURS,
                        open_time=htf_base_time, close_time=htf_base_time + timedelta(hours=4) - timedelta(milliseconds=1),
                        open=Decimal("50000"), high=Decimal("55000"), low=Decimal("45000"), close=Decimal("50000"),
                        volume=Decimal("1000"), quote_volume=Decimal("50000000"), trade_count=10000, source="MOCK"
                    )
                )
                htf_base_time += timedelta(hours=4)
            return htf_candles
        else:
            return candles

    mock_provider.fetch_ohlcv = AsyncMock(side_effect=mock_fetch_ohlcv)

    # Initialize Service
    service = TradingCycleService(
        db=e2e_db_session,
        market_provider=mock_provider,
        time_provider=time_provider,
        strategy_mode="scalping"
    )

    # Act
    cycle = await service.run_cycle(
        account_name="default-paper",
        symbols=["BTCUSDT"],
        timeframe=Timeframe.FIFTEEN_MINUTES,
        strategy_name="rsi_oversold",
        trigger="E2E_TEST"
    )

    # Assert
    assert cycle.status == "COMPLETED"
    
    # Check if position was opened!
    open_positions = e2e_db_session.query(Position).filter_by(status="OPEN").all()
    assert len(open_positions) == 1
    
    position = open_positions[0]
    assert position.symbol == "BTCUSDT"
    assert position.side == "LONG"
    
    # Check if cash was deducted
    e2e_db_session.refresh(account)
    assert account.cash_balance < Decimal("10000.0")
