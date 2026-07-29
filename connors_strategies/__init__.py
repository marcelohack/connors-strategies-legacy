"""Connors Strategies - Shared strategy logic for backtesting and live trading.

Strategy logic classes depend only on the MarketSnapshot protocol from
connors_core, making them environment-agnostic. TP/SL is NOT part of this
layer — it's the caller's responsibility (RiskManager in bots, embedded
in backtest strategy wrappers).

Lab strategies (experimental, backtesting.py-specific) live in the stratslab repo.
"""

from connors_strategies.base_logic import BaseStrategyLogic
from connors_strategies.rsi2_logic import RSI2Logic
from connors_strategies.multitimeframe_base import MultiTimeframeStrategy

__all__ = [
    "BaseStrategyLogic",
    "RSI2Logic",
    "MultiTimeframeStrategy",
]
