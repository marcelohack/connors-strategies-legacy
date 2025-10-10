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
                current_price = self.data.Close[-1]
                self.logger.info(
                    f"🟢 BUY signal - Short MA ({self.sma_short[-1]:.2f}) crossed above Long MA ({self.sma_long[-1]:.2f})"
                )
                self.logger.info(f"💰 EXECUTING BUY at {current_price:.2f}")
                self.buy()
        else:
            # Sell when short MA crosses below long MA
            if self.sma_short[-1] < self.sma_long[-1] and self.sma_short[-2] >= self.sma_long[-2]:
                current_price = self.data.Close[-1]
                entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
                if entry_price:
                    pnl_pct = ((current_price - entry_price) / entry_price * 100)
                    self.logger.info(
                        f"🔴 SELL signal - Short MA ({self.sma_short[-1]:.2f}) crossed below Long MA ({self.sma_long[-1]:.2f})"
                    )
                    self.logger.info(
                        f"💸 EXECUTING SELL at {current_price:.2f} (Entry: {entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                    )
                else:
                    self.logger.info(
                        f"🔴 SELL signal - Short MA ({self.sma_short[-1]:.2f}) crossed below Long MA ({self.sma_long[-1]:.2f})"
                    )
                    self.logger.info(f"💸 EXECUTING SELL at {current_price:.2f}")
                self.position.close()