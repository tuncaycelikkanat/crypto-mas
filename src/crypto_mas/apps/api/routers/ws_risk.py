"""
ws_risk.py — WebSocket & REST Dashboard endpoint for Real-Time Risk & Regime Shield.

Endpoints:
    WS  /api/v1/ws/risk-regime
    GET /api/v1/ws/risk-regime/snapshot
"""
import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.engine.regime.regime import RegimeEngine
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.infrastructure.db.session import SessionLocal

logger = logging.getLogger("crypto_mas.ws_risk")

router = APIRouter(prefix="/api/v1/ws", tags=["Real-Time Risk Dashboard"])


def build_risk_regime_snapshot() -> dict[str, Any]:
    """Assemble a comprehensive real-time regime & portfolio risk snapshot."""
    settings = get_settings()
    btc_regime = "NORMAL"
    confidence = 0.5
    risk_multiplier = 1.0

    # Query latest BTCUSDT snapshot for regime assessment
    try:
        with SessionLocal() as db:
            repo = FeatureSnapshotRepository(db)
            snapshots = repo.list_by_symbol(
                exchange="MOCK",
                symbol="BTCUSDT",
                timeframe="4h",
                limit=100,
            )
            if snapshots:
                regime_res = RegimeEngine().evaluate(
                    exchange=snapshots[0].exchange,
                    symbol=snapshots[0].symbol,
                    timeframe=snapshots[0].timeframe,
                    snapshots=snapshots,
                )
                if regime_res:
                    btc_regime = regime_res.regime_type.value
                    confidence = float(regime_res.confidence)
                    risk_multiplier = float(regime_res.risk_multiplier)
    except Exception as exc:
        logger.warning("[ws_risk] Failed to evaluate BTC regime snapshot: %s", exc)

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "system_status": "ACTIVE",
        "trading_mode": settings.trading_mode,
        "regime_snapshot": {
            "btc_regime": btc_regime,
            "confidence": round(confidence, 4),
            "risk_multiplier": round(risk_multiplier, 2),
        },
        "risk_snapshot": {
            "max_drawdown_limit_pct": 15.0,
            "current_drawdown_pct": 0.0,
            "gross_exposure_pct": 0.0,
            "correlated_symbols_count": len(settings.btc_correlated_symbols),
            "max_positions_allowed": 5,
        },
    }


@router.get("/risk-regime/snapshot")
def get_risk_regime_snapshot() -> dict[str, Any]:
    """Return an immediate JSON snapshot of current regime and risk shield."""
    return build_risk_regime_snapshot()


class ConnectionManager:
    """Manages active WebSocket connections for risk dashboard broadcasting."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast(self, message: dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/risk-regime")
async def websocket_risk_regime(websocket: WebSocket):
    """Real-time WebSocket feed pushing risk and regime metrics every 3 seconds."""
    await manager.connect(websocket)
    try:
        while True:
            snapshot = build_risk_regime_snapshot()
            await manager.send_personal_message(snapshot, websocket)
            await asyncio.sleep(3.0)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("[ws_risk] WebSocket error: %s", exc)
        manager.disconnect(websocket)
