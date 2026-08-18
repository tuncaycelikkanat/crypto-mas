from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/bot", tags=["Trading Bot"])

def get_scheduler(request: Request) -> SchedulerService:
    return request.app.state.scheduler  # type: ignore


class StartBotRequest(BaseModel):
    bot_id: str
    interval_seconds: int | None = None
    symbols: list[str] = ["BTCUSDT", "ETHUSDT"]
    mode: str = "swing"   # scalping | swing | hodl
    exchange: str = "BINANCE"
    risk_level: int = 50
    use_btc_shield: bool = True
    use_htf_shield: bool = True
    use_regime_shield: bool = True


@router.get("/status")
def get_bot_status(scheduler: SchedulerService = Depends(get_scheduler)) -> dict[str, Any]:
    return scheduler.get_status()


@router.post("/start")
def start_bot(request: StartBotRequest, scheduler: SchedulerService = Depends(get_scheduler)) -> dict[str, Any]:
    return scheduler.start_bot(
        bot_id=request.bot_id,
        interval_seconds=request.interval_seconds,
        symbols=request.symbols,
        mode=request.mode,
        exchange=request.exchange,
        risk_level=request.risk_level,
        use_btc_shield=request.use_btc_shield,
        use_htf_shield=request.use_htf_shield,
        use_regime_shield=request.use_regime_shield,
    )


class UpdateSymbolsRequest(BaseModel):
    symbols: list[str]


@router.post("/stop/{bot_id}")
def stop_bot(bot_id: str, scheduler: SchedulerService = Depends(get_scheduler)) -> dict[str, Any]:
    return scheduler.stop_bot(bot_id)


@router.put("/symbols/{bot_id}")
def update_bot_symbols(bot_id: str, request: UpdateSymbolsRequest, scheduler: SchedulerService = Depends(get_scheduler)) -> dict[str, Any]:
    return scheduler.update_symbols(bot_id, request.symbols)


class UpdateRiskRequest(BaseModel):
    risk_level: int


@router.put("/risk/{bot_id}")
def update_bot_risk(bot_id: str, request: UpdateRiskRequest, scheduler: SchedulerService = Depends(get_scheduler)) -> dict[str, Any]:
    return scheduler.update_risk(bot_id, request.risk_level)
