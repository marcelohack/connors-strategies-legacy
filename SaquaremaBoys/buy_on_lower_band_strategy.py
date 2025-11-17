# -*- coding: utf-8 -*-
"""
Arquivo: buy_on_lower_band_strategy.py

Classe de estratégia baseada no livro:
- Nome do Livro: Manual de Setups – Volume 4 (Bandas de Bollinger)
- Nome do Setup: 102 – Compra na banda inferior
- Estratégia: Retorno à média com Bandas de Bollinger. Compra quando o fechamento cruza PARA CIMA a banda
              inferior; encerra a posição ao atingir (tocar/fechar em) a banda superior.
- Autor/Referência do Setup: John Bollinger (descrição e testes no Vol. 4)
- Páginas (edição do PDF fornecido): ~27–33 (aprox., conforme paginação impressa)
- Período alvo: Diário
- Regras operacionais importantes do livro (adaptadas para execução sistemática):
  * ENTRADA SOMENTE NA COMPRA.
  * Entrada ocorre quando o fechamento volta para dentro das bandas cruzando PARA CIMA a banda inferior.
  * Saída ocorre ao atingir a banda superior (toque/fechamento em/above). Sem alvo fixo adicional.
  * Parâmetros padrão: Bollinger(20, 2, SMA).
  * Biblioteca de indicadores: TA-Lib 0.6.7.
  * Framework de backtests: backtesting.py 0.6.5.
"""

#from typing import Tuple

import numpy as np
#import pandas as pd
import talib
from backtesting import Strategy  # Backtest
from backtesting.lib import crossover

def _crossunder(a, b) -> bool:
    """Cruzamento de A PARA BAIXO de B entre a barra anterior e a atual."""
    if len(a) < 2 or len(b) < 2:
        return False
    a_prev, a_now = float(a[-2]), float(a[-1])
    b_prev, b_now = float(b[-2]), float(b[-1])
    vals = np.array([a_prev, a_now, b_prev, b_now], dtype=float)
    if not np.all(np.isfinite(vals)):
        return False
    return (a_prev >= b_prev) and (a_now < b_now)

class BuyOnLowerBandStrategy(Strategy):
    """
    Implementação do Setup 102 – "Compra na banda inferior" (apenas COMPRAS).

    Regras (resumo):
    - Indicador: Bandas de Bollinger (período = 20, desvios = 2, SMA).
    - ENTRADA (compra):
        * Condição: fechamento cruza PARA CIMA a banda inferior (sai de fora para dentro das bandas).
        * Implementação: close[-2] < lower[-2] e close[-1] >= lower[-1].
    - SAÍDA (encerramento total da posição):
        * Condição: preço atinge a banda superior (toque/fechamento em/above).
        * Implementação: close[-1] >= upper[-1].
    - Stop inicial: configurável via stop_loss_pct (padrão: 10% abaixo da entrada).
    - Proteção: após min_bars_for_protection dias (padrão: 2) e lucro > gain_threshold_pct (padrão: 1,5%),
      move stop para stop_gain_pct (padrão: 0,5%) acima da entrada.
      Observação: o setup não define stop fixo; a gestão é por condição de saída na banda superior.
                  Opcionalmente, pode-se abortar se voltar a fechar abaixo da banda inferior (proteção), mas
                  isto **não** é exigido pela regra-base do livro e, portanto, **não** está habilitado por padrão.

    Documentação:
    - Livro: Manual de Setups – Volume 4 (Bandas de Bollinger)
    - Setup: 102 – Compra na banda inferior
    - Autor: John Bollinger
    - Páginas: ~27–33 (aprox.)
    """

    # -----------------------
    # Parâmetros configuráveis
    # -----------------------
    bb_period: int = 20          # Período das Bandas de Bollinger
    bb_dev: float = 2.0          # Desvio padrão (iguais para cima e para baixo)
    bb_matype: int = 0           # 0 = SMA no TA-Lib
    #risk_per_trade: float = 1.0  # % do capital a arriscar por trade (não obrigatório; sizing opcional)
    protective_exit_on_rebreak: bool = False  # Se True, sai se voltar a fechar abaixo da banda inferior

    # Parâmetros de stop loss e stop gain
    stop_loss_pct: float = 0.10       # Stop loss inicial (padrão: 10% abaixo da entrada)
    gain_threshold_pct: float = 0.015  # Limiar de ganho para ativar proteção (padrão: 1.5%)
    stop_gain_pct: float = 0.005      # Stop gain de proteção (padrão: 0.5% acima da entrada)
    min_bars_for_protection: int = 2   # Número mínimo de dias antes de ativar proteção de ganho

    def init(self) -> None:
        self.bb_upper = self.I(
            lambda s: talib.BBANDS(
                s.astype(float),
                timeperiod=self.bb_period,
                nbdevup=self.bb_dev,
                nbdevdn=self.bb_dev,
                matype=self.bb_matype
            )[0],
            self.data.Close,
            name="BB_upper"
        )
        self.bb_lower = self.I(
            lambda s: talib.BBANDS(
                s.astype(float),
                timeperiod=self.bb_period,
                nbdevup=self.bb_dev,
                nbdevdn=self.bb_dev,
                matype=self.bb_matype
            )[2],
            self.data.Close,
            name="BB_lower"
        )

        # Estados da operação para gerenciamento de stop
        self.last_stop = None          # nível atual do stop simulado
        self.entry_price = None        # preço de entrada registrado
        self.entry_idx = None          # índice (barra) de entrada

    def next(self) -> None:
        close = self.data.Close
        low = self.data.Low
        upper_now = self.bb_upper[-1]

        cur_idx = len(close) - 1

        # ENTRADA
        if not self.position and crossover(close, self.bb_lower):
            self.buy()
            # Registra parâmetros da operação
            self.entry_price = float(close[-1])
            self.entry_idx = cur_idx
            # Stop inicial: stop_loss_pct abaixo da entrada (simulado)
            self.last_stop = self.entry_price * (1 - self.stop_loss_pct)

        # SAÍDA
        elif self.position:
            # Há posição aberta: sanidade
            if self.entry_price is None or self.entry_idx is None:
                return

            # Regra-base: tocar/fechar na banda superior
            if np.isfinite(upper_now) and close[-1] >= upper_now:
                self.position.close()
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None
                return

            # Opcional: proteção se voltar a cruzar para baixo a inferior
            if self.protective_exit_on_rebreak and _crossunder(close, self.bb_lower):
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

            # SAÍDA por stop loss: fecha se a mínima da barra toca/perde o stop
            if self.last_stop is not None and low[-1] <= self.last_stop:
                self.position.close()
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None


# def buyOnLowerBandStrategy(df, valor_inicial=10000, comissao=0.000):
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

#     bt = Backtest(df, BuyOnLowerBandStrategy, cash=valor_inicial, commission=comissao, trade_on_close=False, finalize_trades=True)
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
#     if '_trades' in stats and hasattr(stats['_trades'], 'to_dict'):
#         stats_new['trades'] = stats['_trades'].to_dict(orient='records')
#     else:
#         stats_new['trades'] = []

#     return stats_new