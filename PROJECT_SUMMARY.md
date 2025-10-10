# Trading Strategies Repository Context

## Project Overview
- **Goal**: Collection of trading strategies converted from Pine Script to Python
- **Framework**: Connors Trading framework with backtesting.py
- **Key Technologies**:
  - Python
  - pandas
  - numpy
  - talib
  - backtesting.py

## Logging Strategy
### Signal Emojis
- 🟢 BUY signals with reasoning
- 🔴 SELL/SHORT signals with reasoning
- 💰 BUY execution
- 💸 SELL execution

### Logging Details
- Price levels
- P&L percentages
- Strategy-specific context

## Current State
### Strategies Updated
- VolumeByTime
- VWAPPriceChannel
- SmartMoneyConcepts
- SimpleMarkov

### Validation Approach
- Manual backtesting validation

## Architectural Patterns
- Self-contained strategy directories
- Registry system for framework integration
- Consistent `init()` and `next()` method implementation
- Standardized risk management parameters

## Future Improvements
- Enhance logging patterns
- Add performance metrics logging

## Repository Status
- **Branch**: main
- **Last Commit**:
  - Hash: b765656
  - Message: "Add colorful logging to all non-multiTF strategies"
- **Current State**: Clean working tree