from backtesting import Backtest, Strategy
import numpy as np
import pandas as pd
import talib

# class HiLo3DailyStrategy(Strategy):
#     """
#     Setup baseado no indicador Hi/Lo (período 3) para timeframe diário.
#     - Entrada: breakout de alta quando o fechamento atual ultrapassa a máxima Hi(3) dos 3 candles anteriores (Hi calculado sem look-ahead).
#     - Saída por inversão do Hi/Lo: fechamento abaixo do Lo(3) (mínima dos 3 candles anteriores).
#     - Apenas compras.
#     - Stop inicial: 10% abaixo do preço de entrada.
#     - Se após pelo menos 1 dia de operação a posição estiver com lucro > 1.5%,
#       mover o stop para proteger 0.5% de ganho (stop = entry_price * 1.005).
#     - Stop móvel simulado (self.last_stop) — fecha manualmente quando low < last_stop.
#     """

#     def init(self):
#         # Hi(3) dos 3 períodos anteriores (sem look-ahead): rolling max com shift(1)
#         self.hi3 = self.I(lambda highs: pd.Series(highs).rolling(3).max().shift(1).values, self.data.High)
#         # Lo(3) dos 3 períodos anteriores (sem look-ahead): rolling min com shift(1)
#         self.lo3 = self.I(lambda lows: pd.Series(lows).rolling(3).min().shift(1).values, self.data.Low)

#         # Variáveis para simular stop móvel / controle da operação
#         self.last_stop = None          # valor atual do stop simulado
#         self.entry_price = None        # preço de entrada registrado
#         self.entry_idx = None          # índice (barra) de entrada

#     def next(self):
#         close = self.data.Close
#         low = self.data.Low
#         hi3 = self.hi3
#         lo3 = self.lo3

#         # índice da barra atual
#         cur_idx = len(close) - 1

#         # Entradas (apenas se não há posição aberta)
#         if not self.position:
#             if np.isfinite(hi3[-1]) and close[-1] > hi3[-1]:
#                 # compra no fechamento do candle do breakout
#                 self.buy()
#                 # registra parâmetros da operação
#                 self.entry_price = float(close[-1])
#                 self.entry_idx = cur_idx
#                 # stop inicial 10% abaixo da entrada
#                 self.last_stop = self.entry_price * (1 - 0.10)
#             return

#         # Se chegou aqui, há posição aberta -> gerenciar stop móvel simulado e sinais de saída
#         if self.entry_price is None or self.entry_idx is None:
#             # segurança: se não tivermos dados de entrada, nada a fazer
#             return

#         # 1) Fechamento por inversão do Hi/Lo (venda): fechar se fechamento atual < Lo3
#         if np.isfinite(lo3[-1]) and close[-1] < lo3[-1]:
#             self.position.close()
#             # limpa estados da operação
#             self.entry_price = None
#             self.entry_idx = None
#             self.last_stop = None
#             return

#         bars_in_trade = cur_idx - self.entry_idx
#         unrealized_gain = (float(close[-1]) / self.entry_price) - 1.0  # em fração (0.015 = 1.5%)

#         # Se após ao menos 1 dia em trade o ganho for > 1.5%, mover stop para entry +0.5%
#         if bars_in_trade >= 1 and unrealized_gain > 0.015:
#             protect_stop = self.entry_price * (1 + 0.005)  # 0.5% acima da entrada
#             # ajusta o stop apenas para cima
#             if self.last_stop is None or protect_stop > self.last_stop:
#                 self.last_stop = protect_stop

#         # Fecha posição manualmente se o preço tocar/perder o stop simulado
#         if self.last_stop is not None and low[-1] < self.last_stop:
#             self.position.close()
#             # limpa estados da operação
#             self.entry_price = None
#             self.entry_idx = None
#             self.last_stop = None


class HiLo3DailyStrategy(Strategy):
    """
    Setup Hi/Lo(3) diário – apenas compras
    - Entrada: fechamento > Hi(3) dos 3 candles anteriores (sem look-ahead).
    - Saída por inversão: fechamento < Lo(3) (mínima dos 3 anteriores).
    - Stop inicial: 10% abaixo da entrada (simulado em self.last_stop).
    - Proteção: após >=1 dia e lucro >1,5%, move stop para +0,5% acima da entrada.
    - Stop móvel por volatilidade (ATR ou σ diário), sempre apertando (nunca alargando).
    """

    # ---------- Parâmetros de trailing ----------
    method = 'ATR'        # 'ATR' ou 'STD' (σ diário)
    atr_period = 14
    atr_mult   = 2.0

    vol_window = 20       # janela p/ sigma diário
    vol_mult   = 2.0

    only_trail_in_profit = True  # só traciona stop se trade estiver positivo

    def init(self):
        # Hi(3) e Lo(3) sem look-ahead (rolling de 3 com shift de 1)
        self.hi3 = self.I(lambda highs: pd.Series(highs).rolling(3).max().shift(1).values,
                          self.data.High)
        self.lo3 = self.I(lambda lows:  pd.Series(lows).rolling(3).min().shift(1).values,
                          self.data.Low)

        # Estados da operação
        self.last_stop = None          # nível atual do stop simulado
        self.entry_price = None        # preço de entrada registrado
        self.entry_idx = None          # índice (barra) de entrada

        # ----- Indicadores de volatilidade -----
        self._init_vol_indicators()

    # ----------------- Indicadores de volatilidade -----------------
    def _init_vol_indicators(self):
        close = self.data.Close
        high  = self.data.High
        low   = self.data.Low

        # ATR: amplitude média verdadeira (inclui gaps)
        self._atr = self.I(lambda h, l, c: talib.ATR(h, l, c, timeperiod=self.atr_period),
                           high, low, close)

        # σ diário: desvio-padrão dos retornos log (não anualizado)
        def rolling_sigma_daily(x):
            r = np.empty_like(x)
            r[:] = np.nan
            r[1:] = np.log(x[1:] / x[:-1])
            return talib.STDDEV(r, timeperiod=self.vol_window, nbdev=1)

        self._sigma_d = self.I(rolling_sigma_daily, close)

    def _candidate_trailing_level(self):
        """Calcula o novo nível candidato de stop por volatilidade para posição comprada."""
        close = float(self.data.Close[-1])
        m = (self.method or 'ATR').upper()

        if m == 'ATR':
            dist = float(self._atr[-1]) * float(self.atr_mult)
        elif m == 'STD':
            sigma_daily = float(self._sigma_d[-1])
            dist = close * float(self.vol_mult) * sigma_daily
        else:
            raise ValueError("method deve ser 'ATR' ou 'STD'.")

        if not np.isfinite(dist) or dist <= 0:
            return None

        # Para long, stop por volatilidade fica a 'dist' abaixo do preço atual
        return close - dist

    # ----------------- Lógica principal -----------------
    def next(self):
        close = self.data.Close
        low   = self.data.Low
        hi3   = self.hi3
        lo3   = self.lo3

        cur_idx = len(close) - 1

        # ENTRADA: breakout do Hi(3)
        if not self.position:
            if np.isfinite(hi3[-1]) and close[-1] > hi3[-1]:
                # compra no fechamento do candle do breakout
                self.buy()
                # registra parâmetros da operação
                self.entry_price = float(close[-1])
                self.entry_idx = cur_idx
                # stop inicial: 10% abaixo da entrada (simulado)
                self.last_stop = self.entry_price * (1 - 0.10)
            return

        # Há posição aberta: sanidade
        if self.entry_price is None or self.entry_idx is None:
            return

        # SAÍDA 1 (regra do setup): inversão pelo Lo(3) no FECHAMENTO
        if np.isfinite(lo3[-1]) and close[-1] < lo3[-1]:
            self.position.close()
            self.entry_price = None
            self.entry_idx = None
            self.last_stop = None
            return

        # PROTEÇÃO (regra original): após >=1 dia e lucro >1,5%, garante +0,5% sobre a entrada
        bars_in_trade = cur_idx - self.entry_idx
        unrealized_gain = float(close[-1]) / self.entry_price - 1.0  # fração

        if bars_in_trade >= 1 and unrealized_gain > 0.015:
            protect_stop = self.entry_price * (1 + 0.005)
            if self.last_stop is None:
                self.last_stop = protect_stop
            else:
                self.last_stop = max(self.last_stop, protect_stop)

        # TRAILING por volatilidade (apenas aperta)
        # opcionalmente só traciona se estiver em lucro
        if not self.only_trail_in_profit or float(close[-1]) > self.entry_price:
            candidate = self._candidate_trailing_level()
            if candidate is not None:
                if self.last_stop is None:
                    self.last_stop = candidate
                else:
                    self.last_stop = max(self.last_stop, candidate)

        # SAÍDA 2 (stop simulado): fecha se a mínima da barra toca/perde o stop
        if self.last_stop is not None and low[-1] <= self.last_stop:
            self.position.close()
            self.entry_price = None
            self.entry_idx = None
            self.last_stop = None

# def hiLo3DailyStrategy(df, valor_inicial=10000, comissao=0.000):
#     df = df.rename(columns={
#         'open': 'Open',
#         'high': 'High',
#         'low': 'Low',
#         'close': 'Close',
#         'volume': 'Volume',
#         'date': 'Date'
#     })

#     bt = Backtest(df, HiLo3DailyStrategy, cash=valor_inicial, commission=comissao, trade_on_close=True)
#     stats = bt.run()
#     stats = renomear_chaves_stats(stats)
# #    bt.plot(open_browser=True)
#     return stats


def renomear_chaves_stats(stats):
    """
    Renomeia as principais chaves do dicionário stats para nomes mais amigáveis.
    Adiciona a chave 'trades' como lista de dicionários.
    Retorna um novo dicionário.
    """
    mapeamento = {
        'Start': 'data_inicio',
        'End': 'data_fim',
        'Duration': 'duracao',
        'Exposure Time [%]': 'tempo_operacao_pct',
        'Equity Final [$]': 'equity_final',
        'Equity Peak [$]': 'equity_maxima',
        'Return [%]': 'retorno_total_pct',
        'Buy & Hold Return [%]': 'retorno_buy_hold_pct',
        'Return (Ann.) [%]': 'retorno_anual_pct',
        'Volatility (Ann.) [%]': 'volatilidade_anual_pct',
        'CAGR [%]': 'cagr_pct',
        'Sharpe Ratio': 'sharpe',
        'Sortino Ratio': 'sortino',
        'Calmar Ratio': 'calmar',
        'Alpha [%]': 'alpha_pct',
        'Beta': 'beta',
        'Max. Drawdown [%]': 'max_drawdown_pct',
        'Avg. Drawdown [%]': 'avg_drawdown_pct',
        'Max. Drawdown Duration': 'max_drawdown_duracao',
        'Avg. Drawdown Duration': 'avg_drawdown_duracao',
        '# Trades': 'num_trades',
        'Win Rate [%]': 'taxa_acerto_pct',
        'Best Trade [%]': 'melhor_trade_pct',
        'Worst Trade [%]': 'pior_trade_pct',
        'Avg. Trade [%]': 'media_trade_pct',
        'Max. Trade Duration': 'max_trade_duracao',
        'Avg. Trade Duration': 'avg_trade_duracao',
        'Profit Factor': 'fator_lucro',
        'Expectancy [%]': 'expectancy_pct',
        'SQN': 'sqn',
        'Kelly Criterion': 'kelly',
    }
    stats_new = {mapeamento.get(k, k): v for k, v in stats.items()}

    # Adiciona a lista de trades já pronta para o template
    if '_trades' in stats and hasattr(stats['_trades'], 'to_dict'):
        stats_new['trades'] = stats['_trades'].to_dict(orient='records')
    else:
        stats_new['trades'] = []

    return stats_new