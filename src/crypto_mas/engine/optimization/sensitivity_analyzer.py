import asyncio
import logging
from collections.abc import Callable, Coroutine

from crypto_mas.domain.models.backtest_result import BacktestResult
from crypto_mas.engine.optimization.composite_score import FitnessCalculator

logger = logging.getLogger(__name__)

class SensitivityAnalyzer:
    @staticmethod
    def analyze(
        best_params: dict,
        target_param: str,
        deltas: list[float],
        run_backtest_fn: Callable[[dict], Coroutine],
        min_trades: int = 30
    ) -> dict[float, float]:
        """
        Runs sensitivity analysis by mutating `target_param` around the `best_params`
        using the provided `deltas`. Returns a mapping of delta -> score.
        """
        logger.info(f"Running Sensitivity Analysis on {target_param}...")
        
        results: dict[float, BacktestResult] = {}
        base_val = best_params.get(target_param)
        if base_val is None:
            logger.warning(f"Parameter {target_param} not found in best_params.")
            return results
            
        loop = asyncio.get_event_loop()
        
        for delta in deltas:
            test_params = dict(best_params)
            test_params[target_param] = base_val + delta
            
            # Execute backtest with perturbed parameter
            bt_result: BacktestResult = loop.run_until_complete(run_backtest_fn(test_params))
            score = FitnessCalculator.calculate_composite_score(bt_result, min_trades)
            
            logger.info(f"Sensitivity [ {target_param} = {test_params[target_param]:.3f} (Δ {delta:+.2f}) ] => Score: {score:.3f}")
            results[delta] = score
            
        # Check if it's a spike (needle) or a plateau
        # A simple check: if any neighbor has a drastically lower score (e.g., < 50% of the peak), it's risky.
        
        return results
