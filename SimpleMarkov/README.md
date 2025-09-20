# Simple Markov Strategy

A mean-reversion trading strategy that exploits short-term market inefficiencies following extended selling pressure by detecting consecutive red candles and entering positions expecting a bounce.

**Original Sources**:
- [YouTube: Trading Strategy Development](https://www.youtube.com/watch?v=GWW5L07-etg)
- [Google Colab Research](https://colab.research.google.com/drive/1xSB16U50eIcreJeZyYfexLswbPx8vjeZ#scrollTo=tqRldM3bLqbE)
**Strategy Type**: Original algorithmic development
**Implementation**: Python backtesting.py framework

## Overview

The Simple Markov Strategy is based on the principle that markets exhibit short-term mean-reversion behavior after periods of sustained selling pressure. When the strategy detects a specified number of consecutive red candles (bearish candles where Close < Open), it enters a long position expecting a technical bounce.

### Core Hypothesis

Financial markets occasionally experience selling pressure that pushes prices below their short-term equilibrium. After multiple consecutive red candles, the probability of a mean-reversion bounce increases, creating a statistical edge for contrarian traders.

## Strategy Logic

### Entry Conditions

1. **Consecutive Red Candle Detection**: Identify when the last `n` bars were all red candles
2. **Red Candle Definition**: Close price < Open price (bearish candle)
3. **Pattern Confirmation**: All consecutive bars must satisfy the red candle criteria
4. **Position Entry**: Enter long position at the next bar's open

### Exit Conditions

1. **Fixed Holding Period**: Close position after exactly one bar
2. **Execution Timing**: Position closes at the next bar's open (not current bar's close)

### Critical Backtesting.py Behavior

⚠️ **Important Understanding**: The strategy's behavior in backtesting.py differs from initial intuition:

- **Order Execution**: All orders execute at bar OPEN prices
- **Position Closing**: When `self.position.close()` is called in `next()`, the position closes at the NEXT bar's open
- **Holding Period**: Positions are held from current bar's open to next bar's open
- **Gap Risk**: Strategy is exposed to after-hours price movements and opening gaps

### Special Case: Consecutive Red Continuation

If the current bar is also red (creating 4+ consecutive red candles):
- A sell order (position close) and buy order (new position) both execute at next day's open
- Orders effectively cancel out, maintaining the position
- Strategy continues holding until a green bar occurs

## Parameters

### Core Parameters
- `consecutive_red_bars` (default: 3): Number of consecutive red candles required to trigger entry
- `max_position_size` (default: 1.0): Maximum position size as percentage of available capital

### Risk Management
- **Position Sizing**: Configurable maximum position size
- **Holding Period**: Fixed one-bar holding period minimizes exposure
- **No Stop Loss**: Strategy relies on short holding period for risk control

## Usage Examples

### Basic Usage with Python

```python
from backtesting import Backtest
import yfinance as yf
import sys

# Add strategy path
sys.path.insert(0, '/path/to/strategies')
from SimpleMarkov.simple_markov import SimpleMarkovStrategy

# Download data
data = yf.download('SPY', start='2020-01-01', end='2023-12-31')
data.columns = data.columns.droplevel(1)

# Run backtest
bt = Backtest(data, SimpleMarkovStrategy, cash=10000, commission=.002)
stats = bt.run()
print(stats)

# Visualize results
bt.plot()
```

### Connors Trading Playground Integration

```bash
# Run backtest via Connors CLI
PYTHONPATH="/path/to/strategies:$PYTHONPATH" \
python -m connors.cli.backtest \
  --external-strategy /path/to/strategies/SimpleMarkov/simple_markov.py \
  --strategy SimpleMarkov \
  --tickers SPY \
  --config america \
  --datasource yfinance \
  --start 2020-01-01 \
  --end 2023-12-31 \
  --cash 10000
```

### Parameter Optimization

```python
# Optimize consecutive red bars parameter
bt = Backtest(data, SimpleMarkovStrategy, cash=10000, commission=.002)

stats = bt.optimize(
    consecutive_red_bars=range(2, 8),  # Test 2 to 7 consecutive red bars
    maximize='Sharpe Ratio'
)
```

### Custom Parameters

```bash
# Run with custom parameters
python -m connors.cli.backtest \
  --external-strategy /path/to/strategies/SimpleMarkov/simple_markov.py \
  --strategy SimpleMarkov \
  --strategy-params "consecutive_red_bars:4;max_position_size:0.5" \
  --tickers QQQ \
  --config america \
  --datasource yfinance
```

## Strategy Performance Characteristics

### Strengths

- **Simple Logic**: Easy to understand and implement
- **Short Exposure**: One-bar holding period limits risk
- **Mean Reversion Edge**: Exploits psychological overselling
- **Low Complexity**: Minimal computational requirements
- **Broad Applicability**: Works across different instruments and timeframes

### Limitations

- **Gap Risk**: Vulnerable to adverse opening gaps
- **Limited Profit Capture**: One-bar holding may miss extended bounces
- **False Signals**: Red candles don't always lead to bounces
- **Transaction Costs**: Frequent trading increases commission impact
- **Market Regime Dependency**: Performance varies in trending vs. ranging markets

### Optimization Considerations

1. **Consecutive Bar Count**: Test different values (2-7 bars)
2. **Market Conditions**: Performance may vary in bull vs. bear markets
3. **Timeframe Analysis**: Test on different intervals (daily, hourly, etc.)
4. **Asset Selection**: Some instruments may show stronger mean-reversion patterns
5. **Volume Confirmation**: Consider adding volume filters for stronger signals

## Risk Factors

### Primary Risks

1. **Gap Risk**: After-hours events can create significant opening gaps
2. **Trend Risk**: Strategy may underperform in strong trending markets
3. **Commission Drag**: High trading frequency increases transaction costs
4. **Concentration Risk**: Single-bar holding creates timing dependency

### Risk Mitigation

- **Position Sizing**: Use conservative position sizes
- **Market Selection**: Focus on liquid instruments with tight spreads
- **Time Diversification**: Consider multiple timeframe implementations
- **Commission Optimization**: Use low-cost brokers for frequent trading

## Implementation Notes

### Code Quality Features

- **Comprehensive Documentation**: Detailed docstrings and comments
- **Modular Design**: Clean separation of pattern detection logic
- **Error Handling**: Proper data validation and edge case management
- **Registry Integration**: Compatible with Connors Trading framework
- **Testing Support**: Built-in example usage and validation

### Framework Compatibility

- ✅ Registry system integration with `@registry.register_strategy("SimpleMarkov")`
- ✅ CLI backtesting support via `--external-strategy` parameter
- ✅ Parameter override system compatible
- ✅ Standard backtesting.py Strategy inheritance
- ✅ No external indicator dependencies

## Research Extensions

### Potential Improvements

1. **Multi-Timeframe Confirmation**: Combine daily patterns with intraday signals
2. **Volume Analysis**: Add volume confirmation for stronger setups
3. **Volatility Adjustment**: Scale position size based on market volatility
4. **Exit Optimization**: Test alternative exit rules (profit targets, trailing stops)
5. **Market Regime Filters**: Adapt behavior based on market conditions

### Academic Research

The strategy builds on established behavioral finance concepts:
- **Loss Aversion**: Investors overreact to consecutive losses
- **Mean Reversion**: Short-term price movements tend to reverse
- **Market Microstructure**: Order flow imbalances create temporary inefficiencies

## Integration with Connors Framework

The strategy is fully compatible with the connors_trading framework:
- **Registry System**: Automatic strategy discovery
- **CLI Integration**: Seamless backtesting and parameter management
- **Data Sources**: Compatible with multiple data providers
- **Performance Analysis**: Integration with framework's analysis tools

## Files Structure

```
SimpleMarkov/
├── simple_markov.py          # Main strategy implementation
└── README.md                 # This documentation file
```

## Version History

- **v1.0**: Initial implementation with corrected backtesting.py behavior understanding
  - Accurate position closing mechanics
  - Comprehensive documentation
  - Framework integration
  - Enhanced code legibility and comments

## Disclaimer

This strategy is for educational and research purposes. Past performance does not guarantee future results. The strategy involves significant risks including gap risk and transaction costs. Always perform thorough backtesting and risk assessment before deploying with real capital.

## Support

- **Issues**: Report bugs or questions via GitHub issues
- **Documentation**: Refer to inline code documentation for implementation details
- **Research**: See original source links for theoretical background