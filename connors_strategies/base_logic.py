"""Base strategy logic interface for signal generation.

This module defines the abstract interface for strategy logic that can be
used for both backtesting and live trading. Strategy logic is separated from
framework-specific code to enable reusability.
"""

from abc import ABC, abstractmethod

from connors_core.core.market_data import MarketSnapshot


class BaseStrategyLogic(ABC):
    """Base class for strategy logic (used by both backtesting and live trading).

    Strategy logic classes should inherit from this base class and implement
    the generate_signal method. This allows the same logic to be used for:
    - Backtesting (using DataFrameMarketSnapshot adapter)
    - Live trading (using DictMarketSnapshot adapter)

    Important: This layer contains PURE entry/exit logic only.
    TP/SL and risk management are the caller's responsibility.
    """

    @abstractmethod
    def generate_signal(self, snapshot: MarketSnapshot) -> str:
        """Generate BUY/SELL/HOLD signal from market snapshot.

        Args:
            snapshot: Market snapshot with current bar and indicators

        Returns:
            Trading signal: "BUY", "SELL", or "HOLD"
        """
        pass
