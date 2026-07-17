from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from crypto_mas.domain.models.execution_log import ExecutionLog
from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.domain.models.order import Order
from crypto_mas.domain.models.trade import Trade
from crypto_mas.domain.repositories.execution_log_repository import ExecutionLogRepository
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.order_repository import OrderRepository
from crypto_mas.domain.repositories.paper_account_repository import PaperAccountRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.domain.repositories.trade_repository import TradeRepository
from crypto_mas.engine.portfolio import PortfolioTarget
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.market_data_service.schemas import Exchange
from crypto_mas.services.paper_trading.schemas import (
    PaperExecutionItem,
    PaperExecutionReport,
    PaperExecutionStatus,
    PaperOrderSide,
)


class PaperBrokerService:
    SL_PCT = {"scalping": 0.008, "swing": 0.03, "hodl": 0.05}
    TP_PCT = {"scalping": 0.006, "swing": 0.06, "hodl": 0.12}
    
    COMMISSION_RATE = Decimal("0.001") # 0.1%
    SLIPPAGE_RATE = Decimal("0.0005")  # 0.05%

    def __init__(
        self,
        db: Session,
        time_provider: TimeProvider | None = None,
        strategy_mode: str = "swing",
    ) -> None:
        self.db = db
        self.account_repository = PaperAccountRepository(db)
        self.position_repository = PositionRepository(db)
        self.feature_snapshot_repository = FeatureSnapshotRepository(db)
        self.trade_repository = TradeRepository(db)
        self.order_repository = OrderRepository(db)
        self.log_repository = ExecutionLogRepository(db)
        self.time_provider = time_provider or SystemTimeProvider()
        self.strategy_mode = strategy_mode

    def execute_target_portfolio(
        self,
        account_name: str,
        target: PortfolioTarget,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        account = self.account_repository.get_by_name(account_name)

        if account is None:
            raise ValueError(f"Paper account not found: {account_name}")

        starting_cash = account.cash_balance
        starting_equity = account.equity
        available_cash = account.cash_balance

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
                self._log_execution(
                    account_name=account.name,
                    level="INFO",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {target_position.symbol}: Open position already exists.",
                    cycle_id=cycle_id,
                    payload={"target_weight": target_position.target_weight}
                )
                continue

            latest_snapshot = self.feature_snapshot_repository.get_latest(
                exchange=target.exchange.value,
                symbol=target_position.symbol,
                timeframe=target.timeframe.value,
            )

            price = self._extract_close_price(latest_snapshot)

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
                self._log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {target_position.symbol}: Latest close price not available.",
                    cycle_id=cycle_id,
                    payload={"target_weight": target_position.target_weight}
                )
                continue

            target_notional = Decimal(str(target_position.target_weight)) * starting_equity

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
                self._log_execution(
                    account_name=account.name,
                    level="INFO",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {target_position.symbol}: Target notional is zero.",
                    cycle_id=cycle_id,
                    payload={"target_weight": target_position.target_weight, "price": float(price)}
                )
                continue

            fee = self._money(target_notional * self.COMMISSION_RATE)
            total_cost = target_notional + fee

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
                self._log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Rejected {side_enum.value} for {target_position.symbol}: Insufficient cash.",
                    cycle_id=cycle_id,
                    payload={"total_cost": float(total_cost), "available_cash": float(available_cash)}
                )
                continue

            if target_position.side == "LONG":
                execution_price = self._money(price * (Decimal("1") + self.SLIPPAGE_RATE))
            else:
                execution_price = self._money(price * (Decimal("1") - self.SLIPPAGE_RATE))
            quantity = self._money(target_notional / execution_price)

            # ── Dynamic SL/TP: ATR-based (falls back to fixed %) ──
            # ATR multipliers per mode: scalping tight, hodl wide
            ATR_SL_MULT = {"scalping": 1.5, "swing": 2.0, "hodl": 3.0}
            ATR_TP_MULT = {"scalping": 3.0, "swing": 4.0, "hodl": 6.0}

            stop_loss_price  = None
            take_profit_price = None

            try:
                atr_feature = self.feature_snapshot_repository.get_latest(
                    exchange=target.exchange.value,
                    symbol=target_position.symbol,
                    timeframe="15m" if self.strategy_mode == "scalping" else (
                        "4h" if self.strategy_mode == "swing" else "1d"
                    ),
                    end_time=now,
                )
                if atr_feature and atr_feature.features_json:
                    atr_val = atr_feature.features_json.get("atr_14")
                    if atr_val and atr_val > 0:
                        atr_d = Decimal(str(atr_val))
                        sl_mult = Decimal(str(ATR_SL_MULT.get(self.strategy_mode, 2.0)))
                        tp_mult = Decimal(str(ATR_TP_MULT.get(self.strategy_mode, 4.0)))
                        if target_position.side == "LONG":
                            stop_loss_price   = self._money(price - atr_d * sl_mult)
                            take_profit_price = self._money(price + atr_d * tp_mult)
                        else:
                            stop_loss_price   = self._money(price + atr_d * sl_mult)
                            take_profit_price = self._money(price - atr_d * tp_mult)
            except Exception:
                pass

            if stop_loss_price is None:  # Fallback to static %
                sl_pct = Decimal(str(self.SL_PCT.get(self.strategy_mode, 0.03)))
                tp_pct = Decimal(str(self.TP_PCT.get(self.strategy_mode, 0.06)))
                if target_position.side == "LONG":
                    stop_loss_price   = self._money(price * (1 - sl_pct))
                    take_profit_price = self._money(price * (1 + tp_pct))
                else:
                    stop_loss_price   = self._money(price * (1 + sl_pct))
                    take_profit_price = self._money(price * (1 - tp_pct))

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
                strategy_mode=self.strategy_mode,
                side=target_position.side,
            )

            trade = Trade(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=target_position.symbol,
                side=side_enum.value,
                quantity=quantity,
                price=execution_price,
                notional=target_notional, # Cost basis
                realized_pnl=Decimal("0") - fee, # Initial PnL is the fee paid
                position_id=position.id,
                cycle_id=cycle_id,
                reason=f"Paper {side_enum.value} executed (Fee: {float(fee):.4f})",
                executed_at=self.time_provider.now(),
            )
            self.trade_repository.add(trade)

            order = Order(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=target_position.symbol,
                side=side_enum.value,
                status="FILLED",
                requested_quantity=quantity,
                filled_quantity=quantity,
                requested_price=None,
                filled_price=execution_price,
                trade_id=trade.id,
            )
            self.order_repository.add(order)

            available_cash = self._money(available_cash - total_cost)

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
            self._log_execution(
                account_name=account.name,
                level="INFO",
                stage="PAPER_BROKER",
                message=f"{side_enum.value} {target_position.symbol} @ ${float(price):.4f} | SL=${float(stop_loss_price):.4f} TP=${float(take_profit_price):.4f}",
                cycle_id=cycle_id,
                payload={"notional": float(target_notional), "price": float(price), "quantity": float(quantity), "sl": float(stop_loss_price), "tp": float(take_profit_price)}
            )

        ending_equity = self._money(
            available_cash + self._calculate_open_positions_value(account.name)
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

    def _calculate_open_positions_value(self, account_name: str) -> Decimal:
        positions = self.position_repository.list_open_positions(account_name=account_name)

        return self._money(
            sum(
                (position.current_price * position.quantity for position in positions),
                Decimal("0"),
            )
        )

    def close_positions_not_in_target(
        self,
        account_name: str,
        target: PortfolioTarget,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        account = self.account_repository.get_by_name(account_name)

        if account is None:
            raise ValueError(f"Paper account not found: {account_name}")

        starting_cash = account.cash_balance
        starting_equity = account.equity

        target_symbols = {position.symbol for position in target.target_positions}
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
                self._log_execution(
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

            price = self._extract_close_price(latest_snapshot)
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
                self._log_execution(
                    account_name=account.name,
                    level="WARNING",
                    stage="PAPER_BROKER",
                    message=f"Skipped {side_enum.value} for {position.symbol}: Latest close price not available.",
                    cycle_id=cycle_id,
                )
                continue

            if position.side == "LONG":
                execution_price = self._money(price * (Decimal("1") - self.SLIPPAGE_RATE))
            else:
                execution_price = self._money(price * (Decimal("1") + self.SLIPPAGE_RATE))
            gross_notional = self._money(position.quantity * execution_price)
            fee = self._money(gross_notional * self.COMMISSION_RATE)
            net_recovered = gross_notional - fee
            
            # The close_position method records the trade. But wait, closed_position.realized_pnl is calculated inside repository based on exit_price.
            # We must pass execution_price to close_position!
            closed_position = self.position_repository.close_position(
                position=position,
                exit_price=execution_price,
                closed_at=self.time_provider.now(),
            )
            
            # Adjust realized PnL to account for exit fee
            closed_position.realized_pnl -= fee

            trade = Trade(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=closed_position.symbol,
                side=side_enum.value,
                quantity=closed_position.quantity,
                price=execution_price,
                notional=gross_notional,
                realized_pnl=closed_position.realized_pnl,
                position_id=closed_position.id,
                cycle_id=cycle_id,
                reason=f"Paper {side_enum.value} executed (Fee: ${float(fee):.4f})",
                executed_at=self.time_provider.now(),
            )
            self.trade_repository.add(trade)

            order = Order(
                account_name=account.name,
                exchange=target.exchange.value,
                symbol=closed_position.symbol,
                side=side_enum.value,
                status="FILLED",
                requested_quantity=closed_position.quantity,
                filled_quantity=closed_position.quantity,
                requested_price=None,
                filled_price=execution_price,
                trade_id=trade.id,
            )
            self.order_repository.add(order)

            available_cash = self._money(available_cash + net_recovered)

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
            self._log_execution(
                account_name=account.name,
                level="INFO",
                stage="PAPER_BROKER",
                message=f"Executed {side_enum.value} for {closed_position.symbol}.",
                cycle_id=cycle_id,
                payload={"notional": float(closed_position.notional_value), "price": float(price), "quantity": float(closed_position.quantity)}
            )

        open_positions_value = self._calculate_open_positions_value(account.name)
        ending_equity = self._money(available_cash + open_positions_value)

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

    @staticmethod
    def _extract_close_price(snapshot: FeatureSnapshot | None) -> Decimal | None:
        if snapshot is None:
            return None

        features: dict[str, Any] = snapshot.features_json
        value = features.get("close")

        if value is None:
            return None

        try:
            return Decimal(str(value))
        except Exception:
            return None

    def update_mark_prices(
        self,
        account_name: str,
        exchange: Exchange,
        timeframe: str,
        cycle_id: int | None = None,
    ) -> PaperExecutionReport:
        account = self.account_repository.get_by_name(account_name)

        if account is None:
            raise ValueError(f"Paper account not found: {account_name}")

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

            price = self._extract_close_price(latest_snapshot)

            if price is None or price <= Decimal("0"):
                executed.append(
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
                self._log_execution(
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
            )

            # --- Trailing Stop-Loss Update ---
            sl_pct = Decimal(str(self.SL_PCT.get(self.strategy_mode, 0.03)))
            
            if updated_position.side == "LONG":
                potential_sl = self._money(price * (Decimal("1") - sl_pct))
                
                # Only trail the stop loss UPWARDS, and only if the price has moved favorably (above entry)
                if updated_position.stop_loss_price is None or potential_sl > updated_position.stop_loss_price:
                    if price > updated_position.entry_price:
                        updated_position = self.position_repository.update_stop_loss(
                            position=updated_position,
                            stop_loss_price=potential_sl,
                        )
                        self._log_execution(
                            account_name=account.name,
                            level="INFO",
                            stage="TRAILING_SL",
                            message=f"Trailing SL moved UP for {updated_position.symbol} to ${float(potential_sl):.4f} (Locking profit)",
                            cycle_id=cycle_id,
                        )

                # --- Stop-Loss / Take-Profit Check ---
                sl_hit = (
                    updated_position.stop_loss_price is not None
                    and price <= updated_position.stop_loss_price
                )
                tp_hit = (
                    updated_position.take_profit_price is not None
                    and price >= updated_position.take_profit_price
                )
            else:
                potential_sl = self._money(price * (Decimal("1") + sl_pct))
                
                # Trail the stop loss DOWNWARDS, only if the price has moved favorably (below entry)
                if updated_position.stop_loss_price is None or potential_sl < updated_position.stop_loss_price:
                    if price < updated_position.entry_price:
                        updated_position = self.position_repository.update_stop_loss(
                            position=updated_position,
                            stop_loss_price=potential_sl,
                        )
                        self._log_execution(
                            account_name=account.name,
                            level="INFO",
                            stage="TRAILING_SL",
                            message=f"Trailing SL moved DOWN for {updated_position.symbol} to ${float(potential_sl):.4f} (Locking profit)",
                            cycle_id=cycle_id,
                        )

                # --- Stop-Loss / Take-Profit Check ---
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
                
                if position.side == "LONG":
                    execution_price = self._money(price * (Decimal("1") - self.SLIPPAGE_RATE))
                    pnl_pct = float((execution_price - position.entry_price) / position.entry_price * 100)
                else:
                    execution_price = self._money(price * (Decimal("1") + self.SLIPPAGE_RATE))
                    pnl_pct = float((position.entry_price - execution_price) / position.entry_price * 100)

                gross_notional = self._money(position.quantity * execution_price)
                fee = self._money(gross_notional * self.COMMISSION_RATE)
                net_recovered = gross_notional - fee
                
                closed = self.position_repository.close_position(
                    position=updated_position,
                    exit_price=execution_price,
                    closed_at=self.time_provider.now(),
                    close_reason=close_reason,
                )
                
                # Adjust realized PnL to account for exit fee
                closed.realized_pnl -= fee

                # Return cash to account
                new_cash = self._money(account.cash_balance + net_recovered)
                account.cash_balance = new_cash
                self.db.commit()

                # Log the closure trade
                side_enum = PaperOrderSide.SELL if position.side == "LONG" else PaperOrderSide.BUY
                trade = Trade(
                    account_name=account.name,
                    exchange=exchange.value,
                    symbol=closed.symbol,
                    side=side_enum.value,
                    quantity=closed.quantity,
                    price=execution_price,
                    notional=gross_notional,
                    realized_pnl=closed.realized_pnl,
                    position_id=closed.id,
                    cycle_id=cycle_id,
                    reason=f"Auto-closed: {close_reason} (Fee: ${float(fee):.4f})",
                    executed_at=self.time_provider.now(),
                )
                self.trade_repository.add(trade)

                emoji = "🔴" if sl_hit else "🟢"
                self._log_execution(
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
            self._log_execution(
                account_name=account.name,
                level="INFO",
                stage="PAPER_BROKER",
                message=f"M2M {updated_position.symbol} @ ${float(updated_position.current_price):.4f} | uPnL: ${float(updated_position.unrealized_pnl):.4f}",
                cycle_id=cycle_id,
                payload={"price": float(updated_position.current_price), "unrealized_pnl": float(updated_position.unrealized_pnl)}
            )

        open_positions_value = self._calculate_open_positions_value(account.name)
        ending_equity = self._money(account.cash_balance + open_positions_value)

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

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.00000001"))

    @staticmethod
    def _zero_if_tiny(value: Decimal) -> Decimal:
        if abs(value) < Decimal("0.00000001"):
            return Decimal("0.00000000")

        return value.quantize(Decimal("0.00000001"))

    def _log_execution(
        self,
        account_name: str,
        level: str,
        stage: str,
        message: str,
        cycle_id: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        log = ExecutionLog(
            account_name=account_name,
            cycle_id=cycle_id,
            level=level,
            stage=stage,
            message=message,
            payload_json=payload,
            created_at=self.time_provider.now(),
        )
        self.log_repository.add(log)
