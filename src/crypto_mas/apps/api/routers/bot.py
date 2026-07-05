from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

from crypto_mas.services.scheduler_service import SchedulerService

router = APIRouter(prefix="/api/v1/bot", tags=["Trading Bot"])
scheduler = SchedulerService()


class StartBotRequest(BaseModel):
    bot_id: str
    interval_seconds: int | None = None
    symbols: list[str] = ["BTCUSDT", "ETHUSDT"]
    mode: str = "swing"   # scalping | swing | hodl
    exchange: str = "BINANCE"


@router.get("/status")
def get_bot_status() -> dict[str, Any]:
    return scheduler.get_status()


@router.post("/start")
def start_bot(request: StartBotRequest) -> dict[str, Any]:
    return scheduler.start_bot(
        bot_id=request.bot_id,
        interval_seconds=request.interval_seconds,
        symbols=request.symbols,
        mode=request.mode,
        exchange=request.exchange,
    )


class UpdateSymbolsRequest(BaseModel):
    symbols: list[str]


@router.post("/stop/{bot_id}")
def stop_bot(bot_id: str) -> dict[str, Any]:
    return scheduler.stop_bot(bot_id)


@router.put("/symbols/{bot_id}")
def update_bot_symbols(bot_id: str, request: UpdateSymbolsRequest) -> dict[str, Any]:
    return scheduler.update_symbols(bot_id, request.symbols)
