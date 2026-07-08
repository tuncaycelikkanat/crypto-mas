from datetime import datetime, UTC, timedelta
from decimal import Decimal
import pytest

from crypto_mas.services.market_data_service.schemas import OHLCVCandle, Timeframe, Exchange
from crypto_mas.services.market_data_service.integrity import CandleIntegrityChecker, IntegrityIssue, IntegrityReport

def _create_candle(open_time_dt, **kwargs):
    close_time_dt = open_time_dt + timedelta(minutes=1)
    defaults = dict(
        exchange=Exchange.BINANCE,
        symbol="BTCUSDT",
        timeframe=Timeframe.ONE_MINUTE,
        open_time=open_time_dt,
        close_time=close_time_dt,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000"),
        quote_volume=Decimal("100000"),
        trades=100
    )
    defaults.update(kwargs)
    return OHLCVCandle(**defaults)

def test_validate_empty():
    checker = CandleIntegrityChecker()
    report = checker.validate([], Timeframe.ONE_MINUTE)
    assert not report.is_valid
    assert len(report.issues) == 1
    assert report.issues[0].code == "EMPTY_CANDLE_LIST"

def test_validate_valid():
    checker = CandleIntegrityChecker()
    dt1 = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    dt2 = datetime(2023, 1, 1, 12, 1, tzinfo=UTC)
    c1 = _create_candle(dt1)
    c2 = _create_candle(dt2)
    report = checker.validate([c1, c2], Timeframe.ONE_MINUTE)
    assert report.is_valid
    assert len(report.issues) == 0

def test_check_sorting():
    checker = CandleIntegrityChecker()
    dt1 = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    dt2 = datetime(2023, 1, 1, 12, 1, tzinfo=UTC)
    c1 = _create_candle(dt1)
    c2 = _create_candle(dt2)
    # Reverse order
    report = checker.validate([c2, c1], Timeframe.ONE_MINUTE)
    assert not report.is_valid
    issue_codes = [i.code for i in report.issues]
    assert "CANDLES_NOT_SORTED" in issue_codes

def test_check_duplicates():
    checker = CandleIntegrityChecker()
    dt1 = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    c1 = _create_candle(dt1)
    c2 = _create_candle(dt1)
    report = checker.validate([c1, c2], Timeframe.ONE_MINUTE)
    assert not report.is_valid
    issue_codes = [i.code for i in report.issues]
    assert "DUPLICATE_CANDLE" in issue_codes

def test_check_ohlc_negative():
    checker = CandleIntegrityChecker()
    dt1 = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    c1 = _create_candle(dt1, open=Decimal("-10"))
    report = checker.validate([c1], Timeframe.ONE_MINUTE)
    assert not report.is_valid
    issue_codes = [i.code for i in report.issues]
    assert "NON_POSITIVE_PRICE" in issue_codes

def test_check_ohlc_invalid_high_low():
    checker = CandleIntegrityChecker()
    dt1 = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    c1 = _create_candle(dt1, high=Decimal("95")) # High is lower than open(100)
    c2 = _create_candle(dt1 + timedelta(minutes=1), low=Decimal("115")) # Low is higher than high(110)
    report = checker.validate([c1, c2], Timeframe.ONE_MINUTE)
    assert not report.is_valid
    issue_codes = [i.code for i in report.issues]
    assert "INVALID_HIGH" in issue_codes
    assert "INVALID_LOW" in issue_codes

def test_check_volume_negative():
    checker = CandleIntegrityChecker()
    dt1 = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    c1 = _create_candle(dt1, volume=Decimal("-10"))
    c2 = _create_candle(dt1 + timedelta(minutes=1), quote_volume=Decimal("-10"))
    report = checker.validate([c1, c2], Timeframe.ONE_MINUTE)
    assert not report.is_valid
    issue_codes = [i.code for i in report.issues]
    assert "NEGATIVE_VOLUME" in issue_codes
    assert "NEGATIVE_QUOTE_VOLUME" in issue_codes

def test_check_time_bounds():
    checker = CandleIntegrityChecker()
    dt1 = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    c1 = _create_candle(dt1)
    c1.close_time = dt1 - timedelta(minutes=1)
    report = checker.validate([c1], Timeframe.ONE_MINUTE)
    assert not report.is_valid
    issue_codes = [i.code for i in report.issues]
    assert "INVALID_TIME_BOUNDS" in issue_codes

def test_check_missing_candles():
    checker = CandleIntegrityChecker()
    dt1 = datetime(2023, 1, 1, 12, 0, tzinfo=UTC)
    dt3 = datetime(2023, 1, 1, 12, 2, tzinfo=UTC)
    c1 = _create_candle(dt1)
    c3 = _create_candle(dt3)
    report = checker.validate([c1, c3], Timeframe.ONE_MINUTE)
    assert not report.is_valid
    issue_codes = [i.code for i in report.issues]
    assert "MISSING_OR_IRREGULAR_CANDLE" in issue_codes

def test_timeframes():
    checker = CandleIntegrityChecker()
    assert checker._timeframe_to_delta(Timeframe.FIVE_MINUTES) == timedelta(minutes=5)
    assert checker._timeframe_to_delta(Timeframe.FIFTEEN_MINUTES) == timedelta(minutes=15)
    assert checker._timeframe_to_delta(Timeframe.ONE_HOUR) == timedelta(hours=1)
    assert checker._timeframe_to_delta(Timeframe.FOUR_HOURS) == timedelta(hours=4)
    assert checker._timeframe_to_delta(Timeframe.ONE_DAY) == timedelta(days=1)
