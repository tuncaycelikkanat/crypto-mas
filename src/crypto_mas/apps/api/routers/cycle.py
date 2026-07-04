from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from crypto_mas.infrastructure.db.session import get_db_session
from crypto_mas.services.market_data_service.provider_factory import get_market_data_provider
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe
from crypto_mas.services.trading_cycle_service.cycle_orchestrator import TradingCycleService

router = APIRouter(prefix="/cycle", tags=["Trading Cycle"])

class RunCycleRequest(BaseModel):
    account_name: str
    exchange: Exchange
    symbols: list[str]
    timeframe: Timeframe
    strategy_name: str = "multi_agent"
    trigger: str = "MANUAL"

class RunCycleResponse(BaseModel):
    cycle_id: int
    account_name: str
    status: str
    strategy_name: str
    symbols_processed: int
    decisions_made: int
    trades_executed: int
    cycle_pnl: float

@router.post("/run", response_model=RunCycleResponse)
async def run_trading_cycle(
    request: RunCycleRequest,
    db: Annotated[Session, Depends(get_db_session)],
) -> RunCycleResponse:
    try:
        provider = get_market_data_provider(request.exchange)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    service = TradingCycleService(db=db, market_provider=provider)
    
    try:
        cycle = await service.run_cycle(
            account_name=request.account_name,
            symbols=request.symbols,
            timeframe=request.timeframe,
            strategy_name=request.strategy_name,
            trigger=request.trigger,
        )
        
        return RunCycleResponse(
            cycle_id=cycle.id,
            account_name=cycle.account_name,
            status=cycle.status,
            strategy_name=request.strategy_name,
            symbols_processed=cycle.symbols_processed,
            decisions_made=cycle.decisions_made,
            trades_executed=cycle.trades_executed,
            cycle_pnl=float(cycle.cycle_pnl),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cycle execution failed: {str(e)}")
