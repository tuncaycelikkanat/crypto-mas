import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.trading_cycle_repository import TradingCycleRepository
from crypto_mas.engine.portfolio.portfolio import PortfolioEngine
from crypto_mas.engine.regime.htf_manager import HTFRegimeManager
from crypto_mas.engine.risk.risk import RiskEngine
from crypto_mas.engine.strategy.factory import StrategyFactory
from crypto_mas.infrastructure.time.time_provider import SystemTimeProvider, TimeProvider
from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.interfaces import MarketDataProvider
from crypto_mas.services.market_data_service.schemas import Timeframe
from crypto_mas.services.paper_trading.paper_broker import PaperBrokerService
from crypto_mas.services.gainers_service import fetch_gainers, fetch_hidden_gems

logger = logging.getLogger(__name__)


class TradingCycleService:
    def __init__(
        self,
        db: Session,
        market_provider: MarketDataProvider,
        time_provider: TimeProvider | None = None,
        strategy_mode: str = "swing",
        candle_repo = None,
        feature_repo = None,
        ws_client = None,
    ) -> None:
        self.db = db
        self.time_provider = time_provider or SystemTimeProvider()
        self.strategy_mode = strategy_mode
        self.ws_client = ws_client

        self.cycle_repository = TradingCycleRepository(db)
        self.feature_snapshot_repository = feature_repo or FeatureSnapshotRepository(db)

        self.fetcher_service = HistoricalFetcherService(provider=market_provider, db=db)
        self.feature_service = FeaturePipelineService(
            db, 
            candle_repo=candle_repo, 
            feature_repo=self.feature_snapshot_repository
        )

        self.portfolio_engine = PortfolioEngine(time_provider=self.time_provider)
        self.risk_engine = RiskEngine()
        self.paper_broker = PaperBrokerService(
            db=db,
            time_provider=self.time_provider,
            strategy_mode=strategy_mode,
        )
        self.htf_manager = HTFRegimeManager()

    async def run_cycle(
        self,
        account_name: str,
        symbols: list[str],
        timeframe: Timeframe,
        strategy_name: str = "multi_agent",
        trigger: str = "MANUAL",
        risk_level: int = 50,
    ) -> TradingCycle:
        now = self.time_provider.now()
        strategy = StrategyFactory.create(strategy_name, time_provider=self.time_provider)
        
        if "AUTO_GAINERS" in symbols:
            try:
                # Calculate minimum volume dynamically based on risk_level (0-100)
                # Risk 0 -> 500,000 | Risk 50 -> 252,500 | Risk 100 -> 5,000
                min_vol = max(5_000, 500_000 - (risk_level * 4950))
                gainer_data = await fetch_gainers(exchange=self.fetcher_service.provider.exchange.value, limit=50, only_pump=True, min_volume_usdt=min_vol)
                auto_symbols = [item["symbol"] for item in gainer_data.get("pumpwatch", [])]
                if not auto_symbols:
                    auto_symbols = [item["symbol"] for item in gainer_data.get("gainers", [])]
                if auto_symbols:
                    symbols = auto_symbols
                    if self.ws_client:
                        for sym in symbols:
                            self.ws_client.add_subscription(sym, "trade")
                else:
                    symbols = ["BTCUSDT", "ETHUSDT"] # Fallback
            except Exception as e:
                logger.error(f"Failed to fetch auto gainers: {e}")
                if len(symbols) == 1:
                    symbols = ["BTCUSDT", "ETHUSDT"] # Fallback
                else:
                    symbols = [s for s in symbols if s != "AUTO_GAINERS"]
                    
        elif "HIDDEN_GEMS" in symbols:
            try:
                # Risk 0 -> requires slightly higher volume? Or we just use fixed thresholds for hidden gems.
                # Since hidden gems implies low volume, we can use a baseline.
                min_vol = 50_000
                max_vol = 5_000_000
                gem_data = await fetch_hidden_gems(exchange=self.fetcher_service.provider.exchange.value, limit=50, min_volume_usdt=min_vol, max_volume_usdt=max_vol)
                auto_symbols = [item["symbol"] for item in gem_data.get("hidden_gems", [])]
                if auto_symbols:
                    symbols = auto_symbols
                    if self.ws_client:
                        for sym in symbols:
                            self.ws_client.add_subscription(sym, "trade")
                else:
                    symbols = ["BTCUSDT", "ETHUSDT"] # Fallback
            except Exception as e:
                logger.error(f"Failed to fetch hidden gems: {e}")
                if len(symbols) == 1:
                    symbols = ["BTCUSDT", "ETHUSDT"] # Fallback
                else:
                    symbols = [s for s in symbols if s != "HIDDEN_GEMS"]
        
        # 1. Initialize Cycle
        cycle = TradingCycle(
            account_name=account_name,
            exchange=self.fetcher_service.provider.exchange.value,
            timeframe=timeframe.value,
            status="RUNNING",
            trigger=trigger,
            started_at=now,
        )
        self.cycle_repository.add(cycle)
        self.db.commit()
        
        def _log(stage: str, message: str, level: str = "INFO", payload: dict | None = None):
            from crypto_mas.domain.models.execution_log import ExecutionLog
            log = ExecutionLog(
                account_name=account_name,
                cycle_id=cycle.id,
                level=level,
                stage=stage,
                message=message,
                payload_json=payload,
                created_at=self.time_provider.now()
            )
            self.db.add(log)

        _log("INIT", f"Cycle started for {len(symbols)} symbols: {symbols}", payload={
            "cycle_id": cycle.id,
            "account": account_name,
            "symbols": symbols,
            "strategy": strategy_name,
            "trigger": trigger,
            "time": now.isoformat(),
        })

        try:
            # 2. Market Data Sync
            logger.info(f"[Cycle {cycle.id}] Starting market data sync for {len(symbols)} symbols.")
            _log("MARKET_DATA", f"Fetching history from {self.fetcher_service.provider.exchange.value} for {timeframe}")
            
            # Ensure BTCUSDT is in the fetch list for market-wide correlation checks
            fetch_symbols = set(symbols)
            fetch_symbols.add("BTCUSDT")
            fetch_symbols_list = list(fetch_symbols)
            
            # Fetch up to 60 periods back as a fallback if no state exists
            fallback_start = now - self._get_timedelta(timeframe) * 60
            
            await self.fetcher_service.backfill_universe(
                symbols=fetch_symbols_list,
                timeframe=timeframe,
                start_time=fallback_start,
                end_time=now,
            )
            
            # Fetch HTF data if we are trading on a lower timeframe
            htf_map = {
                Timeframe.ONE_MINUTE: Timeframe.FOUR_HOURS,
                Timeframe.FIFTEEN_MINUTES: Timeframe.FOUR_HOURS,
                Timeframe.ONE_HOUR: Timeframe.ONE_DAY,
                Timeframe.FOUR_HOURS: Timeframe.ONE_WEEK,
                Timeframe.ONE_DAY: Timeframe.ONE_MONTH,
            }
            htf = htf_map.get(timeframe)
            
            if htf:
                _log("MARKET_DATA", f"Fetching HTF ({htf.value}) history for Regime Filter")
                htf_start = now - self._get_timedelta(htf) * 60
                await self.fetcher_service.backfill_universe(
                    symbols=fetch_symbols_list,
                    timeframe=htf,
                    start_time=htf_start,
                    end_time=now,
                )
                
            # Pre-calculate BTC features for market-wide check
            self.feature_service.calculate_and_store(
                exchange=self.fetcher_service.provider.exchange,
                symbol="BTCUSDT",
                timeframe=timeframe,
                end_time=now,
                limit=1000,
            )
            btc_snapshots = self.feature_snapshot_repository.list_by_symbol(
                exchange=self.fetcher_service.provider.exchange.value,
                symbol="BTCUSDT",
                timeframe=timeframe.value,
                limit=5,
            )
            
            btc_is_crashing = False
            if btc_snapshots:
                latest_btc = btc_snapshots[-1].features_json
                btc_roc = latest_btc.get("roc_14")
                if btc_roc is not None and btc_roc < -2.0: # BTC dropped > 2% in the last 14 periods
                    btc_is_crashing = True
                    _log("RISK", f"MARKET CRASH DETECTED! BTC ROC: {btc_roc:.2f}%. Longs will be restricted.", "WARN")
            
            # 3 & 4. Feature Engineering and Decisions
            decisions = []
            for symbol in symbols:
                logger.info(f"[Cycle {cycle.id}] Processing features and decisions for {symbol}")
                _log("STRATEGY", f"Evaluating {strategy_name} for {symbol}")
                
                # Calculate features
                self.feature_service.calculate_and_store(
                    exchange=self.fetcher_service.provider.exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    end_time=now,
                    limit=1000,
                )
                
                # Get latest snapshots
                snapshots = self.feature_snapshot_repository.list_by_symbol(
                    exchange=self.fetcher_service.provider.exchange.value,
                    symbol=symbol,
                    timeframe=timeframe.value,
                    limit=100,
                )
                
                if not snapshots:
                    logger.warning(f"[Cycle {cycle.id}] No feature snapshots for {symbol}. Skipping.")
                    _log("STRATEGY", f"No data available for {symbol}, skipped", "WARN")
                    continue
                
                # Check HTF Filter
                htf_long_allowed = True
                htf_short_allowed = True
                if htf:
                    self.feature_service.calculate_and_store(
                        exchange=self.fetcher_service.provider.exchange,
                        symbol=symbol,
                        timeframe=htf,
                    )
                    htf_snapshots = self.feature_snapshot_repository.list_by_symbol(
                        exchange=self.fetcher_service.provider.exchange.value,
                        symbol=symbol,
                        timeframe=htf.value,
                        limit=5,
                    )
                    htf_long_allowed = self.htf_manager.is_long_allowed(htf_snapshots)
                    htf_short_allowed = self.htf_manager.is_short_allowed(htf_snapshots)
                
                # Decision
                decision = strategy.decide(
                    exchange=self.fetcher_service.provider.exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    snapshots=snapshots,
                    risk_level=risk_level,
                )
                
                if decision:
                    # Apply HTF filter overrides
                    from crypto_mas.engine.strategy.schemas import DecisionAction
                    
                    if decision.action == DecisionAction.CONSIDER_LONG:
                        if btc_is_crashing and symbol != "BTCUSDT":
                            _log("STRATEGY", f"Decision CONSIDER_LONG for {symbol} REJECTED due to general BTC market crash.", "WARN")
                            decision.action = DecisionAction.HOLD
                            decision.reason += " | REJECTED by BTC Crash Filter"
                        elif not htf_long_allowed:
                            _log("STRATEGY", f"Decision CONSIDER_LONG for {symbol} REJECTED by HTF ({htf.value}) Bear Trend filter.", "WARN")
                            decision.action = DecisionAction.HOLD
                            decision.reason += f" | REJECTED by HTF {htf.value} Bear Trend"
                            
                    elif decision.action == DecisionAction.CONSIDER_SHORT and not htf_short_allowed:
                        _log("STRATEGY", f"Decision CONSIDER_SHORT for {symbol} REJECTED by HTF ({htf.value}) Bull Trend filter.", "WARN")
                        decision.action = DecisionAction.HOLD
                        decision.reason += f" | REJECTED by HTF {htf.value} Bull Trend"
                        
                    latest_snap = snapshots[-1].features_json if snapshots else {}
                    
                    if decision.action != DecisionAction.HOLD:
                        decisions.append(decision)
                        # Build rich feature payload from the latest snapshot
                        _log(
                            "STRATEGY",
                            f"Decision made for {symbol}: {decision.action.value} (Confidence: {decision.confidence:.4f})",
                            payload={
                                "symbol": symbol,
                                "action": decision.action.value,
                                "confidence": round(decision.confidence, 4),
                                "score": {
                                    "final_score": round(decision.score.final_score, 4),
                                    "trend_score": round(decision.score.trend_score, 4),
                                    "momentum_score": round(decision.score.momentum_score, 4),
                                    "volatility_penalty": round(decision.score.volatility_penalty, 4),
                                },
                                "features": {
                                    k: round(v, 4) if isinstance(v, float) else v
                                    for k, v in latest_snap.items()
                                    if k in (
                                        "rsi_14", "ema_20", "ema_50", "macd", "macd_signal",
                                        "bb_upper", "bb_lower", "bb_mid", "atr_14",
                                        "volume_sma_20", "roc_14", "adx_14",
                                        "close", "high", "low", "open",
                                    )
                                },
                                "reason": decision.reason,
                                "regime": {
                                    "trend": decision.regime.trend_label if hasattr(decision.regime, 'trend_label') else None,
                                    "volatility": decision.regime.volatility_label if hasattr(decision.regime, 'volatility_label') else None,
                                } if decision.regime else None,
                            }
                        )
                    else:
                        # Log the HOLD reason and features so the user can analyze why it wasn't bought
                        _log(
                            "STRATEGY",
                            f"Skipped {symbol}: {decision.reason or 'Conditions not met'}",
                            payload={
                                "symbol": symbol,
                                "action": "HOLD",
                                "features": {
                                    k: round(v, 4) if isinstance(v, float) else v
                                    for k, v in latest_snap.items()
                                    if k in ("rsi_14", "macd", "macd_signal", "close", "roc_14", "volume_sma_20")
                                }
                            }
                        )
                else:
                    # If strategy returned None
                    latest_snap = snapshots[-1].features_json if snapshots else {}
                    _log(
                        "STRATEGY",
                        f"Skipped {symbol}: No signal generated by strategy",
                        payload={
                            "symbol": symbol,
                            "action": "NONE",
                            "features": {
                                k: round(v, 4) if isinstance(v, float) else v
                                for k, v in latest_snap.items()
                                if k in ("rsi_14", "macd", "macd_signal", "close", "roc_14")
                            }
                        }
                    )
                    
            cycle.symbols_processed = len(symbols)
            cycle.decisions_made = len(decisions)
            
            # 5. Portfolio Construction
            logger.info(f"[Cycle {cycle.id}] Constructing portfolio target from {len(decisions)} decisions.")
            _log("PORTFOLIO", f"Constructing target portfolio from {len(decisions)} active signals", payload={
                "total_signals": len(decisions),
                "candidate_symbols": [d.symbol for d in decisions],
                "actions": {d.symbol: d.action.value for d in decisions},
            })
            target_portfolio = self.portfolio_engine.build_target_portfolio(
                exchange=self.fetcher_service.provider.exchange,
                timeframe=timeframe,
                decisions=decisions,
            )
            
            # 6. Risk Management
            logger.info(f"[Cycle {cycle.id}] Evaluating risk limits.")
            risk_assessment = self.risk_engine.assess(target=target_portfolio)
            approved_portfolio = risk_assessment.approved_target
            
            if approved_portfolio is None:
                _log("RISK", f"Risk engine rejected portfolio: {risk_assessment.reason}. Holding current positions.", "WARN")
                # Build an empty target to hold all current positions (no new buys, no forced sells)
                from crypto_mas.engine.portfolio import PortfolioTarget
                approved_portfolio = PortfolioTarget(
                    exchange=target_portfolio.exchange,
                    timeframe=target_portfolio.timeframe,
                    target_positions=[],
                    cash_weight=1.0,
                    gross_exposure=0.0,
                    reason="Risk-rejected: holding cash.",
                    created_at=self.time_provider.now(),
                )

            # Build approved portfolio payload
            if approved_portfolio and approved_portfolio.target_positions:
                _log("RISK", "Risk checks passed, proceeding to execution", payload={
                    "status": risk_assessment.status.value if hasattr(risk_assessment.status, 'value') else str(risk_assessment.status),
                    "reason": risk_assessment.reason,
                    "approved_positions": [
                        {"symbol": p.symbol, "weight": round(p.target_weight, 4), "confidence": round(p.confidence, 4)}
                        for p in approved_portfolio.target_positions
                    ],
                    "gross_exposure": round(approved_portfolio.gross_exposure, 4),
                    "cash_weight": round(approved_portfolio.cash_weight, 4),
                })
            else:
                _log("RISK", "Risk checks passed — no new positions to open", payload={
                    "status": "APPROVED",
                    "approved_positions": [],
                    "reason": "No eligible long candidates survived filters.",
                })
            
            # 7. Execution
            logger.info(f"[Cycle {cycle.id}] Executing portfolio.")
            _log("EXECUTION", "Executing orders against virtual broker")
            
            # Mark to Market
            self.paper_broker.update_mark_prices(
                account_name=account_name,
                exchange=self.fetcher_service.provider.exchange,
                timeframe=timeframe.value,
                cycle_id=cycle.id,
            )
            
            # Close positions not in target (Skip for scalping as it relies purely on SL/TP)
            if self.strategy_mode != "scalping":
                close_report = self.paper_broker.close_positions_not_in_target(
                    account_name=account_name,
                    target=approved_portfolio,
                    cycle_id=cycle.id,
                )
            else:
                from crypto_mas.services.paper_trading.schemas import PaperExecutionReport
                account_model = self.paper_broker.account_repository.get_by_name(account_name)
                start_eq = account_model.cash_balance + self.paper_broker._calculate_open_positions_value(account_name)
                close_report = PaperExecutionReport(
                    account_name=account_name,
                    exchange=self.fetcher_service.provider.exchange,
                    starting_cash=float(account_model.cash_balance),
                    ending_cash=float(account_model.cash_balance),
                    starting_equity=float(start_eq),
                    ending_equity=float(start_eq),
                    executed=[],
                    skipped=[],
                    created_at=self.time_provider.now()
                )
            
            # Execute target
            execute_report = self.paper_broker.execute_target_portfolio(
                account_name=account_name,
                target=approved_portfolio,
                cycle_id=cycle.id,
            )
            
            cycle.trades_executed = len(close_report.executed) + len(execute_report.executed)
            cycle.starting_equity = close_report.starting_equity
            cycle.ending_equity = execute_report.ending_equity
            cycle.cycle_pnl = cycle.ending_equity - cycle.starting_equity
            
            # 8. Finalize
            self.cycle_repository.update_status(cycle.id, "COMPLETED")
            cycle.finished_at = self.time_provider.now()
            
            logger.info(f"[Cycle {cycle.id}] Completed successfully. PnL: {cycle.cycle_pnl}")
            _log(
                "COMPLETED",
                f"Cycle #{cycle.id} tamamlandı. {len(symbols)} coin tarandı, {cycle.trades_executed} işlem yapıldı. PnL: ${cycle.cycle_pnl:.4f}",
                "INFO" if cycle.trades_executed == 0 else "SUCCESS",
                payload={
                    "cycle_id": cycle.id,
                    "symbols_scanned": len(symbols),
                    "decisions_made": cycle.decisions_made,
                    "trades_executed": cycle.trades_executed,
                    "starting_equity": float(cycle.starting_equity) if cycle.starting_equity else None,
                    "ending_equity": float(cycle.ending_equity) if cycle.ending_equity else None,
                    "cycle_pnl": float(cycle.cycle_pnl) if cycle.cycle_pnl else 0.0,
                    "duration_secs": round((self.time_provider.now() - now).total_seconds(), 1),
                }
            )
            
            # Commit all logs, snapshot and cycle states in one transaction per cycle
            self.db.commit()
            return cycle
            
        except Exception as e:
            logger.exception(f"[Cycle {cycle.id}] Failed with error: {e}")
            _log("FAILED", f"Critical error in cycle: {str(e)}", "ERROR")
            self.cycle_repository.update_status(cycle.id, "FAILED")
            self.db.commit()
            raise e
            
    @staticmethod
    def _get_timedelta(timeframe: Timeframe) -> timedelta:
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
