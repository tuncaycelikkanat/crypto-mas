from decimal import Decimal
from crypto_mas.services.paper_trading.risk_calculator import RiskCalculator


def test_custom_commission_and_slippage():
    calc = RiskCalculator(
        strategy_mode="swing",
        commission_rate=0.0005,  # 0.05%
        slippage_rate=0.0004,    # 0.04%
        dynamic_slippage=False,
    )

    assert calc.commission_rate == Decimal("0.0005")
    assert calc.slippage_rate == Decimal("0.0004")

    price = Decimal("100.0")
    long_exec = calc.calculate_execution_price(price, side="LONG")
    assert long_exec == Decimal("100.04000000")

    short_exec = calc.calculate_execution_price(price, side="SHORT")
    assert short_exec == Decimal("99.96000000")


def test_dynamic_slippage_adjustment():
    calc_dynamic = RiskCalculator(
        strategy_mode="swing",
        slippage_rate=0.0002,
        dynamic_slippage=True,
    )

    price = Decimal("100.0")
    # Low ATR
    slip_normal = calc_dynamic.calculate_effective_slippage(price, atr_val=0.5, is_high_volatility=False)
    assert slip_normal == Decimal("0.00020000")

    # High ATR (5.0 on price 100.0 is 5% ATR)
    slip_high_atr = calc_dynamic.calculate_effective_slippage(price, atr_val=5.0, is_high_volatility=False)
    assert slip_high_atr > Decimal("0.00020000")

    # High volatility regime
    slip_vol = calc_dynamic.calculate_effective_slippage(price, atr_val=5.0, is_high_volatility=True)
    assert slip_vol > slip_high_atr
