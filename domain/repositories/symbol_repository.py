from collections.abc import Sequence

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from domain.models.symbol import Symbol
from services.market_data_service.schemas import MarketSymbol


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

        stmt = insert(Symbol).values(rows)

        stmt = stmt.on_conflict_do_update(
            constraint="uq_symbols_exchange_symbol",
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
