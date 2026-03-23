"""Tests for connors_strategies package imports and structure."""


def test_package_imports():
    """Package exports BaseStrategyLogic and LCRSI2Logic."""
    from connors_strategies import BaseStrategyLogic, LCRSI2Logic

    assert BaseStrategyLogic is not None
    assert LCRSI2Logic is not None


def test_all_exports():
    """__all__ contains the expected exports."""
    import connors_strategies

    assert "BaseStrategyLogic" in connors_strategies.__all__
    assert "LCRSI2Logic" in connors_strategies.__all__


def test_base_logic_is_abstract():
    """BaseStrategyLogic cannot be instantiated directly."""
    import pytest

    from connors_strategies import BaseStrategyLogic

    with pytest.raises(TypeError):
        BaseStrategyLogic()


def test_lcrsi2_is_subclass():
    """LCRSI2Logic inherits from BaseStrategyLogic."""
    from connors_strategies import BaseStrategyLogic, LCRSI2Logic

    assert issubclass(LCRSI2Logic, BaseStrategyLogic)
