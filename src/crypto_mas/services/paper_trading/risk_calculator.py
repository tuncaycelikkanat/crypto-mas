import logging
from decimal import Decimal
from typing import Any

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot

logger = logging.getLogger(__name__)

class RiskCalculator:
    SL_PCT = {"scalping": 0.020, "swing": 0.03, "hodl": 0.05}
    TP_PCT = {"scalping": 0.024, "swing": 0.06, "hodl": 0.12}
    
    COMMISSION_RATE = Decimal("0.0002") # 0.02% Futures Maker limit fee
    SLIPPAGE_RATE = Decimal("0.0002")  # 0.02% Limit order slippage/execution spread
    
    MAX_RISK_PER_TRADE = Decimal("1.00")

    def __init__(self, strategy_mode: str = "swing"):
        self.strategy_mode = strategy_mode

    def calculate_target_notional(self, target_weight: float, starting_equity: Decimal) -> Decimal:
        weight_notional = Decimal(str(target_weight)) * starting_equity
        max_notional = starting_equity * self.MAX_RISK_PER_TRADE
        return min(weight_notional, max_notional)

    def calculate_total_cost(self, notional: Decimal) -> tuple[Decimal, Decimal]:
        fee = self._money(notional * self.COMMISSION_RATE)
        total_cost = notional + fee
        return total_cost, fee
        
    def calculate_execution_price(self, price: Decimal, side: str) -> Decimal:
        if side == "LONG":
            return self._money(price * (Decimal("1") + self.SLIPPAGE_RATE))
        else:
            return self._money(price * (Decimal("1") - self.SLIPPAGE_RATE))
            
    def calculate_exit_price(self, price: Decimal, side: str) -> Decimal:
        if side == "LONG":
            return self._money(price * (Decimal("1") - self.SLIPPAGE_RATE))
        else:
            return self._money(price * (Decimal("1") + self.SLIPPAGE_RATE))

    def calculate_quantity(self, notional: Decimal, execution_price: Decimal) -> Decimal:
        return self._money(notional / execution_price)

    def calculate_sl_tp(self, price: Decimal, side: str, atr_val: float | None = None, override_sl: float | None = None, override_tp: float | None = None) -> tuple[Decimal, Decimal]:
        ATR_SL_MULT = {"scalping": 1.5, "swing": 2.0, "hodl": 3.0}
        ATR_TP_MULT = {"scalping": 3.0, "swing": 4.0, "hodl": 6.0}
        
        stop_loss_price = None
        take_profit_price = None
        
        if atr_val and atr_val > 0:
            atr_d = Decimal(str(atr_val))
            sl_mult = Decimal(str(override_sl)) if override_sl else Decimal(str(ATR_SL_MULT.get(self.strategy_mode, 2.0)))
            tp_mult = Decimal(str(override_tp)) if override_tp else Decimal(str(ATR_TP_MULT.get(self.strategy_mode, 4.0)))
            
            if side == "LONG":
                stop_loss_price   = self._money(price - atr_d * sl_mult)
                take_profit_price = self._money(price + atr_d * tp_mult)
            else:
                stop_loss_price   = self._money(price + atr_d * sl_mult)
                take_profit_price = self._money(price - atr_d * tp_mult)
                
        if stop_loss_price is None:
            friction = Decimal(str((self.COMMISSION_RATE + self.SLIPPAGE_RATE) * 2))
            sl_pct = Decimal(str(self.SL_PCT.get(self.strategy_mode, 0.03)))
            tp_pct = Decimal(str(self.TP_PCT.get(self.strategy_mode, 0.06))) + friction
            
            if side == "LONG":
                stop_loss_price   = self._money(price * (1 - sl_pct))
                take_profit_price = self._money(price * (1 + tp_pct))
            else:
                stop_loss_price   = self._money(price * (1 + sl_pct))
                take_profit_price = self._money(price * (1 - tp_pct))
                
        return stop_loss_price, take_profit_price

    def calculate_fee(self, gross_notional: Decimal) -> Decimal:
        return self._money(gross_notional * self.COMMISSION_RATE)
        
    def calculate_pnl(self, entry_price: Decimal, exit_price: Decimal, quantity: Decimal, side: str) -> tuple[Decimal, float]:
        if side == "LONG":
            raw_realized_pnl = (exit_price - entry_price) * quantity
            pnl_pct = float((exit_price - entry_price) / entry_price * 100)
        else:
            raw_realized_pnl = (entry_price - exit_price) * quantity
            pnl_pct = float((entry_price - exit_price) / entry_price * 100)
        return raw_realized_pnl, pnl_pct

    @staticmethod
    def extract_close_price(snapshot: FeatureSnapshot | None) -> Decimal | None:
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

    @staticmethod
    def is_thin_liquidity_or_excessive_spread(snapshot: FeatureSnapshot | None) -> tuple[bool, str]:
        if snapshot is None or not snapshot.features_json:
            return False, ""
        features = snapshot.features_json
        close = features.get("close")
        high = features.get("high")
        low = features.get("low")
        volume = features.get("volume")

        if close and float(close) > 0:
            c = float(close)
            if high is not None and low is not None:
                spread = (float(high) - float(low)) / c
                if spread > 0.08:
                    return True, f"Excessive bar spread/range ({spread:.1%} > 8.0%)"

            if volume is not None:
                usdt_volume = float(volume) * c
                if usdt_volume < 1000.0:
                    return True, f"Thin liquidity bar volume (${usdt_volume:,.0f} < $1,000)"

        return False, ""

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.00000001"))
