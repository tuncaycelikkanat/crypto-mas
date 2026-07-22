from datetime import timedelta

from crypto_mas.services.market_data_service.schemas import Timeframe


def get_timedelta(timeframe: Timeframe) -> timedelta:
    if timeframe == Timeframe.ONE_MINUTE:
        return timedelta(minutes=1)
    if timeframe == Timeframe.FIFTEEN_MINUTES:
        return timedelta(minutes=15)
    if timeframe == Timeframe.ONE_HOUR:
        return timedelta(hours=1)
    if timeframe == Timeframe.FOUR_HOURS:
        return timedelta(hours=4)
    if timeframe == Timeframe.ONE_DAY:
        return timedelta(days=1)
    if timeframe == Timeframe.ONE_WEEK:
        return timedelta(days=7)
    if timeframe == Timeframe.ONE_MONTH:
        return timedelta(days=30)
    return timedelta(hours=1)
