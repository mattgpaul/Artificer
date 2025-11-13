"""Unit tests for FundamentalsDaemon - Fundamentals Queue Processing.

Tests cover initialization, signal handling, queue processing, and cleanup.
All Redis and SQLite operations are mocked. Thread tests use timeouts.
"""

import signal

import pytest

from system.algo_trader.sqlite.fundamentals_daemon import (
    FUNDAMENTALS_STATIC_QUEUE_NAME,
    FundamentalsDaemon,
)


class TestFundamentalsDaemonInitialization:
    """Test FundamentalsDaemon initialization."""

    def test_initialization_success(self, mock_fundamentals_daemon_dependencies):
        """Test successful daemon initialization."""
        daemon = FundamentalsDaemon()

        assert daemon.running is False
        assert daemon.queue_broker is not None
        assert daemon.sqlite_client is not None
        assert daemon.logger is not None
        # Verify signal handlers registered
        assert mock_fundamentals_daemon_dependencies["signal"].call_count == 2

    def test_initialization_creates_components(self, mock_fundamentals_daemon_dependencies):
        """Test initialization creates QueueBroker and FundamentalsClient."""
        daemon = FundamentalsDaemon()

        assert daemon.queue_broker is mock_fundamentals_daemon_dependencies["queue_broker"]
        assert daemon.sqlite_client is mock_fundamentals_daemon_dependencies["client"]


class TestFundamentalsDaemonSignalHandling:
    """Test signal handling."""

    def test_signal_handler_sets_running_false(self, mock_fundamentals_daemon_dependencies):
        """Test signal handler stops daemon."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        daemon._signal_handler(signal.SIGTERM, None)

        assert daemon.running is False
        mock_fundamentals_daemon_dependencies["logger"].info.assert_called()

    def test_signal_handler_logs_signal_name(self, mock_fundamentals_daemon_dependencies):
        """Test signal handler logs correct signal name."""
        daemon = FundamentalsDaemon()

        daemon._signal_handler(signal.SIGINT, None)

        # Verify signal name was logged
        log_calls = mock_fundamentals_daemon_dependencies["logger"].info.call_args_list
        assert any("SIGINT" in str(call) for call in log_calls)


class TestFundamentalsDaemonQueueProcessing:
    """Test queue processing operations."""

    def test_process_queue_empty_queue(self, mock_fundamentals_daemon_dependencies):
        """Test processing empty queue returns early."""
        daemon = FundamentalsDaemon()
        mock_fundamentals_daemon_dependencies["queue_broker"].get_queue_size.return_value = 0

        daemon._process_queue()

        mock_fundamentals_daemon_dependencies["queue_broker"].dequeue.assert_not_called()

    def test_process_queue_successful_processing(self, mock_fundamentals_daemon_dependencies):
        """Test successful queue item processing."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        # Make dequeue return None after first item to exit loop
        call_count = {"count": 0}

        def dequeue_side_effect(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return "item_1"
            return None

        mock_fundamentals_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_fundamentals_daemon_dependencies[
            "queue_broker"
        ].dequeue.side_effect = dequeue_side_effect
        mock_fundamentals_daemon_dependencies["queue_broker"].get_data.return_value = {
            "ticker": "AAPL",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "entity_name": "Apple Inc.",
            "sic": "3571",
        }
        mock_fundamentals_daemon_dependencies["client"].upsert_fundamentals.return_value = True

        daemon._process_queue()

        mock_fundamentals_daemon_dependencies["client"].upsert_fundamentals.assert_called_once_with(
            {
                "ticker": "AAPL",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "entity_name": "Apple Inc.",
                "sic": "3571",
            }
        )
        mock_fundamentals_daemon_dependencies["queue_broker"].delete_data.assert_called_with(
            FUNDAMENTALS_STATIC_QUEUE_NAME, "item_1"
        )
        mock_fundamentals_daemon_dependencies["logger"].info.assert_called()

    def test_process_queue_missing_data(self, mock_fundamentals_daemon_dependencies):
        """Test processing handles missing data."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        call_count = {"count": 0}

        def dequeue_side_effect(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return "item_1"
            return None

        mock_fundamentals_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_fundamentals_daemon_dependencies[
            "queue_broker"
        ].dequeue.side_effect = dequeue_side_effect
        mock_fundamentals_daemon_dependencies["queue_broker"].get_data.return_value = None

        daemon._process_queue()

        mock_fundamentals_daemon_dependencies["logger"].error.assert_called()
        mock_fundamentals_daemon_dependencies["client"].upsert_fundamentals.assert_not_called()

    def test_process_queue_invalid_data_structure(self, mock_fundamentals_daemon_dependencies):
        """Test processing handles invalid data structure."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        call_count = {"count": 0}

        def dequeue_side_effect(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return "item_1"
            return None

        mock_fundamentals_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_fundamentals_daemon_dependencies[
            "queue_broker"
        ].dequeue.side_effect = dequeue_side_effect
        mock_fundamentals_daemon_dependencies["queue_broker"].get_data.return_value = {
            "sector": "Technology"
        }  # Missing ticker

        daemon._process_queue()

        mock_fundamentals_daemon_dependencies["logger"].error.assert_called()
        mock_fundamentals_daemon_dependencies["queue_broker"].delete_data.assert_called()

    def test_process_queue_sqlite_failure(self, mock_fundamentals_daemon_dependencies):
        """Test processing handles SQLite write failure."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        call_count = {"count": 0}

        def dequeue_side_effect(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return "item_1"
            return None

        mock_fundamentals_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_fundamentals_daemon_dependencies[
            "queue_broker"
        ].dequeue.side_effect = dequeue_side_effect
        mock_fundamentals_daemon_dependencies["queue_broker"].get_data.return_value = {
            "ticker": "AAPL",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "entity_name": "Apple Inc.",
            "sic": "3571",
        }
        mock_fundamentals_daemon_dependencies["client"].upsert_fundamentals.return_value = False

        daemon._process_queue()

        mock_fundamentals_daemon_dependencies["logger"].error.assert_called()
        mock_fundamentals_daemon_dependencies["queue_broker"].delete_data.assert_called()

    def test_process_queue_exception_handling(self, mock_fundamentals_daemon_dependencies):
        """Test processing handles exceptions."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        call_count = {"count": 0}

        def dequeue_side_effect(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return "item_1"
            return None

        mock_fundamentals_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_fundamentals_daemon_dependencies[
            "queue_broker"
        ].dequeue.side_effect = dequeue_side_effect
        mock_fundamentals_daemon_dependencies["queue_broker"].get_data.side_effect = Exception(
            "Redis error"
        )

        daemon._process_queue()

        mock_fundamentals_daemon_dependencies["logger"].error.assert_called()
        mock_fundamentals_daemon_dependencies["queue_broker"].delete_data.assert_called()

    def test_process_queue_stops_when_running_false(self, mock_fundamentals_daemon_dependencies):
        """Test processing stops when running flag is False."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        mock_fundamentals_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1

        def dequeue_side_effect(*args, **kwargs):
            daemon.running = False
            return "item_1"

        mock_fundamentals_daemon_dependencies[
            "queue_broker"
        ].dequeue.side_effect = dequeue_side_effect

        daemon._process_queue()

        # Should stop after first item when running becomes False
        assert daemon.running is False


class TestFundamentalsDaemonRunLoop:
    """Test daemon main run loop."""

    @pytest.mark.timeout(2)
    def test_run_loop_processes_queue(self, mock_fundamentals_daemon_dependencies):
        """Test run loop processes queue and sleeps."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        # Make run loop exit after one iteration
        call_count = {"count": 0}

        def stop_after_one(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return 0  # Empty queue, will return early from _process_queue
            daemon.running = False
            return 0

        mock_fundamentals_daemon_dependencies[
            "queue_broker"
        ].get_queue_size.side_effect = stop_after_one

        daemon.run()

        mock_fundamentals_daemon_dependencies["queue_broker"].get_queue_size.assert_called()
        mock_fundamentals_daemon_dependencies["sleep"].assert_called()

    @pytest.mark.timeout(2)
    def test_run_loop_handles_exceptions(self, mock_fundamentals_daemon_dependencies):
        """Test run loop handles exceptions gracefully."""
        daemon = FundamentalsDaemon()
        daemon.running = True

        call_count = {"count": 0}

        def raise_then_stop(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise Exception("Processing error")
            daemon.running = False
            return 0

        mock_fundamentals_daemon_dependencies[
            "queue_broker"
        ].get_queue_size.side_effect = raise_then_stop

        daemon.run()

        mock_fundamentals_daemon_dependencies["logger"].error.assert_called()
        assert daemon.running is False


class TestFundamentalsDaemonCleanup:
    """Test daemon cleanup operations."""

    def test_cleanup_closes_sqlite_client(self, mock_fundamentals_daemon_dependencies):
        """Test cleanup closes SQLite client."""
        daemon = FundamentalsDaemon()
        daemon._cleanup()

        mock_fundamentals_daemon_dependencies["client"].close.assert_called_once()
        mock_fundamentals_daemon_dependencies["logger"].info.assert_called()

    def test_cleanup_handles_close_error(self, mock_fundamentals_daemon_dependencies):
        """Test cleanup handles SQLite close errors."""
        daemon = FundamentalsDaemon()
        mock_fundamentals_daemon_dependencies["client"].close.side_effect = Exception("Close error")

        daemon._cleanup()

        mock_fundamentals_daemon_dependencies["logger"].warning.assert_called()
