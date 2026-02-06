"""
Multi-Timeframe Momentum Strategy - External Strategy Example

This strategy demonstrates how to create external multi-timeframe strategies
that can be used with the Connors backtesting framework.

Strategy Logic:
- Weekly timeframe: Check if price > 50-week SMA (long-term trend)
- Daily timeframe: Check if RSI(14) > 50 (momentum confirmation)
- Hourly timeframe: Entry when price breaks above 20-hour SMA
- Exit when price falls below 10-hour SMA

This is a complete working example showing:
1. How to inherit from MultiTimeframeStrategy
2. How to configure timeframes and primary timeframe
3. How to access different timeframe data
4. How to implement multi-timeframe trading logic
5. How to register the strategy for external use
"""

import talib
import pandas as pd
from typing import Any, Dict

# Import the registry system - this is required for external strategies
from connors.core.registry import registry
from connors.strategies.multitimeframe.base import MultiTimeframeStrategy


@registry.register_strategy("MultiTF_Momentum")
class MultiTimeframeMomentumStrategy(MultiTimeframeStrategy):
    """
    Multi-Timeframe Momentum Strategy

    This strategy combines multiple timeframes for robust trade signals:
    - Weekly: Long-term trend filter using SMA
    - Daily: Momentum confirmation using RSI
    - Hourly: Entry/exit timing using SMAs

    The strategy only takes long positions when all conditions align.
    """

    # REQUIRED: Define the timeframes this strategy uses
    # Order matters - data will be fetched for these timeframes
    timeframes = ['1wk', '1d', '1h']

    # REQUIRED: Define which timeframe to use for trade execution
    # This should be the shortest timeframe for best precision
    primary_timeframe = '1h'

    # Strategy Parameters - these can be overridden via CLI/Streamlit
    weekly_sma_period = 50      # Weekly trend SMA
    daily_rsi_period = 14       # Daily momentum RSI
    hourly_entry_sma = 20       # Hourly entry SMA
    hourly_exit_sma = 10        # Hourly exit SMA

    def __init__(self, broker=None, data=None, params=None):
        """Initialize the strategy"""
        super().__init__(broker, data, params)

    def _init_indicators(self):
        """
        Initialize indicators for each timeframe

        This method is called automatically and should set up all
        technical indicators needed for the strategy.
        """

        # Initialize indicators based on available timeframes
        available_timeframes = list(self.tf_data.keys()) if hasattr(self, 'tf_data') and self.tf_data else []

        # Weekly timeframe indicators - long-term trend
        if '1wk' in available_timeframes:
            weekly_data = self.get_timeframe_data('1wk')
            self.weekly_trend_sma = self.I(
                lambda x: talib.SMA(x, timeperiod=self.weekly_sma_period),
                weekly_data.Close,
                name=f'Weekly_SMA_{self.weekly_sma_period}'
            )
        else:
            self.weekly_trend_sma = None

        # Daily timeframe indicators - momentum
        if '1d' in available_timeframes:
            daily_data = self.get_timeframe_data('1d')
            self.daily_rsi = self.I(
                lambda x: talib.RSI(x, timeperiod=self.daily_rsi_period),
                daily_data.Close,
                name=f'Daily_RSI_{self.daily_rsi_period}'
            )
        else:
            self.daily_rsi = None

        # Hourly timeframe indicators - entry/exit timing
        if '1h' in available_timeframes:
            hourly_data = self.get_timeframe_data('1h')
            self.hourly_entry_sma = self.I(
                lambda x: talib.SMA(x, timeperiod=self.hourly_entry_sma),
                hourly_data.Close,
                name=f'Hourly_Entry_SMA_{self.hourly_entry_sma}'
            )
            self.hourly_exit_sma = self.I(
                lambda x: talib.SMA(x, timeperiod=self.hourly_exit_sma),
                hourly_data.Close,
                name=f'Hourly_Exit_SMA_{self.hourly_exit_sma}'
            )
        else:
            # If hourly not available, use daily data for entry/exit
            if '1d' in available_timeframes:
                daily_data = self.get_timeframe_data('1d')
                self.hourly_entry_sma = self.I(
                    lambda x: talib.SMA(x, timeperiod=self.hourly_entry_sma),
                    daily_data.Close,
                    name=f'Daily_Entry_SMA_{self.hourly_entry_sma}'
                )
                self.hourly_exit_sma = self.I(
                    lambda x: talib.SMA(x, timeperiod=self.hourly_exit_sma),
                    daily_data.Close,
                    name=f'Daily_Exit_SMA_{self.hourly_exit_sma}'
                )
            else:
                self.hourly_entry_sma = None
                self.hourly_exit_sma = None

    def next(self):
        """
        Main trading logic executed on each bar

        This is called for each bar in the primary timeframe.
        We check conditions across all available timeframes before making trades.
        """

        # Get current price and date (from primary timeframe)
        current_price = self.data.Close[-1]
        current_date = self.data.index[-1] if hasattr(self.data, "index") else f"Bar {len(self.data) - 1}"

        # === WEEKLY TREND CHECK ===
        weekly_uptrend = True  # Default to True if no weekly data
        weekly_sma_current = None
        if self.weekly_trend_sma is not None:
            # Ensure we have enough data for weekly SMA
            if len(self.weekly_trend_sma) == 0 or pd.isna(self.weekly_trend_sma[-1]):
                return  # Skip this bar

            weekly_sma_current = self.weekly_trend_sma[-1]
            weekly_uptrend = current_price > weekly_sma_current

        # === DAILY MOMENTUM CHECK ===
        daily_momentum_positive = True  # Default to True if no daily data
        daily_rsi_current = 50  # Default neutral RSI
        if self.daily_rsi is not None:
            # Ensure we have enough data for daily RSI
            if len(self.daily_rsi) == 0 or pd.isna(self.daily_rsi[-1]):
                return  # Skip this bar

            daily_rsi_current = self.daily_rsi[-1]
            daily_momentum_positive = daily_rsi_current > 50

        # === ENTRY/EXIT TIMING CHECKS ===
        if self.hourly_entry_sma is None or self.hourly_exit_sma is None:
            return  # Need at least entry/exit indicators

        # Ensure we have enough data for entry/exit SMAs
        if (len(self.hourly_entry_sma) == 0 or pd.isna(self.hourly_entry_sma[-1]) or
            len(self.hourly_exit_sma) == 0 or pd.isna(self.hourly_exit_sma[-1])):
            return

        hourly_entry_sma_current = self.hourly_entry_sma[-1]
        hourly_exit_sma_current = self.hourly_exit_sma[-1]

        # Entry condition: price above entry SMA
        entry_signal = current_price > hourly_entry_sma_current

        # Exit condition: price below exit SMA
        exit_signal = current_price < hourly_exit_sma_current

        # Format weekly SMA for logging
        weekly_sma_str = f"{weekly_sma_current:.2f}" if weekly_sma_current is not None else "N/A"

        # Log current market conditions (DEBUG level)
        self.logger.debug(
            f"Market data - Date: {current_date}, Price: {current_price:.2f}, "
            f"Weekly_SMA: {weekly_sma_str}, "
            f"Daily_RSI: {daily_rsi_current:.1f}, "
            f"Entry_SMA: {hourly_entry_sma_current:.2f}, Exit_SMA: {hourly_exit_sma_current:.2f}"
        )

        # === TRADING LOGIC ===

        if not self.position:
            # No position - check for entry
            if weekly_uptrend and daily_momentum_positive and entry_signal:
                # All conditions met - enter long position
                self.logger.info(
                    f"🟢 BUY signal - Weekly uptrend (price {current_price:.2f} > SMA {weekly_sma_str}), "
                    f"Daily momentum positive (RSI {daily_rsi_current:.1f} > 50), "
                    f"Hourly breakout (price {current_price:.2f} > Entry_SMA {hourly_entry_sma_current:.2f})"
                )
                self.logger.info(f"💰 EXECUTING BUY at {current_price:.2f} on {current_date}")
                self.buy(size=1)

        else:
            # Have position - check for exit
            if exit_signal:
                # Exit condition met - close position
                entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
                if entry_price:
                    profit_loss = ((current_price - entry_price) / entry_price * 100)
                    self.logger.info(
                        f"🔴 SELL signal - Price {current_price:.2f} < Exit_SMA {hourly_exit_sma_current:.2f}"
                    )
                    self.logger.info(
                        f"💸 EXECUTING SELL at {current_price:.2f} on {current_date} "
                        f"(Entry: {entry_price:.2f}, P&L: {profit_loss:.2f}%)"
                    )
                else:
                    self.logger.info(
                        f"🔴 SELL signal - Price {current_price:.2f} < Exit_SMA {hourly_exit_sma_current:.2f}"
                    )
                    self.logger.info(f"💸 EXECUTING SELL at {current_price:.2f} on {current_date}")
                self.position.close()

    def get_strategy_metadata(self) -> Dict[str, Any]:
        """
        Return strategy metadata for display and logging

        This method provides information about the strategy that can be
        displayed in results and used for documentation.
        """
        metadata = super().get_strategy_metadata()
        metadata.update({
            "strategy_type": "Multi-Timeframe Momentum",
            "description": "Uses weekly trend, daily momentum, and hourly timing",
            "timeframes_used": self.timeframes,
            "primary_timeframe": self.primary_timeframe,
            "weekly_sma_period": self.weekly_sma_period,
            "daily_rsi_period": self.daily_rsi_period,
            "hourly_entry_sma": self.hourly_entry_sma,
            "hourly_exit_sma": self.hourly_exit_sma,
            "trade_direction": "Long only",
            "complexity": "Advanced - Multi-timeframe analysis"
        })
        return metadata


# Example usage and testing
if __name__ == "__main__":
    """
    This section shows how to test the strategy locally
    """
    print("Multi-Timeframe Momentum Strategy")
    print("=" * 40)

    # Create strategy instance for testing
    strategy = MultiTimeframeMomentumStrategy()

    # Print strategy information
    metadata = strategy.get_strategy_metadata()
    for key, value in metadata.items():
        print(f"{key}: {value}")

    print("\nTo run this strategy:")
    print("python -m connors.cli.backtest \\")
    print("  --external-strategy ~/.connors/strategies/MultiTimeframeExample/multi_tf_momentum.py \\")
    print("  --strategy MultiTF_Momentum \\")
    print("  --tickers AAPL \\")
    print("  --config america \\")
    print("  --datasource yfinance \\")
    print("  --timeframes 1wk,1d,1h \\")
    print("  --primary-timeframe 1h \\")
    print("  --start 2024-01-01 \\")
    print("  --end 2024-06-01")