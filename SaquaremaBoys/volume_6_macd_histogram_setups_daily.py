"""
Módulo: volume6_macd_histogram_setups_daily

Contém classes de estratégias (apenas Compra) do Manual de Setups – Volume 6 (MACD Histograma),
implementadas para o período DIÁRIO usando TA‑Lib 0.6.7 e backtesting.py 0.6.5.

ATENÇÃO:
- Cada classe pode ser separada em seu próprio arquivo .py conforme necessidade.
- Comentários estão em PT‑BR; nomes das classes e identificadores em EN‑US, conforme requisitos.
- Todas as entradas iniciam apenas por COMPRA; saídas por alvo/stop ou condições de reversão.
- As regras abaixo estão documentadas em cada classe com base no conteúdo do PDF fornecido.

Dependências:
    pip install ta-lib==0.6.7 backtesting==0.6.5 pandas numpy

Observação de execução:
- O backtesting.py espera colunas com capitalização: Open, High, Low, Close, Volume.
- Os dados de entrada devem seguir o JSON informado no documento de exemplo.
"""
from __future__ import annotations
#from dataclasses import dataclass
#from typing import Optional, Tuple
from typing import Tuple

import numpy as np
#import pandas as pd

from backtesting import Strategy # Backtest
#from backtesting.lib import crossover
#from backtesting.test import SMA

import talib


# ===============================
# Utilitários comuns
# ===============================

def macd_hist(close: np.ndarray, fast: int, slow: int, signal: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Wrapper para obter linhas do MACD via TA‑Lib.
    Retorna (macd_line, macd_signal, macd_histogram).
    """
    macd_line, macd_signal, macd_h = talib.MACD(close, fastperiod=fast, slowperiod=slow, signalperiod=signal)
    return macd_line, macd_signal, macd_h


def pct_envelope(series: np.ndarray, period: int, pct: float) -> Tuple[np.ndarray, np.ndarray]:
    """Calcula envelope percentual (superior e inferior) em torno de SMA(period) com desvio pct (ex.: 0.08 para 8%)."""
    base = talib.SMA(series, timeperiod=period)
    upper = base * (1 + pct)
    lower = base * (1 - pct)
    return upper, lower


# ======================================================================================
# 1) HistogramZeroLineTrend — Compra quando o Histograma do MACD cruza/está acima de 0
#    Saída quando o Histograma cruza/está abaixo de 0
#    (Baseado nas seções que citam “Ponto de compra sendo MACD Histograma subindo acima da linha do zero;
#     Ponto de venda sendo MACD Histograma caindo abaixo da linha do zero.”)
# ======================================================================================
class HistogramZeroLineTrend(Strategy):
    """Estratégia: MACD Histogram Zero-Line Trend (diário)

    Regras (do Manual):
    - **Compra** quando o **MACD Histograma** está **subindo acima da linha do zero**.
    - **Saída** quando o **MACD Histograma** **cai abaixo da linha do zero**.
    - Parâmetros padrão: MACD (12, 26, 9), conforme uso clássico.
    - Stop inicial: configurável via stop_loss_pct (padrão: 10% abaixo da entrada).
    - Proteção: após min_bars_for_protection dias (padrão: 2) e lucro > gain_threshold_pct (padrão: 1,5%),
      move stop para stop_gain_pct (padrão: 0,5%) acima da entrada.

    Observações operacionais:
    - Esta é uma estratégia seguidora de tendência; espera-se menor taxa de acerto e payoff maior.
    - Apenas operações de Compra (long). Não abre posições vendidas.
    """

    # Parâmetros configuráveis
    fast: int = 12
    slow: int = 26
    signal: int = 9

    # Parâmetros de stop loss e stop gain
    stop_loss_pct: float = 0.10       # Stop loss inicial (padrão: 10% abaixo da entrada)
    gain_threshold_pct: float = 0.015  # Limiar de ganho para ativar proteção (padrão: 1.5%)
    stop_gain_pct: float = 0.005      # Stop gain de proteção (padrão: 0.5% acima da entrada)
    min_bars_for_protection: int = 2   # Número mínimo de dias antes de ativar proteção de ganho

    def init(self):
        # -- Calcula MACD e Histograma --
        self.macd, self.signal_line, self.hist = self.I(
            lambda x: macd_hist(x, self.fast, self.slow, self.signal), self.data.Close, name='MACD'
        )

        # Estados da operação para gerenciamento de stop
        self.last_stop = None          # nível atual do stop simulado
        self.entry_price = None        # preço de entrada registrado
        self.entry_idx = None          # índice (barra) de entrada

    def next(self):
        close = self.data.Close
        low = self.data.Low
        hist_now = self.hist[-1]
        hist_prev = self.hist[-2] if len(self.hist) > 1 else np.nan

        cur_idx = len(close) - 1

        # Entrada: histograma cruzando para cima de zero e subindo (confirmação de momentum)
        cond_buy = (hist_now > 0) and (hist_prev <= 0) and (hist_now > hist_prev)

        if not self.position:
            if cond_buy:
                # Compra a mercado
                self.buy()
                # Registra parâmetros da operação
                self.entry_price = float(close[-1])
                self.entry_idx = cur_idx
                # Stop inicial: stop_loss_pct abaixo da entrada (simulado)
                self.last_stop = self.entry_price * (1 - self.stop_loss_pct)
        else:
            # Há posição aberta: sanidade
            if self.entry_price is None or self.entry_idx is None:
                return

            # Saída 1: histograma cai abaixo de zero (regra original)
            cond_exit = (hist_now < 0) and (hist_prev >= 0)
            if cond_exit:
                self.position.close()
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None
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

            # SAÍDA 2 por stop loss: fecha se a mínima da barra toca/perde o stop
            if self.last_stop is not None and low[-1] <= self.last_stop:
                self.position.close()
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None

# def histogramZeroLineTrend(df, valor_inicial=10000, comissao=0.000):
#     """
#     Realiza o backtest usando a estratégia 9.1 definida na classe Setup91TA
#     df: DataFrame com colunas ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
#     Returns os resultados do backtest.
#     class Backtest(
#         data: DataFrame, 
#             #data is a pd.DataFrame with columns: Open, High, Low, Close, and (optionally) Volume.
#             #The passed data frame can contain additional columns that can be used by the strategy.
#             #DataFrame index can be either a datetime index (timestamps) or a simple integer index.
#         strategy: type[Strategy],
#         *,
#         cash: float = 10000,
#         spread: float = 0,
#         commission: float | Tuple[float, float] = 0,
#         margin: float = 1,
#         trade_on_close: bool = False,
#             #If True, market orders will be filled with respect to the current bar's closing price instead of the next bar's open.
#         hedging: bool = False,
#             #If True, allow trades in both directions simultaneously. 
#             #If False, the opposite-facing orders first close existing trades in a FIFO manner.
#         exclusive_orders: bool = False,
#             #If True, only one order (buy or sell) can be pending at any time. 
#             #New orders cancel existing ones.
#         finalize_trades: bool = False
#             #If True, all open trades are closed at the end of the backtest.
#     ) -> BacktestResults:
#     métricas do resultado (stats dict) incluem:
#         Start
#         End
#         Duration
#         Exposure Time [%]
#         Equity Final [$]
#         Equity Peak [$]
#         Return [%]
#         Buy & Hold Return [%]
#         Return (Ann.) [%]
#         Volatility (Ann.) [%]
#         CAGR [%]
#         Sharpe Ratio
#         Sortino Ratio
#         Calmar Ratio
#         Alpha [%]
#         Beta
#         Max. Drawdown [%]
#         Avg. Drawdown [%]
#         Max. Drawdown Duration
#         Avg. Drawdown Duration
#         # Trades (ver colunas abaixo)
#         Win Rate [%]
#         Best Trade [%]
#         Worst Trade [%]
#         Avg. Trade [%]
#         Max. Trade Duration
#         Avg. Trade Duration
#         Profit Factor
#         Expectancy [%]
#         SQN (ler documentação abaixo para detalhes)
#         Kelly Criterion (ler documentação abaixo para detalhes)
#         _strategy (instancia da estratégia usada)
#         _equity_curve (DataFrame com o patrimônio ao longo do tempo)
#         _trades (DataFrame com detalhes de cada trade)
#             EntryTime — Data/hora de entrada na operação
#             ExitTime — Data/hora de saída da operação
#             EntryPrice — Preço de entrada
#             ExitPrice — Preço de saída
#             Size — Quantidade de ativos negociados (negativo = vendido)
#             EntryBar — Índice do candle de entrada
#             ExitBar — Índice do candle de saída
#             PnL — Lucro/prejuízo bruto da operação
#             ReturnPct — Retorno percentual da operação
#             MAE — Maximum Adverse Excursion (maior perda durante a operação)
#             MFE — Maximum Favorable Excursion (maior ganho durante a operação)
#             Duration — Duração da operação (em candles)

#         **SQN** (System Quality Number) é uma métrica desenvolvida por Van K. Tharp para avaliar a qualidade de um sistema de trading.
#         É calculada como a razão entre o retorno médio por trade e o desvio padrão dos retornos por trade, multiplicada pela raiz quadrada do número total de trades.
#         A fórmula é:
#         SQN = (Retorno Médio por Trade / Desvio Padrão dos Retornos por Trade) * √(Número de Trades)
#         Interpretação:
#             SQN < 1,6: Sistema ruim
#             1,6 ≤ SQN < 2,0: Sistema aceitável
#             2,0 ≤ SQN < 2,5: Sistema bom
#             2,5 ≤ SQN < 3,0: Sistema excelente
#             SQN ≥ 3,0: Sistema excepcional
#         Resumo:
#             Quanto maior o SQN, melhor e mais consistente é o sistema de trading.
#             Ele leva em conta tanto o retorno médio quanto a volatilidade (risco) e o número de operações.
        
#         **Kelly Criterion** 
#         É uma fórmula usada para determinar o tamanho ideal de uma série de apostas para maximizar o crescimento do capital ao longo do tempo. 
#         O Kelly Criterion calcula qual fração do seu capital você deve arriscar em cada trade, levando em conta:
#             A probabilidade de ganhar (win rate)
#             O ganho médio quando acerta
#             A perda média quando erra 
#         A fórmula básica do Kelly Criterion é:
#             f* = (bp - q) / b
#         Onde:
#             f* é a fração do capital a ser apostada
#             b é a razão entre o ganho médio e a perda média (odds)
#             p é a probabilidade de ganhar (win rate)
#             q é a probabilidade de perder (1 - p)
#         Interpretação: 
#             Próximo de 1 sugere que o sistema é muito bom e você pode arriscar uma fração maior do capital
#             Um valor próximo de 0 sugere que o sistema é ruim ou neutro.
#             Valores negativos indicam que o sistema é perdedor (não deve ser operado).
#         Valores típicos:
#             f* > 0: Indica que você deve apostar essa fração do seu capital
#             f* = 0: Indica que você não deve apostar nada
#             f* < 0: Indica que você deve apostar uma fração negativa, ou seja, evitar a aposta
#         Resumo:  
#             Quanto maior o f*, maior a fração do capital a ser apostada.
#             O Kelly Criterion ajuda a responder: "Qual o tamanho ideal da minha posição para crescer o capital de forma eficiente e segura?"
#     """
#     df = df.rename(columns={
#         'open': 'Open',
#         'high': 'High',
#         'low': 'Low',
#         'close': 'Close',
#         'volume': 'Volume',
#         'date': 'Date'
#     })

#     bt = Backtest(df, HistogramZeroLineTrend, cash=valor_inicial, commission=comissao, trade_on_close=False, finalize_trades=True)
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