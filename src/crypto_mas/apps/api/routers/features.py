from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from crypto_mas.infrastructure.db.session import get_db_session
from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
from crypto_mas.services.market_data_service.schemas import Exchange, Timeframe

router = APIRouter(prefix="/features", tags=["Features"])

@router.post("/mock/calculate")
def calculate_mock_features(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, object]:
    service = FeaturePipelineService(db)
    return service.calculate_and_store(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        limit=200,
    )

@router.post("/mock/calculate-all")
def calculate_all_mock_features(db: Annotated[Session, Depends(get_db_session)]) -> dict[str, object]:
    service = FeaturePipelineService(db)
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    results: list[dict[str, object]] = []

    for symbol in symbols:
        result = service.calculate_and_store(
            exchange=Exchange.MOCK,
            symbol=symbol,
            timeframe=Timeframe.FOUR_HOURS,
            limit=200,
        )
        results.append(result)

    return {
        "exchange": Exchange.MOCK.value,
        "symbols": symbols,
        "results": results,
    }
