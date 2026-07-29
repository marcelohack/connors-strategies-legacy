"""Larry Connors 2-Period RSI - Pure Entry/Exit Logic.

This is the shared strategy logic used by both backtesting and live bots.
It contains ONLY the core entry/exit rules — no TP/SL, no framework dependencies.

Entry: RSI(rsi_length) < rsi_level AND Close > SMA(long_sma_length)
Exit:  Close >= SMA(short_sma_length)
"""

from connors_core.core.market_data import MarketSnapshot
from connors_strategies.base_logic import BaseStrategyLogic


class RSI2Logic(BaseStrategyLogic):
    """Pure RSI-2 entry/exit signal logic.

    This class is environment-agnostic — it works with any MarketSnapshot
    implementation (DataFrameMarketSnapshot for backtesting,
    DictMarketSnapshot for live bots).

    Position awareness is passed in via `has_position` parameter rather
    than querying a broker, keeping this class free of side effects.
    """

    def __init__(
        self,
        rsi_length: int = 2,
        rsi_level: float = 5.0,
        short_sma_length: int = 5,
        long_sma_length: int = 200,
    ):
        self.rsi_length = rsi_length
        self.rsi_level = rsi_level
        self.short_sma_length = short_sma_length
        self.long_sma_length = long_sma_length

    def generate_signal(
        self,
        snapshot: MarketSnapshot,
        has_position: bool = False,
    ) -> str:
        """Generate trading signal from market snapshot.

        Args:
            snapshot: Market snapshot with current bar and indicators.
            has_position: True if currently holding a position.

        Returns:
            "BUY", "SELL", or "HOLD"
        """
        current_close = snapshot.bar.close
        current_rsi = snapshot.get_indicator(f"RSI_{self.rsi_length}")
        current_long_sma = snapshot.get_indicator(f"SMA_{self.long_sma_length}")
        current_short_sma = snapshot.get_indicator(f"SMA_{self.short_sma_length}")

        # Not enough data yet
        if current_rsi is None or current_long_sma is None or current_short_sma is None:
            return "HOLD"

        # Entry: oversold RSI in uptrend
        if not has_position:
            if current_rsi < self.rsi_level and current_close > current_long_sma:
                return "BUY"

        # Exit: price recovers above short-term average
        if has_position:
            if current_close >= current_short_sma:
                return "SELL"

        return "HOLD"
