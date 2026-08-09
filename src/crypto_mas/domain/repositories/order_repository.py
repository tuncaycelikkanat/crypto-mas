from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from crypto_mas.domain.models.order import Order
from crypto_mas.domain.value_objects.enums import OrderStatus



class OrderRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, order: Order) -> Order:
        self.session.add(order)
        self.session.flush()
        return order

    def get_by_id(self, order_id: int) -> Order | None:
        return self.session.get(Order, order_id)

    def list_open_orders(self, account_name: str) -> Sequence[Order]:
        stmt = (
            select(Order)
            .where(Order.account_name == account_name)
            .where(Order.status.in_([OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED, OrderStatus.NEW]))
            .order_by(Order.created_at.asc())
        )
        return self.session.scalars(stmt).all()

    def update_status(self, order_id: int, status: str) -> None:
        stmt = (
            update(Order)
            .where(Order.id == order_id)
            .values(status=status)
        )
        self.session.execute(stmt)
        self.session.flush()
