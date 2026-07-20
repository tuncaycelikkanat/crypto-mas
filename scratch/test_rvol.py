from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crypto_mas.domain.models.candle import Candle
from crypto_mas.services.feature_pipeline.calculator import FeatureCalculator

engine = create_engine("sqlite:///crypto_mas.db")
with Session(engine) as session:
    candles = session.scalars(select(Candle).where(Candle.symbol == "BTCUSDT", Candle.timeframe == "1m").order_by(Candle.open_time.asc()).limit(40000)).all()

calc = FeatureCalculator()
snaps = calc.calculate(candles)

count = sum(1 for s in snaps if (s["features_json"].get("rvol") or 0.0) >= 3.0)
print(f"Total snaps: {len(snaps)}, Spikes: {count}")

spikes = [s for s in snaps if (s["features_json"].get("rvol") or 0.0) >= 3.0]
if spikes:
    print(spikes[0]["features_json"])
