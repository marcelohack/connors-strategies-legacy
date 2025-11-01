from backtesting import Backtest, Strategy
import talib
from plotly.offline import plot

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

    def init(self):
        # MME10 "normal"
        self.ema10 = self.I(_ema, self.data.Close, 10)
        # MME10 deslocada em 1 (via shift de 1)
        self.ema10_shifted = self.I(lambda x: pd.Series(_ema(x, 10)).shift(1).values, self.data.Close)
        # Para armazenar stop do candle sinal
        self._signal_low = None

    def next(self):
        close = self.data.Close
        ema = self.ema10
        ema_sh = self.ema10_shifted

        # Detecta cruzamento de alta da MME10 normal sobre a deslocada
        if not self.position and crossover(ema, ema_sh):
            # Define stop na mínima do candle sinal (barra atual)
            self._signal_low = self.data.Low[-1]
            self.buy(sl=self._signal_low)

        # Saída: cruzamento de baixa da MME10 normal sob a deslocada
        if self.position and crossover(ema_sh, ema):
            self.position.close()



def shadowLineStrategy_py(df, valor_inicial=10000, comissao=0.000):
    df = df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume',
        'date': 'Date'
    })

    bt = Backtest(df, ShadowLineStrategy, cash=valor_inicial, commission=comissao, trade_on_close=True,finalize_trades=True)
    stats = bt.run()
    #bt.plot()
    stats = renomear_chaves_stats(stats)
    return stats

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