"""Tests for BaseStrategyLogic abstract base class."""

import pytest

from connors_strategies.base_logic import BaseStrategyLogic
from tests.conftest import MockSnapshot


class ConcreteStrategy(BaseStrategyLogic):
    """Minimal concrete implementation for testing."""

    def generate_signal(self, snapshot) -> str:
        return "HOLD"


class TestBaseStrategyLogic:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseStrategyLogic()

    def test_concrete_subclass_instantiates(self):
        strategy = ConcreteStrategy()
        assert strategy is not None

    def test_concrete_subclass_returns_signal(self):
        strategy = ConcreteStrategy()
        snapshot = MockSnapshot()
        assert strategy.generate_signal(snapshot) == "HOLD"

    def test_generate_signal_is_abstract(self):
        assert hasattr(BaseStrategyLogic, "generate_signal")
        assert getattr(BaseStrategyLogic.generate_signal, "__isabstractmethod__", False)
