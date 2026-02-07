from connors_core.core.registry import registry
from backtesting import Backtest, Strategy
from backtesting.lib import crossover, FractionalBacktest

import pandas as pd
import talib


@registry.register_strategy("rbi_v3-10_20_2025.DifferentialCrossover")
class DifferentialCrossover(Strategy, FractionalBacktest):
    ema20_period = 20
    sma50_period = 50
    sma200_period = 200
    swing_window = 10
    risk_percent = 0.01
    rr_ratio = 2
    sl_percent_swing = 0.015  # 1.5% below swing low
    sl_percent_sma = 0.01     # 1% below 200 SMA

    def init(self):
        close = self.data.Close
        self.sma50 = self.I(talib.SMA, close, timeperiod=self.sma50_period)
        self.sma200 = self.I(talib.SMA, close, timeperiod=self.sma200_period)
        self.diff = self.I(lambda: self.sma50 - self.sma200)
        self.ema_diff = self.I(lambda: talib.EMA(self.diff, timeperiod=self.ema20_period))
        self.ema20p = self.I(talib.EMA, close, timeperiod=self.ema20_period)
        self.trailing_active = False
        self.initial_risk = 0
        self.current_sl = None
        print("🌙 Moon Dev: Initialized DifferentialCrossover Strategy ✨")

    def next(self):
        if len(self.data) < self.sma200_period:
            return

        # Exit logic first
        if self.position:
            # Manual stop loss check
            if self.current_sl is not None and self.data.Low[-1] <= self.current_sl:
                self.position.close()
                print(f"🌙 Moon Dev: SL hit! Price low: {self.data.Low[-1]}, SL: {self.current_sl:.2f} ✨")
                self.trailing_active = False
                self.initial_risk = 0
                self.current_sl = None
                return

            # Signal exit: Diff crosses below EMA_diff
            if (self.diff[-1] < self.ema_diff[-1] and
                self.diff[-2] >= self.ema_diff[-2]):
                self.position.close()
                print(f"🚀 Moon Dev: Exit on momentum reversal at {self.data.Close[-1]} 🌙")
                self.trailing_active = False
                self.current_sl = None
                return

            # Trailing activation and update logic
            if self.position.pl > self.initial_risk and not self.trailing_active:
                self.trailing_active = True
                print("✨ Moon Dev: Trailing stop activated 🚀")

            if self.trailing_active:
                new_sl = self.ema20p[-1]
                if new_sl > self.current_sl:
                    self.current_sl = new_sl
                    print(f"🌙 Moon Dev: Trailing SL updated to {new_sl:.2f} ✨")

        # Entry logic
        if not self.position:
            if (self.sma50[-1] < self.sma200[-1] and
                self.diff[-1] > self.ema_diff[-1] and
                self.diff[-2] <= self.ema_diff[-2]):

                entry_price = float(self.data.Close[-1])
                print(f"🌙 Moon Dev: Potential entry signal at {entry_price} 🚀")

                # Calculate swing low (past 10 bars, excluding current)
                past_lows = self.data.Low[-self.swing_window-1 : -1]
                if len(past_lows) == 0:
                    return
                recent_swing_low = float(past_lows.min())

                # Candidate stops
                sl_swing = recent_swing_low * (1 - self.sl_percent_swing)
                sl_sma = float(self.sma200[-1]) * (1 - self.sl_percent_sma)

                # Choose the valid one with smaller risk (higher SL price)
                valid_sls = []
                if sl_swing < entry_price:
                    valid_sls.append(sl_swing)
                if sl_sma < entry_price:
                    valid_sls.append(sl_sma)
                if not valid_sls:
                    print("⚠️ Moon Dev: No valid SL candidates below entry, skipping 🌙")
                    return
                sl = max(valid_sls)

                risk = entry_price - sl
                equity = float(self.equity)
                risk_amount = equity * self.risk_percent
                size = risk_amount / risk
                size = int(round(float(size)))

                if size <= 0:
                    print("⚠️ Moon Dev: Position size too small, skipping 🚀")
                    return

                tp = entry_price + self.rr_ratio * risk

                # Safeguard for invalid parameters (technical fix for potential data anomalies)
                if risk <= 0 or tp <= entry_price:
                    print(f"⚠️ Moon Dev: Invalid trade parameters - risk: {risk:.4f}, tp: {tp:.4f}, entry: {entry_price:.4f}, skipping 🌙")
                    return

                self.buy(size=size, sl=None, tp=tp)
                self.current_sl = sl
                self.initial_risk = size * risk
                self.trailing_active = False
                print(f"🌙 Moon Dev: LONG Entry! Price: {entry_price}, Size: {size}, SL: {sl:.2f}, TP: {tp:.2f}, Risk: {risk:.2f} ✨🚀")

