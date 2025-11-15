"""Unit tests for check_queues - Redis Queue Status Checker.

Tests cover queue status checking and diagnostics output.
All Redis operations are mocked to avoid requiring a Redis server.
"""

from unittest.mock import patch

from system.algo_trader.redis.check_queues import (
    BAD_TICKER_QUEUE,
    FUNDAMENTALS_QUEUE,
    FUNDAMENTALS_STATIC_QUEUE,
    OHLCV_QUEUE,
    check_queue_status,
    main,
)


class TestCheckQueueStatus:
    """Test check_queue_status function."""

    def test_check_queue_status_empty_queue(self, mock_check_queues_queue_broker):
        """Test checking empty queue."""
        mock_check_queues_queue_broker.get_queue_size.return_value = 0
        mock_check_queues_queue_broker.peek_queue.return_value = []
        mock_check_queues_queue_broker.get_data.return_value = None

        result = check_queue_status(mock_check_queues_queue_broker, "test_queue")

        assert result["size"] == 0
        assert result["sample_items"] == []
        assert result["sample_data"] == []

    def test_check_queue_status_with_items(self, mock_check_queues_queue_broker):
        """Test checking queue with items."""
        mock_check_queues_queue_broker.get_queue_size.return_value = 5
        mock_check_queues_queue_broker.peek_queue.return_value = ["item1", "item2", "item3"]
        mock_check_queues_queue_broker.get_data.side_effect = [
            {"ticker": "AAPL", "data": "test"},
            {"ticker": "TSLA", "data": "test"},
            None,  # Third item has no data
        ]

        result = check_queue_status(mock_check_queues_queue_broker, "test_queue")

        assert result["size"] == 5
        assert len(result["sample_items"]) == 3
        assert len(result["sample_data"]) == 2  # Only items with data

    def test_check_queue_status_extracts_ticker(self, mock_check_queues_queue_broker):
        """Test status extraction includes ticker information."""
        mock_check_queues_queue_broker.get_queue_size.return_value = 1
        mock_check_queues_queue_broker.peek_queue.return_value = ["item1"]
        mock_check_queues_queue_broker.get_data.return_value = {"ticker": "AAPL", "data": "test"}

        result = check_queue_status(mock_check_queues_queue_broker, "test_queue")

        assert len(result["sample_data"]) == 1
        assert result["sample_data"][0]["ticker"] == "AAPL"
        assert result["sample_data"][0]["item_id"] == "item1"

    def test_check_queue_status_limits_sample_data(self, mock_check_queues_queue_broker):
        """Test status limits sample data to first 3 items."""
        mock_check_queues_queue_broker.get_queue_size.return_value = 10
        mock_check_queues_queue_broker.peek_queue.return_value = [
            "item1",
            "item2",
            "item3",
            "item4",
            "item5",
        ]
        mock_check_queues_queue_broker.get_data.side_effect = [
            {"ticker": "AAPL"},
            {"ticker": "TSLA"},
            {"ticker": "GOOGL"},
            {"ticker": "MSFT"},
            {"ticker": "AMZN"},
        ]

        result = check_queue_status(mock_check_queues_queue_broker, "test_queue")

        assert len(result["sample_data"]) == 3  # Limited to first 3

    def test_check_queue_status_limits_sample_items(self, mock_check_queues_queue_broker):
        """Test status limits sample items to first 10."""
        mock_check_queues_queue_broker.get_queue_size.return_value = 20
        mock_check_queues_queue_broker.peek_queue.return_value = [f"item{i}" for i in range(15)]

        result = check_queue_status(mock_check_queues_queue_broker, "test_queue")

        assert len(result["sample_items"]) == 10  # Limited to first 10


class TestCheckQueuesMain:
    """Test main function."""

    def test_main_success_empty_queues(
        self, mock_check_queues_logger, mock_check_queues_queue_broker
    ):
        """Test main returns 0 when all queues are empty."""
        mock_check_queues_queue_broker.get_queue_size.return_value = 0
        mock_check_queues_queue_broker.peek_queue.return_value = []

        result = main()

        assert result == 0

    def test_main_success_with_pending_items(
        self, mock_check_queues_logger, mock_check_queues_queue_broker
    ):
        """Test main returns 0 even with pending items."""

        def queue_size_side_effect(queue_name):
            if queue_name == OHLCV_QUEUE:
                return 5
            return 0

        mock_check_queues_queue_broker.get_queue_size.side_effect = queue_size_side_effect
        mock_check_queues_queue_broker.peek_queue.return_value = ["item1", "item2"]

        result = main()

        assert result == 0

    def test_main_handles_exception(self, mock_check_queues_logger):
        """Test main handles exceptions gracefully."""
        with patch("system.algo_trader.redis.check_queues.QueueBroker") as mock_queue_broker_class:
            mock_queue_broker_class.side_effect = Exception("Connection error")

            result = main()

            assert result == 1

    def test_main_checks_all_queues(self, mock_check_queues_logger, mock_check_queues_queue_broker):
        """Test main checks all configured queues."""
        mock_check_queues_queue_broker.get_queue_size.return_value = 0
        mock_check_queues_queue_broker.peek_queue.return_value = []

        main()

        # Verify all queues were checked
        assert mock_check_queues_queue_broker.get_queue_size.call_count >= 4

    def test_main_calculates_total_pending(
        self, mock_check_queues_logger, mock_check_queues_queue_broker
    ):
        """Test main calculates total pending items."""

        def queue_size_side_effect(queue_name):
            sizes = {
                FUNDAMENTALS_STATIC_QUEUE: 3,
                FUNDAMENTALS_QUEUE: 5,
                OHLCV_QUEUE: 2,
                BAD_TICKER_QUEUE: 1,
            }
            return sizes.get(queue_name, 0)

        mock_check_queues_queue_broker.get_queue_size.side_effect = queue_size_side_effect
        mock_check_queues_queue_broker.peek_queue.return_value = []

        result = main()

        assert result == 0
        # Total should be 3 + 5 + 2 + 1 = 11


class TestCheckQueuesConstants:
    """Test queue name constants."""

    def test_queue_constants_defined(self):
        """Test all queue constants are defined."""
        assert FUNDAMENTALS_STATIC_QUEUE == "fundamentals_static_queue"
        assert FUNDAMENTALS_QUEUE == "fundamentals_queue"
        assert OHLCV_QUEUE == "ohlcv_queue"
        assert BAD_TICKER_QUEUE == "bad_ticker_queue"

