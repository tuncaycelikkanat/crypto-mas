import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.domain.repositories.position_repository import PositionRepository
from crypto_mas.engine.llm_committee.cost_tracker import CostTracker
from crypto_mas.engine.llm_committee.gemini_provider import GeminiProvider
from crypto_mas.engine.llm_committee.orchestrator import LLMCommitteeOrchestrator
from crypto_mas.engine.risk.manager import RiskManager
from crypto_mas.engine.strategy.schemas import DecisionAction
from crypto_mas.infrastructure.config.settings import get_settings
from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.schemas import Timeframe
from crypto_mas.services.trading_cycle_service.utils import get_timedelta

logger = logging.getLogger(__name__)


class StrategyOrchestrator:
    def __init__(
        self,
        db: Session,
        fetcher_service: HistoricalFetcherService,
        feature_service: FeaturePipelineService,
        feature_snapshot_repository: FeatureSnapshotRepository,
        risk_manager: RiskManager,
        bt_position_repo: PositionRepository | None = None,
    ) -> None:
        self.db = db
        self.fetcher_service = fetcher_service
        self.feature_service = feature_service
        self.feature_snapshot_repository = feature_snapshot_repository
        self.risk_manager = risk_manager
        self._bt_position_repo = bt_position_repo
        
        # Initialize LLM Committee
        self.llm_orchestrator = None
        settings = get_settings()
        api_key = getattr(settings, "gemini_api_key", None)
        if api_key:
            provider = GeminiProvider(api_key=api_key)
            cost_tracker = CostTracker()
            self.llm_orchestrator = LLMCommitteeOrchestrator(provider=provider, cost_tracker=cost_tracker)

    async def run_strategies_and_score(
        self, 
        symbols: list[str], 
        timeframe: Timeframe, 
        now: datetime, 
        strategy, 
        strategy_name: str, 
        risk_level: int, 
        cycle: TradingCycle, 
        account_name: str, 
        htf: Timeframe | None, 
        btc_is_crashing: bool, 
        _log, 
        use_btc_shield: bool = True, 
        use_htf_shield: bool = True, 
        use_regime_shield: bool = True, 
        config_json: dict | None = None, 
        display_id: int | None = None
    ) -> tuple[list, list[str]]:
        display_id = display_id if display_id is not None else cycle.id
        decisions = []
        is_backtest = cycle.trigger.startswith("BACKTEST-")
        
        exchange_str = self.fetcher_service.provider.exchange.value
        
        pos_repo = self._bt_position_repo if is_backtest else None
        if pos_repo is None:
            pos_repo = PositionRepository(self.db)
        
        open_position_symbols: set[str] = pos_repo.get_open_position_symbols(account_name, exchange_str)
        cooldown_symbols: set[str] = pos_repo.get_recent_closed_symbols(
            account_name=account_name,
            exchange=exchange_str,
            time_now=now,
            cooldown_minutes=60,
        )
        
        for symbol in symbols:
            _log("STRATEGY", f"Evaluating {strategy_name} for {symbol}")
            
            if not is_backtest:
                self.feature_service.calculate_and_store(
                    exchange=self.fetcher_service.provider.exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    end_time=now,
                    limit=1000,
                )
            
            snapshots = self.feature_snapshot_repository.list_by_symbol(
                exchange=self.fetcher_service.provider.exchange.value,
                symbol=symbol,
                timeframe=timeframe.value,
                end_time=now,
                limit=5,
            )
            
            if not snapshots:
                if not is_backtest:
                    logger.warning(f"[Cycle {display_id}] No feature snapshots for {symbol}. Skipping.")
                    _log("STRATEGY", f"No data available for {symbol}, skipped", "WARN")
                continue
            
            latest_snapshot = snapshots[-1]
            timeframe_delta = get_timedelta(timeframe)
            max_allowed_delay = timeframe_delta + timedelta(minutes=15)
            
            snap_time = latest_snapshot.timestamp
            if snap_time.tzinfo is None:
                snap_time = snap_time.replace(tzinfo=UTC)
            if now - snap_time > max_allowed_delay:
                err_msg = f"STALE DATA DETECTED for {symbol}: Latest snapshot timestamp {latest_snapshot.timestamp} is older than allowed {max_allowed_delay} from now {now}. Kill-Switch triggered."
                if is_backtest:
                    continue
                else:
                    logger.error(f"[Cycle {display_id}] {err_msg}")
                    raise ValueError(err_msg)

            htf_snapshots = []
            if htf and use_htf_shield:
                if not is_backtest:
                    self.feature_service.calculate_and_store(
                        exchange=self.fetcher_service.provider.exchange,
                        symbol=symbol,
                        timeframe=htf,
                    )
                htf_snapshots = self.feature_snapshot_repository.list_by_symbol(
                    exchange=self.fetcher_service.provider.exchange.value,
                    symbol=symbol,
                    timeframe=htf.value,
                    end_time=now,
                    limit=5,
                )
            
            kwargs: dict[str, Any] = {}
            if strategy_name == "regime_adaptive":
                kwargs["config"] = config_json or {}
            elif strategy_name == "multi_agent":
                kwargs["use_regime_shield"] = use_regime_shield
                
            decision = strategy.decide(
                exchange=self.fetcher_service.provider.exchange,
                symbol=symbol,
                timeframe=timeframe,
                snapshots=snapshots,
                risk_level=risk_level,
                is_open=(symbol in open_position_symbols),
                **kwargs
            )
            
            if decision:
                if decision.action in (DecisionAction.CONSIDER_LONG, DecisionAction.CONSIDER_SHORT):
                    if symbol in open_position_symbols:
                        _log("STRATEGY", f"Decision {decision.action.value} for {symbol} REJECTED: Already have an open position.", "WARN")
                        decision.action = DecisionAction.HOLD
                        decision.reason += " | REJECTED: Open Position Exists"
                        
                    elif symbol in cooldown_symbols:
                        _log("STRATEGY", f"Decision {decision.action.value} for {symbol} REJECTED: Cooldown active (Recently Closed).", "WARN")
                        decision.action = DecisionAction.HOLD
                        decision.reason += " | REJECTED: Cooldown (60m)"
                    else:
                        # ── Regime-Adaptive Whipsaw Cooldown ──────────────────────
                        whipsaw_min_stops = 2
                        whipsaw_cooldown_mins = 2880  # Default 48h (SIDEWAYS)
                        from crypto_mas.engine.regime import MarketRegime
                        if decision.regime:
                            if decision.regime.regime == MarketRegime.BULL_TREND:
                                whipsaw_min_stops = 3
                                whipsaw_cooldown_mins = 720   # 12h in BULL
                            elif decision.regime.regime == MarketRegime.BEAR_TREND:
                                whipsaw_min_stops = 2
                                whipsaw_cooldown_mins = 1440  # 24h in BEAR

                        whipsaw_symbols = pos_repo.get_whipsaw_cooldown_symbols(
                            account_name=account_name,
                            exchange=exchange_str,
                            time_now=now,
                            min_stop_count=whipsaw_min_stops,
                            cooldown_minutes=whipsaw_cooldown_mins,
                        ) if hasattr(pos_repo, "get_whipsaw_cooldown_symbols") else set()

                        if symbol in whipsaw_symbols:
                            regime_name = decision.regime.regime.value if decision.regime else "SIDEWAYS"
                            _log("STRATEGY", f"Decision {decision.action.value} for {symbol} REJECTED: Whipsaw Cooldown active ({whipsaw_min_stops}+ consecutive stop-losses in {regime_name}).", "WARN")
                            decision.action = DecisionAction.HOLD
                            decision.reason += f" | REJECTED: Whipsaw Cooldown ({whipsaw_cooldown_mins // 60}h)"

                if decision.action not in (DecisionAction.HOLD, DecisionAction.CLOSE_LONG, DecisionAction.CLOSE_SHORT):
                    context = {
                        "btc_is_crashing": btc_is_crashing,
                        "use_btc_shield": use_btc_shield,
                        "htf_snapshots": htf_snapshots,
                        "use_htf_shield": use_htf_shield,
                        "use_regime_shield": use_regime_shield,
                    }
                    decision = self.risk_manager.evaluate_decision(decision, context)
                    
                    if decision.action == DecisionAction.HOLD:
                        _log("STRATEGY", f"Decision for {symbol} REJECTED by RiskManager: {decision.reason}", "WARN")
                        
                    # Phase 0: Trigger LLM Committee (Shadow Mode) if there's a strong signal
                    else:
                        run_llm = config_json.get("run_llm", False) if config_json else False
                        if self.llm_orchestrator and decision.action in (DecisionAction.CONSIDER_LONG, DecisionAction.CONSIDER_SHORT) and (not is_backtest or run_llm):
                            # Construct context for LLM
                            llm_context = {
                                "symbol": symbol,
                                "market_regime": decision.regime.regime.value if decision.regime else "UNKNOWN",
                                "score": decision.score.total_score,
                                "recent_features": snapshots[-1].features_json if snapshots else {}
                            }
                            
                            _log("LLM_COMMITTEE", f"Triggering Shadow Mode LLM Committee for {symbol}")
                            decision = await self.llm_orchestrator.evaluate_decision(
                                symbol=symbol,
                                context=llm_context,
                                original_decision=decision,
                                db=self.db
                            )
                    
                latest_snap = snapshots[-1].features_json if snapshots else {}
                
                if decision.action != DecisionAction.AVOID:
                    if decision.action == DecisionAction.HOLD and symbol not in open_position_symbols:
                        pass
                    else:
                        decisions.append(decision)
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
        return decisions, list(open_position_symbols)
