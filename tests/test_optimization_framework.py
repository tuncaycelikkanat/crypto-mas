import pytest
from datetime import datetime, timezone
from crypto_mas.engine.optimization.fold_generator import FoldGenerator
from crypto_mas.engine.optimization.composite_score import FitnessCalculator
from crypto_mas.engine.optimization.sensitivity_analyzer import SensitivityAnalyzer
from crypto_mas.domain.models.backtest_result import BacktestResult

def test_fold_generator_rolling():
    start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2023, 6, 1, tzinfo=timezone.utc)
    
    # Train 3 months, Test 1 month
    # Folds:
    # 1: Train (Jan, Feb, Mar), Test (Apr)
    # 2: Train (Feb, Mar, Apr), Test (May)
    
    folds = FoldGenerator.generate_rolling_folds(
        start_date=start_date,
        end_date=end_date,
        train_months=3,
        test_months=1
    )
    
    assert len(folds) == 2
    assert folds[0].train_start == datetime(2023, 1, 1, tzinfo=timezone.utc)
    assert folds[0].train_end == datetime(2023, 4, 1, tzinfo=timezone.utc)
    assert folds[0].test_start == datetime(2023, 4, 1, tzinfo=timezone.utc)
    assert folds[0].test_end == datetime(2023, 5, 1, tzinfo=timezone.utc)

    assert folds[1].train_start == datetime(2023, 2, 1, tzinfo=timezone.utc)
    assert folds[1].train_end == datetime(2023, 5, 1, tzinfo=timezone.utc)
    assert folds[1].test_start == datetime(2023, 5, 1, tzinfo=timezone.utc)
    assert folds[1].test_end == datetime(2023, 6, 1, tzinfo=timezone.utc)


def test_composite_score_low_trades():
    # Less than 30 trades should penalize severely
    result = BacktestResult(
        total_trades=10,
        sortino_ratio=2.0,
        calmar_ratio=1.5,
        profit_factor=1.8,
        max_drawdown=0.1,
        initial_balance=1000.0,
        final_equity=1200.0
    )
    
    score = FitnessCalculator.calculate_composite_score(result, min_trades=30)
    assert score == -999.0

def test_composite_score_calculation():
    # Valid trade count
    result = BacktestResult(
        total_trades=40,
        sortino_ratio=2.0,  # 2.0 * 0.4 = 0.8
        calmar_ratio=1.5,   # 1.5 * 0.3 = 0.45
        profit_factor=2.0,  # 2.0 * 0.2 = 0.40
        max_drawdown=0.2,   # (1-0.2) * 0.1 = 0.08
        initial_balance=1000.0,
        final_equity=1500.0
    )
    
    # Expected: 0.8 + 0.45 + 0.40 + 0.08 = 1.73
    score = FitnessCalculator.calculate_composite_score(result, min_trades=30)
    assert pytest.approx(score, 0.01) == 1.73

def test_composite_score_penalty():
    # Valid trade count but final equity < initial balance
    result = BacktestResult(
        total_trades=40,
        sortino_ratio=0.0,
        calmar_ratio=0.0,
        profit_factor=0.5,  # 0.5 * 0.2 = 0.1
        max_drawdown=0.5,   # (1-0.5)*0.1 = 0.05
        initial_balance=1000.0,
        final_equity=800.0    # Lost money -> penalty -5.0
    )
    
    score = FitnessCalculator.calculate_composite_score(result, min_trades=30)
    # Expected: 0.1 + 0.05 - 5.0 = -4.85
    assert pytest.approx(score, 0.01) == -4.85


@pytest.mark.asyncio
async def test_sensitivity_analyzer():
    async def mock_run_backtest(params: dict) -> BacktestResult:
        # Mocking a scenario where higher TP mult yields worse results
        tp = params.get("tp_mult", 2.0)
        pnl = 1500.0 - (tp * 100) # e.g. tp 2.0 -> 1300 equity. tp 2.1 -> 1290.
        return BacktestResult(
            total_trades=50,
            sortino_ratio=1.0,
            calmar_ratio=1.0,
            profit_factor=1.0,
            max_drawdown=0.1,
            initial_balance=1000.0,
            final_equity=pnl
        )

    best_params = {"tp_mult": 2.0, "sl_mult": 1.0}
    deltas = [-0.1, 0.0, 0.1]
    
    results = SensitivityAnalyzer.analyze(
        best_params=best_params,
        target_param="tp_mult",
        deltas=deltas,
        run_backtest_fn=mock_run_backtest,
        min_trades=30
    )
    
    assert len(results) == 3
    # Check that keys are present
    assert -0.1 in results
    assert 0.0 in results
    assert 0.1 in results
