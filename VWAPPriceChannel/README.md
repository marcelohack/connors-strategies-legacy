# VWAP Price Channel Strategy

A Python backtesting.py implementation of the Pine Script "VWAP Price Channel" indicator, converted into a systematic trading strategy for the connors framework.

**Original Source**: [VWAP Price Channel](https://www.tradingview.com/v/Psnjpa2Y/)
**Indicator Author**: SamRecio
**Conversion**: Pine Script to Python backtesting.py implementation

## Overview

The VWAP Price Channel Strategy creates dynamic price channels using Volume Weighted Average Price (VWAP) calculations anchored to highest and lowest price levels over a specified lookback period. The strategy generates trading signals based on price breakouts from these adaptive channels.

## Strategy Logic

### Core Mechanism
- **Channel Construction**: Creates upper and lower channels based on VWAP calculations
- **VWAP Anchoring**: Resets VWAP calculation when new highs/lows are detected
- **Dynamic Adjustment**: Channels adapt based on VWAP changes and price action
- **Trend Detection**: Identifies bullish/bearish bias based on new extreme detection

### Entry Conditions
- **Long Entry**: Price breaks above upper channel with bullish trend confirmation
- **Short Entry**: Price breaks below lower channel with bearish trend confirmation
- **Breakout Threshold**: Configurable minimum percentage breakout required

### Exit Conditions
- **Profit Target**: Configurable percentage gain target
- **Stop Loss**: Configurable percentage loss limit
- **Channel Exit**: Exit when price returns to middle channel
- **Time Exit**: Maximum holding period limit

## Parameters

### Core Parameters
- `length` (default: 20): Lookback period for highest/lowest calculation
- `channel_breakout_threshold` (default: 0.001): Minimum breakout percentage (0.1%)
- `use_trend_filter` (default: True): Only trade in direction of detected trend

### Risk Management
- `stop_loss_pct` (default: 2.0): Stop loss percentage
- `profit_target_pct` (default: 4.0): Profit target percentage
- `max_holding_bars` (default: 50): Maximum holding period in bars

### Position Sizing
- `position_size` (default: 1.0): Position size multiplier

## Pine Script Conversion Details

### Original Pine Script Components Converted

1. **VWAP Calculation**:
   - Pine Script: `ta.vwap(high, new_high)` and `ta.vwap(low, new_low)`
   - Python: Custom VWAP calculation with volume weighting and reset conditions

2. **Highest/Lowest Detection**:
   - Pine Script: `ta.highest(len)` and `ta.lowest(len)`
   - Python: `np.max()` and `np.min()` on rolling windows

3. **Channel Construction**:
   - Pine Script: Complex conditional logic for upper/lower channel updates
   - Python: Translated conditional logic with state tracking

4. **Trend Direction**:
   - Pine Script: `dir` and `dir2` variables for trend tracking
   - Python: `trend_direction` and `persistent_trend` variables

### Key Adaptations for Backtesting

- **State Management**: Added proper state tracking for VWAP values and channels
- **Signal Generation**: Converted visual indicator into actionable buy/sell signals
- **Risk Management**: Added comprehensive exit conditions beyond original indicator
- **Volume Handling**: Graceful handling of missing volume data with fallback values

## Usage Examples

### Basic Usage
```python
from backtesting import Backtest
from vwap_price_channel import VWAPPriceChannelStrategy
import yfinance as yf

# Load data
data = yf.download("AAPL", start="2020-01-01", end="2023-01-01")

# Run backtest
bt = Backtest(data, VWAPPriceChannelStrategy)
result = bt.run()
print(result)
```

### Custom Parameters
```python
# Modify strategy parameters
result = bt.run(
    length=30,                          # Longer lookback period
    stop_loss_pct=1.5,                 # Tighter stop loss
    profit_target_pct=6.0,             # Higher profit target
    channel_breakout_threshold=0.005,   # Larger breakout threshold
    use_trend_filter=False              # Disable trend filter
)
```

### Integration with Connors CLI
```bash
# Run backtest using connors CLI
python -m connors.cli.backtest \
    --external-strategy ~/.connors/strategies/VWAPPriceChannel/vwap_price_channel.py \
    --strategy VWAPPriceChannel \
    --tickers AAPL \
    --config america \
    --datasource yfinance \
    --start 2020-01-01 \
    --end 2023-01-01
```

## Performance Characteristics

### Strengths
- **Adaptive Channels**: Dynamically adjusts to market volatility
- **Volume Integration**: Uses volume information for more accurate price levels
- **Trend Awareness**: Can filter trades based on trend direction
- **Configurable Risk**: Flexible risk management parameters

### Considerations
- **Complexity**: More complex than simple moving average strategies
- **Parameter Sensitivity**: Performance may be sensitive to length parameter
- **Volume Dependency**: Best performance requires reliable volume data
- **Market Conditions**: May perform differently in trending vs ranging markets

## Strategy Registration

The strategy is automatically registered with the connors framework using:
```python
@registry.register_strategy("VWAPPriceChannel")
```

This allows discovery and execution through the CLI and framework tools.

## Technical Implementation

### Dependencies
- `pandas`: Data manipulation
- `numpy`: Numerical calculations
- `talib`: Technical analysis functions
- `backtesting`: Backtesting framework
- `connors.core.registry`: Strategy registration

### Code Structure
- **Initialization**: Sets up tracking variables and indicators
- **VWAP Calculation**: Implements volume-weighted average price with resets
- **Channel Updates**: Maintains dynamic upper/lower channel boundaries
- **Signal Generation**: Produces buy/sell signals based on breakouts
- **Risk Management**: Handles exits based on various conditions

## Future Enhancements

Potential improvements and variations:
- **Multi-Timeframe**: Support for different timeframe channel calculations
- **Volatility Adjustment**: Dynamic channel width based on volatility
- **Volume Profile**: Enhanced volume analysis for better VWAP anchoring
- **Machine Learning**: ML-based signal filtering or parameter optimization
- **Alternative Exits**: Additional exit conditions based on momentum or volatility

## References

- Original Pine Script: "VWAP Price Channel" indicator
- Larry Connors: RSI and mean reversion concepts
- VWAP Theory: Volume-weighted average price analysis
- Backtesting.py: Python backtesting framework documentation