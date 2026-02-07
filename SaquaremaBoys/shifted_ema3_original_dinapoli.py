from backtesting import Strategy # Backtest
#from backtesting.lib import crossover
import numpy as np

# Dependência: TA-Lib 0.6.7
import talib


class ShiftedEma3OriginalDinapoli(Strategy):
    """
    Nome do Livro/Arquivo: Setup Joe DiNapoli (slides)
    Nome do Setup: EMA3 deslocada (3) – Reversão com Dois Fechamentos (Versão Original)
    Estratégia: Tendência -> reversão operacional baseada em fechamentos relativos à MME3 deslocada em +3 períodos e alvo por expansão alternada de Fibonacci (161% da 1ª perna)
    Autor da Estratégia: Joe DiNapoli (material didático compilado)
    Páginas: Não foi possível identificar a paginação exata (arquivo de slides sem numeração detectável).

    Regras (Compra) — versão ORIGINAL, adaptadas ao período DIÁRIO:
      1) Contexto: mercado vinha fechando abaixo da MME3 deslocada em +3 (MME3(shift=+3)).
      2) Detectar o 1º FECHAMENTO ACIMA da MME3(3). O "Fundo 1" é definido como o menor fechamento observado no trecho imediatamente anterior em que os fechamentos estavam abaixo da MME3(3).
      3) Em seguida, aguardar um FECHAMENTO ABAIXO da MME3(3) que NÃO PERCA, EM FECHAMENTO, o nível do Fundo 1. Esse ponto marca a região do "Fundo 2".
      4) Na próxima ocasião em que ocorrer um 2º FECHAMENTO ACIMA da MME3(3), marca-se a MÁXIMA desse candle; a entrada é por STOP (breakout) dessa máxima acrescida de 1 "tick".
      5) STOP (ORIGINAL): na mínima do candle do 2º fechamento acima.
      6) ALVO (TP): expansão alternada de 161% da 1ª perna de alta (do Fundo 1 até o 1º fechamento acima), projetada a partir do preço de entrada.

    Observações de Implementação:
      - Em plataformas gráficas, "MME3 deslocada em +3" significa a MME deslocada três barras para a direita. Para uma série temporal, implementamos a condição como: Close[t] em relação a EMA3[t-3].
      - Assim, comparamos o fechamento atual com a EMA3 "defasada" (shift para trás de 3 barras).
      - A classe inicia SÓ com operações de COMPRA, conforme restrição do usuário.
      - Mantém no máximo uma ordem/posição por vez.
      - Parâmetros configuráveis:
           tick_size: incremento mínimo de preço para ordens stop/stop-loss;
           fib_ratio: razão de expansão (padrão 1.618);
           displace: deslocamento da EMA (padrão 3);
           ema_period: período da EMA (padrão 3).
      - Proteções adicionais (opcionais):
           use_max_stop_loss: aplica stop loss máximo de segurança (padrão: True);
           stop_loss_pct: stop loss máximo em % (padrão: 10%);
           gain_threshold_pct: limiar de ganho para ativar proteção (padrão: 1,5%);
           stop_gain_pct: stop gain de proteção em % (padrão: 0,5%);
           min_bars_for_protection: dias mínimos antes de ativar proteção (padrão: 2).

    """

    # ---------- Parâmetros configuráveis ----------
    tick_size: float = 0.01     # tamanho do "tick" (ex.: ações brasileiras: 0,01)
    fib_ratio: float = 1.618    # fator de expansão de Fibonacci para o alvo
    displace: int = 3           # deslocamento para a direita da MME (comparação com EMA[t-3])
    ema_period: int = 3         # período da MME

    # Parâmetros de stop loss e stop gain adicionais
    use_max_stop_loss: bool = True      # Usar stop loss máximo de segurança
    stop_loss_pct: float = 0.10         # Stop loss máximo (padrão: 10% abaixo da entrada)
    gain_threshold_pct: float = 0.015   # Limiar de ganho para ativar proteção (padrão: 1.5%)
    stop_gain_pct: float = 0.005        # Stop gain de proteção (padrão: 0.5% acima da entrada)
    min_bars_for_protection: int = 2    # Número mínimo de dias antes de ativar proteção de ganho

    def init(self):
        close = self.data.Close

        # Calcula EMA(3) com TA-Lib
        #ema = self.I(lambda x: talib.EMA(x, timeperiod=self.ema_period), close)

        # Gera série "EMA deslocada" no sentido de comparação Close[t] vs EMA[t-displace]
        # Implementação: shift positivo para trás (alinha EMA passada com o Close atual)
        def shifted(arr, n):
            out = np.full_like(arr, np.nan, dtype=float)
            if n <= 0:
                return arr
            out[n:] = arr[:-n]
            return out

        self.ema_shifted = self.I(lambda x: shifted(talib.EMA(x, timeperiod=self.ema_period), self.displace), close)

        # Estados internos do setup
        self._state = "seek_first_close_above"
        self._fund1 = np.nan           # Fundo 1 (nível de preço por fechamento)
        self._first_close_above_idx = None
        self._trigger_high = np.nan    # Máxima do candle do 2º fechamento acima
        self._second_close_above_low = np.nan  # Mínima do candle do 2º fechamento acima
        self._pending_buy_stop_price = np.nan  # Preço stop de compra

        # Estados da operação para gerenciamento de stop adicional
        self.last_stop = None          # nível atual do stop simulado
        self.entry_price = None        # preço de entrada registrado
        self.entry_idx = None          # índice (barra) de entrada

    def _current_close_above(self, i):
        """Fecha acima da EMA deslocada?"""
        ema_s = self.ema_shifted[i]
        c = self.data.Close[i]
        if np.isnan(ema_s):
            return False
        return c > ema_s

    def _current_close_below(self, i):
        """Fecha abaixo da EMA deslocada?"""
        ema_s = self.ema_shifted[i]
        c = self.data.Close[i]
        if np.isnan(ema_s):
            return False
        return c < ema_s

    def next(self):
        i = len(self.data.Close) - 1
        close = self.data.Close
        low = self.data.Low

        # Não abrimos outra posição se já estivermos posicionados ou com ordem pendente colocada nesta barra
        has_position = bool(self.position)
        # backtesting.py não expõe "open orders" facilmente; então controlamos via variável local de stop pendente
        # Colocamos a ordem somente na barra do 2º fechamento acima e ela aciona quando o preço alcançar.
        # Após chamar self.buy(stop=...), não há como "consultar" a existência da ordem; por isso, evitamos duplicidade
        # garantindo que só emitimos a ordem quando _pending_buy_stop_price é NaN.
        # A cada nova barra, zeramos o gatilho se já estivermos em posição.
        if has_position:
            self._pending_buy_stop_price = np.nan

            # GERENCIAMENTO DE STOP GAIN ADICIONAL (proteção extra além do SL/TP original)
            if self.entry_price is not None and self.entry_idx is not None:
                # Calcula dias em operação e ganho não realizado
                bars_in_trade = i - self.entry_idx
                unrealized_gain = float(close[-1]) / self.entry_price - 1.0  # fração

                # PROTEÇÃO: após dias configurados e lucro > limiar, move stop para garantir stop_gain_pct
                if bars_in_trade >= self.min_bars_for_protection and unrealized_gain > self.gain_threshold_pct:
                    protect_stop = self.entry_price * (1 + self.stop_gain_pct)
                    if self.last_stop is None:
                        self.last_stop = protect_stop
                    else:
                        self.last_stop = max(self.last_stop, protect_stop)

                # SAÍDA por stop gain adicional: fecha se a mínima tocar o stop de proteção
                if self.last_stop is not None and low[-1] <= self.last_stop:
                    self.position.close()
                    self.entry_price = None
                    self.entry_idx = None
                    self.last_stop = None
            return

        # Estado: procurar 1º fechamento acima após sequência de closes abaixo
        if self._state == "seek_first_close_above":
            # Só validamos se EMA deslocada existe
            if self._current_close_above(i):
                # Determina Fundo 1: menor FECHAMENTO enquanto abaixo da EMA deslocada desde o último pivot
                # Varremos para trás até encontrar a barra em que passamos a ficar consistentemente abaixo (ou início)
                j = i - 1
                min_close = np.inf
                while j >= 0 and self._current_close_below(j):
                    min_close = min(min_close, float(self.data.Close[j]))
                    j -= 1
                # Se não houve trecho abaixo, o setup não se forma corretamente
                if min_close == np.inf:
                    return
                self._fund1 = min_close
                self._first_close_above_idx = i
                self._state = "seek_close_below_without_losing_fund1"
                return

        # Estado: aguardar um fechamento abaixo que NÃO perca, em fechamento, o Fundo 1
        if self._state == "seek_close_below_without_losing_fund1":
            if self._current_close_below(i):
                # Verifica se NÃO perdeu, EM FECHAMENTO, o Fundo 1
                if self.data.Close[i] >= self._fund1:
                    # Aceita como "Fundo 2" válido em termos de fechamento
                    self._state = "seek_second_close_above"
                else:
                    # Perdeu o Fundo 1: invalida sequência; recomeça
                    self._reset_pattern()
            return

        # Estado: procurar o 2º fechamento acima; ao encontrá-lo, armar buy stop
        if self._state == "seek_second_close_above":
            if self._current_close_above(i):
                # 2º fechamento acima confirmado
                self._trigger_high = float(self.data.High[i])
                self._second_close_above_low = float(self.data.Low[i])

                # Define preço de entrada (stop) e SL/TP conforme regras
                entry_stop = self._trigger_high + self.tick_size  # breakout da máxima + 1 tick
                stop_loss_original = self._second_close_above_low  # stop na mínima do candle do 2º fechamento acima (regra original)

                # Aplica stop loss máximo de segurança se habilitado
                if self.use_max_stop_loss:
                    max_stop_loss = entry_stop * (1 - self.stop_loss_pct)
                    stop_loss = max(stop_loss_original, max_stop_loss)  # usa o stop mais conservador (maior)
                else:
                    stop_loss = stop_loss_original

                # Calcula a 1ª perna de alta: Fundo 1 -> fechamento do 1º fechamento acima
                if self._first_close_above_idx is None or np.isnan(self._fund1):
                    # Segurança — se algo faltou, aborta e reseta padrão
                    self._reset_pattern()
                    return
                first_leg = float(self.data.Close[self._first_close_above_idx]) - float(self._fund1)
                if first_leg <= 0 or not np.isfinite(first_leg):
                    # Se a "perna 1" não for válida, aborta e reseta
                    self._reset_pattern()
                    return

                # Alvo de 161% a partir do preço de entrada
                take_profit = entry_stop + self.fib_ratio * first_leg

                # Emite ordem de compra por STOP (será executada quando o preço atingir entry_stop)
                # O backtesting.py executa a ordem quando High da próxima barra ultrapassa o nível de stop.
                self.buy(stop=entry_stop, sl=stop_loss, tp=take_profit)

                # Arma flag para evitar múltiplas ordens (somente uma por padrão)
                self._pending_buy_stop_price = entry_stop

                # Registra entrada para gerenciamento de stop gain adicional
                self.entry_price = entry_stop
                self.entry_idx = i
                self.last_stop = stop_loss

                # Após emitir ordem, reinicia o padrão para evitar duplicidade futura enquanto aguardamos nova sequência
                self._reset_pattern(soft=True)
                return

    def _reset_pattern(self, soft=False):
        """
        Reset do padrão interno.
        soft=True preserva _pending_buy_stop_price (evita limpar ordem recém-emitida).
        """
        self._state = "seek_first_close_above"
        self._fund1 = np.nan
        self._first_close_above_idx = None
        self._trigger_high = np.nan
        self._second_close_above_low = np.nan
        if not soft:
            self._pending_buy_stop_price = np.nan


# def shiftedEma3OriginalDinapoli(df, valor_inicial=10000, comissao=0.000):
#     df = df.rename(columns={
#         'open': 'Open',
#         'high': 'High',
#         'low': 'Low',
#         'close': 'Close',
#         'volume': 'Volume',
#         'date': 'Date'
#     })

#     bt = Backtest(df, ShiftedEma3OriginalDinapoli, cash=valor_inicial, commission=comissao, trade_on_close=True)
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