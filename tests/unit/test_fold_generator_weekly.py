"""Unit tests for weekly rolling folds in FoldGenerator."""
from datetime import UTC, datetime

from crypto_mas.engine.optimization.fold_generator import FoldGenerator


def test_generate_weekly_rolling_folds():
    start = datetime(2022, 1, 1, tzinfo=UTC)
    end = datetime(2022, 3, 1, tzinfo=UTC)  # ~8 weeks

    folds = FoldGenerator.generate_weekly_rolling_folds(
        start_date=start,
        end_date=end,
        train_weeks=4,
        test_weeks=1,
        step_weeks=1,
    )

    assert len(folds) >= 3
    assert folds[0].fold_id == 1
    assert (folds[0].train_end - folds[0].train_start).days == 28  # 4 weeks
    assert (folds[0].test_end - folds[0].test_start).days == 7   # 1 week
