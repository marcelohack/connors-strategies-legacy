from backtesting import Strategy  # Backtest, 
import talib
#from plotly.offline import plot

import numpy as np
#from backtesting.lib import crossover
import pandas as pd

# =============================
# Funções auxiliares
# =============================

def _sma(a: np.ndarray, period: int) -> np.ndarray:
    """Retorna SMA via TA-Lib."""
    return talib.SMA(a, timeperiod=period)


def _rolling_min(a: np.ndarray, period: int) -> np.ndarray:
    """Mínima rolante (shiftada em 1 para evitar look-ahead)."""
    s = pd.Series(a)
    return s.rolling(period).min().shift(1).values

# =============================
# 4) Pullback na média das 5 mínimas com SMA20 ascendente
# =============================

class TouchFiveLowsSMA20UpStrategy(Strategy):
    """
    Compra quando o candle encosta na média das 5 mínimas e a SMA20 está ascendendo.
    - Entrada no fechamento do candle do toque.
    - Stop móvel na mínima dos últimos 10 dias (ajustando apenas para cima).
    - Stop inicial: configurável via stop_loss_pct (padrão: 10% abaixo da entrada).
    - Proteção: após min_bars_for_protection dias (padrão: 2) e lucro > gain_threshold_pct (padrão: 1,5%),
      move stop para stop_gain_pct (padrão: 0,5%) acima da entrada.
    """

    # Parâmetros de stop loss e stop gain
    stop_loss_pct: float = 0.10       # Stop loss inicial (padrão: 10% abaixo da entrada)
    gain_threshold_pct: float = 0.015  # Limiar de ganho para ativar proteção (padrão: 1.5%)
    stop_gain_pct: float = 0.005      # Stop gain de proteção (padrão: 0.5% acima da entrada)
    min_bars_for_protection: int = 2   # Número mínimo de dias antes de ativar proteção de ganho

    def init(self):
        # Média simples de 20 períodos (filtro direcional)
        self.sma20 = self.I(_sma, self.data.Close, 20)
        # Média das 5 mínimas (rolling mean de Low)
        self.mean5_lows = self.I(lambda x: pd.Series(x).rolling(5).mean().values, self.data.Low)
        # Mínima dos últimos 10 dias (shiftada para evitar look-ahead)
        self.min10 = self.I(_rolling_min, self.data.Low, 10)

        # Estados da operação para gerenciamento de stop
        self.last_stop = None          # nível atual do stop simulado
        self.entry_price = None        # preço de entrada registrado
        self.entry_idx = None          # índice (barra) de entrada

    def next(self):
        close = self.data.Close
        low = self.data.Low
        sma20 = self.sma20
        m5 = self.mean5_lows
        min10 = self.min10

        cur_idx = len(close) - 1

        # Filtro direcional: SMA20 ascendente
        sma20_up = len(sma20) > 1 and sma20[-1] > sma20[-2]

        # Preço de fechamento acima da SMA20
        close_above_sma20 = close[-1] > sma20[-1]

        # Candle toca a média das 5 mínimas
        touched = np.isfinite(m5[-1]) and low[-1] <= m5[-1]

        # ENTRADA
        if not self.position and sma20_up and close_above_sma20 and touched:
            self.buy()
            # Registra parâmetros da operação
            self.entry_price = float(close[-1])
            self.entry_idx = cur_idx
            # Stop inicial: stop_loss_pct abaixo da entrada (simulado)
            self.last_stop = self.entry_price * (1 - self.stop_loss_pct)
            return

        # GERENCIAMENTO DE STOP
        if self.position:
            # Há posição aberta: sanidade
            if self.entry_price is None or self.entry_idx is None:
                return

            # PROTEÇÃO (regra de stop gain): após dias configurados e lucro > limiar, garante stop_gain_pct sobre a entrada
            bars_in_trade = cur_idx - self.entry_idx
            unrealized_gain = float(close[-1]) / self.entry_price - 1.0  # fração

            if bars_in_trade >= self.min_bars_for_protection and unrealized_gain > self.gain_threshold_pct:
                protect_stop = self.entry_price * (1 + self.stop_gain_pct)
                if self.last_stop is None:
                    self.last_stop = protect_stop
                else:
                    self.last_stop = max(self.last_stop, protect_stop)

            # Stop móvel pela mínima dos últimos 10 dias (ajusta só para cima)
            if np.isfinite(min10[-1]):
                new_sl = max(self.last_stop, min10[-1]) if self.last_stop is not None else min10[-1]
                if new_sl > (self.last_stop if self.last_stop is not None else -np.inf):
                    self.last_stop = new_sl

            # SAÍDA por stop loss: fecha se a mínima da barra toca/perde o stop
            if self.last_stop is not None and low[-1] <= self.last_stop:
                self.position.close()
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None

# def touchFiveLowsSMA20UpStrategy_py(df, valor_inicial=10000, comissao=0.000):
#     df = df.rename(columns={
#         'open': 'Open',
#         'high': 'High',
#         'low': 'Low',
#         'close': 'Close',
#         'volume': 'Volume',
#         'date': 'Date'
#     })

#     bt = Backtest(df, TouchFiveLowsSMA20UpStrategy, cash=valor_inicial, commission=comissao, trade_on_close=False, finalize_trades=True)
#     stats = bt.run()
# #    bt.plot()
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
#     if '_trades' in stats and hasattr(stats['_trades'], 'to_dict'):
#         stats_new['trades'] = stats['_trades'].to_dict(orient='records')
#     else:
#         stats_new['trades'] = []

#     return stats_new