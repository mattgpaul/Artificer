"""Unit and integration tests for queue_processor.

Tests cover queue processing, data validation, empty data handling, tag column validation,
dynamic table name resolution, target database handling, error handling, and complete workflows.
All external dependencies are mocked via conftest.py. Integration tests use 'debug' database.
"""

import pytest

from system.algo_trader.influx.publisher.queue_processor import process_queue


class TestProcessQueueEmptyQueue:
    """Test process_queue with empty queue."""

    @pytest.mark.unit
    def test_process_queue_empty_queue(self, mock_queue_broker, mock_market_data_influx):
        """Test processing empty queue."""
        mock_queue_broker.get_queue_size.return_value = 0

        queue_config = {"name": "test_queue", "table": "test_table"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 0
        assert failed == 0
        mock_queue_broker.dequeue.assert_not_called()


class TestProcessQueueOHLCVQueue:
    """Test process_queue for OHLCV queue."""

    @pytest.mark.unit
    def test_process_queue_ohlcv_success(
        self, mock_queue_broker, mock_market_data_influx, sample_ohlcv_queue_data
    ):
        """Test successful OHLCV queue processing."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["AAPL_20240101", None]
        mock_queue_broker.get_data.return_value = sample_ohlcv_queue_data
        mock_market_data_influx.write.return_value = True

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 1
        assert failed == 0
        mock_market_data_influx.write.assert_called_once()

    @pytest.mark.unit
    def test_process_queue_ohlcv_empty_candles(self, mock_queue_broker, mock_market_data_influx):
        """Test handling empty candles list."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["AAPL_20240101", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "candles": [],
            "database": "debug",
        }

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 0
        assert failed == 1
        mock_queue_broker.delete_data.assert_called_once()

    @pytest.mark.unit
    def test_process_queue_ohlcv_empty_datetime(self, mock_queue_broker, mock_market_data_influx):
        """Test handling empty datetime array."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["AAPL_20240101", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "data": {"datetime": []},
            "database": "debug",
        }

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 0
        assert failed == 1


class TestProcessQueueBacktestQueues:
    """Test process_queue for backtest queues."""

    @pytest.mark.unit
    def test_process_queue_backtest_trades_success(
        self, mock_queue_broker, mock_market_data_influx, sample_backtest_trades_queue_data
    ):
        """Test successful backtest trades queue processing."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["backtest_1", None]
        mock_queue_broker.get_data.return_value = sample_backtest_trades_queue_data
        mock_market_data_influx.write.return_value = True

        queue_config = {"name": "backtest_trades_queue", "table": "backtest_trades"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 1
        assert failed == 0
        call_args = mock_market_data_influx.write.call_args
        assert call_args[1]["table"] == "SMACrossoverStrategy"  # Dynamic table name
        assert call_args[1]["database"] == "debug"

    @pytest.mark.unit
    def test_process_queue_backtest_metrics_success(
        self, mock_queue_broker, mock_market_data_influx, sample_backtest_metrics_queue_data
    ):
        """Test successful backtest metrics queue processing."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["backtest_1", None]
        mock_queue_broker.get_data.return_value = sample_backtest_metrics_queue_data
        mock_market_data_influx.write.return_value = True

        queue_config = {"name": "backtest_metrics_queue", "table": "backtest_metrics"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 1
        assert failed == 0
        call_args = mock_market_data_influx.write.call_args
        assert call_args[1]["table"] == "SMACrossoverStrategy_summary"  # Dynamic table name

    @pytest.mark.unit
    def test_process_queue_backtest_empty_datetime(
        self, mock_queue_broker, mock_market_data_influx
    ):
        """Test handling empty datetime in backtest queue."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["backtest_1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "strategy_name": "SMACrossoverStrategy",
            "backtest_id": "test-id",
            "data": {"datetime": []},
            "database": "debug",
        }

        queue_config = {"name": "backtest_trades_queue", "table": "backtest_trades"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 0
        assert failed == 1


class TestProcessQueueTagColumns:
    """Test tag column handling."""

    @pytest.mark.unit
    def test_process_queue_tag_columns_backtest_id(
        self, mock_queue_broker, mock_market_data_influx
    ):
        """Test backtest_id tag column handling."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["backtest_1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "strategy_name": "SMACrossoverStrategy",
            "backtest_id": "test-id",
            "data": {
                "datetime": [1704067200000],
                "entry_price": [100.0],
            },
            "database": "debug",
        }
        mock_market_data_influx.write.return_value = True

        queue_config = {"name": "backtest_trades_queue", "table": "backtest_trades"}
        processed, _failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 1
        call_args = mock_market_data_influx.write.call_args
        assert "backtest_id" in call_args[1]["tag_columns"]

    @pytest.mark.unit
    def test_process_queue_tag_columns_backtest_hash(
        self, mock_queue_broker, mock_market_data_influx
    ):
        """Test backtest_hash tag column handling."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["backtest_1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "strategy_name": "SMACrossoverStrategy",
            "backtest_hash": "abc123",
            "data": {
                "datetime": [1704067200000],
                "entry_price": [100.0],
            },
            "database": "debug",
        }
        mock_market_data_influx.write.return_value = True

        queue_config = {"name": "backtest_trades_queue", "table": "backtest_trades"}
        processed, _failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 1
        call_args = mock_market_data_influx.write.call_args
        assert "backtest_hash" in call_args[1]["tag_columns"]

    @pytest.mark.unit
    def test_process_queue_tag_columns_strategy(self, mock_queue_broker, mock_market_data_influx):
        """Test strategy tag column handling."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["backtest_1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "strategy_name": "SMACrossoverStrategy",
            "data": {
                "datetime": [1704067200000],
                "entry_price": [100.0],
            },
            "database": "debug",
        }
        mock_market_data_influx.write.return_value = True

        queue_config = {"name": "backtest_trades_queue", "table": "backtest_trades"}
        processed, _failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 1
        call_args = mock_market_data_influx.write.call_args
        assert "strategy" in call_args[1]["tag_columns"]

    @pytest.mark.unit
    def test_process_queue_tag_columns_none_values(
        self, mock_queue_broker, mock_market_data_influx
    ):
        """Test handling None tag values."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["backtest_1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "strategy_name": "SMACrossoverStrategy",
            "backtest_id": None,
            "backtest_hash": None,
            "data": {
                "datetime": [1704067200000],
                "entry_price": [100.0],
            },
            "database": "debug",
        }
        mock_market_data_influx.write.return_value = True

        queue_config = {"name": "backtest_trades_queue", "table": "backtest_trades"}
        processed, _failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 1
        # None values should not be added as tags


class TestProcessQueueErrorHandling:
    """Test error handling."""

    @pytest.mark.unit
    def test_process_queue_no_data(self, mock_queue_broker, mock_market_data_influx):
        """Test handling missing data."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item_1", None]
        mock_queue_broker.get_data.return_value = None

        queue_config = {"name": "test_queue", "table": "test_table"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 0
        assert failed == 1

    @pytest.mark.unit
    def test_process_queue_no_ticker(self, mock_queue_broker, mock_market_data_influx):
        """Test handling missing ticker."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item_1", None]
        mock_queue_broker.get_data.return_value = {
            "data": {"datetime": [1704067200000]},
            "database": "debug",
        }

        queue_config = {"name": "test_queue", "table": "test_table"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 0
        assert failed == 1
        mock_queue_broker.delete_data.assert_called_once()

    @pytest.mark.unit
    def test_process_queue_no_datetime(self, mock_queue_broker, mock_market_data_influx):
        """Test handling missing datetime array."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item_1", None]
        mock_queue_broker.get_data.return_value = {
            "ticker": "AAPL",
            "data": {"entry_price": [100.0]},
            "database": "debug",
        }

        queue_config = {"name": "test_queue", "table": "test_table"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 0
        assert failed == 1

    @pytest.mark.unit
    def test_process_queue_write_failure(
        self, mock_queue_broker, mock_market_data_influx, sample_ohlcv_queue_data
    ):
        """Test handling write failure."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item_1", None]
        mock_queue_broker.get_data.return_value = sample_ohlcv_queue_data
        mock_market_data_influx.write.return_value = False

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 0
        assert failed == 1


class TestProcessQueueTargetDatabase:
    """Test target database handling."""

    @pytest.mark.unit
    def test_process_queue_target_database(
        self, mock_queue_broker, mock_market_data_influx, sample_ohlcv_queue_data
    ):
        """Test target database specification."""
        mock_queue_broker.get_queue_size.return_value = 1
        mock_queue_broker.dequeue.side_effect = ["item_1", None]
        mock_queue_broker.get_data.return_value = sample_ohlcv_queue_data
        mock_market_data_influx.write.return_value = True

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        processed, _failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 1
        call_args = mock_market_data_influx.write.call_args
        assert call_args[1]["database"] == "debug"

    @pytest.mark.integration
    def test_process_queue_complete_workflow(
        self, mock_queue_broker, mock_market_data_influx, sample_candle
    ):
        """Test complete queue processing workflow."""
        mock_queue_broker.get_queue_size.return_value = 2
        mock_queue_broker.dequeue.side_effect = ["item_1", "item_2", None]
        # Create MSFT candle with different values
        msft_candle = sample_candle.copy()
        msft_candle.update(
            {"open": 200.0, "high": 205.0, "low": 199.0, "close": 204.0, "volume": 2000000}
        )
        msft_candle["datetime"] = sample_candle["datetime"] + 1000
        mock_queue_broker.get_data.side_effect = [
            {
                "ticker": "AAPL",
                "candles": [sample_candle],
                # No database specified - uses default client
            },
            {
                "ticker": "MSFT",
                "candles": [msft_candle],
                # No database specified - uses default client
            },
        ]
        mock_market_data_influx.write.return_value = True
        # Ensure database attribute exists for comparison
        mock_market_data_influx.database = "ohlcv"

        queue_config = {"name": "ohlcv_queue", "table": "ohlcv"}
        processed, failed = process_queue(
            queue_config=queue_config,
            queue_broker=mock_queue_broker,
            influx_client=mock_market_data_influx,
            running=True,
        )

        assert processed == 2
        assert failed == 0
        # When no database is specified in data, uses default client
        assert mock_market_data_influx.write.call_count == 2
