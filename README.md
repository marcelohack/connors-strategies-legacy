# connors-strategies

> Part of the [Connors Trading System](https://github.com/marcelohack/connors-playground) — Private strategy collection

## Overview

Shared strategy logic for the Connors trading system. Contains environment-agnostic strategy logic classes that can be used by both backtesting and live trading bots.

For experimental backtesting strategies, see [stratslab](https://github.com/marcelohack/connors-stratslab).

## Development Setup

**Prerequisites**: [uv](https://github.com/astral-sh/uv) (will install Python 3.13 if needed).
Sibling repo must be cloned alongside this one: `../core` (wired as an editable path source via `[tool.uv.sources]`).

```bash
uv sync --extra dev
```

uv reads `.python-version` to pick the interpreter and creates `.venv/` automatically. Run commands with `uv run <cmd>` (no activation needed), or `source .venv/bin/activate`.

## Usage

```python
from connors_strategies import LCRSI2Logic

logic = LCRSI2Logic(rsi_length=2, rsi_level=5.0)
signal = logic.generate_signal(snapshot, has_position=False)
# Returns "BUY", "SELL", or "HOLD"
```

## Package Contents

| Class | Description |
|-------|-------------|
| `BaseStrategyLogic` | Abstract base class for strategy signal generation |
| `LCRSI2Logic` | Larry Connors 2-Period RSI entry/exit logic |

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
