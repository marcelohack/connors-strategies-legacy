"""
Unit tests for Multi-Timeframe functionality

Tests the multi-timeframe strategy architecture, data handling, and integration.
"""

import pandas as pd
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from connors_strategies.services.backtest_service import BacktestService, BacktestResult
from connors_strategies.strategies.multitimeframe.base import MultiTimeframeStrategy
from connors_strategies.strategies.multitimeframe.mtf_rsi2 import MTF_RSI2_Strategy


class TestMultiTimeframeStrategy:
    """Test suite for MultiTimeframeStrategy base class"""

    @pytest.fixture
    def strategy_class(self):
        """Create a test multi-timeframe strategy class"""
        class TestMTFStrategy(MultiTimeframeStrategy):
            timeframes = ['1wk', '1d', '1h']
            primary_timeframe = '1h'

            def _init_indicators(self):
                pass  # Mock implementation

            def next(self):
                pass  # Mock implementation

        return TestMTFStrategy

    def test_strategy_initialization(self, strategy_class):
        """Test multi-timeframe strategy initialization"""
        # Test with broker, data, params (normal backtesting scenario)
        broker = Mock()
        data = Mock()
        params = {}

        strategy = strategy_class(broker, data, params)

        assert strategy.timeframes == ['1wk', '1d', '1h']
        assert strategy.primary_timeframe == '1h'
        assert hasattr(strategy, 'tf_data')
        assert hasattr(strategy, '_tf_indicators')

    def test_timeframe_configuration_validation(self):
        """Test timeframe configuration validation"""
        class InvalidStrategy(MultiTimeframeStrategy):
            timeframes = []  # Empty timeframes

            def _init_indicators(self):
                pass

            def next(self):
                pass

        broker, data, params = Mock(), Mock(), {}
        strategy = InvalidStrategy(broker, data, params)

        # Should raise error when init() is called with empty timeframes
        with pytest.raises(ValueError, match="Multi-timeframe strategies must define 'timeframes' attribute"):
            strategy.init()

    def test_primary_timeframe_validation(self):
        """Test primary timeframe validation"""
        class InvalidPrimaryTFStrategy(MultiTimeframeStrategy):
            timeframes = ['1wk', '1d']
            primary_timeframe = '1h'  # Not in timeframes list

            def _init_indicators(self):
                pass

            def next(self):
                pass

        broker, data, params = Mock(), Mock(), {}
        strategy = InvalidPrimaryTFStrategy(broker, data, params)

        # Should raise error when primary_timeframe is not in timeframes list
        with pytest.raises(ValueError, match="Primary timeframe '1h' must be in timeframes list"):
            strategy.init()

    def test_auto_primary_timeframe_selection(self):
        """Test automatic primary timeframe selection"""
        class AutoPrimaryStrategy(MultiTimeframeStrategy):
            timeframes = ['1wk', '1d', '1h', '15m']
            primary_timeframe = None  # Should auto-select shortest

            def _init_indicators(self):
                pass

            def next(self):
                pass

        broker, data, params = Mock(), Mock(), {}
        strategy = AutoPrimaryStrategy(broker, data, params)

        # Mock the timeframe data to avoid errors
        strategy.set_timeframe_data({
            '1wk': Mock(), '1d': Mock(), '1h': Mock(), '15m': Mock()
        })

        strategy.init()
        assert strategy.primary_timeframe == '15m'  # Shortest timeframe

    def test_timeframe_data_access(self, strategy_class):
        """Test timeframe data access methods"""
        broker, data, params = Mock(), Mock(), {}
        strategy = strategy_class(broker, data, params)

        # Mock timeframe data
        mock_weekly_data = pd.DataFrame({'Close': [100, 101, 102]})
        mock_daily_data = pd.DataFrame({'Close': [100, 101, 102, 103]})
        mock_hourly_data = pd.DataFrame({'Close': [100, 101, 102, 103, 104]})

        tf_data = {
            '1wk': mock_weekly_data,
            '1d': mock_daily_data,
            '1h': mock_hourly_data
        }

        strategy.set_timeframe_data(tf_data)

        # Test data retrieval
        assert strategy.get_timeframe_data('1wk').equals(mock_weekly_data)
        assert strategy.get_timeframe_data('1d').equals(mock_daily_data)
        assert strategy.get_timeframe_data('1h').equals(mock_hourly_data)

        # Test invalid timeframe
        with pytest.raises(ValueError, match="Timeframe '5m' not available"):
            strategy.get_timeframe_data('5m')

    def test_strategy_metadata(self, strategy_class):
        """Test strategy metadata generation"""
        broker, data, params = Mock(), Mock(), {}
        strategy = strategy_class(broker, data, params)

        metadata = strategy.get_strategy_metadata()

        assert metadata['is_multitimeframe'] == True
        assert metadata['timeframes'] == ['1wk', '1d', '1h']
        assert metadata['primary_timeframe'] == '1h'
        assert metadata['total_timeframes'] == 3


class TestMTFRSI2Strategy:
    """Test suite for MTF_RSI2 strategy"""

    def test_strategy_attributes(self):
        """Test MTF_RSI2 strategy attributes"""
        assert MTF_RSI2_Strategy.timeframes == ['1wk', '1d']
        assert MTF_RSI2_Strategy.primary_timeframe == '1d'
        assert MTF_RSI2_Strategy.weekly_sma_length == 20
        assert MTF_RSI2_Strategy.daily_rsi_length == 2
        assert MTF_RSI2_Strategy.daily_rsi_level == 5

    def test_strategy_metadata(self):
        """Test MTF_RSI2 strategy metadata"""
        broker, data, params = Mock(), Mock(), {}
        strategy = MTF_RSI2_Strategy(broker, data, params)

        metadata = strategy.get_strategy_metadata()

        assert metadata['strategy_type'] == "Mean Reversion with Trend Filter"
        assert metadata['weekly_sma_period'] == 20
        assert metadata['daily_rsi_period'] == 2
        assert metadata['daily_rsi_threshold'] == 5
        assert metadata['exit_sma_period'] == 5


class TestBacktestServiceMultiTimeframe:
    """Test suite for BacktestService multi-timeframe functionality"""

    @pytest.fixture
    def service(self):
        """Create a BacktestService instance"""
        return BacktestService()

    @pytest.fixture
    def mock_data(self):
        """Create mock OHLCV data"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        return pd.DataFrame({
            'Open': [100 + i for i in range(10)],
            'High': [101 + i for i in range(10)],
            'Low': [99 + i for i in range(10)],
            'Close': [100.5 + i for i in range(10)],
            'Volume': [1000 + i for i in range(10)]
        }, index=dates)

    def test_multitimeframe_strategy_detection(self, service):
        """Test multi-timeframe strategy detection"""
        # Test with multi-timeframe strategy
        assert service._is_multitimeframe_strategy(MTF_RSI2_Strategy) == True

        # Test with regular strategy (mock)
        class RegularStrategy:
            timeframes = []  # Empty timeframes attribute

        assert service._is_multitimeframe_strategy(RegularStrategy) == False

        class NoTimeframesStrategy:
            pass  # No timeframes attribute

        assert service._is_multitimeframe_strategy(NoTimeframesStrategy) == False

    def test_primary_timeframe_determination(self, service):
        """Test primary timeframe determination logic"""
        # Test with various timeframe combinations
        assert service._determine_primary_timeframe(['1wk', '1d', '1h']) == '1h'
        assert service._determine_primary_timeframe(['1mo', '1wk']) == '1wk'
        assert service._determine_primary_timeframe(['4h', '1d', '1h']) == '1h'
        assert service._determine_primary_timeframe(['1d']) == '1d'

        # Test with empty list
        with pytest.raises(ValueError, match="No valid timeframes provided"):
            service._determine_primary_timeframe([])

    def test_timeframe_data_alignment(self, service, mock_data):
        """Test multi-timeframe data alignment"""
        # Create mock datasets for different timeframes
        weekly_data = mock_data.iloc[::7]  # Every 7th row for weekly
        daily_data = mock_data.copy()

        datasets = {'1wk': weekly_data, '1d': daily_data}

        # Test alignment
        aligned = service._align_timeframes(datasets, '1d')

        # Should have both timeframes
        assert '1wk' in aligned
        assert '1d' in aligned

        # Daily data should remain unchanged (primary timeframe)
        assert aligned['1d'].equals(daily_data)

        # Weekly data should be aligned (forward-filled)
        assert len(aligned['1wk']) <= len(daily_data)

    @patch('connors_strategies.services.backtest_service.BacktestService._load_data_from_source')
    def test_fetch_multi_timeframe_data(self, mock_load_data, service, mock_data):
        """Test multi-timeframe data fetching"""
        # Mock data loading for different timeframes
        mock_load_data.return_value = mock_data

        timeframes = ['1wk', '1d']
        result = service.fetch_multi_timeframe_data(
            ticker='TEST',
            datasource='mock',
            timeframes=timeframes,
            start='2024-01-01',
            end='2024-01-10',
            market_config='test',
            primary_timeframe='1d'
        )

        # Should return data for all timeframes
        assert '1wk' in result
        assert '1d' in result

        # Should have called load_data for each timeframe
        assert mock_load_data.call_count == 2

        # Check call arguments
        calls = mock_load_data.call_args_list
        timeframes_called = [call[0][4] for call in calls]  # 5th argument is interval/timeframe
        assert '1wk' in timeframes_called
        assert '1d' in timeframes_called

    def test_fetch_multi_timeframe_data_with_dataset_file(self, service):
        """Test multi-timeframe data fetching with dataset file validation"""
        # Should raise error for multi-timeframe with dataset file
        with pytest.raises(ValueError, match="Dataset files are only supported for single timeframe"):
            service.fetch_multi_timeframe_data(
                ticker='TEST',
                datasource='mock',
                timeframes=['1wk', '1d'],
                start='2024-01-01',
                end='2024-01-10',
                market_config='test',
                dataset_file='/path/to/file.csv'
            )

    @patch('connors_strategies.services.backtest_service.BacktestService.fetch_multi_timeframe_data')
    @patch('connors_strategies.services.backtest_service.BacktestService._load_data_from_source')
    @patch('connors_strategies.services.backtest_service.Backtest')
    def test_run_backtest_with_multitimeframe(self, mock_backtest, mock_load_data, mock_fetch_mtf, service, mock_data):
        """Test running backtest with multi-timeframe strategy"""
        # Mock multi-timeframe data
        tf_data = {'1wk': mock_data, '1d': mock_data}
        mock_fetch_mtf.return_value = tf_data

        # Mock backtest results
        mock_bt_instance = Mock()
        mock_results = Mock()
        mock_results.__getitem__ = Mock(side_effect=lambda k: pd.DataFrame() if 'trades' in k else mock_data)
        mock_bt_instance.run.return_value = mock_results
        mock_backtest.return_value = mock_bt_instance

        # Mock registry and strategy
        with patch.object(service, 'registry') as mock_registry:
            mock_registry._strategies = {'MTF_RSI2': MTF_RSI2_Strategy}

            with patch.object(service, 'config_manager') as mock_config:
                mock_config.get_market_config.return_value = Mock(yf_ticker_suffix='')

                with patch.object(service, 'get_market_config_info') as mock_market_info:
                    mock_market_info.return_value = {'name': 'test'}

                    # Run backtest with multi-timeframe parameters
                    result = service.run_backtest(
                        ticker='TEST',
                        strategy='MTF_RSI2',
                        datasource='mock',
                        start='2024-01-01',
                        end='2024-01-10',
                        timeframes=['1wk', '1d'],
                        primary_timeframe='1d'
                    )

                    # Verify multi-timeframe result attributes
                    assert result.is_multitimeframe == True
                    assert result.timeframes_used == ['1wk', '1d']
                    assert result.primary_timeframe == '1d'
                    assert result.tf_data == tf_data

                    # Verify multi-timeframe data fetching was called
                    mock_fetch_mtf.assert_called_once()


class TestMultiTimeframeIntegration:
    """Integration tests for multi-timeframe functionality"""

    @pytest.fixture
    def service(self):
        """Create a BacktestService instance"""
        return BacktestService()

    def test_multitimeframe_strategy_registration(self, service):
        """Test that MTF_RSI2 strategy is properly registered"""
        strategies = service.get_strategies()
        assert 'MTF_RSI2' in strategies

    def test_multitimeframe_strategy_info(self, service):
        """Test getting strategy info for multi-timeframe strategy"""
        strategy_info = service.get_strategy_info('MTF_RSI2')

        assert strategy_info is not None
        assert strategy_info['name'] == 'MTF_RSI2'
        assert 'MTF_RSI2_Strategy' in strategy_info['class_name']

    @patch('connors_strategies.services.backtest_service.BacktestService.fetch_multi_timeframe_data')
    def test_run_multiple_backtests_with_multitimeframe(self, mock_fetch_mtf, service):
        """Test running multiple backtests with multi-timeframe parameters"""
        # Mock data
        mock_data = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [101, 102, 103],
            'Low': [99, 100, 101],
            'Close': [100, 101, 102],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range('2024-01-01', periods=3))

        tf_data = {'1wk': mock_data, '1d': mock_data}
        mock_fetch_mtf.return_value = tf_data

        # Mock other dependencies
        with patch('connors_strategies.services.backtest_service.Backtest') as mock_backtest:
            mock_bt_instance = Mock()
            mock_results = Mock()
            mock_results.__getitem__ = Mock(side_effect=lambda k: pd.DataFrame() if 'trades' in k else mock_data)
            mock_bt_instance.run.return_value = mock_results
            mock_backtest.return_value = mock_bt_instance

            with patch.object(service, 'config_manager') as mock_config:
                mock_config.get_market_config.return_value = Mock(yf_ticker_suffix='')

                with patch.object(service, 'get_market_config_info') as mock_market_info:
                    mock_market_info.return_value = {'name': 'test'}

                    # Test run_multiple_backtests with multi-timeframe
                    results = service.run_multiple_backtests(
                        tickers=['TEST1', 'TEST2'],
                        strategy='MTF_RSI2',
                        datasource='mock',
                        start='2024-01-01',
                        end='2024-01-10',
                        timeframes=['1wk', '1d'],
                        primary_timeframe='1d'
                    )

                    assert len(results) == 2
                    for result in results:
                        assert result.is_multitimeframe == True
                        assert result.timeframes_used == ['1wk', '1d']
                        assert result.primary_timeframe == '1d'


class TestMultiTimeframeErrorHandling:
    """Test error handling in multi-timeframe functionality"""

    @pytest.fixture
    def service(self):
        """Create a BacktestService instance"""
        return BacktestService()

    def test_invalid_primary_timeframe_error(self, service):
        """Test error when primary timeframe not in timeframes list"""
        with patch.object(service, '_is_multitimeframe_strategy') as mock_is_mtf:
            mock_is_mtf.return_value = True

            with patch.object(service.registry, '_strategies') as mock_strategies:
                mock_strategy = Mock()
                mock_strategy.timeframes = ['1wk', '1d']
                mock_strategies.get.return_value = mock_strategy

                with pytest.raises(ValueError, match="Primary timeframe '1h' must be in timeframes list"):
                    service.run_backtest(
                        ticker='TEST',
                        strategy='MTF_TEST',
                        datasource='mock',
                        start='2024-01-01',
                        end='2024-01-10',
                        timeframes=['1wk', '1d'],
                        primary_timeframe='1h'  # Not in timeframes list
                    )

    def test_missing_timeframes_error(self, service):
        """Test error when multi-timeframe strategy has no timeframes specified"""
        with patch.object(service, '_is_multitimeframe_strategy') as mock_is_mtf:
            mock_is_mtf.return_value = True

            with patch.object(service.registry, '_strategies') as mock_strategies:
                mock_strategy = Mock()
                mock_strategy.timeframes = []  # Empty timeframes
                mock_strategies.get.return_value = mock_strategy

                with pytest.raises(ValueError, match="Multi-timeframe strategy requires timeframes to be specified"):
                    service.run_backtest(
                        ticker='TEST',
                        strategy='MTF_TEST',
                        datasource='mock',
                        start='2024-01-01',
                        end='2024-01-10'
                        # No timeframes provided
                    )

    @patch('connors_strategies.services.backtest_service.BacktestService._load_data_from_source')
    def test_partial_timeframe_data_failure(self, mock_load_data, service):
        """Test handling when some timeframes fail to load data"""
        # Mock one successful and one failed data load
        def side_effect(datasource, ticker, start, end, tf, market_config):
            if tf == '1wk':
                raise Exception("Failed to fetch weekly data")
            else:
                dates = pd.date_range('2024-01-01', periods=5)
                return pd.DataFrame({
                    'Open': [100, 101, 102, 103, 104],
                    'High': [101, 102, 103, 104, 105],
                    'Low': [99, 100, 101, 102, 103],
                    'Close': [100, 101, 102, 103, 104],
                    'Volume': [1000, 1100, 1200, 1300, 1400]
                }, index=dates)

        mock_load_data.side_effect = side_effect

        # Should continue with available data
        result = service.fetch_multi_timeframe_data(
            ticker='TEST',
            datasource='mock',
            timeframes=['1wk', '1d'],
            start='2024-01-01',
            end='2024-01-10',
            market_config='test'
        )

        # Should only have daily data (weekly failed)
        assert '1d' in result
        assert '1wk' not in result