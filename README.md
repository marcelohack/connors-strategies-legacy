# connors-strategies

> Part of the [Connors Trading System](https://github.com/marcelohack/connors-playground) — Private strategy collection

## Overview

A curated collection of trading strategies for use with [connors-backtest](https://github.com/marcelohack/connors-backtest). Each strategy is a standalone Python file that integrates with the Connors framework via the `@registry.register_strategy()` decorator.

This is **not** a pip package — strategies are loaded at runtime via the `--external-strategy` CLI parameter or by adding this directory to `PYTHONPATH`.

## Development Setup

**Prerequisites**: Python 3.13, [pyenv](https://github.com/pyenv/pyenv) + [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv)

```bash
# 1. Create and activate a virtual environment
pyenv virtualenv 3.13 connors-strategies
pyenv activate connors-strategies

# 2. Install connors packages from local checkouts (not on PyPI)
pip install -e ../core -e ../datafetch

# 3. Install backtest infrastructure (strategies depend on it)
pip install -e "../backtest[dev]"
```

A `.python-version` file is included so pyenv auto-activates when you `cd` into this directory.

## Usage

### Via CLI (`--external-strategy`)

```bash
# Run a strategy from this collection
python -m connors.cli.backtest \
  --external-strategy /path/to/connors-strategies/VolumeByTime/volume_by_time.py \
  --strategy VolumeByTime \
  --tickers AAPL --config america --datasource yfinance --timespan 6M

# Multi-timeframe strategy
python -m connors.cli.backtest \
  --external-strategy /path/to/connors-strategies/MultiTimeframeExample/multi_tf_momentum.py \
  --strategy MultiTFMomentum \
  --timeframes 1wk,1d --primary-timeframe 1d --tickers AAPL --timespan 1Y

# Moon Dev crypto strategy
python -m connors.cli.backtest \
  --external-strategy /path/to/connors-strategies/moon-dev/rbi_v3-10_20_2025/DivergentReversion/divergent_reversion.py \
  --strategy "rbi_v3-10_20_2025.DivergentReversion" \
  --tickers BTC-USD --cash 100000
```

### Via `{appHome}/strategies/`

Copy strategy directories into `~/.connors/strategies/` (or `$CONNORS_HOME/strategies/`) for automatic discovery by the Streamlit UI.

## Strategy Catalog

| Strategy | Directory | Description |
|----------|-----------|-------------|
| VolumeByTime | `VolumeByTime/` | Time-based volume anomaly detection |
| VWAPPriceChannel | `VWAPPriceChannel/` | Dynamic VWAP-based price channel breakouts |
| SmartMoneyConcepts | `SmartMoneyConcepts/` | Institutional trading methodology (order blocks, FVGs) |
| SimpleMarkov | `SimpleMarkov/` | Markov chain-based regime trading |
| MultiTFMomentum | `MultiTimeframeExample/` | Multi-timeframe momentum example |
| SimpleTrendFollow | `MultiTimeframeExample/` | Multi-timeframe trend following example |
| PartialElephantBars | `BR_AU_TradingBro/` | Elephant bar pattern detection |
| SaquaremaBoys (11) | `SaquaremaBoys/` | Collection of Brazilian trading strategies |
| YTStrategies (4) | `YTStrategies/` | YouTube-sourced strategy conversions |
| Moon Dev RBI v3 (10) | `moon-dev/rbi_v3-10_20_2025/` | Advanced divergence/momentum crypto strategies |

## Adding New Strategies

1. Create a directory: `MyStrategy/`
2. Create the strategy file: `my_strategy.py`
3. Use the registry decorator:

```python
from backtesting import Strategy
from connors_core.core.registry import registry

@registry.register_strategy("MyStrategy")
class MyStrategy(Strategy):
    param1 = 10

    def init(self):
        pass

    def next(self):
        pass
```

4. Add a `README.md` with documentation
5. Test via CLI: `python -m connors.cli.backtest --external-strategy MyStrategy/my_strategy.py --strategy MyStrategy ...`

## Related Packages

| Package | Description | Links |
|---------|-------------|-------|
| [connors-playground](https://github.com/marcelohack/connors-playground) | CLI + Streamlit UI (integration hub) | [README](https://github.com/marcelohack/connors-playground#readme) |
| [connors-backtest](https://github.com/marcelohack/connors-backtest) | Backtesting service + built-in strategies | [README](https://github.com/marcelohack/connors-backtest#readme) |
| [connors-core](https://github.com/marcelohack/connors-core) | Registry, config, indicators, metrics | [README](https://github.com/marcelohack/connors-core#readme) |
| [connors-screener](https://github.com/marcelohack/connors-screener) | Stock screening system | [README](https://github.com/marcelohack/connors-screener#readme) |
| [connors-datafetch](https://github.com/marcelohack/connors-datafetch) | Multi-source data downloader | [README](https://github.com/marcelohack/connors-datafetch#readme) |
| [connors-sr](https://github.com/marcelohack/connors-sr) | Support & Resistance calculator | [README](https://github.com/marcelohack/connors-sr#readme) |
| [connors-regime](https://github.com/marcelohack/connors-regime) | Market regime detection | [README](https://github.com/marcelohack/connors-regime#readme) |
| [connors-bots](https://github.com/marcelohack/connors-bots) | Automated trading bots | [README](https://github.com/marcelohack/connors-bots#readme) |

## License

MIT
