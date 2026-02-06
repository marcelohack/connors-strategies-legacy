"""Larry Connors 2-Period RSI Strategy - Vectorized talipp Version

This implementation uses vectorized talipp indicators with backtesting.py's self.I() interface.

Key Features:
- Uses self.I() for automatic caching and plotting
- Cleaner code with vectorized indicators
- Same talipp logic as incremental version
- Automatic indicator visualization in backtesting plots

Comparison with Incremental Version:
+---------------------+-------------------------+---------------------------+
| Feature             | Incremental (talipp)    | Vectorized (self.I)       |
+---------------------+-------------------------+---------------------------+
| Update Method       | .update() in next()     | Automatic vectorization   |
| Plotting            | Manual                  | Automatic via self.I()    |
| Caching             | Manual                  | Automatic                 |
| Code Complexity     | More verbose            | Cleaner, simpler          |
| Live Trading        | ✅ O(1) incremental     | ❌ Needs full recalc      |
| Backtesting         | ✅ Works                | ✅ Optimized              |
+---------------------+-------------------------+---------------------------+

Recommendation:
- Use this vectorized version for backtesting/research
- Use incremental version for live trading bots
- Same talipp logic ensures consistent results
"""

from backtesting import Strategy
from connors_core.core.registry import registry
from connors_core.core.logging import setup_strategy_logger
from connors_core.indicators.talipp_backtesting import talipp_rsi, talipp_sma


@registry.register_strategy("LCRSI2_vectorized")
class LCRSI2VectorizedStrategy(Strategy):
    """
    Larry Connors RSI(2) Strategy using vectorized talipp indicators.

    Entry Rules:
    - RSI(2) < 5 (oversold condition)
    - Price > SMA(200) (uptrend filter)

    Exit Rules:
    - Price >= SMA(5) (mean reversion complete)

    Implementation:
    - Uses self.I() for automatic caching and plotting
    - Vectorized talipp indicators for clean code
    - Same logic as incremental version
    """

    # Strategy parameters
    rsi_length = 2
    rsi_level = 5
    short_sma_length = 5
    long_sma_length = 200

    def init(self):
        """Initialize indicators using self.I() interface"""
        # Logger
        self.logger = setup_strategy_logger("LCRSI2_vectorized")
        self.logger.info(
            f"✨ Initializing LCRSI2_vectorized with RSI={self.rsi_length}, "
            f"RSI level={self.rsi_level}, Short SMA={self.short_sma_length}, "
            f"Long SMA={self.long_sma_length}"
        )

        # Vectorized indicators with self.I() - automatically cached and plotted
        self.rsi = self.I(talipp_rsi, self.data.Close, self.rsi_length)
        self.short_sma = self.I(talipp_sma, self.data.Close, self.short_sma_length)
        self.long_sma = self.I(talipp_sma, self.data.Close, self.long_sma_length)

        self.logger.info("✅ Indicators initialized (vectorized with self.I)")

    def next(self):
        """Execute strategy logic on each bar"""
        close = self.data.Close[-1]
        current_rsi = self.rsi[-1]
        current_short_sma = self.short_sma[-1]
        current_long_sma = self.long_sma[-1]

        # Skip if indicators not ready (NaN values)
        if (
            current_rsi is None
            or current_short_sma is None
            or current_long_sma is None
        ):
            return

        # Get current date for logging
        current_date = (
            self.data.index[-1]
            if hasattr(self.data, "index")
            else f"Bar {len(self.data) - 1}"
        )

        # Debug log
        self.logger.debug(
            f"{current_date} | Close: {close:.2f} | "
            f"RSI({self.rsi_length}): {current_rsi:.2f} | "
            f"SMA{self.short_sma_length}: {current_short_sma:.2f} | "
            f"SMA{self.long_sma_length}: {current_long_sma:.2f}"
        )

        # Entry Logic
        if not self.position:
            if current_rsi < self.rsi_level and close > current_long_sma:
                self.logger.info(
                    f"🟢 BUY signal at {close:.2f} on {current_date} "
                    f"(RSI: {current_rsi:.2f}, SMA200: {current_long_sma:.2f})"
                )
                self.buy()

        # Exit Logic
        else:
            if close >= current_short_sma:
                entry_price = getattr(self.position, "entry_price", None)
                if entry_price:
                    profit_loss = (close - entry_price) / entry_price * 100
                    self.logger.info(
                        f"🔴 SELL at {close:.2f} on {current_date} "
                        f"(P&L: {profit_loss:.2f}%, SMA5: {current_short_sma:.2f})"
                    )
                else:
                    self.logger.info(f"🔴 SELL at {close:.2f} on {current_date}")
                self.position.close()
