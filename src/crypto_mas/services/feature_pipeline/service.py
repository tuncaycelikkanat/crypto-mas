from datetime import datetime

from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.candle_repository import CandleRepository
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.services.feature_pipeline.calculator import FeatureCalculator
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe


class FeaturePipelineService:
    def __init__(self, db: Session) -> None:
        self.candle_repository = CandleRepository(db)
        self.feature_snapshot_repository = FeatureSnapshotRepository(db)
        self.calculator = FeatureCalculator()

    def calculate_and_store(
        self,
        exchange: Exchange,
        symbol: str,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> dict[str, object]:
        candles = self.candle_repository.list_by_symbol(
            exchange=exchange.value,
            symbol=symbol,
            timeframe=timeframe.value,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        snapshots = self.calculator.calculate(candles)
        processed_rows = self.feature_snapshot_repository.bulk_upsert(snapshots)

        return {
            "exchange": exchange.value,
            "symbol": symbol,
            "timeframe": timeframe.value,
            "candles": len(candles),
            "features": len(snapshots),
            "processed_rows": processed_rows,
        }
