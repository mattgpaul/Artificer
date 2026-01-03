"""Shared fixtures for ProcessManager tests."""

import time
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.config import ProcessConfig


@pytest.fixture(autouse=True)
def mock_logger():
    """Auto-mock logger to prevent logging calls."""
    with patch("infrastructure.multiprocess.process_manager.get_logger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


@pytest.fixture
def process_config():
    """Create a ProcessConfig for testing."""
    return ProcessConfig(
        max_processes=2,
        process_timeout=5,
        start_method="spawn",
    )


# Top-level functions for multiprocessing (must be at module level for pickling)
def _simple_task(value):
    """Simple task function for testing."""
    return value * 2


def _failing_task():
    """Task that raises an exception."""
    raise ValueError("Test exception")


def _slow_task(duration=0.1):
    """Task that takes time to complete."""
    time.sleep(duration)
    return "completed"


@pytest.fixture
def simple_task():
    """Simple task function for testing."""
    return _simple_task


@pytest.fixture
def failing_task():
    """Task that raises an exception."""
    return _failing_task


@pytest.fixture
def slow_task():
    """Task that takes time to complete."""
    return _slow_task


@pytest.fixture
def mock_multiprocessing_context():
    """Mock multiprocessing context for testing."""
    with patch("multiprocessing.get_context") as mock_get_context:
        mock_ctx = MagicMock()
        mock_get_context.return_value = mock_ctx
        yield {"get_context": mock_get_context, "context": mock_ctx}


@pytest.fixture
def mock_process():
    """Create a mock process for testing."""
    mock_process = MagicMock()
    mock_process.name = "test_process"
    mock_process.pid = 12345
    mock_process.is_alive.return_value = False
    mock_process.start = MagicMock()
    mock_process.terminate = MagicMock()
    mock_process.join = MagicMock()
    mock_process.kill = MagicMock()
    return mock_process


@pytest.fixture
def mock_process_pool():
    """Create a mock process pool for testing."""
    mock_pool = MagicMock()
    mock_pool.map.return_value = []
    mock_pool.close = MagicMock()
    mock_pool.join = MagicMock()
    mock_pool.terminate = MagicMock()
    return mock_pool
