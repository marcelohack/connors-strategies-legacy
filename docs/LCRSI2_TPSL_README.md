# LCRSI2_TPSL Strategy - Take Profit & Stop Loss

Enhanced version of the Larry Connors 2-Period RSI strategy with configurable Take Profit and Stop Loss risk management.

## Overview

LCRSI2_TPSL extends the base LCRSI2 strategy with priority-based exit logic:

1. **Priority 1 (HIGHEST)**: Stop Loss - Exit when loss ≥ `stop_loss_pct`
2. **Priority 2**: Take Profit - Exit when profit ≥ `take_profit_pct`
3. **Priority 3**: Regular Exit - Exit when close ≥ SMA(5)

## Strategy Rules

### Entry
- RSI(2) < `rsi_level` (default: 5)
- Close > SMA(200)

### Exit (Priority Order)
1. **Stop Loss**: Loss ≥ 2% (default) → Immediate exit 🛑
2. **Take Profit**: Profit ≥ 5% (default) → Immediate exit 🎯
3. **Regular Exit**: Close ≥ SMA(5) → Mean reversion complete 🔴

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rsi_length` | 2 | RSI calculation period |
| `rsi_level` | 5 | RSI oversold threshold for entry |
| `short_sma_length` | 5 | Short SMA for regular exit signal |
| `long_sma_length` | 200 | Long SMA for trend filter |
| `take_profit_pct` | 5.0 | Take profit percentage (5% = 5.0) |
| `stop_loss_pct` | 2.0 | Stop loss percentage (2% = 2.0) |

## Usage

### Basic Backtest

```bash
python -m connors.cli.backtest \
  --tickers AAPL \
  --strategy LCRSI2_TPSL \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2024-12-31
```

### With Custom TP/SL

```bash
python -m connors.cli.backtest \
  --tickers AAPL \
  --strategy LCRSI2_TPSL \
  --strategy-params "take_profit_pct:3.0;stop_loss_pct:1.5" \
  --config america \
  --datasource yfinance
```

### With Dataset File

```bash
python -m connors.cli.backtest \
  --tickers ELET3 \
  --strategy LCRSI2_TPSL \
  --dataset_file ~/Downloads/ELET3.json \
  --commission 0.0 \
  --cash 10000000
```

### Optimize Take Profit & Stop Loss

**Using integer ranges (recommended):**
```bash
python -m connors.cli.backtest \
  --tickers AAPL \
  --strategy LCRSI2_TPSL \
  --config america \
  --datasource yfinance \
  --optimize \
  --optimize-params "take_profit_pct:range(2, 11, 1);stop_loss_pct:range(1, 6, 1)"
```

This tests:
- Take Profit: 2%, 3%, 4%, 5%, 6%, 7%, 8%, 9%, 10%
- Stop Loss: 1%, 2%, 3%, 4%, 5%
- **Total: 9 × 5 = 45 combinations**

**Using explicit lists (for decimal values):**
```bash
python -m connors.cli.backtest \
  --tickers AAPL \
  --strategy LCRSI2_TPSL \
  --config america \
  --datasource yfinance \
  --optimize \
  --optimize-params "take_profit_pct:[2,3,4,5,6,7,8,9,10];stop_loss_pct:[1,1.5,2,2.5,3,3.5,4,4.5,5]"
```

This tests:
- Take Profit: 2%, 3%, 4%, 5%, 6%, 7%, 8%, 9%, 10%
- Stop Loss: 1%, 1.5%, 2%, 2.5%, 3%, 3.5%, 4%, 4.5%, 5%
- **Total: 9 × 9 = 81 combinations**

**Note:** Python's `range()` only accepts integers. Use explicit lists `[...]` for decimal step sizes.

## Implementation Notes

### Type Handling (Critical)

This strategy handles `backtesting.py`'s internal `Decimal` types correctly:

```python
# backtesting.py uses Decimal internally
current_close = Decimal(str(self.data.Close[-1]))  # Convert numpy.float64 → Decimal
entry_price = Decimal(str(raw_entry))              # Convert numpy.float64 → Decimal

# Use Decimal('100') for all percentage calculations
pnl_pct = ((current_close - entry_price) / entry_price) * Decimal('100')
```

**Why this matters:**
- `backtesting.py` uses `decimal.Decimal` for all prices internally
- `self.trades[-1].entry_price` returns `numpy.float64`
- Python's `Decimal` cannot do arithmetic with `float` or `numpy.float64`
- Solution: Convert all prices to `Decimal` via `Decimal(str(value))`
- Use `Decimal('100')` instead of `100` to keep everything in Decimal type

**Optimizer Support:**
The strategy automatically converts integer parameters to float:
```python
self.take_profit_pct = float(take_profit_pct)  # Handles optimizer integers
self.stop_loss_pct = float(stop_loss_pct)      # Converts 2 → 2.0
```

### MarketSnapshot Protocol

Uses the same high-performance MarketSnapshot protocol as LCRSI2:
- 4-10x faster than DataFrame-based approaches
- Zero-copy data access
- Type-safe signal generation

## Example Output

```
2025-10-16 20:11:35 | INFO | 🟢 BUY signal - RSI 3.09 < 5 AND Close 37.27 > Long_SMA 33.48
2025-10-16 20:11:35 | INFO | 💰 EXECUTING BUY at 37.27 on 2024-01-08 00:00:00
2025-10-16 20:11:35 | INFO | 🔴 REGULAR EXIT signal - Close 37.83 >= Short_SMA 37.58 (P&L: +1.51%)
2025-10-16 20:11:35 | INFO | 💸 EXECUTING SELL at 37.83 on 2024-01-09 (Entry: 37.27, P&L: +1.51%)
```

## Comparison with LCRSI2

| Feature | LCRSI2 | LCRSI2_TPSL |
|---------|-----------|----------------|
| Entry Logic | ✅ Same | ✅ Same |
| Regular Exit | ✅ Close ≥ SMA(5) | ✅ Close ≥ SMA(5) (Priority 3) |
| Stop Loss | ❌ No | ✅ Yes (Priority 1) |
| Take Profit | ❌ No | ✅ Yes (Priority 2) |
| Risk Management | ❌ None | ✅ Configurable TP/SL |
| Entry Price Tracking | ❌ No | ✅ Yes |

## Performance Tips

1. **Stop Loss < Take Profit**: Keep SL tighter than TP (e.g., SL=2%, TP=5%)
2. **Mean Reversion**: This strategy expects quick reversals, so TP should be modest (3-8%)
3. **Volatility**: Adjust TP/SL based on asset volatility (higher vol = wider stops)
4. **Optimization**: Run grid search to find optimal TP/SL for your asset/timeframe

## Files

- `connors/strategies/lcrsi2_tpsl.py` - Strategy implementation
- `connors/strategies/__init__.py` - Strategy registration
- `connors/strategies/LCRSI2_TPSL_README.md` - This documentation

## See Also

- [LCRSI2 (base strategy)](./lcrsi2.py)
- [Backtest Documentation](../docs/BACKTEST.md)
- [Strategy Registry](../core/registry.py)
