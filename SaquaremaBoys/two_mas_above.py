from backtesting import Strategy
import talib
#from plotly.offline import plot
import numpy as np


# =============================
# Funções auxiliares
# =============================

def _sma(a: np.ndarray, period: int) -> np.ndarray:
    """Retorna SMA via TA-Lib."""
    return talib.SMA(a, timeperiod=period)


# =============================
# 1) Setup 34 – Preços acima de duas médias
# =============================

class TwoMAsAboveStrategy(Strategy):

    """Setup 34 — Preços acima de duas médias (SMA10 & SMA20).
    - Compra ao fechar acima das duas médias.
    - Saída quando fechar abaixo da SMA20 e cruzar para baixo a SMA10.
    - Stop inicial: configurável via stop_loss_pct (padrão: 10% abaixo da entrada).
    - Proteção: após min_bars_for_protection dias (padrão: 1) e lucro > gain_threshold_pct (padrão: 1,5%),
      move stop para stop_gain_pct (padrão: 0,5%) acima da entrada.
    - Stop móvel por volatilidade (ATR ou σ diário), sempre apertando (nunca alargando).
    """

    # ---------- Parâmetros de trailing ----------
    method = 'ATR'        # 'ATR' ou 'STD' (σ diário)
    atr_period = 14
    atr_mult   = 2.0

    vol_window = 20       # janela p/ sigma diário
    vol_mult   = 2.0

    only_trail_in_profit = True  # só traciona stop se trade estiver positivo

    # Parâmetros de stop loss e stop gain
    stop_loss_pct: float = 0.10       # Stop loss inicial (padrão: 10% abaixo da entrada)
    gain_threshold_pct: float = 0.015  # Limiar de ganho para ativar proteção (padrão: 1.5%)
    stop_gain_pct: float = 0.005      # Stop gain de proteção (padrão: 0.5% acima da entrada)
    min_bars_for_protection: int = 1   # Número mínimo de dias antes de ativar proteção de ganho

    def init(self):
        # Calcula as médias móveis simples de 10 e 20 períodos
        self.sma10 = self.I(_sma, self.data.Close, 10)
        self.sma20 = self.I(_sma, self.data.Close, 20)

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
        self._atr = self.I(lambda h, low_data, c: talib.ATR(h, low_data, c, timeperiod=self.atr_period),
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
        sma10 = self.sma10
        sma20 = self.sma20

        cur_idx = len(close) - 1

        # Condição de compra: fechamento acima das duas médias
        if not self.position:
            if close[-1] > sma10[-1] and close[-1] > sma20[-1]:
                self.buy()
                # Registra parâmetros da operação
                self.entry_price = float(close[-1])
                self.entry_idx = cur_idx
                # Stop inicial: stop_loss_pct abaixo da entrada (simulado)
                self.last_stop = self.entry_price * (1 - self.stop_loss_pct)
            return

        # Há posição aberta: sanidade
        if self.entry_price is None or self.entry_idx is None:
            return

        # SAÍDA 1 (regra do setup): preço abaixo da SMA20 e cruzando para baixo a SMA10
        cond1 = close[-1] < sma20[-1]
        cond2 = len(close) > 1 and close[-2] >= sma10[-2] and close[-1] < sma10[-1]
        if cond1 and cond2:
            self.position.close()
            self.entry_price = None
            self.entry_idx = None
            self.last_stop = None
            return

        # # PROTEÇÃO (regra original): após >=1 dia e lucro >1,5%, garante +0,5% sobre a entrada
        # bars_in_trade = cur_idx - self.entry_idx
        # unrealized_gain = float(close[-1]) / self.entry_price - 1.0  # fração

        # if bars_in_trade >= 1 and unrealized_gain > 0.015:
        #     protect_stop = self.entry_price * (1 + 0.005)
        #     if self.last_stop is None:
        #         self.last_stop = protect_stop
        #     else:
        #         self.last_stop = max(self.last_stop, protect_stop)

        # # TRAILING por volatilidade (apenas aperta)
        # # opcionalmente só traciona se estiver em lucro
        # if not self.only_trail_in_profit or float(close[-1]) > self.entry_price:
        #     candidate = self._candidate_trailing_level()
        #     if candidate is not None:
        #         if self.last_stop is None:
        #             self.last_stop = candidate
        #         else:
        #             self.last_stop = max(self.last_stop, candidate)

        # SAÍDA 2 (stop simulado): fecha se a mínima da barra toca/perde o stop
        if self.last_stop is not None and low[-1] <= self.last_stop:
            self.position.close()
            self.entry_price = None
            self.entry_idx = None
            self.last_stop = None


# def twoMAsAboveStrategy_py(df, valor_inicial=10000, comissao=0.000):
#     df = df.rename(columns={
#         'open': 'Open',
#         'high': 'High',
#         'low': 'Low',
#         'close': 'Close',
#         'volume': 'Volume',
#         'date': 'Date'
#     })

#     bt = Backtest(df, TwoMAsAboveStrategy, cash=valor_inicial, commission=comissao, trade_on_close=True,finalize_trades=True)
#     stats = bt.run()
#     #bt.plot()
#     stats = renomear_chaves_stats(stats)
#     return stats

# def renomear_chaves_stats(stats):
#     """
#     Renomeia as principais chaves do dicionário stats para nomes mais amigáveis.
#     Adiciona a chave 'trades' como lista de dicionários.
#     Retorna um novo dicionário.
#     """
#     mapeamento = {
#         'Start': 'data_inicio',
#         'End': 'data_fim',
#         'Duration': 'duracao',
#         'Exposure Time [%]': 'tempo_operacao_pct',
#         'Equity Final [$]': 'equity_final',
#         'Equity Peak [$]': 'equity_maxima',
#         'Return [%]': 'retorno_total_pct',
#         'Buy & Hold Return [%]': 'retorno_buy_hold_pct',
#         'Return (Ann.) [%]': 'retorno_anual_pct',
#         'Volatility (Ann.) [%]': 'volatilidade_anual_pct',
#         'CAGR [%]': 'cagr_pct',
#         'Sharpe Ratio': 'sharpe',
#         'Sortino Ratio': 'sortino',
#         'Calmar Ratio': 'calmar',
#         'Alpha [%]': 'alpha_pct',
#         'Beta': 'beta',
#         'Max. Drawdown [%]': 'max_drawdown_pct',
#         'Avg. Drawdown [%]': 'avg_drawdown_pct',
#         'Max. Drawdown Duration': 'max_drawdown_duracao',
#         'Avg. Drawdown Duration': 'avg_drawdown_duracao',
#         '# Trades': 'num_trades',
#         'Win Rate [%]': 'taxa_acerto_pct',
#         'Best Trade [%]': 'melhor_trade_pct',
#         'Worst Trade [%]': 'pior_trade_pct',
#         'Avg. Trade [%]': 'media_trade_pct',
#         'Max. Trade Duration': 'max_trade_duracao',
#         'Avg. Trade Duration': 'avg_trade_duracao',
#         'Profit Factor': 'fator_lucro',
#         'Expectancy [%]': 'expectancy_pct',
#         'SQN': 'sqn',
#         'Kelly Criterion': 'kelly',
#     }
#     stats_new = {mapeamento.get(k, k): v for k, v in stats.items()}

#     # Adiciona a lista de trades já pronta para o template
#     if '_trades' in stats and hasattr(stats['_trades'], 'to_dict'):
#         stats_new['trades'] = stats['_trades'].to_dict(orient='records')
#     else:
#         stats_new['trades'] = []

#     return stats_new