import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from crypto_mas.engine.portfolio import PortfolioTarget
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTask:
    account_name: str
    target: PortfolioTarget
    cycle_id: int | None


class OrderExecutorQueue:
    _instance: Optional["OrderExecutorQueue"] = None

    def __init__(self):
        self.queue: asyncio.Queue[ExecutionTask] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None
        self._broker_factory = None
        self.sync_mode: bool = False

    @classmethod
    def get_instance(cls) -> "OrderExecutorQueue":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_broker_factory(self, broker_factory):
        """Allows lazy initialization of the broker service."""
        self._broker_factory = broker_factory

    def enqueue(self, account_name: str, target: PortfolioTarget, cycle_id: int | None = None) -> None:
        """Puts a portfolio target into the async execution queue. If sync_mode is True, executes immediately."""
        task = ExecutionTask(account_name=account_name, target=target, cycle_id=cycle_id)
        
        if self.sync_mode:
            logger.debug(f"Executing execution task synchronously for cycle {cycle_id}")
            self._execute_task_sync(task)
            return

        self.queue.put_nowait(task)
        logger.debug(f"Enqueued execution task for cycle {cycle_id}, account {account_name}")

    def _execute_task_sync(self, task: ExecutionTask) -> None:
        if self._broker_factory is None:
            logger.error("Broker factory not set on OrderExecutorQueue.")
            return
            
        broker = self._broker_factory()
        db = broker.db
        from crypto_mas.domain.repositories.trading_cycle_repository import TradingCycleRepository
        cycle_repo = TradingCycleRepository(db)
        
        broker.update_mark_prices(
            account_name=task.account_name,
            exchange=task.target.exchange,
            timeframe=task.target.timeframe.value,
            cycle_id=task.cycle_id,
        )
        
        if broker.strategy_mode != "scalping":
            close_report = broker.close_positions_not_in_target(
                account_name=task.account_name,
                target=task.target,
                cycle_id=task.cycle_id,
            )
        else:
            from crypto_mas.services.paper_trading.schemas import PaperExecutionReport
            account_model = broker.account_repository.get_by_name(task.account_name)
            start_eq = account_model.cash_balance + broker._calculate_open_positions_value(task.account_name)
            close_report = PaperExecutionReport(
                account_name=task.account_name,
                exchange=task.target.exchange,
                starting_cash=float(account_model.cash_balance),
                ending_cash=float(account_model.cash_balance),
                starting_equity=float(start_eq),
                ending_equity=float(start_eq),
                executed=[],
                skipped=[],
                created_at=broker.time_provider.now()
            )
        
        execute_report = broker.execute_target_portfolio(
            account_name=task.account_name,
            target=task.target,
            cycle_id=task.cycle_id,
        )
        
        if task.cycle_id:
            cycle = cycle_repo.get_by_id(task.cycle_id)
            if cycle:
                cycle.trades_executed = len(close_report.executed) + len(execute_report.executed)
                cycle.starting_equity = close_report.starting_equity
                cycle.ending_equity = execute_report.ending_equity
                cycle.cycle_pnl = cycle.ending_equity - cycle.starting_equity
                cycle.status = "COMPLETED"
                cycle.finished_at = broker.time_provider.now()
                if not self.sync_mode:
                    db.commit()

    async def worker(self) -> None:
        """Background task that processes the queue sequentially."""
        logger.info("OrderExecutorQueue worker started.")
        while True:
            try:
                task = await self.queue.get()
                
                logger.info(f"Executing queue task for cycle {task.cycle_id}")
                
                # Fetch a new DB session and broker for this isolated execution context
                if self._broker_factory is None:
                    logger.error("Broker factory not set on OrderExecutorQueue.")
                    self.queue.task_done()
                    continue

                broker: PaperBrokerService = self._broker_factory()
                
                # Execute synchronously inside a thread pool
                loop = asyncio.get_running_loop()
                def sync_execute(task=task, broker=broker):
                    db = broker.db
                    from crypto_mas.domain.repositories.trading_cycle_repository import (
                        TradingCycleRepository,
                    )
                    cycle_repo = TradingCycleRepository(db)
                    
                    broker.update_mark_prices(
                        account_name=task.account_name,
                        exchange=task.target.exchange,
                        timeframe=task.target.timeframe.value,
                        cycle_id=task.cycle_id,
                    )
                    
                    if broker.strategy_mode != "scalping":
                        close_report = broker.close_positions_not_in_target(
                            account_name=task.account_name,
                            target=task.target,
                            cycle_id=task.cycle_id,
                        )
                    else:
                        from crypto_mas.services.paper_trading.schemas import PaperExecutionReport
                        account_model = broker.account_repository.get_by_name(task.account_name)
                        start_eq = account_model.cash_balance + broker._calculate_open_positions_value(task.account_name)
                        close_report = PaperExecutionReport(
                            account_name=task.account_name,
                            exchange=task.target.exchange,
                            starting_cash=float(account_model.cash_balance),
                            ending_cash=float(account_model.cash_balance),
                            starting_equity=float(start_eq),
                            ending_equity=float(start_eq),
                            executed=[],
                            skipped=[],
                            created_at=broker.time_provider.now()
                        )
                    
                    execute_report = broker.execute_target_portfolio(
                        account_name=task.account_name,
                        target=task.target,
                        cycle_id=task.cycle_id,
                    )
                    
                    if task.cycle_id:
                        cycle = cycle_repo.get_by_id(task.cycle_id)
                        if cycle:
                            cycle.trades_executed = len(close_report.executed) + len(execute_report.executed)
                            cycle.starting_equity = close_report.starting_equity
                            cycle.ending_equity = execute_report.ending_equity
                            cycle.cycle_pnl = cycle.ending_equity - cycle.starting_equity
                            cycle.status = "COMPLETED"
                            cycle.finished_at = broker.time_provider.now()
                            db.commit()
                
                await loop.run_in_executor(None, sync_execute)
                
                logger.info(f"Execution completed for cycle {task.cycle_id}")
                self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("OrderExecutorQueue worker cancelled.")
                break
            except Exception as e:
                logger.exception(f"Error executing queued target: {e}")
                self.queue.task_done()

    def start(self) -> None:
        """Starts the worker task if not already running."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self.worker())

    def stop(self) -> None:
        """Stops the worker task."""
        if self._worker_task is not None and not self._worker_task.done():
            self._worker_task.cancel()
