# LCRSI2_ATR Strategy - ATR-Based Dynamic Take Profit & Stop Loss

Enhanced version of the Larry Connors 2-Period RSI strategy with ATR-based dynamic risk management that adapts to market volatility.

## Overview

LCRSI2_ATR extends the base LCRSI2 strategy with volatility-adaptive exit logic using ATR (Average True Range):

1. **Priority 1 (HIGHEST)**: Stop Loss - Exit when price ≤ entry - (ATR × sl_multiplier)
2. **Priority 2**: Take Profit - Exit when price ≥ entry + (ATR × tp_multiplier)
3. **Priority 3**: Regular Exit - Exit when close ≥ SMA(5)

## Key Advantages Over Fixed Percent TP/SL

| Feature | Fixed % (LCRSI2_TPSL) | ATR-Based (LCRSI2_ATR) |
|---------|-------------------------|---------------------------|
| **Adaptability** | ❌ Static levels | ✅ Adapts to volatility |
| **Market Conditions** | ❌ Same in all markets | ✅ Wider stops in volatile markets |
| **Risk Management** | ⚠️ Fixed risk per trade | ✅ Volatility-adjusted risk |
| **Whipsaws** | ⚠️ More in volatile markets | ✅ Fewer due to wider stops |
| **Profit Capture** | ⚠️ May exit too early/late | ✅ Aligned with price swings |

## Strategy Rules

### Entry
- RSI(2) < `rsi_level` (default: 5)
- Close > SMA(200)

### Exit (Priority Order)
1. **Stop Loss**: Price ≤ Entry - (ATR × 1.5) → Immediate exit 🛑
2. **Take Profit**: Price ≥ Entry + (ATR × 2.5) → Immediate exit 🎯
3. **Regular Exit**: Close ≥ SMA(5) → Mean reversion complete 🔴

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `rsi_length` | 2 | RSI calculation period |
| `rsi_level` | 5 | RSI oversold threshold for entry |
| `short_sma_length` | 5 | Short SMA for regular exit signal |
| `long_sma_length` | 200 | Long SMA for trend filter |
| `atr_period` | 14 | ATR calculation period |
| `atr_sl_multiplier` | 1.5 | ATR multiplier for stop loss (1.5x ATR below entry) |
| `atr_tp_multiplier` | 2.5 | ATR multiplier for take profit (2.5x ATR above entry) |

## How ATR-Based TP/SL Works

### ATR (Average True Range)
ATR measures market volatility by calculating the average range of price movement over N periods.

**Example:** If ATR = $2.00 and entry price = $100.00:
- **Stop Loss** (1.5x multiplier): $100.00 - ($2.00 × 1.5) = **$97.00**
- **Take Profit** (2.5x multiplier): $100.00 + ($2.00 × 2.5) = **$105.00**

### Dynamic Adjustment
As market volatility changes, ATR adjusts automatically:

| Market Condition | ATR Value | Stop Loss | Take Profit |
|-----------------|-----------|-----------|-------------|
| **Low Volatility** | $1.00 | Entry - $1.50 | Entry + $2.50 |
| **Medium Volatility** | $2.00 | Entry - $3.00 | Entry + $5.00 |
| **High Volatility** | $4.00 | Entry - $6.00 | Entry + $10.00 |

This means:
- ✅ Wider stops in volatile markets (avoid premature stops)
- ✅ Tighter stops in calm markets (protect capital)
- ✅ Profit targets aligned with actual price swings

## Usage

### Basic Backtest

```bash
python -m connors.cli.backtest \
  --tickers AAPL \
  --strategy LCRSI2_ATR \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2024-12-31
```

### With Custom ATR Parameters

```bash
python -m connors.cli.backtest \
  --tickers AAPL \
  --strategy LCRSI2_ATR \
  --strategy-params "atr_period:14;atr_sl_multiplier:2.0;atr_tp_multiplier:3.0" \
  --config america \
  --datasource yfinance
```

### With Dataset File

```bash
python -m connors.cli.backtest \
  --tickers ELET3 \
  --strategy LCRSI2_ATR \
  --dataset_file ~/Downloads/ELET3.json \
  --commission 0.0 \
  --cash 10000000
```

### Optimize ATR Multipliers

**Optimize both SL and TP multipliers:**
```bash
python -m connors.cli.backtest \
  --tickers AAPL \
  --strategy LCRSI2_ATR \
  --config america \
  --datasource yfinance \
  --optimize \
  --optimize-params "atr_sl_multiplier:[1.0,1.5,2.0,2.5,3.0];atr_tp_multiplier:[2.0,2.5,3.0,3.5,4.0]"
```

This tests:
- Stop Loss: 1.0x, 1.5x, 2.0x, 2.5x, 3.0x ATR
- Take Profit: 2.0x, 2.5x, 3.0x, 3.5x, 4.0x ATR
- **Total: 5 × 5 = 25 combinations**

**Optimize ATR period and multipliers:**
```bash
python -m connors.cli.backtest \
  --tickers AAPL \
  --strategy LCRSI2_ATR \
  --config america \
  --datasource yfinance \
  --optimize \
  --optimize-params "atr_period:range(10, 21, 2);atr_sl_multiplier:[1.5,2.0];atr_tp_multiplier:[2.5,3.0]"
```

This tests:
- ATR Period: 10, 12, 14, 16, 18, 20
- Stop Loss: 1.5x, 2.0x ATR
- Take Profit: 2.5x, 3.0x ATR
- **Total: 6 × 2 × 2 = 24 combinations**

## Implementation Notes

### ATR Calculation at Entry

This strategy stores the ATR value at entry time to ensure consistent TP/SL levels throughout the trade:

```python
# At entry
entry_price = 100.00
entry_atr = 2.00  # ATR value at entry time

# TP/SL levels remain constant during trade
stop_loss_level = 100.00 - (2.00 × 1.5) = 97.00
take_profit_level = 100.00 + (2.00 × 2.5) = 105.00
```

**Why store ATR at entry?**
- ✅ Consistent risk/reward ratio throughout trade
- ✅ Prevents stop/target moving during position
- ✅ Clearer trade management and logging

### Type Handling (Critical)

This strategy handles `backtesting.py`'s internal `Decimal` types correctly:

```python
# backtesting.py uses Decimal internally
current_close = Decimal(str(self.data.Close[-1]))
entry_price = Decimal(str(raw_entry))
entry_atr = Decimal(str(current_atr_raw))

# Calculate dynamic levels with Decimal arithmetic
stop_loss_level = entry_price - (entry_atr * Decimal(str(self.atr_sl_multiplier)))
take_profit_level = entry_price + (entry_atr * Decimal(str(self.atr_tp_multiplier)))
```

**Optimizer Support:**
The strategy automatically converts integer parameters to float:
```python
self.atr_sl_multiplier = float(atr_sl_multiplier)  # Handles optimizer integers
self.atr_tp_multiplier = float(atr_tp_multiplier)  # Converts 2 → 2.0
```

### MarketSnapshot Protocol

Uses the same high-performance MarketSnapshot protocol as LCRSI2:
- 4-10x faster than DataFrame-based approaches
- Zero-copy data access
- Type-safe signal generation

## Example Output

```
2025-10-16 22:00:00 | INFO | 🟢 BUY signal - RSI 3.09 < 5 AND Close 37.27 > Long_SMA 33.48, ATR: 1.85
2025-10-16 22:00:00 | INFO | 💰 EXECUTING BUY at 37.27 on 2024-01-08 00:00:00, ATR: 1.85
2025-10-16 22:00:00 | INFO | 🎯 ATR TAKE PROFIT triggered - Price: $41.90 >= TP: $41.90 (Entry: $37.27, ATR: 1.85, Multiplier: 2.5x, P&L: +12.42%)
2025-10-16 22:00:00 | INFO | 💸 EXECUTING SELL at 41.90 on 2024-01-15 (Entry: 37.27, P&L: +12.42%)
```

## Comparison of TP/SL Approaches

| Feature | LCRSI2 | LCRSI2_TPSL | LCRSI2_ATR |
|---------|-----------|----------------|---------------|
| Entry Logic | ✅ Same | ✅ Same | ✅ Same |
| Regular Exit | ✅ Close ≥ SMA(5) | ✅ Close ≥ SMA(5) | ✅ Close ≥ SMA(5) |
| Stop Loss | ❌ No | ✅ Fixed % | ✅ ATR-based (dynamic) |
| Take Profit | ❌ No | ✅ Fixed % | ✅ ATR-based (dynamic) |
| Volatility Adaptive | ❌ No | ❌ No | ✅ Yes |
| Risk Management | ❌ None | ✅ Fixed risk | ✅ Volatility-adjusted risk |

## When to Use Each Strategy

### Use LCRSI2_ATR (ATR-Based) When:
- ✅ Trading across different volatility regimes
- ✅ Want stops to adapt to market conditions
- ✅ Asset has varying volatility (tech stocks, crypto)
- ✅ Want fewer whipsaws in volatile markets
- ✅ Need consistent risk-adjusted returns

### Use LCRSI2_TPSL (Fixed %) When:
- ✅ Trading stable, low-volatility assets
- ✅ Want predictable risk per trade
- ✅ Testing specific risk/reward ratios
- ✅ Simpler optimization (fewer parameters)
- ✅ Prefer percentage-based thinking

## Performance Tips

1. **ATR Period Selection**
   - Shorter periods (7-10): More responsive to recent volatility
   - Standard period (14): Balanced view of volatility
   - Longer periods (20-30): Smoother, less reactive

2. **Stop Loss Multipliers**
   - Conservative: 2.0-3.0x ATR (wider stops, fewer stops)
   - Standard: 1.5-2.0x ATR (balanced approach)
   - Aggressive: 1.0-1.5x ATR (tighter stops, more stops)

3. **Take Profit Multipliers**
   - Conservative: 2.0-2.5x ATR (quick profits)
   - Standard: 2.5-3.0x ATR (balanced targets)
   - Aggressive: 3.0-4.0x ATR (larger winners)

4. **Risk/Reward Ratio**
   - Maintain TP multiplier > SL multiplier
   - Common ratios: 1.5:2.5, 2.0:3.0, 1.0:2.0
   - Test different ratios via optimization

5. **Asset-Specific Tuning**
   - High volatility assets: Larger multipliers (avoid whipsaws)
   - Low volatility assets: Smaller multipliers (capture smaller moves)
   - Run optimization to find optimal values per asset

## Files

- `connors/strategies/lcrsi2_atr.py` - Strategy implementation
- `connors/strategies/__init__.py` - Strategy registration
- `connors/strategies/LCRSI2_ATR_README.md` - This documentation

## See Also

- [LCRSI2 (base strategy)](./lcrsi2.py)
- [LCRSI2_TPSL (fixed percent TP/SL)](./lcrsi2_tpsl.py)
- [Backtest Documentation](../docs/BACKTEST.md)
- [Strategy Registry](../core/registry.py)
- [ATR Indicator (TA-Lib)](https://www.ta-lib.org/function.html?name=ATR)
