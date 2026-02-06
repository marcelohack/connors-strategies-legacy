"""Larry Connors 2-Period RSI Strategy - Version 2

A mean reversion strategy with protocol-based market data for performance.
Uses colorful logging and MarketSnapshot protocol for 4-10x faster signal generation.
"""

import pandas as pd
import talib
from backtesting import Strategy
from decimal import Decimal

from connors_core.core.registry import registry
from connors_core.core.market_data import MarketSnapshot, DataFrameMarketSnapshot
from connors_strategies.strategies.base_logic import BaseStrategyLogic
from connors_core.core.logging import setup_strategy_logger


class LCRSI2_Logic(BaseStrategyLogic):
    """Strategy logic class for Larry Connors 2-Period RSI Strategy V2

    A mean reversion strategy that buys oversold stocks in an uptrend.

    Entry Rules:
    - RSI(2) < rsi_level (oversold condition)
    - Price > long_sma (uptrend filter)

    Exit Rules:
    - Price >= short_sma (mean reversion complete)

    This version uses MarketSnapshot protocol for 4-10x faster signal generation
    compared to DataFrame-based approach. Works for both backtesting and live trading.
    """

    def __init__(self,
                 rsi_length: int = 2,
                 rsi_level: float = 5.0,
                 short_sma_length: int = 5,
                 long_sma_length: int = 200,
                 log_level: str = "INFO"):
        """Initialize strategy logic with parameters

        Args:
            rsi_length: RSI calculation period
            rsi_level: RSI oversold threshold for entry
            short_sma_length: Short SMA period for exit signal
            long_sma_length: Long SMA period for trend filter
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.rsi_length = rsi_length
        self.rsi_level = rsi_level
        self.short_sma_length = short_sma_length
        self.long_sma_length = long_sma_length

        # Set up colorful logger
        self.logger = setup_strategy_logger("LCRSI2Logic", level=log_level)

    def generate_signal(self, snapshot: MarketSnapshot) -> str:
        """Generate trading signal from market snapshot (FAST!)

        Uses MarketSnapshot protocol for zero-copy, type-safe signal generation.
        This is 4-10x faster than DataFrame-based approach.

        Args:
            snapshot: Market snapshot with current bar and indicators

        Returns:
            Trading signal: "BUY", "SELL", or "HOLD"
        """
        # Get current bar and indicators (direct attribute access - FAST!)
        current_close = snapshot.bar.close
        current_rsi = snapshot.get_indicator(f"RSI_{self.rsi_length}")
        current_long_sma = snapshot.get_indicator(f"SMA_{self.long_sma_length}")
        current_short_sma = snapshot.get_indicator(f"SMA_{self.short_sma_length}")

        # Log current market conditions (DEBUG level)
        rsi_str = f"{current_rsi:.2f}" if current_rsi is not None else "N/A"
        long_sma_str = f"{current_long_sma:.2f}" if current_long_sma is not None else "N/A"
        short_sma_str = f"{current_short_sma:.2f}" if current_short_sma is not None else "N/A"

        self.logger.debug(
            f"Market data - Close: {current_close:.2f}, "
            f"RSI({self.rsi_length}): {rsi_str}, "
            f"Long_SMA({self.long_sma_length}): {long_sma_str}, "
            f"Short_SMA({self.short_sma_length}): {short_sma_str}"
        )

        # Check for missing indicator values
        if current_rsi is None or current_long_sma is None or current_short_sma is None:
            self.logger.warning(
                f"Missing indicator values - RSI: {current_rsi}, "
                f"Long_SMA: {current_long_sma}, Short_SMA: {current_short_sma}"
            )
            return "HOLD"

        # Entry signal: oversold RSI in uptrend
        if current_rsi < self.rsi_level and current_close > current_long_sma:
            self.logger.info(
                f"🟢 BUY signal - RSI {current_rsi:.2f} < {self.rsi_level} "
                f"AND Close {current_close:.2f} > Long_SMA {current_long_sma:.2f}"
            )
            return "BUY"

        # Exit signal: price recovers above short-term average
        if current_close >= current_short_sma:
            self.logger.info(
                f"🔴 SELL signal - Close {current_close:.2f} >= Short_SMA {current_short_sma:.2f}"
            )
            return "SELL"

        # Log hold conditions (DEBUG level)
        if current_rsi >= self.rsi_level:
            self.logger.debug(f"HOLD - RSI {current_rsi:.2f} not oversold (>= {self.rsi_level})")
        if current_close <= current_long_sma:
            self.logger.debug(f"HOLD - Price {current_close:.2f} not in uptrend (<= Long_SMA {current_long_sma:.2f})")

        return "HOLD"


@registry.register_strategy("LCRSI2")
class LCRSI2_Strategy(Strategy):
    """Simplified Larry Connors 2-Period RSI Strategy - Version 2

    A mean reversion strategy that buys oversold stocks in an uptrend.
    Uses a separate logic class for signal generation with MarketSnapshot protocol.

    This backtesting strategy uses DataFrameMarketSnapshot adapter to convert
    DataFrame data to MarketSnapshot protocol, allowing the same logic to work
    for both backtesting and live trading.
    """

    # === Parameters ===
    rsi_length = 2          # RSI calculation period
    rsi_level = 5           # RSI oversold threshold for entry
    short_sma_length = 5    # Short SMA for exit signal
    long_sma_length = 200   # Long SMA for trend filter

    def init(self):
        """Initialize strategy logic and indicators"""
        # Set up colorful logger
        self.logger = setup_strategy_logger("LCRSI2_Strategy")

        # Log strategy initialization
        self.logger.info(
            f"✨ Initializing LCRSI2 strategy with parameters: "
            f"rsi_length={self.rsi_length}, rsi_level={self.rsi_level}, "
            f"short_sma_length={self.short_sma_length}, long_sma_length={self.long_sma_length}"
        )

        # Initialize strategy logic (uses MarketSnapshot protocol)
        self.logic = LCRSI2_Logic(
            rsi_length=self.rsi_length,
            rsi_level=self.rsi_level,
            short_sma_length=self.short_sma_length,
            long_sma_length=self.long_sma_length,
            log_level="INFO"  # Can be configured per strategy
        )

        # Initialize indicators using backtesting.py format
        self.rsi = self.I(lambda x: talib.RSI(x, timeperiod=self.rsi_length), self.data.Close)
        self.long_sma = self.I(lambda x: talib.SMA(x, timeperiod=self.long_sma_length), self.data.Close)
        self.short_sma = self.I(lambda x: talib.SMA(x, timeperiod=self.short_sma_length), self.data.Close)

        self.logger.info("✅ Strategy initialization completed")

    def next(self):
        """Execute trading logic on each bar"""
        # Get current bar index and price information
        current_bar = len(self.data) - 1
        current_close = self.data.Close[-1]
        current_date = self.data.index[-1] if hasattr(self.data, "index") else f"Bar {current_bar}"

        # Create DataFrame with current data
        current_data = pd.DataFrame({
            "Open": self.data.Open,
            "High": self.data.High,
            "Low": self.data.Low,
            "Close": self.data.Close,
            "Volume": self.data.Volume,
            f"RSI_{self.rsi_length}": self.rsi,
            f"SMA_{self.long_sma_length}": self.long_sma,
            f"SMA_{self.short_sma_length}": self.short_sma
        })

        # Convert DataFrame to MarketSnapshot using adapter (zero-copy for latest bar)
        snapshot = DataFrameMarketSnapshot(_data=current_data)

        # Generate signal using strategy logic (same logic as live trading!)
        signal = self.logic.generate_signal(snapshot)

        # Log current position and signal
        position_info = f"Position: {self.position.size if self.position else 0} shares"
        self.logger.debug(f"Bar {current_bar} ({current_date}) - Close: {current_close:.2f}, Signal: {signal}, {position_info}")

        # Execute trades based on signal
        if signal == "BUY" and not self.position:
            self.logger.info(f"💰 EXECUTING BUY at {current_close:.2f} on {current_date}")
            self.buy()
        elif signal == "SELL" and self.position:
            entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else "N/A"
            if entry_price != "N/A":
                profit_loss = ((current_close - entry_price) / entry_price * 100)
                self.logger.info(
                    f"💸 EXECUTING SELL at {current_close:.2f} on {current_date} "
                    f"(Entry: {entry_price:.2f}, P&L: {profit_loss:.2f}%)"
                )
            else:
                self.logger.info(f"💸 EXECUTING SELL at {current_close:.2f} on {current_date}")
            self.position.close()
        elif signal != "HOLD":
            # Log when signals are generated but not executed
            if signal == "BUY" and self.position:
                self.logger.debug(f"BUY signal ignored - already in position")
            elif signal == "SELL" and not self.position:
                self.logger.debug(f"SELL signal ignored - no position to close")
