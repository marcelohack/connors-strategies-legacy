"""
Previous Day High and Low Break and Retest Strategy

This strategy identifies the previous day's high and low from the New York session
and trades the break and retest of these levels for continuation or reversal setups.

Key Concepts:
- Previous day's high/low are significant levels with resting volume
- Break above/below these levels indicates potential directional move
- Retest of broken level provides lower-risk entry opportunity
- Works best in trending markets for continuation trades

Entry Logic:
1. Track previous day's high and low
2. Detect break above previous day high (bullish) or below previous day low (bearish)
3. Wait for price to retest the broken level
4. Enter long on successful retest of broken high (continuation)
   or short on successful retest of broken low (continuation)

Exit Logic:
- Stop loss: Just below retest level for longs, above for shorts
- Take profit: Based on risk-reward ratio (default 1:2)
"""

from backtesting import Strategy
from backtesting.lib import crossover
import talib
import pandas as pd
import numpy as np


class PreviousDayHighLowBreakRetest(Strategy):
    """
    Previous Day High and Low Break and Retest Strategy

    Trades the break and retest of previous day's high/low levels.
    """

    # Strategy Parameters
    risk_per_trade = 0.02  # 2% risk per trade
    reward_risk_ratio = 2.0  # 1:2 risk-reward
    retest_proximity_pct = 0.005  # 0.5% proximity to consider a retest
    stop_loss_buffer_pct = 0.002  # 0.2% buffer below/above retest level
    lookback_bars = 3  # Bars to confirm break

    def init(self):
        """Initialize strategy indicators and tracking variables"""

        # Track previous day's high and low
        self.prev_day_high = None
        self.prev_day_low = None
        self.current_date = None

        # Track break status
        self.high_broken = False
        self.low_broken = False
        self.break_high_price = None
        self.break_low_price = None

        # Track if we're in a retest phase
        self.in_high_retest = False
        self.in_low_retest = False

        # ATR for dynamic stop placement
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

    def next(self):
        """Execute strategy logic for each bar"""

        # Get current bar's date
        current_bar_date = pd.Timestamp(self.data.index[-1]).date()

        # Update previous day levels when new day starts
        if self.current_date is None or current_bar_date != self.current_date:
            # Store previous day's high/low before updating
            if len(self.data.Close) > 1:
                # Find all bars from previous day
                prev_bars_mask = [pd.Timestamp(t).date() == self.current_date
                                 for t in self.data.index[:-1]]

                if any(prev_bars_mask):
                    # Get indices of previous day's bars
                    prev_day_indices = [i for i, is_prev_day in enumerate(prev_bars_mask) if is_prev_day]

                    if prev_day_indices:
                        # Calculate previous day's high and low
                        self.prev_day_high = max(self.data.High[i] for i in prev_day_indices)
                        self.prev_day_low = min(self.data.Low[i] for i in prev_day_indices)

                        # Reset break status for new day
                        self.high_broken = False
                        self.low_broken = False
                        self.in_high_retest = False
                        self.in_low_retest = False
                        self.break_high_price = None
                        self.break_low_price = None

            # Update current date
            self.current_date = current_bar_date

        # Skip if we don't have previous day levels yet
        if self.prev_day_high is None or self.prev_day_low is None:
            return

        # Skip if already in a position
        if self.position:
            return

        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]

        # Detect break above previous day high
        if not self.high_broken and current_high > self.prev_day_high:
            self.high_broken = True
            self.break_high_price = current_price
            self.in_high_retest = False
            print(f"Break above previous day high at ${current_price:.2f} (PDH: ${self.prev_day_high:.2f})")

        # Detect break below previous day low
        if not self.low_broken and current_low < self.prev_day_low:
            self.low_broken = True
            self.break_low_price = current_price
            self.in_low_retest = False
            print(f"Break below previous day low at ${current_price:.2f} (PDL: ${self.prev_day_low:.2f})")

        # Long setup: After breaking high, wait for retest
        if self.high_broken and not self.in_high_retest:
            # Check if price is retesting the previous day high
            retest_range = self.prev_day_high * self.retest_proximity_pct

            if abs(current_price - self.prev_day_high) <= retest_range:
                self.in_high_retest = True
                print(f"Retest of previous day high at ${current_price:.2f}")

                # Entry: Long on retest
                entry_price = current_price
                stop_loss = self.prev_day_high * (1 - self.stop_loss_buffer_pct)
                risk = entry_price - stop_loss

                # Calculate position size
                risk_amount = self.equity * self.risk_per_trade
                position_size = int(round(risk_amount / risk))

                if position_size > 0:
                    # Calculate take profit
                    take_profit = entry_price + (risk * self.reward_risk_ratio)

                    print(f"Moon Dev Long Entry @ ${entry_price:.2f} | SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
                    self.buy(size=position_size, sl=stop_loss, tp=take_profit)

        # Short setup: After breaking low, wait for retest
        if self.low_broken and not self.in_low_retest:
            # Check if price is retesting the previous day low
            retest_range = self.prev_day_low * self.retest_proximity_pct

            if abs(current_price - self.prev_day_low) <= retest_range:
                self.in_low_retest = True
                print(f"Retest of previous day low at ${current_price:.2f}")

                # Entry: Short on retest
                entry_price = current_price
                stop_loss = self.prev_day_low * (1 + self.stop_loss_buffer_pct)
                risk = stop_loss - entry_price

                # Calculate position size
                risk_amount = self.equity * self.risk_per_trade
                position_size = int(round(risk_amount / risk))

                if position_size > 0:
                    # Calculate take profit
                    take_profit = entry_price - (risk * self.reward_risk_ratio)

                    print(f"Moon Dev Short Entry @ ${entry_price:.2f} | SL: ${stop_loss:.2f} | TP: ${take_profit:.2f}")
                    self.sell(size=position_size, sl=stop_loss, tp=take_profit)
