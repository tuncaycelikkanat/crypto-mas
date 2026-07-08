from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot
from crypto_mas.engine.regime import MarketRegime

class HTFRegimeManager:
    """
    Higher Timeframe (HTF) Regime Manager.
    Used to filter out bad trades by checking the overall market trend on a higher timeframe (e.g. 4H or 1D).
    """
    
    def is_long_allowed(self, htf_snapshots: list[FeatureSnapshot]) -> bool:
        """
        Returns False if the HTF trend is strongly bearish, which means we should AVOID buying the dip on smaller timeframes.
        """
        if not htf_snapshots:
            # If no HTF data available, allow by default but might be risky
            return True
            
        latest = htf_snapshots[-1]
        features = latest.features_json
        
        close = features.get("close")
        ema_20 = features.get("ema_20")
        ema_50 = features.get("ema_50")
        roc_14 = features.get("roc_14")
        
        if None in {close, ema_20, ema_50, roc_14}:
            return True
            
        # Define Major Bear Trend: Price is below both EMAs, Fast EMA is below Slow EMA, and Momentum is negative.
        bearish = close < ema_20 < ema_50 and roc_14 < 0
        
        if bearish:
            # Strong downtrend on HTF. Do not catch falling knives.
            return False
            
        return True
        
    def is_short_allowed(self, htf_snapshots: list[FeatureSnapshot]) -> bool:
        """
        Returns False if the HTF trend is strongly bullish, which means we should AVOID shorting the peak on smaller timeframes.
        """
        if not htf_snapshots:
            return True
            
        latest = htf_snapshots[-1]
        features = latest.features_json
        
        close = features.get("close")
        ema_20 = features.get("ema_20")
        ema_50 = features.get("ema_50")
        roc_14 = features.get("roc_14")
        
        if None in {close, ema_20, ema_50, roc_14}:
            return True
            
        # Define Major Bull Trend
        bullish = close > ema_20 > ema_50 and roc_14 > 0
        
        if bullish:
            # Strong uptrend on HTF. Do not short.
            return False
            
        return True
