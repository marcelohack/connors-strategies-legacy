# -*- coding: utf-8 -*-
"""
Classe: WalkingUpTheBands (Setup 101)

Fonte: "Manual de Setups – Volume 4: Setups baseados na Banda de Bollinger" (Alexandre Wolwacz, 2010).
Páginas relevantes (edição disponibilizada): 21–23 (descrição do modelo e validação no diário);
26 (observação de que o modelo não deve ser invertido para venda).

Regras do Setup (conforme o livro, adaptadas para implementação no diário):
- Entrada (compra): comprar no fechamento do candle que FECHAR acima da banda superior da Bollinger.
- Saída: encerrar a posição no fechamento do candle que FECHAR abaixo da banda inferior da Bollinger.
- Observações: o modelo explora a continuação (momentum) após o rompimento para cima da banda superior; 
  o próprio livro destaca validação para o gráfico diário e ressalta que o modelo não deve ser invertido para a venda.

Observância às Diretrizes do Projeto:
- Timeframe: este setup é destinado ao gráfico diário. Não crie entradas a partir de venda descoberta.
- Stops/Targets: o livro não define stop/target adicionais além da saída por fechamento abaixo da banda inferior.
  Portanto, não foram adicionados alvos nem estopes artificiais, mantendo a fidelidade ao texto.
- Bibliotecas: TA-Lib (0.6.7) para Bandas de Bollinger; backtesting.py (0.6.5) para a estrutura de backtesting.

Notas de Implementação:
- A classe assume OHLCV com índice temporal diário (pandas.DatetimeIndex). Caso o índice não seja diário,
  a responsabilidade de ajuste é do usuário/rotina que cria o Backtest.
- Parâmetros de Bollinger configuráveis (período e desvios) foram expostos para varreduras/otimizações.
- Estratégia somente-comprada (long-only), conforme exigido.
"""

#from typing import Tuple

import numpy as np
import pandas as pd
import talib
from backtesting import Strategy  # Backtest,


class WalkingUpTheBands(Strategy):
    """
    Estratégia baseada no **Setup 101 — Walking up the Bands**.

    Parâmetros
    ----------
    bb_period : int
        Período da Média Móvel Simples usada nas Bandas de Bollinger. Padrão: 20.
    bb_dev : float
        Número de desvios padrão para as bandas superior/inferior. Padrão: 2.0.
    stop_loss_pct : float
        Stop loss inicial (padrão: 10% abaixo da entrada).
    gain_threshold_pct : float
        Limiar de ganho para ativar proteção (padrão: 1.5%).
    stop_gain_pct : float
        Stop gain de proteção (padrão: 0.5% acima da entrada).
    min_bars_for_protection : int
        Número mínimo de dias antes de ativar proteção de ganho (padrão: 1).

    Série Esperada
    --------------
    `self.data` deve conter colunas `Open`, `High`, `Low`, `Close` (OHLC) com **frequência diária**.

    Regras (resumo)
    ---------------
    - Compra: fechamento acima da banda superior (close > upper_band) => compra na próxima barra.
    - Saída: fechamento abaixo da banda inferior (close < lower_band) => encerra posição na próxima barra.
    - Stop inicial: configurável via stop_loss_pct abaixo da entrada.
    - Proteção: após min_bars_for_protection dias e lucro > gain_threshold_pct,
      move stop para stop_gain_pct acima da entrada.

    Observações
    -----------
    - Sem vendas a descoberto.
    - Modelo validado no **gráfico diário** no livro, e explicitamente indicado como **não invertido** para venda.
    """

    # Parâmetros padrão (podem ser ajustados ao instanciar o Backtest)
    bb_period: int = 20
    bb_dev: float = 2.0

    # Parâmetros de stop loss e stop gain
    stop_loss_pct: float = 0.10       # Stop loss inicial (padrão: 10% abaixo da entrada)
    gain_threshold_pct: float = 0.015  # Limiar de ganho para ativar proteção (padrão: 1.5%)
    stop_gain_pct: float = 0.005      # Stop gain de proteção (padrão: 0.5% acima da entrada)
    min_bars_for_protection: int = 1   # Número mínimo de dias antes de ativar proteção de ganho

    def init(self) -> None:
        # Comentário: obtém a série de fechamentos para cálculo das Bandas de Bollinger via TA-Lib.
        close = self.data.Close

        # Comentário: converte para array numpy, pois TA-Lib espera arrays contíguos.
        close_np = np.asarray(close, dtype=float)

        # Comentário: calcula as Bandas de Bollinger (média, banda superior e banda inferior).
        # Utiliza período e desvios configuráveis; TA-Lib BBANDS retorna (upper, middle, lower).
        upper, middle, lower = talib.BBANDS(
            close_np,
            timeperiod=int(self.bb_period),
            nbdevup=float(self.bb_dev),
            nbdevdn=float(self.bb_dev),
            matype=0,  # 0 = SMA, conforme o uso clássico do livro
        )

        # Comentário: registra as séries calculadas em buffers internos do backtesting.py para uso no next().
        self.upper = self.I(lambda: upper)
        self.middle = self.I(lambda: middle)
        self.lower = self.I(lambda: lower)

        # Estados da operação para controle de stop
        self.last_stop = None          # nível atual do stop simulado
        self.entry_price = None        # preço de entrada registrado
        self.entry_idx = None          # índice (barra) de entrada

        # Comentário: verificação leve de frequência diária (opcional; não aborta execução).
        self._warn_if_not_daily_index()

    def _warn_if_not_daily_index(self) -> None:
        # Comentário: tenta inferir se o índice é diário; caso não seja, emite aviso via print.
        try:
            index = getattr(self.data, 'index', None)
            if isinstance(index, pd.DatetimeIndex) and len(index) > 10:
                # Comentário: mede mediana do delta entre barras.
                deltas = np.diff(index.values.astype('datetime64[ns]')).astype('timedelta64[D]').astype(float)
                median_days = np.nanmedian(deltas)
                if not (0.9 <= median_days <= 1.1):
                    print("[WalkingUpTheBands] Aviso: índice não aparenta ser diário (median Δ≈{:.2f}d).".format(median_days))
        except Exception:
            # Comentário: não interromper o fluxo em caso de problemas na inspeção.
            pass

    def next(self) -> None:
        # Comentário: pega o último fechamento e valores atuais das bandas.
        close = float(self.data.Close[-1])
        low = float(self.data.Low[-1])
        upper = float(self.upper[-1])
        lower = float(self.lower[-1])

        cur_idx = len(self.data.Close) - 1

        # ===== Regras de ENTRADA (somente compra) =====
        # Comentário: se não temos posição e o fechamento cruzou/está acima da banda superior => compra.
        if not self.position:
            # Comentário: checamos a condição do candle FECHAR acima da banda superior.
            if np.isfinite(upper) and close > upper:
                # Comentário: compra na próxima barra (backtesting.py envia ordem a mercado na abertura da próxima barra).
                self.buy()
                # Registra parâmetros da operação
                self.entry_price = close
                self.entry_idx = cur_idx
                # Stop inicial: stop_loss_pct abaixo da entrada (simulado)
                self.last_stop = self.entry_price * (1 - self.stop_loss_pct)
                return

        # ===== Regras de SAÍDA =====
        # Há posição aberta: sanidade
        if self.entry_price is None or self.entry_idx is None:
            return

        # Comentário: se estamos posicionados e o fechamento cruzou/está abaixo da banda inferior => sair.
        if self.position:
            # SAÍDA 1 (regra original): fechamento abaixo da banda inferior
            if np.isfinite(lower) and close < lower:
                # Comentário: encerra posição na próxima barra (ordem a mercado), fiel à regra de saída.
                self.position.close()
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None
                return

            # PROTEÇÃO: após min_bars_for_protection dias e lucro > gain_threshold_pct,
            # garante stop_gain_pct acima da entrada
            bars_in_trade = cur_idx - self.entry_idx
            unrealized_gain = close / self.entry_price - 1.0  # fração

            if bars_in_trade >= self.min_bars_for_protection and unrealized_gain > self.gain_threshold_pct:
                protect_stop = self.entry_price * (1 + self.stop_gain_pct)
                if self.last_stop is None:
                    self.last_stop = protect_stop
                else:
                    self.last_stop = max(self.last_stop, protect_stop)

            # SAÍDA 2 (stop simulado): fecha se a mínima da barra toca/perde o stop
            if self.last_stop is not None and low <= self.last_stop:
                self.position.close()
                self.entry_price = None
                self.entry_idx = None
                self.last_stop = None
                return


# def walkingUpTheBands(df, valor_inicial=10000, comissao=0.000):
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

#     bt = Backtest(df, WalkingUpTheBands, cash=valor_inicial, commission=comissao, trade_on_close=False, finalize_trades=True)
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