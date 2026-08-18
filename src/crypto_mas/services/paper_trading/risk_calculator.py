import logging
from decimal import Decimal
from typing import Any

from crypto_mas.domain.models.feature_snapshot import FeatureSnapshot

logger = logging.getLogger(__name__)

class RiskCalculator:
    SL_PCT = {"scalping": 0.020, "swing": 0.03, "hodl": 0.05}
    TP_PCT = {"scalping": 0.024, "swing": 0.06, "hodl": 0.12}
    
    DEFAULT_COMMISSION_RATE = Decimal("0.0002")  # 0.02% Futures Maker limit fee
    DEFAULT_SLIPPAGE_RATE = Decimal("0.0002")    # 0.02% Limit order slippage/execution spread
    
    MAX_RISK_PER_TRADE = Decimal("1.00")

    def __init__(
        self,
        strategy_mode: str = "swing",
        commission_rate: Decimal | float | None = None,
        slippage_rate: Decimal | float | None = None,
        dynamic_slippage: bool = False,
    ):
        self.strategy_mode = strategy_mode
        self.commission_rate = (
            Decimal(str(commission_rate)) if commission_rate is not None else self.DEFAULT_COMMISSION_RATE
        )
        self.slippage_rate = (
            Decimal(str(slippage_rate)) if slippage_rate is not None else self.DEFAULT_SLIPPAGE_RATE
        )
        self.dynamic_slippage = dynamic_slippage
        # Retain backward compatibility constants as instance/class aliases
        self.COMMISSION_RATE = self.commission_rate
        self.SLIPPAGE_RATE = self.slippage_rate

    def calculate_effective_slippage(
        self,
        price: Decimal,
        atr_val: float | None = None,
        is_high_volatility: bool = False,
    ) -> Decimal:
        """
        Calculates effective slippage based on baseline rate + dynamic volatility adjustment.
        """
        base = self.slippage_rate
        if not self.dynamic_slippage or price <= 0:
            return base

        # Volatility multiplier
        vol_mult = Decimal("1.5") if is_high_volatility else Decimal("1.0")
        if atr_val and atr_val > 0:
            atr_ratio = Decimal(str(atr_val)) / price
            # If ATR > 2% of price, add proportional slippage buffer
            if atr_ratio > Decimal("0.02"):
                dynamic_bump = min(atr_ratio * Decimal("0.05"), Decimal("0.003"))  # cap at 0.3%
                return self._money((base + dynamic_bump) * vol_mult)

        return self._money(base * vol_mult)

    def calculate_target_notional(self, target_weight: float, starting_equity: Decimal) -> Decimal:
        weight_notional = Decimal(str(target_weight)) * starting_equity
        max_notional = starting_equity * self.MAX_RISK_PER_TRADE
        return min(weight_notional, max_notional)

    def calculate_total_cost(self, notional: Decimal) -> tuple[Decimal, Decimal]:
        fee = self._money(notional * self.commission_rate)
        total_cost = notional + fee
        return total_cost, fee
        
    def calculate_execution_price(
        self,
        price: Decimal,
        side: str,
        atr_val: float | None = None,
        is_high_volatility: bool = False,
    ) -> Decimal:
        slip = self.calculate_effective_slippage(price, atr_val=atr_val, is_high_volatility=is_high_volatility)
        if side == "LONG":
            return self._money(price * (Decimal("1") + slip))
        else:
            return self._money(price * (Decimal("1") - slip))
            
    def calculate_exit_price(
        self,
        price: Decimal,
        side: str,
        atr_val: float | None = None,
        is_high_volatility: bool = False,
    ) -> Decimal:
        slip = self.calculate_effective_slippage(price, atr_val=atr_val, is_high_volatility=is_high_volatility)
        if side == "LONG":
            return self._money(price * (Decimal("1") - slip))
        else:
            return self._money(price * (Decimal("1") + slip))

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
