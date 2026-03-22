# SaquaremaBoys Strategy Collection

A collection of classic Brazilian trading strategies adapted for the backtesting.py framework, featuring three proven setups focused on trend-following and breakout techniques.

## Strategies Overview

### 1. HiLo3DailyStrategy - Hi/Lo(3) Breakout System

**Type**: Breakout / Trend-following
**Timeframe**: Daily
**Direction**: Long only

#### Strategy Description
Implements a breakout system based on the Hi/Lo(3) indicator - tracking 3-period highs and lows. The strategy enters on breakouts above the 3-candle high and uses adaptive trailing stops based on volatility (ATR or standard deviation).

#### Entry Rules
- Buy when close > Hi(3) (maximum of previous 3 candles, calculated without look-ahead bias)
- Position opened at close of breakout candle

#### Exit Rules
1. **Reversal Exit**: Close < Lo(3) (minimum of previous 3 candles)
2. **Initial Stop**: 10% below entry price
3. **Profit Protection**: After 1+ days and >1.5% profit, raises stop to +0.5% above entry
4. **Trailing Stop**: Volatility-based trailing using ATR or daily standard deviation
   - Only tightens, never widens
   - Optional: only trails when in profit

#### Key Parameters
```python
method = 'ATR'                    # 'ATR' or 'STD' (standard deviation)
atr_period = 14                   # ATR calculation period
atr_mult = 2.0                    # ATR multiplier for stop distance
vol_window = 20                   # Window for standard deviation
vol_mult = 2.0                    # Volatility multiplier for stop
only_trail_in_profit = True       # Only trail when trade is profitable
```

#### Best Use Cases
- Trending markets with clear directional moves
- Liquid stocks with consistent volatility patterns
- Daily timeframe swing trading

---

### 2. ShadowLineStrategy - Larry Williams' Shadow Line (Setup 35)

**Type**: Moving average crossover
**Timeframe**: Any (optimized for daily)
**Direction**: Long only

#### Strategy Description
Classic Larry Williams setup using EMA(10) crossovers with a displaced version of itself. The "shadow" is created by shifting EMA(10) by 1 period, creating a responsive trend-following signal.

#### Entry Rules
- Buy when EMA(10) crosses above EMA(10) shifted by 1 period
- Stop loss set at the low of the signal candle

#### Exit Rules
- Close position when EMA(10) crosses below EMA(10) shifted
- Hard stop at signal candle low

#### Key Parameters
```python
# Uses fixed 10-period EMA
# 1-period displacement for shadow line
```

#### Best Use Cases
- Smooth trending markets
- Filtering whipsaws in choppy conditions
- Quick entries on momentum shifts

---

### 3. TwoMAsAboveStrategy - Dual Moving Average (Setup 34)

**Type**: Moving average trend filter
**Timeframe**: Any (optimized for daily)
**Direction**: Long only

#### Strategy Description
Simple yet effective trend-following strategy requiring price to be above both SMA(10) and SMA(20) for entry, with exit when price crosses below both averages.

#### Entry Rules
- Buy when close > SMA(10) AND close > SMA(20)
- Confirms uptrend alignment

#### Exit Rules
- Exit when:
  1. Close < SMA(20), AND
  2. Close crosses below SMA(10) (previous close >= SMA(10), current close < SMA(10))

#### Key Parameters
```python
# Uses fixed SMA(10) and SMA(20)
```

#### Best Use Cases
- Strong trending markets
- Filtering sideways price action
- Conservative trend following

---

## Installation & Usage

### Basic Backtest with Connors CLI

```bash
# Example: HiLo3DailyStrategy
python -m connors.cli.backtest \
  --external-strategy /path/to/SaquaremaBoys/hi_lo_strategy.py \
  --strategy HiLo3DailyStrategy \
  --tickers PETR4.SA \
  --config brazil \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31

# Example: ShadowLineStrategy
python -m connors.cli.backtest \
  --external-strategy /path/to/SaquaremaBoys/shadow_line.py \
  --strategy ShadowLineStrategy \
  --tickers VALE3.SA \
  --config brazil \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31

# Example: TwoMAsAboveStrategy
python -m connors.cli.backtest \
  --external-strategy /path/to/SaquaremaBoys/two_mas_above.py \
  --strategy TwoMAsAboveStrategy \
  --tickers BBAS3.SA \
  --config brazil \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31
```

### Parameter Customization

```bash
# HiLo3DailyStrategy with custom volatility settings
python -m connors.cli.backtest \
  --external-strategy /path/to/SaquaremaBoys/hi_lo_strategy.py \
  --strategy HiLo3DailyStrategy \
  --strategy-params "method:STD;vol_window:30;vol_mult:1.5" \
  --tickers PETR4.SA \
  --config brazil \
  --datasource yfinance
```

### Direct backtesting.py Usage

```python
from backtesting import Backtest
from SaquaremaBoys.hi_lo_strategy import HiLo3DailyStrategy
import yfinance as yf

# Load Brazilian stock data
data = yf.download("PETR4.SA", start="2023-01-01", end="2023-12-31")
data.columns = data.columns.droplevel(1)

# Run backtest
bt = Backtest(data, HiLo3DailyStrategy, cash=10000, commission=.002)
stats = bt.run()
print(stats)
bt.plot()
```

## Dependencies

All strategies require:
- `backtesting`: Core backtesting framework
- `pandas`: Data manipulation
- `numpy`: Numerical calculations
- `talib`: Technical analysis functions (EMA, SMA, ATR, STDDEV)

## Strategy Characteristics Comparison

| Strategy | Complexity | Trade Frequency | Risk Management | Best Market |
|----------|-----------|-----------------|-----------------|-------------|
| HiLo3Daily | Medium-High | Medium | Advanced (trailing stops) | Trending |
| ShadowLine | Low-Medium | Medium-High | Basic (fixed stop) | Trending |
| TwoMAsAbove | Low | Low-Medium | None (MA-based exits) | Strong trends |

## Performance Optimization Tips

### HiLo3DailyStrategy
- Optimize `atr_mult` and `vol_mult` for different volatility regimes
- Test `only_trail_in_profit` parameter - may reduce whipsaws
- Consider enabling/disabling profit protection based on market conditions

### ShadowLineStrategy
- Simple design allows for easy multi-timeframe testing
- Stop at signal candle low provides clear risk definition
- Consider adding position sizing based on stop distance

### TwoMAsAboveStrategy
- Test different MA periods for various instruments
- Consider adding a third MA for stronger trend confirmation
- May benefit from volume filter

## Risk Warnings

- **ShadowLine & TwoMAs**: No hard stops - can result in large drawdowns
- **HiLo3Daily**: Complex trailing logic - backtest thoroughly before live use
- All strategies are long-only - perform poorly in bear markets
- Designed for Brazilian market characteristics (B3) - test before using on other markets

## Development Notes

All strategies include utility functions for Portuguese-language statistics output (`renomear_chaves_stats`), making them suitable for Brazilian trading platforms and reporting.

## Attribution

These strategies are classic Brazilian trading setups:
- **Setup 34 & 35**: Traditional Brazilian technical analysis patterns
- **Hi/Lo(3)**: Adapted from Brazilian day trading methodologies

Converted to Python/backtesting.py format for the Connors Trading framework.

## License

See main repository LICENSE file.
