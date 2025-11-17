from backtesting import Strategy  #Backtest, 
import talib
#from plotly.offline import plot

# Importações Marco
import numpy as np
from backtesting.lib import crossover
import pandas as pd

# =============================
# Funções auxiliares
# =============================

def _ema(a: np.ndarray, period: int) -> np.ndarray:
    """Retorna EMA via TA-Lib."""
    return talib.EMA(a, timeperiod=period)


# =============================
# 2) Setup 35 – Linha da Sombra (Larry Williams)
# =============================

class ShadowLineStrategy(Strategy):
    """Setup 35 — Linha da Sombra (Larry Williams) com MME10 normal e MME10 deslocada 1.
    - Compra no cruzamento MME10 (normal) > MME10 (deslocada).
    - Stop na mínima do candle do cruzamento.
    - Saída quando MME10 cruza para baixo a MME10 deslocada.
    """

    # Parâmetros configuráveis
    stop_inicial_pct = 0.10  # 10% - Stop inicial abaixo da entrada
    stop_movel_pct = 0.005   # 0.5% - Stop móvel acima da entrada
    lucro_minimo_pct = 0.015 # 1.5% - Lucro mínimo para ativar stop móvel

    def init(self):
        # MME10 "normal"
        self.ema10 = self.I(_ema, self.data.Close, 10)
        # MME10 deslocada em 1 (via shift de 1)
        self.ema10_shifted = self.I(lambda x: pd.Series(_ema(x, 10)).shift(1).values, self.data.Close)
        # Para armazenar stop do candle sinal
        self._signal_low = None

    def next(self):
        close = self.data.Close
        low = self.data.Low
        ema = self.ema10
        ema_sh = self.ema10_shifted

        # Índice da barra atual
        cur_idx = len(close) - 1

        # Detecta cruzamento de alta da MME10 normal sobre a deslocada
        if not self.position and crossover(ema, ema_sh):
            # Compra no fechamento
            self.buy()
            # Registra parâmetros da operação
            self.entry_price = float(close[-1])
            self.entry_idx = cur_idx
            # Stop inicial (configurável) abaixo da entrada
            self.last_stop = self.entry_price * (1 - self.stop_inicial_pct)
            return

        # Se há posição aberta, gerenciar stop móvel e saídas
        if self.position:
            if self.entry_price is None or self.entry_idx is None:
                # Segurança: se não tivermos dados de entrada, nada a fazer
                return

            # Saída 1: cruzamento de baixa da MME10 normal sob a deslocada
            if crossover(ema_sh, ema):
                self.position.close()
                # Limpa estados da operação
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None
                return

            # Calcula dias em operação e ganho não realizado
            bars_in_trade = cur_idx - self.entry_idx
            unrealized_gain = (float(close[-1]) / self.entry_price) - 1.0  # em fração

            # Proteção: após pelo menos 1 dia e lucro > lucro_minimo_pct, move stop para entry + stop_movel_pct
            if bars_in_trade >= 1 and unrealized_gain > self.lucro_minimo_pct:
                protect_stop = self.entry_price * (1 + self.stop_movel_pct)
                # Ajusta o stop apenas para cima (nunca reduz)
                if self.last_stop is None or protect_stop > self.last_stop:
                    self.last_stop = protect_stop

            # Saída 2: fechamento por stop simulado (se a mínima tocar/perder o stop)
            if self.last_stop is not None and low[-1] <= self.last_stop:
                self.position.close()
                # Limpa estados da operação
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None

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

# def shadowLineStrategy_py(df, valor_inicial=10000, comissao=0.000):
#     df = df.rename(columns={
#         'open': 'Open',
#         'high': 'High',
#         'low': 'Low',
#         'close': 'Close',
#         'volume': 'Volume',
#         'date': 'Date'
#     })

#     bt = Backtest(df, ShadowLineStrategy, cash=valor_inicial, commission=comissao, trade_on_close=True,finalize_trades=True)
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
