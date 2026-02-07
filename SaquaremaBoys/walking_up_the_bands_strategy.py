# -*- coding: utf-8 -*-
"""
Arquivo: walking_up_the_bands_strategy.py

Classe de estratégia baseada no livro:
- Nome do Livro: Manual de Setups – Volume 4 (Bandas de Bollinger)
- Nome do Setup: 101 – Walking up the Bands (Subida pela Banda)
- Estratégia: Seguir a tendência comprando quando o fechamento ultrapassa a banda superior das Bandas de Bollinger
             e encerrando a posição quando o fechamento cruza para baixo a banda inferior.
- Autor/Referência do Setup: John Bollinger (adaptado e testado no Vol. 4)
- Páginas (edição do PDF fornecido): 21–27 (aprox., conforme paginação impressa)
- Período alvo: Diário
- Observações importantes:
  * Segue estritamente a regra de ENTRADA SOMENTE NA COMPRA (sem operação de venda/short).
  * Não utiliza alvo fixo; a saída é por condição (fechamento abaixo da banda inferior).
  * Parâmetros padrão das Bandas de Bollinger: período 20, desvio 2, SMA (matype=0).
  * Biblioteca de indicadores: TA-Lib 0.6.7.
  * Framework de backtests: backtesting.py 0.6.5.

ATENÇÃO: Esta classe implementa as regras conforme descritas no livro, mantendo fidelidade conceitual
e restrição a operações de compra, conforme solicitado.
"""

#from typing import Tuple

import numpy as np
import talib
from backtesting import Strategy # Backtest
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


class WalkingUpTheBandsStrategy(Strategy):
    """
    Implementação do Setup 101 – "Walking up the Bands" (apenas para COMPRAS).

    Regras de operação (resumo):
    - Indicador: Bandas de Bollinger (período = 20, desvios = 2, SMA).
    - ENTRADA (compra):
        * Condição: Fechamento atual cruza PARA CIMA a banda superior.
        * Implementação: close[-2] <= upper[-2] e close[-1] > upper[-1].
    - SAÍDA (encerramento total):
        * Condição: Fechamento atual cruza PARA BAIXO a banda inferior.
        * Implementação: close[-2] >= lower[-2] e close[-1] < lower[-1].
    - Sem alvo fixo; a gestão é por condição de saída nas bandas.
    - Apenas uma posição de cada vez (verificação implícita via self.position).

    Documentação:
    - Livro: Manual de Setups – Volume 4 (Bandas de Bollinger)
    - Setup: 101 – Walking up the Bands
    - Autor: John Bollinger (setup clássico descrito e testado no Vol. 4)
    - Páginas: 21–27 (aprox.)
    """

    # -----------------------
    # Parâmetros configuráveis
    # -----------------------
    bb_period: int = 20          # Período das Bandas de Bollinger
    bb_dev: float = 2.0          # Desvio padrão (iguais para cima e para baixo)
    bb_matype: int = 0           # 0 = SMA no TA-Lib
    #risk_per_trade: float = 1.0  # % do capital a arriscar por trade (não obrigatório; usado se for gerenciar tamanho)

    def init(self) -> None:
        # Registrar bandas como indicadores independentes (atualizam barra a barra)
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

    def next(self) -> None:
        close = self.data.Close

        # ENTRADA: close cruza para cima a banda superior
        if not self.position and crossover(close, self.bb_upper):
            self.buy()

        # SAÍDA: close cruza para baixo a banda inferior
        elif self.position and _crossunder(close, self.bb_lower):
            self.position.close()


# def walkingUpTheBandsStrategy(df, valor_inicial=10000, comissao=0.000):
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

#     bt = Backtest(df, WalkingUpTheBandsStrategy, cash=valor_inicial, commission=comissao, trade_on_close=False, finalize_trades=True)
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