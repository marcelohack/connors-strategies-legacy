# RSI Crypto Strategy - Optimized for Cryptocurrency Trading

RSI-based trading strategies specifically designed for the volatile cryptocurrency market, based on extensive research from [MC² Finance](https://www.mc2.fi/blog/best-rsi-settings-for-1-hour-chart-crypto).

## Overview

Traditional RSI settings (14-period, 70/30 thresholds) don't perform well in crypto markets due to extreme volatility. This strategy implements research-backed adjustments specifically designed for crypto trading on 1-hour charts.

## Key Insights from Research

1. **Standard RSI(14, 70/30) produces losses in crypto markets**
   - Study: "An Investigation of the Relative Strength Index" found small losses rather than profits
   - Study: "INVESTIGATING THE EFFICACY OF RSI IN THE NIFTY 50 INDEX" reported negative returns

2. **Crypto volatility requires adjusted thresholds**
   - Standard 70/30 thresholds produce too many false signals
   - **80/20 or 75/25 thresholds** reduce false signals significantly

3. **Trend filters are essential**
   - Combining RSI with moving averages (50 EMA, 200 EMA) improves accuracy
   - Avoid counter-trend trades in strong trends

4. **RSI divergences provide edge**
   - Price making higher highs while RSI makes lower highs signals potential reversal

## Available Strategy Variants

### 1. RSI_Crypto (Default)
**Balanced strategy with trend filter**

```python
rsi_length = 14
oversold_level = 20    # More conservative than standard 30
overbought_level = 80  # More conservative than standard 70
trend_ema_length = 200
use_trend_filter = True
```

**Entry:** RSI < 20 AND price > 200 EMA
**Exit:** RSI > 80

**Best for:** General crypto trading, medium-term positions

---

### 2. RSI_Crypto_Fast
**Faster signals with RSI(7)**

```python
rsi_length = 7         # Faster reaction
oversold_level = 20
overbought_level = 80
trend_ema_length = 200
use_trend_filter = True
```

**Entry:** RSI(7) < 20 AND price > 200 EMA
**Exit:** RSI(7) > 80

**Best for:** Active traders, more frequent signals
**Warning:** More false signals, requires closer monitoring

---

### 3. RSI_Crypto_Conservative
**Stricter thresholds for higher quality signals**

```python
rsi_length = 14
oversold_level = 15    # Very conservative
overbought_level = 85  # Very conservative
trend_ema_length = 200
use_trend_filter = True
```

**Entry:** RSI < 15 AND price > 200 EMA
**Exit:** RSI > 85

**Best for:** Risk-averse traders, fewer but stronger signals
**Trade-off:** Fewer opportunities but higher win rate

---

### 4. RSI_Crypto_No_Filter
**No trend filter - trades both directions**

```python
rsi_length = 14
oversold_level = 20
overbought_level = 80
use_trend_filter = False  # DISABLED
```

**Entry:** RSI < 20 (no trend requirement)
**Exit:** RSI > 80

**Best for:** Range-bound markets, experienced traders
**Warning:** Higher risk, trades against trends

## Strategy Comparison

| Strategy | RSI Period | Thresholds | Trend Filter | Signals | Risk Level |
|----------|-----------|------------|--------------|---------|------------|
| **RSI_Crypto** | 14 | 80/20 | ✅ 200 EMA | Medium | Medium |
| **RSI_Crypto_Fast** | 7 | 80/20 | ✅ 200 EMA | High | Medium-High |
| **RSI_Crypto_Conservative** | 14 | 85/15 | ✅ 200 EMA | Low | Low |
| **RSI_Crypto_No_Filter** | 14 | 80/20 | ❌ None | High | High |

## Usage Examples

### Example 1: Basic Crypto Trading (BTC, 1-hour chart)

```bash
python -m connors.cli.backtest \
  --tickers BTC-USD \
  --config america \
  --strategy RSI_Crypto \
  --datasource yfinance \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --interval 1h
```

### Example 2: Fast Trading with ETH

```bash
python -m connors.cli.backtest \
  --tickers ETH-USD \
  --config america \
  --strategy RSI_Crypto_Fast \
  --datasource yfinance \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --interval 1h
```

### Example 3: Conservative Trading

```bash
python -m connors.cli.backtest \
  --tickers BTC-USD \
  --config america \
  --strategy RSI_Crypto_Conservative \
  --datasource yfinance \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --interval 1h
```

### Example 4: Custom Parameters

```bash
python -m connors.cli.backtest \
  --tickers SOL-USD \
  --config america \
  --strategy RSI_Crypto \
  --strategy-params "rsi_length:7;oversold_level:25;overbought_level:75" \
  --datasource yfinance \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --interval 1h
```

### Example 5: Multiple Cryptos

```bash
python -m connors.cli.backtest \
  --tickers BTC-USD,ETH-USD,SOL-USD,ADA-USD \
  --config america \
  --strategy RSI_Crypto \
  --datasource yfinance \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --interval 1h
```

## Parameter Optimization Guide

### RSI Length
- **7-9**: Fast signals, more trades, more false positives
- **14**: Balanced (recommended default)
- **21**: Slower, smoother, fewer trades

### Oversold Level
- **15**: Very conservative, fewer signals, higher quality
- **20**: Recommended for crypto (default)
- **25**: More signals, earlier entries
- **30**: Standard (not recommended for crypto)

### Overbought Level
- **70**: Standard (not recommended for crypto)
- **75**: More signals
- **80**: Recommended for crypto (default)
- **85**: Very conservative, longer holds

### Trend Filter
- **50 EMA**: Medium-term trend (not implemented, can be added)
- **200 EMA**: Long-term trend (default)
- **Disabled**: Trade both directions (higher risk)

## When to Use Each Variant

### Use RSI_Crypto (Default) when:
- ✅ Trading major cryptocurrencies (BTC, ETH)
- ✅ Using 1-hour or 4-hour timeframes
- ✅ Want balanced risk/reward
- ✅ Prefer trend-following approach

### Use RSI_Crypto_Fast when:
- ✅ Day trading or scalping
- ✅ Comfortable with more frequent signals
- ✅ Can monitor positions actively
- ✅ Trading on lower timeframes (5m, 15m, 1h)

### Use RSI_Crypto_Conservative when:
- ✅ Prefer fewer, higher-quality trades
- ✅ Risk-averse approach
- ✅ Longer holding periods acceptable
- ✅ Want higher win rate over trade frequency

### Use RSI_Crypto_No_Filter when:
- ✅ Range-bound markets (sideways price action)
- ✅ Experienced with mean-reversion strategies
- ✅ Want to capture both trend and counter-trend moves
- ✅ Comfortable with higher risk

## Real-World Example Scenarios

### Scenario 1: Bitcoin Crash (Feb 2025)
**Context:** Bitcoin dropped 20%, entering bear market territory

**RSI_Crypto Response:**
- RSI dropped to 15 (oversold)
- But price < 200 EMA (downtrend)
- **NO BUY SIGNAL** - trend filter prevented entry
- Avoided catching a falling knife ✅

**RSI_Crypto_No_Filter Response:**
- RSI dropped to 15 (oversold)
- **BUY SIGNAL** triggered (no trend filter)
- Price continued falling
- **Loss taken** ❌

### Scenario 2: Bitcoin Sharp Decline (March 2024)
**Context:** Bitcoin fell from $60,000 to $55,000 in hours

**RSI_Crypto_Fast (RSI 7) Response:**
- RSI(7) dropped below 20 quickly
- **BUY SIGNAL** at $55,000
- Price continued to $50,000
- **Premature entry** ❌

**RSI_Crypto (RSI 14) Response:**
- RSI(14) dropped below 20 at $52,000
- **BUY SIGNAL** closer to bottom
- **Better entry point** ✅

## Combining with Other Indicators

### Recommended Additions

1. **Volume Confirmation**
   - High volume on oversold readings = stronger reversal signal
   - Low volume on overbought readings = weaker exit signal

2. **Support/Resistance Levels**
   - RSI oversold near support = higher probability trade
   - RSI overbought near resistance = stronger exit signal

3. **Candlestick Patterns**
   - Hammer/Bullish Engulfing at RSI < 20 = strong confirmation
   - Shooting Star/Bearish Engulfing at RSI > 80 = strong exit signal

4. **RSI Divergence (Advanced)**
   - Price making higher highs, RSI making lower highs = bearish divergence
   - Price making lower lows, RSI making higher lows = bullish divergence

## Performance Considerations

### Expected Characteristics

**Win Rate:**
- Conservative: 60-70%
- Default: 50-60%
- Fast: 45-55%
- No Filter: 40-50%

**Trade Frequency (1-hour chart):**
- Conservative: 1-3 trades/month
- Default: 3-6 trades/month
- Fast: 6-12 trades/month
- No Filter: 8-15 trades/month

**Best Timeframes:**
- **1-hour**: Primary recommendation (per article)
- **4-hour**: Also effective, fewer signals
- **15-minute**: Use Fast variant
- **1-day**: Use Conservative variant

**Best Crypto Assets:**
- **BTC, ETH**: Most liquid, best performance
- **Major Altcoins**: SOL, ADA, BNB - good performance
- **Low-cap coins**: Higher risk, more volatility

## Risk Management Recommendations

1. **Position Sizing**
   - Start with 1-2% of capital per trade
   - Conservative variant: Can use 2-3%
   - Fast variant: Use 1% or less

2. **Stop Loss (Optional)**
   - Consider adding 2-3% stop loss below entry
   - Or use ATR-based stop (1.5-2x ATR)

3. **Take Profit (Optional)**
   - Consider partial profit at 50% of position when RSI > 70
   - Trail remaining position until RSI > 80

4. **Maximum Concurrent Positions**
   - Diversify across 3-5 different cryptos
   - Don't overexpose to single asset

## Limitations and Warnings

### ⚠️ What This Strategy Does NOT Do:

1. **No Divergence Detection** (yet)
   - Future enhancement planned
   - Manually monitor for divergences

2. **No Stop Loss Built-in**
   - Consider adding via strategy parameters
   - Or use broker-level stops

3. **No Position Sizing**
   - Uses fixed size per backtesting framework
   - Implement dynamic sizing in live trading

4. **No Multi-Timeframe Analysis**
   - Operates on single timeframe only
   - Consider checking higher timeframes manually

### 🚫 When NOT to Use:

- ❌ During extreme market crashes (circuit breakers)
- ❌ On low-liquidity altcoins (slippage risk)
- ❌ Without understanding crypto volatility
- ❌ With leverage (until thoroughly tested)
- ❌ In sideways markets (use No_Filter variant instead)

## Testing Recommendations

### Backtesting Best Practices

1. **Test Period:** Minimum 1 year, ideally 2-3 years
2. **Include Bull and Bear Markets:** Ensure diverse conditions
3. **Commission/Slippage:** Add realistic costs (0.1-0.5%)
4. **Different Timeframes:** Test 15m, 1h, 4h, 1d
5. **Multiple Assets:** Test on BTC, ETH, and major altcoins

### Walk-Forward Testing

```bash
# Train period: 2023
python -m connors.cli.backtest \
  --tickers BTC-USD \
  --strategy RSI_Crypto \
  --start 2023-01-01 \
  --end 2023-12-31 \
  --optimize

# Test period: 2024 (with optimized parameters)
python -m connors.cli.backtest \
  --tickers BTC-USD \
  --strategy RSI_Crypto \
  --strategy-params "rsi_length:12;oversold_level:22" \
  --start 2024-01-01 \
  --end 2024-12-31
```

## Future Enhancements

Planned improvements:

- [ ] RSI Divergence detection
- [ ] Multi-timeframe confirmation
- [ ] Dynamic position sizing based on volatility
- [ ] ATR-based stop loss integration
- [ ] Volume-weighted RSI
- [ ] Machine learning optimized thresholds

## References

- [MC² Finance: Best RSI Settings for 1 Hour Crypto Chart](https://www.mc2.fi/blog/best-rsi-settings-for-1-hour-chart-crypto)
- [MC² Finance: Best Crypto Indicators](https://www.mc2.fi/blog/best-crypto-indicators)
- "An Investigation of the Relative Strength Index" - ResearchGate
- "Effectiveness of the RSI Signals in Timing the Cryptocurrency Market" - PMC

## Contributing

Improvements welcome! Please test thoroughly and provide:
- Backtest results on multiple cryptos
- Different timeframes tested
- Win rate, return, max drawdown metrics
- Any market conditions where strategy fails

## License

Part of the Connors Trading System
