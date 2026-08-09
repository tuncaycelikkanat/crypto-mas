import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.infrastructure.time.time_provider import TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange
from crypto_mas.services.paper_trading.execution_reporter import ExecutionReporter
from crypto_mas.services.paper_trading.risk_calculator import RiskCalculator
from crypto_mas.services.paper_trading.schemas import (
    PaperExecutionItem,
    PaperExecutionReport,
    PaperExecutionStatus,
    PaperOrderSide,
)

logger = logging.getLogger(__name__)

class MarkToMarket:
    def __init__(
        self, 
        db: Session, 
        risk_calculator: RiskCalculator, 
        reporter: ExecutionReporter, 
        time_provider: TimeProvider,
        is_backtest: bool = False
    ):
        self.db = db
        self.risk_calculator = risk_calculator
        self.reporter = reporter
        self.time_provider = time_provider
        self.is_backtest = is_backtest
        self.account_repository = PaperAccountRepository(db)
        self.position_repository = PositionRepository(db)
        self.feature_snapshot_repository = FeatureSnapshotRepository(db)
        
    def _calculate_open_positions_value(self, account_name: str) -> Decimal:
        positions = self.position_repository.list_open_positions(account_name=account_name)
        total_value = Decimal("0")
        for position in positions:
            if position.side == "LONG":
                total_value += position.current_price * position.quantity
            else:
                total_value += (Decimal("2") * position.entry_price - position.current_price) * position.quantity
        return self.risk_calculator._money(total_value)

    def update_mark_prices(
        self,
        account: Any,
        exchange: Exchange,
        timeframe: str,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        starting_cash = account.cash_balance
        starting_equity = account.equity

        positions = self.position_repository.list_open_positions(account_name=account.name)
        executed: list[PaperExecutionItem] = []
        skipped: list[PaperExecutionItem] = []

        for position in positions:
            latest_snapshot = self.feature_snapshot_repository.get_latest(
                exchange=exchange.value,
                symbol=position.symbol,
                timeframe=timeframe,
                end_time=self.time_provider.now(),
            )

            price = self.risk_calculator.extract_close_price(latest_snapshot)

            if price is None or price <= Decimal("0"):
                skipped.append(
                    PaperExecutionItem(
                        symbol=position.symbol,
                        side=PaperOrderSide.BUY if position.side == "LONG" else PaperOrderSide.SELL,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=0.0,
                        notional=float(position.notional_value),
                        price=None,
                        quantity=float(position.quantity),
                        reason="Latest close price not available for mark-to-market.",
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Skipped M2M for {position.symbol}: Latest close price not available.",
                    cycle_id=cycle_id,
                )
                continue

            updated_position = self.position_repository.update_mark_price(
                position=position,
                current_price=price,
                skip_commit=self.is_backtest,
            )

            atr_14 = latest_snapshot.features_json.get("atr_14") if latest_snapshot else None
            
            if atr_14 and float(atr_14) > 0:
                sl_pct = Decimal(str((float(atr_14) / float(price)) * 2.0))
            else:
                sl_pct = Decimal(str(self.risk_calculator.SL_PCT.get(self.risk_calculator.strategy_mode, 0.03)))
                
            if updated_position.side == "LONG":
                current_pnl_pct = (price - updated_position.entry_price) / updated_position.entry_price
            else:
                current_pnl_pct = (updated_position.entry_price - price) / updated_position.entry_price
                
            if current_pnl_pct > Decimal("0.02"):
                sl_pct = sl_pct * Decimal("0.5")
            elif current_pnl_pct > Decimal("0.01"):
                sl_pct = sl_pct * Decimal("0.75")
            
            if updated_position.side == "LONG":
                potential_sl = self.risk_calculator._money(price * (Decimal("1") - sl_pct))
                
                friction = Decimal(str((self.risk_calculator.COMMISSION_RATE + self.risk_calculator.SLIPPAGE_RATE) * 2))
                break_even_price = updated_position.entry_price * (Decimal("1") + friction)
                if updated_position.stop_loss_price is None or potential_sl > updated_position.stop_loss_price:
                    if price > break_even_price:
                        updated_position = self.position_repository.update_stop_loss(
                            position=updated_position,
                            stop_loss_price=potential_sl,
                            skip_commit=self.is_backtest,
                        )
                        self.reporter.log_execution(
                            account_name=account.name,
                            level="INFO",
                            stage="TRAILING_SL",
                            message=f"Trailing SL moved UP for {updated_position.symbol} to ${float(potential_sl):.4f} (Locking profit)",
                            cycle_id=cycle_id,
                        )

                sl_hit = (
                    updated_position.stop_loss_price is not None
                    and price <= updated_position.stop_loss_price
                )
                tp_hit = (
                    updated_position.take_profit_price is not None
                    and price >= updated_position.take_profit_price
                )
            else:
                potential_sl = self.risk_calculator._money(price * (Decimal("1") + sl_pct))
                
                friction = Decimal(str((self.risk_calculator.COMMISSION_RATE + self.risk_calculator.SLIPPAGE_RATE) * 2))
                break_even_price = updated_position.entry_price * (Decimal("1") - friction)
                if updated_position.stop_loss_price is None or potential_sl < updated_position.stop_loss_price:
                    if price < break_even_price:
                        updated_position = self.position_repository.update_stop_loss(
                            position=updated_position,
                            stop_loss_price=potential_sl,
                            skip_commit=self.is_backtest,
                        )
                        self.reporter.log_execution(
                            account_name=account.name,
                            level="INFO",
                            stage="TRAILING_SL",
                            message=f"Trailing SL moved DOWN for {updated_position.symbol} to ${float(potential_sl):.4f} (Locking profit)",
                            cycle_id=cycle_id,
                        )

                sl_hit = (
                    updated_position.stop_loss_price is not None
                    and price >= updated_position.stop_loss_price
                )
                tp_hit = (
                    updated_position.take_profit_price is not None
                    and price <= updated_position.take_profit_price
                )

            if sl_hit or tp_hit:
                close_reason = "STOP_LOSS" if sl_hit else "TAKE_PROFIT"
                
                execution_price = self.risk_calculator.calculate_exit_price(price, position.side)
                raw_realized_pnl, pnl_pct = self.risk_calculator.calculate_pnl(position.entry_price, execution_price, position.quantity, position.side)

                gross_notional = self.risk_calculator._money(position.quantity * execution_price)
                fee = self.risk_calculator.calculate_fee(gross_notional)
                net_recovered = self.risk_calculator._money((position.quantity * position.entry_price) + raw_realized_pnl - fee)
                
                closed = self.position_repository.close_position(
                    position=updated_position,
                    exit_price=execution_price,
                    closed_at=self.time_provider.now(),
                    close_reason=close_reason,
                    skip_commit=self.is_backtest,
                )
                
                closed.realized_pnl -= fee

                new_cash = self.risk_calculator._money(account.cash_balance + net_recovered)
                account.cash_balance = new_cash
                if not self.is_backtest:
                    self.db.commit()

                side_enum = PaperOrderSide.SELL if position.side == "LONG" else PaperOrderSide.BUY
                
                self.reporter.record_trade_and_order(
                    account_name=account.name,
                    exchange=exchange.value,
                    symbol=closed.symbol,
                    side=side_enum.value,
                    quantity=closed.quantity,
                    execution_price=execution_price,
                    notional=gross_notional,
                    realized_pnl=closed.realized_pnl,
                    position_id=closed.id,
                    cycle_id=cycle_id,
                    reason=f"Auto-closed: {close_reason} (Fee: ${float(fee):.4f})"
                )

                if not self.is_backtest:
                    from crypto_mas.services.alerting.telegram_bot import TelegramAlerter
                    alerter = TelegramAlerter.get_instance()
                    if alerter and alerter._enabled and alerter.loop:
                        import asyncio
                        try:
                            if close_reason == "STOP_LOSS":
                                asyncio.run_coroutine_threadsafe(
                                    alerter.alert_stop_loss(
                                        symbol=closed.symbol,
                                        stop_price=float(execution_price),
                                        realized_pnl=float(closed.realized_pnl),
                                        account=account.name,
                                    ),
                                    alerter.loop
                                )
                            else:
                                asyncio.run_coroutine_threadsafe(
                                    alerter.alert_position_closed(
                                        symbol=closed.symbol,
                                        exit_price=float(execution_price),
                                        realized_pnl=float(closed.realized_pnl),
                                        close_reason=close_reason,
                                        account=account.name,
                                    ),
                                    alerter.loop
                                )
                        except Exception as e:
                            logger.warning("Failed to send Telegram alert: %s", e)

                emoji = "🔴" if sl_hit else "🟢"
                self.reporter.log_execution(
                    account_name=account.name,
                    level="SUCCESS" if tp_hit else "WARN",
                    stage="SL_TP",
                    message=f"{emoji} {close_reason}: {closed.symbol} @ ${float(execution_price):.4f} | PnL: {pnl_pct:+.2f}%",
                    cycle_id=cycle_id,
                    payload={"reason": close_reason, "price": float(execution_price), "realized_pnl": float(closed.realized_pnl)},
                )

                executed.append(
                    PaperExecutionItem(
                        symbol=closed.symbol,
                        side=side_enum,
                        status=PaperExecutionStatus.EXECUTED,
                        target_weight=0.0,
                        notional=float(net_recovered),
                        price=float(execution_price),
                        quantity=float(closed.quantity),
                        reason=close_reason,
                    )
                )
                continue

            executed.append(
                PaperExecutionItem(
                    symbol=updated_position.symbol,
                    side=PaperOrderSide.BUY,
                    status=PaperExecutionStatus.EXECUTED,
                    target_weight=0.0,
                    notional=float(updated_position.notional_value),
                    price=float(updated_position.current_price),
                    quantity=float(updated_position.quantity),
                    reason="Position marked to latest close price.",
                )
            )
            self.reporter.log_execution(
                account_name=account.name,
                level="INFO",
                stage="PAPER_BROKER",
                message=f"M2M {updated_position.symbol} @ ${float(updated_position.current_price):.4f} | uPnL: ${float(updated_position.unrealized_pnl):.4f}",
                cycle_id=cycle_id,
                payload={"price": float(updated_position.current_price), "unrealized_pnl": float(updated_position.unrealized_pnl)}
            )

        open_positions_value = self._calculate_open_positions_value(account.name)
        ending_equity = self.risk_calculator._money(account.cash_balance + open_positions_value)

        updated_account = self.account_repository.update_balances(
            account=account,
            cash_balance=account.cash_balance,
            equity=ending_equity,
        )

        return PaperExecutionReport(
            account_name=account.name,
            exchange=exchange,
            starting_cash=float(starting_cash),
            ending_cash=float(updated_account.cash_balance),
            starting_equity=float(starting_equity),
            ending_equity=float(updated_account.equity),
            executed=executed,
            skipped=skipped,
            created_at=self.time_provider.now(),
        )
