# Quick Start Guide - YT Strategies

## Three Strategies at a Glance

### 1️⃣ Previous Day High/Low Break & Retest
**Best for:** Daily/4H trending markets
**Risk:** 2% per trade
**R:R:** 1:2
**Concept:** Trade breakouts of previous day's high/low levels

```python
from YTStrategies.previous_day_high_low_break_retest import PreviousDayHighLowBreakRetest
```

### 2️⃣ Opening Range Break & Retest
**Best for:** Intraday (1m/5m/15m)
**Risk:** 1% per trade
**R:R:** 1:2
**Concept:** Trade breakouts of first candle(s) of the day

```python
from YTStrategies.opening_range_break_retest import OpeningRangeBreakRetest
```

### 3️⃣ Order Block Break & Retest
**Best for:** Trending markets (any timeframe)
**Risk:** 1% per trade
**R:R:** 1:2
**Concept:** Trade institutional order blocks in trends

```python
from YTStrategies.order_block_break_retest import OrderBlockBreakRetest
```

## Quick Test (Copy & Paste)

```python
from backtesting import Backtest
from YTStrategies.previous_day_high_low_break_retest import PreviousDayHighLowBreakRetest
import yfinance as yf

# Get data
data = yf.download("AAPL", start="2023-01-01", end="2023-12-31", interval="1d")
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Run backtest
bt = Backtest(data, PreviousDayHighLowBreakRetest, cash=1_000_000, commission=0.002)
stats = bt.run()
print(stats)
```

## Key Parameters to Optimize

### All Strategies
- `risk_per_trade`: 0.01 to 0.02 (1-2%)
- `reward_risk_ratio`: 1.5 to 3.0

### Previous Day High/Low
- `retest_proximity_pct`: 0.003 to 0.01

### Opening Range
- `opening_range_bars`: 1, 3, 5, 10 (depends on timeframe)
- `retest_proximity_pct`: 0.002 to 0.005

### Order Block
- `trend_lookback`: 10, 20, 30, 50
- `swing_lookback`: 5, 10, 15, 20

## Common Issues & Fixes

**Issue:** "size must be positive"
**Fix:** Position size is too small, increase risk_per_trade or use higher cash

**Issue:** No trades generated
**Fix:** Check retest_proximity_pct (may be too tight), check data quality

**Issue:** Too many trades
**Fix:** Increase retest_proximity_pct, add filters

## File Locations

All files in: `/Users/mhack/Projects/connors/strategies/YTStrategies/`

- `*.py` - Strategy implementations
- `*.json` - Strategy definitions
- `README.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- `test_strategies.py` - Test all strategies
- `QUICK_START.md` - This file

## Next Steps

1. Read `README.md` for detailed usage
2. Review `IMPLEMENTATION_SUMMARY.md` for technical details
3. Test strategies with your data
4. Optimize parameters for your markets
5. Combine with other indicators for confluence

## Strategy Selection Guide

**Use Previous Day H/L when:**
- Trading daily or 4H charts
- Clear overnight gaps
- Strong directional moves

**Use Opening Range when:**
- Intraday trading
- Strong opening drives
- Price opens inside prev day range

**Use Order Block when:**
- Clear trending market
- Looking for pullback entries
- Higher timeframe confirms trend

## Remember

- Test before live trading
- Start with small risk (1%)
- Verify data quality
- Track results
- Adapt to market conditions
