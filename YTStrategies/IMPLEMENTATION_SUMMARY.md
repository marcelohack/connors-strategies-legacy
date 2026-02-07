# YouTube Strategies Implementation Summary

## Overview

Successfully implemented three mechanical trading strategies from YouTube/social media concepts, adapted for the backtesting.py framework.

## Files Created

### Strategy 1: Previous Day High and Low Break and Retest
- **JSON:** `previous_day_high_low_break_retest.json` (2.6 KB)
- **Python:** `previous_day_high_low_break_retest.py` (7.0 KB)
- **Class:** `PreviousDayHighLowBreakRetest`

### Strategy 2: Opening Range Break and Retest
- **JSON:** `opening_range_break_retest.json` (2.1 KB)
- **Python:** `opening_range_break_retest.py` (7.1 KB)
- **Class:** `OpeningRangeBreakRetest`

### Strategy 3: Order Block Break and Retest
- **JSON:** `order_block_break_retest.json` (2.4 KB)
- **Python:** `order_block_break_retest.py` (12 KB)
- **Class:** `OrderBlockBreakRetest`

### Documentation
- **README.md:** Comprehensive documentation (10 KB)
- **test_strategies.py:** Test script to verify implementations (4 KB)
- **IMPLEMENTATION_SUMMARY.md:** This file

## Implementation Approach

### Core Design Principles

1. **Break and Retest Methodology**: All strategies follow the same pattern:
   - Identify key price levels
   - Detect break through those levels
   - Wait for price to retest the broken level
   - Enter on successful retest with proper risk management

2. **Risk Management**: Consistent across all strategies:
   - Fixed percentage risk per trade (1-2%)
   - Position sizing based on stop loss distance
   - Risk-reward ratios (default 1:2)
   - Integer position sizes (critical for backtesting.py)

3. **Retest Detection**: Implemented using proximity-based logic:
   - Configurable `retest_proximity_pct` parameter
   - Price must be within X% of broken level
   - Price must be on correct side of level

### Strategy-Specific Implementations

#### 1. Previous Day High/Low Break and Retest

**Complexity:** Medium

**Key Implementation Details:**
- Tracks previous day's high/low using date-based segmentation
- Maintains break status across multiple bars
- Retest detection when price returns to within 0.5% of broken level
- Stop loss placed just beyond retest level with small buffer

**Assumptions/Simplifications:**
- Uses calendar days rather than NY session times (9:30 AM - 4:00 PM EST)
- Works on any timeframe by tracking full day's range
- Single position at a time

**Parameters:**
- `risk_per_trade`: 0.02 (2%)
- `reward_risk_ratio`: 2.0
- `retest_proximity_pct`: 0.005 (0.5%)
- `stop_loss_buffer_pct`: 0.002 (0.2%)

#### 2. Opening Range Break and Retest

**Complexity:** Low-Medium

**Key Implementation Details:**
- Establishes opening range from first N bars of each trading day
- Adapts to any timeframe (not strictly 5-minute candles)
- Simple break detection above/below opening range
- Retest detection with tighter proximity (0.3%)

**Assumptions/Simplifications:**
- Opening range defined by first bar(s) of day, not specifically NY open
- `opening_range_bars` parameter allows adaptation to different timeframes
- For 1-minute data, might want 5 bars; for daily data, use 1 bar
- No multi-timeframe confirmation (original strategy uses 5m break + 1m entry)

**Parameters:**
- `risk_per_trade`: 0.01 (1%)
- `reward_risk_ratio`: 2.0
- `opening_range_bars`: 1 (adjustable)
- `retest_proximity_pct`: 0.003 (0.3%)

#### 3. Order Block Break and Retest

**Complexity:** High

**Key Implementation Details:**
- Trend detection using dual moving averages (20/50 SMA) + price structure
- Order block identification:
  - Uptrend: down-close candles with clear lower wicks
  - Downtrend: up-close candles with clear upper wicks
- Wick validation (minimum 30% of body size)
- Order block zone: from wick to body (opposite end)
- Maintains list of up to 5 recent order blocks per type

**Assumptions/Simplifications:**
- Simple trend detection (could be enhanced with more sophisticated methods)
- Wick requirement: 30% of body size (arbitrary but reasonable)
- Only trades most recent order block
- No multi-timeframe trend confirmation
- No volume analysis for confluence

**Parameters:**
- `risk_per_trade`: 0.01 (1%)
- `reward_risk_ratio`: 2.0
- `trend_lookback`: 20 bars
- `swing_lookback`: 10 bars
- `retest_proximity_pct`: 0.005 (0.5%)

## Technical Implementation Details

### Data Handling

All strategies expect standard OHLCV data:
```python
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
```

### Common Patterns

1. **Date Tracking:**
```python
current_bar_date = pd.Timestamp(self.data.index[-1]).date()
if self.current_date != current_bar_date:
    # New day detected
    self.current_date = current_bar_date
```

2. **Retest Detection:**
```python
retest_range = level * self.retest_proximity_pct
if abs(current_price - level) <= retest_range:
    # Retest detected
```

3. **Position Sizing:**
```python
risk_amount = self.equity * self.risk_per_trade
risk = entry_price - stop_loss
position_size = int(round(risk_amount / risk))  # MUST be integer
```

4. **Entry with SL/TP:**
```python
self.buy(size=position_size, sl=stop_loss, tp=take_profit)
```

### Critical Implementation Notes

1. **Integer Position Sizes:** backtesting.py requires integer position sizes or fractions (0-1). Always convert calculated sizes to integers.

2. **self.I() Wrapper:** All indicators should be wrapped with `self.I()` for proper backtesting.py integration.

3. **Date Handling:** Using `pd.Timestamp().date()` for day-based segmentation works across all timeframes.

4. **Single Position:** All strategies enforce single position at a time with `if self.position: return`.

## Challenges and Limitations

### 1. Session Time Filtering

**Challenge:** Original strategies specify NY session times (9:30 AM - 4:00 PM EST)

**Solution:** Adapted to use full calendar days instead of intraday sessions

**Impact:** May include after-hours price action not intended in original strategies

**Future Enhancement:** Add timezone-aware datetime filtering for proper session isolation

### 2. Multi-Timeframe Concepts

**Challenge:** Opening Range strategy originally uses 5m break confirmation + 1m entry

**Solution:** Simplified to single-timeframe implementation

**Impact:** May miss some nuance of original strategy

**Future Enhancement:** Implement MTF analysis using higher timeframe data

### 3. Retest Sensitivity

**Challenge:** What constitutes a "retest" is subjective

**Solution:** Proximity-based detection with configurable parameter

**Impact:** May generate false signals if too wide, miss signals if too narrow

**Recommendation:** Optimize `retest_proximity_pct` based on:
- Asset volatility (use ATR)
- Timeframe (lower TF needs tighter proximity)
- Market conditions (trending vs ranging)

### 4. Trend Detection (Order Block Strategy)

**Challenge:** Identifying "clear trending markets" programmatically

**Solution:** Simple MA crossover + price structure

**Impact:** May trade in choppy markets where strategy underperforms

**Future Enhancement:**
- ADX for trend strength
- Higher timeframe trend confirmation
- Volatility filters

### 5. Intraday vs Daily Data

**Challenge:** Strategies designed for intraday data but may be tested on daily

**Solution:** Adaptive implementations that work on any timeframe

**Impact:** Performance may vary significantly by timeframe

**Recommendation:** Test each strategy on its optimal timeframe:
- Previous Day High/Low: 15m, 1H, 4H
- Opening Range: 1m, 5m, 15m
- Order Block: Any timeframe with HTF confirmation

## Optimization Recommendations

### Previous Day High/Low Break and Retest

**High Priority:**
1. `retest_proximity_pct`: Test 0.003 to 0.01
2. `reward_risk_ratio`: Test 1.5 to 3.0
3. Session time filtering (if using intraday data)

**Medium Priority:**
4. Volume confirmation on break
5. Multi-day level tracking (2-3 days)
6. Trend filter (only trade with higher timeframe trend)

**Low Priority:**
7. Time-of-day filters
8. Volatility-based proximity adjustment

### Opening Range Break and Retest

**High Priority:**
1. `opening_range_bars`: Test 1, 3, 5, 10 (varies by timeframe)
2. `retest_proximity_pct`: Test 0.002 to 0.005
3. Previous day range filter (only trade if open inside prev day)

**Medium Priority:**
4. Strong opening drive filter (large first candle)
5. Volume analysis on break
6. Time limit (only trade first X hours)

**Low Priority:**
7. Gap detection and handling
8. Confluence with other levels

### Order Block Break and Retest

**High Priority:**
1. `trend_lookback`: Test 10, 20, 30, 50
2. `swing_lookback`: Test 5, 10, 15, 20
3. Trend strength filter (only trade in strong trends)

**Medium Priority:**
4. Wick size requirements (currently 30% of body)
5. Order block age filtering (only use recent OBs)
6. Multiple confluence (OB + other level)

**Low Priority:**
7. Volume analysis at order block
8. Multi-timeframe OB alignment
9. Refined trend detection (ADX, etc.)

## Performance Expectations

### Trade Frequency

- **Previous Day High/Low:** Low-Medium (depends on volatility, expect 2-5 trades per month on daily data)
- **Opening Range:** Medium-High (intraday strategy, may generate daily signals on lower timeframes)
- **Order Block:** Low-Medium (requires clear trends, may have dry spells in ranging markets)

### Win Rate

- Expected: 40-60% due to fixed 1:2 risk-reward
- Higher win rates with proper confluence and filtering
- Lower win rates in choppy/ranging markets

### Risk-Adjusted Returns

- Target Sharpe Ratio: >1.0 in trending markets
- Maximum Drawdown: Expect 10-25% depending on risk per trade
- Profit Factor: Target >1.5 with proper filtering

### Market Conditions

**Best Performance:**
- Clear trending markets
- High liquidity (tight spreads)
- Strong directional moves
- Volatility expansion phases

**Worst Performance:**
- Ranging/consolidating markets
- Low volatility
- Choppy price action
- Mean-reverting conditions

## Testing Recommendations

### Backtesting Protocol

1. **Timeframe Selection:**
   - Previous Day High/Low: 15m, 1H, 4H, Daily
   - Opening Range: 1m, 5m, 15m
   - Order Block: 15m, 1H, 4H (with HTF trend)

2. **Data Requirements:**
   - Minimum: 1 year (252 trading days)
   - Recommended: 3-5 years for robustness
   - Include different market regimes (bull, bear, sideways)

3. **Asset Selection:**
   - High liquidity (avoid low-volume stocks)
   - Clear price action (avoid penny stocks)
   - Sufficient volatility for signals
   - Test on multiple uncorrelated assets

4. **Parameter Optimization:**
   - Use walk-forward analysis
   - Avoid overfitting (limit optimization parameters)
   - Test robustness across different periods
   - Validate on out-of-sample data

5. **Risk Management:**
   - Start with conservative risk (1% per trade)
   - Test different risk-reward ratios
   - Analyze maximum consecutive losses
   - Ensure sufficient capital for drawdowns

### Example Backtest Code

```python
from backtesting import Backtest
from YTStrategies.previous_day_high_low_break_retest import PreviousDayHighLowBreakRetest
import yfinance as yf
import pandas as pd

# Download data
ticker = "AAPL"
data = yf.download(ticker, start="2020-01-01", end="2023-12-31", interval="1h")

# Clean data
data.columns = data.columns.str.strip().str.lower()
data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()])
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Run backtest
bt = Backtest(data, PreviousDayHighLowBreakRetest, cash=1_000_000, commission=0.002)

# Basic run
stats = bt.run()
print(stats)

# Parameter optimization
stats = bt.optimize(
    risk_per_trade=[0.01, 0.02],
    reward_risk_ratio=[1.5, 2.0, 2.5, 3.0],
    retest_proximity_pct=[0.003, 0.005, 0.007, 0.01],
    maximize='Sharpe Ratio',
    constraint=lambda p: p.risk_per_trade <= 0.02
)
print(stats)
print(stats._strategy)
```

## Integration with Connors Framework

All strategies are designed to integrate with the Connors Trading framework:

### Registry Integration

To add registry support, modify each strategy file:

```python
from connors_trading.core.registry import registry

@registry.register_strategy("PreviousDayHighLowBreakRetest")
class PreviousDayHighLowBreakRetest(Strategy):
    # ... strategy code ...
```

### CLI Usage

```bash
# Basic backtest
PYTHONPATH="/Users/mhack/Projects/connors/strategies:$PYTHONPATH" \
python -m connors.cli.backtest \
  --external-strategy /Users/mhack/Projects/connors/strategies/YTStrategies/previous_day_high_low_break_retest.py \
  --strategy PreviousDayHighLowBreakRetest \
  --tickers AAPL,TSLA,NVDA \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31

# With parameter overrides
PYTHONPATH="/Users/mhack/Projects/connors/strategies:$PYTHONPATH" \
python -m connors.cli.backtest \
  --external-strategy /Users/mhack/Projects/connors/strategies/YTStrategies/opening_range_break_retest.py \
  --strategy OpeningRangeBreakRetest \
  --strategy-params "risk_per_trade:0.01;reward_risk_ratio:3.0;opening_range_bars:5" \
  --tickers SPY \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31
```

## Future Enhancements

### High Priority

1. **Multi-Timeframe Analysis:**
   - Confirm trades with higher timeframe trends
   - Use HTF structure for better entries
   - Filter signals based on HTF context

2. **Session Time Filtering:**
   - Implement proper timezone handling
   - Filter for NY session (9:30 AM - 4:00 PM EST)
   - Add Asian/London session filters

3. **Volume Confirmation:**
   - Validate breaks with volume spikes
   - Require above-average volume on breakouts
   - Use volume profile for better level identification

### Medium Priority

4. **Adaptive Parameters:**
   - Use ATR for dynamic proximity calculation
   - Volatility-based position sizing
   - Market regime detection (trending vs ranging)

5. **Confluence Filters:**
   - Combine multiple signals for higher probability
   - Add support/resistance confluence
   - Fibonacci level alignment

6. **Advanced Risk Management:**
   - Trailing stops based on ATR
   - Partial profit taking
   - Scale in/out logic

### Low Priority

7. **Machine Learning Integration:**
   - Pattern recognition for retests
   - Trade quality scoring
   - Parameter optimization using ML

8. **Live Trading Features:**
   - Real-time signal generation
   - Alert system
   - Trade journal integration

## Conclusion

Successfully implemented three mechanical trading strategies with:
- Clean, maintainable code following project conventions
- Comprehensive documentation (JSON + README)
- Proper risk management and position sizing
- Adaptive implementations that work across timeframes
- Clear entry/exit logic with Moon Dev themed logging

All strategies are production-ready for backtesting and can be easily enhanced with the suggested optimizations. The implementations balance simplicity (for understanding and maintenance) with sophistication (proper risk management and adaptive logic).

## Files Summary

| File | Size | Purpose |
|------|------|---------|
| previous_day_high_low_break_retest.json | 2.6 KB | Strategy definition and documentation |
| previous_day_high_low_break_retest.py | 7.0 KB | Strategy implementation |
| opening_range_break_retest.json | 2.1 KB | Strategy definition and documentation |
| opening_range_break_retest.py | 7.1 KB | Strategy implementation |
| order_block_break_retest.json | 2.4 KB | Strategy definition and documentation |
| order_block_break_retest.py | 12 KB | Strategy implementation |
| README.md | 10 KB | Comprehensive usage documentation |
| test_strategies.py | 4 KB | Automated testing script |
| IMPLEMENTATION_SUMMARY.md | This file | Implementation details and recommendations |

**Total:** 9 files, ~45 KB of code and documentation
