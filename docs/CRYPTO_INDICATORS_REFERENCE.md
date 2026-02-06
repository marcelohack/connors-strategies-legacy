# Crypto Indicators Reference Guide

Comprehensive reference for technical indicators commonly used in cryptocurrency trading, based on industry research and best practices.

**Source:** [MC² Finance: Best Crypto Indicators](https://www.mc2.fi/blog/best-crypto-indicators)

---

## 📊 Momentum Indicators

### 1. RSI (Relative Strength Index)

**Purpose:** Identify overbought/oversold conditions and momentum

**Settings for Crypto:**
- **Period:** 14 (standard), 7-9 (faster), 21 (slower)
- **Overbought:** 70 (standard), 80 (crypto-adjusted)
- **Oversold:** 30 (standard), 20 (crypto-adjusted)
- **Timeframe:** 1-hour recommended, also effective on 15m, 4h, 1d

**Trading Signals:**
- Buy: RSI < 20-30 (oversold)
- Sell: RSI > 70-80 (overbought)
- Divergence: Price vs RSI divergence signals reversals

**Crypto-Specific Notes:**
- Use wider thresholds (80/20 instead of 70/30) due to volatility
- Combine with trend filters (200 EMA)
- More effective on liquid assets (BTC, ETH)

---

### 2. MACD (Moving Average Convergence Divergence)

**Purpose:** Trend direction, momentum, and potential reversals

**Standard Settings:**
- **Fast EMA:** 12
- **Slow EMA:** 26
- **Signal Line:** 9

**Crypto-Optimized Settings:**
- **5-minute chart:** Faster settings (5, 13, 5)
- **1-minute chart:** Even faster (3, 10, 16)
- **1-hour chart:** Standard (12, 26, 9)

**Trading Signals:**
- **Bullish Crossover:** MACD crosses above signal line
- **Bearish Crossover:** MACD crosses below signal line
- **Histogram:** Momentum strength (growing = strengthening trend)
- **Zero Line:** Above = bullish, Below = bearish

**Crypto-Specific Notes:**
- Adjust settings based on timeframe
- Use faster settings for volatile markets
- Combine with volume confirmation

---

### 3. Stochastic Oscillator

**Purpose:** Momentum and overbought/oversold levels

**Settings:**
- **%K Period:** 14
- **%D Period:** 3
- **Smoothing:** 3

**Trading Signals:**
- **Overbought:** > 80
- **Oversold:** < 20
- **Bullish:** %K crosses above %D in oversold
- **Bearish:** %K crosses below %D in overbought

---

## 📈 Trend Indicators

### 4. Moving Averages (SMA/EMA)

**Purpose:** Identify trend direction and support/resistance

**Common Periods:**
- **Short-term:** 5, 10, 20
- **Medium-term:** 50, 100
- **Long-term:** 200

**EMA vs SMA:**
- **EMA:** More responsive, better for crypto volatility
- **SMA:** Smoother, better for long-term trends

**Trading Strategies:**
- **Golden Cross:** 50 EMA crosses above 200 EMA (bullish)
- **Death Cross:** 50 EMA crosses below 200 EMA (bearish)
- **Price above 200 EMA:** Uptrend filter
- **Multiple MA:** Use 20/50/200 for multi-timeframe confirmation

**Crypto-Specific Settings:**
- **1-hour:** 50 EMA, 200 EMA
- **4-hour:** 20 EMA, 50 EMA
- **Daily:** 50 SMA, 200 SMA

---

### 5. Bollinger Bands

**Purpose:** Volatility and overbought/oversold levels

**Settings:**
- **Period:** 20
- **Standard Deviations:** 2

**Trading Signals:**
- **Price touches lower band:** Potential buy (oversold)
- **Price touches upper band:** Potential sell (overbought)
- **Squeeze:** Low volatility, potential breakout
- **Expansion:** High volatility, trend continuation

**Crypto-Specific Notes:**
- Consider 2.5 or 3 standard deviations for high volatility
- Use with RSI for confirmation
- Effective on 1-hour and 4-hour charts

---

## 🔊 Volume Indicators

### 6. Volume Profile

**Purpose:** Identify support/resistance based on volume

**Key Concepts:**
- **Point of Control (POC):** Highest volume level
- **Value Area:** 70% of volume (support/resistance zone)
- **High Volume Nodes:** Strong support/resistance
- **Low Volume Nodes:** Weak levels, price moves quickly through

**Trading Application:**
- Buy near high volume support
- Sell near high volume resistance
- Breakouts from value area = strong moves

---

### 7. OBV (On-Balance Volume)

**Purpose:** Confirm trends and detect divergences

**Calculation:** Cumulative volume based on price direction

**Trading Signals:**
- **Rising OBV:** Accumulation (bullish)
- **Falling OBV:** Distribution (bearish)
- **Divergence:** OBV rising while price falling = bullish

---

## 💹 Volatility Indicators

### 8. ATR (Average True Range)

**Purpose:** Measure volatility, set stop losses

**Settings:**
- **Period:** 14

**Applications:**
- **Position Sizing:** Adjust based on volatility
- **Stop Loss:** Entry - (ATR × 1.5-2.0)
- **Take Profit:** Entry + (ATR × 2.5-3.0)
- **Breakout Filter:** High ATR = strong breakout

**Crypto-Specific:**
- ATR typically higher than stocks (30-50% range)
- Use for dynamic stop losses
- Combine with RSI for volatility-adjusted entries

---

### 9. Keltner Channels

**Purpose:** Volatility-based channels for trend trading

**Settings:**
- **EMA Period:** 20
- **ATR Multiplier:** 2

**Trading Signals:**
- **Price above channel:** Strong uptrend
- **Price below channel:** Strong downtrend
- **Bounce off channel:** Trend continuation

---

## 🎯 Multi-Indicator Strategies

### Strategy 1: RSI + EMA Trend Filter
```
Entry: RSI < 20 AND Price > 200 EMA
Exit: RSI > 80
```
*Implemented in RSI_Crypto strategy*

---

### Strategy 2: MACD + Volume
```
Entry: MACD bullish crossover AND volume > 20-day average
Exit: MACD bearish crossover
```

---

### Strategy 3: Bollinger + RSI
```
Entry: Price touches lower band AND RSI < 30
Exit: Price touches middle band OR RSI > 70
```

---

### Strategy 4: EMA Crossover + ATR
```
Entry: 50 EMA crosses above 200 EMA
Stop Loss: Entry - (ATR × 1.5)
Take Profit: Entry + (ATR × 3.0)
```

---

## 🕐 Timeframe-Specific Recommendations

### 1-Minute Chart (Scalping)
- **Primary:** MACD (3, 10, 16)
- **Secondary:** RSI (7), Volume
- **Risk:** Very high, requires tight stops

### 5-Minute Chart (Day Trading)
- **Primary:** MACD (5, 13, 5), RSI (9)
- **Secondary:** Volume Profile, EMA (20, 50)
- **Best for:** Active traders

### 15-Minute Chart (Swing Trading)
- **Primary:** RSI (14), MACD (12, 26, 9)
- **Secondary:** Bollinger Bands, 50/200 EMA
- **Best for:** Part-time traders

### 1-Hour Chart (Position Trading)
- **Primary:** RSI (14), 50/200 EMA
- **Secondary:** MACD, ATR, Volume
- **Best for:** Working professionals
- **Most researched:** Optimal for crypto according to MC² Finance

### 4-Hour Chart (Swing/Position)
- **Primary:** EMA (20, 50, 200), RSI (14)
- **Secondary:** MACD, Bollinger Bands
- **Best for:** Medium-term positions

### Daily Chart (Long-term)
- **Primary:** SMA (50, 200), Volume Profile
- **Secondary:** RSI (14), MACD
- **Best for:** Investors, trend followers

---

## 🚨 Common Mistakes to Avoid

### 1. Using Too Many Indicators
- **Problem:** Conflicting signals, analysis paralysis
- **Solution:** Stick to 2-3 complementary indicators

### 2. Ignoring Timeframes
- **Problem:** Indicator works on one timeframe, fails on another
- **Solution:** Optimize for your specific timeframe

### 3. Standard Settings on Crypto
- **Problem:** Stock indicator settings don't work for crypto volatility
- **Solution:** Use crypto-adjusted thresholds (RSI 80/20, wider Bollinger Bands)

### 4. No Trend Filter
- **Problem:** Counter-trend trades in strong trends
- **Solution:** Always use 200 EMA or similar trend filter

### 5. Over-Optimization
- **Problem:** Settings work in backtest, fail in live trading
- **Solution:** Use standard or slightly adjusted settings, walk-forward test

---

## 📚 Indicator Combinations by Goal

### Maximum Win Rate
- **Indicators:** RSI (14, 85/15), 200 EMA, Volume
- **Strategy:** Very conservative entries, trend-following only
- **Expected:** 60-70% win rate, fewer trades

### Maximum Trade Frequency
- **Indicators:** RSI (7, 70/30), MACD (fast settings)
- **Strategy:** Fast signals, both trend and counter-trend
- **Expected:** 40-50% win rate, many trades

### Best Risk/Reward
- **Indicators:** RSI (14, 80/20), 200 EMA, ATR
- **Strategy:** Trend-following with volatility-based stops
- **Expected:** 50-60% win rate, good profit factor

### Lowest Drawdown
- **Indicators:** RSI (14, 85/15), 50/200 EMA, ATR stops
- **Strategy:** Ultra-conservative, long-term trend only
- **Expected:** Low returns but minimal drawdowns

---

## 🔮 Advanced Topics

### RSI Divergence
- **Bullish:** Price lower low, RSI higher low
- **Bearish:** Price higher high, RSI lower high
- **Note:** Powerful but requires experience to identify

### Volume Divergence
- **Rising price + falling volume:** Weak rally, potential reversal
- **Falling price + rising volume:** Strong selloff, potential bounce

### Multi-Timeframe Analysis
- **Higher timeframe:** Determine overall trend (daily for direction)
- **Lower timeframe:** Find precise entry (1-hour for timing)
- **Rule:** Only trade in direction of higher timeframe trend

---

## 📖 Implementation Status

### Currently Implemented in Connors System
- ✅ RSI (all variants) - `RSI_Crypto` strategy
- ✅ SMA/EMA - Used in trend filters
- ✅ ATR - `LCRSI2_ATR` strategy
- ✅ MACD - Planned for future strategies

### Planned Implementations
- 🔄 Bollinger Bands strategy
- 🔄 Stochastic + RSI combo
- 🔄 Volume Profile integration
- 🔄 Multi-timeframe strategies

---

## 📊 Quick Reference Table

| Indicator | Best Timeframe | Crypto Setting | Primary Use | Difficulty |
|-----------|----------------|----------------|-------------|------------|
| **RSI** | 1h, 4h | 14 period, 80/20 | Overbought/Oversold | Easy |
| **MACD** | 5m, 1h | 12/26/9 or 5/13/5 | Trend + Momentum | Medium |
| **EMA** | All | 50, 200 | Trend Filter | Easy |
| **Bollinger** | 1h, 4h | 20, 2-2.5 SD | Volatility | Medium |
| **ATR** | All | 14 period | Stop Loss | Easy |
| **Stochastic** | 15m, 1h | 14, 3, 3 | Momentum | Medium |
| **Volume** | All | N/A | Confirmation | Medium |
| **OBV** | 4h, 1d | N/A | Divergence | Hard |

---

## 🎓 Learning Path

### Beginner (Month 1-2)
1. Master RSI with 80/20 thresholds
2. Learn 200 EMA trend filter
3. Understand basic support/resistance
4. Paper trade RSI_Crypto strategy

### Intermediate (Month 3-4)
1. Add MACD to your toolkit
2. Learn Bollinger Bands
3. Understand volume analysis
4. Combine RSI + EMA + Volume

### Advanced (Month 5-6)
1. Study RSI divergences
2. Multi-timeframe analysis
3. Volume Profile
4. Custom strategy development

### Expert (Month 7+)
1. Develop your own indicator combos
2. Optimize for specific market conditions
3. Implement risk management rules
4. Build automated trading systems

---

## 🔗 External Resources

- [MC² Finance: Best Crypto Indicators](https://www.mc2.fi/blog/best-crypto-indicators)
- [MC² Finance: Best RSI Settings for 1 Hour Crypto Chart](https://www.mc2.fi/blog/best-rsi-settings-for-1-hour-chart-crypto)
- [MC² Finance: Best MACD Settings](https://www.mc2.fi/blog/best-macd-setting-for-5-minute-chart)
- TradingView Indicator Documentation
- Investopedia Technical Analysis Guide

---

## 📝 Notes

This reference guide is based on industry research and best practices for cryptocurrency trading. Always backtest indicators on your specific assets and timeframes before live trading.

**Remember:**
- No indicator works 100% of the time
- Combine multiple indicators for confirmation
- Always use proper risk management
- Adjust settings based on market volatility
- Paper trade before risking real capital

---

*Part of the Connors Trading System*
*Last Updated: 2025-10-18*
