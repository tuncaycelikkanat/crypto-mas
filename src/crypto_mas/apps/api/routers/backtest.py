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

router = APIRouter(prefix="/api/v1/backtest", tags=["Backtesting"])

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
    except Exception:
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

@router.get("", response_model=list[BacktestStatusResponse])
def get_all_backtests(
    db: Annotated[Session, Depends(get_db_session)],
    limit: int = 50
) -> list[BacktestStatusResponse]:
    repo = BacktestResultRepository(db)
    results = repo.list_all(limit=limit)
    
    return [
        BacktestStatusResponse(
            job_id=r.job_id,
            status=r.status,
            exchange=r.exchange,
            timeframe=r.timeframe,
            strategy_name=r.strategy_name,
            symbols=r.symbols,
            start_time=r.start_time,
            end_time=r.end_time,
            initial_balance=r.initial_balance,
            final_equity=r.final_equity,
            total_trades=r.total_trades,
            win_rate=r.win_rate,
            max_drawdown=r.max_drawdown,
            error_message=r.error_message,
        )
        for r in results
    ]

@router.post("/{job_id}/cancel")
def cancel_backtest(
    job_id: str,
    db: Annotated[Session, Depends(get_db_session)],
) -> dict:
    repo = BacktestResultRepository(db)
    result = repo.get_by_job_id(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
    if result.status == "RUNNING":
        repo.update_status(job_id, "CANCELLED")
        return {"message": "Cancellation requested"}
    return {"message": "Job is not running"}

@router.delete("")
def clear_all_backtests(
    db: Annotated[Session, Depends(get_db_session)],
) -> dict:
    from sqlalchemy import text
    db.execute(text("DELETE FROM backtest_results"))
    db.execute(text("DELETE FROM paper_accounts WHERE name LIKE 'backtest-%'"))
    db.execute(text("DELETE FROM execution_logs WHERE account_name LIKE 'backtest-%'"))
    db.commit()
    return {"message": "All backtest data cleared successfully"}
