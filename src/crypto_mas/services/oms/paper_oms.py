"""
services/oms/paper_oms.py — Paper Order Management System.

Wraps PaperBrokerService to satisfy the IOrderManagementSystem Protocol.
This thin adapter ensures the rest of the system can talk to OMS without
knowing whether it is paper or (future) live.
"""
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.services.oms.interfaces import (
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
)

logger = logging.getLogger(__name__)


class PaperOMS:
    """Paper-trading implementation of IOrderManagementSystem.

    Routes orders through PaperBrokerService. All orders are treated as
    market orders that fill immediately at the given price.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._position_repo = PositionRepository(db)
        # In-memory order ledger (a full DB table can replace this later)
        self._orders: dict[str, Order] = {}
        self._results: dict[str, OrderResult] = {}

    async def submit_order(self, order: Order) -> OrderResult:
        """Immediately fill a paper order at the given price."""
        self._orders[order.order_id] = order

        if order.side == OrderSide.BUY:
            result = await self._execute_buy(order)
        else:
            result = await self._execute_sell(order)

        self._results[order.order_id] = result
        return result

    async def cancel_order(self, order_id: str) -> bool:
        """Paper orders fill instantly — nothing to cancel."""
        logger.debug("[PaperOMS] cancel_order called for %s — no-op in paper mode.", order_id)
        return False

    async def get_order_status(self, order_id: str) -> OrderResult:
        """Return the stored result of a previously submitted order."""
        if order_id in self._results:
            return self._results[order_id]
        return OrderResult(
            order_id=order_id,
            status=OrderStatus.REJECTED,
            filled_quantity=Decimal("0"),
            filled_price=Decimal("0"),
            commission=Decimal("0"),
            message="Order not found.",
        )

    async def list_open_orders(self, account_name: str) -> list[Order]:
        """Paper orders fill instantly — there are never open orders."""
        return []

    # --- Private execution helpers ---

    async def _execute_buy(self, order: Order) -> OrderResult:
        try:
            position = self._position_repo.create_open_position(
                account_name=order.account_name,
                exchange=order.exchange,
                symbol=order.symbol,
                quantity=order.quantity,
                entry_price=order.price,
                notional_value=order.quantity * order.price,
                opened_at=order.created_at,
                strategy_mode=order.strategy_mode,
            )
            logger.info(
                "[PaperOMS] BUY filled: %s %s qty=%s @ %s",
                order.account_name, order.symbol, order.quantity, order.price,
            )
            return OrderResult(
                order_id=order.order_id,
                status=OrderStatus.FILLED,
                filled_quantity=order.quantity,
                filled_price=order.price,
                commission=Decimal("0"),
                message=f"Paper BUY filled. Position ID: {position.id}",
            )
        except Exception as exc:
            logger.error("[PaperOMS] BUY failed for %s: %s", order.symbol, exc)
            return OrderResult(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal("0"),
                filled_price=Decimal("0"),
                commission=Decimal("0"),
                message=str(exc),
            )

    async def _execute_sell(self, order: Order) -> OrderResult:
        try:
            open_pos = self._position_repo.get_open_position(
                account_name=order.account_name,
                exchange=order.exchange,
                symbol=order.symbol,
            )
            if not open_pos:
                return OrderResult(
                    order_id=order.order_id,
                    status=OrderStatus.REJECTED,
                    filled_quantity=Decimal("0"),
                    filled_price=Decimal("0"),
                    commission=Decimal("0"),
                    message=f"No open position found for {order.symbol}.",
                )
            position = self._position_repo.close_position(
                position=open_pos,
                exit_price=order.price,
                closed_at=order.created_at,
                close_reason="OMS_SELL",
            )
            logger.info(
                "[PaperOMS] SELL filled: %s %s @ %s pnl=%s",
                order.account_name, order.symbol, order.price, position.realized_pnl,
            )
            return OrderResult(
                order_id=order.order_id,
                status=OrderStatus.FILLED,
                filled_quantity=position.quantity,
                filled_price=order.price,
                commission=Decimal("0"),
                message=f"Paper SELL filled. Realized PnL: {position.realized_pnl}",
            )
        except Exception as exc:
            logger.error("[PaperOMS] SELL failed for %s: %s", order.symbol, exc)
            return OrderResult(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                filled_quantity=Decimal("0"),
                filled_price=Decimal("0"),
                commission=Decimal("0"),
                message=str(exc),
            )


def create_order(
    account_name: str,
    exchange: str,
    symbol: str,
    side: OrderSide,
    quantity: Decimal,
    price: Decimal,
    strategy_mode: str | None = None,
) -> Order:
    """Factory helper to create an Order with a generated ID and current timestamp."""
    return Order(
        order_id=str(uuid.uuid4()),
        account_name=account_name,
        exchange=exchange,
        symbol=symbol,
        side=side,
        quantity=quantity,
        price=price,
        created_at=datetime.now(UTC),
        strategy_mode=strategy_mode,
    )
