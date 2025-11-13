"""Unit tests for UnifiedMySQLDaemon - MySQL Queue Processing.

Tests cover initialization, signal handling, queue processing, and cleanup.
All Redis and MySQL operations are mocked. Thread tests use timeouts.
"""

import signal

import pytest

from system.algo_trader.mysql.unified_mysql_daemon import (
    BAD_TICKER_QUEUE_NAME,
    FUNDAMENTALS_STATIC_QUEUE_NAME,
    UnifiedMySQLDaemon,
)


class TestUnifiedMySQLDaemonInitialization:
    """Test UnifiedMySQLDaemon initialization."""

    def test_initialization_success(self, mock_unified_mysql_daemon_dependencies):
        """Test successful daemon initialization."""
        daemon = UnifiedMySQLDaemon()

        assert daemon.running is False
        assert daemon.queue_broker is not None
        assert daemon.bad_ticker_client is not None
        assert daemon.fundamentals_client is not None
        assert daemon.logger is not None
        # Verify signal handlers registered
        assert mock_unified_mysql_daemon_dependencies["signal"].call_count == 2

    def test_initialization_creates_components(self, mock_unified_mysql_daemon_dependencies):
        """Test initialization creates QueueBroker and MySQL clients."""
        daemon = UnifiedMySQLDaemon()

        assert daemon.queue_broker is mock_unified_mysql_daemon_dependencies["queue_broker"]
        assert daemon.bad_ticker_client is mock_unified_mysql_daemon_dependencies["bad_ticker_client"]
        assert daemon.fundamentals_client is mock_unified_mysql_daemon_dependencies["fundamentals_client"]


class TestUnifiedMySQLDaemonSignalHandling:
    """Test signal handling."""

    def test_signal_handler_sets_running_false(self, mock_unified_mysql_daemon_dependencies):
        """Test signal handler stops daemon."""
        daemon = UnifiedMySQLDaemon()
        daemon.running = True

        daemon._signal_handler(signal.SIGTERM, None)

        assert daemon.running is False
        mock_unified_mysql_daemon_dependencies["logger"].info.assert_called()

    def test_signal_handler_logs_signal_name(self, mock_unified_mysql_daemon_dependencies):
        """Test signal handler logs correct signal name."""
        daemon = UnifiedMySQLDaemon()

        daemon._signal_handler(signal.SIGINT, None)

        # Verify signal name was logged
        log_calls = mock_unified_mysql_daemon_dependencies["logger"].info.call_args_list
        assert any("SIGINT" in str(call) for call in log_calls)


class TestUnifiedMySQLDaemonQueueProcessing:
    """Test queue processing operations."""

    def test_process_bad_ticker_queue_empty(self, mock_unified_mysql_daemon_dependencies):
        """Test processing empty bad ticker queue returns early."""
        daemon = UnifiedMySQLDaemon()
        mock_unified_mysql_daemon_dependencies["queue_broker"].get_queue_size.return_value = 0

        daemon._process_bad_ticker_queue()

        mock_unified_mysql_daemon_dependencies["queue_broker"].dequeue.assert_not_called()

    def test_process_fundamentals_queue_empty(self, mock_unified_mysql_daemon_dependencies):
        """Test processing empty fundamentals queue returns early."""
        daemon = UnifiedMySQLDaemon()
        mock_unified_mysql_daemon_dependencies["queue_broker"].get_queue_size.return_value = 0

        daemon._process_fundamentals_queue()

        mock_unified_mysql_daemon_dependencies["queue_broker"].dequeue.assert_not_called()

    def test_process_bad_ticker_queue_success(self, mock_unified_mysql_daemon_dependencies):
        """Test successful bad ticker queue processing."""
        daemon = UnifiedMySQLDaemon()
        daemon.running = True

        mock_unified_mysql_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_unified_mysql_daemon_dependencies["queue_broker"].dequeue.side_effect = ["item1", None]
        mock_unified_mysql_daemon_dependencies["queue_broker"].get_data.return_value = {
            "ticker": "AAPL",
            "timestamp": "2024-01-01T00:00:00",
            "reason": "Invalid",
        }
        mock_unified_mysql_daemon_dependencies["bad_ticker_client"].log_bad_ticker.return_value = True

        daemon._process_bad_ticker_queue()

        mock_unified_mysql_daemon_dependencies["bad_ticker_client"].log_bad_ticker.assert_called_once()
        mock_unified_mysql_daemon_dependencies["queue_broker"].delete_data.assert_called()

    def test_process_fundamentals_queue_success(self, mock_unified_mysql_daemon_dependencies):
        """Test successful fundamentals queue processing."""
        daemon = UnifiedMySQLDaemon()
        daemon.running = True

        mock_unified_mysql_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_unified_mysql_daemon_dependencies["queue_broker"].dequeue.side_effect = ["item1", None]
        mock_unified_mysql_daemon_dependencies["queue_broker"].get_data.return_value = {
            "ticker": "AAPL",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        }
        mock_unified_mysql_daemon_dependencies["fundamentals_client"].upsert_fundamentals.return_value = True

        daemon._process_fundamentals_queue()

        mock_unified_mysql_daemon_dependencies["fundamentals_client"].upsert_fundamentals.assert_called_once()
        mock_unified_mysql_daemon_dependencies["queue_broker"].delete_data.assert_called()


class TestUnifiedMySQLDaemonCleanup:
    """Test cleanup operations."""

    def test_cleanup_closes_clients(self, mock_unified_mysql_daemon_dependencies):
        """Test cleanup closes MySQL clients."""
        daemon = UnifiedMySQLDaemon()

        daemon._cleanup()

        mock_unified_mysql_daemon_dependencies["bad_ticker_client"].close.assert_called_once()
        mock_unified_mysql_daemon_dependencies["fundamentals_client"].close.assert_called_once()
        mock_unified_mysql_daemon_dependencies["logger"].info.assert_called()

    def test_cleanup_handles_errors(self, mock_unified_mysql_daemon_dependencies):
        """Test cleanup handles client close errors gracefully."""
        daemon = UnifiedMySQLDaemon()
        mock_unified_mysql_daemon_dependencies["bad_ticker_client"].close.side_effect = Exception("Close error")

        daemon._cleanup()

        # Should still attempt to close fundamentals client
        mock_unified_mysql_daemon_dependencies["fundamentals_client"].close.assert_called_once()
        mock_unified_mysql_daemon_dependencies["logger"].warning.assert_called()

