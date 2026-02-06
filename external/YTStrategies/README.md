# YouTube Trading Strategies

This folder contains three mechanical trading strategies adapted from popular YouTube/social media trading concepts, implemented in Python using the backtesting.py framework.

## Overview

All strategies follow the "break and retest" methodology, which is a core concept in technical analysis:
1. Identify key price levels
2. Wait for price to break through these levels
3. Enter on the retest of the broken level
4. Use proper risk management with fixed risk-reward ratios

## Strategies

### 1. Previous Day High and Low Break and Retest

**File:** `previous_day_high_low_break_retest.py`

**Concept:** Trades the break and retest of the previous trading day's high and low levels, which represent significant volume clusters from the main trading session.

**Key Features:**
- Tracks previous day's high and low levels
- Detects break above/below these levels
- Enters on retest for continuation trades
- 2% risk per trade, 1:2 risk-reward ratio (default)

**Parameters:**
- `risk_per_trade`: Risk percentage per trade (default: 0.02)
- `reward_risk_ratio`: Risk-reward ratio (default: 2.0)
- `retest_proximity_pct`: Proximity to consider a retest (default: 0.005)
- `stop_loss_buffer_pct`: Buffer for stop loss placement (default: 0.002)

**Best For:**
- Trending markets
- Stocks with clear directional moves
- Higher timeframes (4H, Daily)

### 2. Opening Range Break and Retest

**File:** `opening_range_break_retest.py`

**Concept:** A mechanical strategy that trades the break and retest of the opening range (first candle(s) of the trading day).

**Key Features:**
- Establishes opening range from first bar(s) of each day
- Detects break above/below opening range
- Enters on retest of broken level
- 1% risk per trade, 1:2 risk-reward ratio (default)

**Parameters:**
- `risk_per_trade`: Risk percentage per trade (default: 0.01)
- `reward_risk_ratio`: Risk-reward ratio (default: 2.0)
- `opening_range_bars`: Number of bars to define opening range (default: 1)
- `retest_proximity_pct`: Proximity to consider a retest (default: 0.003)

**Best For:**
- Intraday trading
- Markets with strong opening moves
- Lower timeframes (1m, 5m, 15m)

**Note:** Adapted for any timeframe by using the first bar(s) of each trading day, rather than strictly requiring 5-minute data.

### 3. Order Block Break and Retest

**File:** `order_block_break_retest.py`

**Concept:** Identifies institutional "order blocks" (specific candle patterns) and trades their break and retest in trending markets.

**Key Features:**
- Identifies trend using moving averages and price structure
- Marks order blocks:
  - Uptrend: down-close candles with clear lower wicks
  - Downtrend: up-close candles with clear upper wicks
- Trades break and retest of order blocks
- 1% risk per trade, 1:2 risk-reward ratio (default)

**Parameters:**
- `risk_per_trade`: Risk percentage per trade (default: 0.01)
- `reward_risk_ratio`: Risk-reward ratio (default: 2.0)
- `trend_lookback`: Bars to identify trend (default: 20)
- `swing_lookback`: Bars to identify swing highs/lows (default: 10)
- `retest_proximity_pct`: Proximity to consider a retest (default: 0.005)

**Best For:**
- Strongly trending markets
- Higher timeframes for trend identification
- Markets with clear institutional activity

**Requirements:**
- Clear trending market (ineffective in ranging/consolidating conditions)
- Higher probability with confluence from other levels

## Common Features

All strategies implement:
- **Risk Management:** Fixed percentage risk per trade with position sizing based on stop loss distance
- **Risk-Reward Ratios:** Configurable target ratios (default 1:2)
- **Integer Position Sizes:** Proper conversion of calculated sizes to integers
- **Moon Dev Themed Logging:** Clear entry/exit signals with pricing information
- **ATR Integration:** For dynamic reference (though not currently used for stops)

## Usage

### Direct Backtesting.py Usage

```python
from backtesting import Backtest
from YTStrategies.previous_day_high_low_break_retest import PreviousDayHighLowBreakRetest
import yfinance as yf
import pandas as pd

# Load data
data = yf.download("AAPL", start="2023-01-01", end="2023-12-31")
data.columns = data.columns.str.strip().str.lower()
data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()])
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Run backtest
bt = Backtest(data, PreviousDayHighLowBreakRetest, cash=1_000_000, commission=0.002)
stats = bt.run()
print(stats)
```

### With Connors CLI (if integrated)

```bash
PYTHONPATH="/Users/mhack/Projects/connors/strategies:$PYTHONPATH" \
python -m connors.cli.backtest \
  --external-strategy /Users/mhack/Projects/connors/strategies/YTStrategies/previous_day_high_low_break_retest.py \
  --strategy PreviousDayHighLowBreakRetest \
  --tickers AAPL \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31
```

### Parameter Override

```python
# Override default parameters
stats = bt.run(
    risk_per_trade=0.01,  # 1% risk instead of default
    reward_risk_ratio=3.0,  # 1:3 risk-reward
    retest_proximity_pct=0.01  # Wider retest zone
)
```

## Implementation Notes

### Data Requirements

All strategies work with standard OHLCV data:
- **Open, High, Low, Close, Volume** columns (capitalized)
- DateTime index
- Any timeframe supported (though strategies have optimal timeframes)

### Timeframe Adaptations

Since these strategies are adapted from intraday concepts:

1. **Previous Day High/Low:** Works on any timeframe by tracking previous calendar day's levels
2. **Opening Range:** Adapted to use first bar(s) of each trading day rather than strictly 5-minute candles
3. **Order Block:** Fully adaptable to any timeframe with trend detection

### Retest Logic

All strategies detect "retests" when:
- Price returns to within a small percentage of the broken level
- Price is on the correct side of the level (above for longs, below for shorts)
- Configurable via `retest_proximity_pct` parameter

### Limitations

1. **Session Time Handling:** NY session times (9:30 AM - 4:00 PM EST) are conceptual. Implementations use daily boundaries rather than intraday session filtering.

2. **Intraday vs Daily Data:** Strategies are adapted for daily data but work best on intraday timeframes (1m, 5m, 15m) where the original concepts were designed.

3. **Trend Detection:** Order Block strategy uses simple trend detection (moving averages + price structure). Could be enhanced with more sophisticated methods.

4. **Single Position:** Strategies only take one position at a time. Multiple order blocks or levels are tracked but only one trade per signal.

5. **Retest Sensitivity:** The `retest_proximity_pct` parameter may need tuning based on:
   - Asset volatility
   - Timeframe
   - Market conditions

## Recommended Optimizations

### Previous Day High/Low
- `retest_proximity_pct`: 0.003 to 0.01 depending on volatility
- `reward_risk_ratio`: 2.0 to 3.0 for trending markets
- `risk_per_trade`: 0.01 to 0.02 based on conviction

### Opening Range
- `opening_range_bars`: 1 to 5 depending on timeframe (more bars for lower timeframes)
- `retest_proximity_pct`: 0.002 to 0.005 for tight entries
- Best tested on 5m or 15m data

### Order Block
- `trend_lookback`: 10 to 50 for different trend sensitivities
- `swing_lookback`: 5 to 20 for different market structures
- Works best with longer lookbacks on higher timeframes
- Consider adding minimum wick size requirements

## Testing Recommendations

1. **Backtest Period:** Use at least 1 year of data to capture different market conditions
2. **Market Conditions:** Test separately in trending vs ranging markets
3. **Timeframe Testing:** Test each strategy on its optimal timeframe(s)
4. **Parameter Sweeps:** Optimize risk-reward ratios and retest proximity settings
5. **Asset Selection:** Test on liquid assets with clear price action (avoid low-volume stocks)

## Performance Considerations

- **Trade Frequency:** Will vary significantly based on market conditions and timeframe
- **Win Rate:** Expected 40-60% due to fixed risk-reward ratios
- **Drawdowns:** Expected during ranging/choppy markets
- **Best Performance:** Trending markets with clear directional moves

## Future Enhancements

Potential improvements:
1. **Multi-timeframe Analysis:** Confirm trades with higher timeframe trends
2. **Volume Confirmation:** Add volume analysis to confirm breaks and retests
3. **Dynamic Stop Loss:** Use ATR-based stops instead of fixed percentages
4. **Confluence Filters:** Combine multiple strategy signals for higher probability trades
5. **Session Filtering:** Add proper timezone handling for NY session times
6. **Adaptive Parameters:** Adjust retest proximity based on recent volatility (ATR)

## JSON Definitions

Each strategy has a corresponding JSON file with complete documentation:
- `previous_day_high_low_break_retest.json`
- `opening_range_break_retest.json`
- `order_block_break_retest.json`

These files contain detailed descriptions, entry/exit rules, risk management, and examples.
