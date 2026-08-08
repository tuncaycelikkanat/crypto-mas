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
    risk_level: int = Field(100, ge=0, le=200)
    use_btc_shield: bool = True
    use_htf_shield: bool = True
    use_regime_shield: bool = True
    config_json: dict | None = None
    run_llm: bool = False

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
    total_fees_paid: float | None = None
    total_trades: int | None
    win_rate: float | None
    max_drawdown: float | None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    calmar_ratio: float | None = None
    profit_factor: float | None = None
    expectancy: float | None = None
    avg_win: float | None = None
    avg_loss: float | None = None
    avg_trade_duration_s: float | None = None
    error_message: str | None
    config_json: dict | None = None


async def run_backtest_task(
    job_id: str,
    exchange: Exchange,
    symbols: list[str],
    timeframe: Timeframe,
    strategy_name: str,
    start_time: datetime,
    end_time: datetime,
    initial_balance: float,
    risk_level: int,
    use_btc_shield: bool,
    use_htf_shield: bool,
    use_regime_shield: bool,
    config_json: dict | None = None,
    run_llm: bool = False,
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
            risk_level=risk_level,
            use_btc_shield=use_btc_shield,
            use_htf_shield=use_htf_shield,
            use_regime_shield=use_regime_shield,
            config_json=config_json,
            run_llm=run_llm,
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
        risk_level=request.risk_level,
        use_btc_shield=request.use_btc_shield,
        use_htf_shield=request.use_htf_shield,
        use_regime_shield=request.use_regime_shield,
        config_json=request.config_json,
        run_llm=request.run_llm,
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
        job_id=result.job_id,  # type: ignore
        status=result.status,  # type: ignore
        exchange=result.exchange,  # type: ignore
        timeframe=result.timeframe,  # type: ignore
        strategy_name=result.strategy_name,  # type: ignore
        symbols=result.symbols,  # type: ignore
        start_time=result.start_time,  # type: ignore
        end_time=result.end_time,  # type: ignore
        initial_balance=result.initial_balance,  # type: ignore
        final_equity=result.final_equity,  # type: ignore
        total_fees_paid=result.total_fees_paid,  # type: ignore
        total_trades=result.total_trades,  # type: ignore
        win_rate=result.win_rate,  # type: ignore
        max_drawdown=result.max_drawdown,  # type: ignore
        sharpe_ratio=result.sharpe_ratio,  # type: ignore
        sortino_ratio=result.sortino_ratio,  # type: ignore
        calmar_ratio=result.calmar_ratio,  # type: ignore
        profit_factor=result.profit_factor,  # type: ignore
        expectancy=result.expectancy,  # type: ignore
        avg_win=result.avg_win,  # type: ignore
        avg_loss=result.avg_loss,  # type: ignore
        avg_trade_duration_s=result.avg_trade_duration_s,  # type: ignore
        error_message=result.error_message,  # type: ignore
        config_json=result.config_json,  # type: ignore
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
            job_id=r.job_id,  # type: ignore
            status=r.status,  # type: ignore
            exchange=r.exchange,  # type: ignore
            timeframe=r.timeframe,  # type: ignore
            strategy_name=r.strategy_name,  # type: ignore
            symbols=r.symbols,  # type: ignore
            start_time=r.start_time,  # type: ignore
            end_time=r.end_time,  # type: ignore
            initial_balance=r.initial_balance,  # type: ignore
            final_equity=r.final_equity,  # type: ignore
            total_fees_paid=r.total_fees_paid,  # type: ignore
            total_trades=r.total_trades,  # type: ignore
            win_rate=r.win_rate,  # type: ignore
            max_drawdown=r.max_drawdown,  # type: ignore
            sharpe_ratio=r.sharpe_ratio,  # type: ignore
            sortino_ratio=r.sortino_ratio,  # type: ignore
            calmar_ratio=r.calmar_ratio,  # type: ignore
            profit_factor=r.profit_factor,  # type: ignore
            expectancy=r.expectancy,  # type: ignore
            avg_win=r.avg_win,  # type: ignore
            avg_loss=r.avg_loss,  # type: ignore
            avg_trade_duration_s=r.avg_trade_duration_s,  # type: ignore
            error_message=r.error_message,  # type: ignore
            config_json=r.config_json,  # type: ignore
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
    return {"message": "All backtests cleared"}

@router.delete("/{job_id}")
def delete_backtest(
    job_id: str,
    db: Annotated[Session, Depends(get_db_session)],
) -> dict:
    from sqlalchemy import text
    repo = BacktestResultRepository(db)
    result = repo.get_by_job_id(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")
        
    # Delete DB records
    db.execute(text("DELETE FROM backtest_results WHERE job_id = :jid"), {"jid": job_id})
    db.execute(text("DELETE FROM paper_accounts WHERE name = :aname"), {"aname": f"backtest-{job_id}"})
    db.execute(text("DELETE FROM execution_logs WHERE account_name = :aname"), {"aname": f"backtest-{job_id}"})
    db.commit()
    
    # Optionally delete the archive folder
    import shutil
    from pathlib import Path
    archive_dir = Path(f"data/backtests/{job_id}")
    if archive_dir.exists() and archive_dir.is_dir():
        shutil.rmtree(archive_dir)
        
    return {"message": f"Backtest {job_id} deleted"}

@router.get("/{job_id}/equity-curve")
def get_equity_curve(
    job_id: str,
    db: Annotated[Session, Depends(get_db_session)],
    source: str = "trades",  # "trades" (trade-level) or "cycles"
):
    """
    Returns a high-resolution equity curve for a backtest.

    - source=trades  → a data point per closed trade (most detailed)
    - source=cycles  → a data point per simulated cycle (faster, but coarser)
    """
    from sqlalchemy import select

    account_name = f"backtest-{job_id}"

    result = BacktestResultRepository(db).get_by_job_id(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest not found")

    initial_balance = result.initial_balance or 10000.0

    if source == "trades":
        from crypto_mas.domain.models.trade import Trade
        trades = db.execute(
            select(Trade)
            .where(Trade.account_name == account_name)
            .where(Trade.realized_pnl.is_not(None))
            .order_by(Trade.executed_at.asc())
        ).scalars().all()

        equity = initial_balance
        curve = [{"time": result.start_time.isoformat(), "value": equity}]
        for t in trades:
            equity += float(t.realized_pnl)  # type: ignore
            curve.append({
                "time": t.executed_at.isoformat() if t.executed_at else None,
                "value": round(equity, 4),
                "symbol": t.symbol,
                "pnl": round(float(t.realized_pnl), 4),
            })
        return {"job_id": job_id, "source": "trades", "data": curve}

    else:
        from crypto_mas.domain.models.trading_cycle import TradingCycle
        cycles = db.execute(
            select(TradingCycle.finished_at, TradingCycle.ending_equity)
            .where(TradingCycle.account_name == account_name)
            .where(TradingCycle.finished_at.is_not(None))
            .order_by(TradingCycle.finished_at.asc())
        ).all()
        curve = [
            {"time": c.finished_at.isoformat(), "value": float(c.ending_equity)}
            for c in cycles if c.ending_equity is not None
        ]
        return {"job_id": job_id, "source": "cycles", "data": curve}


@router.get("/{job_id}/compare-data")
def get_backtest_compare_data(
    job_id: str,
    db: Annotated[Session, Depends(get_db_session)],
):
    """Legacy endpoint — returns cycle-level equity curve for comparison charts."""
    from sqlalchemy import select

    from crypto_mas.domain.models.trading_cycle import TradingCycle

    account_name = f"backtest-{job_id}"
    cycles = db.execute(
        select(TradingCycle.finished_at, TradingCycle.ending_equity)
        .where(TradingCycle.account_name == account_name)
        .where(TradingCycle.finished_at.is_not(None))
        .order_by(TradingCycle.finished_at.asc())
    ).all()

    equity_curve = [
        {"time": c.finished_at.isoformat(), "equity": float(c.ending_equity)}
        for c in cycles if c.ending_equity is not None
    ]
    return {"job_id": job_id, "equity_curve": equity_curve}

