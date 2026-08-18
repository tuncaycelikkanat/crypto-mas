from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from crypto_mas.domain.models.symbol import Symbol
from crypto_mas.services.market_data_service.schemas import MarketSymbol


class SymbolRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_upsert(self, symbols: Sequence[MarketSymbol]) -> int:
        if not symbols:
            return 0

        rows = [
            {
                "exchange": symbol.exchange.value,
                "symbol": symbol.symbol,
                "base_asset": symbol.base_asset,
                "quote_asset": symbol.quote_asset,
                "status": symbol.status,
                "is_active": symbol.is_active,
                "is_stablecoin": symbol.is_stablecoin,
                "is_leveraged_token": symbol.is_leveraged_token,
                "listing_date": symbol.listing_date,
                "delisting_date": symbol.delisting_date,
            }
            for symbol in symbols
        ]

        is_pg = bool(self.db.bind and hasattr(self.db.bind, "dialect") and "postgresql" in getattr(self.db.bind.dialect, "name", ""))
        if is_pg:
            stmt = pg_insert(Symbol).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["exchange", "symbol"],
                set_={
                    "base_asset": stmt.excluded.base_asset,
                    "quote_asset": stmt.excluded.quote_asset,
                    "status": stmt.excluded.status,
                    "is_active": stmt.excluded.is_active,
                    "is_stablecoin": stmt.excluded.is_stablecoin,
                    "is_leveraged_token": stmt.excluded.is_leveraged_token,
                    "listing_date": stmt.excluded.listing_date,
                    "delisting_date": stmt.excluded.delisting_date,
                },
            )
        else:
            stmt = sqlite_insert(Symbol).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["exchange", "symbol"],
                set_={
                    "base_asset": stmt.excluded.base_asset,
                    "quote_asset": stmt.excluded.quote_asset,
                    "status": stmt.excluded.status,
                    "is_active": stmt.excluded.is_active,
                    "is_stablecoin": stmt.excluded.is_stablecoin,
                    "is_leveraged_token": stmt.excluded.is_leveraged_token,
                    "listing_date": stmt.excluded.listing_date,
                    "delisting_date": stmt.excluded.delisting_date,
                },
            )

        self.db.execute(stmt)
        self.db.commit()

        return len(rows)

    def list_active_symbols(
        self,
        exchange: str,
        quote_asset: str | None = None,
        limit: int | None = None,
    ) -> list[Symbol]:
        stmt = (
            select(Symbol)
            .where(Symbol.exchange == exchange)
            .where(Symbol.is_active.is_(True))
            .order_by(Symbol.symbol.asc())
        )

        if quote_asset is not None:
            stmt = stmt.where(Symbol.quote_asset == quote_asset)

        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.db.scalars(stmt).all())
