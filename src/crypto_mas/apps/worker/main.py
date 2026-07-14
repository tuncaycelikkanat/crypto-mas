"""
apps/worker/main.py — Async background task worker.

Runs as a standalone process that picks up background jobs (e.g. backtests)
and executes them asynchronously, decoupling long-running work from the API.

Usage:
    uv run python -m crypto_mas.apps.worker.main

Or from docker-compose as a separate service.
"""
import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from crypto_mas.infrastructure.logging.setup import setup_logging

# Set up logging before anything else
setup_logging(env=os.getenv("APP_ENV", "dev"), log_dir="logs")
logger = logging.getLogger(__name__)

# Simple in-memory job queue (can be replaced with Redis/Celery in the future)
_job_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
_job_status: dict[str, dict[str, Any]] = {}  # job_id → {status, started_at, completed_at, error}


async def enqueue_backtest(
    job_id: str,
    exchange: str,
    symbols: list[str],
    timeframe: str,
    strategy_name: str,
    start_time: datetime,
    end_time: datetime,
    initial_balance: float = 10_000.0,
) -> None:
    """Enqueue a backtest job for async execution."""
    job = {
        "type": "backtest",
        "job_id": job_id,
        "exchange": exchange,
        "symbols": symbols,
        "timeframe": timeframe,
        "strategy_name": strategy_name,
        "start_time": start_time,
        "end_time": end_time,
        "initial_balance": initial_balance,
    }
    _job_status[job_id] = {
        "status": "QUEUED",
        "queued_at": datetime.now(UTC).isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
    await _job_queue.put(job)
    logger.info("[Worker] Job %s enqueued.", job_id)


def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Return the current status dict for a job, or None if unknown."""
    return _job_status.get(job_id)


def list_jobs() -> list[dict[str, Any]]:
    """Return all known job statuses."""
    return [{"job_id": jid, **status} for jid, status in _job_status.items()]


async def _run_backtest_job(job: dict[str, Any]) -> None:
    """Execute a single backtest job."""
    job_id = job["job_id"]
    _job_status[job_id]["status"] = "RUNNING"
    _job_status[job_id]["started_at"] = datetime.now(UTC).isoformat()

    try:
        from crypto_mas.infrastructure.db.session import SessionLocal
        from crypto_mas.services.backtesting.engine import BacktestEngineService
        from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

        exchange = Exchange(job["exchange"])
        timeframe = Timeframe(job["timeframe"])

        with SessionLocal() as db:
            service = BacktestEngineService(db)
            result = await service.run_backtest(
                job_id=job_id,
                exchange=exchange,
                symbols=job["symbols"],
                timeframe=timeframe,
                strategy_name=job["strategy_name"],
                start_time=job["start_time"],
                end_time=job["end_time"],
                initial_balance=job["initial_balance"],
            )

        _job_status[job_id]["status"] = result.status
        _job_status[job_id]["completed_at"] = datetime.now(UTC).isoformat()
        logger.info("[Worker] Backtest job %s completed: status=%s", job_id, result.status)

    except Exception as exc:
        logger.exception("[Worker] Backtest job %s failed: %s", job_id, exc)
        _job_status[job_id]["status"] = "FAILED"
        _job_status[job_id]["error"] = str(exc)
        _job_status[job_id]["completed_at"] = datetime.now(UTC).isoformat()


async def _job_dispatcher() -> None:
    """Continuously pull jobs from the queue and execute them."""
    logger.info("[Worker] Dispatcher started — waiting for jobs...")
    while True:
        job = await _job_queue.get()
        logger.info("[Worker] Processing job: %s (type=%s)", job.get("job_id"), job.get("type"))
        try:
            if job["type"] == "backtest":
                await _run_backtest_job(job)
            else:
                logger.warning("[Worker] Unknown job type: %s", job["type"])
        except Exception as exc:
            logger.exception("[Worker] Unhandled error in dispatcher: %s", exc)
        finally:
            _job_queue.task_done()


async def main() -> None:
    """Worker entrypoint — runs the job dispatcher until cancelled."""
    logger.info("[Worker] Starting crypto-mas background worker...")
    await _job_dispatcher()


if __name__ == "__main__":
    asyncio.run(main())
