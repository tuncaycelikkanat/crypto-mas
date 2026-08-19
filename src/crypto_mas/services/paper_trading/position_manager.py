import logging
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.engine.portfolio import PortfolioTarget
from crypto_mas.infrastructure.time.time_provider import TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange
from crypto_mas.services.paper_trading.execution_reporter import ExecutionReporter
from crypto_mas.services.paper_trading.mark_to_market import MarkToMarket
from crypto_mas.services.paper_trading.risk_calculator import RiskCalculator
from crypto_mas.services.paper_trading.schemas import (
    PaperExecutionItem,
    PaperExecutionReport,
    PaperExecutionStatus,
    PaperOrderSide,
)

logger = logging.getLogger(__name__)

class PositionManager:
    def __init__(
        self, 
        db: Session, 
        risk_calculator: RiskCalculator, 
        reporter: ExecutionReporter, 
        mark_to_market: MarkToMarket,
        time_provider: TimeProvider,
        is_backtest: bool = False
    ):
        self.db = db
        self.risk_calculator = risk_calculator
        self.reporter = reporter
        self.mark_to_market = mark_to_market
        self.time_provider = time_provider
        self.is_backtest = is_backtest
        self.account_repository = PaperAccountRepository(db)
        self.position_repository = PositionRepository(db)
        self.feature_snapshot_repository = FeatureSnapshotRepository(db)

    def execute_target_portfolio(
        self,
        account: Any,
        target: PortfolioTarget,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        starting_cash = account.cash_balance
        starting_equity = account.equity
        available_cash = account.cash_balance

        now = self.time_provider.now()
        cooldown_sl_symbols = self.position_repository.get_recent_stop_loss_symbols(
            account_name=account.name,
            exchange=target.exchange.value,
            time_now=now,
            cooldown_minutes=120,
        )
        whipsaw_symbols = self.position_repository.get_whipsaw_cooldown_symbols(
            account_name=account.name,
            exchange=target.exchange.value,
            time_now=now,
            min_stop_count=2,
            cooldown_minutes=2880,
        ) if hasattr(self.position_repository, "get_whipsaw_cooldown_symbols") else set()

        executed: list[PaperExecutionItem] = []
        skipped: list[PaperExecutionItem] = []

        for target_position in target.target_positions:
            existing_position = self.position_repository.get_open_position(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=target_position.symbol,
            )

            side_enum = PaperOrderSide.BUY if target_position.side == "LONG" else PaperOrderSide.SELL
            if existing_position is not None:
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=side_enum,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=target_position.target_weight,
                        notional=0.0,
                        price=float(existing_position.current_price),
                        quantity=float(existing_position.quantity),
                        reason="Open position already exists.",
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="INFO",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {target_position.symbol}: Open position already exists.",
                    cycle_id=cycle_id,
                    payload={"target_weight": target_position.target_weight}
                )
                continue

            if target_position.symbol in cooldown_sl_symbols or target_position.symbol in whipsaw_symbols:
                cooldown_reason = (
                    "Symbol in Stop-Loss Cooldown (120m)."
                    if target_position.symbol in cooldown_sl_symbols
                    else "Symbol in Whipsaw Cooldown (48h)."
                )
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=side_enum,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=target_position.target_weight,
                        notional=0.0,
                        price=None,
                        quantity=None,
                        reason=cooldown_reason,
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {target_position.symbol}: {cooldown_reason}",
                    cycle_id=cycle_id,
                    payload={"target_weight": target_position.target_weight}
                )
                continue

            latest_snapshot = self.feature_snapshot_repository.get_latest(
                exchange=target.exchange.value,
                symbol=target_position.symbol,
                timeframe=target.timeframe.value,
                end_time=self.time_provider.now(),
            )

            price = self.risk_calculator.extract_close_price(latest_snapshot)

            if price is None or price <= Decimal("0"):
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=side_enum,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=target_position.target_weight,
                        notional=0.0,
                        price=None,
                        quantity=None,
                        reason="Latest close price not available.",
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {target_position.symbol}: Latest close price not available.",
                    cycle_id=cycle_id,
                    payload={"target_weight": target_position.target_weight}
                )
                continue

            is_risky, reason_msg = self.risk_calculator.is_thin_liquidity_or_excessive_spread(latest_snapshot)
            if is_risky:
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=side_enum,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=target_position.target_weight,
                        notional=0.0,
                        price=float(price),
                        quantity=0.0,
                        reason=f"ABORT_THIN_LIQUIDITY: {reason_msg}",
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {target_position.symbol}: ABORT_THIN_LIQUIDITY — {reason_msg}.",
                    cycle_id=cycle_id,
                    payload={"target_weight": target_position.target_weight, "reason": reason_msg}
                )
                continue

            target_notional = self.risk_calculator.calculate_target_notional(target_position.target_weight, starting_equity)

            if target_notional <= Decimal("0"):
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=side_enum,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=target_position.target_weight,
                        notional=float(target_notional),
                        price=float(price),
                        quantity=None,
                        reason="Target notional is zero.",
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="INFO",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {target_position.symbol}: Target notional is zero.",
                    cycle_id=cycle_id,
                    payload={"target_weight": target_position.target_weight, "price": float(price)}
                )
                continue

            total_cost, fee = self.risk_calculator.calculate_total_cost(target_notional)

            if total_cost > available_cash:
                skipped.append(
                    PaperExecutionItem(
                        symbol=target_position.symbol,
                        side=side_enum,
                        status=PaperExecutionStatus.REJECTED,
                        target_weight=target_position.target_weight,
                        notional=float(total_cost),
                        price=float(price),
                        quantity=None,
                        reason="Insufficient paper cash balance for notional + fee.",
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Rejected {side_enum.value} for {target_position.symbol}: Insufficient cash.",
                    cycle_id=cycle_id,
                    payload={"total_cost": float(total_cost), "available_cash": float(available_cash)}
                )
                continue

            execution_price = self.risk_calculator.calculate_execution_price(price, target_position.side)
            quantity = self.risk_calculator.calculate_quantity(target_notional, execution_price)

            atr_val = None
            try:
                atr_feature = self.feature_snapshot_repository.get_latest(
                    exchange=target.exchange.value,
                    symbol=target_position.symbol,
                    timeframe="15m" if self.risk_calculator.strategy_mode == "scalping" else (
                        "4h" if self.risk_calculator.strategy_mode == "swing" else "1d"
                    ),
                    end_time=self.time_provider.get_time(),
                )
                if atr_feature and atr_feature.features_json:
                    atr_val = atr_feature.features_json.get("atr_14")
            except Exception:
                pass
                
            override_sl = target_position.metadata.get("sl_mult_override") if hasattr(target_position, "metadata") else None
            override_tp = target_position.metadata.get("tp_mult_override") if hasattr(target_position, "metadata") else None
            
            stop_loss_price, take_profit_price = self.risk_calculator.calculate_sl_tp(
                price, target_position.side, atr_val, override_sl, override_tp
            )

            position = self.position_repository.create_open_position(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=target_position.symbol,
                quantity=quantity,
                entry_price=price,
                notional_value=target_notional,
                opened_at=self.time_provider.now(),
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                strategy_mode=self.risk_calculator.strategy_mode,
                side=target_position.side,
                skip_commit=self.is_backtest,
            )

            realized_pnl = Decimal("0") - fee
            
            self.reporter.record_trade_and_order(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=target_position.symbol,
                side=side_enum.value,
                quantity=quantity,
                execution_price=execution_price,
                notional=target_notional,
                realized_pnl=realized_pnl,
                position_id=position.id,
                cycle_id=cycle_id,
                reason=f"Paper {side_enum.value} executed (Fee: {float(fee):.4f})"
            )

            available_cash = self.risk_calculator._money(available_cash - total_cost)

            if not self.is_backtest:
                from crypto_mas.services.alerting.telegram_bot import TelegramAlerter
                alerter = TelegramAlerter.get_instance()
                if alerter and alerter._enabled and alerter.loop:
                    import asyncio
                    try:
                        asyncio.run_coroutine_threadsafe(
                            alerter.alert_position_opened(
                                symbol=position.symbol,
                                entry_price=float(position.entry_price),
                                quantity=float(position.quantity),
                                strategy=self.risk_calculator.strategy_mode or "multi_agent",
                                account=account.name,
                            ),
                            alerter.loop
                        )
                    except Exception as e:
                        logger.warning("Failed to send Telegram alert: %s", e)

            executed.append(
                PaperExecutionItem(
                    symbol=target_position.symbol,
                    side=side_enum,
                    status=PaperExecutionStatus.EXECUTED,
                    target_weight=target_position.target_weight,
                    notional=float(target_notional),
                    price=float(execution_price),
                    quantity=float(quantity),
                    reason=f"Paper {side_enum.value} executed with slippage/fee. Fee: ${float(fee):.4f}",
                )
            )
            self.reporter.log_execution(
                account_name=account.name,
                level="INFO",
                stage="PAPER_BROKER",
                message=f"{side_enum.value} {target_position.symbol} @ ${float(price):.4f} | SL=${float(stop_loss_price):.4f} TP=${float(take_profit_price):.4f}",
                cycle_id=cycle_id,
                payload={"notional": float(target_notional), "price": float(price), "quantity": float(quantity), "sl": float(stop_loss_price), "tp": float(take_profit_price)}
            )

        if self.is_backtest:
            account.cash_balance = available_cash
            account.equity = self.risk_calculator._money(available_cash + self.mark_to_market._calculate_open_positions_value(account.name))
            updated_account = account
        else:
            ending_equity = self.risk_calculator._money(
                available_cash + self.mark_to_market._calculate_open_positions_value(account.name)
            )
            updated_account = self.account_repository.update_balances(
                account=account,
                cash_balance=available_cash,
                equity=ending_equity,
            )

        return PaperExecutionReport(
            account_name=account.name,
            exchange=Exchange(target.exchange.value),
            starting_cash=float(starting_cash),
            ending_cash=float(updated_account.cash_balance),
            starting_equity=float(starting_equity),
            ending_equity=float(updated_account.equity),
            executed=executed,
            skipped=skipped,
            created_at=self.time_provider.now(),
        )

    def close_positions_not_in_target(
        self,
        account: Any,
        target: PortfolioTarget,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        starting_cash = account.cash_balance
        starting_equity = account.equity

        open_positions = self.position_repository.list_open_positions(account_name=account.name)

        available_cash = account.cash_balance
        executed: list[PaperExecutionItem] = []
        skipped: list[PaperExecutionItem] = []

        for position in open_positions:
            target_pos = next((p for p in target.target_positions if p.symbol == position.symbol), None)
            if target_pos and target_pos.side == position.side:
                skipped.append(
                    PaperExecutionItem(
                        symbol=position.symbol,
                        side=PaperOrderSide.SELL if position.side == "LONG" else PaperOrderSide.BUY,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=0.0,
                        notional=float(position.notional_value),
                        price=float(position.current_price),
                        quantity=float(position.quantity),
                        reason="Position is still present in target portfolio.",
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="INFO",
                    stage="PAPER_BROKER",
                    message=f"Skipped close for {position.symbol}: Position is still in target portfolio with same side.",
                    cycle_id=cycle_id,
                )
                continue

            latest_snapshot = self.feature_snapshot_repository.get_latest(
                exchange=target.exchange.value,
                symbol=position.symbol,
                timeframe=target.timeframe.value,
                end_time=self.time_provider.now(),
            )

            price = self.risk_calculator.extract_close_price(latest_snapshot)
            side_enum = PaperOrderSide.SELL if position.side == "LONG" else PaperOrderSide.BUY

            if price is None or price <= Decimal("0"):
                skipped.append(
                    PaperExecutionItem(
                        symbol=position.symbol,
                        side=side_enum,
                        status=PaperExecutionStatus.SKIPPED,
                        target_weight=0.0,
                        notional=float(position.notional_value),
                        price=None,
                        quantity=float(position.quantity),
                        reason=f"Latest close price not available for paper {side_enum.value}.",
                    )
                )
                self.reporter.log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {position.symbol}: Latest close price not available.",
                    cycle_id=cycle_id,
                )
                continue

            execution_price = self.risk_calculator.calculate_exit_price(price, position.side)
            raw_realized_pnl, _ = self.risk_calculator.calculate_pnl(position.entry_price, execution_price, position.quantity, position.side)
                
            gross_notional = self.risk_calculator._money(position.quantity * execution_price)
            fee = self.risk_calculator.calculate_fee(gross_notional)
            
            net_recovered = self.risk_calculator._money((position.quantity * position.entry_price) + raw_realized_pnl - fee)
            
            # Determine real close reason if provided by the strategy
            strategy_reason = target.metadata.get("close_reasons", {}).get(position.symbol)
            if strategy_reason:
                close_reason_msg = f"{strategy_reason} (Fee: ${float(fee):.4f})"
            else:
                close_reason_msg = f"Closed by PortfolioEngine (Fee: ${float(fee):.4f})"

            closed_position = self.position_repository.close_position(
                position=position,
                exit_price=execution_price,
                closed_at=self.time_provider.now(),
                close_reason=close_reason_msg,
                skip_commit=self.is_backtest,
            )
            
            closed_position.realized_pnl -= fee

            self.reporter.record_trade_and_order(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=closed_position.symbol,
                side=side_enum.value,
                quantity=closed_position.quantity,
                execution_price=execution_price,
                notional=gross_notional,
                realized_pnl=closed_position.realized_pnl,
                position_id=closed_position.id,
                cycle_id=cycle_id,
                reason=close_reason_msg
            )

            if not self.is_backtest:
                from crypto_mas.services.alerting.telegram_bot import TelegramAlerter
                alerter = TelegramAlerter.get_instance()
                if alerter and alerter._enabled and alerter.loop:
                    import asyncio
                    try:
                        asyncio.run_coroutine_threadsafe(
                            alerter.alert_position_closed(
                                symbol=closed_position.symbol,
                                exit_price=float(execution_price),
                                realized_pnl=float(closed_position.realized_pnl),
                                close_reason="REBALANCING",
                                account=account.name,
                            ),
                            alerter.loop
                        )
                    except Exception as e:
                        logger.warning("Failed to send Telegram alert: %s", e)

            available_cash = self.risk_calculator._money(available_cash + net_recovered)

            executed.append(
                PaperExecutionItem(
                    symbol=closed_position.symbol,
                    side=side_enum,
                    status=PaperExecutionStatus.EXECUTED,
                    target_weight=0.0,
                    notional=float(net_recovered),
                    price=float(execution_price),
                    quantity=float(closed_position.quantity),
                    reason=f"Paper {side_enum.value} executed because position is not in target portfolio.",
                )
            )
            self.reporter.log_execution(
                account_name=account.name,
                level="INFO",
                stage="PAPER_BROKER",
                message=f"Executed {side_enum.value} for {closed_position.symbol}.",
                cycle_id=cycle_id,
                payload={"notional": float(closed_position.notional_value), "price": float(price), "quantity": float(closed_position.quantity)}
            )

        open_positions_value = self.mark_to_market._calculate_open_positions_value(account.name)
        ending_equity = self.risk_calculator._money(available_cash + open_positions_value)

        updated_account = self.account_repository.update_balances(
            account=account,
            cash_balance=available_cash,
            equity=ending_equity,
        )

        return PaperExecutionReport(
            account_name=account.name,
            exchange=target.exchange,
            starting_cash=float(starting_cash),
            ending_cash=float(updated_account.cash_balance),
            starting_equity=float(starting_equity),
            ending_equity=float(updated_account.equity),
            executed=executed,
            skipped=skipped,
            created_at=self.time_provider.now(),
        )
