from collections.abc import Sequence
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from domain.models.feature_snapshot import FeatureSnapshot


class FeatureSnapshotRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def bulk_upsert(self, snapshots: Sequence[dict[str, Any]]) -> int:
        if not snapshots:
            return 0

        stmt = insert(FeatureSnapshot).values(list(snapshots))

        stmt = stmt.on_conflict_do_update(
            constraint="uq_feature_snapshots_exchange_symbol_tf_timestamp",
            set_={
                "available_at": stmt.excluded.available_at,
                "features_json": stmt.excluded.features_json,
            },
        )

        self.db.execute(stmt)
        self.db.commit()

        return len(snapshots)
