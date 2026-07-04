import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.backtest_result_repository import BacktestResultRepository
from crypto_mas.infrastructure.db.session import SessionLocal, get_db_session
from crypto_mas.services.backtesting.engine import BacktestEngineService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

router = APIRouter(prefix="/backtest", tags=["Backtesting"])

class RunBacktestRequest(BaseModel):
    exchange: Exchange
    symbols: list[str] = Field(..., min_length=1)
    timeframe: Timeframe
    strategy_name: str = "multi_agent"
    start_time: datetime
    end_time: datetime
    initial_balance: float = 10000.0

class RunBacktestResponse(BaseModel):
    job_id: str
    message: str

class BacktestStatusResponse(BaseModel):
    job_id: str
    status: str
    exchange: str
    timeframe: str
    strategy_name: str
    symbols: list[str]
    start_time: datetime
    end_time: datetime
    initial_balance: float
    final_equity: float | None
    total_trades: int | None
    win_rate: float | None
    max_drawdown: float | None
    error_message: str | None


async def run_backtest_task(
    job_id: str,
    exchange: Exchange,
    symbols: list[str],
    timeframe: Timeframe,
    strategy_name: str,
    start_time: datetime,
    end_time: datetime,
    initial_balance: float,
) -> None:
    db = SessionLocal()
    try:
        service = BacktestEngineService(db)
        await service.run_backtest(
            job_id=job_id,
            exchange=exchange,
            symbols=symbols,
            timeframe=timeframe,
            strategy_name=strategy_name,
            start_time=start_time,
            end_time=end_time,
            initial_balance=initial_balance,
        )
    except Exception as e:
        pass  # Errors are logged inside the service
    finally:
        db.close()


@router.post("/run", response_model=RunBacktestResponse)
async def start_backtest(
    request: RunBacktestRequest,
    background_tasks: BackgroundTasks,
) -> RunBacktestResponse:
    if request.start_time >= request.end_time:
        raise HTTPException(status_code=400, detail="start_time must be before end_time")
        
    job_id = str(uuid.uuid4())
    
    background_tasks.add_task(
        run_backtest_task,
        job_id=job_id,
        exchange=request.exchange,
        symbols=request.symbols,
        timeframe=request.timeframe,
        strategy_name=request.strategy_name,
        start_time=request.start_time,
        end_time=request.end_time,
        initial_balance=request.initial_balance,
    )
    
    return RunBacktestResponse(
        job_id=job_id,
        message="Backtest job started in the background. Check status using /status endpoint.",
    )


@router.get("/{job_id}/status", response_model=BacktestStatusResponse)
def get_backtest_status(
    job_id: str,
    db: Annotated[Session, Depends(get_db_session)],
) -> BacktestStatusResponse:
    repo = BacktestResultRepository(db)
    result = repo.get_by_job_id(job_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Backtest job not found")
        
    return BacktestStatusResponse(
        job_id=result.job_id,
        status=result.status,
        exchange=result.exchange,
        timeframe=result.timeframe,
        strategy_name=result.strategy_name,
        symbols=result.symbols,
        start_time=result.start_time,
        end_time=result.end_time,
        initial_balance=result.initial_balance,
        final_equity=result.final_equity,
        total_trades=result.total_trades,
        win_rate=result.win_rate,
        max_drawdown=result.max_drawdown,
        error_message=result.error_message,
    )
