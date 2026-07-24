from crypto_mas.domain.models.backtest_result import BacktestResult


class FitnessCalculator:
    @staticmethod
    def calculate_composite_score(result: BacktestResult, min_trades: int = 30) -> float:
        """
        Calculates a risk-adjusted composite score to prevent Optuna from favoring
        high-variance or curve-fitted parameters.
        """
        if result.total_trades is None or result.total_trades < min_trades:
            return -999.0
            
        sortino = result.sortino_ratio or 0.0
        calmar = result.calmar_ratio or 0.0
        pf = result.profit_factor or 0.0
        max_dd = result.max_drawdown or 1.0  # Worst case DD if none
        
        # 40% Downside risk adjusted returns
        # 30% Drawdown adjusted returns
        # 20% Profit Factor
        # 10% Capital Preservation
        score = (
            sortino * 0.4 +
            calmar * 0.3 +
            pf * 0.2 +
            (1.0 - max_dd) * 0.1
        )
        
        if result.final_equity and result.initial_balance and result.final_equity < result.initial_balance:
            score -= 5.0  # Penalty for unprofitability
            
        return float(score)
