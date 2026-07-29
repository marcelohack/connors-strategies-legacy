"""Tests for connors_strategies package imports and structure."""


def test_package_imports():
    """Package exports BaseStrategyLogic and RSI2Logic."""
    from connors_strategies import BaseStrategyLogic, RSI2Logic

    assert BaseStrategyLogic is not None
    assert RSI2Logic is not None


def test_all_exports():
    """__all__ contains the expected exports."""
    import connors_strategies

    assert "BaseStrategyLogic" in connors_strategies.__all__
    assert "RSI2Logic" in connors_strategies.__all__


def test_base_logic_is_abstract():
    """BaseStrategyLogic cannot be instantiated directly."""
    import pytest

    from connors_strategies import BaseStrategyLogic

    with pytest.raises(TypeError):
        BaseStrategyLogic()


def test_rsi2_is_subclass():
    """RSI2Logic inherits from BaseStrategyLogic."""
    from connors_strategies import BaseStrategyLogic, RSI2Logic

    assert issubclass(RSI2Logic, BaseStrategyLogic)
