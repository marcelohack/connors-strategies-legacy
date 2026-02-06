"""
RSI Crypto Strategy - Optimized for 1-Hour Crypto Charts

Based on research from MC² Finance article:
https://www.mc2.fi/blog/best-rsi-settings-for-1-hour-chart-crypto

Key Insights:
- Standard RSI(14, 70/30) doesn't perform well in crypto
- Crypto volatility requires adjusted thresholds: 80/20 or 75/25
- Combining RSI with trend filters (EMA) improves accuracy
- RSI divergences provide competitive edge

Strategy Rules:
- Entry: RSI < oversold_level (default 20) AND price > trend_ema (default 200)
- Exit: RSI > overbought_level (default 80)
- Trend Filter: 200 EMA to avoid counter-trend trades
"""

import logging
from backtesting import Strategy
from backtesting.lib import crossover, FractionalBacktest
import numpy as np
import talib

from connors_core.core.registry import registry


@registry.register_strategy("RSI_Crypto")
class RSICryptoStrategy(Strategy, FractionalBacktest):
    """
    RSI Crypto Strategy - Optimized for volatile crypto markets

    Designed for 1-hour timeframe but adaptable to other timeframes.
    Uses conservative RSI thresholds (80/20) to reduce false signals
    in high-volatility crypto markets.

    Parameters:
        rsi_length: RSI calculation period (default: 14)
        oversold_level: Oversold threshold for entry (default: 20, more conservative than 30)
        overbought_level: Overbought threshold for exit (default: 80, more conservative than 70)
        trend_ema_length: EMA length for trend filter (default: 200)
        use_trend_filter: Enable/disable trend filter (default: True)

    Entry Signal:
        - RSI drops below oversold_level (default: 20)
        - Price is above trend_ema (if use_trend_filter=True)

    Exit Signal:
        - RSI rises above overbought_level (default: 80)
    """

    # Strategy parameters
    rsi_length = 14
    oversold_level = 20  # More conservative than standard 30
    overbought_level = 80  # More conservative than standard 70
    trend_ema_length = 200  # Long-term trend filter
    use_trend_filter = True  # Enable trend filter by default

    def init(self):
        """Initialize indicators"""
        self.logger = logging.getLogger(f"{__name__}.RSICryptoStrategy")

        # RSI indicator using TA-Lib
        close = self.data.Close
        self.rsi = self.I(lambda x: talib.RSI(x, timeperiod=self.rsi_length), close)

        # Trend filter (200 EMA) using TA-Lib
        if self.use_trend_filter:
            self.trend_ema = self.I(
                lambda x: talib.EMA(x, timeperiod=self.trend_ema_length),
                close,
                overlay=True
            )

        self.logger.info(
            f"RSI_Crypto initialized: RSI({self.rsi_length}), "
            f"Thresholds: {self.oversold_level}/{self.overbought_level}, "
            f"Trend Filter: {self.use_trend_filter} (EMA{self.trend_ema_length})"
        )

    def next(self):
        """Execute strategy logic on each bar"""
        price = self.data.Close[-1]
        rsi_value = self.rsi[-1]

        # Skip if RSI not ready
        if np.isnan(rsi_value):
            return

        # Check trend filter
        in_uptrend = True
        if self.use_trend_filter and len(self.trend_ema) > 0:
            trend_ema_value = self.trend_ema[-1]
            in_uptrend = price > trend_ema_value

        # Entry Logic: RSI oversold AND in uptrend (if filter enabled)
        if not self.position:
            if rsi_value < self.oversold_level and in_uptrend:
                self.logger.info(
                    f"BUY Signal: RSI={rsi_value:.2f} < {self.oversold_level}, "
                    f"Price={price:.2f}, In Uptrend={in_uptrend}"
                )
                self.buy()

        # Exit Logic: RSI overbought
        elif self.position:
            if rsi_value > self.overbought_level:
                self.logger.info(
                    f"SELL Signal: RSI={rsi_value:.2f} > {self.overbought_level}, "
                    f"Price={price:.2f}"
                )
                self.position.close()


@registry.register_strategy("RSI_Crypto_Fast")
class RSICryptoFastStrategy(RSICryptoStrategy):
    """
    Faster RSI Crypto Strategy - Uses shorter RSI period for quicker signals

    Based on article recommendation for more active trading.
    Uses RSI(7) instead of RSI(14) for faster reaction to price changes.

    WARNING: Produces more signals but also more false positives!

    Parameters:
        rsi_length: 7 (faster than standard 14)
        oversold_level: 20
        overbought_level: 80
        trend_ema_length: 200
        use_trend_filter: True
    """

    # Override default RSI length for faster signals
    rsi_length = 7

    def init(self):
        """Initialize with faster RSI settings"""
        super().init()
        self.logger.info(
            f"RSI_Crypto_Fast initialized: RSI({self.rsi_length}) - FAST MODE"
        )


@registry.register_strategy("RSI_Crypto_Conservative")
class RSICryptoConservativeStrategy(RSICryptoStrategy):
    """
    Conservative RSI Crypto Strategy - Stricter thresholds for fewer but higher-quality signals

    Uses even more extreme thresholds (85/15) to filter out noise
    in highly volatile crypto markets.

    Parameters:
        rsi_length: 14
        oversold_level: 15 (very conservative)
        overbought_level: 85 (very conservative)
        trend_ema_length: 200
        use_trend_filter: True
    """

    # More conservative thresholds
    oversold_level = 15
    overbought_level = 85

    def init(self):
        """Initialize with conservative settings"""
        super().init()
        self.logger.info(
            f"RSI_Crypto_Conservative initialized: "
            f"Thresholds: {self.oversold_level}/{self.overbought_level} - CONSERVATIVE MODE"
        )


@registry.register_strategy("RSI_Crypto_No_Filter")
class RSICryptoNoFilterStrategy(RSICryptoStrategy):
    """
    RSI Crypto Strategy WITHOUT Trend Filter

    Trades both with and against the trend.
    Higher risk but potentially more opportunities.

    Parameters:
        rsi_length: 14
        oversold_level: 20
        overbought_level: 80
        trend_ema_length: 200 (not used)
        use_trend_filter: False (DISABLED)
    """

    # Disable trend filter
    use_trend_filter = False

    def init(self):
        """Initialize without trend filter"""
        super().init()
        self.logger.info(
            f"RSI_Crypto_No_Filter initialized: NO TREND FILTER - Higher risk!"
        )
