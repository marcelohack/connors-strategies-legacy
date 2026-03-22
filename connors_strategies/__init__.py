"""Connors Strategies - Shared strategy logic for backtesting and live trading.

Strategy logic classes depend only on the MarketSnapshot protocol from
connors_core, making them environment-agnostic. TP/SL is NOT part of this
layer — it's the caller's responsibility (RiskManager in bots, embedded
in backtest strategy wrappers).

Lab strategies (experimental, backtesting.py-specific) live in ../labs/.
"""

from connors_strategies.base_logic import BaseStrategyLogic
from connors_strategies.lcrsi2_logic import LCRSI2Logic

__all__ = [
    "BaseStrategyLogic",
    "LCRSI2Logic",
]
