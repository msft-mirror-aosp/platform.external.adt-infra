import pytest
from typing import List, Tuple
import time
import numpy as np

from emu.recording.screen_grab import (
    ScreenGrabStrategy,
    ScreenGrabStrategyFactory,
    MSSStrategy,
    PILStrategy,
    PyScreezeStrategy,
)


def get_available_strategies() -> List[Tuple[str, ScreenGrabStrategy]]:
    """Get all available screen grab strategies that can be initialized."""
    strategies = []
    for strategy_name in ScreenGrabStrategyFactory.PREFERRED_ORDER:
        try:
            strategy = ScreenGrabStrategyFactory.create_strategy(strategy_name)
            strategies.append((strategy_name, strategy))
        except Exception:
            continue
    return strategies


@pytest.fixture(scope="session")
def strategies():
    """Fixture that provides all available strategies."""
    return get_available_strategies()


def test_strategy_availability(strategies):
    """Verify that at least one strategy is available for testing."""
    assert len(strategies) > 0, "No screen grab strategies available for testing"
    for name, strategy in strategies:
        assert isinstance(strategy, ScreenGrabStrategy)
        print(f"Strategy available: {name}")


@pytest.mark.benchmark(group="initialization", min_rounds=5, max_time=30.0)
@pytest.mark.parametrize("strategy_name", ScreenGrabStrategyFactory.PREFERRED_ORDER)
def test_strategy_initialization(benchmark, strategy_name):
    """Benchmark strategy initialization time."""

    def init_strategy():
        try:
            return ScreenGrabStrategyFactory.create_strategy(strategy_name)
        except Exception:
            return None

    strategy = benchmark(init_strategy)
    if strategy is not None:
        assert isinstance(strategy, ScreenGrabStrategy)


@pytest.mark.benchmark(group="screen_capture", min_rounds=50, max_time=30.0)
@pytest.mark.parametrize("strategy_name", ScreenGrabStrategyFactory.PREFERRED_ORDER)
def test_screen_capture_performance(benchmark, strategy_name):
    """Benchmark screen capture performance for each available strategy."""
    strategy = ScreenGrabStrategyFactory.create_strategy(strategy_name)

    def capture_screen():
        frame = strategy.grab_screen()
        assert isinstance(frame, np.ndarray)
        assert len(frame.shape) == 3  # Should be a 3D array (height, width, channels)
        assert frame.shape[2] == 3  # Should have 3 color channels (BGR)
        return frame

    benchmark(capture_screen)


@pytest.mark.benchmark(group="screen_size", min_rounds=50, max_time=30.0)
@pytest.mark.parametrize("strategy_name", ScreenGrabStrategyFactory.PREFERRED_ORDER)
def test_get_screen_size_performance(benchmark, strategy_name):
    """Benchmark get_screen_size performance for each available strategy."""
    strategy = ScreenGrabStrategyFactory.create_strategy(strategy_name)

    def get_size():
        size = strategy.get_screen_size()
        assert isinstance(size, tuple)
        assert len(size) == 2
        assert all(isinstance(dim, int) for dim in size)
        return size

    benchmark(get_size)
