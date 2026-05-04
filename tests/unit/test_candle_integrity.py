from datetime import UTC, datetime, timedelta
from decimal import Decimal

from services.market_data_service.integrity import CandleIntegrityChecker
from services.market_data_service.schemas import Exchange, OHLCVCandle, Timeframe


def _make_candle(open_time: datetime) -> OHLCVCandle:
    return OHLCVCandle(
        exchange=Exchange.MOCK,
        symbol="BTCUSDT",
        timeframe=Timeframe.FOUR_HOURS,
        open_time=open_time,
        close_time=open_time + timedelta(hours=4),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000"),
        quote_volume=Decimal("100000"),
        trade_count=100,
        source="TEST",
    )


def test_valid_candles_pass_integrity_check() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)

    candles = [
        _make_candle(start),
        _make_candle(start + timedelta(hours=4)),
        _make_candle(start + timedelta(hours=8)),
    ]

    report = CandleIntegrityChecker().validate(candles, Timeframe.FOUR_HOURS)

    assert report.is_valid is True
    assert report.issue_count == 0


def test_missing_candle_fails_integrity_check() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)

    candles = [
        _make_candle(start),
        _make_candle(start + timedelta(hours=8)),
    ]

    report = CandleIntegrityChecker().validate(candles, Timeframe.FOUR_HOURS)

    assert report.is_valid is False
    assert any(issue.code == "MISSING_OR_IRREGULAR_CANDLE" for issue in report.issues)


def test_invalid_ohlc_fails_integrity_check() -> None:
    candle = _make_candle(datetime(2026, 1, 1, tzinfo=UTC))
    candle.high = Decimal("80")

    report = CandleIntegrityChecker().validate([candle], Timeframe.FOUR_HOURS)

    assert report.is_valid is False
    assert any(issue.code == "INVALID_HIGH" for issue in report.issues)
