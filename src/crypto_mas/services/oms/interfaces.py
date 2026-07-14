"""
services/oms/interfaces.py — Order Management System Protocol.

Defines the contract that any order management implementation must fulfill.
Currently only PaperOMS is implemented; a LiveOMS can be added in the future
without changing any call sites.
"""
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class Order(BaseModel):
    """An order to submit to the OMS."""

    order_id: str
    account_name: str
    exchange: str
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal        # Limit price; use market price for paper
    created_at: datetime
    strategy_mode: str | None = None


class OrderResult(BaseModel):
    """Result of a submitted or queried order."""

    order_id: str
    status: OrderStatus
    filled_quantity: Decimal
    filled_price: Decimal
    commission: Decimal
    message: str = ""


class IOrderManagementSystem(Protocol):
    """Interface that all OMS implementations must satisfy."""

    async def submit_order(self, order: Order) -> OrderResult:
        """Submit an order and return its result once acknowledged."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Request cancellation of a pending order.

        Returns True if the cancellation was accepted.
        """
        ...

    async def get_order_status(self, order_id: str) -> OrderResult:
        """Return the current status of an order by ID."""
        ...

    async def list_open_orders(self, account_name: str) -> list[Order]:
        """Return all currently pending (unfilled) orders for an account."""
        ...
