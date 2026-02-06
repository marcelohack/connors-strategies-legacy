"""
Unit tests for BacktestService
"""

import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pandas as pd
import pytest

from connors_core.config.manager import BacktestConfig
from connors_strategies.services.backtest_service import BacktestResult, BacktestService


class TestBacktestService:
    """Test suite for BacktestService"""

    @pytest.fixture
    def service(self):
        """Create a BacktestService instance for testing"""
        return BacktestService()

    @pytest.fixture
    def mock_market_config(self):
        """Mock market configuration"""
        return BacktestConfig(
            name="test_market", yf_ticker_suffix=".TEST", cash=10000, utc_offset=0
        )

    @pytest.fixture
    def mock_strategy_class(self):
        """Mock strategy class"""
        strategy = Mock()
        strategy.__name__ = "TestStrategy"
        strategy.__doc__ = "Test strategy for unit tests"
        return strategy

    @pytest.fixture
    def mock_backtest_results(self):
        """Mock backtest results"""
        results = Mock()
        results.to_string.return_value = "Mock backtest results"
        trades_df = pd.DataFrame(
            {
                "EntryTime": ["2024-01-01", "2024-01-02"],
                "ExitTime": ["2024-01-01", "2024-01-02"],
                "Size": [100, -100],
                "EntryPrice": [50.0, 55.0],
                "ExitPrice": [52.0, 53.0],
                "PnL": [200.0, -200.0],
            }
        )
        equity_curve = pd.DataFrame({"Equity": [10000, 10200, 10000]})

        # Mock the dictionary-like access
        results.__getitem__ = Mock(
            side_effect=lambda key: {
                "_trades": trades_df,
                "_equity_curve": equity_curve,
            }[key]
        )

        return results

    @pytest.fixture
    def mock_sample_data(self):
        """Mock OHLCV data"""
        return pd.DataFrame(
            {
                "Open": [50.0, 51.0, 52.0],
                "High": [51.0, 52.0, 53.0],
                "Low": [49.0, 50.0, 51.0],
                "Close": [50.5, 51.5, 52.5],
                "Volume": [1000, 1100, 1200],
            },
            index=pd.date_range("2024-01-01", periods=3),
        )

    @pytest.fixture
    def mock_backtest_result(self, mock_backtest_results):
        """Mock BacktestResult object"""
        return BacktestResult(
            ticker="TEST",
            strategy="LCRSI2",
            results=mock_backtest_results,
            trades=mock_backtest_results["_trades"],
            equity_curve=mock_backtest_results["_equity_curve"],
            start_date="2024-01-01",
            end_date="2024-01-31",
            market="test_market",
            parameters={"rsi_period": 2},
        )

    def test_init(self, service):
        """Test service initialization"""
        assert service is not None
        assert hasattr(service, "registry")
        assert hasattr(service, "config_manager")
        assert hasattr(service, "logger")

    def test_get_strategies(self, service):
        """Test getting available strategies"""
        with patch.object(
            service.registry, "list_strategies", return_value=["LCRSI2", "LCRSI2"]
        ) as mock_method:
            strategies = service.get_strategies()

            assert strategies == ["LCRSI2", "LCRSI2"]
            mock_method.assert_called_once()

    def test_get_strategies_error(self, service):
        """Test getting strategies when an error occurs"""
        with patch.object(
            service.registry, "list_strategies", side_effect=Exception("Registry error")
        ):
            strategies = service.get_strategies()

            assert strategies == []

    def test_get_strategy_info(self, service, mock_strategy_class):
        """Test getting strategy information"""
        with (
            patch.object(
                service.registry, "_strategies", {"LCRSI2": mock_strategy_class}
            ),
            patch(
                "connors_strategies.services.backtest_service.get_strategy_parameter_info",
                return_value="Parameter info",
            ),
        ):

            strategy_info = service.get_strategy_info("LCRSI2")

            assert strategy_info["name"] == "LCRSI2"
            assert strategy_info["class_name"] == "TestStrategy"
            assert strategy_info["description"] == "Test strategy for unit tests"
            assert strategy_info["parameters"] == "Parameter info"

    def test_get_strategy_info_not_found(self, service):
        """Test getting strategy info for non-existent strategy"""
        with patch.object(service.registry, "_strategies", {}):
            strategy_info = service.get_strategy_info("NONEXISTENT")

            assert strategy_info == {}

    def test_get_datasources(self, service):
        """Test getting available data sources"""
        with patch(
            "connors_strategies.services.backtest_service.datasource_registry.list_datasources",
            return_value=["yfinance", "polygon"]
        ) as mock_method:
            datasources = service.get_datasources()

            assert datasources == ["yfinance", "polygon"]
            mock_method.assert_called_once()

    def test_get_market_configs(self, service):
        """Test getting available market configurations"""
        with patch.object(
            service.config_manager,
            "list_configs",
            return_value=["australia", "america"],
        ) as mock_method:
            configs = service.get_market_configs()

            assert configs == ["australia", "america"]
            mock_method.assert_called_once()

    def test_get_market_config_info(self, service, mock_market_config):
        """Test getting market configuration information"""
        with patch.object(
            service.config_manager, "get_market_config", return_value=mock_market_config
        ):
            config_info = service.get_market_config_info("test_config")

            assert config_info["name"] == "test_market"
            assert config_info["yf_ticker_suffix"] == ".TEST"
            assert config_info["cash"] == 10000
            assert config_info["utc_offset"] == 0

    def test_validate_dataset_file_success(self, service):
        """Test successful dataset file validation"""
        csv_data = "Date,Open,High,Low,Close,Volume\n2024-01-01,50,51,49,50.5,1000"

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pandas.read_csv",
                return_value=pd.DataFrame(
                    {
                        "open": [50.0],
                        "high": [51.0],
                        "low": [49.0],
                        "close": [50.5],
                        "volume": [1000],
                    },
                    index=pd.date_range("2024-01-01", periods=1),
                ),
            ),
        ):

            result = service.validate_dataset_file("/path/to/test.csv")

            assert result["valid"] is True
            assert result["shape"] == (1, 5)
            assert "date_range" in result

    def test_validate_dataset_file_not_found(self, service):
        """Test dataset file validation for non-existent file"""
        with patch("pathlib.Path.exists", return_value=False):
            result = service.validate_dataset_file("/path/to/nonexistent.csv")

            assert result["valid"] is False
            assert "File not found" in result["error"]

    def test_validate_dataset_file_wrong_extension(self, service):
        """Test dataset file validation for wrong file extension"""
        import tempfile
        from pathlib import Path

        # Create a temporary file with wrong extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test data")
            temp_file = f.name

        try:
            result = service.validate_dataset_file(temp_file)
            assert result["valid"] is False
            assert "must be a CSV or JSON file" in result["error"]
        finally:
            Path(temp_file).unlink()

    def test_validate_dataset_file_missing_columns(self, service):
        """Test dataset file validation with missing columns"""
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch(
                "pandas.read_csv",
                return_value=pd.DataFrame(
                    {
                        "open": [50.0],
                        "high": [51.0],
                        "low": [49.0],  # Missing close and volume
                    },
                    index=pd.date_range("2024-01-01", periods=1),
                ),
            ),
        ):

            result = service.validate_dataset_file("/path/to/test.csv")

            assert result["valid"] is False
            assert "Missing required OHLCV columns" in result["error"]

    def test_get_default_dates(self, service, mock_market_config):
        """Test getting default dates"""
        with patch.object(
            service.config_manager, "get_market_config", return_value=mock_market_config
        ):
            dates = service.get_default_dates("test_config")

            assert "start" in dates
            assert "end" in dates
            # Should be roughly one year ago to today
            start_date = datetime.strptime(dates["start"], "%Y-%m-%d").date()
            end_date = datetime.strptime(dates["end"], "%Y-%m-%d").date()
            assert (end_date - start_date).days >= 365

    def test_get_default_dates_fallback(self, service):
        """Test getting default dates with fallback logic"""
        with patch.object(
            service.config_manager,
            "get_market_config",
            side_effect=Exception("Config error"),
        ):
            dates = service.get_default_dates("invalid_config")

            assert "start" in dates
            assert "end" in dates

    def test_get_available_timespans(self, service):
        """Test getting available timespans"""
        timeframes = service.get_available_timeframes()
        assert isinstance(timeframes, list)
        assert len(timeframes) > 0
        assert "1Y" in timeframes
        assert "6M" in timeframes
        assert "YTD" in timeframes

    def test_get_timespan_description(self, service):
        """Test getting timespan descriptions"""
        desc = service.get_timeframe_description("1Y")
        assert desc == "1 Year"

        desc = service.get_timeframe_description("YTD")
        assert desc == "Year to Date"

    def test_calculate_dates_from_timespan(self, service):
        """Test calculating dates from timespan"""
        # Test with timespan only
        dates = service.calculate_dates_from_timeframe(timeframe="1Y")
        assert isinstance(dates, dict)
        assert "start" in dates
        assert "end" in dates

        # Validate date format
        start_date = datetime.strptime(dates["start"], "%Y-%m-%d")
        end_date = datetime.strptime(dates["end"], "%Y-%m-%d")
        assert start_date < end_date

    def test_calculate_dates_from_timespan_with_custom_dates(self, service):
        """Test calculating dates with custom start/end override"""
        dates = service.calculate_dates_from_timeframe(
            timeframe="6M", start_date="2023-01-01", end_date="2023-12-31"
        )
        assert dates["start"] == "2023-01-01"
        assert dates["end"] == "2023-12-31"

    def test_calculate_dates_from_timespan_error_handling(self, service):
        """Test error handling in timespan calculation"""
        with patch(
            "connors_datafetch.core.timespan.TimespanCalculator.calculate_dates",
            side_effect=Exception("Timeframe error"),
        ):
            dates = service.calculate_dates_from_timeframe(timeframe="INVALID")
            # Should fallback to default dates
            assert isinstance(dates, dict)
            assert "start" in dates
            assert "end" in dates

    def test_run_backtest_success(
        self,
        service,
        mock_strategy_class,
        mock_sample_data,
        mock_backtest_results,
        mock_market_config,
    ):
        """Test successful backtest execution"""
        # Mock all dependencies
        with (
            patch.object(
                service.registry, "_strategies", {"LCRSI2": mock_strategy_class}
            ),
            patch.object(
                service, "_load_data_from_source", return_value=mock_sample_data
            ),
            patch.object(
                service, "get_market_config_info", return_value={"name": "test_market"}
            ),
            patch("connors_strategies.services.backtest_service.Backtest") as mock_backtest_class,
        ):

            # Configure mock backtest
            mock_backtest_instance = Mock()
            mock_backtest_instance.run.return_value = mock_backtest_results
            mock_backtest_class.return_value = mock_backtest_instance

            result = service.run_backtest(
                ticker="TEST",
                strategy="LCRSI2",
                datasource="yfinance",
                start="2024-01-01",
                end="2024-01-31",
                market_config="test_config",
            )

            assert isinstance(result, BacktestResult)
            assert result.ticker == "TEST"
            assert result.strategy == "LCRSI2"
            assert result.start_date == "2024-01-01"
            assert result.end_date == "2024-01-31"

            # Verify Backtest was called with default commission
            mock_backtest_class.assert_called_once()
            call_args = mock_backtest_class.call_args
            assert call_args[1]["commission"] == 0.0025  # Default commission value

    def test_run_backtest_with_parameters(
        self, service, mock_strategy_class, mock_sample_data, mock_backtest_results
    ):
        """Test backtest with strategy parameters"""
        with (
            patch.object(
                service.registry, "_strategies", {"LCRSI2": mock_strategy_class}
            ),
            patch.object(
                service, "_load_data_from_source", return_value=mock_sample_data
            ),
            patch.object(
                service, "get_market_config_info", return_value={"name": "test_market"}
            ),
            patch(
                "connors_strategies.services.backtest_service.create_strategy_with_params",
                return_value=mock_strategy_class,
            ) as mock_create_strategy,
            patch("connors_strategies.services.backtest_service.Backtest") as mock_backtest_class,
        ):

            mock_backtest_instance = Mock()
            mock_backtest_instance.run.return_value = mock_backtest_results
            mock_backtest_class.return_value = mock_backtest_instance

            result = service.run_backtest(
                ticker="TEST",
                strategy="LCRSI2",
                datasource="yfinance",
                start="2024-01-01",
                end="2024-01-31",
                strategy_params={"rsi_period": 3},
            )

            mock_create_strategy.assert_called_once_with(
                mock_strategy_class, {"rsi_period": 3}
            )

            # Verify default commission is still used
            call_args = mock_backtest_class.call_args
            assert call_args[1]["commission"] == 0.0025

    def test_run_backtest_strategy_not_found(self, service):
        """Test backtest with non-existent strategy"""
        with patch.object(service.registry, "_strategies", {}):
            with pytest.raises(ValueError) as exc_info:
                service.run_backtest(
                    ticker="TEST",
                    strategy="NONEXISTENT",
                    datasource="yfinance",
                    start="2024-01-01",
                    end="2024-01-31",
                )

            assert "Strategy 'NONEXISTENT' not found" in str(exc_info.value)

    def test_run_backtest_with_timespan(
        self,
        service,
        mock_strategy_class,
        mock_sample_data,
        mock_backtest_results,
        mock_market_config,
    ):
        """Test running backtest with timespan parameter"""
        with (
            patch.object(
                service.registry, "_strategies", {"LCRSI2": mock_strategy_class}
            ),
            patch.object(
                service.config_manager,
                "get_market_config",
                return_value=mock_market_config,
            ),
            patch(
                "connors_strategies.services.backtest_service.datasource_registry.create_datasource"
            ) as mock_create_datasource,
            patch("connors_strategies.services.backtest_service.Backtest") as mock_backtest_class,
            patch(
                "connors_datafetch.core.timespan.TimespanCalculator.calculate_dates",
                return_value=("2023-06-15", "2024-06-15"),
            ) as mock_calc_dates,
        ):
            mock_datasource = Mock()
            mock_datasource.fetch.return_value = mock_sample_data
            mock_create_datasource.return_value = mock_datasource

            mock_backtest_instance = Mock()
            mock_backtest_instance.run.return_value = mock_backtest_results
            mock_backtest_class.return_value = mock_backtest_instance

            result = service.run_backtest(
                ticker="TEST",
                strategy="LCRSI2",
                datasource="yfinance",
                timeframe="1Y",
            )

            # Verify timespan calculation was called
            mock_calc_dates.assert_called_once_with(
                timespan="1Y", start_date=None, end_date=None
            )

            # Verify datasource fetch was called with calculated dates (with market suffix)
            mock_datasource.fetch.assert_called_once_with(
                "TEST.TEST", "2023-06-15", "2024-06-15", "1d"
            )

            assert result is not None
            assert result.ticker == "TEST"
            assert result.start_date == "2023-06-15"
            assert result.end_date == "2024-06-15"

    def test_run_backtest_timespan_with_custom_dates(
        self,
        service,
        mock_strategy_class,
        mock_sample_data,
        mock_backtest_results,
        mock_market_config,
    ):
        """Test running backtest with timespan and custom date override"""
        with (
            patch.object(
                service.registry, "_strategies", {"LCRSI2": mock_strategy_class}
            ),
            patch.object(
                service.config_manager,
                "get_market_config",
                return_value=mock_market_config,
            ),
            patch(
                "connors_strategies.services.backtest_service.datasource_registry.create_datasource"
            ) as mock_create_datasource,
            patch("connors_strategies.services.backtest_service.Backtest") as mock_backtest_class,
            patch(
                "connors_datafetch.core.timespan.TimespanCalculator.calculate_dates",
                return_value=("2023-01-01", "2023-12-31"),
            ) as mock_calc_dates,
        ):
            mock_datasource = Mock()
            mock_datasource.fetch.return_value = mock_sample_data
            mock_create_datasource.return_value = mock_datasource

            mock_backtest_instance = Mock()
            mock_backtest_instance.run.return_value = mock_backtest_results
            mock_backtest_class.return_value = mock_backtest_instance

            result = service.run_backtest(
                ticker="TEST",
                strategy="LCRSI2",
                datasource="yfinance",
                start="2023-01-01",
                timeframe="6M",
            )

            # Verify timespan calculation was called with custom start
            mock_calc_dates.assert_called_once_with(
                timespan="6M", start_date="2023-01-01", end_date=None
            )

            assert result is not None

    def test_load_dataset_from_file(self, service, mock_sample_data):
        """Test loading dataset from file"""
        with (
            patch.object(
                service, "validate_dataset_file", return_value={"valid": True}
            ),
            patch("pandas.read_csv", return_value=mock_sample_data),
        ):

            df = service._load_dataset_from_file("/path/to/test.csv", "TEST")

            assert not df.empty
            assert list(df.columns) == ["open", "high", "low", "close", "volume"]

    def test_load_data_from_source(self, service, mock_sample_data, mock_market_config):
        """Test loading data from data source"""
        mock_datasource = Mock()
        mock_datasource.fetch.return_value = mock_sample_data

        with (
            patch(
                "connors_strategies.services.backtest_service.datasource_registry.create_datasource",
                return_value=mock_datasource
            ),
            patch.object(
                service.config_manager,
                "get_market_config",
                return_value=mock_market_config,
            ),
        ):

            df = service._load_data_from_source(
                datasource="yfinance",
                ticker="TEST",
                start="2024-01-01",
                end="2024-01-31",
                interval="1d",
                market_config="test_config",
            )

            assert not df.empty
            mock_datasource.fetch.assert_called_once_with(
                "TEST.TEST", "2024-01-01", "2024-01-31", "1d"
            )

    def test_load_data_from_source_empty_data(self, service, mock_market_config):
        """Test loading data from source with empty result"""
        mock_datasource = Mock()
        mock_datasource.fetch.return_value = pd.DataFrame()  # Empty DataFrame

        with (
            patch(
                "connors_strategies.services.backtest_service.datasource_registry.create_datasource",
                return_value=mock_datasource
            ),
            patch.object(
                service.config_manager,
                "get_market_config",
                return_value=mock_market_config,
            ),
        ):

            with pytest.raises(ValueError) as exc_info:
                service._load_data_from_source(
                    datasource="yfinance",
                    ticker="TEST",
                    start="2024-01-01",
                    end="2024-01-31",
                    interval="1d",
                    market_config="test_config",
                )

            assert "No data found for TEST.TEST" in str(exc_info.value)

    def test_save_results_to_file(self, service, mock_backtest_result):
        """Test saving backtest results to files"""
        with (
            patch.object(service, "_get_app_home", return_value=Path("/mock/home")),
            patch.object(service, "_ensure_directory_exists"),
            patch("builtins.open", mock_open()) as mock_file,
        ):

            saved_files = service.save_results_to_file(
                mock_backtest_result, save_results=True, save_trades=True
            )

            assert "results" in saved_files
            assert "trades" in saved_files
            assert mock_file.call_count == 2  # Two files opened

    def test_str2bool(self, service):
        """Test string to boolean conversion"""
        assert service.str2bool(True) is True
        assert service.str2bool(False) is False
        assert service.str2bool("true") is True
        assert service.str2bool("false") is False
        assert service.str2bool("yes") is True
        assert service.str2bool("no") is False
        assert service.str2bool("1") is True
        assert service.str2bool("0") is False

        with pytest.raises(ValueError):
            service.str2bool("invalid")

    def test_parse_tickers(self, service):
        """Test ticker string parsing"""
        tickers = service.parse_tickers("AAPL, GOOGL , 'MSFT'")
        assert tickers == ["AAPL", "GOOGL", "MSFT"]

    def test_open_file_in_browser(self, service):
        """Test opening file in browser"""
        test_path = Path("/test/file.html")

        # Test macOS
        with patch("sys.platform", "darwin"), patch("subprocess.run") as mock_run:
            service.open_file_in_browser(test_path)
            mock_run.assert_called_once_with(["open", str(test_path)])

        # Test Windows
        with patch("sys.platform", "win32"), patch("subprocess.run") as mock_run:
            service.open_file_in_browser(test_path)
            mock_run.assert_called_once_with(["start", str(test_path)], shell=True)

        # Test Linux
        with patch("sys.platform", "linux"), patch("subprocess.run") as mock_run:
            service.open_file_in_browser(test_path)
            mock_run.assert_called_once_with(["xdg-open", str(test_path)])

    def test_run_multiple_backtests(
        self, service, mock_strategy_class, mock_sample_data, mock_backtest_results
    ):
        """Test running multiple backtests"""
        with (
            patch.object(service, "run_backtest") as mock_run_backtest,
            patch.object(service, "save_results_to_file") as mock_save,
        ):

            # Mock run_backtest to return BacktestResult objects
            mock_result1 = Mock(spec=BacktestResult)
            mock_result1.ticker = "AAPL"
            mock_result2 = Mock(spec=BacktestResult)
            mock_result2.ticker = "GOOGL"

            mock_run_backtest.side_effect = [mock_result1, mock_result2]

            results = service.run_multiple_backtests(
                tickers=["AAPL", "GOOGL"],
                strategy="LCRSI2",
                datasource="yfinance",
                start="2024-01-01",
                end="2024-01-31",
                save_results=True,
                commission=0.002,  # Test commission parameter in multiple backtests
                cash=15000,
            )

            assert len(results) == 2
            assert mock_run_backtest.call_count == 2
            assert mock_save.call_count == 2

            # Verify commission and cash were passed to each backtest
            for call in mock_run_backtest.call_args_list:
                assert call[1]["commission"] == 0.002
                assert call[1]["cash"] == 15000

    def test_run_multiple_backtests_dataset_file_error(self, service):
        """Test multiple backtests with dataset file (should error)"""
        with pytest.raises(ValueError) as exc_info:
            service.run_multiple_backtests(
                tickers=["AAPL", "GOOGL"],  # Multiple tickers
                strategy="LCRSI2",
                datasource="yfinance",
                start="2024-01-01",
                end="2024-01-31",
                dataset_file="/path/to/file.csv",  # Dataset file provided
            )

        assert "Dataset file can only be used with a single ticker" in str(
            exc_info.value
        )

    def test_run_backtest_with_custom_commission(
        self,
        service,
        mock_strategy_class,
        mock_sample_data,
        mock_backtest_results,
    ):
        """Test backtest with custom commission parameter"""
        with (
            patch.object(
                service.registry, "_strategies", {"LCRSI2": mock_strategy_class}
            ),
            patch.object(
                service, "_load_data_from_source", return_value=mock_sample_data
            ),
            patch.object(
                service, "get_market_config_info", return_value={"name": "test_market"}
            ),
            patch("connors_strategies.services.backtest_service.Backtest") as mock_backtest_class,
        ):

            mock_backtest_instance = Mock()
            mock_backtest_instance.run.return_value = mock_backtest_results
            mock_backtest_class.return_value = mock_backtest_instance

            result = service.run_backtest(
                ticker="TEST",
                strategy="LCRSI2",
                datasource="yfinance",
                start="2024-01-01",
                end="2024-01-31",
                commission=0.005,  # Custom commission
                cash=20000,  # Custom cash amount
            )

            assert isinstance(result, BacktestResult)

            # Verify Backtest was called with custom commission and cash
            mock_backtest_class.assert_called_once()
            call_args = mock_backtest_class.call_args
            assert call_args[1]["commission"] == 0.005
            assert call_args[1]["cash"] == 20000
            assert call_args[1]["trade_on_close"] is True  # Default value
            assert call_args[1]["finalize_trades"] is False  # Default value

    def test_run_backtest_with_all_options(
        self,
        service,
        mock_strategy_class,
        mock_sample_data,
        mock_backtest_results,
    ):
        """Test backtest with all optional parameters set"""
        with (
            patch.object(
                service.registry, "_strategies", {"LCRSI2": mock_strategy_class}
            ),
            patch.object(
                service, "_load_data_from_source", return_value=mock_sample_data
            ),
            patch.object(
                service, "get_market_config_info", return_value={"name": "test_market"}
            ),
            patch("connors_strategies.services.backtest_service.Backtest") as mock_backtest_class,
        ):

            mock_backtest_instance = Mock()
            mock_backtest_instance.run.return_value = mock_backtest_results
            mock_backtest_class.return_value = mock_backtest_instance

            result = service.run_backtest(
                ticker="TEST",
                strategy="LCRSI2",
                datasource="yfinance",
                start="2024-01-01",
                end="2024-01-31",
                commission=0.001,
                cash=50000,
                trade_on_close=False,
                finalize_trades=True,
                interval="1wk",
            )

            assert isinstance(result, BacktestResult)

            # Verify all parameters were passed correctly
            call_args = mock_backtest_class.call_args
            assert call_args[1]["commission"] == 0.001
            assert call_args[1]["cash"] == 50000
            assert call_args[1]["trade_on_close"] is False
            assert call_args[1]["finalize_trades"] is True

    def test_parameter_validation(self, service):
        """Test parameter validation in various methods"""
        # Test missing strategy
        with pytest.raises(ValueError) as exc_info:
            service.get_strategy_info("")
        assert "Missing required parameters" in str(exc_info.value)

        # Test missing config_name
        with pytest.raises(ValueError) as exc_info:
            service.get_market_config_info("")
        assert "Missing required parameters" in str(exc_info.value)

        # Test missing parameters for run_backtest
        with pytest.raises(ValueError) as exc_info:
            service.run_backtest("", "LCRSI2", "yfinance", "2024-01-01", "2024-01-31")
        assert "Missing required parameters" in str(exc_info.value)


class TestBacktestServiceIntegration:
    """Integration tests that use real components where possible"""

    @pytest.fixture
    def service(self):
        """Create a BacktestService instance for integration testing"""
        return BacktestService()

    def test_service_initialization_integration(self, service):
        """Test that service initializes with real components"""
        # These should work with the actual registry and config manager
        strategies = service.get_strategies()
        assert isinstance(strategies, list)

        datasources = service.get_datasources()
        assert isinstance(datasources, list)

        configs = service.get_market_configs()
        assert isinstance(configs, list)
        assert len(configs) > 0

    def test_default_dates_integration(self, service):
        """Test default date calculation with real config manager"""
        dates = service.get_default_dates()

        assert "start" in dates
        assert "end" in dates

        # Validate date format
        start_date = datetime.strptime(dates["start"], "%Y-%m-%d")
        end_date = datetime.strptime(dates["end"], "%Y-%m-%d")
        assert start_date < end_date

    def test_dataset_validation_integration(self, service):
        """Test dataset validation with actual CSV content"""
        # Test with invalid file path
        result = service.validate_dataset_file("/nonexistent/file.csv")
        assert result["valid"] is False
        assert "File not found" in result["error"]

        # Test with wrong extension - create actual file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test")
            temp_file = f.name

        try:
            result = service.validate_dataset_file(temp_file)
            assert result["valid"] is False
            assert "must be a CSV or JSON file" in result["error"]
        finally:
            Path(temp_file).unlink()

    def test_str2bool_integration(self, service):
        """Test str2bool with various inputs"""
        true_values = ["true", "True", "TRUE", "yes", "Yes", "Y", "y", "1", True]
        false_values = ["false", "False", "FALSE", "no", "No", "N", "n", "0", False]

        for val in true_values:
            assert service.str2bool(val) is True

        for val in false_values:
            assert service.str2bool(val) is False

        # Test invalid values
        invalid_values = ["maybe", "invalid", "2", ""]
        for val in invalid_values:
            with pytest.raises(ValueError):
                service.str2bool(val)

    def test_ticker_parsing_integration(self, service):
        """Test ticker parsing with various formats"""
        test_cases = [
            ("AAPL", ["AAPL"]),
            ("AAPL,GOOGL", ["AAPL", "GOOGL"]),
            ("AAPL, GOOGL , MSFT", ["AAPL", "GOOGL", "MSFT"]),
            ("'AAPL','GOOGL'", ["AAPL", "GOOGL"]),
            ("AAPL,   GOOGL   ,MSFT", ["AAPL", "GOOGL", "MSFT"]),
        ]

        for input_str, expected in test_cases:
            result = service.parse_tickers(input_str)
            assert result == expected, f"Failed for input: {input_str}"

    def test_run_backtest_with_optimization(self, service):
        """Test backtest optimization functionality"""
        # Mock backtest instance
        mock_bt = Mock()
        mock_bt.optimize.return_value = {"Sharpe Ratio": 1.5, "Return [%]": 25.0}

        optimize_params = {
            "rsi_level": range(3, 6, 1),  # Small range for testing
            "maximize": "Sharpe Ratio",
            "max_tries": 10,
        }

        result = service._run_optimization(mock_bt, optimize_params)

        # Verify optimize was called with correct parameters
        mock_bt.optimize.assert_called_once()
        call_kwargs = mock_bt.optimize.call_args[1]

        assert "rsi_level" in call_kwargs
        assert call_kwargs["maximize"] == "Sharpe Ratio"
        assert call_kwargs["max_tries"] == 10
        assert result is not None

    def test_optimization_parameter_parsing(self, service):
        """Test optimization parameter handling"""
        optimize_params = {
            "param1": range(1, 5, 1),
            "param2": [5, 7, 10],
            "maximize": "Return [%]",
            "constraint": lambda p: p.get("param1", 0) < 10,
        }

        mock_bt = Mock()
        mock_bt.optimize.return_value = {"Return [%]": 15.0}

        service._run_optimization(mock_bt, optimize_params)

        # Verify all parameters were passed
        call_kwargs = mock_bt.optimize.call_args[1]
        assert "param1" in call_kwargs
        assert "param2" in call_kwargs
        assert "constraint" in call_kwargs
        assert call_kwargs["maximize"] == "Return [%]"


class TestBaseServiceHelpers:
    """Test BaseService helper methods"""

    @pytest.fixture
    def service(self):
        """Create a BacktestService instance to test base service methods"""
        return BacktestService()

    def test_validate_required_params_success(self, service):
        """Test parameter validation with valid params"""
        params = {'ticker': 'AAPL', 'strategy': 'LCRSI2'}
        required = ['ticker', 'strategy']

        # Should not raise
        service._validate_required_params(params, required)

    def test_validate_required_params_missing(self, service):
        """Test parameter validation with missing params"""
        params = {'ticker': 'AAPL'}
        required = ['ticker', 'strategy']

        with pytest.raises(ValueError) as exc_info:
            service._validate_required_params(params, required)

        assert 'strategy' in str(exc_info.value)

    def test_validate_required_params_empty_value(self, service):
        """Test parameter validation with empty string"""
        params = {'ticker': 'AAPL', 'strategy': ''}
        required = ['ticker', 'strategy']

        with pytest.raises(ValueError):
            service._validate_required_params(params, required)

    def test_validate_required_params_none_value(self, service):
        """Test parameter validation with None value"""
        params = {'ticker': 'AAPL', 'strategy': None}
        required = ['ticker', 'strategy']

        with pytest.raises(ValueError):
            service._validate_required_params(params, required)

    def test_safe_execute_success(self, service):
        """Test safe execution of function"""
        def success_func(**kwargs):
            return kwargs['value'] * 2

        result = service._safe_execute(
            success_func,
            error_msg="Test failed",
            value=5
        )

        assert result == 10

    def test_safe_execute_error(self, service):
        """Test safe execution with error"""
        def error_func(**kwargs):
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            service._safe_execute(error_func, error_msg="Test failed")

    def test_ensure_directory_exists_new(self, service):
        """Test directory creation"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / 'new_dir' / 'nested'
            service._ensure_directory_exists(test_dir)
            assert test_dir.exists()

    def test_ensure_directory_exists_existing(self, service):
        """Test directory creation when already exists"""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            test_dir = Path(tmpdir) / 'existing'
            test_dir.mkdir()

            # Should not raise
            service._ensure_directory_exists(test_dir)
            assert test_dir.exists()
