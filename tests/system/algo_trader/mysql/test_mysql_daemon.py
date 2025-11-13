"""Unit tests for MySQLDaemon - MySQL Queue Processing.

Tests cover initialization, signal handling, queue processing, and cleanup.
All Redis and MySQL operations are mocked. Thread tests use timeouts.
"""

import signal

from system.algo_trader.mysql.mysql_daemon import (
    MySQLDaemon,
)


class TestMySQLDaemonInitialization:
    """Test MySQLDaemon initialization."""

    def test_initialization_success(self, mock_mysql_daemon_dependencies):
        """Test successful daemon initialization."""
        daemon = MySQLDaemon()

        assert daemon.running is False
        assert daemon.queue_broker is not None
        assert daemon.bad_ticker_client is not None
        assert daemon.fundamentals_client is not None
        assert daemon.logger is not None
        # Verify signal handlers registered
        assert mock_mysql_daemon_dependencies["signal"].call_count == 2

    def test_initialization_creates_components(self, mock_mysql_daemon_dependencies):
        """Test initialization creates QueueBroker and MySQL clients."""
        daemon = MySQLDaemon()

        assert daemon.queue_broker is mock_mysql_daemon_dependencies["queue_broker"]
        assert daemon.bad_ticker_client is mock_mysql_daemon_dependencies["bad_ticker_client"]
        assert daemon.fundamentals_client is mock_mysql_daemon_dependencies["fundamentals_client"]


class TestMySQLDaemonSignalHandling:
    """Test signal handling."""

    def test_signal_handler_sets_running_false(self, mock_mysql_daemon_dependencies):
        """Test signal handler stops daemon."""
        daemon = MySQLDaemon()
        daemon.running = True

        daemon._signal_handler(signal.SIGTERM, None)

        assert daemon.running is False
        mock_mysql_daemon_dependencies["logger"].info.assert_called()

    def test_signal_handler_logs_signal_name(self, mock_mysql_daemon_dependencies):
        """Test signal handler logs correct signal name."""
        daemon = MySQLDaemon()

        daemon._signal_handler(signal.SIGINT, None)

        # Verify signal name was logged
        log_calls = mock_mysql_daemon_dependencies["logger"].info.call_args_list
        assert any("SIGINT" in str(call) for call in log_calls)


class TestMySQLDaemonQueueProcessing:
    """Test queue processing operations."""

    def test_process_bad_ticker_queue_empty(self, mock_mysql_daemon_dependencies):
        """Test processing empty bad ticker queue returns early."""
        daemon = MySQLDaemon()
        mock_mysql_daemon_dependencies["queue_broker"].get_queue_size.return_value = 0

        daemon._process_bad_ticker_queue()

        mock_mysql_daemon_dependencies["queue_broker"].dequeue.assert_not_called()

    def test_process_fundamentals_queue_empty(self, mock_mysql_daemon_dependencies):
        """Test processing empty fundamentals queue returns early."""
        daemon = MySQLDaemon()
        mock_mysql_daemon_dependencies["queue_broker"].get_queue_size.return_value = 0

        daemon._process_fundamentals_queue()

        mock_mysql_daemon_dependencies["queue_broker"].dequeue.assert_not_called()

    def test_process_bad_ticker_queue_success(self, mock_mysql_daemon_dependencies):
        """Test successful bad ticker queue processing."""
        daemon = MySQLDaemon()
        daemon.running = True

        mock_mysql_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_mysql_daemon_dependencies["queue_broker"].dequeue.side_effect = ["item1", None]
        mock_mysql_daemon_dependencies["queue_broker"].get_data.return_value = {
            "ticker": "AAPL",
            "timestamp": "2024-01-01T00:00:00",
            "reason": "Invalid",
        }
        mock_mysql_daemon_dependencies["bad_ticker_client"].log_bad_ticker.return_value = True

        daemon._process_bad_ticker_queue()

        mock_mysql_daemon_dependencies["bad_ticker_client"].log_bad_ticker.assert_called_once()
        mock_mysql_daemon_dependencies["queue_broker"].delete_data.assert_called()

    def test_process_fundamentals_queue_success(self, mock_mysql_daemon_dependencies):
        """Test successful fundamentals queue processing."""
        daemon = MySQLDaemon()
        daemon.running = True

        mock_mysql_daemon_dependencies["queue_broker"].get_queue_size.return_value = 1
        mock_mysql_daemon_dependencies["queue_broker"].dequeue.side_effect = ["item1", None]
        mock_mysql_daemon_dependencies["queue_broker"].get_data.return_value = {
            "ticker": "AAPL",
            "sector": "Technology",
            "industry": "Consumer Electronics",
        }
        mock_mysql_daemon_dependencies[
            "fundamentals_client"
        ].upsert_fundamentals.return_value = True

        daemon._process_fundamentals_queue()

        mock_mysql_daemon_dependencies[
            "fundamentals_client"
        ].upsert_fundamentals.assert_called_once()
        mock_mysql_daemon_dependencies["queue_broker"].delete_data.assert_called()


class TestMySQLDaemonCleanup:
    """Test cleanup operations."""

    def test_cleanup_closes_clients(self, mock_mysql_daemon_dependencies):
        """Test cleanup closes MySQL clients."""
        daemon = MySQLDaemon()

        daemon._cleanup()

        mock_mysql_daemon_dependencies["bad_ticker_client"].close.assert_called_once()
        mock_mysql_daemon_dependencies["fundamentals_client"].close.assert_called_once()
        mock_mysql_daemon_dependencies["logger"].info.assert_called()

    def test_cleanup_handles_errors(self, mock_mysql_daemon_dependencies):
        """Test cleanup handles client close errors gracefully."""
        daemon = MySQLDaemon()
        mock_mysql_daemon_dependencies["bad_ticker_client"].close.side_effect = Exception(
            "Close error"
        )

        daemon._cleanup()

        # Should still attempt to close fundamentals client
        mock_mysql_daemon_dependencies["fundamentals_client"].close.assert_called_once()
        mock_mysql_daemon_dependencies["logger"].warning.assert_called()
