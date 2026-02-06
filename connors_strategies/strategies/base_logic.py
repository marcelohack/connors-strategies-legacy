"""Base strategy logic interface for signal generation.

This module defines the abstract interface for strategy logic that can be
used for both backtesting and live trading. Strategy logic is separated from
the backtesting framework to enable reusability.
"""

from abc import ABC, abstractmethod
import pandas as pd

from connors_core.core.market_data import MarketSnapshot, DataFrameMarketSnapshot


class BaseStrategyLogic(ABC):
    """Base class for strategy logic (used by both backtesting and live trading).

    Strategy logic classes should inherit from this base class and implement
    the generate_signal method. This allows the same logic to be used for:
    - Backtesting (using DataFrame adapter)
    - Live trading (using broker-specific MarketSnapshot implementations)
    """

    @abstractmethod
    def generate_signal(self, snapshot: MarketSnapshot) -> str:
        """Generate BUY/SELL/HOLD signal from market snapshot.

        This method is used for LIVE TRADING (performance-critical).
        Receives a MarketSnapshot which is a zero-copy wrapper around
        broker-native data structures.

        Args:
            snapshot: Market snapshot with current bar and indicators

        Returns:
            Trading signal: "BUY", "SELL", or "HOLD"
        """
        pass

    def generate_signal_from_dataframe(self, data: pd.DataFrame) -> str:
        """Convenience method for backtesting (optional override).

        Default implementation converts DataFrame to MarketSnapshot using
        the DataFrameMarketSnapshot adapter. Can be overridden if needed
        for custom DataFrame handling.

        Args:
            data: DataFrame with OHLCV and indicator columns

        Returns:
            Trading signal: "BUY", "SELL", or "HOLD"
        """
        snapshot = DataFrameMarketSnapshot(_data=data)
        return self.generate_signal(snapshot)
