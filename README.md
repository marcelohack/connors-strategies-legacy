# Connors Trading Strategies

A curated collection of quantitative trading strategies developed for systematic backtesting and execution within the [Connors Trading Playground](https://github.com/marcelohack/connors-playground) ecosystem.

## Overview

This repository contains professionally implemented trading strategies ranging from original algorithmic approaches to converted TradingView Pine Script indicators. Each strategy is built using the `backtesting.py` framework and integrates seamlessly with the Connors Trading framework for comprehensive analysis, optimization, and execution.

### Design Philosophy

- **Strategy Development**: Original quantitative strategies and proven Pine Script conversions
- **Systematic Trading**: Focus on rules-based, quantitative approaches with robust risk management
- **Framework Integration**: Native compatibility with the Connors Trading Playground for streamlined workflow
- **Educational Value**: Well-documented implementations that serve as learning resources for algorithmic trading

## Available Strategies

### 📊 Volume by Time Strategy
**Strategy Focus**: Time-based volume anomaly detection

Analyzes volume patterns by time of day and generates trading signals based on volume spikes compared to historical averages. Ideal for capturing volume-driven price movements and institutional activity patterns.

**Key Features**:
- Historical volume analysis by time periods
- Bullish/bearish volume distinction
- Multiple exit conditions (profit target, stop loss, time-based, volume normalization)
- Configurable volume threshold multipliers

**Best Use Cases**: High-volume stocks, trend-following in liquid markets, short-term trading (1-10 days)

### 📈 VWAP Price Channel Strategy
**Strategy Focus**: Dynamic price channel breakouts

Creates adaptive price channels using Volume Weighted Average Price (VWAP) calculations anchored to highest and lowest price levels. Captures breakout movements with volume confirmation.

**Key Features**:
- VWAP-based channel construction with automatic resets
- Trend-aware signal filtering
- Dynamic channel adaptation to market volatility
- Volume-weighted price level calculations

**Best Use Cases**: Trending markets, breakout trading, instruments with reliable volume data

### 🏛️ Smart Money Concepts Strategy
**Strategy Focus**: Institutional trading methodology

Comprehensive implementation of Smart Money Concepts (SMC) including market structure analysis, order blocks, fair value gaps, and premium/discount zones. Follows institutional trading patterns and "smart money" movements.

**Key Features**:
- Market structure break detection (BOS/CHoCH)
- Order block identification and tracking
- Fair Value Gap (FVG) detection and mitigation
- Premium/discount zone analysis
- Multi-factor confluence requirements

**Best Use Cases**: Higher timeframe trading, trend following with institutional confirmation, complex multi-factor strategies

## Quick Start

### Prerequisites

```bash
# Core dependencies
pip install pandas numpy talib backtesting yfinance

# Connors Trading framework (from playground repository)
# Follow setup instructions at: https://github.com/marcelohack/connors-playground
```

### Basic Usage

#### 1. Direct Backtesting with backtesting.py

```python
from backtesting import Backtest
import yfinance as yf
import sys

# Add strategy path
sys.path.insert(0, '/path/to/strategies')
from VolumeByTime.volume_by_time import VolumeByTimeStrategy

# Download data
data = yf.download('AAPL', start='2023-01-01', end='2023-12-31')
data.columns = data.columns.droplevel(1)

# Run backtest
bt = Backtest(data, VolumeByTimeStrategy, cash=10000, commission=.002)
stats = bt.run()
print(stats)

# Visualize results
bt.plot()
```

#### 2. Connors Trading Playground Integration

```bash
# Set up environment
source setenv.sh

# Run backtest via Connors CLI
PYTHONPATH="/path/to/strategies:$PYTHONPATH" \
python -m connors.cli.backtest \
  --external-strategy /path/to/strategies/VolumeByTime/volume_by_time.py \
  --strategy VolumeByTime \
  --tickers AAPL \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31 \
  --cash 10000
```

#### 3. Parameter Optimization

```python
# Optimize strategy parameters
bt = Backtest(data, VolumeByTimeStrategy, cash=10000, commission=.002)

stats = bt.optimize(
    volume_threshold_multiplier=range(15, 40, 5),  # 1.5x to 4.0x
    profit_target_pct=range(3, 11, 2),             # 3% to 10%
    stop_loss_pct=range(1, 6, 1),                  # 1% to 5%
    maximize='Sharpe Ratio'
)
```

## Repository Structure

Each strategy follows a consistent directory structure pattern:

```
connors-trading-strategies/
├── README.md                           # This file
├── CLAUDE.md                          # Claude Code guidance
├── <TradingStrategyName>/              # Strategy directory
│   ├── <strategy_file>.py             # Strategy implementation
│   └── README.md                      # Detailed strategy documentation
├── VolumeByTime/                      # Example: Volume analysis strategy
│   ├── volume_by_time.py
│   └── README.md
├── VWAPPriceChannel/                  # Example: VWAP-based strategy
│   ├── vwap_price_channel.py
│   └── README.md
└── SmartMoneyConcepts/                # Example: Institutional concepts
    ├── smart_money_concepts.py
    └── README.md
```

### Naming Convention
- **Directory Name**: `<TradingStrategyName>` (e.g., `VolumeByTime`, `MeanReversion`, `BreakoutMomentum`)
- **Python File**: Descriptive filename matching the strategy (e.g., `volume_by_time.py`, `mean_reversion.py`)
- **Strategy Class**: Registered with `@registry.register_strategy("<TradingStrategyName>")`

## Strategy Development Guidelines

### Framework Compatibility

All strategies follow consistent patterns for seamless integration:

```python
from backtesting import Strategy
from connors.core.registry import registry

@registry.register_strategy("StrategyName")
class YourStrategy(Strategy):
    # Parameters as class attributes
    param1 = 10
    param2 = 2.0

    def init(self):
        # Initialize indicators using self.I() wrapper
        self.indicator = self.I(some_indicator_function)

    def next(self):
        # Trading logic
        if entry_condition:
            self.buy()
        elif exit_condition:
            self.position.close()
```

### Parameter Override System

Strategies support runtime parameter modification via CLI:

```bash
--strategy-params "volume_threshold_multiplier:3.0;profit_target_pct:7.0;stop_loss_pct:1.5"
```

### Risk Management Standards

All strategies implement consistent risk management:
- **Position Sizing**: Percentage-based or fixed dollar amounts
- **Stop Losses**: ATR-based or percentage-based stops
- **Profit Targets**: Risk-reward ratio based targets
- **Time Exits**: Maximum holding period limits
- **Drawdown Protection**: Optional maximum drawdown limits

## Advanced Usage

### Multi-Strategy Portfolio

```python
# Run multiple strategies on portfolio of instruments
strategies = ['VolumeByTime', 'VWAPPriceChannel', 'SmartMoneyConcepts']
tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

for strategy in strategies:
    for ticker in tickers:
        # Run backtest for each combination
        # Aggregate results for portfolio analysis
```

### Parameter Optimization Workflows

```python
# Multi-objective optimization
from backtesting.lib import optimize_by

# Optimize for multiple metrics
results = bt.optimize(
    param1=range(10, 50, 5),
    param2=[1.0, 1.5, 2.0, 2.5, 3.0],
    maximize=lambda stats: stats['Sharpe Ratio'] * stats['Return [%]'],
    constraint=lambda stats: stats['Max. Drawdown [%]'] < -10
)
```

### Integration with Connors Playground

The strategies in this repository are designed to work seamlessly with the [Connors Trading Playground](https://github.com/marcelohack/connors-playground) ecosystem:

1. **Data Sources**: Compatible with multiple data providers (yfinance, Alpha Vantage, etc.)
2. **Execution Engine**: Can be deployed for live trading through the playground's execution framework
3. **Analysis Tools**: Integrates with the playground's performance analysis and reporting tools
4. **Parameter Management**: Supports the playground's configuration and parameter override systems

## Performance Considerations

### Strategy Selection Guidelines

| Market Condition | Recommended Strategy | Key Parameters |
|------------------|---------------------|----------------|
| **High Volume Trending** | Volume by Time | `volume_threshold_multiplier: 2.0-3.0` |
| **Breakout Markets** | VWAP Price Channel | `channel_breakout_threshold: 0.001-0.005` |
| **Institutional Patterns** | Smart Money Concepts | `risk_per_trade: 1.0-2.0%` |
| **Range-Bound** | Volume by Time (conservative) | `volume_threshold_multiplier: 3.0+` |

### Optimization Best Practices

1. **Walk-Forward Analysis**: Use rolling optimization windows
2. **Out-of-Sample Testing**: Reserve 20-30% of data for validation
3. **Multiple Timeframes**: Test on different intervals (1H, 4H, 1D)
4. **Market Regime Analysis**: Evaluate performance across different market conditions
5. **Transaction Cost Modeling**: Include realistic commission and slippage

## Contributing

### Adding New Strategies

1. **Create Strategy Directory**: Follow naming convention `<TradingStrategyName>/`
   ```bash
   mkdir MeanReversion
   cd MeanReversion
   ```

2. **Implement Strategy Class**: Create Python file inheriting from `backtesting.Strategy`
   ```python
   # mean_reversion.py
   from backtesting import Strategy
   from connors.core.registry import registry

   @registry.register_strategy("MeanReversion")
   class MeanReversionStrategy(Strategy):
       # Your strategy implementation
   ```

3. **Strategy Registration**: Use the directory name in the decorator
   ```python
   @registry.register_strategy("MeanReversion")  # Matches directory name
   ```

4. **Create Documentation**: Comprehensive README.md with:
   - Strategy logic explanation
   - Parameter descriptions
   - Usage examples
   - Performance characteristics

5. **Framework Compatibility**: Ensure integration with Connors Trading framework

### Strategy Development Types

- **Original Strategies**: Develop algorithmic approaches from research, academic papers, or trading ideas
- **Pine Script Conversions**: Convert proven TradingView Pine Script indicators into systematic strategies
- **Hybrid Approaches**: Combine multiple concepts or enhance existing strategies with additional filters/conditions

### Code Standards

- **Documentation**: Comprehensive docstrings and README files
- **Parameter Naming**: Consistent naming conventions across strategies
- **Risk Management**: Always include stop loss and position sizing
- **Testing**: Validate on multiple instruments and time periods
- **Performance**: Optimize for speed in `next()` method

## Resources

### Related Projects
- [Connors Trading Playground](https://github.com/marcelohack/connors-playground) - Main trading framework
- [backtesting.py](https://kernc.github.io/backtesting.py/) - Core backtesting framework
- [TA-Lib](https://ta-lib.org/) - Technical analysis library

### Educational Materials
- Strategy documentation in individual README files
- Original strategy development patterns
- Pine Script to Python conversion examples
- Risk management implementation examples
- Parameter optimization methodologies

### Support
- Issues: Open GitHub issues for bugs or questions
- Discussions: Use GitHub Discussions for strategy ideas and optimizations
- Documentation: Refer to individual strategy README files for detailed information

## License

This project follows the same licensing terms as the Connors Trading Playground framework.

---

**Disclaimer**: These strategies are for educational and research purposes. Past performance does not guarantee future results. Always perform your own due diligence and risk assessment before deploying any trading strategy with real capital.