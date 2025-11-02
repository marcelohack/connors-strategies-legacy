"""
Test script to verify all YT strategies can be imported and run

This script tests each strategy with sample data to ensure:
1. Strategy imports correctly
2. Strategy can be instantiated
3. Backtest can be executed without errors
4. Basic statistics are generated
"""

from backtesting import Backtest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import strategies
from previous_day_high_low_break_retest import PreviousDayHighLowBreakRetest
from opening_range_break_retest import OpeningRangeBreakRetest
from order_block_break_retest import OrderBlockBreakRetest


def generate_sample_data(days=100, start_price=100):
    """
    Generate sample OHLCV data for testing

    Args:
        days: Number of trading days
        start_price: Starting price

    Returns:
        DataFrame with OHLCV data
    """
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')

    # Generate random price movements
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, days)  # 0.1% mean, 2% std
    close_prices = start_price * (1 + returns).cumprod()

    # Generate OHLCV
    data = pd.DataFrame({
        'Open': close_prices * (1 + np.random.uniform(-0.01, 0.01, days)),
        'High': close_prices * (1 + np.random.uniform(0.005, 0.02, days)),
        'Low': close_prices * (1 + np.random.uniform(-0.02, -0.005, days)),
        'Close': close_prices,
        'Volume': np.random.randint(1000000, 10000000, days)
    }, index=dates)

    # Ensure High is highest and Low is lowest
    data['High'] = data[['Open', 'High', 'Close']].max(axis=1)
    data['Low'] = data[['Open', 'Low', 'Close']].min(axis=1)

    return data


def test_strategy(strategy_class, strategy_name, data):
    """
    Test a strategy with sample data

    Args:
        strategy_class: Strategy class to test
        strategy_name: Name of strategy for logging
        data: OHLCV DataFrame

    Returns:
        dict with test results
    """
    print(f"\n{'='*60}")
    print(f"Testing {strategy_name}")
    print(f"{'='*60}")

    try:
        # Create backtest
        bt = Backtest(
            data,
            strategy_class,
            cash=1_000_000,
            commission=0.002
        )

        # Run backtest
        print(f"Running backtest...")
        stats = bt.run()

        # Print key statistics
        print(f"\nKey Statistics:")
        print(f"  Total Return: {stats['Return [%]']:.2f}%")
        print(f"  Sharpe Ratio: {stats['Sharpe Ratio']:.2f}")
        print(f"  Max Drawdown: {stats['Max. Drawdown [%]']:.2f}%")
        print(f"  Total Trades: {stats['# Trades']}")
        print(f"  Win Rate: {stats['Win Rate [%]']:.2f}%")

        if stats['# Trades'] > 0:
            print(f"  Avg Trade: {stats['Avg. Trade [%]']:.2f}%")

        print(f"\nTest PASSED for {strategy_name}")
        return {
            'status': 'PASSED',
            'trades': stats['# Trades'],
            'return': stats['Return [%]']
        }

    except Exception as e:
        print(f"\nTest FAILED for {strategy_name}")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'status': 'FAILED',
            'error': str(e)
        }


def main():
    """Run all strategy tests"""
    print("Generating sample data...")
    data = generate_sample_data(days=252)  # 1 year of trading days

    print(f"Data shape: {data.shape}")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    print(f"Price range: ${data['Close'].min():.2f} to ${data['Close'].max():.2f}")

    # Test each strategy
    results = {}

    results['PreviousDayHighLowBreakRetest'] = test_strategy(
        PreviousDayHighLowBreakRetest,
        "Previous Day High/Low Break and Retest",
        data
    )

    results['OpeningRangeBreakRetest'] = test_strategy(
        OpeningRangeBreakRetest,
        "Opening Range Break and Retest",
        data
    )

    results['OrderBlockBreakRetest'] = test_strategy(
        OrderBlockBreakRetest,
        "Order Block Break and Retest",
        data
    )

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    for strategy_name, result in results.items():
        status = result['status']
        if status == 'PASSED':
            print(f"{strategy_name}: {status} ({result['trades']} trades, {result['return']:.2f}% return)")
        else:
            print(f"{strategy_name}: {status} ({result.get('error', 'Unknown error')})")

    # Overall result
    all_passed = all(r['status'] == 'PASSED' for r in results.values())
    print(f"\n{'='*60}")
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - Check errors above")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
