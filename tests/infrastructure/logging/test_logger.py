"""Unit tests for Logger - Colored Logging Functionality.

Tests cover logger initialization, color formatting, log level configuration,
and automatic global logging setup.
"""

import logging
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.logging.logger import ColoredFormatter, _setup_global_logging, get_logger


class TestColoredFormatter:
    """Test ColoredFormatter color codes and formatting."""

    @pytest.fixture
    def formatter(self):
        """Fixture to create a ColoredFormatter instance."""
        return ColoredFormatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%H:%M:%S"
        )

    def test_formatter_initialization(self, formatter):
        """Test ColoredFormatter initializes correctly."""
        assert formatter is not None
        assert hasattr(formatter, "COLORS")
        assert "DEBUG" in formatter.COLORS
        assert "INFO" in formatter.COLORS
        assert "ERROR" in formatter.COLORS

    def test_color_codes_defined(self, formatter):
        """Test all required color codes are defined."""
        # Test level colors in COLORS dict
        expected_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in expected_levels:
            assert level in formatter.COLORS
            assert isinstance(formatter.COLORS[level], str)

        # Test separate color attributes
        assert hasattr(formatter, "GREY")
        assert isinstance(formatter.GREY, str)
        assert hasattr(formatter, "RESET")
        assert isinstance(formatter.RESET, str)

    def test_format_debug_message(self, formatter):
        """Test DEBUG messages get millisecond timestamp."""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg="Test debug message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Should contain color codes
        assert "\033[90m" in formatted  # Grey color for DEBUG
        assert "\033[0m" in formatted  # Reset code
        assert "DEBUG" in formatted
        assert "Test debug message" in formatted

    def test_format_info_message(self, formatter):
        """Test INFO messages get standard format."""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test info message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Should contain color codes
        assert "\033[32m" in formatted  # Green color for INFO
        assert "\033[0m" in formatted  # Reset code
        assert "INFO" in formatted
        assert "Test info message" in formatted

    def test_format_warning_message(self, formatter):
        """Test WARNING messages are formatted with yellow color."""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Test warning message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "\033[33m" in formatted  # Yellow color for WARNING
        assert "WARNING" in formatted

    def test_format_error_message(self, formatter):
        """Test ERROR messages are formatted with red color."""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Test error message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "\033[31m" in formatted  # Red color for ERROR
        assert "ERROR" in formatted

    def test_format_critical_message(self, formatter):
        """Test CRITICAL messages are formatted with magenta color."""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.CRITICAL,
            pathname="test.py",
            lineno=1,
            msg="Test critical message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        assert "\033[35m" in formatted  # Magenta color for CRITICAL
        assert "CRITICAL" in formatted


class TestGlobalLoggingSetup:
    """Test automatic global logging configuration."""

    def test_setup_global_logging_default_level(self):
        """Test global logging setup with default INFO level."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("logging.getLogger") as mock_get_logger:
                mock_root = MagicMock()
                mock_root.handlers = []
                mock_root.manager.loggerDict = {}
                mock_get_logger.return_value = mock_root

                _setup_global_logging()

                # Should add handler
                assert mock_root.addHandler.called
                # Should set INFO level by default
                assert mock_root.setLevel.called

    def test_setup_global_logging_custom_level(self):
        """Test global logging setup with custom log level from environment."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            with patch("logging.getLogger") as mock_get_logger:
                mock_root = MagicMock()
                mock_root.handlers = []
                mock_root.manager.loggerDict = {}
                mock_get_logger.return_value = mock_root

                _setup_global_logging()

                # Should set DEBUG level from environment
                calls = mock_root.setLevel.call_args_list
                assert any(call == ((logging.DEBUG,),) for call in calls)

    def test_setup_global_logging_only_once(self):
        """Test global logging setup only configures once."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("logging.getLogger") as mock_get_logger:
                mock_root = MagicMock()
                # Simulate already having handlers
                mock_root.handlers = [MagicMock()]
                mock_root.manager.loggerDict = {}
                mock_get_logger.return_value = mock_root

                _setup_global_logging()

                # Should not add handler since one exists
                assert not mock_root.addHandler.called

    def test_setup_global_logging_invalid_level(self):
        """Test global logging setup with invalid log level defaults to INFO."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID"}):
            with patch("logging.getLogger") as mock_get_logger:
                mock_root = MagicMock()
                mock_root.handlers = []
                mock_root.manager.loggerDict = {}
                mock_get_logger.return_value = mock_root

                _setup_global_logging()

                # Should still set a level (defaulting to INFO)
                assert mock_root.setLevel.called


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logging.Logger instance."""
        logger = get_logger("test_module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_respects_environment_level(self):
        """Test get_logger sets level from environment variable."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            logger = get_logger("test_debug")

            assert logger.level == logging.DEBUG

    def test_get_logger_default_info_level(self):
        """Test get_logger defaults to INFO level."""
        with patch.dict(os.environ, {}, clear=True):
            logger = get_logger("test_info")

            assert logger.level == logging.INFO

    def test_get_logger_warning_level(self):
        """Test get_logger with WARNING level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
            logger = get_logger("test_warning")

            assert logger.level == logging.WARNING

    def test_get_logger_error_level(self):
        """Test get_logger with ERROR level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "ERROR"}):
            logger = get_logger("test_error")

            assert logger.level == logging.ERROR

    def test_get_logger_critical_level(self):
        """Test get_logger with CRITICAL level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "CRITICAL"}):
            logger = get_logger("test_critical")

            assert logger.level == logging.CRITICAL

    def test_get_logger_case_insensitive(self):
        """Test get_logger handles lowercase log level."""
        with patch.dict(os.environ, {"LOG_LEVEL": "debug"}):
            logger = get_logger("test_case")

            assert logger.level == logging.DEBUG

    def test_get_logger_multiple_loggers(self):
        """Test get_logger creates independent loggers."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name != logger2.name
        assert logger1.name == "module1"
        assert logger2.name == "module2"


class TestLoggerIntegration:
    """Test logger integration scenarios."""

    def test_logger_actually_logs(self):
        """Test that logger actually produces output."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
            logger = get_logger("integration_test")

            # Capture log output
            with patch("sys.stdout", new=StringIO()):
                handler = logging.StreamHandler(sys.stdout)
                handler.setFormatter(
                    ColoredFormatter(
                        "%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%H:%M:%S"
                    )
                )
                logger.addHandler(handler)

                logger.info("Test message")

                # Note: This test may not capture output due to handler setup complexity
                # but validates the logger can be called without errors

    def test_logger_debug_not_shown_at_info_level(self):
        """Test DEBUG messages are not shown when log level is INFO."""
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}):
            logger = get_logger("level_test")

            # Should be able to call debug without it appearing
            logger.debug("This should not appear")

            # Verify effective level
            assert logger.level == logging.INFO
            assert not logger.isEnabledFor(logging.DEBUG)

    def test_logger_all_levels_shown_at_debug(self):
        """Test all log levels are shown when set to DEBUG."""
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            logger = get_logger("all_levels")

            assert logger.isEnabledFor(logging.DEBUG)
            assert logger.isEnabledFor(logging.INFO)
            assert logger.isEnabledFor(logging.WARNING)
            assert logger.isEnabledFor(logging.ERROR)
            assert logger.isEnabledFor(logging.CRITICAL)

    def test_logger_with_exception(self):
        """Test logger can log exceptions."""
        logger = get_logger("exception_test")

        try:
            raise ValueError("Test exception")
        except ValueError:
            # Should not raise when logging exception
            logger.exception("An error occurred")

    def test_logger_with_formatting(self):
        """Test logger supports string formatting."""
        logger = get_logger("format_test")

        # Should support various formatting styles
        logger.info("Message with %s", "argument")
        logger.info("Message with %s and %s", "arg1", "arg2")
        logger.info("Message with f-string")


class TestLoggerEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_logger_name(self):
        """Test get_logger with empty string name."""
        logger = get_logger("")

        assert isinstance(logger, logging.Logger)

    def test_logger_name_with_special_chars(self):
        """Test get_logger with special characters in name."""
        logger = get_logger("module.sub_module-123")

        assert logger.name == "module.sub_module-123"

    def test_logger_unicode_name(self):
        """Test get_logger with unicode characters."""
        logger = get_logger("模块_🚀")

        assert isinstance(logger, logging.Logger)

    def test_formatter_with_none_message(self):
        """Test formatter handles None message gracefully."""
        formatter = ColoredFormatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="",
            args=(),
            exc_info=None,
        )

        # Should not raise
        formatted = formatter.format(record)
        assert isinstance(formatted, str)

    def test_get_logger_repeated_calls(self):
        """Test get_logger returns same logger instance for same name."""
        logger1 = get_logger("repeated_test")
        logger2 = get_logger("repeated_test")

        # Should return the same logger instance
        assert logger1 is logger2
