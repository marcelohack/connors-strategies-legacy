# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Shared strategy logic package (`connors_strategies`) for the Connors trading system. Contains environment-agnostic strategy logic classes used by both backtesting and live trading bots.

Experimental backtesting strategies have been moved to the `stratslab` repo (`../stratslab`).

## Package Structure

- `connors_strategies/base_logic.py` — Abstract `BaseStrategyLogic` interface
- `connors_strategies/rsi2_logic.py` — Larry Connors 2-Period RSI logic
- `tests/` — Package tests

## Key Imports

```python
from connors_strategies import BaseStrategyLogic, RSI2Logic
from connors_core.core.market_data import MarketSnapshot
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
