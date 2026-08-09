import logging
from typing import Any

from sqlalchemy.orm import Session

from crypto_mas.domain.models.execution_log import ExecutionLog
from crypto_mas.domain.models.order import Order
from crypto_mas.domain.models.trade import Trade
from crypto_mas.domain.repositories.execution_log_repository import ExecutionLogRepository
from crypto_mas.domain.repositories.order_repository import OrderRepository
from crypto_mas.domain.repositories.trade_repository import TradeRepository
from crypto_mas.infrastructure.time.time_provider import TimeProvider

logger = logging.getLogger(__name__)

class ExecutionReporter:
    def __init__(self, db: Session, time_provider: TimeProvider, is_backtest: bool = False):
        self.db = db
        self.time_provider = time_provider
        self.is_backtest = is_backtest
        self.log_repository = ExecutionLogRepository(db)
        self.trade_repository = TradeRepository(db)
        self.order_repository = OrderRepository(db)

    def record_trade_and_order(
        self,
        account_name: str,
        exchange: str,
        symbol: str,
        side: str,
        quantity: Any,
        execution_price: Any,
        notional: Any,
        realized_pnl: Any,
        position_id: Any,
        cycle_id: int | None,
        reason: str
    ) -> None:
        trade = Trade(
            account_name=account_name,
            exchange=exchange,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=execution_price,
            notional=notional,
            realized_pnl=realized_pnl,
            position_id=position_id,
            cycle_id=cycle_id,
            reason=reason,
            executed_at=self.time_provider.now(),
        )
        self.trade_repository.add(trade)

        order = Order(
            account_name=account_name,
            exchange=exchange,
            symbol=symbol,
            side=side,
            status="FILLED",
            requested_quantity=quantity,
            filled_quantity=quantity,
            requested_price=None,
            filled_price=execution_price,
            trade_id=trade.id,
        )
        self.order_repository.add(order)

    def log_execution(
        self,
        account_name: str,
        level: str,
        stage: str,
        message: str,
        cycle_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        # In backtest mode, skip writing logs to DB to avoid thousands of flushes
        if self.is_backtest:
            if level in ("WARN", "WARNING"):
                logger.warning("[%s] %s", stage, message)
            return
        log = ExecutionLog(
            account_name=account_name,
            cycle_id=cycle_id,
            level=level,
            stage=stage,
            message=message,
            payload_json=payload,
            created_at=self.time_provider.now(),
        )
        self.log_repository.add(log)
