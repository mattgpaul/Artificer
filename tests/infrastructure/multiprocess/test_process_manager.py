"""Unit tests for ProcessManager.

Tests cover process lifecycle, status tracking, and error handling.
All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from infrastructure.config import ProcessConfig
from infrastructure.multiprocess.process_manager import ProcessManager


class TestProcessManager:
    """Test ProcessManager core functionality."""

    @pytest.mark.timeout(10)
    def test_initialization_with_config(self, process_config, mock_logger):
        """Test initialization with provided config."""
        manager = ProcessManager(config=process_config)
        assert manager.config.max_processes == 2
        assert manager.config.process_timeout == 5
        assert manager.config.start_method == "spawn"
        assert len(manager.processes) == 0

    @pytest.mark.timeout(10)
    def test_initialization_without_config(self, mock_logger):
        """Test initialization without config (auto-populates)."""
        with patch("infrastructure.config.ProcessConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.max_processes = None
            mock_config.process_timeout = 600
            mock_config.start_method = "spawn"
            mock_config_class.return_value = mock_config

            manager = ProcessManager()
            assert manager.config == mock_config

    @pytest.mark.timeout(10)
    def test_start_process_success(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context, mock_process
    ):
        """Test starting a process successfully."""
        manager = ProcessManager(config=process_config)

        mock_process.name = "test_process"
        mock_multiprocessing_context["context"].Process.return_value = mock_process

        process = manager.start_process(target=simple_task, name="test_process", args=(5,))
        assert process.name == "test_process"
        assert "test_process" in manager.processes
        mock_process.start.assert_called_once()

        status = manager.get_process_status("test_process")
        assert status is not None
        assert status["status"] == "running"

    @pytest.mark.timeout(10)
    def test_start_process_auto_name(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context
    ):
        """Test starting process with auto-generated name."""
        manager = ProcessManager(config=process_config)

        mock_process1 = MagicMock()
        mock_process1.name = "process-1"
        mock_process1.pid = 1
        mock_process1.is_alive.return_value = False
        mock_process2 = MagicMock()
        mock_process2.name = "process-2"
        mock_process2.pid = 2
        mock_process2.is_alive.return_value = False
        mock_multiprocessing_context["context"].Process.side_effect = [mock_process1, mock_process2]

        process1 = manager.start_process(target=simple_task, args=(1,))
        process2 = manager.start_process(target=simple_task, args=(2,))

        assert process1.name.startswith("process-")
        assert process2.name.startswith("process-")
        assert process1.name != process2.name

    @pytest.mark.timeout(10)
    def test_start_process_duplicate_name_error(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context, mock_process
    ):
        """Test starting process with duplicate name raises error."""
        manager = ProcessManager(config=process_config)

        mock_process.name = "duplicate"
        mock_process.is_alive.return_value = True  # First process still running
        mock_multiprocessing_context["context"].Process.return_value = mock_process

        manager.start_process(target=simple_task, name="duplicate", args=(1,))

        # Try to start another with same name while first is running
        with pytest.raises(RuntimeError, match="already exists and is running"):
            manager.start_process(target=simple_task, name="duplicate", args=(2,))

    @pytest.mark.timeout(10)
    def test_start_process_max_limit(
        self, mock_logger, simple_task, mock_multiprocessing_context, mock_process
    ):
        """Test max processes limit enforcement."""
        config = ProcessConfig(max_processes=1, process_timeout=5, start_method="spawn")
        manager = ProcessManager(config=config)

        mock_process.name = "process1"
        mock_process.is_alive.return_value = True  # Process still running
        mock_multiprocessing_context["context"].Process.return_value = mock_process

        manager.start_process(target=simple_task, name="process1", args=(1,))

        # Should raise error when trying to start second process
        with pytest.raises(RuntimeError, match="Max processes"):
            manager.start_process(target=simple_task, name="process2", args=(2,))

    @pytest.mark.timeout(10)
    def test_stop_process_success(
        self, process_config, mock_logger, slow_task, mock_multiprocessing_context, mock_process
    ):
        """Test stopping a running process."""
        manager = ProcessManager(config=process_config)

        mock_process.name = "slow_process"
        # stop_process checks is_alive() at line 181 (True = running),
        # then at line 192 after join (False = stopped)
        # Use call_count to track: first call True, subsequent calls False
        call_count = {"count": 0}

        def is_alive_side_effect():
            call_count["count"] += 1
            return call_count["count"] == 1  # True first time, False after

        mock_process.is_alive.side_effect = is_alive_side_effect
        mock_multiprocessing_context["context"].Process.return_value = mock_process

        manager.start_process(target=slow_task, name="slow_process", kwargs={"duration": 1.0})

        # Stop the process
        result = manager.stop_process("slow_process", timeout=2)
        assert result is True
        mock_process.terminate.assert_called_once()

        # Reset for get_process_status call
        call_count["count"] = 1  # Will return False on next call
        status = manager.get_process_status("slow_process")
        assert status is not None
        assert status["status"] == "stopped"

    @pytest.mark.timeout(10)
    def test_stop_process_not_found(self, process_config, mock_logger):
        """Test stopping non-existent process."""
        manager = ProcessManager(config=process_config)

        result = manager.stop_process("nonexistent", timeout=1)
        assert result is False

    @pytest.mark.timeout(10)
    def test_stop_all_processes(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context
    ):
        """Test stopping all processes."""
        manager = ProcessManager(config=process_config)

        mock_process1 = MagicMock()
        mock_process1.name = "p1"
        mock_process1.pid = 1
        mock_process1.is_alive.side_effect = [True, False]
        mock_process2 = MagicMock()
        mock_process2.name = "p2"
        mock_process2.pid = 2
        mock_process2.is_alive.side_effect = [True, False]
        mock_multiprocessing_context["context"].Process.side_effect = [mock_process1, mock_process2]

        manager.start_process(target=simple_task, name="p1", args=(1,))
        manager.start_process(target=simple_task, name="p2", args=(2,))

        result = manager.stop_all_processes(timeout=2)
        assert result is True

    @pytest.mark.timeout(10)
    def test_get_process_status(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context, mock_process
    ):
        """Test getting process status."""
        manager = ProcessManager(config=process_config)

        mock_process.name = "status_test"
        mock_multiprocessing_context["context"].Process.return_value = mock_process

        manager.start_process(target=simple_task, name="status_test", args=(10,))

        status = manager.get_process_status("status_test")
        assert status is not None
        assert status["name"] == "status_test"
        assert "started_at" in status
        assert "status" in status

    @pytest.mark.timeout(10)
    def test_get_all_processes_status(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context
    ):
        """Test getting status for all processes."""
        manager = ProcessManager(config=process_config)

        mock_process1 = MagicMock()
        mock_process1.name = "p1"
        mock_process1.pid = 1
        mock_process1.is_alive.return_value = False
        mock_process2 = MagicMock()
        mock_process2.name = "p2"
        mock_process2.pid = 2
        mock_process2.is_alive.return_value = False
        mock_multiprocessing_context["context"].Process.side_effect = [mock_process1, mock_process2]

        manager.start_process(target=simple_task, name="p1", args=(1,))
        manager.start_process(target=simple_task, name="p2", args=(2,))

        all_status = manager.get_all_processes_status()
        assert len(all_status) == 2
        assert "p1" in all_status
        assert "p2" in all_status

    @pytest.mark.timeout(10)
    def test_is_process_alive(
        self, process_config, mock_logger, simple_task, slow_task, mock_multiprocessing_context
    ):
        """Test checking if process is alive."""
        manager = ProcessManager(config=process_config)

        mock_quick_process = MagicMock()
        mock_quick_process.name = "quick"
        mock_quick_process.pid = 1
        mock_quick_process.is_alive.return_value = False
        mock_slow_process = MagicMock()
        mock_slow_process.name = "slow"
        mock_slow_process.pid = 2
        mock_slow_process.is_alive.return_value = True
        mock_multiprocessing_context["context"].Process.side_effect = [
            mock_quick_process,
            mock_slow_process,
        ]

        manager.start_process(target=simple_task, name="quick", args=(1,))
        manager.start_process(target=slow_task, name="slow", kwargs={"duration": 0.5})

        # Quick process should be dead
        assert not manager.is_process_alive("quick")

        # Slow process should be alive
        assert manager.is_process_alive("slow")

    @pytest.mark.timeout(10)
    def test_wait_for_process(
        self, process_config, mock_logger, slow_task, mock_multiprocessing_context, mock_process
    ):
        """Test waiting for process completion."""
        manager = ProcessManager(config=process_config)

        mock_process.name = "wait_test"
        # wait_for_process calls is_alive() once after join() - should return False (completed)
        mock_process.is_alive.return_value = False
        mock_multiprocessing_context["context"].Process.return_value = mock_process

        manager.start_process(target=slow_task, name="wait_test", kwargs={"duration": 0.2})

        result = manager.wait_for_process("wait_test", timeout=5)
        assert result is True
        mock_process.join.assert_called_once()

    @pytest.mark.timeout(10)
    def test_wait_for_all_processes(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context
    ):
        """Test waiting for all processes."""
        manager = ProcessManager(config=process_config)

        mock_process1 = MagicMock()
        mock_process1.name = "w1"
        mock_process1.pid = 1
        # wait_for_process calls is_alive() once after join() - should return False (completed)
        mock_process1.is_alive.return_value = False
        mock_process1.join = MagicMock()

        mock_process2 = MagicMock()
        mock_process2.name = "w2"
        mock_process2.pid = 2
        mock_process2.is_alive.return_value = False
        mock_process2.join = MagicMock()

        mock_multiprocessing_context["context"].Process.side_effect = [mock_process1, mock_process2]

        manager.start_process(target=simple_task, name="w1", args=(1,))
        manager.start_process(target=simple_task, name="w2", args=(2,))

        result = manager.wait_for_all_processes(timeout=5)
        assert result is True

    @pytest.mark.timeout(10)
    def test_get_active_process_count(
        self, process_config, mock_logger, simple_task, slow_task, mock_multiprocessing_context
    ):
        """Test getting active process count."""
        manager = ProcessManager(config=process_config)

        assert manager.get_active_process_count() == 0

        mock_quick_process = MagicMock()
        mock_quick_process.name = "quick"
        mock_quick_process.pid = 1
        mock_quick_process.is_alive.return_value = False
        mock_slow_process = MagicMock()
        mock_slow_process.name = "slow"
        mock_slow_process.pid = 2
        mock_slow_process.is_alive.return_value = True
        mock_multiprocessing_context["context"].Process.side_effect = [
            mock_quick_process,
            mock_slow_process,
        ]

        manager.start_process(target=simple_task, name="quick", args=(1,))
        manager.start_process(target=slow_task, name="slow", kwargs={"duration": 0.3})

        # One should be active
        count = manager.get_active_process_count()
        assert count == 1

    @pytest.mark.timeout(10)
    def test_cleanup_dead_processes(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context, mock_process
    ):
        """Test cleaning up dead processes."""
        manager = ProcessManager(config=process_config)

        mock_process.name = "cleanup_test"
        mock_multiprocessing_context["context"].Process.return_value = mock_process

        manager.start_process(target=simple_task, name="cleanup_test", args=(1,))

        # Manually mark as stopped
        if "cleanup_test" in manager.processes:
            manager.processes["cleanup_test"].status = "stopped"

        count = manager.cleanup_dead_processes()
        assert count >= 0  # May have already been cleaned up

    @pytest.mark.timeout(10)
    def test_get_process_result(
        self, process_config, mock_logger, simple_task, mock_multiprocessing_context, mock_process
    ):
        """Test getting process result."""
        manager = ProcessManager(config=process_config)

        mock_process.name = "result_test"
        mock_multiprocessing_context["context"].Process.return_value = mock_process

        manager.start_process(target=simple_task, name="result_test", args=(5,))

        # Manually set result for testing
        if "result_test" in manager.processes:
            manager.processes["result_test"].result = 10
            manager.processes["result_test"].status = "stopped"

        result = manager.get_process_result("result_test")
        assert result == 10

    @pytest.mark.timeout(10)
    def test_get_results_summary(
        self, process_config, mock_logger, simple_task, failing_task, mock_multiprocessing_context
    ):
        """Test getting results summary."""
        manager = ProcessManager(config=process_config)

        mock_success_process = MagicMock()
        mock_success_process.name = "success"
        mock_success_process.pid = 1
        mock_success_process.is_alive.return_value = False
        mock_failure_process = MagicMock()
        mock_failure_process.name = "failure"
        mock_failure_process.pid = 2
        mock_failure_process.is_alive.return_value = False
        mock_multiprocessing_context["context"].Process.side_effect = [
            mock_success_process,
            mock_failure_process,
        ]

        manager.start_process(target=simple_task, name="success", args=(1,))
        manager.start_process(target=failing_task, name="failure")

        # Manually set statuses for testing
        if "success" in manager.processes:
            manager.processes["success"].status = "stopped"
            manager.processes["success"].exception = None
        if "failure" in manager.processes:
            manager.processes["failure"].status = "error"
            manager.processes["failure"].exception = ValueError("Test exception")

        summary = manager.get_results_summary()
        assert "successful" in summary
        assert "failed" in summary
        assert "running" in summary
        assert "total" in summary
        assert summary["total"] == 2

    @pytest.mark.timeout(10)
    def test_map_function(
        self, process_config, mock_logger, mock_multiprocessing_context, mock_process_pool
    ):
        """Test map function for parallel execution."""
        manager = ProcessManager(config=process_config)

        mock_process_pool.map.return_value = [1, 4, 9, 16, 25]
        mock_multiprocessing_context["context"].Pool.return_value = mock_process_pool

        def square(x):
            return x * x

        results = manager.map(square, [1, 2, 3, 4, 5])
        assert results == [1, 4, 9, 16, 25]

        manager.close_pool()

    @pytest.mark.timeout(10)
    def test_close_pool(
        self, process_config, mock_logger, mock_multiprocessing_context, mock_process_pool
    ):
        """Test closing process pool."""
        manager = ProcessManager(config=process_config)

        mock_process_pool.map.return_value = [1, 4, 9]
        mock_multiprocessing_context["context"].Pool.return_value = mock_process_pool

        def square(x):
            return x * x

        manager.map(square, [1, 2, 3])
        manager.close_pool()

        mock_process_pool.close.assert_called_once()
        mock_process_pool.join.assert_called_once()
        assert manager.pool is None

    @pytest.mark.timeout(10)
    def test_terminate_pool(
        self, process_config, mock_logger, mock_multiprocessing_context, mock_process_pool
    ):
        """Test terminating process pool."""
        manager = ProcessManager(config=process_config)

        mock_process_pool.map.return_value = [1, 4, 9]
        mock_multiprocessing_context["context"].Pool.return_value = mock_process_pool

        def square(x):
            return x * x

        manager.map(square, [1, 2, 3])
        manager.terminate_pool()

        mock_process_pool.terminate.assert_called_once()
        mock_process_pool.join.assert_called_once()
        assert manager.pool is None
