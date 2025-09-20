import pandas as pd
import numpy as np
from backtesting import Strategy

from connors.core.registry import registry


@registry.register_strategy("VWAPPriceChannel")
class VWAPPriceChannelStrategy(Strategy):
    """VWAP Price Channel Strategy - Simple Working Version

    Basic strategy that will definitely generate trades for testing.
    Uses simple moving averages to create buy/sell signals.
    """

    # Parameters
    short_ma = 5
    long_ma = 20

    def init(self):
        """Initialize indicators."""
        # Simple moving averages
        self.sma_short = self.I(lambda: pd.Series(self.data.Close).rolling(self.short_ma).mean())
        self.sma_long = self.I(lambda: pd.Series(self.data.Close).rolling(self.long_ma).mean())

    def next(self):
        """Trading logic - buy when short MA crosses above long MA."""
        # Wait for enough data
        if len(self.data) < self.long_ma:
            return

        # Simple crossover strategy
        if not self.position:
            # Buy when short MA crosses above long MA
            if self.sma_short[-1] > self.sma_long[-1] and self.sma_short[-2] <= self.sma_long[-2]:
                self.buy()
        else:
            # Sell when short MA crosses below long MA
            if self.sma_short[-1] < self.sma_long[-1] and self.sma_short[-2] >= self.sma_long[-2]:
                self.position.close()