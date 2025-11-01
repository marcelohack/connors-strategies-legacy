from backtesting import Backtest, Strategy
import talib
from plotly.offline import plot
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
    """

    def init(self):
        # Calcula as médias móveis simples de 10 e 20 períodos
        self.sma10 = self.I(_sma, self.data.Close, 10)
        self.sma20 = self.I(_sma, self.data.Close, 20)

    def next(self):
        close = self.data.Close
        sma10 = self.sma10
        sma20 = self.sma20

        # Condição de compra: fechamento acima das duas médias
        if not self.position and close[-1] > sma10[-1] and close[-1] > sma20[-1]:
            self.buy()

        # Condição de saída: preço abaixo da SMA20 e cruzando para baixo a SMA10
        if self.position:
            cond1 = close[-1] < sma20[-1]
            cond2 = len(close) > 1 and close[-2] >= sma10[-2] and close[-1] < sma10[-1]
            if cond1 and cond2:
                self.position.close()


def twoMAsAboveStrategy_py(df, valor_inicial=10000, comissao=0.000):
    df = df.rename(columns={
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume',
        'date': 'Date'
    })

    bt = Backtest(df, TwoMAsAboveStrategy, cash=valor_inicial, commission=comissao, trade_on_close=True,finalize_trades=True)
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