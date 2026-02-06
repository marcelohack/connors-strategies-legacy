"""
Multi-Timeframe RSI2 Strategy

A multi-timeframe version of the RSI2 strategy that uses:
- Weekly trend filter (SMA 20)
- Daily RSI2 oversold signal (<5)
- Hourly entry timing
"""

import talib
from typing import Any, Dict

from connors_core.core.registry import registry
from connors_strategies.strategies.multitimeframe.base import MultiTimeframeStrategy


@registry.register_strategy("MTF_RSI2")
class MTF_RSI2_Strategy(MultiTimeframeStrategy):
    """
    Multi-Timeframe RSI2 Strategy

    Entry Rules:
    - Weekly trend: Price > 20-week SMA (uptrend filter)
    - Daily signal: RSI(2) < 5 (oversold condition)
    - Entry timing: Current bar execution

    Exit Rules:
    - Price > 5-day SMA (mean reversion complete)
    """

    # Multi-timeframe configuration
    timeframes = ['1wk', '1d']  # Weekly trend, daily signals
    primary_timeframe = '1d'   # Execute trades on daily bars

    # Strategy parameters
    weekly_sma_length = 20     # Weekly trend SMA
    daily_rsi_length = 2       # Daily RSI period
    daily_rsi_level = 5        # RSI oversold threshold
    daily_exit_sma_length = 5  # Daily exit SMA

    def __init__(self, broker=None, data=None, params=None):
        super().__init__(broker, data, params)

    def _init_indicators(self):
        """Initialize indicators for each timeframe"""

        # Weekly timeframe indicators
        weekly_data = self.get_timeframe_data('1wk')
        self.weekly_trend = self.I(
            lambda x: talib.SMA(x, timeperiod=self.weekly_sma_length),
            weekly_data.Close,
            name='Weekly_SMA'
        )

        # Daily timeframe indicators
        daily_data = self.get_timeframe_data('1d')
        self.daily_rsi = self.I(
            lambda x: talib.RSI(x, timeperiod=self.daily_rsi_length),
            daily_data.Close,
            name='Daily_RSI'
        )
        self.daily_exit_sma = self.I(
            lambda x: talib.SMA(x, timeperiod=self.daily_exit_sma_length),
            daily_data.Close,
            name='Daily_Exit_SMA'
        )

    def next(self):
        """Execute trading logic on each bar"""

        # Get current prices and indicator values
        current_close = self.data.Close[-1]
        current_date = self.data.index[-1] if hasattr(self.data, "index") else f"Bar {len(self.data) - 1}"

        # Weekly trend check (current close vs weekly SMA)
        weekly_sma_current = self.weekly_trend[-1]
        weekly_uptrend = current_close > weekly_sma_current

        # Daily RSI signal
        daily_rsi_current = self.daily_rsi[-1]
        daily_oversold = daily_rsi_current < self.daily_rsi_level

        # Daily exit signal
        daily_exit_sma_current = self.daily_exit_sma[-1]

        # Log current market conditions (DEBUG level)
        self.logger.debug(
            f"Market data - Date: {current_date}, Close: {current_close:.2f}, "
            f"Weekly_SMA: {weekly_sma_current:.2f}, Daily_RSI: {daily_rsi_current:.2f}, "
            f"Exit_SMA: {daily_exit_sma_current:.2f}"
        )

        # Entry logic: No position AND weekly uptrend AND daily oversold
        if not self.position:
            if weekly_uptrend and daily_oversold:
                self.logger.info(
                    f"🟢 BUY signal - Weekly uptrend (close {current_close:.2f} > SMA {weekly_sma_current:.2f}) "
                    f"AND Daily oversold (RSI {daily_rsi_current:.2f} < {self.daily_rsi_level})"
                )
                self.logger.info(f"💰 EXECUTING BUY at {current_close:.2f} on {current_date}")
                self.buy(size=1)

        # Exit logic: Has position AND price above daily exit SMA
        else:
            if current_close >= daily_exit_sma_current:
                entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
                if entry_price:
                    profit_loss = ((current_close - entry_price) / entry_price * 100)
                    self.logger.info(
                        f"🔴 SELL signal - Close {current_close:.2f} >= Exit_SMA {daily_exit_sma_current:.2f}"
                    )
                    self.logger.info(
                        f"💸 EXECUTING SELL at {current_close:.2f} on {current_date} "
                        f"(Entry: {entry_price:.2f}, P&L: {profit_loss:.2f}%)"
                    )
                else:
                    self.logger.info(
                        f"🔴 SELL signal - Close {current_close:.2f} >= Exit_SMA {daily_exit_sma_current:.2f}"
                    )
                    self.logger.info(f"💸 EXECUTING SELL at {current_close:.2f} on {current_date}")
                self.position.close()

    def get_strategy_metadata(self) -> Dict[str, Any]:
        """Get strategy-specific metadata"""
        metadata = super().get_strategy_metadata()
        metadata.update({
            "strategy_type": "Mean Reversion with Trend Filter",
            "weekly_sma_period": self.weekly_sma_length,
            "daily_rsi_period": self.daily_rsi_length,
            "daily_rsi_threshold": self.daily_rsi_level,
            "exit_sma_period": self.daily_exit_sma_length,
        })
        return metadata