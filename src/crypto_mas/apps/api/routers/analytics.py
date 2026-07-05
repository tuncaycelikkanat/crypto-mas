from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crypto_mas.infrastructure.db.session import SessionLocal
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.domain.repositories.trade_repository import TradeRepository
from crypto_mas.domain.repositories.trading_cycle_repository import TradingCycleRepository
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.domain.repositories.execution_log_repository import ExecutionLogRepository
from crypto_mas.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)) -> dict[str, Any]:
    account_repo = PaperAccountRepository(db)
    trade_repo = TradeRepository(db)
    position_repo = PositionRepository(db)
    
    account_name = "default-paper"
    account = account_repo.get_by_name(account_name)
    
    if not account:
        return {
            "initial_balance": 10000.0,
            "current_balance": 10000.0,
            "equity": 10000.0,
            "total_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "open_positions": 0
        }
        
    trades = trade_repo.list_by_account(account_name, limit=10000)
    open_positions = position_repo.list_open_positions(account_name)
    
    # Calculate win rate and total PNL from sell trades (closed positions)
    sell_trades = [t for t in trades if t.side == "SELL"]
    total_closed = len(sell_trades)
    winning_trades = sum(1 for t in sell_trades if float(t.realized_pnl) > 0)
    
    win_rate = (winning_trades / total_closed * 100) if total_closed > 0 else 0.0
    total_pnl = sum(float(t.realized_pnl) for t in sell_trades)
    
    return {
        "initial_balance": float(account.initial_balance),
        "current_balance": float(account.cash_balance),
        "equity": float(account.equity),
        "total_trades": total_closed,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2),
        "open_positions": len(open_positions)
    }


@router.get("/equity-curve")
def get_equity_curve(db: Session = Depends(get_db)) -> dict[str, Any]:
    cycle_repo = TradingCycleRepository(db)
    account_name = "default-paper"
    
    cycles = cycle_repo.list_recent(account_name, limit=1000)
    # Return chronologically ascending order for charts
    cycles = sorted(cycles, key=lambda c: c.started_at)
    
    data = []
    for c in cycles:
        if c.ending_equity:
            data.append({
                "time": c.started_at.isoformat(),
                "value": float(c.ending_equity)
            })
            
    # If no cycles, at least return initial state
    if not data:
        account_repo = PaperAccountRepository(db)
        account = account_repo.get_by_name(account_name)
        if account:
            data.append({
                "time": account.created_at.isoformat(),
                "value": float(account.initial_balance)
            })
            
    return {"data": data}


@router.get("/trade-history")
def get_trade_history(db: Session = Depends(get_db)) -> dict[str, Any]:
    trade_repo = TradeRepository(db)
    account_name = "default-paper"
    
    trades = trade_repo.list_by_account(account_name, limit=50)
    
    history = []
    for t in trades:
        history.append({
            "id": t.id,
            "symbol": t.symbol,
            "side": t.side,
            "quantity": float(t.quantity),
            "price": float(t.price),
            "notional": float(t.notional),
            "realized_pnl": float(t.realized_pnl) if t.side == "SELL" else None,
            "reason": t.reason,
            "executed_at": t.executed_at.isoformat()
        })
        
    return {"history": history}


@router.get("/coins")
def get_active_coins() -> dict[str, Any]:
    scheduler = SchedulerService()
    status = scheduler.get_status()
    
    all_symbols = set()
    for bot in status.get("bots", []):
        for sym in bot.get("symbols", []):
            all_symbols.add(sym)
            
    return {
        "symbols": sorted(list(all_symbols)),
        "bots": status.get("bots", [])
    }


@router.get("/coin/{symbol}")
def get_coin_details(symbol: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    scheduler = SchedulerService()
    status = scheduler.get_status()
    
    # Try to find the bot that runs this symbol to get its exchange/mode
    exchange_str = "BINANCE"
    mode = "swing"
    
    for bot in status.get("bots", []):
        if symbol in bot.get("symbols", []):
            exchange_str = bot.get("exchange", "BINANCE")
            mode = bot.get("mode", "swing")
            break
            
    # Map timeframe from mode
    timeframe = "4h"
    if mode == "scalping": timeframe = "15m"
    elif mode == "hodl": timeframe = "1d"
        
    # Repositories
    candle_repo = CandleRepository(db)
    feature_repo = FeatureSnapshotRepository(db)
    log_repo = ExecutionLogRepository(db)
    
    # 1. Fetch Candles (Last 100)
    candles = candle_repo.list_by_symbol(
        exchange=exchange_str,
        symbol=symbol,
        timeframe=timeframe,
        limit=100
    )
    
    candle_data = []
    for c in candles:
        candle_data.append({
            "time": c.open_time.isoformat(),
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume),
        })
        
    # 2. Fetch Latest Features
    latest_feature = feature_repo.get_latest(
        exchange=exchange_str,
        symbol=symbol,
        timeframe=timeframe,
    )
    
    features = {}
    if latest_feature and latest_feature.features_json:
        features = latest_feature.features_json
        
    # 3. Fetch Recent Logs related to this symbol
    all_logs = log_repo.list_recent("default-paper", limit=200)
    
    symbol_logs = []
    for log in reversed(all_logs): # chronological
        if symbol in log.message or (log.payload_json and symbol in str(log.payload_json)):
            symbol_logs.append({
                "id": log.id,
                "level": log.level,
                "stage": log.stage,
                "message": log.message,
                "created_at": log.created_at.isoformat(),
                "payload": log.payload_json
            })
            
    return {
        "symbol": symbol,
        "exchange": exchange_str,
        "timeframe": timeframe,
        "candles": candle_data,
        "features": features,
        "logs": symbol_logs[-20:]
    }
