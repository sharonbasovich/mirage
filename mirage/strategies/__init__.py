"""Strategy library.

Each strategy is a declarative config producing a target-position schedule;
a parameter grid = a set of trials.
"""

from mirage.strategies.base import (
    STRATEGIES,
    Strategy,
    StrategySpec,
    build_strategy,
    param_grid,
)
from mirage.strategies import library as _library  # noqa: F401  (registers families)
from mirage.strategies import ml as _ml  # noqa: F401

__all__ = ["STRATEGIES", "Strategy", "StrategySpec", "build_strategy", "param_grid"]
