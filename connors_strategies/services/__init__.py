"""
Service layer for Connors Strategies

Provides high-level business logic interfaces for UI and API integration.
"""

from connors_strategies.services.backtest_service import BacktestService

__all__ = [
    "BacktestService",
]
