import pandas as pd
import talib
import numpy as np
from collections import defaultdict
from datetime import datetime, time
from backtesting import Strategy

from connors.core.registry import registry


@registry.register_strategy("VolumeByTime")
class VolumeByTimeStrategy(Strategy):
    """Volume by Time Strategy based on LuxAlgo's Volume by Time indicator

    This strategy analyzes volume patterns by time of day and generates trading signals
    based on volume anomalies compared to historical averages at the same time.

    Core Logic:
    - Tracks volume patterns by time of day (hour:minute:second)
    - Calculates average or median volume for each time slot
    - Generates buy signals when volume significantly exceeds historical average (bullish volume spike)
    - Generates sell signals when volume significantly below average or when profit target is reached
    - Uses bidirectional analysis to distinguish bullish vs bearish volume

    Entry Conditions:
    - Volume spike above threshold compared to historical average for that time
    - Bullish volume (close > open)
    - Optional: Price above moving average filter

    Exit Conditions:
    - Volume returns to normal levels
    - Profit target reached
    - Stop loss triggered
    - Time-based exit after holding period
    """

    # === Core Parameters ===
    analysis_type = "Average"  # "Average" or "Median"
    length_days = 20  # Number of days for volume averaging (0 = all available data)
    volume_threshold_multiplier = 2.0  # Volume must be X times the average to trigger entry
    min_volume_threshold = 1000  # Minimum absolute volume to consider

    # === Signal Parameters ===
    use_bidirectional = True  # Use bullish/bearish volume distinction
    bullish_volume_only = True  # Only trade on bullish volume (close > open)

    # === Filters ===
    use_price_filter = True  # Only trade when price is above MA
    price_filter_length = 50  # Moving average length for price filter

    # === Exit Parameters ===
    profit_target_pct = 5.0  # Take profit at X% gain
    stop_loss_pct = 2.0  # Stop loss at X% loss
    max_holding_bars = 10  # Maximum bars to hold position
    volume_exit_threshold = 0.8  # Exit when volume drops below X times average

    def init(self) -> None:
        """Initialize indicators and volume tracking structures."""
        # Price filter moving average
        if self.use_price_filter:
            self.price_ma = self.I(talib.SMA, self.data.Close, self.price_filter_length)

        # Volume tracking by time
        self.volume_by_time = defaultdict(list)  # time_key -> list of volumes
        self.volume_direction_by_time = defaultdict(list)  # time_key -> list of directional volumes

        # Entry tracking
        self.entry_price = None
        self.entry_bar = None
        self.last_volume_signal = 0  # Track last volume signal strength

    def _get_time_key(self, bar_index: int) -> str:
        """Get time key for current bar (hour:minute:second format)."""
        # For backtesting, we'll use a simplified approach based on bar index
        # In real implementation, this would extract actual time from timestamp
        # For now, we'll group by hour equivalent (assuming daily bars, use day of week)

        # If we have datetime index, use actual time
        if hasattr(self.data.index, 'time'):
            dt = self.data.index[bar_index]
            if hasattr(dt, 'time'):
                t = dt.time()
                return f"{t.hour:02d}{t.minute:02d}{t.second:02d}"

        # Fallback: use modulo operation to create time-like grouping
        # This creates recurring patterns that simulate intraday time cycles
        time_cycle = bar_index % 24  # 24-hour cycle simulation
        return f"{time_cycle:02d}0000"

    def _update_volume_history(self, time_key: str, volume: float, directional_volume: float) -> None:
        """Update volume history for the given time key."""
        # Add new volume data
        self.volume_by_time[time_key].append(volume)
        self.volume_direction_by_time[time_key].append(directional_volume)

        # Limit history length if specified
        if self.length_days > 0:
            max_length = self.length_days
            if len(self.volume_by_time[time_key]) > max_length:
                self.volume_by_time[time_key] = self.volume_by_time[time_key][-max_length:]
                self.volume_direction_by_time[time_key] = self.volume_direction_by_time[time_key][-max_length:]

    def _get_volume_average(self, time_key: str) -> tuple[float, float]:
        """Get volume average/median for the given time key."""
        volumes = self.volume_by_time[time_key]
        directional_volumes = self.volume_direction_by_time[time_key]

        if len(volumes) < 2:
            return 0.0, 0.0

        if self.analysis_type == "Median":
            avg_volume = np.median(volumes)
            avg_directional = np.median(directional_volumes)
        else:  # Average
            avg_volume = np.mean(volumes)
            avg_directional = np.mean(directional_volumes)

        return avg_volume, avg_directional

    def _is_bullish_volume(self) -> bool:
        """Check if current bar has bullish volume (close > open)."""
        return self.data.Close[-1] > self.data.Open[-1]

    def _calculate_volume_signal(self, current_volume: float, avg_volume: float, directional_volume: float, avg_directional: float) -> float:
        """Calculate volume signal strength."""
        if avg_volume == 0:
            return 0.0

        # Base signal from volume ratio
        volume_ratio = current_volume / avg_volume

        # Adjust for directional bias if using bidirectional analysis
        if self.use_bidirectional and avg_directional != 0:
            directional_ratio = abs(directional_volume) / abs(avg_directional) if avg_directional != 0 else 1.0
            # Weight the signal by direction strength
            if directional_volume > 0:  # Bullish volume
                volume_ratio *= directional_ratio
            else:  # Bearish volume
                volume_ratio *= directional_ratio * 0.5  # Reduce bearish signal strength

        return volume_ratio

    def next(self) -> None:
        """Main trading logic executed on each bar."""
        current_bar = len(self.data) - 1
        current_volume = self.data.Volume[-1]
        current_close = self.data.Close[-1]
        current_open = self.data.Open[-1]

        # Skip if volume is too low
        if current_volume < self.min_volume_threshold:
            return

        # Get time key for current bar
        time_key = self._get_time_key(current_bar)

        # Calculate directional volume
        directional_volume = current_volume if current_close > current_open else -current_volume

        # Update volume history
        self._update_volume_history(time_key, current_volume, directional_volume)

        # Get historical averages for this time
        avg_volume, avg_directional = self._get_volume_average(time_key)

        # Calculate volume signal strength
        volume_signal = self._calculate_volume_signal(current_volume, avg_volume, directional_volume, avg_directional)
        self.last_volume_signal = volume_signal

        # Price filter check
        price_filter_ok = True
        if self.use_price_filter and hasattr(self, 'price_ma'):
            price_filter_ok = current_close > self.price_ma[-1]

        # === EXIT LOGIC ===
        if self.position.is_long:
            # Calculate current P&L
            if self.entry_price is not None:
                pnl_pct = (current_close - self.entry_price) / self.entry_price * 100

                # Profit target
                if pnl_pct >= self.profit_target_pct:
                    self.logger.info(
                        f"🔴 SELL signal - Profit target reached ({pnl_pct:.2f}% >= {self.profit_target_pct:.2f}%)"
                    )
                    self.logger.info(
                        f"💸 EXECUTING SELL at {current_close:.2f} "
                        f"(Entry: {self.entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                    )
                    self.position.close()
                    return

                # Stop loss
                if pnl_pct <= -self.stop_loss_pct:
                    self.logger.info(
                        f"🔴 SELL signal - Stop loss triggered ({pnl_pct:.2f}% <= -{self.stop_loss_pct:.2f}%)"
                    )
                    self.logger.info(
                        f"💸 EXECUTING SELL at {current_close:.2f} "
                        f"(Entry: {self.entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                    )
                    self.position.close()
                    return

            # Time-based exit
            if self.entry_bar is not None and (current_bar - self.entry_bar) >= self.max_holding_bars:
                bars_held = current_bar - self.entry_bar
                pnl_pct = (current_close - self.entry_price) / self.entry_price * 100 if self.entry_price else 0
                self.logger.info(
                    f"🔴 SELL signal - Time-based exit ({bars_held} bars >= {self.max_holding_bars} bars)"
                )
                self.logger.info(
                    f"💸 EXECUTING SELL at {current_close:.2f} "
                    f"(Entry: {self.entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                )
                self.position.close()
                return

            # Volume-based exit (volume returns to normal)
            if volume_signal < self.volume_exit_threshold:
                pnl_pct = (current_close - self.entry_price) / self.entry_price * 100 if self.entry_price else 0
                self.logger.info(
                    f"🔴 SELL signal - Volume returned to normal ({volume_signal:.2f}x < {self.volume_exit_threshold:.2f}x)"
                )
                self.logger.info(
                    f"💸 EXECUTING SELL at {current_close:.2f} "
                    f"(Entry: {self.entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                )
                self.position.close()
                return

        # === ENTRY LOGIC ===
        if not self.position.is_long and avg_volume > 0:
            # Check volume threshold
            volume_spike = volume_signal >= self.volume_threshold_multiplier

            # Check bullish volume condition
            bullish_condition = True
            if self.bullish_volume_only:
                bullish_condition = self._is_bullish_volume()

            # Entry signal
            if volume_spike and bullish_condition and price_filter_ok:
                self.logger.info(
                    f"🟢 BUY signal - Volume spike detected ({volume_signal:.2f}x >= {self.volume_threshold_multiplier:.2f}x avg), "
                    f"Bullish volume (Close {current_close:.2f} > Open {current_open:.2f}), "
                    f"Price filter OK"
                )
                self.logger.info(f"💰 EXECUTING BUY at {current_close:.2f}")
                self.buy(size=1)
                self.entry_price = current_close
                self.entry_bar = current_bar