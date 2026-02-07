import pandas as pd
import talib
import numpy as np
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from collections import deque
from backtesting import Strategy

from connors_core.core.registry import registry


@dataclass
class SwingPoint:
    """Represents a swing high or low point"""
    index: int
    price: float
    is_high: bool
    strength: int = 1


@dataclass
class OrderBlock:
    """Represents an order block zone"""
    start_index: int
    end_index: int
    high: float
    low: float
    is_bullish: bool
    strength: int = 1
    mitigated: bool = False


@dataclass
class FairValueGap:
    """Represents a Fair Value Gap"""
    start_index: int
    high: float
    low: float
    is_bullish: bool
    filled: bool = False


@dataclass
class StructureBreak:
    """Represents a market structure break (BOS/CHoCH)"""
    index: int
    price: float
    is_bullish: bool
    is_bos: bool  # True for BOS, False for CHoCH
    previous_structure: bool  # Previous trend direction


@registry.register_strategy("SmartMoneyConcepts")
class SmartMoneyConceptsStrategy(Strategy):
    """Smart Money Concepts Trading Strategy

    This strategy implements the core Smart Money Concepts (SMC) methodology including:
    - Market Structure Analysis (BOS/CHoCH detection)
    - Order Blocks identification and trading
    - Fair Value Gaps detection
    - Premium/Discount zone analysis
    - Multi-timeframe confluence

    The strategy focuses on identifying institutional trading patterns and following
    smart money movements through price structure analysis.

    Entry Conditions:
    - Market structure break (BOS) in favor of trade direction
    - Price retraces to order block or fair value gap
    - Price in discount zone for longs, premium zone for shorts
    - Confluence of multiple SMC factors

    Exit Conditions:
    - Opposite structure break
    - Profit target based on next structure level
    - Stop loss beyond order block or structure level
    - Time-based exit if no momentum
    """

    # === Core SMC Parameters ===
    swing_length = 10  # Length for swing point detection
    structure_length = 20  # Length for structure break detection
    min_structure_strength = 3  # Minimum swing strength for valid structure

    # === Order Block Parameters ===
    enable_order_blocks = True
    max_order_blocks = 5  # Maximum number of order blocks to track
    order_block_mitigation_method = "HighLow"  # "Close" or "HighLow"
    order_block_filter_atr_multiplier = 1.5  # Filter small order blocks

    # === Fair Value Gap Parameters ===
    enable_fair_value_gaps = True
    min_fvg_size_atr_multiplier = 0.5  # Minimum FVG size relative to ATR
    max_fvg_count = 10  # Maximum FVGs to track

    # === Structure Parameters ===
    enable_bos_trading = True  # Trade on Break of Structure
    enable_choch_trading = False  # Trade on Change of Character

    # === Premium/Discount Zones ===
    enable_premium_discount = True
    lookback_period = 100  # Period for high/low calculation

    # === Risk Management ===
    risk_per_trade = 2.0  # Risk percentage per trade
    reward_risk_ratio = 2.0  # Minimum reward:risk ratio
    max_holding_bars = 50  # Maximum bars to hold position
    use_atr_stops = True  # Use ATR-based stops
    atr_stop_multiplier = 2.0  # ATR multiplier for stop loss
    atr_period = 14  # ATR calculation period

    # === Filters ===
    use_trend_filter = True  # Only trade with overall trend
    trend_ema_period = 200  # EMA period for trend determination
    min_trade_gap_bars = 5  # Minimum bars between trades

    def init(self) -> None:
        """Initialize indicators and data structures"""
        # Technical indicators
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_period)

        if self.use_trend_filter:
            self.trend_ema = self.I(talib.EMA, self.data.Close, self.trend_ema_period)

        # SMC data structures
        self.swing_points: List[SwingPoint] = []
        self.order_blocks: List[OrderBlock] = []
        self.fair_value_gaps: List[FairValueGap] = []
        self.structure_breaks: List[StructureBreak] = []

        # Trading state
        self.current_trend = None  # 1 for bullish, -1 for bearish
        self.last_structure_high = None
        self.last_structure_low = None
        self.entry_bar = None
        self.last_trade_bar = None

        # Premium/Discount levels
        self.premium_level = None
        self.discount_level = None
        self.equilibrium_level = None

    def _detect_swing_points(self, index: int) -> Optional[SwingPoint]:
        """Detect swing highs and lows"""
        if index < self.swing_length or index >= len(self.data) - self.swing_length:
            return None

        high_prices = self.data.High[index-self.swing_length:index+self.swing_length+1]
        low_prices = self.data.Low[index-self.swing_length:index+self.swing_length+1]

        current_high = self.data.High[index]
        current_low = self.data.Low[index]

        # Check for swing high
        if current_high == max(high_prices):
            # Calculate strength (how many bars on each side are lower)
            strength = 0
            for i in range(1, self.swing_length + 1):
                if (index - i >= 0 and self.data.High[index - i] < current_high and
                    index + i < len(self.data) and self.data.High[index + i] < current_high):
                    strength += 1
                else:
                    break

            if strength >= self.min_structure_strength:
                return SwingPoint(index, current_high, True, strength)

        # Check for swing low
        if current_low == min(low_prices):
            # Calculate strength
            strength = 0
            for i in range(1, self.swing_length + 1):
                if (index - i >= 0 and self.data.Low[index - i] > current_low and
                    index + i < len(self.data) and self.data.Low[index + i] > current_low):
                    strength += 1
                else:
                    break

            if strength >= self.min_structure_strength:
                return SwingPoint(index, current_low, False, strength)

        return None

    def _detect_structure_break(self, current_index: int) -> Optional[StructureBreak]:
        """Detect market structure breaks (BOS/CHoCH)"""
        if len(self.swing_points) < 2:
            return None

        # Get recent swing points
        recent_highs = [sp for sp in self.swing_points if sp.is_high and sp.index <= current_index]
        recent_lows = [sp for sp in self.swing_points if not sp.is_high and sp.index <= current_index]

        if len(recent_highs) < 1 or len(recent_lows) < 1:
            return None

        # Sort by index
        recent_highs.sort(key=lambda x: x.index, reverse=True)
        recent_lows.sort(key=lambda x: x.index, reverse=True)

        last_high = recent_highs[0]
        last_low = recent_lows[0]

        current_price = self.data.Close[current_index]

        # Bullish structure break (breaking above recent high)
        if current_price > last_high.price:
            # Determine if BOS or CHoCH
            is_bos = self.current_trend == 1  # BOS if already bullish
            previous_structure = self.current_trend == 1

            return StructureBreak(
                current_index,
                last_high.price,
                True,
                is_bos,
                previous_structure
            )

        # Bearish structure break (breaking below recent low)
        if current_price < last_low.price:
            # Determine if BOS or CHoCH
            is_bos = self.current_trend == -1  # BOS if already bearish
            previous_structure = self.current_trend == -1

            return StructureBreak(
                current_index,
                last_low.price,
                False,
                is_bos,
                previous_structure
            )

        return None

    def _create_order_block(self, structure_break: StructureBreak) -> Optional[OrderBlock]:
        """Create order block from structure break"""
        if not self.enable_order_blocks:
            return None

        # Look for the candle that caused the structure break
        break_index = structure_break.index

        # Find the last opposite color candle before the break
        search_start = max(0, break_index - 20)  # Look back up to 20 candles

        order_block_candle_index = None

        if structure_break.is_bullish:
            # For bullish break, find last bearish candle (red candle)
            for i in range(break_index - 1, search_start - 1, -1):
                if self.data.Close[i] < self.data.Open[i]:  # Red candle
                    order_block_candle_index = i
                    break
        else:
            # For bearish break, find last bullish candle (green candle)
            for i in range(break_index - 1, search_start - 1, -1):
                if self.data.Close[i] > self.data.Open[i]:  # Green candle
                    order_block_candle_index = i
                    break

        if order_block_candle_index is None:
            return None

        # Create order block from the identified candle
        ob_high = self.data.High[order_block_candle_index]
        ob_low = self.data.Low[order_block_candle_index]

        # Filter small order blocks using ATR
        current_atr = self.atr[order_block_candle_index] if order_block_candle_index < len(self.atr) else self.atr[-1]
        if current_atr > 0:
            ob_size = ob_high - ob_low
            if ob_size < current_atr * self.order_block_filter_atr_multiplier:
                return None

        return OrderBlock(
            order_block_candle_index,
            order_block_candle_index,
            ob_high,
            ob_low,
            structure_break.is_bullish,
            1,
            False
        )

    def _detect_fair_value_gap(self, current_index: int) -> Optional[FairValueGap]:
        """Detect Fair Value Gaps"""
        if not self.enable_fair_value_gaps or current_index < 2:
            return None

        # Need at least 3 candles for FVG detection
        candle1_high = self.data.High[current_index - 2]
        candle1_low = self.data.Low[current_index - 2]
        candle2_high = self.data.High[current_index - 1]  # Middle candle
        candle2_low = self.data.Low[current_index - 1]
        candle3_high = self.data.High[current_index]
        candle3_low = self.data.Low[current_index]

        # Bullish FVG: candle1.low > candle3.high (gap between 1st and 3rd candle)
        if candle1_low > candle3_high:
            gap_high = candle1_low
            gap_low = candle3_high

            # Check minimum size
            current_atr = self.atr[current_index] if current_index < len(self.atr) else self.atr[-1]
            if current_atr > 0 and (gap_high - gap_low) >= current_atr * self.min_fvg_size_atr_multiplier:
                return FairValueGap(current_index - 1, gap_high, gap_low, True, False)

        # Bearish FVG: candle1.high < candle3.low (gap between 1st and 3rd candle)
        elif candle1_high < candle3_low:
            gap_high = candle3_low
            gap_low = candle1_high

            # Check minimum size
            current_atr = self.atr[current_index] if current_index < len(self.atr) else self.atr[-1]
            if current_atr > 0 and (gap_high - gap_low) >= current_atr * self.min_fvg_size_atr_multiplier:
                return FairValueGap(current_index - 1, gap_high, gap_low, False, False)

        return None

    def _update_premium_discount_zones(self, current_index: int) -> None:
        """Update premium and discount zones"""
        if not self.enable_premium_discount:
            return

        # Calculate recent high and low
        start_index = max(0, current_index - self.lookback_period)
        recent_high = max(self.data.High[start_index:current_index + 1])
        recent_low = min(self.data.Low[start_index:current_index + 1])

        # Calculate zones
        range_size = recent_high - recent_low
        self.premium_level = recent_high - (range_size * 0.3)  # Upper 30%
        self.discount_level = recent_low + (range_size * 0.3)  # Lower 30%
        self.equilibrium_level = recent_low + (range_size * 0.5)  # Middle 50%

    def _is_in_premium_zone(self, price: float) -> bool:
        """Check if price is in premium zone"""
        return self.premium_level is not None and price >= self.premium_level

    def _is_in_discount_zone(self, price: float) -> bool:
        """Check if price is in discount zone"""
        return self.discount_level is not None and price <= self.discount_level

    def _check_order_block_mitigation(self, current_index: int, current_price: float) -> None:
        """Check if any order blocks have been mitigated"""
        for ob in self.order_blocks:
            if ob.mitigated:
                continue

            if self.order_block_mitigation_method == "Close":
                if ob.is_bullish and current_price <= ob.low:
                    ob.mitigated = True
                elif not ob.is_bullish and current_price >= ob.high:
                    ob.mitigated = True
            else:  # HighLow method
                current_high = self.data.High[current_index]
                current_low = self.data.Low[current_index]

                if ob.is_bullish and current_low <= ob.low:
                    ob.mitigated = True
                elif not ob.is_bullish and current_high >= ob.high:
                    ob.mitigated = True

    def _check_fair_value_gap_fill(self, current_index: int) -> None:
        """Check if any FVGs have been filled"""
        current_high = self.data.High[current_index]
        current_low = self.data.Low[current_index]

        for fvg in self.fair_value_gaps:
            if fvg.filled:
                continue

            # Check if current candle overlaps with FVG
            if fvg.is_bullish:
                # Bullish FVG filled when price goes back down into the gap
                if current_low <= fvg.high and current_high >= fvg.low:
                    fvg.filled = True
            else:
                # Bearish FVG filled when price goes back up into the gap
                if current_high >= fvg.low and current_low <= fvg.high:
                    fvg.filled = True

    def _get_valid_order_blocks(self, is_bullish: bool) -> List[OrderBlock]:
        """Get valid (non-mitigated) order blocks for given direction"""
        return [ob for ob in self.order_blocks
                if ob.is_bullish == is_bullish and not ob.mitigated]

    def _get_valid_fair_value_gaps(self, is_bullish: bool) -> List[FairValueGap]:
        """Get valid (non-filled) fair value gaps for given direction"""
        return [fvg for fvg in self.fair_value_gaps
                if fvg.is_bullish == is_bullish and not fvg.filled]

    def _calculate_position_size(self, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk management"""
        if stop_loss == entry_price:
            return 0.1  # Default small size if no risk calculation possible

        risk_amount = abs(entry_price - stop_loss)
        account_risk = self.equity * (self.risk_per_trade / 100)

        if risk_amount > 0:
            position_size = account_risk / risk_amount
            # Normalize position size (backtesting.py expects fractional size)
            return min(position_size / entry_price, 1.0)

        return 0.1

    def next(self) -> None:
        """Main trading logic executed on each bar"""
        current_index = len(self.data) - 1
        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]

        # Update premium/discount zones
        self._update_premium_discount_zones(current_index)

        # Detect new swing points
        swing_point = self._detect_swing_points(current_index)
        if swing_point:
            self.swing_points.append(swing_point)
            # Keep only recent swing points
            self.swing_points = self.swing_points[-50:]

        # Detect structure breaks
        structure_break = self._detect_structure_break(current_index)
        if structure_break:
            self.structure_breaks.append(structure_break)
            # Update current trend
            self.current_trend = 1 if structure_break.is_bullish else -1

            # Create order block from structure break
            if structure_break.is_bos or (not structure_break.is_bos and self.enable_choch_trading):
                order_block = self._create_order_block(structure_break)
                if order_block:
                    self.order_blocks.append(order_block)
                    # Keep only recent order blocks
                    self.order_blocks = self.order_blocks[-self.max_order_blocks:]

        # Detect Fair Value Gaps
        if self.enable_fair_value_gaps:
            fvg = self._detect_fair_value_gap(current_index)
            if fvg:
                self.fair_value_gaps.append(fvg)
                # Keep only recent FVGs
                self.fair_value_gaps = self.fair_value_gaps[-self.max_fvg_count:]

        # Update order block and FVG status
        self._check_order_block_mitigation(current_index, current_price)
        self._check_fair_value_gap_fill(current_index)

        # Trend filter
        trend_bullish = True
        if self.use_trend_filter and hasattr(self, 'trend_ema'):
            trend_bullish = current_price > self.trend_ema[-1]

        # === EXIT LOGIC ===
        if self.position:
            # Time-based exit
            if self.entry_bar and (current_index - self.entry_bar) >= self.max_holding_bars:
                bars_held = current_index - self.entry_bar
                entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
                if entry_price:
                    pnl_pct = ((current_price - entry_price) / entry_price * 100)
                    self.logger.info(
                        f"🔴 SELL signal - Time-based exit ({bars_held} bars >= {self.max_holding_bars} bars)"
                    )
                    self.logger.info(
                        f"💸 EXECUTING SELL at {current_price:.2f} "
                        f"(Entry: {entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                    )
                else:
                    self.logger.info(
                        f"🔴 SELL signal - Time-based exit ({bars_held} bars >= {self.max_holding_bars} bars)"
                    )
                    self.logger.info(f"💸 EXECUTING SELL at {current_price:.2f}")
                self.position.close()
                return

            # Structure-based exit (opposite structure break)
            if structure_break:
                if self.position.is_long and not structure_break.is_bullish:
                    entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
                    if entry_price:
                        pnl_pct = ((current_price - entry_price) / entry_price * 100)
                        self.logger.info(
                            f"🔴 SELL signal - Bearish structure break detected"
                        )
                        self.logger.info(
                            f"💸 EXECUTING SELL at {current_price:.2f} "
                            f"(Entry: {entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                        )
                    else:
                        self.logger.info(f"🔴 SELL signal - Bearish structure break detected")
                        self.logger.info(f"💸 EXECUTING SELL at {current_price:.2f}")
                    self.position.close()
                    return
                elif self.position.is_short and structure_break.is_bullish:
                    entry_price = self.position.entry_price if hasattr(self.position, "entry_price") else None
                    if entry_price:
                        pnl_pct = ((entry_price - current_price) / entry_price * 100)
                        self.logger.info(
                            f"🔴 COVER signal - Bullish structure break detected"
                        )
                        self.logger.info(
                            f"💸 EXECUTING COVER at {current_price:.2f} "
                            f"(Entry: {entry_price:.2f}, P&L: {pnl_pct:.2f}%)"
                        )
                    else:
                        self.logger.info(f"🔴 COVER signal - Bullish structure break detected")
                        self.logger.info(f"💸 EXECUTING COVER at {current_price:.2f}")
                    self.position.close()
                    return

        # === ENTRY LOGIC ===
        if not self.position:
            # Minimum gap between trades
            if (self.last_trade_bar and
                current_index - self.last_trade_bar < self.min_trade_gap_bars):
                return

            # Look for bullish setups
            if (self.enable_bos_trading and self.current_trend == 1 and trend_bullish):
                # Check for retracement to order block or FVG in discount zone
                valid_obs = self._get_valid_order_blocks(True)
                valid_fvgs = self._get_valid_fair_value_gaps(True)

                entry_signal = False
                entry_zone_low = None

                # Check order block retracement
                for ob in valid_obs:
                    if ob.low <= current_low <= ob.high:
                        if self._is_in_discount_zone(current_price):
                            entry_signal = True
                            entry_zone_low = ob.low
                            break

                # Check FVG retracement
                if not entry_signal:
                    for fvg in valid_fvgs:
                        if fvg.low <= current_low <= fvg.high:
                            if self._is_in_discount_zone(current_price):
                                entry_signal = True
                                entry_zone_low = fvg.low
                                break

                if entry_signal and entry_zone_low:
                    # Calculate stop loss and take profit
                    if self.use_atr_stops:
                        stop_loss = entry_zone_low - (self.atr[-1] * self.atr_stop_multiplier)
                    else:
                        stop_loss = entry_zone_low

                    # Take profit based on reward:risk ratio
                    risk = current_price - stop_loss
                    take_profit = current_price + (risk * self.reward_risk_ratio)

                    # Calculate position size
                    size = self._calculate_position_size(current_price, stop_loss)

                    if size > 0:
                        self.logger.info(
                            f"🟢 BUY signal - Bullish structure, retracement to order block/FVG in discount zone"
                        )
                        self.logger.info(
                            f"💰 EXECUTING BUY at {current_price:.2f} (SL: {stop_loss:.2f}, TP: {take_profit:.2f}, R:R {self.reward_risk_ratio:.1f})"
                        )
                        self.buy(size=size, sl=stop_loss, tp=take_profit)
                        self.entry_bar = current_index
                        self.last_trade_bar = current_index

            # Look for bearish setups
            elif (self.enable_bos_trading and self.current_trend == -1 and not trend_bullish):
                # Check for retracement to order block or FVG in premium zone
                valid_obs = self._get_valid_order_blocks(False)
                valid_fvgs = self._get_valid_fair_value_gaps(False)

                entry_signal = False
                entry_zone_high = None

                # Check order block retracement
                for ob in valid_obs:
                    if ob.low <= current_high <= ob.high:
                        if self._is_in_premium_zone(current_price):
                            entry_signal = True
                            entry_zone_high = ob.high
                            break

                # Check FVG retracement
                if not entry_signal:
                    for fvg in valid_fvgs:
                        if fvg.low <= current_high <= fvg.high:
                            if self._is_in_premium_zone(current_price):
                                entry_signal = True
                                entry_zone_high = fvg.high
                                break

                if entry_signal and entry_zone_high:
                    # Calculate stop loss and take profit
                    if self.use_atr_stops:
                        stop_loss = entry_zone_high + (self.atr[-1] * self.atr_stop_multiplier)
                    else:
                        stop_loss = entry_zone_high

                    # Take profit based on reward:risk ratio
                    risk = stop_loss - current_price
                    take_profit = current_price - (risk * self.reward_risk_ratio)

                    # Calculate position size
                    size = self._calculate_position_size(current_price, stop_loss)

                    if size > 0:
                        self.logger.info(
                            f"🔴 SHORT signal - Bearish structure, retracement to order block/FVG in premium zone"
                        )
                        self.logger.info(
                            f"💰 EXECUTING SHORT at {current_price:.2f} (SL: {stop_loss:.2f}, TP: {take_profit:.2f}, R:R {self.reward_risk_ratio:.1f})"
                        )
                        self.sell(size=size, sl=stop_loss, tp=take_profit)
                        self.entry_bar = current_index
                        self.last_trade_bar = current_index