"""Larry Connors 2-Period RSI Strategy - Version 2 with ATR-Based Dynamic TP/SL

A mean reversion strategy with protocol-based market data and ATR-based risk management.
Extends LCRSI2 with dynamic Take Profit and Stop Loss levels based on market volatility (ATR).
"""

import pandas as pd
import talib
from backtesting import Strategy
from decimal import Decimal
from typing import Optional, Tuple

from connors_core.core.registry import registry
from connors_core.core.market_data import MarketSnapshot, DataFrameMarketSnapshot
from connors_strategies.strategies.base_logic import BaseStrategyLogic
from connors_core.core.logging import setup_strategy_logger


class LCRSI2ATRLogic(BaseStrategyLogic):
    """Strategy logic class for LCRSI2 with ATR-Based Dynamic TP/SL

    A mean reversion strategy that buys oversold stocks in an uptrend,
    with ATR-based dynamic risk management that adapts to market volatility.

    Entry Rules:
    - RSI(2) < rsi_level (oversold condition)
    - Price > long_sma (uptrend filter)

    Exit Rules (Priority Order):
    1. Stop Loss: Price <= entry_price - (ATR × sl_multiplier) → Immediate exit 🛑
    2. Take Profit: Price >= entry_price + (ATR × tp_multiplier) → Immediate exit 🎯
    3. Regular Exit: Price >= short_sma (mean reversion complete) 🔴

    This version uses MarketSnapshot protocol for 4-10x faster signal generation
    compared to DataFrame-based approach. Works for both backtesting and live trading.
    """

    def __init__(self,
                 rsi_length: int = 2,
                 rsi_level: float = 5.0,
                 short_sma_length: int = 5,
                 long_sma_length: int = 200,
                 atr_period: int = 14,
                 atr_sl_multiplier: float = 1.5,
                 atr_tp_multiplier: float = 2.5,
                 log_level: str = "INFO"):
        """Initialize strategy logic with parameters

        Args:
            rsi_length: RSI calculation period
            rsi_level: RSI oversold threshold for entry
            short_sma_length: Short SMA period for exit signal
            long_sma_length: Long SMA period for trend filter
            atr_period: ATR calculation period (default: 14)
            atr_sl_multiplier: ATR multiplier for stop loss (default: 1.5)
            atr_tp_multiplier: ATR multiplier for take profit (default: 2.5)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.rsi_length = rsi_length
        self.rsi_level = float(rsi_level)
        self.short_sma_length = short_sma_length
        self.long_sma_length = long_sma_length
        self.atr_period = atr_period
        # Ensure these are always floats (optimizer may pass integers)
        self.atr_sl_multiplier = float(atr_sl_multiplier)
        self.atr_tp_multiplier = float(atr_tp_multiplier)

        # Set up colorful logger
        self.logger = setup_strategy_logger("LCRSI2_ATR_Logic", level=log_level)

    def generate_signal(self,
                       snapshot: MarketSnapshot,
                       entry_price: Optional[Decimal] = None,
                       entry_atr: Optional[Decimal] = None) -> str:
        """Generate trading signal from market snapshot with ATR-based TP/SL

        Uses MarketSnapshot protocol for zero-copy, type-safe signal generation.
        This is 4-10x faster than DataFrame-based approach.

        Args:
            snapshot: Market snapshot with current bar and indicators
            entry_price: Entry price of current position (None if flat)
            entry_atr: ATR value at entry time (None if flat)

        Returns:
            Trading signal: "BUY", "SELL", or "HOLD"
        """
        # Get current bar and indicators (direct attribute access - FAST!)
        current_close = snapshot.bar.close
        current_rsi = snapshot.get_indicator(f"RSI_{self.rsi_length}")
        current_long_sma = snapshot.get_indicator(f"SMA_{self.long_sma_length}")
        current_short_sma = snapshot.get_indicator(f"SMA_{self.short_sma_length}")
        current_atr = snapshot.get_indicator(f"ATR_{self.atr_period}")

        # Log current market conditions (DEBUG level)
        rsi_str = f"{current_rsi:.2f}" if current_rsi is not None else "N/A"
        long_sma_str = f"{current_long_sma:.2f}" if current_long_sma is not None else "N/A"
        short_sma_str = f"{current_short_sma:.2f}" if current_short_sma is not None else "N/A"
        atr_str = f"{current_atr:.2f}" if current_atr is not None else "N/A"

        self.logger.debug(
            f"Market data - Close: {current_close:.2f}, "
            f"RSI({self.rsi_length}): {rsi_str}, "
            f"Long_SMA({self.long_sma_length}): {long_sma_str}, "
            f"Short_SMA({self.short_sma_length}): {short_sma_str}, "
            f"ATR({self.atr_period}): {atr_str}"
        )

        # Check for missing indicator values
        if current_rsi is None or current_long_sma is None or current_short_sma is None:
            self.logger.warning(
                f"Missing indicator values - RSI: {current_rsi}, "
                f"Long_SMA: {current_long_sma}, Short_SMA: {current_short_sma}"
            )
            return "HOLD"

        # === PRIORITY 1: Check ATR-Based Take Profit & Stop Loss (if in position) ===
        if entry_price is not None and entry_atr is not None:
            # Calculate dynamic TP/SL levels based on entry ATR
            stop_loss_level = entry_price - (entry_atr * Decimal(str(self.atr_sl_multiplier)))
            take_profit_level = entry_price + (entry_atr * Decimal(str(self.atr_tp_multiplier)))

            # Calculate current profit/loss percentage for logging
            pnl_pct = ((current_close - entry_price) / entry_price) * Decimal('100')

            # Stop Loss check (HIGHEST PRIORITY)
            if current_close <= stop_loss_level:
                self.logger.warning(
                    f"🛑 ATR STOP LOSS triggered - Price: ${current_close:.2f} <= SL: ${stop_loss_level:.2f} "
                    f"(Entry: ${entry_price:.2f}, ATR: {entry_atr:.2f}, Multiplier: {self.atr_sl_multiplier}x, "
                    f"P&L: {pnl_pct:.2f}%)"
                )
                return "SELL"

            # Take Profit check (SECOND PRIORITY)
            if current_close >= take_profit_level:
                self.logger.info(
                    f"🎯 ATR TAKE PROFIT triggered - Price: ${current_close:.2f} >= TP: ${take_profit_level:.2f} "
                    f"(Entry: ${entry_price:.2f}, ATR: {entry_atr:.2f}, Multiplier: {self.atr_tp_multiplier}x, "
                    f"P&L: {pnl_pct:.2f}%)"
                )
                return "SELL"

            # Log current P&L and levels if in position (DEBUG level)
            self.logger.debug(
                f"Position Status - P&L: {pnl_pct:+.2f}%, "
                f"SL: ${stop_loss_level:.2f} ({self.atr_sl_multiplier}x ATR), "
                f"TP: ${take_profit_level:.2f} ({self.atr_tp_multiplier}x ATR)"
            )

        # === PRIORITY 2: Check regular entry/exit signals ===

        # Entry signal: oversold RSI in uptrend
        if entry_price is None and current_rsi < self.rsi_level and current_close > current_long_sma:
            atr_log = f", ATR: {current_atr:.2f}" if current_atr is not None else ""
            self.logger.info(
                f"🟢 BUY signal - RSI {current_rsi:.2f} < {self.rsi_level} "
                f"AND Close {current_close:.2f} > Long_SMA {current_long_sma:.2f}{atr_log}"
            )
            return "BUY"

        # Regular exit signal: price recovers above short-term average
        if entry_price is not None and current_close >= current_short_sma:
            pnl_pct = ((current_close - entry_price) / entry_price) * Decimal('100')
            self.logger.info(
                f"🔴 REGULAR EXIT signal - Close {current_close:.2f} >= Short_SMA {current_short_sma:.2f} "
                f"(P&L: {pnl_pct:+.2f}%)"
            )
            return "SELL"

        # Log hold conditions (DEBUG level)
        if entry_price is None:
            if current_rsi >= self.rsi_level:
                self.logger.debug(f"HOLD - RSI {current_rsi:.2f} not oversold (>= {self.rsi_level})")
            if current_close <= current_long_sma:
                self.logger.debug(f"HOLD - Price {current_close:.2f} not in uptrend (<= Long_SMA {current_long_sma:.2f})")

        return "HOLD"


@registry.register_strategy("LCRSI2_ATR")
class LCRSI2_ATR_Strategy(Strategy):
    """Larry Connors 2-Period RSI Strategy - V2 with ATR-Based Dynamic TP/SL

    A mean reversion strategy that buys oversold stocks in an uptrend,
    with ATR-based dynamic risk management that adapts to market volatility.

    Uses a separate logic class for signal generation with MarketSnapshot protocol.
    This backtesting strategy uses DataFrameMarketSnapshot adapter to convert
    DataFrame data to MarketSnapshot protocol, allowing the same logic to work
    for both backtesting and live trading.

    Risk Management (Dynamic):
    - Stop Loss: Entry price - (ATR × sl_multiplier)
    - Take Profit: Entry price + (ATR × tp_multiplier)
    - Regular Exit: Price >= short_sma (mean reversion)
    """

    # === Parameters ===
    rsi_length = 2          # RSI calculation period
    rsi_level = 5           # RSI oversold threshold for entry
    short_sma_length = 5    # Short SMA for exit signal
    long_sma_length = 200   # Long SMA for trend filter
    atr_period = 14         # ATR calculation period
    atr_sl_multiplier = 1.5 # ATR multiplier for stop loss (1.5x ATR below entry)
    atr_tp_multiplier = 2.5 # ATR multiplier for take profit (2.5x ATR above entry)

    def init(self):
        """Initialize strategy logic and indicators"""
        # Set up colorful logger
        self.logger = setup_strategy_logger("LCRSI2_ATR_Strategy")

        # Log strategy initialization
        self.logger.info(
            f"✨ Initializing LCRSI2_ATR strategy with parameters: "
            f"rsi_length={self.rsi_length}, rsi_level={self.rsi_level}, "
            f"short_sma_length={self.short_sma_length}, long_sma_length={self.long_sma_length}, "
            f"atr_period={self.atr_period}, "
            f"atr_sl_multiplier={self.atr_sl_multiplier}x, atr_tp_multiplier={self.atr_tp_multiplier}x"
        )

        # Initialize strategy logic (uses MarketSnapshot protocol)
        self.logic = LCRSI2ATRLogic(
            rsi_length=self.rsi_length,
            rsi_level=self.rsi_level,
            short_sma_length=self.short_sma_length,
            long_sma_length=self.long_sma_length,
            atr_period=self.atr_period,
            atr_sl_multiplier=self.atr_sl_multiplier,
            atr_tp_multiplier=self.atr_tp_multiplier,
            log_level="INFO"  # Can be configured per strategy
        )

        # Initialize indicators using backtesting.py format
        self.rsi = self.I(lambda x: talib.RSI(x, timeperiod=self.rsi_length), self.data.Close)
        self.long_sma = self.I(lambda x: talib.SMA(x, timeperiod=self.long_sma_length), self.data.Close)
        self.short_sma = self.I(lambda x: talib.SMA(x, timeperiod=self.short_sma_length), self.data.Close)

        # ATR indicator (uses High, Low, Close)
        self.atr = self.I(
            lambda h, l, c: talib.ATR(h, l, c, timeperiod=self.atr_period),
            self.data.High, self.data.Low, self.data.Close
        )

        # Track ATR at entry time for dynamic TP/SL calculation
        self.entry_atr_value = None

        self.logger.info("✅ Strategy initialization completed")

    def next(self):
        """Execute trading logic on each bar with ATR-based TP/SL support"""
        # Get current bar index and price information
        current_bar = len(self.data) - 1
        current_close_raw = self.data.Close[-1]
        # Convert to Decimal to match backtesting.py internal types
        current_close = Decimal(str(current_close_raw)) if not isinstance(current_close_raw, Decimal) else current_close_raw
        current_date = self.data.index[-1] if hasattr(self.data, "index") else f"Bar {current_bar}"

        # Get current ATR value
        current_atr_raw = self.atr[-1]
        current_atr = Decimal(str(current_atr_raw)) if current_atr_raw is not None else None

        # Get entry price and entry ATR if in position
        entry_price = None
        entry_atr = None

        if self.position:
            if hasattr(self.position, 'entry_price'):
                raw_entry = self.position.entry_price
                # Convert to Decimal if it's a float type to match backtesting.py internal types
                if isinstance(raw_entry, (float, int)) or hasattr(raw_entry, 'dtype'):  # numpy types have dtype
                    entry_price = Decimal(str(raw_entry))
                else:
                    entry_price = raw_entry  # Already Decimal
            else:
                entry_price = None

            # Fallback: use trades history if entry_price not available
            if entry_price is None and len(self.trades) > 0:
                raw_trade_entry = self.trades[-1].entry_price if hasattr(self.trades[-1], 'entry_price') else None
                # Convert numpy.float64 to Decimal to match backtesting.py internal types
                if raw_trade_entry is not None:
                    entry_price = Decimal(str(raw_trade_entry))
                else:
                    entry_price = None

            # Get ATR at entry time
            entry_atr = self.entry_atr_value

        # Create DataFrame with current data
        current_data = pd.DataFrame({
            "Open": self.data.Open,
            "High": self.data.High,
            "Low": self.data.Low,
            "Close": self.data.Close,
            "Volume": self.data.Volume,
            f"RSI_{self.rsi_length}": self.rsi,
            f"SMA_{self.long_sma_length}": self.long_sma,
            f"SMA_{self.short_sma_length}": self.short_sma,
            f"ATR_{self.atr_period}": self.atr
        })

        # Convert DataFrame to MarketSnapshot using adapter (zero-copy for latest bar)
        snapshot = DataFrameMarketSnapshot(_data=current_data)

        # Generate signal using strategy logic with entry price and ATR for TP/SL
        signal = self.logic.generate_signal(snapshot, entry_price=entry_price, entry_atr=entry_atr)

        # Log current position and signal
        position_info = f"Position: {self.position.size if self.position else 0} shares"
        if entry_price is not None and entry_atr is not None:
            pnl_pct = ((current_close - entry_price) / entry_price) * Decimal('100')
            sl_level = entry_price - (entry_atr * Decimal(str(self.atr_sl_multiplier)))
            tp_level = entry_price + (entry_atr * Decimal(str(self.atr_tp_multiplier)))
            position_info += (
                f", Entry: ${entry_price:.2f}, P&L: {pnl_pct:+.2f}%, "
                f"SL: ${sl_level:.2f}, TP: ${tp_level:.2f}"
            )

        self.logger.debug(f"Bar {current_bar} ({current_date}) - Close: {current_close:.2f}, Signal: {signal}, {position_info}")

        # Execute trades based on signal
        if signal == "BUY" and not self.position:
            # Store ATR at entry time for TP/SL calculation
            self.entry_atr_value = current_atr

            atr_log = f", ATR: {current_atr:.2f}" if current_atr is not None else ""
            self.logger.info(f"💰 EXECUTING BUY at {current_close:.2f} on {current_date}{atr_log}")
            self.buy()

        elif signal == "SELL" and self.position:
            entry_price_log = entry_price if entry_price is not None else "N/A"
            if entry_price is not None:
                profit_loss = ((current_close - entry_price) / entry_price * Decimal('100'))
                self.logger.info(
                    f"💸 EXECUTING SELL at {current_close:.2f} on {current_date} "
                    f"(Entry: {entry_price:.2f}, P&L: {profit_loss:+.2f}%)"
                )
            else:
                self.logger.info(f"💸 EXECUTING SELL at {current_close:.2f} on {current_date}")

            # Clear entry ATR value
            self.entry_atr_value = None
            self.position.close()

        elif signal != "HOLD":
            # Log when signals are generated but not executed
            if signal == "BUY" and self.position:
                self.logger.debug(f"BUY signal ignored - already in position")
            elif signal == "SELL" and not self.position:
                self.logger.debug(f"SELL signal ignored - no position to close")
