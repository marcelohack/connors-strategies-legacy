"""
Larry Williams 'Zero Loss' Setup Strategy

Estratégia de seguimento de tendência usando duas médias móveis de 3 períodos
(uma no high, outra no low) para entrar em pullbacks e sair em toques na média oposta.

Descrição:
    Esta estratégia identifica tendências e entra em pullbacks usando um sistema de
    duas médias móveis de curto prazo. A média móvel de 3 períodos calculada nos highs
    é usada para sinalizar saídas de posições long e entradas short. A média móvel de
    3 períodos calculada nos lows é usada para sinalizar entradas long e saídas short.

    O gerenciamento de stop é adaptativo: o stop é movido para o low de cada candle
    que faz nova máxima em uptrends, e para o high de cada candle que faz nova mínima
    em downtrends.

Regras de Entrada:
    LONG:
        - Preço está em uptrend (acima da MA de 55 períodos, se filtro ativado)
        - Candle fecha abaixo da MA de 3 períodos dos lows (pullback)
        - Stop inicial não excede max_initial_stop pontos

    SHORT:
        - Preço está em downtrend (abaixo da MA de 55 períodos, se filtro ativado)
        - Candle fecha acima da MA de 3 períodos dos highs (pullback)
        - Stop inicial não excede max_initial_stop pontos

Regras de Saída:
    LONG:
        - Candle fecha acima da MA de 3 períodos dos highs
        - OU stop trailing é atingido

    SHORT:
        - Candle fecha abaixo da MA de 3 períodos dos lows
        - OU stop trailing é atingido

Gerenciamento de Risco:
    - Stop inicial máximo: 250-300 pontos (configurável)
    - Trailing stop: Move para low/high de cada candle fazendo novas máximas/mínimas
    - Position sizing: Baseado no tamanho do stop inicial

Parâmetros:
    ma_period (int): Período para as médias móveis de high/low (padrão: 3)
    trend_ma_period (int): Período para a média móvel de tendência (padrão: 55)
    use_trend_filter (bool): Usar filtro de tendência (padrão: True)
    max_initial_stop (float): Stop loss inicial máximo em pontos (padrão: 300)
    enable_shorts (bool): Permitir posições short (padrão: True)
    risk_per_trade (float): Percentual de risco por trade (padrão: 0.02 = 2%)

Mercado Ideal:
    Mercados com tendência clara e direcional. Performance pode ser pobre em
    mercados laterais ou choppy.

Timeframe Sugerido:
    5m ou 15m (mas funciona em qualquer timeframe)

Autor: Larry Williams
Implementação: Moon Dev Trading
"""

from backtesting import Strategy
import numpy as np
import pandas as pd
import talib
from connors_core.core.registry import registry


@registry.register_strategy("LarryWilliamsZeroLoss")
class LarryWilliamsZeroLossStrategy(Strategy):
    """
    Larry Williams 'Zero Loss' Setup Strategy

    Estratégia de seguimento de tendência com duas MAs de 3 períodos e
    gerenciamento adaptativo de stop loss.
    """

    # Parâmetros da estratégia
    ma_period = 3  # Período para MAs de high/low
    trend_ma_period = 55  # Período para filtro de tendência
    use_trend_filter = True  # Usar filtro de tendência
    max_initial_stop = 300  # Stop loss inicial máximo em pontos
    enable_shorts = True  # Permitir posições short
    risk_per_trade = 0.02  # 2% de risco por trade

    def init(self):
        """
        Inicializa os indicadores da estratégia.

        Indicadores:
            - MA de 3 períodos dos highs (para saídas long/entradas short)
            - MA de 3 períodos dos lows (para entradas long/saídas short)
            - MA de 55 períodos do close (filtro de tendência)
            - Highest high e lowest low para trailing stops
        """
        # Médias móveis principais do sistema
        self.ma_high = self.I(talib.SMA, self.data.High, timeperiod=self.ma_period)
        self.ma_low = self.I(talib.SMA, self.data.Low, timeperiod=self.ma_period)

        # Filtro de tendência (opcional)
        self.ma_trend = self.I(talib.SMA, self.data.Close, timeperiod=self.trend_ma_period)

        # Rastreamento de extremos para trailing stops
        # Highest high nos últimos N períodos (para identificar novos highs)
        self.highest_high = self.I(talib.MAX, self.data.High, timeperiod=5)
        self.lowest_low = self.I(talib.MIN, self.data.Low, timeperiod=5)

        # Variáveis de controle de posição
        self.entry_price = None
        self.entry_bar = None
        self.trailing_stop = None
        self.position_highest = None  # Maior high desde entrada (longs)
        self.position_lowest = None  # Menor low desde entrada (shorts)

    def next(self):
        """
        Executa a lógica de trading em cada candle.

        Fluxo:
            1. Gerencia posições existentes (trailing stops e saídas)
            2. Avalia novas entradas se não há posição
            3. Atualiza trailing stops baseado em novos extremos
        """
        # Valores atuais
        price = self.data.Close[-1]
        high = self.data.High[-1]
        low = self.data.Low[-1]

        # Verifica tendência se filtro estiver ativo
        if self.use_trend_filter:
            is_uptrend = price > self.ma_trend[-1]
            is_downtrend = price < self.ma_trend[-1]
        else:
            # Sem filtro de tendência, sempre permite ambas direções
            is_uptrend = True
            is_downtrend = True

        # === GERENCIAMENTO DE POSIÇÕES EXISTENTES ===
        if self.position:
            if self.position.is_long:
                # === LONG POSITION MANAGEMENT ===

                # Atualiza o highest high desde entrada
                if self.position_highest is None or high > self.position_highest:
                    self.position_highest = high
                    # Move trailing stop para o low deste candle
                    self.trailing_stop = low
                    print(f"🔒 Trailing Stop Long atualizado: ${self.trailing_stop:.2f} (Novo High: ${high:.2f})")

                # Verifica exit por stop trailing
                if self.trailing_stop is not None and low <= self.trailing_stop:
                    print(f"🛑 Exit Long por Trailing Stop @ ${price:.2f} (Stop: ${self.trailing_stop:.2f})")
                    self.position.close()
                    self._reset_position_tracking()
                    return

                # Verifica exit por close acima da MA high
                if price > self.ma_high[-1]:
                    exit_reason = "Close acima MA High"
                    profit = price - self.entry_price
                    print(f"🌙 Exit Long @ ${price:.2f} | {exit_reason} | P&L: ${profit:.2f}")
                    self.position.close()
                    self._reset_position_tracking()
                    return

            else:  # Short position
                # === SHORT POSITION MANAGEMENT ===

                # Atualiza o lowest low desde entrada
                if self.position_lowest is None or low < self.position_lowest:
                    self.position_lowest = low
                    # Move trailing stop para o high deste candle
                    self.trailing_stop = high
                    print(f"🔒 Trailing Stop Short atualizado: ${self.trailing_stop:.2f} (Novo Low: ${low:.2f})")

                # Verifica exit por stop trailing
                if self.trailing_stop is not None and high >= self.trailing_stop:
                    print(f"🛑 Exit Short por Trailing Stop @ ${price:.2f} (Stop: ${self.trailing_stop:.2f})")
                    self.position.close()
                    self._reset_position_tracking()
                    return

                # Verifica exit por close abaixo da MA low
                if price < self.ma_low[-1]:
                    exit_reason = "Close abaixo MA Low"
                    profit = self.entry_price - price
                    print(f"🌙 Exit Short @ ${price:.2f} | {exit_reason} | P&L: ${profit:.2f}")
                    self.position.close()
                    self._reset_position_tracking()
                    return

        # === SINAIS DE ENTRADA (apenas se não há posição) ===
        else:
            # === LONG ENTRY SIGNAL ===
            # Condições: uptrend + close abaixo MA low + stop inicial válido
            if is_uptrend and price < self.ma_low[-1]:
                # Calcula stop inicial (abaixo do low atual)
                initial_stop = low
                stop_distance = price - initial_stop

                # Valida se stop não excede máximo permitido
                if stop_distance > 0 and stop_distance <= self.max_initial_stop:
                    # Calcula position size baseado no risco
                    risk_amount = self.equity * self.risk_per_trade
                    position_size = int(round(risk_amount / stop_distance))

                    if position_size > 0:
                        print(f"🚀 LONG Entry @ ${price:.2f} | Stop: ${initial_stop:.2f} | Risk: ${stop_distance:.2f}")
                        print(f"   Sinal: Close (${price:.2f}) < MA Low (${self.ma_low[-1]:.2f})")

                        # Entra na posição
                        self.buy(size=position_size)

                        # Inicializa tracking
                        self.entry_price = price
                        self.entry_bar = len(self.data)
                        self.trailing_stop = initial_stop
                        self.position_highest = high
                        self.position_lowest = None

            # === SHORT ENTRY SIGNAL ===
            # Condições: downtrend + close acima MA high + stop inicial válido + shorts habilitados
            elif self.enable_shorts and is_downtrend and price > self.ma_high[-1]:
                # Calcula stop inicial (acima do high atual)
                initial_stop = high
                stop_distance = initial_stop - price

                # Valida se stop não excede máximo permitido
                if stop_distance > 0 and stop_distance <= self.max_initial_stop:
                    # Calcula position size baseado no risco
                    risk_amount = self.equity * self.risk_per_trade
                    position_size = int(round(risk_amount / stop_distance))

                    if position_size > 0:
                        print(f"🔻 SHORT Entry @ ${price:.2f} | Stop: ${initial_stop:.2f} | Risk: ${stop_distance:.2f}")
                        print(f"   Sinal: Close (${price:.2f}) > MA High (${self.ma_high[-1]:.2f})")

                        # Entra na posição
                        self.sell(size=position_size)

                        # Inicializa tracking
                        self.entry_price = price
                        self.entry_bar = len(self.data)
                        self.trailing_stop = initial_stop
                        self.position_highest = None
                        self.position_lowest = low

    def _reset_position_tracking(self):
        """
        Reseta todas as variáveis de tracking de posição após saída.
        """
        self.entry_price = None
        self.entry_bar = None
        self.trailing_stop = None
        self.position_highest = None
        self.position_lowest = None


# === CÓDIGO DE TESTE STANDALONE ===
if __name__ == "__main__":
    """
    Exemplo de uso standalone da estratégia.

    Execute este arquivo diretamente para testar a estratégia:
        python larry_williams_zero_loss_setup.py
    """
    from backtesting import Backtest
    import yfinance as yf

    print("=" * 80)
    print("LARRY WILLIAMS 'ZERO LOSS' SETUP STRATEGY - Backtest")
    print("=" * 80)

    # Download dados do Yahoo Finance
    print("\n📊 Baixando dados do Yahoo Finance...")
    ticker = "SPY"  # S&P 500 ETF
    start_date = "2023-01-01"
    end_date = "2024-01-01"

    data = yf.download(ticker, start=start_date, end=end_date, interval="15m")

    # Limpa e prepara os dados
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)

    data.columns = data.columns.str.strip().str.lower()
    data = data.drop(columns=[col for col in data.columns if 'unnamed' in col.lower()], errors='ignore')
    data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

    print(f"✅ Dados carregados: {len(data)} candles de {data.index[0]} a {data.index[-1]}")

    # Configura e executa o backtest
    print("\n🔄 Executando backtest...")
    bt = Backtest(
        data,
        LarryWilliamsZeroLossStrategy,
        cash=1_000_000,
        commission=0.002,
        exclusive_orders=True
    )

    # Roda com parâmetros padrão
    stats = bt.run()

    # Exibe resultados
    print("\n" + "=" * 80)
    print("RESULTADOS DO BACKTEST")
    print("=" * 80)
    print(stats)

    print("\n" + "=" * 80)
    print("PARÂMETROS DA ESTRATÉGIA")
    print("=" * 80)
    print(stats._strategy)
