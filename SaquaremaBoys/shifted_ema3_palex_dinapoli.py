from backtesting import Strategy # Backtest
import numpy as np

# Dependência: TA-Lib 0.6.7
import talib

class ShiftedEma3PalexDiNapoli(Strategy):
    """
    Nome do Livro/Arquivo: Setup Joe DiNapoli (slides)
    Nome do Setup: EMA3 deslocada (3) – Reversão com Dois Fechamentos (Variação "Stop Palex")
    Estratégia: Tendência -> reversão operacional baseada em fechamentos relativos à MME3 deslocada em +3 períodos e alvo por expansão alternada de Fibonacci (161% da 1ª perna)
    Autor da Estratégia: Joe DiNapoli (material didático compilado) | Variação de stop por "Palex"
    Páginas: Não foi possível identificar a paginação exata (arquivo de slides sem numeração detectável).

    Regras (Compra) — variação "STOP PALEX", adaptadas ao período DIÁRIO:
      1) Contexto: mercado vinha fechando abaixo da MME3 deslocada em +3 (MME3(shift=+3)).
      2) Detectar o 1º FECHAMENTO ACIMA da MME3(3). O "Fundo 1" é o menor fechamento observado no trecho imediatamente anterior em que os fechamentos estavam abaixo da MME3(3).
      3) Em seguida, aguardar um FECHAMENTO ABAIXO da MME3(3) que NÃO PERCA, EM FECHAMENTO, o nível do Fundo 1 -> define-se a região do "Fundo 2".
         - Armazenar a MÍNIMA do candle desse fechamento abaixo como "mínima do Fundo 2".
      4) Na próxima ocasião em que ocorrer um 2º FECHAMENTO ACIMA da MME3(3), marca-se a MÁXIMA desse candle; a entrada é por STOP (breakout) dessa máxima acrescida de 1 "tick".
      5) STOP (PALEX): na MÍNIMA DO FUNDO 2 (em vez da mínima do 2º fechamento acima).
      6) ALVO (TP): expansão alternada de 161% da 1ª perna de alta (do Fundo 1 até o 1º fechamento acima), projetada a partir do preço de entrada.

    Observações de Implementação:
      - "MME3 deslocada em +3" em série temporal: comparamos Close[t] com EMA3[t-3].
      - Operações apenas de COMPRA.
      - Uma posição por vez.
      - Parâmetros configuráveis: tick_size, fib_ratio, displace, ema_period.
    """

    # ---------- Parâmetros configuráveis ----------
    tick_size: float = 0.01     # tamanho do "tick" (ex.: ações brasileiras: 0,01)
    fib_ratio: float = 1.618    # fator de expansão de Fibonacci para o alvo
    displace: int = 3           # deslocamento para a direita da MME (comparação com EMA[t-3])
    ema_period: int = 3         # período da MME

    def init(self):
        close = self.data.Close

        # EMA(3) via TA-Lib
        def ema_func(x):
            #import talib
            return talib.EMA(x, timeperiod=self.ema_period)
        self.ema = self.I(ema_func, close)

        # Série EMA deslocada (shift para trás = comparar Close[t] com EMA[t-displace])
        def shifted(arr, n):
            out = np.full_like(arr, np.nan, dtype=float)
            if n <= 0:
                return arr
            out[n:] = arr[:-n]
            return out
        self.ema_shifted = self.I(lambda x: shifted(ema_func(x), self.displace), close)

        # Estados internos
        self._state = "seek_first_close_above"
        self._fund1_close = np.nan
        self._fund2_low = np.nan
        self._first_close_above_idx = None

    def _close_above_shifted(self, i):
        ema_s = self.ema_shifted[i]
        c = self.data.Close[i]
        if np.isnan(ema_s):
            return False
        return c > ema_s

    def _close_below_shifted(self, i):
        ema_s = self.ema_shifted[i]
        c = self.data.Close[i]
        if np.isnan(ema_s):
            return False
        return c < ema_s

    def next(self):
        i = len(self.data.Close) - 1

        if self.position:
            return

        # 1) Buscar 1º fechamento acima após sequência abaixo
        if self._state == "seek_first_close_above":
            if self._close_above_shifted(i):
                j = i - 1
                min_close = np.inf
                while j >= 0 and self._close_below_shifted(j):
                    min_close = min(min_close, float(self.data.Close[j]))
                    j -= 1
                if min_close == np.inf:
                    return
                self._fund1_close = min_close
                self._first_close_above_idx = i
                self._state = "seek_close_below_without_losing_fund1"
                return

        # 2) Fechamento abaixo que NÃO perca em fechamento o Fundo 1 -> define Fundo 2 (guardar Low)
        if self._state == "seek_close_below_without_losing_fund1":
            if self._close_below_shifted(i):
                if float(self.data.Close[i]) >= self._fund1_close:
                    self._fund2_low = float(self.data.Low[i])
                    self._state = "seek_second_close_above"
                else:
                    self._reset_pattern()
            return

        # 3) 2º fechamento acima -> armar buy stop; validar ordem SL < ENTRY < TP
        if self._state == "seek_second_close_above":
            if self._close_above_shifted(i):
                trigger_high = float(self.data.High[i])
                entry_stop = trigger_high + self.tick_size

                if not np.isfinite(self._fund2_low):
                    self._reset_pattern()
                    return
                stop_loss = self._fund2_low

                if self._first_close_above_idx is None or not np.isfinite(self._fund1_close):
                    self._reset_pattern()
                    return
                first_leg = float(self.data.Close[self._first_close_above_idx]) - float(self._fund1_close)
                if first_leg <= 0 or not np.isfinite(first_leg):
                    self._reset_pattern()
                    return

                take_profit = entry_stop + self.fib_ratio * first_leg

                # ---- Validação de ordenação exigida pelo backtesting.py ----
                # Long: exige SL < ENTRY < TP. Se falhar, não abrimos trade e reiniciamos o padrão.
                if not (stop_loss < entry_stop < take_profit):
                    self._reset_pattern()
                    return

                self.buy(stop=entry_stop, sl=stop_loss, tp=take_profit)
                self._reset_pattern(soft=True)
                return

    def _reset_pattern(self, soft=False):
        self._state = "seek_first_close_above"
        self._fund1_close = np.nan
        self._fund2_low = np.nan
        self._first_close_above_idx = None

# def shiftedEma3PalexDiNapoli(df, valor_inicial=10000, comissao=0.000):
#     df = df.rename(columns={
#         'open': 'Open',
#         'high': 'High',
#         'low': 'Low',
#         'close': 'Close',
#         'volume': 'Volume',
#         'date': 'Date'
#     })

#     bt = Backtest(df, ShiftedEma3PalexDiNapoli, cash=valor_inicial, commission=comissao, trade_on_close=True)
#     stats = bt.run()
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