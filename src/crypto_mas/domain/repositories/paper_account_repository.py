from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from crypto_mas.domain.models.paper_account import PaperAccount


class PaperAccountRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_name(self, name: str) -> PaperAccount | None:
        stmt = select(PaperAccount).where(PaperAccount.name == name)

        return self.db.scalars(stmt).first()

    def create_if_not_exists(
        self,
        name: str,
        exchange: str,
        base_currency: str,
        initial_balance: Decimal,
    ) -> PaperAccount:
        existing = self.get_by_name(name)

        if existing is not None:
            return existing

        account = PaperAccount(
            name=name,
            exchange=exchange,
            base_currency=base_currency,
            initial_balance=initial_balance,
            cash_balance=initial_balance,
            equity=initial_balance,
        )

        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        return account

    def update_balances(
        self,
        account: PaperAccount,
        cash_balance: Decimal,
        equity: Decimal,
    ) -> PaperAccount:
        account.cash_balance = cash_balance
        account.equity = equity

        self.db.commit()
        self.db.refresh(account)

        return account
