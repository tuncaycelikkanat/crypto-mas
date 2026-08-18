import pytest
from crypto_mas.engine.strategy.bandit_allocator import MultiArmedBanditAllocator


def test_bandit_initial_state_and_ucb():
    tactics = ["BullTactic", "BearTactic", "SidewaysTactic"]
    bandit = MultiArmedBanditAllocator(tactic_names=tactics, exploration_c=1.0)

    # Initial UCB scores should prioritize all unexplored arms
    initial_scores = bandit.calculate_ucb_scores()
    for name in tactics:
        assert initial_scores[name] == 999.0

    # Initial capital allocation should be balanced
    weights = bandit.get_capital_allocation_weights()
    assert pytest.approx(sum(weights.values()), 0.01) == 1.0
    for name in tactics:
        assert weights[name] > 0.0


def test_bandit_adapts_to_winning_tactic():
    tactics = ["BullTactic", "BearTactic", "SidewaysTactic"]
    bandit = MultiArmedBanditAllocator(tactic_names=tactics, exploration_c=1.0)

    # Simulate BullTactic winning consistently in a bull market
    for _ in range(20):
        bandit.record_outcome("BullTactic", return_pct=5.0)

    # Simulate BearTactic losing
    for _ in range(10):
        bandit.record_outcome("BearTactic", return_pct=-3.0)

    # Sideways breaking even
    for _ in range(10):
        bandit.record_outcome("SidewaysTactic", return_pct=0.2)

    weights = bandit.get_capital_allocation_weights()
    
    # BullTactic should have the highest allocated weight
    assert weights["BullTactic"] > weights["BearTactic"]
    assert weights["BullTactic"] > weights["SidewaysTactic"]
    assert pytest.approx(sum(weights.values()), 0.01) == 1.0

    # Thompson Sampling should heavily favor BullTactic
    sampled = [bandit.sample_thompson() for _ in range(100)]
    bull_count = sampled.count("BullTactic")
    assert bull_count >= 50
