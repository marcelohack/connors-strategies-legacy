# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a collection of external trading strategies for use with connors-backtest and the Connors Trading Playground. This is **not** a Python package — it is a plain directory of strategy files.

## Strategy Structure

Each strategy lives in its own directory:
- Main Python file implementing the strategy class
- README.md with documentation
- All strategies inherit from `backtesting.Strategy`
- Strategies using the registry use `@registry.register_strategy("Name")` decorator

## Key Imports

```python
# Registry (for framework integration)
from connors_core.core.registry import registry

# Multi-timeframe base class (from connors-backtest)
from connors_backtest.strategies.multitimeframe.base import MultiTimeframeStrategy
```

## Usage

Strategies are loaded via the CLI `--external-strategy` parameter:
```bash
python -m connors.cli.backtest \
  --external-strategy /path/to/StrategyDir/strategy_file.py \
  --strategy StrategyName \
  --tickers AAPL --config america --datasource yfinance
```

## Conventions

- Directory name matches strategy name (e.g., `VolumeByTime/volume_by_time.py`)
- Strategy class registered with `@registry.register_strategy("DirectoryName")`
- Parameters defined as class attributes with default values
- Risk management (stop loss, position sizing) included in every strategy
