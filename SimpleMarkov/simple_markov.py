"""
SimpleMarkov Trading Strategy

A mean-reversion strategy based on consecutive red candles that exploits
short-term market inefficiencies following extended selling pressure.

Original Research Sources:
- https://www.youtube.com/watch?v=GWW5L07-etg
- https://colab.research.google.com/drive/1xSB16U50eIcreJeZyYfexLswbPx8vjeZ#scrollTo=tqRldM3bLqbE

Strategy Logic:
When we detect n consecutive red candles (Close < Open), we expect a mean-reversion
bounce and enter a long position. The position is held for exactly one bar and
then closed, capturing any potential bounce.

Important Backtesting.py Behavior:
- Orders are executed at bar OPEN prices
- Position closes occur at NEXT bar's open, not current bar's close
- If consecutive red candles continue, sell and buy orders effectively cancel out
"""

import pandas as pd
import numpy as np
from backtesting import Strategy
from connors.core.registry import registry


@registry.register_strategy("SimpleMarkov")
class SimpleMarkovStrategy(Strategy):
    """
    Simple Markov Mean Reversion Strategy

    Strategy based on the principle that after n consecutive red candles,
    the market tends to show short-term mean reversion behavior.

    Core Concept:
    - Red candle defined as: Close < Open
    - After n consecutive red candles, enter long position
    - Hold position for exactly one bar (exit at next bar's open)
    - Capture potential bounce from oversold conditions

    Key Insight:
    Due to backtesting.py's execution model, positions are closed at the NEXT
    bar's open, not the current bar's close. This means we're exposed to
    after-hours price movements and gap risk.
    """

    # === Strategy Parameters ===
    consecutive_red_bars = 3  # Number of consecutive red candles required

    # === Position Management ===
    max_position_size = 1.0   # Maximum position size (1.0 = 100% of available capital)

    def init(self):
        """
        Initialize strategy indicators and state variables.

        Note: This strategy doesn't require complex indicators, just raw OHLC data.
        """
        # No indicators needed for this simple strategy
        # All logic is based on comparing Close vs Open prices
        pass

    def next(self):
        """
        Main strategy logic executed on each bar.

        Execution Flow:
        1. Check if we have sufficient historical data
        2. Close any existing positions (occurs at next bar's open)
        3. Check for consecutive red candle pattern
        4. Enter new position if pattern is detected

        Critical Understanding:
        - When we call self.buy(), the order executes at CURRENT bar's open
        - When we call self.position.close(), it executes at NEXT bar's open
        - This creates a one-bar holding period from current open to next open
        """

        # === Data Validation ===
        if len(self.data) < self.consecutive_red_bars:
            # Insufficient data for pattern detection
            return

        # === Position Management ===
        # Close any existing positions first
        # Important: This executes at NEXT bar's open, not current bar's close
        if self.position:
            current_price = self.data.Close[-1]
            entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
            if entry_price:
                pnl_pct = ((current_price - entry_price) / entry_price * 100)
                self.logger.info(
                    f"🔴 SELL signal - One-bar holding period complete"
                )
                self.logger.info(
                    f"💸 EXECUTING SELL at next bar open (Current: {current_price:.2f}, Entry: {entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                )
            else:
                self.logger.info(f"🔴 SELL signal - One-bar holding period complete")
                self.logger.info(f"💸 EXECUTING SELL at next bar open (Current: {current_price:.2f})")
            self.position.close()

        # === Pattern Detection ===
        # Check for consecutive red candles pattern
        consecutive_red_detected = self._detect_consecutive_red_candles()

        if consecutive_red_detected:
            # Enter long position expecting mean reversion
            # Order executes at current bar's open
            current_price = self.data.Close[-1]
            self.logger.info(
                f"🟢 BUY signal - {self.consecutive_red_bars} consecutive red candles detected (mean reversion expected)"
            )
            self.logger.info(f"💰 EXECUTING BUY at next bar open (Current: {current_price:.2f})")
            self.buy(size=self.max_position_size)

    def _detect_consecutive_red_candles(self) -> bool:
        """
        Detect if the last n bars were all red candles.

        Red Candle Definition: Close < Open (bearish candle)

        Returns:
            bool: True if last n bars were all red, False otherwise

        Implementation Details:
        - self.data.Close[-1] = most recent completed bar's close
        - self.data.Close[-2] = previous bar's close, etc.
        - We check the last n completed bars for the red pattern
        """

        # Check each of the last n bars for red candle pattern
        # Range(1, n+1) gives us [-1, -2, -3, ..., -n] indices
        red_candles = []

        for bar_offset in range(1, self.consecutive_red_bars + 1):
            current_bar_close = self.data.Close[-bar_offset]
            current_bar_open = self.data.Open[-bar_offset]

            # Red candle: Close < Open
            is_red_candle = current_bar_close < current_bar_open
            red_candles.append(is_red_candle)

        # All bars in the sequence must be red
        all_red = all(red_candles)

        return all_red

    def _format_position_info(self) -> str:
        """
        Helper method for debugging and logging position information.

        Returns:
            str: Formatted position information
        """
        if self.position:
            return f"Position: {self.position.size:.2f} shares @ {self.position.pl:.2f} P&L"
        else:
            return "Position: None"


# Example usage and testing
if __name__ == "__main__":
    """
    Example usage of the SimpleMarkov strategy.

    This section demonstrates how to run the strategy with sample data.
    For production use, integrate with the connors CLI framework.
    """

    from backtesting import Backtest
    import yfinance as yf

    # Download sample data
    print("Downloading sample data...")
    data = yf.download("SPY", start="2020-01-01", end="2023-12-31")

    # Remove multi-level column index if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    # Run backtest
    print("Running SimpleMarkov backtest...")
    backtest = Backtest(data, SimpleMarkovStrategy, cash=10000, commission=0.002)

    # Execute backtest
    results = backtest.run()

    # Display results
    print("\n" + "="*60)
    print("SIMPLE MARKOV STRATEGY BACKTEST RESULTS")
    print("="*60)
    print(f"Start Date: {data.index[0].strftime('%Y-%m-%d')}")
    print(f"End Date: {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"Total Return: {results['Return [%]']:.2f}%")
    print(f"Buy & Hold Return: {results['Buy & Hold Return [%]']:.2f}%")
    print(f"Sharpe Ratio: {results['Sharpe Ratio']:.2f}")
    print(f"Max Drawdown: {results['Max. Drawdown [%]']:.2f}%")
    print(f"Number of Trades: {results['# Trades']}")
    print(f"Win Rate: {results['Win Rate [%]']:.1f}%")
    print("="*60)

    # Plot results
    # backtest.plot()