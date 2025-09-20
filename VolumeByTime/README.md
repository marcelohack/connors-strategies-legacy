# Volume by Time Strategy

## Overview

The Volume by Time strategy is converted from LuxAlgo's "Volume by Time" Pine Script indicator. This strategy analyzes volume patterns by time of day and generates trading signals based on volume anomalies compared to historical averages at the same time periods.

## Strategy Logic

### Core Concept
- **Time-Based Volume Analysis**: Tracks volume patterns for each time period (simplified to daily cycles in backtesting)
- **Historical Comparison**: Compares current volume to historical average/median for the same time period
- **Directional Volume**: Distinguishes between bullish (close > open) and bearish (close < open) volume

### Entry Conditions
1. **Volume Spike**: Current volume exceeds historical average by the threshold multiplier (default: 2.0x)
2. **Bullish Volume**: Volume occurs on an up bar (close > open) when `bullish_volume_only = True`
3. **Price Filter**: Price is above moving average when `use_price_filter = True`
4. **Minimum Volume**: Volume exceeds minimum threshold to avoid low-liquidity trades

### Exit Conditions
1. **Profit Target**: Close position when profit target percentage is reached (default: 5%)
2. **Stop Loss**: Close position when stop loss percentage is hit (default: 2%)
3. **Time-Based Exit**: Close position after maximum holding period (default: 10 bars)
4. **Volume Normalization**: Close when volume returns below normal levels (default: 0.8x average)

## Parameters

### Core Parameters
- `analysis_type`: "Average" or "Median" for volume calculations
- `length_days`: Historical lookback period in days (20 days default, 0 = all data)
- `volume_threshold_multiplier`: Volume spike threshold (2.0x default)
- `min_volume_threshold`: Minimum absolute volume required (1000 default)

### Signal Parameters
- `use_bidirectional`: Enable bullish/bearish volume distinction (True)
- `bullish_volume_only`: Only trade on bullish volume bars (True)

### Filter Parameters
- `use_price_filter`: Enable price above moving average filter (True)
- `price_filter_length`: Moving average length for price filter (50 bars)

### Exit Parameters
- `profit_target_pct`: Profit target percentage (5.0%)
- `stop_loss_pct`: Stop loss percentage (2.0%)
- `max_holding_bars`: Maximum holding period in bars (10)
- `volume_exit_threshold`: Volume normalization exit threshold (0.8x)

## Usage Examples

### Basic Usage with Python

```python
import sys
sys.path.insert(0, '/Users/mhack/.connors/strategies/VolumeByTime')
from volume_by_time import VolumeByTimeStrategy

import yfinance as yf
from backtesting import Backtest

# Download data
data = yf.download('AAPL', start='2023-01-01', end='2023-12-31')
data.columns = data.columns.droplevel(1)

# Run backtest
bt = Backtest(data, VolumeByTimeStrategy, cash=10000, commission=.002)
stats = bt.run()
print(stats)
```

### Usage with Connors CLI

```bash
# Set up environment
source setenv.sh

# Add strategy path to Python path and run backtest
PYTHONPATH="/Users/mhack/.connors/strategies:$PYTHONPATH" \\
python -m connors.cli.backtest \\
  --external-strategy /Users/mhack/.connors/strategies/VolumeByTime/volume_by_time.py \\
  --strategy VolumeByTime \\
  --tickers AAPL \\
  --config america \\
  --datasource yfinance \\
  --start 2023-01-01 \\
  --end 2023-12-31 \\
  --cash 10000

# Override strategy parameters
PYTHONPATH="/Users/mhack/.connors/strategies:$PYTHONPATH" \\
python -m connors.cli.backtest \\
  --external-strategy /Users/mhack/.connors/strategies/VolumeByTime/volume_by_time.py \\
  --strategy VolumeByTime \\
  --strategy-params "volume_threshold_multiplier:3.0;profit_target_pct:7.0" \\
  --tickers AAPL \\
  --config america \\
  --datasource yfinance
```

### Parameter Optimization

```python
# Optimize key parameters
bt = Backtest(data, VolumeByTimeStrategy, cash=10000, commission=.002)

stats = bt.optimize(
    volume_threshold_multiplier=range(15, 40, 5),  # 1.5x to 4.0x in 0.5 steps
    profit_target_pct=range(3, 11, 2),             # 3% to 10% in 2% steps
    stop_loss_pct=range(1, 6, 1),                  # 1% to 5% in 1% steps
    maximize='Sharpe Ratio'
)
```

## Strategy Performance Notes

### Strengths
- **Volume-Based Edge**: Exploits volume anomalies that often precede price moves
- **Time-Aware**: Considers historical context for each time period
- **Risk Management**: Multiple exit conditions protect capital
- **Flexible**: Highly configurable parameters for different market conditions

### Considerations
- **Market Dependent**: Performance varies by market volatility and volume patterns
- **Time Simplification**: Daily backtesting simplifies intraday time patterns
- **Parameter Sensitivity**: Requires optimization for specific instruments and timeframes
- **Volume Quality**: Works best with liquid instruments having consistent volume data

### Recommended Use Cases
- **High-Volume Stocks**: Best suited for liquid stocks with consistent volume patterns
- **Trend Following**: Works well in trending markets with clear volume patterns
- **Short-Term Trading**: Designed for short holding periods (1-10 days)
- **Volume Anomaly Detection**: Ideal for capturing volume-driven price moves

## Integration with Connors Framework

The strategy is fully compatible with the connors_trading framework:
- ✅ Registry system integration with `@registry.register_strategy("VolumeByTime")`
- ✅ CLI backtesting support via `--external-strategy` parameter
- ✅ Parameter override system compatible
- ✅ Standard backtesting.py Strategy inheritance
- ✅ TA-Lib integration for indicators

## Files Created

- `/Users/mhack/.connors/strategies/VolumeByTime/volume_by_time.py`: Main strategy implementation
- `/Users/mhack/.connors/strategies/VolumeByTime/README.md`: This documentation file

## Next Steps

1. **Parameter Optimization**: Run optimization on historical data for target instruments
2. **Multi-Timeframe Testing**: Test on different intervals (1h, 4h, 1d, 1w)
3. **Market Comparison**: Compare performance across different markets (US, AU, BR)
4. **Volume Pattern Analysis**: Analyze which volume patterns work best
5. **Integration Testing**: Test with full connors CLI workflow and data sources

The strategy successfully converts the Pine Script indicator logic into a functional backtesting.py strategy while maintaining the core volume analysis principles and adding robust risk management features.