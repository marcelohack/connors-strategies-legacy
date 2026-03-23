"""Shared test fixtures for connors_strategies tests."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

import pytest


@dataclass
class MockBar:
    """Simple mock for MarketBar protocol."""

    timestamp: datetime = field(default_factory=datetime.now)
    open: Decimal = Decimal("100.00")
    high: Decimal = Decimal("105.00")
    low: Decimal = Decimal("95.00")
    close: Decimal = Decimal("102.00")
    volume: int = 1000


@dataclass
class MockSnapshot:
    """Simple mock for MarketSnapshot protocol."""

    _bar: MockBar = field(default_factory=MockBar)
    _indicators: Dict[str, Optional[Decimal]] = field(default_factory=dict)

    @property
    def bar(self) -> MockBar:
        return self._bar

    @property
    def indicators(self) -> Dict[str, Optional[Decimal]]:
        return self._indicators

    def get_indicator(self, name: str) -> Optional[Decimal]:
        return self._indicators.get(name)

    def get_bar(self, offset: int = 0) -> Optional[MockBar]:
        if offset == 0:
            return self._bar
        return None

    @property
    def bar_count(self) -> int:
        return 1


@pytest.fixture
def mock_bar():
    """Create a mock bar with default values."""
    return MockBar()


@pytest.fixture
def mock_snapshot():
    """Create a mock snapshot with default values."""
    return MockSnapshot()


def make_snapshot(
    close: float = 102.0,
    rsi_2: Optional[float] = None,
    sma_5: Optional[float] = None,
    sma_200: Optional[float] = None,
) -> MockSnapshot:
    """Helper to create a snapshot with common indicators."""
    bar = MockBar(close=Decimal(str(close)))
    indicators: Dict[str, Optional[Decimal]] = {}
    if rsi_2 is not None:
        indicators["RSI_2"] = Decimal(str(rsi_2))
    if sma_5 is not None:
        indicators["SMA_5"] = Decimal(str(sma_5))
    if sma_200 is not None:
        indicators["SMA_200"] = Decimal(str(sma_200))
    return MockSnapshot(_bar=bar, _indicators=indicators)
