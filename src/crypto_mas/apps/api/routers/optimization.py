from typing import Any
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from crypto_mas.domain.models.optimization_history import OptimizationHistory
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import get_db
from crypto_mas.services.auto_optimizer_service import AutoOptimizerService
from crypto_mas.services.market_data_service.schemas import Timeframe

router = APIRouter(prefix="/optimization", tags=["Optimization"])
logger = logging.getLogger(__name__)


def background_optimization_task(db: Session, symbols: list[str], timeframe: Timeframe, strategy_name: str, lookback_months: int):
    try:
        service = AutoOptimizerService(db=db)
        service.run_optimization_job(
            symbols=symbols,
            timeframe=timeframe,
            strategy_name=strategy_name,
            lookback_months=lookback_months,
            n_trials=50,
            triggered_by="MANUAL"
        )
    except Exception as e:
        logger.error(f"Background optimization task failed: {e}")
    finally:
        db.close()


@router.post("/force")
def force_optimization(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Manually triggers the Auto-Optimizer job to run in the background.
    """
    settings = get_settings()
    symbols = settings.scheduled_symbols
    timeframe = Timeframe(settings.scheduled_timeframe)
    strategy_name = "regime_adaptive"
    lookback_months = 3
    
    # We pass a new DB session since the request session will close before the background task finishes.
    from crypto_mas.infrastructure.db.session import SessionLocal
    bg_db = SessionLocal()

    background_tasks.add_task(
        background_optimization_task,
        bg_db,
        symbols,
        timeframe,
        strategy_name,
        lookback_months
    )
    
    return {
        "status": "success",
        "message": f"Optimization job queued for {len(symbols)} symbols over the past {lookback_months} months."
    }


@router.get("/history")
def get_optimization_history(limit: int = 50, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """
    Retrieves the history of all optimization runs.
    """
    records = db.query(OptimizationHistory).order_by(desc(OptimizationHistory.id)).limit(limit).all()
    
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "status": r.status,
            "triggered_by": r.triggered_by,
            "strategy_name": r.strategy_name,
            "symbols_json": r.symbols_json,
            "lookback_months": r.lookback_months,
            "best_params_json": r.best_params_json,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        })
    return result
