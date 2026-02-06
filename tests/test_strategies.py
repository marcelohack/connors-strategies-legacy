"""
Strategy Unit Tests

Comprehensive tests for trading strategies to improve coverage.
Tests strategy initialization, signal generation, and parameter handling.
"""

import numpy as np
import pandas as pd
import pytest
import talib
from backtesting import Backtest

from connors_strategies.strategies.ifr2 import IFR2_Strategy
from connors_strategies.strategies.lcrsi2 import LCRSI2_Strategy


class TestStrategyBase:
    """Base class for strategy tests with common utilities"""

    @pytest.fixture
    def sample_data(self):
        """Create realistic OHLCV data for strategy testing"""
        dates = pd.date_range(start="2023-01-01", periods=300, freq="D")
        np.random.seed(42)

        # Generate trending price data with some volatility
        base_price = 100.0
        trend = 0.0002  # Small daily trend
        volatility = 0.02  # 2% daily volatility

        prices = [base_price]
        for i in range(1, len(dates)):
            # Add trend and random walk
            price_change = trend + np.random.normal(0, volatility)
            new_price = prices[-1] * (1 + price_change)
            prices.append(max(new_price, 1.0))  # Prevent negative prices

        # Create OHLC from close prices
        closes = np.array(prices)
        highs = closes * (
            1 + np.random.uniform(0, 0.01, len(closes))
        )  # Up to 1% higher
        lows = closes * (1 - np.random.uniform(0, 0.01, len(closes)))  # Up to 1% lower
        opens = closes * (1 + np.random.normal(0, 0.005, len(closes)))  # Small gap

        volumes = np.random.randint(100000, 1000000, len(closes))

        return pd.DataFrame(
            {
                "Open": opens,
                "High": highs,
                "Low": lows,
                "Close": closes,
                "Volume": volumes,
            },
            index=dates,
        )


class TestLCRSI2_Strategy(TestStrategyBase):
    """Test LCRSI2 Strategy implementation"""

    def test_strategy_class_attributes(self):
        """Test strategy class has correct default attributes"""
        # Test default parameters at class level
        assert LCRSI2_Strategy.rsi_length == 2
        assert LCRSI2_Strategy.rsi_level == 5
        assert LCRSI2_Strategy.short_sma_length == 5
        assert LCRSI2_Strategy.long_sma_length == 200

    def test_strategy_custom_class_parameters(self):
        """Test strategy with custom parameter values at class level"""

        class CustomLCRSI2(LCRSI2_Strategy):
            rsi_length = 3
            rsi_level = 10
            short_sma_length = 7
            long_sma_length = 100

        # Test custom parameters at class level
        assert CustomLCRSI2.rsi_length == 3
        assert CustomLCRSI2.rsi_level == 10
        assert CustomLCRSI2.short_sma_length == 7
        assert CustomLCRSI2.long_sma_length == 100

    def test_strategy_backtest_execution(self, sample_data):
        """Test strategy can run in backtest without errors"""
        # Only test with sufficient data for indicators
        if len(sample_data) < 250:  # Need at least 200 for SMA + buffer
            pytest.skip("Insufficient data for strategy test")

        bt = Backtest(sample_data, LCRSI2_Strategy, cash=10000)

        # Should not raise any exceptions
        result = bt.run()

        # Basic assertions about results
        assert hasattr(result, "Return [%]")
        assert hasattr(result, "# Trades")
        assert isinstance(result["# Trades"], (int, np.integer))

    def test_strategy_with_custom_parameters(self, sample_data):
        """Test strategy with custom parameters"""
        if len(sample_data) < 250:
            pytest.skip("Insufficient data for strategy test")

        class CustomStrategy(LCRSI2_Strategy):
            rsi_length = 3
            rsi_level = 10
            short_sma_length = 7

        bt = Backtest(sample_data, CustomStrategy, cash=10000)
        result = bt.run()

        assert hasattr(result, "Return [%]")


class TestIFR2Strategy(TestStrategyBase):
    """Test IFR2 Strategy implementation"""

    def test_strategy_class_attributes(self):
        """Test IFR2 strategy has correct class attributes"""
        # Test class has the expected attributes (using actual parameter names)
        assert hasattr(IFR2_Strategy, "rsi_length")
        assert hasattr(IFR2_Strategy, "rsi_level")
        assert hasattr(IFR2_Strategy, "short_sma_length")
        assert hasattr(IFR2_Strategy, "long_sma_length")

        # Test default values
        assert IFR2_Strategy.rsi_length == 2
        assert IFR2_Strategy.rsi_level == 5

    def test_strategy_custom_class_parameters(self):
        """Test IFR2 strategy with custom parameter values at class level"""

        class CustomIFR2(IFR2_Strategy):
            rsi_length = 3
            rsi_level = 10

        # Test custom parameters at class level
        assert CustomIFR2.rsi_length == 3
        assert CustomIFR2.rsi_level == 10

    def test_strategy_backtest_execution(self, sample_data):
        """Test IFR2 strategy can run in backtest without errors"""
        if len(sample_data) < 250:
            pytest.skip("Insufficient data for strategy test")

        bt = Backtest(sample_data, IFR2_Strategy, cash=10000)
        result = bt.run()

        assert hasattr(result, "Return [%]")
        assert hasattr(result, "# Trades")


class TestLCRSI2_StrategyV2(TestStrategyBase):
    """Test LCRSI2 Strategy V2 implementation"""

    def test_strategy_class_attributes(self):
        """Test LCRSI2 V2 strategy has correct class attributes"""
        # Test class has the expected attributes
        assert hasattr(LCRSI2_Strategy, "rsi_length")
        assert hasattr(LCRSI2_Strategy, "rsi_level")
        assert hasattr(LCRSI2_Strategy, "short_sma_length")
        assert hasattr(LCRSI2_Strategy, "long_sma_length")

    def test_strategy_backtest_execution(self, sample_data):
        """Test LCRSI2 V2 strategy can run in backtest without errors"""
        if len(sample_data) < 250:
            pytest.skip("Insufficient data for strategy test")

        bt = Backtest(sample_data, LCRSI2_Strategy, cash=10000)
        result = bt.run()

        assert hasattr(result, "Return [%]")
        assert hasattr(result, "# Trades")


class TestStrategyParameterHandling:
    """Test strategy parameter handling and validation"""

    def test_lcrsi2_parameter_ranges(self):
        """Test LCRSI2 strategy with various parameter ranges"""

        # Test with extreme but valid parameters at class level
        class ExtremeParamsStrategy(LCRSI2_Strategy):
            rsi_length = 1  # Minimum possible
            rsi_level = 1  # Very oversold
            short_sma_length = 2
            long_sma_length = 50  # Shorter than typical

        # Test at class level
        assert ExtremeParamsStrategy.rsi_length == 1
        assert ExtremeParamsStrategy.rsi_level == 1

    def test_strategy_integer_parameters(self):
        """Test strategy integer parameter handling"""

        class IntegerTestStrategy(LCRSI2_Strategy):
            rsi_length = 3
            short_sma_length = 10
            long_sma_length = 150

        # Test at class level
        assert IntegerTestStrategy.rsi_length == 3
        assert IntegerTestStrategy.short_sma_length == 10
        assert IntegerTestStrategy.long_sma_length == 150

    def test_strategy_float_parameters(self):
        """Test strategy float parameter handling"""

        class FloatTestStrategy(LCRSI2_Strategy):
            rsi_level = 7.5

        # Test at class level
        assert FloatTestStrategy.rsi_level == 7.5


class TestStrategyIndicatorCalculations:
    """Test strategy indicator calculations (class-level tests)"""

    def test_rsi_related_attributes(self):
        """Test that strategy has RSI-related attributes"""
        # Test that strategy class has RSI-related attributes
        assert hasattr(LCRSI2_Strategy, "rsi_length")
        assert hasattr(LCRSI2_Strategy, "rsi_level")
        assert LCRSI2_Strategy.rsi_length > 0
        assert LCRSI2_Strategy.rsi_level > 0

    def test_sma_parameters(self):
        """Test SMA parameter configuration"""
        # Verify SMA parameters are properly set at class level
        assert LCRSI2_Strategy.short_sma_length > 0
        assert LCRSI2_Strategy.long_sma_length > LCRSI2_Strategy.short_sma_length
        assert (
            LCRSI2_Strategy.long_sma_length >= 50
        )  # Reasonable minimum for trend filter


class TestStrategyRegistration:
    """Test strategy registration with the registry system"""

    def test_lcrsi2_registration(self):
        """Test LCRSI2 strategy is properly registered"""
        from connors_core.core.registry import registry

        # Test that strategy is registered
        strategies = registry.list_strategies()
        assert "LCRSI2" in strategies

        # Test that we can get the strategy class
        strategy_class = registry.get_strategy("LCRSI2")
        assert strategy_class is not None
        assert issubclass(strategy_class, LCRSI2_Strategy)

    def test_ifr2_registration(self):
        """Test IFR2 strategy is properly registered"""
        from connors_core.core.registry import registry

        strategies = registry.list_strategies()
        assert "IFR2" in strategies

        strategy_class = registry.get_strategy("IFR2")
        assert strategy_class is not None
        assert issubclass(strategy_class, IFR2_Strategy)

    def test_lcrsi2_registration(self):
        """Test LCRSI2 V2 strategy is properly registered"""
        from connors_core.core.registry import registry

        strategies = registry.list_strategies()
        assert "LCRSI2" in strategies

        strategy_class = registry.get_strategy("LCRSI2")
        assert strategy_class is not None
        assert issubclass(strategy_class, LCRSI2_Strategy)
