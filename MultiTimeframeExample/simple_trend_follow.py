"""
Simple Multi-Timeframe Trend Following Strategy

A beginner-friendly example showing the basics of multi-timeframe analysis.

This strategy uses:
- Weekly timeframe: Long-term trend direction (SMA 10)
- Daily timeframe: Entry signals and trade execution

Strategy Rules:
- Enter long when daily price > daily SMA(5) AND weekly price > weekly SMA(10)
- Exit when daily price < daily SMA(5)

This is a simplified example perfect for learning multi-timeframe concepts.
"""

import talib
import pandas as pd
from typing import Any, Dict

from connors.core.registry import registry
from connors.strategies.multitimeframe.base import MultiTimeframeStrategy


@registry.register_strategy("SimpleTrendFollow")
class SimpleTrendFollowStrategy(MultiTimeframeStrategy):
    """
    Simple trend following strategy using weekly and daily timeframes

    Perfect for beginners to understand multi-timeframe concepts.
    """

    # Use only 2 timeframes to keep it simple
    timeframes = ['1wk', '1d']  # Weekly trend + daily execution
    primary_timeframe = '1d'    # Trade on daily bars

    # Simple parameters
    weekly_sma_period = 10  # Weekly trend SMA (shorter period for more trades)
    daily_sma_period = 5    # Daily entry/exit SMA

    def __init__(self, broker=None, data=None, params=None):
        super().__init__(broker, data, params)

    def _init_indicators(self):
        """Initialize simple indicators"""

        # Weekly trend SMA
        weekly_data = self.get_timeframe_data('1wk')
        self.weekly_sma = self.I(
            lambda x: talib.SMA(x, timeperiod=self.weekly_sma_period),
            weekly_data.Close,
            name=f'Weekly_SMA_{self.weekly_sma_period}'
        )

        # Daily entry/exit SMA
        daily_data = self.get_timeframe_data('1d')
        self.daily_sma = self.I(
            lambda x: talib.SMA(x, timeperiod=self.daily_sma_period),
            daily_data.Close,
            name=f'Daily_SMA_{self.daily_sma_period}'
        )

    def next(self):
        """Simple trading logic"""

        current_price = self.data.Close[-1]
        current_date = self.data.index[-1] if hasattr(self.data, "index") else f"Bar {len(self.data) - 1}"

        # Check if we have enough data
        if (len(self.weekly_sma) == 0 or pd.isna(self.weekly_sma[-1]) or
            len(self.daily_sma) == 0 or pd.isna(self.daily_sma[-1])):
            return

        # Get indicator values
        weekly_sma_value = self.weekly_sma[-1]
        daily_sma_value = self.daily_sma[-1]

        # Weekly trend check
        weekly_uptrend = current_price > weekly_sma_value

        # Daily signal check
        daily_above_sma = current_price > daily_sma_value
        daily_below_sma = current_price < daily_sma_value

        # Log current market conditions (DEBUG level)
        self.logger.debug(
            f"Market data - Date: {current_date}, Price: {current_price:.2f}, "
            f"Weekly_SMA: {weekly_sma_value:.2f}, Daily_SMA: {daily_sma_value:.2f}"
        )

        # Trading logic
        if not self.position:
            # Enter long when both conditions are met
            if weekly_uptrend and daily_above_sma:
                self.logger.info(
                    f"🟢 BUY signal - Weekly uptrend (price {current_price:.2f} > Weekly_SMA {weekly_sma_value:.2f}) "
                    f"AND Daily strength (price {current_price:.2f} > Daily_SMA {daily_sma_value:.2f})"
                )
                self.logger.info(f"💰 EXECUTING BUY at {current_price:.2f} on {current_date}")
                self.buy(size=1)
        else:
            # Exit when daily condition fails
            if daily_below_sma:
                entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
                if entry_price:
                    profit_loss = ((current_price - entry_price) / entry_price * 100)
                    self.logger.info(
                        f"🔴 SELL signal - Price {current_price:.2f} < Daily_SMA {daily_sma_value:.2f}"
                    )
                    self.logger.info(
                        f"💸 EXECUTING SELL at {current_price:.2f} on {current_date} "
                        f"(Entry: {entry_price:.2f}, P&L: {profit_loss:.2f}%)"
                    )
                else:
                    self.logger.info(
                        f"🔴 SELL signal - Price {current_price:.2f} < Daily_SMA {daily_sma_value:.2f}"
                    )
                    self.logger.info(f"💸 EXECUTING SELL at {current_price:.2f} on {current_date}")
                self.position.close()

    def get_strategy_metadata(self) -> Dict[str, Any]:
        """Strategy information"""
        metadata = super().get_strategy_metadata()
        metadata.update({
            "strategy_type": "Simple Trend Following",
            "description": "Basic multi-timeframe trend following for beginners",
            "complexity": "Beginner",
            "weekly_sma_period": self.weekly_sma_period,
            "daily_sma_period": self.daily_sma_period,
        })
        return metadata


if __name__ == "__main__":
    print("Simple Multi-Timeframe Trend Following Strategy")
    print("=" * 50)

    strategy = SimpleTrendFollowStrategy()
    metadata = strategy.get_strategy_metadata()

    for key, value in metadata.items():
        print(f"{key}: {value}")

    print("\nTo run this strategy:")
    print("python -m connors.cli.backtest \\")
    print("  --external-strategy ~/.connors/strategies/MultiTimeframeExample/simple_trend_follow.py \\")
    print("  --strategy SimpleTrendFollow \\")
    print("  --tickers AAPL \\")
    print("  --timeframes 1wk,1d \\")
    print("  --primary-timeframe 1d")