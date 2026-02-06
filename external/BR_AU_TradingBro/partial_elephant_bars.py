"""
Partial Elephant Bars Strategy

Detects Elephant Bars -- unusually large candles with strong bodies and high volume --
and trades breakouts from them using a partial profit management system with dual trades.

An Elephant Bar is identified when ALL three conditions are met:
    1. Amplitude: (High - Low) > ATR(14) * atr_factor
    2. Volume:    current_volume * volume_factor > SMA(volume, 20)
    3. Body:      |Close - Open| / (High - Low) * 100 > candle_body_pct

Once detected, the strategy places a pending entry order:
    - Bullish elephant bar: pending long entry above the high
    - Bearish elephant bar: pending short entry below the low

Entry execution uses a dual-trade approach for partial profit management:
    - Trade 1 (partial_position_pct): exits at partial_gain_pct of risk distance
    - Trade 2 (remaining): exits at full risk_reward_ratio target
    - After partial exit, the remaining trade's stop is moved to breakeven + protection

Parameters:
    atr_period (int): ATR calculation period (default: 14)
    atr_factor (float): Multiplier for elephant bar amplitude threshold (default: 2.5)
    volume_factor (float): Volume comparison multiplier (default: 2.0)
    volume_sma_period (int): Volume moving average period (default: 20)
    candle_body_pct (float): Minimum body percentage of total range (default: 80.0)
    use_financial_volume (bool): Use Close*Volume instead of Volume (default: False)
    entry_distance_ticks (int): Ticks above/below elephant bar for entry (default: 1)
    stop_distance_ticks (int): Ticks beyond elephant bar for stop (default: 1)
    tick_size (float): Minimum price increment (default: 0.01)
    pending_timeout_bars (int): Bars before pending entry expires (default: 5)
    risk_reward_ratio (float): Full target R:R ratio (default: 1.5)
    partial_position_pct (float): Percent of position for partial exit (default: 60.0)
    partial_gain_pct (float): Percent of risk distance for partial target (default: 50.0)
    protection_distance_ticks (int): Breakeven protection distance after partial (default: 100)
    risk_per_trade (float): Percent of equity risked per trade (default: 2.0)
    enable_shorts (bool): Allow short entries (default: True)

Ideal Market:
    Works best on liquid instruments with clear directional moves and volume spikes.
    Elephant bars represent institutional participation and tend to produce continuation.

Suggested Timeframe:
    15m, 1h, or daily

Original Source:
    Converted from Profit Chart (Nelogica) language implementation by BR_AU TradingBro.
"""

import pandas as pd
import numpy as np
import talib
from backtesting import Strategy
from connors.core.registry import registry


# ===========================================================================
# Helper functions for self.I() indicator wrapping
# ===========================================================================

def _compute_body_ratio(open_arr, high_arr, low_arr, close_arr):
    """Compute candle body ratio as percentage of total range.

    Returns an array where each element is:
        |close - open| / (high - low) * 100
    Division by zero (doji with high == low) returns 0.0.
    """
    body = np.abs(close_arr - open_arr)
    total_range = high_arr - low_arr
    ratio = np.zeros_like(body, dtype=float)
    mask = total_range > 0
    ratio[mask] = body[mask] / total_range[mask] * 100.0
    return ratio


def _compute_financial_volume(close_arr, volume_arr):
    """Compute financial volume (price * volume)."""
    return close_arr * volume_arr


def _compute_vol_sma(volume_arr, period):
    """Compute SMA of a volume series."""
    return talib.SMA(volume_arr.astype(float), timeperiod=period)


def _compute_fin_vol_sma(close_arr, volume_arr, period):
    """Compute SMA of financial volume (close * volume)."""
    fin_vol = close_arr * volume_arr
    return talib.SMA(fin_vol.astype(float), timeperiod=period)


# ===========================================================================
# Strategy
# ===========================================================================

@registry.register_strategy("PartialElephantBars")
class PartialElephantBarsStrategy(Strategy):
    """Partial Elephant Bars Strategy

    Detects unusually large candles (elephant bars) with strong bodies and
    high volume, then trades breakouts using dual-trade partial profit management.
    """

    # === Indicator Parameters ===
    atr_period = 14               # ATR calculation period
    atr_factor = 2.5              # Multiplier for elephant bar amplitude threshold
    volume_factor = 2.0           # Volume comparison multiplier
    volume_sma_period = 20        # Volume moving average period
    candle_body_pct = 80.0        # Minimum body percentage of total range
    use_financial_volume = False  # If True, use Close*Volume instead of Volume

    # === Entry Parameters ===
    entry_distance_ticks = 1      # Ticks above/below elephant bar for entry trigger
    stop_distance_ticks = 1       # Ticks beyond elephant bar for stop placement
    tick_size = 0.01              # Minimum price increment (0.01 for stocks)
    pending_timeout_bars = 5      # Bars before pending entry expires

    # === Exit Parameters ===
    risk_reward_ratio = 1.5       # Full target R:R ratio
    partial_position_pct = 60.0   # Percent of position for partial exit
    partial_gain_pct = 50.0       # Percent of risk distance for partial target
    protection_distance_ticks = 100  # Breakeven protection distance after partial

    # === Risk Management ===
    risk_per_trade = 2.0          # Percent of equity risked per trade
    enable_shorts = True          # Allow short entries

    def init(self):
        """Initialize indicators and state variables.

        Indicators (all wrapped with self.I()):
            - ATR: Average True Range for amplitude check
            - Volume SMA: Moving average of volume (or financial volume) for
              volume spike detection
            - Body Ratio: Precomputed candle body percentage for each bar
        """
        # -- ATR indicator --
        self.atr = self.I(
            talib.ATR,
            self.data.High,
            self.data.Low,
            self.data.Close,
            timeperiod=self.atr_period,
            name='ATR'
        )

        # -- Volume SMA indicator (handles financial volume toggle) --
        if self.use_financial_volume:
            self.vol_sma = self.I(
                lambda c, v: _compute_fin_vol_sma(c, v, self.volume_sma_period),
                self.data.Close,
                self.data.Volume,
                name='FinVolSMA'
            )
        else:
            self.vol_sma = self.I(
                lambda v: _compute_vol_sma(v, self.volume_sma_period),
                self.data.Volume,
                name='VolSMA'
            )

        # -- Candle body ratio indicator --
        self.body_ratio = self.I(
            _compute_body_ratio,
            self.data.Open,
            self.data.High,
            self.data.Low,
            self.data.Close,
            name='BodyRatio'
        )

        # -- Pending entry state --
        self.pending_long_entry = None
        self.pending_short_entry = None
        self.pending_stop_loss = None
        self.pending_entry_bar = None
        self.elephant_bar_high = None
        self.elephant_bar_low = None

        # -- Position state --
        self.entry_price = None
        self.entry_bar = None

        # -- Partial exit tracking --
        self.partial_target = None
        self.full_target = None
        self.stop_loss = None
        self.partial_closed = False
        self.targets_set = False
        self.initial_trade_count = 0
        self._is_long_entry = True

    # ===================================================================
    # Helper methods
    # ===================================================================

    def _get_volume(self, idx):
        """Return current volume at index, adjusted for financial volume toggle.

        Args:
            idx: Bar index to retrieve volume for.

        Returns:
            float: Raw volume or financial volume (close * volume) at idx.
        """
        if self.use_financial_volume:
            return float(self.data.Close[idx]) * float(self.data.Volume[idx])
        return float(self.data.Volume[idx])

    def _ticks_to_price(self, ticks):
        """Convert a number of ticks to a price distance.

        Args:
            ticks: Number of ticks.

        Returns:
            float: Price distance equal to ticks * tick_size.
        """
        return ticks * self.tick_size

    # ===================================================================
    # Elephant bar detection
    # ===================================================================

    def _is_elephant_bar(self, idx):
        """Detect whether the bar at idx is an elephant bar.

        Checks three conditions:
            1. Amplitude: (high - low) > ATR * atr_factor
            2. Volume: current_volume * volume_factor > volume SMA
            3. Body: body_ratio > candle_body_pct

        Args:
            idx: Bar index to check (relative to data, use -1 for current bar).

        Returns:
            tuple: (is_elephant: bool, is_bullish: bool)
                is_elephant -- True if all three conditions are met.
                is_bullish  -- True if close > open (bullish), False if bearish.
                               Only meaningful when is_elephant is True.
        """
        # Ensure enough data for ATR warmup
        current_bar = len(self.data) - 1
        if current_bar < self.atr_period:
            return False, False

        # Read indicator values at the given index
        atr_val = self.atr[idx]
        vol_sma_val = self.vol_sma[idx]
        body_ratio_val = self.body_ratio[idx]

        # Guard against NaN values during warmup
        if (np.isnan(atr_val) or np.isnan(vol_sma_val) or np.isnan(body_ratio_val)):
            return False, False

        # ATR must be positive for a valid comparison
        if atr_val <= 0:
            return False, False

        # Read OHLC values at index
        high = float(self.data.High[idx])
        low = float(self.data.Low[idx])
        close = float(self.data.Close[idx])
        open_price = float(self.data.Open[idx])

        # -- Condition 1: Amplitude check --
        amplitude = high - low
        if amplitude <= atr_val * self.atr_factor:
            return False, False

        # -- Condition 2: Volume check --
        # Original: volume_ajustado > media(20, volume)
        # Where volume_ajustado = volume * volume_factor (inverted comparison)
        current_vol = self._get_volume(idx)
        if current_vol * self.volume_factor <= vol_sma_val:
            return False, False

        # -- Condition 3: Body ratio check --
        if body_ratio_val <= self.candle_body_pct:
            return False, False

        # -- Direction --
        is_bullish = close > open_price

        return True, is_bullish

    # ===================================================================
    # Entry detection and pending order setup
    # ===================================================================

    def _detect_and_setup_pending(self, current_bar):
        """Check current bar for elephant bar and set up pending entry.

        For a bullish elephant bar:
            - Pending long entry at high + entry_distance_ticks * tick_size
            - Stop loss at low - stop_distance_ticks * tick_size

        For a bearish elephant bar (if shorts enabled):
            - Pending short entry at low - entry_distance_ticks * tick_size
            - Stop loss at high + stop_distance_ticks * tick_size

        Args:
            current_bar: Index of the current bar.
        """
        is_elephant, is_bullish = self._is_elephant_bar(-1)

        if not is_elephant:
            return

        high = float(self.data.High[-1])
        low = float(self.data.Low[-1])
        entry_offset = self._ticks_to_price(self.entry_distance_ticks)
        stop_offset = self._ticks_to_price(self.stop_distance_ticks)

        if is_bullish:
            # Bullish elephant bar: set up pending long
            self.pending_long_entry = high + entry_offset
            self.pending_stop_loss = low - stop_offset
            self.pending_entry_bar = current_bar
            self.elephant_bar_high = high
            self.elephant_bar_low = low
        elif self.enable_shorts:
            # Bearish elephant bar: set up pending short
            self.pending_short_entry = low - entry_offset
            self.pending_stop_loss = high + stop_offset
            self.pending_entry_bar = current_bar
            self.elephant_bar_high = high
            self.elephant_bar_low = low

    # ===================================================================
    # Pending entry management
    # ===================================================================

    def _check_pending_entries(self, current_bar):
        """Check if a pending entry should be triggered or expired.

        Expiry: if more than pending_timeout_bars have passed since the
        elephant bar was detected, the pending order is cancelled.

        Trigger:
            - Long: current high >= pending_long_entry price
            - Short: current low <= pending_short_entry price

        Args:
            current_bar: Index of the current bar.
        """
        # Check timeout
        if self.pending_entry_bar is not None:
            bars_elapsed = current_bar - self.pending_entry_bar
            if bars_elapsed > self.pending_timeout_bars:
                self._clear_pending()
                return

        current_high = float(self.data.High[-1])
        current_low = float(self.data.Low[-1])

        # Check long trigger
        if self.pending_long_entry is not None:
            if current_high >= self.pending_long_entry:
                self._execute_long_entry()
                return

        # Check short trigger
        if self.pending_short_entry is not None:
            if current_low <= self.pending_short_entry:
                self._execute_short_entry()
                return

    # ===================================================================
    # Trade execution with dual-trade partial profit
    # ===================================================================

    def _execute_long_entry(self):
        """Execute a long entry using the dual-trade partial profit approach.

        Enters two trades with SL only. Take profit levels are set on the
        next bar via _set_targets_from_fill() once actual fill prices are
        known, avoiding TP < fill issues from gap openings.

        Position sizing is based on risk_per_trade percent of equity divided
        by the risk distance (trigger - stop).
        """
        trigger_price = self.pending_long_entry
        stop_loss = self.pending_stop_loss
        risk = trigger_price - stop_loss

        if risk <= 0:
            self._clear_pending()
            return

        # Position sizing based on risk, capped to available equity
        risk_amount = self.equity * (self.risk_per_trade / 100.0)
        total_size = risk_amount / risk
        max_shares = int(self.equity * 0.95 / trigger_price)
        total_size = min(total_size, max_shares)

        if total_size < 2:
            self._clear_pending()
            return

        # Split into partial and remaining
        partial_size = max(1, int(total_size * self.partial_position_pct / 100.0))
        remaining_size = max(1, int(total_size - partial_size))

        # Execute dual trades with SL only (TP set after fill)
        self.buy(size=partial_size, sl=stop_loss)
        self.buy(size=remaining_size, sl=stop_loss)

        # Track position state (targets set after fill in _set_targets_from_fill)
        self.entry_price = None  # will be set from actual fill
        self.entry_bar = len(self.data) - 1
        self.stop_loss = stop_loss
        self.partial_target = None
        self.full_target = None
        self.partial_closed = False
        self.targets_set = False
        self.initial_trade_count = 2
        self._is_long_entry = True

        self._clear_pending()

    def _execute_short_entry(self):
        """Execute a short entry using the dual-trade partial profit approach.

        Enters two trades with SL only. Take profit levels are set on the
        next bar via _set_targets_from_fill() once actual fill prices are
        known, avoiding TP issues from gap openings.

        Position sizing is based on risk_per_trade percent of equity divided
        by the risk distance (stop - trigger).
        """
        trigger_price = self.pending_short_entry
        stop_loss = self.pending_stop_loss
        risk = stop_loss - trigger_price

        if risk <= 0:
            self._clear_pending()
            return

        # Position sizing based on risk, capped to available equity
        risk_amount = self.equity * (self.risk_per_trade / 100.0)
        total_size = risk_amount / risk
        max_shares = int(self.equity * 0.95 / trigger_price)
        total_size = min(total_size, max_shares)

        if total_size < 2:
            self._clear_pending()
            return

        # Split into partial and remaining
        partial_size = max(1, int(total_size * self.partial_position_pct / 100.0))
        remaining_size = max(1, int(total_size - partial_size))

        # Execute dual trades with SL only (TP set after fill)
        self.sell(size=partial_size, sl=stop_loss)
        self.sell(size=remaining_size, sl=stop_loss)

        # Track position state (targets set after fill in _set_targets_from_fill)
        self.entry_price = None  # will be set from actual fill
        self.entry_bar = len(self.data) - 1
        self.stop_loss = stop_loss
        self.partial_target = None
        self.full_target = None
        self.partial_closed = False
        self.targets_set = False
        self.initial_trade_count = 2
        self._is_long_entry = False

        self._clear_pending()

    # ===================================================================
    # Exit management
    # ===================================================================

    def _set_targets_from_fill(self):
        """Set TP levels on trades based on actual fill prices.

        Called on the first bar after entry when trades have filled and
        actual entry prices are available. This avoids the problem of
        calculating targets from the trigger price when the actual fill
        (at next bar's open) may differ significantly.
        """
        trades = list(self.trades)
        if not trades:
            return

        # Use the first trade's actual fill price
        actual_entry = trades[0].entry_price
        self.entry_price = actual_entry

        if self._is_long_entry:
            risk = actual_entry - self.stop_loss
            if risk <= 0:
                # Stop is at or above fill — close immediately
                self.position.close()
                self._reset_state()
                return

            partial_target = actual_entry + risk * (self.partial_gain_pct / 100.0)
            full_target = actual_entry + risk * self.risk_reward_ratio
        else:
            risk = self.stop_loss - actual_entry
            if risk <= 0:
                # Stop is at or below fill — close immediately
                self.position.close()
                self._reset_state()
                return

            partial_target = actual_entry - risk * (self.partial_gain_pct / 100.0)
            full_target = actual_entry - risk * self.risk_reward_ratio

        # Assign TP: larger trade gets partial target, smaller gets full target
        sorted_trades = sorted(trades, key=lambda t: abs(t.size), reverse=True)
        sorted_trades[0].tp = partial_target
        if len(sorted_trades) > 1:
            sorted_trades[1].tp = full_target

        self.partial_target = partial_target
        self.full_target = full_target
        self.targets_set = True

    def _manage_exits(self):
        """Manage open trades: set targets from fill, detect partial exit, adjust stops.

        On the first bar after entry, sets TP levels based on actual fill prices.
        After the partial trade is auto-closed by its TP, the remaining
        trade's stop loss is moved to breakeven plus a protection distance.
        """
        # Phase 1: Set targets from actual fill prices (first bar after entry)
        if not self.targets_set:
            self._set_targets_from_fill()
            return

        # Phase 2: Detect partial exit and adjust remaining stop
        if self.position.is_long:
            active_long_trades = [t for t in self.trades if t.is_long]
            if (len(active_long_trades) < self.initial_trade_count
                    and not self.partial_closed):
                # Partial trade was closed by its TP
                self.partial_closed = True
                protection = self._ticks_to_price(self.protection_distance_ticks)
                new_stop = self.entry_price + protection
                for t in active_long_trades:
                    t.sl = new_stop

        elif self.position.is_short:
            active_short_trades = [t for t in self.trades if t.is_short]
            if (len(active_short_trades) < self.initial_trade_count
                    and not self.partial_closed):
                # Partial trade was closed by its TP
                self.partial_closed = True
                protection = self._ticks_to_price(self.protection_distance_ticks)
                new_stop = self.entry_price - protection
                for t in active_short_trades:
                    t.sl = new_stop

    # ===================================================================
    # State management helpers
    # ===================================================================

    def _clear_pending(self):
        """Clear all pending entry state variables."""
        self.pending_long_entry = None
        self.pending_short_entry = None
        self.pending_stop_loss = None
        self.pending_entry_bar = None
        self.elephant_bar_high = None
        self.elephant_bar_low = None

    def _reset_state(self):
        """Reset all position tracking state after a trade is fully closed."""
        self.entry_price = None
        self.entry_bar = None
        self.partial_target = None
        self.full_target = None
        self.stop_loss = None
        self.partial_closed = False
        self.targets_set = False
        self.initial_trade_count = 0
        self._is_long_entry = True

    # ===================================================================
    # Main trading loop
    # ===================================================================

    def next(self):
        """Execute trading logic on each bar.

        Flow:
            1. If in a position, manage exits (partial profit, stop adjustment)
            2. If pending entry exists, check for trigger or expiration
            3. If no position and no pending, scan for new elephant bars
        """
        current_bar = len(self.data) - 1

        # === EXIT LOGIC (managed by sl/tp on individual trades) ===
        if self.position:
            self._manage_exits()
            return

        # Reset state when flat (position was closed by SL/TP automatically)
        if self.entry_bar is not None and not self.position:
            self._reset_state()

        # === CHECK PENDING ENTRIES ===
        if (self.pending_long_entry is not None
                or self.pending_short_entry is not None):
            self._check_pending_entries(current_bar)
            return

        # === DETECT NEW ELEPHANT BARS ===
        self._detect_and_setup_pending(current_bar)


# ===========================================================================
# Standalone test
# ===========================================================================

if __name__ == "__main__":
    """
    Standalone backtest for the Partial Elephant Bars strategy.

    Execute this file directly to test:
        python partial_elephant_bars.py
    """
    from backtesting import Backtest
    import yfinance as yf

    print("=" * 80)
    print("PARTIAL ELEPHANT BARS STRATEGY - Backtest")
    print("=" * 80)

    # Download data from Yahoo Finance
    print("\nDownloading data from Yahoo Finance...")
    ticker = "SPY"
    start_date = "2022-01-01"
    end_date = "2024-12-31"

    data = yf.download(ticker, start=start_date, end=end_date)

    # Clean and prepare data
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data.columns = data.columns.str.strip().str.lower()
    data = data.drop(
        columns=[col for col in data.columns if 'unnamed' in col.lower()],
        errors='ignore'
    )
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

    print(f"Data loaded: {len(data)} bars from {data.index[0]} to {data.index[-1]}")

    # Configure and run backtest
    # NOTE: hedging=True is required for the dual-trade partial profit approach
    print("\nRunning backtest...")
    bt = Backtest(
        data,
        PartialElephantBarsStrategy,
        cash=100_000,
        commission=0.002,
        hedging=True,
        exclusive_orders=False,
        finalize_trades=True,
    )

    # Run with relaxed params for more signals on daily SPY
    stats = bt.run(atr_factor=1.5, candle_body_pct=60.0)

    # Display results
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print(stats)

    print("\n" + "=" * 80)
    print("STRATEGY PARAMETERS")
    print("=" * 80)
    print(stats._strategy)

    # Display trade details if any
    if hasattr(stats, '_trades') and len(stats._trades) > 0:
        print("\n" + "=" * 80)
        print(f"TRADE DETAILS ({len(stats._trades)} trades)")
        print("=" * 80)
        print(stats._trades.to_string())
