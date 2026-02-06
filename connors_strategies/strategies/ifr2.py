import talib
from backtesting import Strategy

from connors_core.core.registry import registry
from connors_core.core.logging import setup_strategy_logger


@registry.register_strategy("IFR2")
class IFR2_Strategy(Strategy):
    """IFR2 - Simplified Larry Connors 2-Period RSI Strategy

    A mean reversion strategy that buys oversold stocks in an uptrend.

    Entry Rules:
    - RSI(2) < 5 (oversold condition)
    - Price > 200-day SMA (uptrend filter)

    Exit Rules:
    - Price >= 5-day SMA (mean reversion complete)
    """

    # === Parameters ===
    rsi_length = 2          # RSI calculation period
    rsi_level = 5           # RSI oversold threshold for entry

    short_sma_length = 5    # Short SMA for exit signal
    long_sma_length = 200   # Long SMA for trend filter

    def init(self):
        """Initialize indicators used in the strategy"""
        # Set up colorful logger
        self.logger = setup_strategy_logger("IFR2_Strategy")

        # Log strategy initialization
        self.logger.info(
            f"✨ Initializing IFR2 strategy with parameters: "
            f"rsi_length={self.rsi_length}, rsi_level={self.rsi_level}, "
            f"short_sma_length={self.short_sma_length}, long_sma_length={self.long_sma_length}"
        )

        # 2-period RSI for oversold detection
        self.ifr2 = self.I(lambda x: talib.RSI(x, timeperiod=self.rsi_length), self.data.Close)
        # 200-day SMA for trend filter (only buy in uptrends)
        self.long_sma = self.I(lambda x: talib.SMA(x, timeperiod=self.long_sma_length), self.data.Close)
        # 5-day SMA for exit signal (price above = mean reversion complete)
        self.short_sma = self.I(lambda x: talib.SMA(x, timeperiod=self.short_sma_length), self.data.Close)

        self.logger.info("✅ IFR2 strategy initialization completed")

    def next(self):
        """Execute trading logic on each bar"""
        close = self.data.Close[-1]
        current_rsi = self.ifr2[-1]
        current_long_sma = self.long_sma[-1]
        current_short_sma = self.short_sma[-1]
        current_date = self.data.index[-1] if hasattr(self.data, "index") else f"Bar {len(self.data) - 1}"

        # Log current market conditions (DEBUG level)
        self.logger.debug(
            f"Market data - Date: {current_date}, Close: {close:.2f}, "
            f"RSI({self.rsi_length}): {current_rsi:.2f}, "
            f"Long_SMA({self.long_sma_length}): {current_long_sma:.2f}, "
            f"Short_SMA({self.short_sma_length}): {current_short_sma:.2f}"
        )

        # Entry logic: buy when oversold in an uptrend
        if not self.position:
            # Check both conditions: oversold RSI AND price above long-term trend
            if current_rsi < self.rsi_level and close > current_long_sma:
                self.logger.info(
                    f"🟢 BUY signal - RSI {current_rsi:.2f} < {self.rsi_level} "
                    f"AND Close {close:.2f} > Long_SMA {current_long_sma:.2f}"
                )
                self.logger.info(f"💰 EXECUTING BUY at {close:.2f} on {current_date}")
                self.buy()

        # Exit logic: close when price recovers above short-term average
        else:
            if close >= current_short_sma:
                entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
                if entry_price:
                    profit_loss = ((close - entry_price) / entry_price * 100)
                    self.logger.info(
                        f"🔴 SELL signal - Close {close:.2f} >= Short_SMA {current_short_sma:.2f}"
                    )
                    self.logger.info(
                        f"💸 EXECUTING SELL at {close:.2f} on {current_date} "
                        f"(Entry: {entry_price:.2f}, P&L: {profit_loss:.2f}%)"
                    )
                else:
                    self.logger.info(
                        f"🔴 SELL signal - Close {close:.2f} >= Short_SMA {current_short_sma:.2f}"
                    )
                    self.logger.info(f"💸 EXECUTING SELL at {close:.2f} on {current_date}")
                self.position.close()
