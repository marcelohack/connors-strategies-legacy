"""
Order Block Break and Retest Strategy

This strategy identifies 'order blocks' - specific candles that signify institutional
activity - and trades the break and retest of these zones in trending markets.

Key Concepts:
- Order blocks are supply/demand zones created by institutional activity
- In uptrend: down-close candles (close < open) create bullish order blocks
- In downtrend: up-close candles (close > open) create bearish order blocks
- Order block zone: from candle's wick to its body
- Break and retest of order block in trend direction = high-probability entry

Entry Logic:
1. Identify trend (higher highs/higher lows for uptrend, lower highs/lower lows for downtrend)
2. Mark order blocks:
   - Uptrend: down-close candles (bearish candles in bullish trend)
   - Downtrend: up-close candles (bullish candles in bearish trend)
3. Wait for price to break through order block
4. Enter on retest of order block in direction of trend

Exit Logic:
- Stop loss: Below order block low for longs, above order block high for shorts
- Take profit: Based on risk-reward ratio (default 1:2)

Requirements:
- Clear trending market (ineffective in ranging/consolidating markets)
- Confluence with other levels increases probability
"""

from backtesting import Strategy
from backtesting.lib import crossover
import talib
import pandas as pd
import numpy as np


class OrderBlockBreakRetest(Strategy):
    """
    Order Block Break and Retest Strategy

    Identifies order blocks in trending markets and trades their break and retest.
    """

    # Strategy Parameters
    risk_per_trade = 0.01  # 1% risk per trade
    reward_risk_ratio = 2.0  # 1:2 risk-reward
    trend_lookback = 20  # Bars to identify trend
    swing_lookback = 10  # Bars to identify swing highs/lows
    retest_proximity_pct = 0.005  # 0.5% proximity to consider a retest
    stop_loss_buffer_pct = 0.003  # 0.3% buffer for stop loss

    def init(self):
        """Initialize strategy indicators and tracking variables"""

        # Trend indicators
        self.sma_fast = self.I(talib.SMA, self.data.Close, timeperiod=20)
        self.sma_slow = self.I(talib.SMA, self.data.Close, timeperiod=50)
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, timeperiod=14)

        # Order block tracking
        self.bullish_order_blocks = []  # List of (high, low, index) tuples
        self.bearish_order_blocks = []  # List of (high, low, index) tuples

        # Active order block for trading
        self.active_ob = None
        self.ob_type = None  # 'bullish' or 'bearish'
        self.ob_broken = False
        self.in_retest = False

    def identify_trend(self):
        """
        Identify market trend based on price action and moving averages

        Returns:
            'uptrend', 'downtrend', or 'sideways'
        """
        if len(self.data.Close) < self.trend_lookback:
            return 'sideways'

        # Check moving average relationship
        if self.sma_fast[-1] > self.sma_slow[-1]:
            # Additional confirmation: higher highs and higher lows
            recent_highs = self.data.High[-self.trend_lookback:]
            recent_lows = self.data.Low[-self.trend_lookback:]

            if recent_highs[-1] >= recent_highs[0] and recent_lows[-1] >= recent_lows[0]:
                return 'uptrend'

        elif self.sma_fast[-1] < self.sma_slow[-1]:
            # Additional confirmation: lower highs and lower lows
            recent_highs = self.data.High[-self.trend_lookback:]
            recent_lows = self.data.Low[-self.trend_lookback:]

            if recent_highs[-1] <= recent_highs[0] and recent_lows[-1] <= recent_lows[0]:
                return 'downtrend'

        return 'sideways'

    def is_down_close_candle(self, index):
        """Check if candle at index is a down-close candle (close < open)"""
        if index < 0 or index >= len(self.data.Close):
            return False
        return self.data.Close[index] < self.data.Open[index]

    def is_up_close_candle(self, index):
        """Check if candle at index is an up-close candle (close > open)"""
        if index < 0 or index >= len(self.data.Close):
            return False
        return self.data.Close[index] > self.data.Open[index]

    def has_clear_wick(self, index, direction='down'):
        """
        Check if candle has a clear wick (higher probability order block)

        Args:
            index: Candle index
            direction: 'down' for bearish candle, 'up' for bullish candle
        """
        if index < 0 or index >= len(self.data.Close):
            return False

        body_size = abs(self.data.Close[index] - self.data.Open[index])
        if body_size == 0:
            return False

        if direction == 'down':
            # For down-close candle, check for lower wick
            lower_wick = min(self.data.Close[index], self.data.Open[index]) - self.data.Low[index]
            return lower_wick > body_size * 0.3  # Wick at least 30% of body
        else:
            # For up-close candle, check for upper wick
            upper_wick = self.data.High[index] - max(self.data.Close[index], self.data.Open[index])
            return upper_wick > body_size * 0.3

    def identify_order_blocks(self):
        """
        Identify order blocks based on current trend

        In uptrend: Look for down-close candles (bullish order blocks)
        In downtrend: Look for up-close candles (bearish order blocks)
        """
        if len(self.data.Close) < 2:
            return

        current_index = len(self.data.Close) - 1
        trend = self.identify_trend()

        # In uptrend, look for down-close candles (bullish order block)
        if trend == 'uptrend' and self.is_down_close_candle(current_index - 1):
            if self.has_clear_wick(current_index - 1, 'down'):
                # Order block: from low wick to close (body bottom)
                ob_high = max(self.data.Open[current_index - 1], self.data.Close[current_index - 1])
                ob_low = self.data.Low[current_index - 1]

                # Add to bullish order blocks (limit list size)
                self.bullish_order_blocks.append((ob_high, ob_low, current_index - 1))
                if len(self.bullish_order_blocks) > 5:
                    self.bullish_order_blocks.pop(0)

                print(f"Bullish Order Block identified: High ${ob_high:.2f}, Low ${ob_low:.2f}")

        # In downtrend, look for up-close candles (bearish order block)
        elif trend == 'downtrend' and self.is_up_close_candle(current_index - 1):
            if self.has_clear_wick(current_index - 1, 'up'):
                # Order block: from close (body top) to high wick
                ob_high = self.data.High[current_index - 1]
                ob_low = min(self.data.Open[current_index - 1], self.data.Close[current_index - 1])

                # Add to bearish order blocks (limit list size)
                self.bearish_order_blocks.append((ob_high, ob_low, current_index - 1))
                if len(self.bearish_order_blocks) > 5:
                    self.bearish_order_blocks.pop(0)

                print(f"Bearish Order Block identified: High ${ob_high:.2f}, Low ${ob_low:.2f}")

    def next(self):
        """Execute strategy logic for each bar"""

        # Skip if not enough data
        if len(self.data.Close) < max(self.trend_lookback, self.swing_lookback):
            return

        # Skip if already in a position
        if self.position:
            return

        # Identify new order blocks
        self.identify_order_blocks()

        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]
        trend = self.identify_trend()

        # Only trade in clear trends
        if trend == 'sideways':
            return

        # Long setup: Bullish order block break and retest in uptrend
        if trend == 'uptrend' and len(self.bullish_order_blocks) > 0:
            # Get most recent bullish order block
            if self.active_ob is None or self.ob_type != 'bullish':
                self.active_ob = self.bullish_order_blocks[-1]
                self.ob_type = 'bullish'
                self.ob_broken = False
                self.in_retest = False

            ob_high, ob_low, ob_index = self.active_ob

            # Check if order block has been broken (price moved above it)
            if not self.ob_broken and current_high > ob_high:
                self.ob_broken = True
                self.in_retest = False
                print(f"Bullish OB broken at ${current_price:.2f}")

            # Wait for retest after break
            if self.ob_broken and not self.in_retest:
                # Check if price is retesting the order block zone
                if current_low <= ob_high and current_price >= ob_low:
                    retest_range = ob_high * self.retest_proximity_pct

                    if abs(current_price - ob_high) <= retest_range or (ob_low <= current_price <= ob_high):
                        self.in_retest = True
                        print(f"Bullish OB retest at ${current_price:.2f}")

                        # Entry: Long on retest
                        entry_price = current_price
                        stop_loss = ob_low * (1 - self.stop_loss_buffer_pct)
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

                                # Reset order block tracking
                                self.active_ob = None

        # Short setup: Bearish order block break and retest in downtrend
        elif trend == 'downtrend' and len(self.bearish_order_blocks) > 0:
            # Get most recent bearish order block
            if self.active_ob is None or self.ob_type != 'bearish':
                self.active_ob = self.bearish_order_blocks[-1]
                self.ob_type = 'bearish'
                self.ob_broken = False
                self.in_retest = False

            ob_high, ob_low, ob_index = self.active_ob

            # Check if order block has been broken (price moved below it)
            if not self.ob_broken and current_low < ob_low:
                self.ob_broken = True
                self.in_retest = False
                print(f"Bearish OB broken at ${current_price:.2f}")

            # Wait for retest after break
            if self.ob_broken and not self.in_retest:
                # Check if price is retesting the order block zone
                if current_high >= ob_low and current_price <= ob_high:
                    retest_range = ob_low * self.retest_proximity_pct

                    if abs(current_price - ob_low) <= retest_range or (ob_low <= current_price <= ob_high):
                        self.in_retest = True
                        print(f"Bearish OB retest at ${current_price:.2f}")

                        # Entry: Short on retest
                        entry_price = current_price
                        stop_loss = ob_high * (1 + self.stop_loss_buffer_pct)
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

                                # Reset order block tracking
                                self.active_ob = None
