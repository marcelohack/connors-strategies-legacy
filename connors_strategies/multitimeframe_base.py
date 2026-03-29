"""
Multi-Timeframe Strategy Base Classes

Provides foundation classes for strategies that analyze multiple timeframes.
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from backtesting import Strategy
from connors_core.core.logging import setup_strategy_logger


class MultiTimeframeStrategy(Strategy):
    """
    Base class for multi-timeframe trading strategies

    This class extends the standard backtesting.Strategy to provide access to
    multiple timeframe datasets within a single strategy.

    Attributes:
        timeframes: List of timeframes to analyze (e.g., ['1w', '1d', '1h'])
        primary_timeframe: Main timeframe for trade execution (e.g., '1h')
        tf_data: Dictionary containing data for each timeframe
    """

    # Strategy configuration - override in child classes
    timeframes: List[str] = []  # e.g., ['1w', '1d', '1h']
    primary_timeframe: Optional[str] = None  # e.g., '1h'
    log_level: str = "INFO"  # Logging level (DEBUG, INFO, WARNING, ERROR)

    def __init__(self, broker=None, data=None, params=None):
        # Always call parent with provided arguments
        # If no arguments provided, Strategy will raise error, which is expected
        super().__init__(broker, data, params)
        self.tf_data: Dict[str, pd.DataFrame] = {}
        self._tf_indicators: Dict[str, Dict[str, Any]] = {}

        # Set up colorful logger
        strategy_name = self.__class__.__name__
        self.logger = setup_strategy_logger(strategy_name, level=self.log_level)

    def init(self):
        """
        Initialize strategy indicators

        Override this method in child strategies to set up indicators
        for each timeframe using get_timeframe_data()
        """
        # Validate timeframe configuration
        if not self.timeframes:
            raise ValueError("Multi-timeframe strategies must define 'timeframes' attribute")

        if not self.primary_timeframe:
            # Auto-set primary timeframe to the lowest/shortest timeframe
            self.primary_timeframe = self._get_shortest_timeframe()

        # Ensure primary timeframe is in the list
        if self.primary_timeframe not in self.timeframes:
            raise ValueError(f"Primary timeframe '{self.primary_timeframe}' must be in timeframes list: {self.timeframes}")

        # Log initialization
        self.logger.info(
            f"✨ Initializing multi-timeframe strategy: "
            f"timeframes={self.timeframes}, primary={self.primary_timeframe}"
        )

        # Initialize child-specific indicators
        self._init_indicators()

        self.logger.info("✅ Multi-timeframe strategy initialization completed")

    def _init_indicators(self):
        """
        Override this method in child strategies to define indicators

        Example:
            # Weekly trend
            weekly_data = self.get_timeframe_data('1w')
            self.weekly_sma = self.I(talib.SMA, weekly_data.Close, 20)

            # Daily momentum
            daily_data = self.get_timeframe_data('1d')
            self.daily_rsi = self.I(talib.RSI, daily_data.Close, 14)
        """
        pass

    def get_timeframe_data(self, timeframe: str) -> pd.DataFrame:
        """
        Get data for a specific timeframe

        Args:
            timeframe: The timeframe to get data for (e.g., '1w', '1d', '1h')

        Returns:
            DataFrame with OHLCV data for the specified timeframe

        Raises:
            ValueError: If timeframe is not available
        """
        if timeframe not in self.tf_data:
            raise ValueError(f"Timeframe '{timeframe}' not available. Available: {list(self.tf_data.keys())}")

        return self.tf_data[timeframe]

    def _get_shortest_timeframe(self) -> str:
        """
        Determine the shortest timeframe from the timeframes list

        Returns:
            The shortest timeframe (e.g., '1h' from ['1w', '1d', '1h'])
        """
        # Define timeframe hierarchy (shortest to longest)
        timeframe_order = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240,
            '1d': 1440, '1w': 10080, '1M': 43200
        }

        # Find the shortest timeframe in our list
        available_tfs = [(tf, timeframe_order.get(tf, float('inf'))) for tf in self.timeframes]
        available_tfs.sort(key=lambda x: x[1])

        if not available_tfs:
            raise ValueError("No valid timeframes found")

        return available_tfs[0][0]

    def set_timeframe_data(self, tf_data: Dict[str, pd.DataFrame]):
        """
        Set the multi-timeframe data (called by BacktestService)

        Args:
            tf_data: Dictionary mapping timeframes to their respective DataFrames
        """
        self.tf_data = tf_data

        # Set the primary timeframe as the main self.data for backtesting.py compatibility
        if self.primary_timeframe and self.primary_timeframe in tf_data:
            # Note: This will be handled by the backtesting engine
            pass

    def get_current_timeframe_values(self, timeframe: str, indicator_name: str, lookback: int = 0) -> Any:
        """
        Get current value(s) from a timeframe-specific indicator

        Args:
            timeframe: The timeframe to get data from
            indicator_name: Name of the indicator
            lookback: How many periods back to look (0 = current)

        Returns:
            Current or historical indicator value
        """
        if timeframe not in self._tf_indicators:
            raise ValueError(f"No indicators found for timeframe '{timeframe}'")

        if indicator_name not in self._tf_indicators[timeframe]:
            raise ValueError(f"Indicator '{indicator_name}' not found for timeframe '{timeframe}'")

        indicator = self._tf_indicators[timeframe][indicator_name]
        if lookback == 0:
            return indicator[-1]
        else:
            return indicator[-1-lookback:-1] if lookback > 0 else indicator[-1:]

    def is_multitimeframe_strategy(self) -> bool:
        """
        Check if this is a multi-timeframe strategy

        Returns:
            True if this strategy uses multiple timeframes
        """
        return len(self.timeframes) > 1

    def get_strategy_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this strategy's timeframe configuration

        Returns:
            Dictionary with strategy metadata
        """
        return {
            "is_multitimeframe": self.is_multitimeframe_strategy(),
            "timeframes": self.timeframes,
            "primary_timeframe": self.primary_timeframe,
            "total_timeframes": len(self.timeframes)
        }
