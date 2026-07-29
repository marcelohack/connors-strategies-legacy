"""Tests for RSI2Logic strategy logic."""

import pytest

from connors_strategies.rsi2_logic import RSI2Logic
from tests.conftest import make_snapshot


class TestRSI2LogicInit:
    def test_default_parameters(self):
        logic = RSI2Logic()
        assert logic.rsi_length == 2
        assert logic.rsi_level == 5.0
        assert logic.short_sma_length == 5
        assert logic.long_sma_length == 200

    def test_custom_parameters(self):
        logic = RSI2Logic(rsi_length=3, rsi_level=10.0, short_sma_length=10, long_sma_length=50)
        assert logic.rsi_length == 3
        assert logic.rsi_level == 10.0
        assert logic.short_sma_length == 10
        assert logic.long_sma_length == 50


class TestRSI2LogicSignals:
    def setup_method(self):
        self.logic = RSI2Logic()

    def test_hold_when_no_indicators(self):
        """Returns HOLD when indicators are missing (not enough data)."""
        snapshot = make_snapshot(close=100.0)
        assert self.logic.generate_signal(snapshot) == "HOLD"

    def test_hold_when_partial_indicators(self):
        """Returns HOLD when only some indicators are available."""
        snapshot = make_snapshot(close=100.0, rsi_2=3.0)
        assert self.logic.generate_signal(snapshot) == "HOLD"

    def test_buy_signal(self):
        """BUY when RSI < level AND close > long SMA (no position)."""
        snapshot = make_snapshot(close=210.0, rsi_2=3.0, sma_5=205.0, sma_200=200.0)
        assert self.logic.generate_signal(snapshot, has_position=False) == "BUY"

    def test_no_buy_when_rsi_above_level(self):
        """HOLD when RSI >= level (not oversold)."""
        snapshot = make_snapshot(close=210.0, rsi_2=10.0, sma_5=205.0, sma_200=200.0)
        assert self.logic.generate_signal(snapshot, has_position=False) == "HOLD"

    def test_no_buy_when_below_long_sma(self):
        """HOLD when close < long SMA (downtrend)."""
        snapshot = make_snapshot(close=190.0, rsi_2=3.0, sma_5=195.0, sma_200=200.0)
        assert self.logic.generate_signal(snapshot, has_position=False) == "HOLD"

    def test_no_buy_when_has_position(self):
        """No BUY signal when already holding a position."""
        snapshot = make_snapshot(close=210.0, rsi_2=3.0, sma_5=205.0, sma_200=200.0)
        assert self.logic.generate_signal(snapshot, has_position=True) != "BUY"

    def test_sell_signal(self):
        """SELL when close >= short SMA (with position)."""
        snapshot = make_snapshot(close=210.0, rsi_2=50.0, sma_5=205.0, sma_200=200.0)
        assert self.logic.generate_signal(snapshot, has_position=True) == "SELL"

    def test_sell_when_close_equals_short_sma(self):
        """SELL when close == short SMA exactly."""
        snapshot = make_snapshot(close=205.0, rsi_2=50.0, sma_5=205.0, sma_200=200.0)
        assert self.logic.generate_signal(snapshot, has_position=True) == "SELL"

    def test_hold_when_below_short_sma_with_position(self):
        """HOLD when close < short SMA (with position, not recovered yet)."""
        snapshot = make_snapshot(close=200.0, rsi_2=3.0, sma_5=205.0, sma_200=190.0)
        assert self.logic.generate_signal(snapshot, has_position=True) == "HOLD"

    def test_hold_no_position_no_entry(self):
        """HOLD when conditions don't trigger any signal."""
        snapshot = make_snapshot(close=210.0, rsi_2=50.0, sma_5=205.0, sma_200=200.0)
        assert self.logic.generate_signal(snapshot, has_position=False) == "HOLD"


class TestRSI2LogicCustomParams:
    def test_custom_rsi_level(self):
        """BUY with custom RSI level threshold."""
        logic = RSI2Logic(rsi_level=10.0)
        snapshot = make_snapshot(close=210.0, rsi_2=8.0, sma_5=205.0, sma_200=200.0)
        assert logic.generate_signal(snapshot, has_position=False) == "BUY"

    def test_custom_rsi_level_too_high(self):
        """No BUY when RSI is above custom level."""
        logic = RSI2Logic(rsi_level=10.0)
        snapshot = make_snapshot(close=210.0, rsi_2=12.0, sma_5=205.0, sma_200=200.0)
        assert logic.generate_signal(snapshot, has_position=False) == "HOLD"
