import logging
from datetime import datetime

from crypto_mas.domain.models.trading_cycle import TradingCycle
from crypto_mas.domain.repositories.feature_snapshot_repository import FeatureSnapshotRepository
from crypto_mas.services.feature_pipeline.service import FeaturePipelineService
from crypto_mas.services.market_data_service.historical_fetcher import HistoricalFetcherService
from crypto_mas.services.market_data_service.schemas import Timeframe
from crypto_mas.services.trading_cycle_service.utils import get_timedelta

logger = logging.getLogger(__name__)


class MarketDataOrchestrator:
    def __init__(
        self,
        fetcher_service: HistoricalFetcherService,
        feature_service: FeaturePipelineService,
        feature_snapshot_repository: FeatureSnapshotRepository,
    ) -> None:
        self.fetcher_service = fetcher_service
        self.feature_service = feature_service
        self.feature_snapshot_repository = feature_snapshot_repository

    async def fetch_data_for_symbols(
        self, 
        symbols: list[str], 
        timeframe: Timeframe, 
        now: datetime, 
        cycle: TradingCycle, 
        _log, 
        use_btc_shield: bool = True, 
        display_id: int | None = None
    ) -> tuple[bool, Timeframe | None]:
        display_id = display_id if display_id is not None else cycle.id
        logger.debug(f"[Cycle {display_id}] Starting market data sync for {len(symbols)} symbols.")
        _log("MARKET_DATA", f"Fetching history from {self.fetcher_service.provider.exchange.value} for {timeframe}")
        
        fetch_symbols = set(symbols)
        if use_btc_shield:
            fetch_symbols.add("BTCUSDT")
        fetch_symbols_list = list(fetch_symbols)
        
        fallback_start = now - get_timedelta(timeframe) * 1000
        
        await self.fetcher_service.backfill_universe(
            symbols=fetch_symbols_list,
            timeframe=timeframe,
            start_time=fallback_start,
            end_time=now,
        )
        
        htf_map = {
            Timeframe.ONE_MINUTE: Timeframe.FOUR_HOURS,
            Timeframe.FIFTEEN_MINUTES: Timeframe.ONE_HOUR,
            Timeframe.ONE_HOUR: Timeframe.ONE_DAY,
            Timeframe.FOUR_HOURS: Timeframe.ONE_WEEK,
            Timeframe.ONE_DAY: Timeframe.ONE_MONTH,
        }
        htf = htf_map.get(timeframe)
        
        if htf:
            _log("MARKET_DATA", f"Fetching HTF ({htf.value}) history for Regime Filter")
            htf_start = now - get_timedelta(htf) * 60
            await self.fetcher_service.backfill_universe(
                symbols=fetch_symbols_list,
                timeframe=htf,
                start_time=htf_start,
                end_time=now,
            )
            
        btc_is_crashing = False
        if use_btc_shield:
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
            
            if btc_snapshots:
                latest_btc = btc_snapshots[-1].features_json
                btc_roc = latest_btc.get("roc_14")
                if btc_roc is not None and btc_roc < -5.0:
                    btc_is_crashing = True
                    _log("RISK", f"MARKET CRASH DETECTED! BTC ROC: {btc_roc:.2f}%. Longs will be restricted.", "WARN")
                    
        return btc_is_crashing, htf
