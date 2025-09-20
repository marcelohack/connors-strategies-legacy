# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a collection of trading strategies converted from Pine Script to Python, designed to work with the Connors Trading framework and backtesting.py. The repository contains three main strategy implementations:

- **VolumeByTime**: Analyzes volume patterns by time of day, generates signals based on volume anomalies
- **VWAPPriceChannel**: Creates dynamic price channels using VWAP calculations anchored to price extremes
- **SmartMoneyConcepts**: Implements institutional trading concepts (order blocks, fair value gaps, market structure)

## Architecture

### Strategy Structure
Each strategy is organized in its own directory with:
- Main Python file implementing the strategy class
- README.md with detailed documentation and usage examples
- All strategies inherit from `backtesting.Strategy` base class
- All strategies use `@registry.register_strategy("StrategyName")` decorator for framework integration

### Dependencies
Common dependencies across all strategies:
- `pandas`: Data manipulation
- `numpy`: Numerical calculations
- `talib`: Technical analysis functions
- `backtesting`: Backtesting framework
- `connors.core.registry`: Strategy registration system

### Framework Integration
All strategies are compatible with the Connors Trading framework:
- Registry system for automatic strategy discovery
- CLI backtesting via `--external-strategy` parameter
- Parameter override system using `--strategy-params`
- Standard strategy parameter and indicator patterns

## Usage Patterns

### Running Strategies with Connors CLI
```bash
# Basic backtest
python -m connors.cli.backtest \
  --external-strategy /path/to/strategy.py \
  --strategy StrategyName \
  --tickers AAPL \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31

# With parameter overrides
python -m connors.cli.backtest \
  --external-strategy /path/to/strategy.py \
  --strategy StrategyName \
  --strategy-params "param1:value1;param2:value2" \
  --tickers AAPL \
  --config america \
  --datasource yfinance
```

### PYTHONPATH Management
When using external strategies, add the strategies directory to PYTHONPATH:
```bash
PYTHONPATH="/Users/mhack/.connors/strategies:$PYTHONPATH" python -m connors.cli.backtest ...
```

### Direct backtesting.py Usage
```python
from backtesting import Backtest
from strategy_module import StrategyClass
import yfinance as yf

# Load data
data = yf.download("AAPL", start="2023-01-01", end="2023-12-31")
data.columns = data.columns.droplevel(1)

# Run backtest
bt = Backtest(data, StrategyClass, cash=10000, commission=.002)
stats = bt.run()
```

## Strategy Characteristics

### VolumeByTime Strategy
- Focuses on time-based volume analysis and anomaly detection
- Key parameters: `volume_threshold_multiplier`, `length_days`, `analysis_type`
- Best suited for liquid stocks with consistent volume patterns
- Designed for short-term trading (1-10 days holding period)

### VWAPPriceChannel Strategy
- Uses VWAP calculations with dynamic channel construction
- Key parameters: `length`, `channel_breakout_threshold`, `use_trend_filter`
- Adaptive to market volatility, requires reliable volume data
- Works well in trending markets with clear directional moves

### SmartMoneyConcepts Strategy
- Implements institutional trading methodology (SMC)
- Key parameters: `swing_length`, `risk_per_trade`, `reward_risk_ratio`
- Multiple confluence factors: order blocks, fair value gaps, market structure
- Complex strategy requiring parameter optimization for specific instruments

## Development Guidelines

### Parameter Configuration
- All strategies support parameter overrides via CLI `--strategy-params`
- Use semicolon-separated key:value pairs: `"param1:value1;param2:value2"`
- Parameters are defined as class attributes with default values
- Risk management parameters are consistently named across strategies

### Code Conventions
- All strategies inherit from `backtesting.Strategy`
- Use `@registry.register_strategy("Name")` decorator for framework registration
- Implement `init()` method for indicator setup
- Implement `next()` method for trading logic
- Use `self.I()` wrapper for indicators to enable plotting and optimization

### Testing and Validation
- No formal test suite exists - strategies are validated through backtesting
- Use parameter optimization features in backtesting.py for validation
- Compare results across different time periods and instruments
- Validate strategy logic through manual inspection of individual trades

## File Locations
- Strategy files: Each in own subdirectory (e.g., `VolumeByTime/volume_by_time.py`)
- Documentation: README.md files in each strategy directory
- No separate test files or configuration files
- Strategies are self-contained within their directories