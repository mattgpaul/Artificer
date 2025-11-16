"""Unit and integration tests for OHLCVProcessor.

Tests cover initialization, ticker processing, thread management, MarketHandler
integration, QueueBroker operations, bad ticker handling, and complete workflows.
All external dependencies are mocked via conftest.py. Integration tests use
'debug' database.
"""

from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.datasource.populate.ohlcv.processor import OHLCVProcessor
from system.algo_trader.schwab.timescale_enum import FrequencyType, PeriodType


class TestOHLCVProcessorInitialization:
    """Test OHLCVProcessor initialization."""

    @pytest.mark.unit
    def test_initialization_default_logger(self):
        """Test initialization creates default logger."""
        with patch(
            "system.algo_trader.datasource.populate.ohlcv.processor.get_logger"
        ) as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            processor = OHLCVProcessor()

            assert processor.logger == mock_logger
            mock_get_logger.assert_called_once_with("OHLCVProcessor")

    @pytest.mark.unit
    def test_initialization_custom_logger(self):
        """Test initialization with custom logger."""
        custom_logger = MagicMock()
        processor = OHLCVProcessor(logger=custom_logger)

        assert processor.logger == custom_logger


class TestOHLCVProcessorProcessTickers:
    """Test process_tickers method."""

    @pytest.mark.unit
    def test_process_tickers_none_tickers(self, mock_logger):
        """Test process_tickers with None tickers."""
        processor = OHLCVProcessor(logger=mock_logger)

        processor.process_tickers(
            tickers=None,
            frequency_type=FrequencyType.DAILY,
            frequency_value=1,
            period_type=PeriodType.MONTH,
            period_value=1,
        )

        mock_logger.error.assert_called_once_with("No tickers found")

    @pytest.mark.unit
    def test_process_tickers_empty_list(self, mock_logger):
        """Test process_tickers with empty ticker list."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            processor.process_tickers(
                tickers=[],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Should log info but not process anything
            mock_logger.info.assert_called()

    @pytest.mark.unit
    def test_process_tickers_logs_info(self, mock_logger):
        """Test process_tickers logs processing info."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            mock_logger.info.assert_called()
            call_args_str = str(mock_logger.info.call_args_list)
            assert "OHLCV data population" in call_args_str

    @pytest.mark.unit
    def test_process_tickers_creates_components(self, mock_logger):
        """Test process_tickers creates MarketHandler, ThreadManager, QueueBroker."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            mock_market_handler_class.assert_called_once()
            mock_thread_manager_class.assert_called_once()
            mock_queue_broker_class.assert_called_once_with(namespace="queue")


class TestOHLCVProcessorFetchTickerData:
    """Test fetch_ticker_data inner function."""

    @pytest.mark.unit
    def test_fetch_ticker_data_success(self, mock_logger):
        """Test successful ticker data fetch."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = {
                "candles": [
                    {"open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000000}
                ]
            }
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker.enqueue.return_value = True
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 1,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Verify MarketHandler was called
            mock_market_handler.get_price_history.assert_called()

    @pytest.mark.unit
    def test_fetch_ticker_data_server_error(self, mock_logger):
        """Test handling server errors (500/502)."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = {
                "_error_status": 500,
                "error": "Internal Server Error",
            }
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Should not enqueue bad ticker for server errors
            bad_ticker_calls = [
                call
                for call in mock_queue_broker.enqueue.call_args_list
                if call[1].get("queue_name") == "bad_ticker_queue"
            ]
            assert len(bad_ticker_calls) == 0

    @pytest.mark.unit
    def test_fetch_ticker_data_api_error(self, mock_logger):
        """Test handling API errors (404, 400)."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = {
                "_error_status": 404,
                "error": "Not Found",
            }
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Should enqueue bad ticker for API errors
            bad_ticker_calls = [
                call
                for call in mock_queue_broker.enqueue.call_args_list
                if call[1].get("queue_name") == "bad_ticker_queue"
            ]
            assert len(bad_ticker_calls) > 0

    @pytest.mark.unit
    def test_fetch_ticker_data_empty_response(self, mock_logger):
        """Test handling empty response."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = {}
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Should enqueue bad ticker
            bad_ticker_calls = [
                call
                for call in mock_queue_broker.enqueue.call_args_list
                if call[1].get("queue_name") == "bad_ticker_queue"
            ]
            assert len(bad_ticker_calls) > 0

    @pytest.mark.unit
    def test_fetch_ticker_data_no_candles(self, mock_logger):
        """Test handling response without candles."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = {"data": "no candles"}
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Should enqueue bad ticker
            bad_ticker_calls = [
                call
                for call in mock_queue_broker.enqueue.call_args_list
                if call[1].get("queue_name") == "bad_ticker_queue"
            ]
            assert len(bad_ticker_calls) > 0

    @pytest.mark.unit
    def test_fetch_ticker_data_empty_candles(self, mock_logger):
        """Test handling empty candles list."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = {"candles": []}
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Should enqueue bad ticker
            bad_ticker_calls = [
                call
                for call in mock_queue_broker.enqueue.call_args_list
                if call[1].get("queue_name") == "bad_ticker_queue"
            ]
            assert len(bad_ticker_calls) > 0

    @pytest.mark.unit
    def test_fetch_ticker_data_redis_enqueue_failure(self, mock_logger):
        """Test handling Redis enqueue failure."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = {
                "candles": [
                    {"open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000000}
                ]
            }
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker.enqueue.return_value = False  # Enqueue failure
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 1,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            mock_logger.error.assert_called()
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any("Failed to enqueue" in str(call) for call in error_calls)

    @pytest.mark.unit
    def test_fetch_ticker_data_exception(self, mock_logger):
        """Test handling exceptions during processing."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.side_effect = Exception("API error")
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 1,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            mock_logger.error.assert_called()
            error_calls = [str(call) for call in mock_logger.error.call_args_list]
            assert any("Exception during processing" in str(call) for call in error_calls)


class TestOHLCVProcessorThreadManagement:
    """Test thread management functionality."""

    @pytest.mark.unit
    def test_process_tickers_batching(self, mock_logger):
        """Test ticker batching when count exceeds max_threads."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 0,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"] * 10,  # More than MAX_THREADS (4)
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            mock_logger.info.assert_called()
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Batching will be used" in str(call) for call in info_calls)

    @pytest.mark.integration
    def test_process_tickers_complete_workflow(self, mock_logger):
        """Test complete workflow: tickers → threads → API → Redis."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_market_handler = MagicMock()
            mock_market_handler.get_price_history.return_value = {
                "candles": [
                    {"open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1000000}
                ]
            }
            mock_market_handler_class.return_value = mock_market_handler

            mock_queue_broker = MagicMock()
            mock_queue_broker.enqueue.return_value = True
            mock_queue_broker_class.return_value = mock_queue_broker

            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 2,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL", "MSFT"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Verify components created
            mock_market_handler_class.assert_called_once()
            mock_thread_manager_class.assert_called_once()
            mock_queue_broker_class.assert_called_once()

            # Verify summary printed
            mock_logger.info.assert_called()
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Batch processing complete" in str(call) for call in info_calls)

    @pytest.mark.integration
    def test_process_tickers_thread_manager_integration(self, mock_logger):
        """Test ThreadManager integration."""
        processor = OHLCVProcessor(logger=mock_logger)

        with (
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.MarketHandler"
            ) as mock_market_handler_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.ThreadManager"
            ) as mock_thread_manager_class,
            patch(
                "system.algo_trader.datasource.populate.ohlcv.processor.QueueBroker"
            ) as mock_queue_broker_class,
        ):
            mock_thread_manager = MagicMock()
            mock_thread_manager.get_active_thread_count.return_value = 0
            mock_thread_manager.get_results_summary.return_value = {
                "successful": 1,
                "failed": 0,
            }
            mock_thread_manager.wait_for_all_threads.return_value = None
            mock_thread_manager.cleanup_dead_threads.return_value = None
            mock_thread_manager.start_thread = MagicMock()
            mock_thread_manager_class.return_value = mock_thread_manager

            processor.process_tickers(
                tickers=["AAPL"],
                frequency_type=FrequencyType.DAILY,
                frequency_value=1,
                period_type=PeriodType.MONTH,
                period_value=1,
            )

            # Verify ThreadManager methods called
            mock_thread_manager.wait_for_all_threads.assert_called_once()
            mock_thread_manager.cleanup_dead_threads.assert_called_once()
            mock_thread_manager.get_results_summary.assert_called()

