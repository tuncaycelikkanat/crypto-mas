from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot


class FeatureSnapshotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_upsert(self, snapshots: Sequence[dict[str, Any]]) -> int:
        if not snapshots:
            return 0

        stmt = sqlite_insert(FeatureSnapshot).values(list(snapshots))

        stmt = stmt.on_conflict_do_update(
            index_elements=["exchange", "symbol", "timeframe", "timestamp"],
            set_={
                "available_at": stmt.excluded.available_at,
                "features_json": stmt.excluded.features_json,
            },
        )

        self.db.execute(stmt)
        self.db.commit()

        return len(snapshots)


    def get_latest(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> FeatureSnapshot | None:
        stmt = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.exchange == exchange)
            .where(FeatureSnapshot.symbol == symbol)
            .where(FeatureSnapshot.timeframe == timeframe)
            .order_by(FeatureSnapshot.timestamp.desc())
            .limit(1)
        )

        return self.db.scalars(stmt).first()

    def list_by_symbol(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[FeatureSnapshot]:
        stmt = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.exchange == exchange)
            .where(FeatureSnapshot.symbol == symbol)
            .where(FeatureSnapshot.timeframe == timeframe)
        )

        if start_time is not None:
            stmt = stmt.where(FeatureSnapshot.timestamp >= start_time)

        if end_time is not None:
            stmt = stmt.where(FeatureSnapshot.timestamp <= end_time)

        if limit is not None:
            stmt = stmt.order_by(FeatureSnapshot.timestamp.desc()).limit(limit)
            snapshots = list(self.db.scalars(stmt).all())
            return list(reversed(snapshots))

        stmt = stmt.order_by(FeatureSnapshot.timestamp.asc())
        return list(self.db.scalars(stmt).all())
