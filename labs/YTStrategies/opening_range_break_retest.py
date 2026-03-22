"""
Opening Range Break and Retest Strategy

This strategy focuses on the first candle of the New York session (9:30 AM EST),
trading the break and retest of that opening range for continuation moves.

Key Concepts:
- Opening range defined by first 5-minute candle of NY session
- Break above/below opening range signals potential directional move
- Retest of broken level provides optimal entry
- Most effective when price opens inside previous day's range

Entry Logic:
1. Mark high and low of first 5-minute candle at NY open (9:30 AM EST)
2. Wait for price to break above opening range high or below opening range low
3. Wait for price to retest the broken level
4. Enter long on retest of broken high, short on retest of broken low

Exit Logic:
- Stop loss: Just on other side of opening range level
- Take profit: Based on risk-reward ratio (default 1:2)

Note: This implementation adapts the concept for any timeframe by identifying
the opening range based on the first bars of each trading day, rather than
strictly requiring 5-minute data.
"""

from backtesting import Strategy
from backtesting.lib import crossover
import talib
import pandas as pd
import numpy as np


class OpeningRangeBreakRetest(Strategy):
    """
    Opening Range Break and Retest Strategy

    Trades the break and retest of the opening range (first candle of the day).
    """

    # Strategy Parameters
    risk_per_trade = 0.01  # 1% risk per trade
    reward_risk_ratio = 2.0  # 1:2 risk-reward
    opening_range_bars = 1  # Number of bars to define opening range (adapt to timeframe)
    retest_proximity_pct = 0.003  # 0.3% proximity to consider a retest
    stop_loss_buffer_pct = 0.002  # 0.2% buffer for stop loss

    def init(self):
        """Initialize strategy indicators and tracking variables"""

        # Opening range tracking
        self.or_high = None
        self.or_low = None
        self.or_established = False
        self.current_date = None
        self.opening_bar_count = 0

        # Break tracking
        self.or_high_broken = False
        self.or_low_broken = False

        # Retest tracking
        self.in_high_retest = False
        self.in_low_retest = False

        # ATR for reference
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

    def next(self):
        """Execute strategy logic for each bar"""

        # Get current bar's date
        current_bar_date = pd.Timestamp(self.data.index[-1]).date()

        # Detect new trading day
        if self.current_date is None or current_bar_date != self.current_date:
            # Reset for new day
            self.current_date = current_bar_date
            self.or_established = False
            self.opening_bar_count = 0
            self.or_high = None
            self.or_low = None
            self.or_high_broken = False
            self.or_low_broken = False
            self.in_high_retest = False
            self.in_low_retest = False

        # Establish opening range
        if not self.or_established:
            self.opening_bar_count += 1

            # Update opening range high/low
            if self.or_high is None:
                self.or_high = self.data.High[-1]
                self.or_low = self.data.Low[-1]
            else:
                self.or_high = max(self.or_high, self.data.High[-1])
                self.or_low = min(self.or_low, self.data.Low[-1])

            # Opening range established after specified number of bars
            if self.opening_bar_count >= self.opening_range_bars:
                self.or_established = True
                print(f"Opening Range established: High ${self.or_high:.2f}, Low ${self.or_low:.2f}")

            return  # Don't trade during opening range formation

        # Skip if opening range not yet established
        if not self.or_established:
            return

        # Skip if already in a position
        if self.position:
            return

        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]

        # Detect break above opening range high
        if not self.or_high_broken and current_high > self.or_high:
            self.or_high_broken = True
            self.in_high_retest = False
            print(f"Break above opening range high at ${current_price:.2f} (OR High: ${self.or_high:.2f})")

        # Detect break below opening range low
        if not self.or_low_broken and current_low < self.or_low:
            self.or_low_broken = True
            self.in_low_retest = False
            print(f"Break below opening range low at ${current_price:.2f} (OR Low: ${self.or_low:.2f})")

        # Long setup: After breaking OR high, wait for retest
        if self.or_high_broken and not self.in_high_retest:
            # Check if price is retesting the opening range high
            retest_range = self.or_high * self.retest_proximity_pct

            if abs(current_price - self.or_high) <= retest_range and current_price >= self.or_high:
                self.in_high_retest = True
                print(f"Retest of opening range high at ${current_price:.2f}")

                # Entry: Long on retest
                entry_price = current_price
                stop_loss = self.or_low - (self.or_low * self.stop_loss_buffer_pct)
                risk = entry_price - stop_loss

                if risk > 0:
                    # Calculate position size
                    risk_amount = self.equity * self.risk_per_trade
                    position_size = int(round(risk_amount / risk))

                    if position_size > 0:
                        # Calculate take profit
                        take_profit = entry_price + (risk * self.reward_risk_ratio)

                        print(f"Moon Dev Long Entry @ ${entry_price:.2f} | SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
                        self.buy(size=position_size, sl=stop_loss, tp=take_profit)

        # Short setup: After breaking OR low, wait for retest
        if self.or_low_broken and not self.in_low_retest:
            # Check if price is retesting the opening range low
            retest_range = self.or_low * self.retest_proximity_pct

            if abs(current_price - self.or_low) <= retest_range and current_price <= self.or_low:
                self.in_low_retest = True
                print(f"Retest of opening range low at ${current_price:.2f}")

                # Entry: Short on retest
                entry_price = current_price
                stop_loss = self.or_high + (self.or_high * self.stop_loss_buffer_pct)
                risk = stop_loss - entry_price

                if risk > 0:
                    # Calculate position size
                    risk_amount = self.equity * self.risk_per_trade
                    position_size = int(round(risk_amount / risk))

                    if position_size > 0:
                        # Calculate take profit
                        take_profit = entry_price - (risk * self.reward_risk_ratio)

                        print(f"Moon Dev Short Entry @ ${entry_price:.2f} | SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
                        self.sell(size=position_size, sl=stop_loss, tp=take_profit)
