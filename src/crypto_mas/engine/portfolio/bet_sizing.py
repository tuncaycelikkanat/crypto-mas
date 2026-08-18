from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BetSizeRecommendation:
    symbol: str
    target_weight: float
    kelly_fraction: float
    volatility_scale: float
    reason: str


class BetSizer:
    """
    Quantitative position sizing engine combining Fractional Kelly Criterion
    and Volatility Targeting for capital preservation and maximum risk-adjusted growth.
    """

    def __init__(
        self,
        target_annual_volatility: float = 0.20,  # 20% annual portfolio target volatility
        kelly_multiplier: float = 0.25,         # Quarter Kelly (institutional standard)
        max_single_weight: float = 0.35,        # Maximum cap per asset
        min_single_weight: float = 0.02,        # Minimum floor
    ):
        self.target_annual_volatility = target_annual_volatility
        self.kelly_multiplier = kelly_multiplier
        self.max_single_weight = max_single_weight
        self.min_single_weight = min_single_weight

    def calculate_fractional_kelly(
        self,
        win_rate: float,
        reward_risk_ratio: float = 2.0,
    ) -> float:
        """
        Calculates Fractional Kelly Criterion:
        f* = lambda * (p - (1 - p) / b)
        where p = win_rate, b = reward_risk_ratio, lambda = kelly_multiplier
        """
        if reward_risk_ratio <= 0:
            return self.min_single_weight

        p = max(0.01, min(win_rate, 0.99))
        b = reward_risk_ratio
        
        full_kelly = p - ((1.0 - p) / b)
        if full_kelly <= 0:
            return 0.0

        fractional = full_kelly * self.kelly_multiplier
        return max(0.0, min(fractional, self.max_single_weight))

    def calculate_volatility_target_weight(
        self,
        asset_atr: float,
        asset_price: float,
        timeframe_annualization_factor: float = 1460.0,  # ~1460 6-hour or 4-hour bars/year
    ) -> float:
        """
        Volatility Targeting:
        weight = target_volatility / asset_volatility
        """
        if asset_price <= 0 or asset_atr <= 0:
            return self.min_single_weight

        bar_volatility = asset_atr / asset_price
        annualized_asset_vol = bar_volatility * (timeframe_annualization_factor ** 0.5)

        if annualized_asset_vol <= 1e-6:
            return self.max_single_weight

        weight = self.target_annual_volatility / annualized_asset_vol
        return max(self.min_single_weight, min(weight, self.max_single_weight))

    def recommend_size(
        self,
        symbol: str,
        confidence_score: float,
        asset_atr: float | None = None,
        asset_price: float | None = None,
        estimated_win_rate: float = 0.55,
        reward_risk_ratio: float = 2.0,
    ) -> BetSizeRecommendation:
        """
        Combines Fractional Kelly with Volatility Targeting and signal confidence
        to produce a mathematically optimal, risk-bounded weight recommendation.
        """
        # 1. Kelly weight
        kelly_weight = self.calculate_fractional_kelly(
            win_rate=estimated_win_rate,
            reward_risk_ratio=reward_risk_ratio,
        )

        # 2. Volatility scaling
        if asset_atr and asset_price and asset_price > 0:
            vol_weight = self.calculate_volatility_target_weight(
                asset_atr=asset_atr,
                asset_price=asset_price,
            )
        else:
            vol_weight = self.max_single_weight

        # 3. Dynamic blend weighted by model conviction score
        base_size = min(kelly_weight, vol_weight) if kelly_weight > 0 else self.min_single_weight
        confidence_adjusted = base_size * max(0.3, min(confidence_score, 1.0))
        
        final_weight = max(self.min_single_weight, min(confidence_adjusted, self.max_single_weight))
        final_weight = round(final_weight, 4)

        reason = (
            f"BetSize: Kelly({kelly_weight*100:.1f}%) & VolTarget({vol_weight*100:.1f}%) "
            f"=> Final: {final_weight*100:.1f}% (Conf: {confidence_score:.2f})"
        )

        return BetSizeRecommendation(
            symbol=symbol,
            target_weight=final_weight,
            kelly_fraction=round(kelly_weight, 4),
            volatility_scale=round(vol_weight, 4),
            reason=reason,
        )
