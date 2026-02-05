# Partial Elephant Bars Strategy

A Python backtesting.py implementation of the "Indicador Barra Elefante Parcial" concept, originally developed for the Profit Chart (Brazilian trading platform). This strategy detects unusually large candlesticks with strong bodies and high volume (Elephant Bars), then enters on breakouts using a dual-target partial profit system.

**Original Concept**: [Day Trading Elephants & Tails Positions](https://www.graduatetutor.com/corporate-finance-tutoring/day-trading-elephants-tails-positions/)
**Original Platform**: Profit Chart (Brazilian trading platform)
**Conversion**: Profit Chart language to Python backtesting.py implementation

## Overview

The Elephant Bar strategy identifies institutional-grade price movements -- bars with exceptional range, volume, and body-to-range ratio -- as signals of strong directional conviction. Once an Elephant Bar is detected, a pending breakout entry is placed beyond its extreme. The position is managed with a dual-target system: a partial exit at a fraction of the risk, followed by a breakeven stop adjustment on the remaining position held for a larger target.

## Strategy Logic

### What is an Elephant Bar?

An Elephant Bar is a candlestick that satisfies all of the following conditions simultaneously:

1. **Exceptional Range**: The bar's range (High - Low) exceeds `ATR(atr_period) x atr_factor`. With defaults, this means the bar must be at least 2.5 times the 14-period Average True Range.
2. **Above-Average Volume**: The bar's volume (optionally financial volume: Close x Volume) multiplied by `volume_factor` exceeds the `SMA(volume_sma_period)` of volume. With defaults, the raw volume multiplied by 2.0 must exceed the 20-period simple moving average of volume.
3. **Strong Body**: The candle body (`|Close - Open|`) represents at least `candle_body_pct` percent of the total range. With the default of 80%, this filters out doji-like bars and ensures directional conviction.
4. **Direction**: A bullish Elephant Bar has `Close > Open`. A bearish Elephant Bar has `Open > Close`.

### Entry Mechanism (Simulated Stop Orders)

Since backtesting.py does not natively support pending (stop) orders, the strategy simulates them using a state machine:

- When a **bullish** Elephant Bar is detected, a pending buy entry is set at `High + entry_distance_ticks x tick_size`.
- When a **bearish** Elephant Bar is detected (and `enable_shorts` is True), a pending sell entry is set at `Low - entry_distance_ticks x tick_size`.
- On each subsequent bar, the strategy checks whether price has exceeded the pending entry level. If it has, the entry is triggered.
- If price does not trigger the entry within `pending_timeout_bars` bars (default: 5), the pending order expires and the signal is discarded.

### Exit Mechanism (Partial Profit + OCO Simulation)

The strategy uses a dual-trade approach to implement partial profit taking, simulating OCO (One-Cancels-Other) order behavior:

**For Long Positions:**

| Component | Calculation |
|---|---|
| Stop Loss | Elephant Bar Low - `stop_distance_ticks` x `tick_size` |
| Partial Target | Entry + Risk x (`partial_gain_pct` / 100) |
| Full Target | Entry + Risk x `risk_reward_ratio` |

- 60% of the position (configurable via `partial_position_pct`) exits at the partial target.
- The remaining 40% is held for the full target.
- After the partial exit triggers, the stop loss on the remaining position moves to breakeven + `protection_distance_ticks` x `tick_size`.

**For Short Positions (mirror logic):**

| Component | Calculation |
|---|---|
| Stop Loss | Elephant Bar High + `stop_distance_ticks` x `tick_size` |
| Partial Target | Entry - Risk x (`partial_gain_pct` / 100) |
| Full Target | Entry - Risk x `risk_reward_ratio` |

- Same partial/full split with breakeven protection after the partial exit fills.

### Position Sizing

Position size is calculated based on risk per trade:

```
risk_amount = equity x (risk_per_trade / 100)
risk_per_share = |entry_price - stop_loss_price|
position_size = int(round(risk_amount / risk_per_share))
```

With the default `risk_per_trade` of 2.0%, each trade risks 2% of current equity. Position size is always converted to an integer to comply with backtesting.py requirements.

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `atr_period` | 14 | ATR calculation period for measuring bar amplitude |
| `atr_factor` | 2.5 | Multiplier applied to ATR for the elephant bar amplitude threshold |
| `volume_factor` | 2.0 | Multiplier for volume comparison against its moving average |
| `volume_sma_period` | 20 | Period for the volume simple moving average |
| `candle_body_pct` | 80.0 | Minimum body percentage of total range to qualify as elephant bar |
| `use_financial_volume` | False | Use financial volume (Close x Volume) instead of raw volume |
| `entry_distance_ticks` | 1 | Number of ticks above/below the elephant bar extreme for entry |
| `stop_distance_ticks` | 1 | Number of ticks beyond the elephant bar extreme for stop loss |
| `tick_size` | 0.01 | Minimum price increment (0.01 for US stocks, adjust for futures) |
| `pending_timeout_bars` | 5 | Number of bars before a pending entry order expires |
| `risk_reward_ratio` | 1.5 | Risk-to-reward ratio for the full target exit |
| `partial_position_pct` | 60.0 | Percentage of position allocated to the partial (first) exit |
| `partial_gain_pct` | 50.0 | Percentage of risk used to calculate the partial target distance |
| `protection_distance_ticks` | 100 | Ticks added beyond breakeven for stop protection after partial fill |
| `risk_per_trade` | 2.0 | Percentage of equity risked per trade |
| `enable_shorts` | True | Allow short (bearish) entries in addition to long entries |

### Parameter Tuning Guidelines

- **US Stocks**: Use defaults (`tick_size: 0.01`, `atr_factor: 2.5`). Consider `enable_shorts: False` for long-only equity portfolios.
- **Brazilian Mini Dollar Futures (WDOL)**: Set `tick_size: 0.5` or `tick_size: 5.0` depending on contract, `protection_distance_ticks: 20`, and consider lowering `atr_factor` to 2.0.
- **Brazilian Mini Index Futures (WIN)**: Set `tick_size: 5.0`, adjust `protection_distance_ticks` to 10-20.
- **Conservative Setup**: Use `candle_body_pct: 85.0`, `risk_per_trade: 1.0`, `enable_shorts: False`.
- **Aggressive Setup**: Use `atr_factor: 2.0`, `risk_per_trade: 3.0`, `risk_reward_ratio: 2.0`.

## Usage Examples

### Connors CLI

```bash
# Basic backtest with SPY
python -m connors.cli.backtest \
  --external-strategy /Users/mhack/Projects/connors/strategies/BR_AU_TradingBro/partial_elephant_bars.py \
  --strategy PartialElephantBars \
  --tickers SPY \
  --config america \
  --datasource yfinance \
  --start 2023-01-01 \
  --end 2023-12-31
```

```bash
# With parameter overrides for Brazilian futures
python -m connors.cli.backtest \
  --external-strategy /Users/mhack/Projects/connors/strategies/BR_AU_TradingBro/partial_elephant_bars.py \
  --strategy PartialElephantBars \
  --strategy-params "tick_size:5.0;atr_factor:2.0;protection_distance_ticks:20" \
  --tickers WDOL \
  --config brazil \
  --datasource yfinance
```

```bash
# Conservative setup (longs only, tighter body filter)
python -m connors.cli.backtest \
  --external-strategy /Users/mhack/Projects/connors/strategies/BR_AU_TradingBro/partial_elephant_bars.py \
  --strategy PartialElephantBars \
  --strategy-params "enable_shorts:False;candle_body_pct:85.0;risk_per_trade:1.0" \
  --tickers AAPL \
  --config america \
  --datasource yfinance
```

### Standalone Python

```python
from backtesting import Backtest
from partial_elephant_bars import PartialElephantBarsStrategy
import yfinance as yf

# Download data
data = yf.download("SPY", start="2023-01-01", end="2023-12-31")
data.columns = data.columns.droplevel(1)

# Run backtest with default parameters
bt = Backtest(data, PartialElephantBarsStrategy, cash=1_000_000, commission=0.002)
stats = bt.run()
print(stats)
```

```python
# Run with custom parameters
stats = bt.run(
    atr_factor=2.0,
    risk_reward_ratio=2.0,
    candle_body_pct=85.0,
    enable_shorts=False
)
print(stats)
```

## Implementation Notes

### 1. Simulated Stop Entries

Backtesting.py executes trades at the current bar's close price and does not support pending (stop) orders that trigger at a specific price level on a future bar. This strategy works around that limitation by implementing a state machine:

- **IDLE**: No signal detected. Scanning for elephant bars.
- **PENDING_LONG / PENDING_SHORT**: An elephant bar was detected. The strategy stores the entry level and checks on each subsequent bar whether the high (for longs) or low (for shorts) has exceeded that level.
- **IN_POSITION**: The pending order was triggered. The strategy manages the active position with stop loss and take profit levels.

A bar counter tracks how many bars have elapsed since the signal. If `pending_timeout_bars` is exceeded without a trigger, the state resets to IDLE.

### 2. Dual-Trade Partial Exits

Backtesting.py does not natively support partial position closes. The strategy simulates this by entering two separate trades simultaneously when a signal triggers:

- **Trade A** (partial): `partial_position_pct`% of the calculated size, with take profit at the partial target.
- **Trade B** (remainder): The remaining position, with take profit at the full target.

Both trades share the same initial stop loss. When Trade A exits at its partial target, the strategy adjusts Trade B's stop loss to breakeven plus the protection distance. This simulates OCO (One-Cancels-Other) bracket order behavior commonly available on live trading platforms.

### 3. Tick Size Configuration

The `tick_size` parameter controls the minimum price increment and directly affects entry placement, stop loss placement, and breakeven protection calculations. Correct configuration is essential:

- **US Equities**: `tick_size = 0.01` (default)
- **Brazilian Mini Dollar (WDOL)**: `tick_size = 0.5` or `tick_size = 5.0`
- **Brazilian Mini Index (WIN)**: `tick_size = 5.0`
- **US Futures (ES, NQ)**: `tick_size = 0.25`

Using an incorrect tick size will produce distorted entry/exit levels and unreliable backtest results.

### 4. Volume Calculation Options

The `use_financial_volume` parameter toggles between two volume measurement approaches:

- **Raw Volume** (`use_financial_volume = False`): Uses the standard volume column directly. Suitable for most equities and ETFs.
- **Financial Volume** (`use_financial_volume = True`): Calculates `Close x Volume`, representing the monetary value of shares traded. This matches the original Profit Chart implementation and is more appropriate for instruments where the nominal volume alone does not reflect the true activity (e.g., comparing low-priced vs high-priced stocks).

### 5. Original Source

This strategy is converted from the Profit Chart platform language implementation called "Indicador Barra Elefante Parcial." Profit Chart is a Brazilian trading platform widely used by day traders in the B3 (Brazilian Stock Exchange) market. The original implementation targets Brazilian futures contracts (mini dollar WDOL and mini index WIN), but the Python conversion generalizes the concept for any instrument supported by backtesting.py.

## Strategy Performance Considerations

### Strengths

- **Institutional Signal**: Elephant bars often represent institutional activity, providing a high-conviction directional signal.
- **Risk Management**: Built-in position sizing, stop losses, and partial profit taking protect capital systematically.
- **Partial Profit Taking**: Locking in partial gains reduces the psychological burden and protects against reversals.
- **Breakeven Protection**: Moving the stop to breakeven after the partial exit eliminates downside risk on the remaining position.
- **Configurable**: Extensive parameter set allows adaptation to different instruments, markets, and trading styles.

### Limitations

- **Signal Frequency**: Elephant bars are relatively rare events. Strategies may generate few trades over short backtest periods.
- **Simulated Orders**: Pending stop orders and partial exits are approximations. Live execution may differ from backtest results.
- **Gap Risk**: Overnight gaps can cause entries and exits at prices significantly different from the intended levels.
- **Parameter Sensitivity**: The `atr_factor` and `candle_body_pct` thresholds significantly affect signal frequency and quality.
- **Tick Size Dependency**: Incorrect tick size configuration produces unreliable results.

### Optimization Tips

1. **Start with defaults** on liquid US equities (SPY, QQQ, AAPL) to establish a baseline.
2. **Adjust `atr_factor`** between 2.0 and 3.0 to control signal frequency: lower values produce more signals, higher values filter for only the most extreme bars.
3. **Test `candle_body_pct`** between 70% and 90% to balance between signal quantity and quality.
4. **Evaluate `risk_reward_ratio`** from 1.0 to 3.0: lower ratios increase win rate at the cost of average win size.
5. **Run extended backtest periods** (3+ years) to collect statistically meaningful trade counts given the low signal frequency.

## Integration with Connors Framework

The strategy is fully compatible with the connors_trading framework:

- Registry system integration with `@registry.register_strategy("PartialElephantBars")`
- CLI backtesting support via `--external-strategy` parameter
- Parameter override system via `--strategy-params` with semicolon-separated key:value pairs
- Standard backtesting.py Strategy class inheritance
- TA-Lib integration for ATR, SMA, MAX, and MIN calculations

## Dependencies

- `pandas` - Data manipulation and time series handling
- `numpy` - Numerical calculations and array operations
- `talib` - Technical analysis functions (ATR, SMA)
- `backtesting` - Backtesting framework (Strategy base class, Backtest runner)
- `connors.core.registry` - Strategy registration for CLI discovery

## Files

- `/Users/mhack/Projects/connors/strategies/BR_AU_TradingBro/partial_elephant_bars.py` - Main strategy implementation
- `/Users/mhack/Projects/connors/strategies/BR_AU_TradingBro/README.md` - This documentation file

## References

- [Day Trading Elephants & Tails Positions](https://www.graduatetutor.com/corporate-finance-tutoring/day-trading-elephants-tails-positions/) - Original elephant bar concept
- [Profit Chart](https://www.nelogica.com.br/produtos/profitchart) - Original platform for "Indicador Barra Elefante Parcial"
- [backtesting.py Documentation](https://kernc.github.io/backtesting.py/) - Python backtesting framework
- [TA-Lib](https://ta-lib.github.io/ta-lib-python/) - Technical analysis library used for indicator calculations

## License

This strategy implementation is part of the Connors Trading framework and follows the same licensing terms.
