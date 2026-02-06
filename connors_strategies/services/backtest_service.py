"""
Backtest Service

Provides high-level interface for backtesting operations,
integrating with strategies, data sources, and result management.
"""

import importlib.util
import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import backtesting
import pandas as pd
from backtesting import Backtest

# Configure backtesting library for proper multiprocessing
backtesting.set_bokeh_output(notebook=False)
if multiprocessing.get_start_method() == "spawn":
    backtesting.Pool = multiprocessing.Pool

import connors_datafetch.datasources.polygon
import connors_datafetch.datasources.yfinance

# Import all strategies and datasources to ensure registration
import connors_strategies.strategies.lcrsi2  # noqa: F401
import connors_strategies.strategies.lcrsi2_talipp  # noqa: F401
import connors_strategies.strategies.ifr2  # noqa: F401
import connors_strategies.strategies.rsi_crypto  # noqa: F401

# Import multi-timeframe strategy base classes
try:
    from connors_strategies.strategies.multitimeframe.base import MultiTimeframeStrategy
    # Also import the multitimeframe module to ensure it's loaded
    import connors_strategies.strategies.multitimeframe
    # Import specific multi-timeframe strategies
    import connors_strategies.strategies.multitimeframe.mtf_rsi2  # noqa: F401
except ImportError:
    MultiTimeframeStrategy = None
from connors_core.config.manager import BacktestConfigManager
from connors_core.core.parameter_override import parse_parameter_string
from connors_core.core.registry import registry
from connors_core.core.strategy_parameter_override import (
    create_strategy_with_params,
    get_strategy_parameter_info,
)
from connors_datafetch.core.timespan import TimespanCalculator
from connors_datafetch.core.registry import registry as datasource_registry
from connors_strategies.services.base import BaseService
from connors_core.utils.datetime_utils import add_utc_offset

@dataclass
class BacktestResult:
    """Container for backtest results"""

    ticker: str
    strategy: str
    results: Any  # Backtest results object
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    start_date: str
    end_date: str
    market: str
    parameters: Dict[str, Any]
    was_optimized: bool = False
    optimal_parameters: Optional[Dict[str, Any]] = None
    # Multi-timeframe specific fields
    is_multitimeframe: bool = False
    timeframes_used: Optional[List[str]] = None
    primary_timeframe: Optional[str] = None
    tf_data: Optional[Dict[str, pd.DataFrame]] = None


class BacktestService(BaseService):
    """Service for backtesting operations"""

    def __init__(self) -> None:
        super().__init__()
        self.registry = registry
        self.config_manager = BacktestConfigManager()

    def get_strategies(self) -> List[str]:
        """Get list of available strategies"""
        try:
            return self.registry.list_strategies()
        except Exception as e:
            self.logger.error(f"Failed to get strategies: {e}")
            return []

    def get_strategy_info(self, strategy: str) -> Dict[str, Any]:
        """Get detailed information about a strategy including parameters"""
        try:
            self._validate_required_params({"strategy": strategy}, ["strategy"])

            strategy_class = self.registry._strategies.get(strategy)
            if not strategy_class:
                self.logger.error(f"Strategy '{strategy}' not found")
                return {}

            # Get parameter information
            param_info = get_strategy_parameter_info(strategy_class)

            return {
                "name": strategy,
                "class_name": strategy_class.__name__,
                "description": strategy_class.__doc__ or "No description available",
                "parameters": param_info,
            }
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Failed to get strategy info for {strategy}: {e}")
            return {}

    def get_datasources(self) -> List[str]:
        """Get list of available data sources"""
        try:
            return datasource_registry.list_datasources()
        except Exception as e:
            self.logger.error(f"Failed to get datasources: {e}")
            return []

    def get_market_configs(self) -> List[str]:
        """Get list of available market configurations"""
        try:
            return self.config_manager.list_configs()
        except Exception as e:
            self.logger.error(f"Failed to get market configs: {e}")
            return []

    def get_market_config_info(self, config_name: str) -> Dict[str, Any]:
        """Get detailed information about a market configuration"""
        try:
            self._validate_required_params(
                {"config_name": config_name}, ["config_name"]
            )

            config = self.config_manager.get_market_config(config_name)
            return {
                "name": config.name,
                "yf_ticker_suffix": config.yf_ticker_suffix,
                "cash": config.cash,
                "utc_offset": config.utc_offset,
            }
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Failed to get market config info: {e}")
            return {}

    def get_available_timeframes(self) -> List[str]:
        """Get list of available predefined timeframes"""
        return TimespanCalculator.get_available_timespans()

    def get_timeframe_description(self, timeframe: str) -> str:
        """Get human-readable description of timeframe"""
        return TimespanCalculator.get_timespan_description(timeframe)

    def calculate_dates_from_timeframe(
        self,
        timeframe: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Calculate start and end dates based on timeframe or explicit dates.

        Args:
            timeframe: Pre-defined timeframe (e.g., "1Y", "6M", "YTD") or None for custom dates
            start_date: Custom start date in YYYY-MM-DD format
            end_date: Custom end date in YYYY-MM-DD format

        Returns:
            Dictionary with 'start' and 'end' keys containing dates in YYYY-MM-DD format
        """
        try:
            start, end = TimespanCalculator.calculate_dates(
                timespan=timeframe, start_date=start_date, end_date=end_date
            )
            return {"start": start, "end": end}
        except Exception as e:
            self.logger.error(f"Failed to calculate dates from timeframe: {e}")
            # Fallback to default 1Y
            return self.get_default_dates()

    def validate_dataset_file(self, file_path: str) -> Dict[str, Any]:
        """
        Validate a dataset file for backtesting compatibility
        Supports both CSV and JSON formats

        Returns dict with validation results and file info
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {"valid": False, "error": f"File not found: {file_path}"}

            file_lower = file_path.lower()
            if not (file_lower.endswith(".csv") or file_lower.endswith(".json")):
                return {"valid": False, "error": "File must be a CSV or JSON file"}

            # Try to load and validate the file
            if file_lower.endswith(".csv"):
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            else:  # JSON file
                with open(file_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)

                # Handle JSON format with "data" wrapper
                if isinstance(json_data, dict) and "data" in json_data:
                    json_data = json_data["data"]

                if not isinstance(json_data, list):
                    return {
                        "valid": False,
                        "error": "JSON must be an array of OHLCV records or have a 'data' array field",
                    }

                if not json_data:
                    return {"valid": False, "error": "JSON file is empty"}

                # Convert JSON to DataFrame
                df = pd.DataFrame(json_data)

                # Handle date column - could be 'date', 'Date' or index
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                    df.set_index("date", inplace=True)
                elif "Date" in df.columns:  # Legacy support for uppercase
                    df["Date"] = pd.to_datetime(df["Date"])
                    df.set_index("Date", inplace=True)
                else:
                    # If no date column, assume index contains dates
                    df.index = pd.to_datetime(df.index)

            # Check for required OHLCV columns (excluding date since it can be index or column)
            ohlcv_data_columns = [col for col in ["date", "open", "high", "low", "close", "volume"] if col != "date"]
            missing_columns = [
                col for col in ohlcv_data_columns if col not in df.columns
            ]

            if missing_columns:
                return {
                    "valid": False,
                    "error": f"Missing required OHLCV columns: {missing_columns}",
                    "available_columns": list(df.columns),
                }

            extra_columns = [col for col in df.columns if col not in ohlcv_data_columns]
            if extra_columns:
                return {
                    "valid": False,
                    "error": f"Extra columns not allowed: {extra_columns}",
                    "required_columns": ohlcv_data_columns,
                }

            return {
                "valid": True,
                "shape": df.shape,
                "date_range": {
                    "start": df.index.min().strftime("%Y-%m-%d"),
                    "end": df.index.max().strftime("%Y-%m-%d"),
                },
                "columns": list(df.columns),
            }

        except Exception as e:
            return {"valid": False, "error": f"Failed to validate file: {str(e)}"}

    def get_default_dates(self, market_config: Optional[str] = None) -> Dict[str, str]:
        """Get default start and end dates based on market configuration"""
        try:
            # Get UTC offset for market
            utc_offset = 0
            if market_config:
                try:
                    config = self.config_manager.get_market_config(market_config)
                    utc_offset = config.utc_offset
                except Exception:
                    pass  # Use default offset

            # Calculate dates
            end = add_utc_offset(datetime.now(timezone.utc), utc_offset).date()
            start = date(year=end.year - 1, month=end.month, day=end.day)

            return {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d"),
            }
        except Exception:
            # Fallback to simple calculation
            end = datetime.now().date()
            start = date(year=end.year - 1, month=end.month, day=end.day)
            return {
                "start": start.strftime("%Y-%m-%d"),
                "end": end.strftime("%Y-%m-%d"),
            }

    def _run_optimization(self, bt: Backtest, optimize_params: Dict[str, Any]):
        """
        Run optimization in a separate method to handle multiprocessing issues
        """
        # Make a copy to avoid modifying the original
        params = optimize_params.copy()

        # Extract optimization configuration
        maximize = params.pop("maximize", "Sharpe Ratio")
        constraint = params.pop("constraint", None)
        max_tries = params.pop("max_tries", None)
        random_state = params.pop("random_state", None)

        # Build optimization kwargs
        opt_kwargs = {"maximize": maximize}
        if constraint is not None:
            opt_kwargs["constraint"] = constraint
        if max_tries is not None:
            opt_kwargs["max_tries"] = max_tries
        if random_state is not None:
            opt_kwargs["random_state"] = random_state

        # Use sequential processing to avoid multiprocessing issues
        # This forces single-threaded execution
        import threading

        old_pool = getattr(backtesting, "Pool", None)

        # Use a dummy pool that just runs sequentially
        class SequentialPool:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def imap_unordered(self, func, iterable):
                return map(func, iterable)

            def imap(self, func, iterable):
                return map(func, iterable)

            def map(self, func, iterable):
                return list(map(func, iterable))

            def close(self):
                pass

            def join(self):
                pass

        backtesting.Pool = SequentialPool

        try:
            results = bt.optimize(**params, **opt_kwargs)

            # Extract optimal parameters from the strategy
            if hasattr(results, "_strategy") and results._strategy:
                strategy_obj = results._strategy
                optimal_params = {}

                # Extract parameters from the optimized strategy
                for param_name in params.keys():
                    if hasattr(strategy_obj, param_name):
                        optimal_params[param_name] = getattr(strategy_obj, param_name)

                # Store optimal parameters in the results object for later access
                results._optimal_parameters = optimal_params

            return results
        finally:
            backtesting.Pool = old_pool

    def fetch_multi_timeframe_data(
        self,
        ticker: str,
        datasource: str,
        timeframes: List[str],
        start: str,
        end: str,
        market_config: str,
        primary_timeframe: Optional[str] = None,
        dataset_file: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch data for multiple timeframes and align them

        Args:
            ticker: Stock ticker symbol
            datasource: Data source name
            timeframes: List of timeframes to fetch (e.g., ['1w', '1d', '1h'])
            start: Start date (YYYY-MM-DD)
            end: End date (YYYY-MM-DD)
            market_config: Market configuration name
            primary_timeframe: Primary timeframe for alignment
            dataset_file: Optional dataset file (only for single timeframe)

        Returns:
            Dictionary mapping timeframes to their respective DataFrames
        """
        if dataset_file and len(timeframes) > 1:
            raise ValueError("Dataset files are only supported for single timeframe backtests")

        datasets = {}

        if dataset_file:
            # For single timeframe with dataset file
            df = self._load_dataset_from_file(dataset_file, ticker)
            # Prepare for backtesting
            df_prepared = self._prepare_dataframe_for_backtest(df)
            datasets[timeframes[0]] = df_prepared
        else:
            # Fetch data for each timeframe
            for tf in timeframes:
                try:
                    df = self._load_data_from_source(
                        datasource, ticker, start, end, tf, market_config
                    )
                    # Prepare each timeframe data for backtesting (convert to uppercase)
                    df_prepared = self._prepare_dataframe_for_backtest(df)
                    datasets[tf] = df_prepared
                except Exception as e:
                    self.logger.warning(f"Failed to fetch data for timeframe {tf}: {e}")
                    # Continue with other timeframes, but log the issue
                    continue

        if not datasets:
            raise ValueError(f"Failed to fetch data for any timeframe: {timeframes}")

        # If we have multiple timeframes, align them
        if len(datasets) > 1:
            return self._align_timeframes(datasets, primary_timeframe or timeframes[-1])

        return datasets

    def _align_timeframes(
        self, datasets: Dict[str, pd.DataFrame], primary_tf: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Align multiple timeframe data to prevent lookahead bias

        Args:
            datasets: Dictionary mapping timeframes to DataFrames
            primary_tf: Primary timeframe for alignment

        Returns:
            Dictionary of aligned DataFrames
        """
        if primary_tf not in datasets:
            raise ValueError(f"Primary timeframe '{primary_tf}' not found in datasets")

        primary_data = datasets[primary_tf]

        # Normalize timezone information across all datasets
        aligned_datasets = {}

        for tf, df in datasets.items():
            df_copy = df.copy()

            # Ensure consistent timezone handling
            if df_copy.index.tz is not None:
                # Convert timezone-aware to naive (local time)
                df_copy.index = df_copy.index.tz_convert(None)

            if tf == primary_tf:
                # Primary timeframe remains unchanged
                aligned_datasets[tf] = df_copy
            else:
                # For other timeframes, forward-fill data to avoid lookahead bias
                primary_copy = primary_data.copy()

                # Ensure primary data is also timezone-naive
                if primary_copy.index.tz is not None:
                    primary_copy.index = primary_copy.index.tz_convert(None)

                # Reindex to primary timeframe dates, forward-filling values
                # This ensures higher timeframe data is available on primary timeframe dates
                try:
                    if len(df_copy) > len(primary_copy):
                        # Higher frequency data - need to filter to primary timeframe
                        aligned_df = df_copy.reindex(primary_copy.index, method='ffill')
                    else:
                        # Lower frequency data - forward fill to primary timeframe
                        aligned_df = df_copy.reindex(primary_copy.index, method='ffill')

                    aligned_datasets[tf] = aligned_df.dropna()

                except Exception as e:
                    self.logger.warning(f"Failed to align timeframe {tf}: {e}")
                    # Fallback: just use original data
                    aligned_datasets[tf] = df_copy

        return aligned_datasets

    def _determine_primary_timeframe(self, timeframes: List[str]) -> str:
        """
        Determine the primary (shortest) timeframe from a list

        Args:
            timeframes: List of timeframes

        Returns:
            The shortest timeframe
        """
        # Define timeframe hierarchy (shortest to longest in minutes)
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30, '1h': 60, '4h': 240,
            '1d': 1440, '1wk': 10080, '1mo': 43200, '1M': 43200
        }

        # Find the shortest timeframe in our list
        valid_timeframes = [(tf, timeframe_minutes.get(tf, float('inf'))) for tf in timeframes]
        valid_timeframes.sort(key=lambda x: x[1])

        if not valid_timeframes:
            raise ValueError("No valid timeframes provided")

        return valid_timeframes[0][0]

    def _is_multitimeframe_strategy(self, strategy_class) -> bool:
        """
        Check if a strategy is a multi-timeframe strategy

        Args:
            strategy_class: The strategy class to check

        Returns:
            True if it's a multi-timeframe strategy
        """
        if MultiTimeframeStrategy is None:
            return False

        try:
            timeframes = getattr(strategy_class, 'timeframes', [])
            # Handle both real lists and Mock objects
            if hasattr(timeframes, '__len__'):
                return len(timeframes) > 0
            else:
                # If it's a Mock or other object without __len__, assume it's not multi-timeframe
                return False
        except (TypeError, AttributeError):
            # Fallback for any other issues with Mock objects
            return False

    def run_backtest(
        self,
        ticker: str,
        strategy: str,
        datasource: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        market_config: str = "australia",
        strategy_params: Optional[Dict[str, Any]] = None,
        strategy_params_string: Optional[str] = None,
        dataset_file: Optional[str] = None,
        external_strategy_file: Optional[str] = None,
        cash: float = 10000,
        commission: float = 0.0025,
        trade_on_close: bool = True,
        finalize_trades: bool = False,
        optimize: bool = False,
        optimize_params: Optional[Dict[str, Any]] = None,
        timeframe: Optional[str] = None,
        # Multi-timeframe parameters
        timeframes: Optional[List[str]] = None,
        primary_timeframe: Optional[str] = None,
    ) -> BacktestResult:
        """
        Run a backtest with specified parameters

        Args:
            ticker: Stock ticker symbol
            strategy: Strategy name
            datasource: Data source name
            start: Start date (YYYY-MM-DD) - optional if timeframe provided
            end: End date (YYYY-MM-DD) - optional if timeframe provided
            interval: Data interval (1d, 1wk, 1mo)
            timeframe: Pre-defined timeframe (e.g., "1Y", "6M", "YTD")
            market_config: Market configuration name
            strategy_params: Strategy parameter overrides as dict
            strategy_params_string: Strategy parameter overrides as string
            dataset_file: Optional CSV file to use instead of downloading
            cash: Initial cash amount
            commission: Commission rate
            trade_on_close: Whether to trade on close price
            finalize_trades: Whether to finalize trades at end
            optimize: Whether to run optimization
            optimize_params: Optimization parameters for bt.optimize()
            timeframes: List of timeframes for multi-timeframe strategies (e.g., ['1w', '1d', '1h'])
            primary_timeframe: Primary timeframe for execution (overrides interval if provided)

        Returns:
            BacktestResult object containing all results
        """
        try:
            # Calculate dates from timeframe if not provided
            if timeframe or not (start and end):
                start, end = TimespanCalculator.calculate_dates(
                    timespan=timeframe, start_date=start, end_date=end
                )

            self._validate_required_params(
                {
                    "ticker": ticker,
                    "strategy": strategy,
                    "datasource": datasource,
                    "start": start,
                    "end": end,
                },
                ["ticker", "strategy", "datasource", "start", "end"],
            )

            # Handle external strategy file loading if provided
            if external_strategy_file:
                try:
                    loaded_strategy_name = self.load_external_strategy(
                        external_strategy_file, strategy
                    )
                    strategy = loaded_strategy_name
                except Exception as e:
                    raise ValueError(f"Failed to load external strategy: {e}")

            # Get strategy class from registry
            strategy_class = self.registry._strategies.get(strategy)
            if not strategy_class:
                raise ValueError(
                    f"Strategy '{strategy}' not found. Available: {self.get_strategies()}"
                )

            # Parse and apply strategy parameters
            parsed_params = {}
            if strategy_params_string:
                parsed_params = parse_parameter_string(strategy_params_string)
            if strategy_params:
                parsed_params.update(strategy_params)

            if parsed_params:
                strategy_class = create_strategy_with_params(
                    strategy_class, parsed_params
                )

            # Determine if this is a multi-timeframe strategy
            is_multitf_strategy = self._is_multitimeframe_strategy(strategy_class)
            tf_data = None

            # Handle multi-timeframe vs single timeframe data loading
            if timeframes or is_multitf_strategy:
                # Multi-timeframe strategy
                if timeframes:
                    # Timeframes explicitly provided
                    strategy_timeframes = timeframes
                else:
                    # Get timeframes from strategy class
                    strategy_timeframes = getattr(strategy_class, 'timeframes', [])

                if not strategy_timeframes:
                    raise ValueError("Multi-timeframe strategy requires timeframes to be specified")

                # Determine primary timeframe
                if primary_timeframe:
                    if primary_timeframe not in strategy_timeframes:
                        raise ValueError(f"Primary timeframe '{primary_timeframe}' must be in timeframes list: {strategy_timeframes}")
                    primary_tf = primary_timeframe
                elif hasattr(strategy_class, 'primary_timeframe') and strategy_class.primary_timeframe:
                    primary_tf = strategy_class.primary_timeframe
                else:
                    primary_tf = self._determine_primary_timeframe(strategy_timeframes)

                # Fetch multi-timeframe data
                tf_data = self.fetch_multi_timeframe_data(
                    ticker, datasource, strategy_timeframes, start, end,
                    market_config, primary_tf, dataset_file
                )

                # Use primary timeframe data for backtesting
                df = tf_data[primary_tf]

            else:
                # Single timeframe strategy (existing logic)
                if dataset_file:
                    df = self._load_dataset_from_file(dataset_file, ticker)
                else:
                    df = self._load_data_from_source(
                        datasource, ticker, start, end, interval, market_config
                    )

            # Convert to uppercase columns required by backtesting library
            df_backtest = self._prepare_dataframe_for_backtest(df)

            # For multi-timeframe strategies, set up the timeframe data
            if tf_data:
                # Check if the strategy class has the set_timeframe_data method
                if hasattr(strategy_class, 'set_timeframe_data') or (MultiTimeframeStrategy and issubclass(strategy_class, MultiTimeframeStrategy)):
                    # Create a custom strategy class that includes timeframe data
                    class MultiTimeframeStrategyWrapper(strategy_class):
                        def __init__(self, broker=None, data=None, params=None):
                            super().__init__(broker, data, params)
                            self.set_timeframe_data(tf_data)

                    strategy_class = MultiTimeframeStrategyWrapper
                else:
                    # Strategy doesn't support multi-timeframe, but we can still pass the data
                    # by adding the method dynamically
                    class MultiTimeframeStrategyWrapper(strategy_class):
                        def __init__(self, broker=None, data=None, params=None):
                            super().__init__(broker, data, params)
                            self.tf_data = tf_data

                        def set_timeframe_data(self, tf_data):
                            self.tf_data = tf_data

                        def get_timeframe_data(self, timeframe):
                            if timeframe not in self.tf_data:
                                raise ValueError(f"Timeframe '{timeframe}' not available. Available: {list(self.tf_data.keys())}")
                            return self.tf_data[timeframe]

                    strategy_class = MultiTimeframeStrategyWrapper

            # Run backtest
            bt = Backtest(
                df_backtest,
                strategy_class,
                cash=cash,
                commission=commission,
                trade_on_close=trade_on_close,
                finalize_trades=finalize_trades,
            )

            if optimize and optimize_params:
                # Use helper method to handle multiprocessing issues
                results = self._run_optimization(bt, optimize_params)
            else:
                results = bt.run()

            # Get market config info
            config_info = self.get_market_config_info(market_config)

            # Check if optimization was performed and extract optimal parameters
            was_optimized = optimize and optimize_params
            optimal_params = None
            if was_optimized and hasattr(results, "_optimal_parameters"):
                optimal_params = results._optimal_parameters

            # Prepare multi-timeframe information
            is_multitf = tf_data is not None
            timeframes_used = list(tf_data.keys()) if tf_data else None
            primary_tf = primary_tf if tf_data else None

            return BacktestResult(
                ticker=ticker,
                strategy=strategy,
                results=results,
                trades=results["_trades"],
                equity_curve=results["_equity_curve"],
                start_date=start,
                end_date=end,
                market=config_info.get("name", market_config),
                parameters=parsed_params,
                was_optimized=was_optimized,
                optimal_parameters=optimal_params,
                # Multi-timeframe fields
                is_multitimeframe=is_multitf,
                timeframes_used=timeframes_used,
                primary_timeframe=primary_tf,
                tf_data=tf_data,
            )

        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            raise

    def _load_dataset_from_file(self, file_path: str, ticker: str) -> pd.DataFrame:
        """Load and validate dataset from CSV or JSON file"""
        validation = self.validate_dataset_file(file_path)
        if not validation["valid"]:
            raise ValueError(f"Invalid dataset file: {validation['error']}")

        # Load the file based on format
        file_lower = file_path.lower()
        if file_lower.endswith(".csv"):
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        else:  # JSON file
            with open(file_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            # Handle JSON format with "data" wrapper (backward compatibility)
            if isinstance(json_data, dict) and "data" in json_data:
                json_data = json_data["data"]

            # Convert JSON to DataFrame
            df = pd.DataFrame(json_data)

            # Handle date column - could be 'date', 'Date' or index
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df.set_index("date", inplace=True)
            elif "Date" in df.columns:  # Legacy support for uppercase
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
            else:
                # If no date column, assume index contains dates
                df.index = pd.to_datetime(df.index)

        # Select only the OHLCV data columns (excluding date since it's now the index)
        ohlcv_data_columns = [col for col in ["date", "open", "high", "low", "close", "volume"] if col != "date"]
        # Try lowercase columns first, fall back to uppercase for backward compatibility
        available_cols = list(df.columns)
        cols_to_select = []
        for col in ohlcv_data_columns:
            if col in available_cols:
                cols_to_select.append(col)
            elif (
                col.title() in available_cols
            ):  # Check for Title case (Open, High, etc)
                cols_to_select.append(col.title())

        df = df[cols_to_select]
        # Rename to lowercase for consistency
        df.columns = df.columns.str.lower()
        df = df.sort_index()

        return df

    def _prepare_dataframe_for_backtest(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert DataFrame with lowercase columns to uppercase format required by backtesting library
        """
        df_backtest = df.copy()

        # Map lowercase column names to uppercase format expected by backtesting library
        column_mapping = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }

        # Rename columns to uppercase
        df_backtest = df_backtest.rename(columns=column_mapping)

        return df_backtest

    def load_external_strategy(
        self, file_path: str, strategy_name: Optional[str] = None
    ) -> str:
        """
        Load an external strategy from a Python file and register it

        Args:
            file_path: Path to the Python file containing the strategy
            strategy_name: Optional name to register the strategy under
                          If not provided, will try to extract from @registry.register_strategy decorator

        Returns:
            The name the strategy was registered under
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Strategy file not found: {file_path}")

            if not file_path.suffix == ".py":
                raise ValueError("Strategy file must be a Python (.py) file")

            # Create module spec and load the module
            module_name = f"external_strategy_{file_path.stem}_{hash(str(file_path))}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module from {file_path}")

            module = importlib.util.module_from_spec(spec)

            # Add the module to sys.modules to ensure proper import context
            import sys

            sys.modules[module_name] = module

            # Ensure the registry is available in the module's namespace
            module.__dict__["registry"] = self.registry

            # Also make sure common imports are available
            try:
                import backtesting

                module.__dict__["Strategy"] = backtesting.Strategy
                module.__dict__["backtesting"] = backtesting
            except ImportError:
                pass

            try:
                import talib

                module.__dict__["talib"] = talib
            except ImportError:
                pass

            try:
                import statsmodels
                import statsmodels.api as sm

                module.__dict__["sm"] = sm
                module.__dict__["statsmodels"] = statsmodels
            except ImportError:
                pass

            try:
                import pandas_ta as ta

                module.__dict__["ta"] = ta
                module.__dict__["pandas_ta"] = ta
            except ImportError:
                pass

            # Store current strategies to detect newly registered ones
            existing_strategies = set(self.registry._strategies.keys())

            # Execute the module (this will run the @registry.register_strategy decorators)
            try:
                spec.loader.exec_module(module)
            except Exception as exec_error:
                # Provide more detailed error information
                raise ImportError(f"Failed to execute module: {exec_error}")

            # Find newly registered strategies
            new_strategies = set(self.registry._strategies.keys()) - existing_strategies

            # If no strategies were registered via decorator, try to find and register Strategy classes manually
            if not new_strategies:
                strategy_classes = []
                # Common base class names to exclude from registration
                excluded_base_classes = {
                    'MultiTimeframeStrategy', 'Strategy', 'BaseStrategy',
                    'AbstractStrategy', 'StrategyBase'
                }

                for attr_name in dir(module):
                    try:
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and hasattr(attr, "__bases__")
                            and any("Strategy" in str(base) for base in attr.__bases__)
                            and attr_name not in excluded_base_classes
                            and not attr_name.startswith('_')  # Exclude private classes
                            and hasattr(attr, '__module__')  # Ensure it's defined in this module
                            and module.__name__ in attr.__module__  # Class is defined in the loaded module
                        ):
                            strategy_classes.append((attr_name, attr))
                    except Exception:
                        continue

                if not strategy_classes:
                    raise ValueError(
                        "No Strategy classes found in the module. "
                        "Make sure your strategy class inherits from backtesting.Strategy"
                    )

                # If strategy_name is provided, use it; otherwise use the class name
                if strategy_name:
                    if len(strategy_classes) > 1:
                        # Check if strategy_name matches any of the found class names
                        matching_strategy = None
                        for class_name, strategy_class in strategy_classes:
                            if class_name == strategy_name:
                                matching_strategy = (class_name, strategy_class)
                                break

                        if matching_strategy:
                            # Use the matching strategy class
                            class_name, strategy_class = matching_strategy
                            self.registry._strategies[strategy_name] = strategy_class
                            strategy_class._registry_name = strategy_name
                            return strategy_name
                        else:
                            # No exact match, user needs to specify which class to use
                            raise ValueError(
                                f"Multiple Strategy classes found: {[name for name, _ in strategy_classes]}. "
                                f"Please specify one of these class names as strategy_name, or use @registry.register_strategy('name') decorator."
                            )
                    else:
                        # Single strategy, register with provided name
                        class_name, strategy_class = strategy_classes[0]
                        self.registry._strategies[strategy_name] = strategy_class
                        strategy_class._registry_name = strategy_name
                        return strategy_name
                else:
                    if len(strategy_classes) > 1:
                        raise ValueError(
                            f"Multiple Strategy classes found: {[name for name, _ in strategy_classes]}. Please use @registry.register_strategy('name') decorator or specify strategy_name."
                        )
                    class_name, strategy_class = strategy_classes[0]
                    # Use the class name as the strategy name
                    self.registry._strategies[class_name] = strategy_class
                    strategy_class._registry_name = class_name
                    return class_name

            # Handle case where strategy_name was provided but decorator was used
            if strategy_name and strategy_name not in new_strategies:
                if len(new_strategies) == 1:
                    # Re-register with the provided name
                    decorator_name = list(new_strategies)[0]
                    strategy_class = self.registry._strategies[decorator_name]
                    self.registry._strategies[strategy_name] = strategy_class
                    strategy_class._registry_name = strategy_name
                    # Remove the old registration
                    del self.registry._strategies[decorator_name]
                    return strategy_name
                else:
                    raise ValueError(
                        f"Requested strategy name '{strategy_name}' not found. Registered: {list(new_strategies)}"
                    )

            if len(new_strategies) > 1:
                raise ValueError(
                    f"Multiple strategies registered: {list(new_strategies)}. "
                    "Please specify strategy_name parameter to choose which one to use"
                )

            return list(new_strategies)[0]

        except Exception as e:
            self.logger.error(f"Failed to load external strategy from {file_path}: {e}")
            raise

    def _load_data_from_source(
        self,
        datasource: str,
        ticker: str,
        start: str,
        end: str,
        interval: str,
        market_config: str,
    ) -> pd.DataFrame:
        """Load data from specified data source"""
        # Get data source from registry
        datasource_instance = datasource_registry.create_datasource(datasource)

        # Get market configuration for ticker suffix
        config = self.config_manager.get_market_config(market_config)
        final_ticker = (
            ticker + config.yf_ticker_suffix if config.yf_ticker_suffix else ticker
        )

        # Fetch data
        df = cast(
            pd.DataFrame, datasource_instance.fetch(final_ticker, start, end, interval)
        )

        if df.empty:
            raise ValueError(
                f"No data found for {final_ticker} from {start} to {end} on {datasource}"
            )

        # Ensure columns are lowercase for consistency
        df.columns = df.columns.str.lower()
        if df.index.name:
            df.index.name = df.index.name.lower()

        return df

    def save_results_to_file(
        self,
        result: BacktestResult,
        save_results: bool = False,
        save_trades: bool = False,
        save_plot: bool = False,
    ) -> Dict[str, str]:
        """
        Save backtest results to organized file structure

        Returns dict with saved file paths
        """
        try:
            app_home = self._get_app_home()
            base_folder = app_home / "backtests" / result.strategy

            saved_files = {}

            # Include multi-timeframe info in filename if applicable
            if result.is_multitimeframe and result.timeframes_used:
                tf_suffix = "_" + "-".join(result.timeframes_used)
                if result.primary_timeframe:
                    tf_suffix += f"_primary-{result.primary_timeframe}"
            else:
                tf_suffix = ""

            # Save results
            if save_results:
                results_folder = base_folder / "results"
                self._ensure_directory_exists(results_folder)
                results_filename = (
                    results_folder
                    / f"{result.ticker}-{result.market}-{result.start_date}-{result.end_date}{tf_suffix}.txt"
                )

                # Create enhanced results content for multi-timeframe strategies
                results_content = result.results.to_string()
                if result.is_multitimeframe:
                    header = f"Multi-Timeframe Strategy Results\n"
                    header += f"Strategy: {result.strategy}\n"
                    header += f"Timeframes: {result.timeframes_used}\n"
                    header += f"Primary Timeframe: {result.primary_timeframe}\n"
                    header += "=" * 50 + "\n\n"
                    results_content = header + results_content

                with open(results_filename, "w") as f:
                    f.write(results_content)
                saved_files["results"] = str(results_filename)

            # Save trades
            if save_trades:
                trades_folder = base_folder / "trades"
                self._ensure_directory_exists(trades_folder)
                trades_filename = (
                    trades_folder
                    / f"{result.ticker}-{result.market}-{result.start_date}-{result.end_date}{tf_suffix}.txt"
                )

                with open(trades_filename, "w") as f:
                    f.write(result.trades.to_string())
                saved_files["trades"] = str(trades_filename)

            # Plot saving is handled separately by create_and_display_plot method

            return saved_files

        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            raise

    def _get_app_home(self) -> Path:
        """Get the application home directory"""
        connors_home = os.environ.get("CONNORS_HOME")
        if connors_home:
            return Path(connors_home)
        else:
            return Path.home() / ".connors"

    def open_file_in_browser(self, file_path: Path) -> None:
        """Open file in the default browser/application"""
        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(file_path)])
            elif sys.platform == "win32":  # Windows
                subprocess.run(["start", str(file_path)], shell=True)
            else:  # Linux and others
                subprocess.run(["xdg-open", str(file_path)])
        except Exception as e:
            self.logger.error(f"Failed to open file in browser: {e}")

    def create_and_display_plot(
        self,
        result: BacktestResult,
        datasource: str,
        market_config: str,
        dataset_file: Optional[str] = None,
        save_plot: bool = False,
        show_plot: bool = True,
        cash: float = 10000,
        trade_on_close: bool = True,
        finalize_trades: bool = False,
        interval: str = "1d",
        return_html: bool = False,
    ) -> Optional[str]:
        """
        Create and optionally display a backtest plot

        Returns the path to the plot file if saved, or HTML content if return_html=True
        """
        try:
            # Need to recreate the Backtest object to generate plot
            # Get strategy class
            strategy_class = self.registry._strategies.get(result.strategy)
            if not strategy_class:
                raise ValueError(f"Strategy '{result.strategy}' not found")

            # Apply parameters if any
            if result.parameters:
                strategy_class = create_strategy_with_params(
                    strategy_class, result.parameters
                )

            # Check if this is a multi-timeframe strategy
            tf_data = None
            primary_tf = None

            if result.is_multitimeframe and result.timeframes_used:
                self.logger.info(f"Creating plot for multi-timeframe strategy: {result.timeframes_used}")

                # Recreate multi-timeframe data
                if dataset_file:
                    # For dataset files, we can only work with the primary timeframe
                    df = self._load_dataset_from_file(dataset_file, result.ticker)
                    df_backtest = self._prepare_dataframe_for_backtest(df)
                else:
                    # Fetch multi-timeframe data
                    tf_data = self.fetch_multi_timeframe_data(
                        result.ticker,
                        datasource,
                        result.timeframes_used,
                        result.start_date,
                        result.end_date,
                        market_config,
                        result.primary_timeframe
                    )

                    # Use primary timeframe data for the main plot
                    primary_tf = result.primary_timeframe or result.timeframes_used[-1]
                    df_backtest = tf_data[primary_tf]

                    # Check if the strategy class has the set_timeframe_data method
                    if hasattr(strategy_class, 'set_timeframe_data') or (MultiTimeframeStrategy and issubclass(strategy_class, MultiTimeframeStrategy)):
                        # Create a custom strategy class that includes timeframe data
                        class MultiTimeframeStrategyWrapper(strategy_class):
                            def __init__(self, broker=None, data=None, params=None):
                                super().__init__(broker, data, params)
                                self.set_timeframe_data(tf_data)

                        strategy_class = MultiTimeframeStrategyWrapper
                    else:
                        # Strategy doesn't support multi-timeframe, but we can still pass the data
                        # by adding the method dynamically
                        class MultiTimeframeStrategyWrapper(strategy_class):
                            def __init__(self, broker=None, data=None, params=None):
                                super().__init__(broker, data, params)
                                self.tf_data = tf_data

                            def set_timeframe_data(self, tf_data):
                                self.tf_data = tf_data

                            def get_timeframe_data(self, timeframe):
                                if timeframe not in self.tf_data:
                                    raise ValueError(f"Timeframe '{timeframe}' not available. Available: {list(self.tf_data.keys())}")
                                return self.tf_data[timeframe]

                        strategy_class = MultiTimeframeStrategyWrapper
            else:
                # Single timeframe strategy
                if dataset_file:
                    df = self._load_dataset_from_file(dataset_file, result.ticker)
                else:
                    df = self._load_data_from_source(
                        datasource,
                        result.ticker,
                        result.start_date,
                        result.end_date,
                        interval,
                        market_config,
                    )

                # Convert to uppercase columns required by backtesting library
                df_backtest = self._prepare_dataframe_for_backtest(df)

            # Create backtest
            bt = Backtest(
                df_backtest,
                strategy_class,
                cash=cash,
                trade_on_close=trade_on_close,
                finalize_trades=finalize_trades,
            )

            # Run backtest to generate results needed for plotting
            bt.run()

            # Generate plot
            if save_plot:
                app_home = self._get_app_home()
                base_folder = app_home / "backtests" / result.strategy
                plots_folder = base_folder / "plots"
                self._ensure_directory_exists(plots_folder)

                # Include multi-timeframe info in filename if applicable
                if result.is_multitimeframe and result.timeframes_used:
                    tf_suffix = "_" + "-".join(result.timeframes_used)
                    if result.primary_timeframe:
                        tf_suffix += f"_primary-{result.primary_timeframe}"
                else:
                    tf_suffix = ""

                plot_filename = (
                    plots_folder
                    / f"{result.ticker}-{result.market}-{result.start_date}-{result.end_date}{tf_suffix}.html"
                )

                bt.plot(filename=str(plot_filename), open_browser=False)

                if show_plot:
                    self.open_file_in_browser(plot_filename)

                if return_html:
                    # Read and return HTML content
                    with open(plot_filename, "r", encoding="utf-8") as f:
                        return f.read()
                else:
                    return str(plot_filename)
            else:
                # Create temporary plot
                with tempfile.NamedTemporaryFile(
                    suffix=".html", delete=False
                ) as temp_file:
                    temp_filename = temp_file.name

                bt.plot(filename=temp_filename, open_browser=False)

                if show_plot:
                    self.open_file_in_browser(Path(temp_filename))

                if return_html:
                    # Read and return HTML content
                    try:
                        with open(temp_filename, "r", encoding="utf-8") as f:
                            html_content = f.read()
                        # Clean up temp file
                        try:
                            os.unlink(temp_filename)
                        except:
                            pass
                        return html_content
                    except Exception as e:
                        self.logger.error(f"Failed to read HTML plot: {e}")
                        return None
                else:
                    return temp_filename

        except Exception as e:
            self.logger.error(f"Failed to create plot: {e}")
            raise

    def str2bool(self, v: Union[str, bool]) -> bool:
        """Convert string to boolean (CLI compatibility)"""
        if isinstance(v, bool):
            return v
        if v.lower() in ("yes", "true", "t", "y", "1"):
            return True
        elif v.lower() in ("no", "false", "f", "n", "0"):
            return False
        else:
            raise ValueError("Boolean value expected.")

    def parse_tickers(self, tickers_string: str) -> List[str]:
        """Parse comma-separated ticker string"""
        return [ticker.strip().replace("'", "") for ticker in tickers_string.split(",")]

    def run_multiple_backtests(
        self,
        tickers: List[str],
        strategy: str,
        datasource: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        interval: str = "1d",
        market_config: str = "australia",
        strategy_params: Optional[Dict[str, Any]] = None,
        strategy_params_string: Optional[str] = None,
        dataset_file: Optional[str] = None,
        external_strategy_file: Optional[str] = None,
        cash: float = 10000,
        commission: float = 0.0025,
        trade_on_close: bool = True,
        finalize_trades: bool = False,
        save_results: bool = False,
        save_trades: bool = False,
        save_plots: bool = False,
        show_plots: bool = False,
        optimize: bool = False,
        optimize_params: Optional[Dict[str, Any]] = None,
        timeframe: Optional[str] = None,
        # Multi-timeframe parameters
        timeframes: Optional[List[str]] = None,
        primary_timeframe: Optional[str] = None,
    ) -> List[BacktestResult]:
        """
        Run backtests for multiple tickers

        Returns list of BacktestResult objects
        """
        # Validate dataset file usage with multiple tickers before starting
        if dataset_file and len(tickers) > 1:
            raise ValueError("Dataset file can only be used with a single ticker")

        results = []

        for ticker in tickers:
            try:

                result = self.run_backtest(
                    ticker=ticker,
                    strategy=strategy,
                    datasource=datasource,
                    start=start,
                    end=end,
                    interval=interval,
                    market_config=market_config,
                    strategy_params=strategy_params,
                    strategy_params_string=strategy_params_string,
                    dataset_file=dataset_file,
                    external_strategy_file=external_strategy_file,
                    cash=cash,
                    commission=commission,
                    trade_on_close=trade_on_close,
                    finalize_trades=finalize_trades,
                    optimize=optimize,
                    optimize_params=optimize_params,
                    timeframe=timeframe,
                    # Multi-timeframe parameters
                    timeframes=timeframes,
                    primary_timeframe=primary_timeframe,
                )

                results.append(result)

                # Save files if requested
                if save_results or save_trades:
                    saved_files = self.save_results_to_file(
                        result, save_results, save_trades, False
                    )
                    for file_type, file_path in saved_files.items():
                        print(f"💾 Saved {file_type}: {file_path}")

                # Handle plots - includes both saving and showing
                if show_plots or save_plots:
                    plot_path = self.create_and_display_plot(
                        result,
                        datasource,
                        market_config,
                        dataset_file,
                        save_plot=save_plots,
                        show_plot=show_plots,
                        cash=cash,
                        trade_on_close=trade_on_close,
                        finalize_trades=finalize_trades,
                        interval=interval,
                    )
                    if save_plots and plot_path:
                        print(f"📊 Saved plot: {plot_path}")
                    if show_plots:
                        print("🌐 Opened plot in browser")

            except Exception as e:
                self.logger.error(f"Backtest failed for {ticker}: {e}")
                # Continue with other tickers
                continue

        return results
