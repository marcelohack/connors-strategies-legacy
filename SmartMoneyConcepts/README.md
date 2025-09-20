# Smart Money Concepts Strategy

A comprehensive implementation of Smart Money Concepts (SMC) trading methodology converted from Pine Script to Python for use with the backtesting.py framework.

## Overview

This strategy implements the core principles of Smart Money Concepts, which focuses on identifying institutional trading patterns and following "smart money" movements through price structure analysis. The strategy identifies key institutional concepts such as:

- **Market Structure Analysis**: Break of Structure (BOS) and Change of Character (CHoCH) detection
- **Order Blocks**: Institutional supply and demand zones
- **Fair Value Gaps (FVG)**: Inefficient price movements that tend to get filled
- **Premium/Discount Zones**: Areas where price is overvalued or undervalued relative to recent range
- **Multi-timeframe Confluence**: Aligning trades with higher timeframe bias

## Strategy Logic

### Entry Conditions

**Long Entries:**
1. Bullish market structure break (BOS) detected
2. Price retraces to a valid bullish order block or fair value gap
3. Price is in discount zone (lower 30% of recent range)
4. Overall trend filter is bullish (price above trend EMA)
5. Minimum time gap since last trade

**Short Entries:**
1. Bearish market structure break (BOS) detected
2. Price retraces to a valid bearish order block or fair value gap
3. Price is in premium zone (upper 30% of recent range)
4. Overall trend filter is bearish (price below trend EMA)
5. Minimum time gap since last trade

### Exit Conditions

1. **Structure-based Exit**: Opposite market structure break
2. **Profit Target**: Based on reward:risk ratio (default 2:1)
3. **Stop Loss**: Beyond order block or ATR-based
4. **Time-based Exit**: Maximum holding period reached

### Risk Management

- **Position Sizing**: Based on percentage risk per trade
- **Stop Loss**: ATR-based or structure-based stops
- **Reward:Risk Ratio**: Configurable minimum ratio
- **Maximum Holding Period**: Prevents indefinite positions

## Key Parameters

### Core SMC Parameters
- `swing_length`: Length for swing point detection (default: 10)
- `structure_length`: Length for structure break detection (default: 20)
- `min_structure_strength`: Minimum swing strength for valid structure (default: 3)

### Order Block Parameters
- `enable_order_blocks`: Enable order block trading (default: True)
- `max_order_blocks`: Maximum number of order blocks to track (default: 5)
- `order_block_mitigation_method`: "Close" or "HighLow" (default: "HighLow")
- `order_block_filter_atr_multiplier`: Filter small order blocks (default: 1.5)

### Fair Value Gap Parameters
- `enable_fair_value_gaps`: Enable FVG trading (default: True)
- `min_fvg_size_atr_multiplier`: Minimum FVG size filter (default: 0.5)
- `max_fvg_count`: Maximum FVGs to track (default: 10)

### Structure Parameters
- `enable_bos_trading`: Trade on Break of Structure (default: True)
- `enable_choch_trading`: Trade on Change of Character (default: False)

### Premium/Discount Zones
- `enable_premium_discount`: Enable zone filtering (default: True)
- `lookback_period`: Period for range calculation (default: 100)

### Risk Management
- `risk_per_trade`: Risk percentage per trade (default: 2.0%)
- `reward_risk_ratio`: Minimum reward:risk ratio (default: 2.0)
- `max_holding_bars`: Maximum bars to hold position (default: 50)
- `use_atr_stops`: Use ATR-based stops (default: True)
- `atr_stop_multiplier`: ATR multiplier for stop loss (default: 2.0)
- `atr_period`: ATR calculation period (default: 14)

### Filters
- `use_trend_filter`: Only trade with overall trend (default: True)
- `trend_ema_period`: EMA period for trend determination (default: 200)
- `min_trade_gap_bars`: Minimum bars between trades (default: 5)

## Smart Money Concepts Explained

### Market Structure
Market structure refers to the pattern of higher highs/higher lows (uptrend) or lower highs/lower lows (downtrend). Key concepts:

- **Break of Structure (BOS)**: When price breaks above a previous high in an uptrend or below a previous low in a downtrend
- **Change of Character (CHoCH)**: When price breaks the opposite direction, indicating a potential trend change

### Order Blocks
Order blocks are zones where institutional traders place large orders, creating supply or demand imbalances:

- **Bullish Order Block**: A down candle before a bullish structure break (demand zone)
- **Bearish Order Block**: An up candle before a bearish structure break (supply zone)
- Order blocks act as support/resistance levels where price often reacts

### Fair Value Gaps (FVG)
Fair Value Gaps are areas where price moves inefficiently, leaving gaps in the chart:

- **Bullish FVG**: Gap created during upward movement (gap between candle 1 low and candle 3 high)
- **Bearish FVG**: Gap created during downward movement (gap between candle 1 high and candle 3 low)
- These gaps often get "filled" when price returns to the area

### Premium/Discount Zones
Based on the recent price range:

- **Premium Zone**: Upper 30% of range (expensive area, good for selling)
- **Discount Zone**: Lower 30% of range (cheap area, good for buying)
- **Equilibrium**: Middle 40% of range (neutral area)

## Usage Examples

### Basic Backtesting
```bash
python -m connors.cli.backtest \
  --external-strategy ~/.connors/strategies/SmartMoneyConcepts/smart_money_concepts.py \
  --strategy SmartMoneyConcepts \
  --tickers AAPL \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31
```

### With Parameter Overrides
```bash
python -m connors.cli.backtest \
  --external-strategy ~/.connors/strategies/SmartMoneyConcepts/smart_money_concepts.py \
  --strategy SmartMoneyConcepts \
  --strategy-params "risk_per_trade:1.5;reward_risk_ratio:3.0;swing_length:15" \
  --tickers AAPL,MSFT,GOOGL \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31
```

### Conservative Settings
```bash
# More conservative approach with strict filters
python -m connors.cli.backtest \
  --external-strategy ~/.connors/strategies/SmartMoneyConcepts/smart_money_concepts.py \
  --strategy SmartMoneyConcepts \
  --strategy-params "risk_per_trade:1.0;min_structure_strength:5;enable_choch_trading:False;min_trade_gap_bars:10" \
  --tickers SPY \
  --config america \
  --datasource yfinance
```

### Aggressive Settings
```bash
# More aggressive approach with looser filters
python -m connors.cli.backtest \
  --external-strategy ~/.connors/strategies/SmartMoneyConcepts/smart_money_concepts.py \
  --strategy SmartMoneyConcepts \
  --strategy-params "risk_per_trade:3.0;enable_choch_trading:True;min_structure_strength:2;reward_risk_ratio:1.5" \
  --tickers QQQ \
  --config america \
  --datasource yfinance
```

## Strategy Performance Considerations

### Strengths
- **Institutional Logic**: Based on how large players actually trade
- **Multiple Confirmation**: Requires confluence of multiple factors
- **Risk Management**: Built-in position sizing and stop losses
- **Trend Following**: Aligns with market structure and momentum
- **Adaptive**: Order blocks and FVGs update dynamically

### Limitations
- **Complexity**: Multiple components that need alignment
- **Lagging**: Structure breaks are confirmed after they occur
- **False Signals**: Market structure can give whipsaws in ranging markets
- **Parameter Sensitivity**: Many parameters that can be optimized
- **Timeframe Dependent**: Works better on higher timeframes

### Optimization Tips
1. **Backtest Multiple Timeframes**: Daily, 4H, 1H to find optimal timeframe
2. **Market Conditions**: May perform differently in trending vs ranging markets
3. **Parameter Tuning**: Adjust swing_length and structure parameters for different assets
4. **Risk Management**: Conservative position sizing is recommended initially
5. **Confluence**: Enable multiple filters for higher quality setups

## Implementation Notes

This Python implementation converts the complex Pine Script logic while maintaining the core SMC principles:

- **Swing Point Detection**: Uses lookback periods to identify significant highs/lows
- **Structure Analysis**: Tracks market structure changes and trend direction
- **Order Block Creation**: Identifies the specific candles that create order blocks
- **FVG Detection**: Implements the 3-candle gap detection logic
- **Zone Calculations**: Dynamic premium/discount zone updates
- **Risk Management**: Professional position sizing and stop loss placement

The strategy is designed to be educational and customizable, allowing traders to understand and modify the core SMC concepts for their specific needs.

## Dependencies

- pandas
- talib
- numpy
- backtesting
- connors.core.registry

## Version History

- **v1.0**: Initial implementation with core SMC concepts
  - Market structure detection (BOS/CHoCH)
  - Order blocks identification
  - Fair Value Gaps detection
  - Premium/Discount zones
  - Comprehensive risk management
  - Multiple filtering options

## License

This strategy implementation is part of the Connors Trading framework and follows the same licensing terms.