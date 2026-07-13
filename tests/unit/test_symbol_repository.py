from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from crypto_mas.domain.models.symbol import Symbol
from crypto_mas.domain.repositories.symbol_repository import SymbolRepository
from crypto_mas.services.market_data_service.schemas import Exchange, MarketSymbol


def test_bulk_upsert_empty():
    db_mock = MagicMock()
    repo = SymbolRepository(db_mock)
    
    result = repo.bulk_upsert([])
    assert result == 0
    db_mock.execute.assert_not_called()

@patch("crypto_mas.domain.repositories.symbol_repository.insert")
def test_bulk_upsert(mock_insert):
    db_mock = MagicMock()
    repo = SymbolRepository(db_mock)
    
    dt = datetime.now(UTC)
    symbol_mock = MarketSymbol(
        exchange=Exchange.BINANCE,
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        status="TRADING",
        is_active=True,
        is_stablecoin=False,
        is_leveraged_token=False,
        listing_date=dt,
        delisting_date=None
    )
    
    insert_stmt_mock = MagicMock()
    mock_insert.return_value.values.return_value = insert_stmt_mock
    insert_stmt_mock.on_conflict_do_update.return_value = insert_stmt_mock
    
    result = repo.bulk_upsert([symbol_mock])
    
    assert result == 1
    mock_insert.assert_called_once_with(Symbol)
    insert_stmt_mock.on_conflict_do_update.assert_called_once()
    db_mock.execute.assert_called_once_with(insert_stmt_mock)
    db_mock.commit.assert_called_once()

def test_list_active_symbols():
    db_mock = MagicMock()
    repo = SymbolRepository(db_mock)
    
    s = Symbol(symbol="BTCUSDT", is_active=True, quote_asset="USDT", exchange="BINANCE")
    db_mock.scalars.return_value.all.return_value = [s]
    
    result = repo.list_active_symbols(exchange="BINANCE")
    
    assert len(result) == 1
    assert result[0].symbol == "BTCUSDT"
    db_mock.scalars.assert_called_once()

def test_list_active_symbols_with_filters():
    db_mock = MagicMock()
    repo = SymbolRepository(db_mock)
    
    s = Symbol(symbol="BTCUSDT", is_active=True, quote_asset="USDT", exchange="BINANCE")
    db_mock.scalars.return_value.all.return_value = [s]
    
    result = repo.list_active_symbols(exchange="BINANCE", quote_asset="USDT", limit=10)
    
    assert len(result) == 1
    assert result[0].symbol == "BTCUSDT"
    db_mock.scalars.assert_called_once()
