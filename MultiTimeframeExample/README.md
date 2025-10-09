# Multi-Timeframe External Strategy Example

This directory contains a complete example of how to create external multi-timeframe strategies for the Connors backtesting framework.

## Overview

Multi-timeframe strategies analyze data across multiple time periods to make more informed trading decisions. This approach helps:

- **Reduce false signals** by confirming trends across timeframes
- **Improve risk management** through better market context
- **Increase win rates** by aligning with dominant trends
- **Provide better entry/exit timing** using shorter timeframes

## Example Strategy: MultiTF_Momentum

The included `multi_tf_momentum.py` demonstrates a complete multi-timeframe momentum strategy:

- **Weekly (1wk)**: Long-term trend filter using 50-period SMA
- **Daily (1d)**: Momentum confirmation using 14-period RSI
- **Hourly (1h)**: Entry/exit timing using 20/10-period SMAs

### Strategy Rules

**Entry Conditions (ALL must be true):**
1. Weekly trend: Current price > 50-week SMA
2. Daily momentum: RSI(14) > 50
3. Hourly timing: Current price > 20-hour SMA

**Exit Conditions:**
- Current price < 10-hour SMA

## How to Create Your Own Multi-Timeframe Strategy

### Step 1: Basic Structure

```python
from connors.core.registry import registry
from connors.strategies.multitimeframe.base import MultiTimeframeStrategy
import talib
import pandas as pd

@registry.register_strategy("YourStrategyName")
class YourMultiTimeframeStrategy(MultiTimeframeStrategy):
    # Define timeframes (required)
    timeframes = ['1wk', '1d', '1h']  # weekly, daily, hourly

    # Define primary timeframe (required)
    primary_timeframe = '1h'  # trades execute on this timeframe

    def __init__(self, broker=None, data=None, params=None):
        super().__init__(broker, data, params)
```

### Step 2: Configure Timeframes

The `timeframes` list defines which time periods your strategy analyzes:

```python
# Common timeframe combinations:
timeframes = ['1wk', '1d']          # Weekly trend + daily signals
timeframes = ['1d', '4h', '1h']     # Daily, 4-hour, hourly analysis
timeframes = ['1wk', '1d', '1h']    # Full spectrum analysis
```

**Available timeframes:**
- `1m`, `5m`, `15m`, `30m` - Minutes
- `1h`, `4h` - Hours
- `1d` - Daily
- `1wk` - Weekly
- `1mo` - Monthly

### Step 3: Set Primary Timeframe

The `primary_timeframe` determines trade execution timing:

```python
primary_timeframe = '1h'  # Execute trades on hourly bars
```

**Best practices:**
- Use the **shortest timeframe** for better entry/exit precision
- Must be included in the `timeframes` list
- Shorter timeframes = more trade opportunities
- Longer timeframes = fewer but potentially higher quality trades

### Step 4: Initialize Indicators

```python
def _init_indicators(self):
    """Set up indicators for each timeframe"""

    # Weekly indicators
    weekly_data = self.get_timeframe_data('1wk')
    self.weekly_sma = self.I(
        lambda x: talib.SMA(x, timeperiod=50),
        weekly_data.Close,
        name='Weekly_SMA_50'
    )

    # Daily indicators
    daily_data = self.get_timeframe_data('1d')
    self.daily_rsi = self.I(
        lambda x: talib.RSI(x, timeperiod=14),
        daily_data.Close,
        name='Daily_RSI_14'
    )
```

### Step 5: Implement Trading Logic

```python
def next(self):
    """Execute trading logic on each primary timeframe bar"""

    current_price = self.data.Close[-1]

    # Check longer timeframe conditions first
    weekly_ok = current_price > self.weekly_sma[-1]
    daily_ok = self.daily_rsi[-1] > 50

    # Entry logic
    if not self.position and weekly_ok and daily_ok:
        self.buy(size=1)

    # Exit logic
    elif self.position and current_price < self.hourly_exit_sma[-1]:
        self.position.close()
```

## Running External Multi-Timeframe Strategies

### Command Line Interface

```bash
# Basic usage
python -m connors.cli.backtest \
  --external-strategy ~/.connors/strategies/MultiTimeframeExample/multi_tf_momentum.py \
  --strategy MultiTF_Momentum \
  --tickers AAPL \
  --config america \
  --datasource yfinance \
  --timeframes 1wk,1d,1h \
  --primary-timeframe 1h

# With custom parameters
python -m connors.cli.backtest \
  --external-strategy ~/.connors/strategies/MultiTimeframeExample/multi_tf_momentum.py \
  --strategy MultiTF_Momentum \
  --strategy-params "weekly_sma_period:30;daily_rsi_period:21" \
  --tickers AAPL \
  --config america \
  --datasource yfinance \
  --timeframes 1wk,1d,1h \
  --primary-timeframe 1h \
  --start 2024-01-01 \
  --end 2024-06-01 \
  --save-results true \
  --save-plot true

# Multiple tickers
python -m connors.cli.backtest \
  --external-strategy ~/.connors/strategies/MultiTimeframeExample/multi_tf_momentum.py \
  --strategy MultiTF_Momentum \
  --tickers "AAPL,MSFT,GOOGL" \
  --config america \
  --datasource yfinance \
  --timeframes 1wk,1d,1h \
  --primary-timeframe 1h
```

### Streamlit Interface

1. Launch the Streamlit interface:
   ```bash
   python -m connors.ui.streamlit_app
   ```

2. Navigate to the **Backtest** section

3. Configure the strategy:
   - **Strategy Type**: Select "External Strategy"
   - **External Strategy File**: Browse and select your `.py` file
   - **Strategy Name**: Enter your registered strategy name
   - **Multi-timeframe Analysis**: Check the box
   - **Timeframes**: Select the timeframes (e.g., 1wk, 1d, 1h)
   - **Primary Timeframe**: Select the execution timeframe

4. Set other parameters (tickers, dates, etc.) and run the backtest

## Advanced Features

### Parameter Overrides

You can override strategy parameters at runtime:

```python
class YourStrategy(MultiTimeframeStrategy):
    # Default parameters
    sma_period = 20
    rsi_threshold = 30
```

Override via CLI:
```bash
--strategy-params "sma_period:50;rsi_threshold:25"
```

### Strategy Metadata

Provide rich information about your strategy:

```python
def get_strategy_metadata(self):
    metadata = super().get_strategy_metadata()
    metadata.update({
        "strategy_type": "Multi-Timeframe Trend Following",
        "description": "Combines weekly trend with daily signals",
        "complexity": "Advanced",
        "trade_direction": "Long/Short",
        "risk_level": "Medium"
    })
    return metadata
```

### Error Handling

Always check for sufficient data:

```python
def next(self):
    # Check if indicators have sufficient data
    if len(self.weekly_sma) == 0 or pd.isna(self.weekly_sma[-1]):
        return  # Skip this bar

    if len(self.daily_rsi) < 2:  # Need at least 2 values
        return

    # Your trading logic here...
```

## Best Practices

### 1. Timeframe Selection
- **Start simple**: Begin with 2-3 timeframes
- **Logical hierarchy**: Use timeframes that are multiples (e.g., 1h, 4h, 1d)
- **Consider data availability**: Some timeframes may have limited historical data

### 2. Data Alignment
- The framework automatically aligns data across timeframes
- Missing data is forward-filled from available timeframes
- Always check for NaN values in your indicators

### 3. Strategy Testing
- Test with different timeframe combinations
- Validate logic across various market conditions
- Use parameter optimization to find optimal settings

### 4. Performance Considerations
- More timeframes = more data = slower backtests
- Start with small date ranges for initial testing
- Use fewer tickers initially to speed up development

## File Structure

Organize your external strategies like this:

```
~/.connors/strategies/
├── YourStrategyName/
│   ├── your_strategy.py     # Main strategy file
│   ├── README.md           # Strategy documentation
│   └── examples/           # Usage examples (optional)
└── MultiTimeframeExample/  # This example
    ├── multi_tf_momentum.py
    └── README.md
```

## Troubleshooting

### Common Issues

1. **"Strategy not found"**: Check strategy registration name matches CLI parameter
2. **"Timeframe data not available"**: Verify timeframes are supported by data source
3. **"Insufficient data"**: Check date range provides enough data for indicators
4. **"Import errors"**: Ensure all required packages are installed

### Testing Your Strategy

Test locally before running backtests:

```python
if __name__ == "__main__":
    # Test strategy creation
    strategy = YourStrategy()
    print(strategy.get_strategy_metadata())

    # Test timeframe configuration
    print(f"Timeframes: {strategy.timeframes}")
    print(f"Primary: {strategy.primary_timeframe}")
```

## Examples and Templates

This directory serves as a template for creating your own multi-timeframe strategies. Copy and modify the example to create your own strategies.

For more examples and advanced techniques, check the built-in strategies in the main codebase under `connors/strategies/multitimeframe/`.

## Support

For questions or issues with multi-timeframe strategies:

1. Check the main documentation
2. Review the unit tests for usage examples
3. Examine built-in strategies for patterns
4. Test with simple configurations first

Happy backtesting! 🚀