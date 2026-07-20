from datetime import timedelta
from decimal import Decimal

from pydantic import BaseModel

from crypto_mas.services.market_data_service.schemas import OHLCVCandle, Timeframe


class IntegrityIssue(BaseModel):
    code: str
    message: str
    symbol: str | None = None
    open_time: str | None = None


class IntegrityReport(BaseModel):
    is_valid: bool
    total_candles: int
    issue_count: int
    issues: list[IntegrityIssue]


class CandleIntegrityChecker:
    def validate(
        self,
        candles: list[OHLCVCandle],
        timeframe: Timeframe,
    ) -> IntegrityReport:
        issues: list[IntegrityIssue] = []

        if not candles:
            issues.append(
                IntegrityIssue(
                    code="EMPTY_CANDLE_LIST",
                    message="Candle list is empty.",
                )
            )
            return IntegrityReport(
                is_valid=False,
                total_candles=0,
                issue_count=len(issues),
                issues=issues,
            )

        issues.extend(self._check_sorting(candles))
        issues.extend(self._check_duplicates(candles))
        issues.extend(self._check_ohlc(candles))
        issues.extend(self._check_volume(candles))
        issues.extend(self._check_time_bounds(candles))
        issues.extend(self._check_missing_candles(candles, timeframe))

        return IntegrityReport(
            is_valid=len(issues) == 0,
            total_candles=len(candles),
            issue_count=len(issues),
            issues=issues,
        )

    def _check_sorting(self, candles: list[OHLCVCandle]) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []

        for previous, current in zip(candles, candles[1:], strict=False):
            if current.open_time < previous.open_time:
                issues.append(
                    IntegrityIssue(
                        code="CANDLES_NOT_SORTED",
                        message="Candles are not sorted by open_time.",
                        symbol=current.symbol,
                        open_time=current.open_time.isoformat(),
                    )
                )

        return issues

    def _check_duplicates(self, candles: list[OHLCVCandle]) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        seen: set[tuple[str, str, str]] = set()

        for candle in candles:
            key = (
                candle.exchange.value,
                candle.symbol,
                candle.open_time.isoformat(),
            )

            if key in seen:
                issues.append(
                    IntegrityIssue(
                        code="DUPLICATE_CANDLE",
                        message="Duplicate candle detected.",
                        symbol=candle.symbol,
                        open_time=candle.open_time.isoformat(),
                    )
                )

            seen.add(key)

        return issues

    def _check_ohlc(self, candles: list[OHLCVCandle]) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []

        for candle in candles:
            values = [candle.open, candle.high, candle.low, candle.close]

            if any(value <= Decimal("0") for value in values):
                issues.append(
                    IntegrityIssue(
                        code="NON_POSITIVE_PRICE",
                        message="OHLC values must be positive.",
                        symbol=candle.symbol,
                        open_time=candle.open_time.isoformat(),
                    )
                )
                continue

            if candle.high < max(candle.open, candle.close, candle.low):
                issues.append(
                    IntegrityIssue(
                        code="INVALID_HIGH",
                        message="High must be greater than or equal to open, close and low.",
                        symbol=candle.symbol,
                        open_time=candle.open_time.isoformat(),
                    )
                )

            if candle.low > min(candle.open, candle.close, candle.high):
                issues.append(
                    IntegrityIssue(
                        code="INVALID_LOW",
                        message="Low must be less than or equal to open, close and high.",
                        symbol=candle.symbol,
                        open_time=candle.open_time.isoformat(),
                    )
                )

        return issues

    def _check_volume(self, candles: list[OHLCVCandle]) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []

        for candle in candles:
            if candle.volume < Decimal("0"):
                issues.append(
                    IntegrityIssue(
                        code="NEGATIVE_VOLUME",
                        message="Volume cannot be negative.",
                        symbol=candle.symbol,
                        open_time=candle.open_time.isoformat(),
                    )
                )

            if candle.quote_volume is not None and candle.quote_volume < Decimal("0"):
                issues.append(
                    IntegrityIssue(
                        code="NEGATIVE_QUOTE_VOLUME",
                        message="Quote volume cannot be negative.",
                        symbol=candle.symbol,
                        open_time=candle.open_time.isoformat(),
                    )
                )

        return issues

    def _check_time_bounds(self, candles: list[OHLCVCandle]) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []

        for candle in candles:
            if candle.close_time <= candle.open_time:
                issues.append(
                    IntegrityIssue(
                        code="INVALID_TIME_BOUNDS",
                        message="close_time must be greater than open_time.",
                        symbol=candle.symbol,
                        open_time=candle.open_time.isoformat(),
                    )
                )

        return issues

    def _check_missing_candles(
        self,
        candles: list[OHLCVCandle],
        timeframe: Timeframe,
    ) -> list[IntegrityIssue]:
        issues: list[IntegrityIssue] = []
        expected_step = self._timeframe_to_delta(timeframe)

        sorted_candles = sorted(candles, key=lambda candle: candle.open_time)

        for previous, current in zip(sorted_candles, sorted_candles[1:], strict=False):
            actual_step = current.open_time - previous.open_time

            if actual_step != expected_step:
                issues.append(
                    IntegrityIssue(
                        code="MISSING_OR_IRREGULAR_CANDLE",
                        message=(
                            f"Expected step {expected_step}, got {actual_step} between candles."
                        ),
                        symbol=current.symbol,
                        open_time=current.open_time.isoformat(),
                    )
                )

        return issues

    @staticmethod
    def _timeframe_to_delta(timeframe: Timeframe) -> timedelta:  # type: ignore
        match timeframe:
            case Timeframe.ONE_MINUTE:
                return timedelta(minutes=1)
            case Timeframe.FIVE_MINUTES:
                return timedelta(minutes=5)
            case Timeframe.FIFTEEN_MINUTES:
                return timedelta(minutes=15)
            case Timeframe.ONE_HOUR:
                return timedelta(hours=1)
            case Timeframe.FOUR_HOURS:
                return timedelta(hours=4)
            case Timeframe.ONE_DAY:
                return timedelta(days=1)
