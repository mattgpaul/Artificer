"""Minimal tests for ThreadManager."""

import threading
import time

import pytest

from infrastructure.config import ThreadConfig
from infrastructure.threads.thread_manager import ThreadManager


def dummy_task(event=None):
    """Simple task that can be synchronized with an event."""
    if event:
        event.wait(timeout=1.0)
    return True


class TestThreadManagerBasic:
    """Basic tests for ThreadManager."""

    def test_initialization(self):
        """Test basic initialization."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        assert manager.config.max_threads == 5
        assert manager.config.daemon_threads is True

    def test_start_single_thread(self):
        """Test starting a single thread that completes immediately."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        # Use event to ensure thread completes
        event = threading.Event()
        event.set()  # Immediate completion

        thread = manager.start_thread(
            target=dummy_task, name="test_thread", kwargs={"event": event}
        )
        thread.join(timeout=2.0)

        assert thread.name == "test_thread"
        # Allow status to update
        time.sleep(0.1)
        assert manager.get_active_thread_count() == 0

    def test_start_multiple_threads(self):
        """Test starting multiple threads that complete immediately."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        threads = []
        for i in range(3):
            event = threading.Event()
            event.set()  # Immediate completion
            thread = manager.start_thread(
                target=dummy_task, name=f"thread_{i}", kwargs={"event": event}
            )
            threads.append(thread)

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=2.0)

        # Allow status to update
        time.sleep(0.1)
        assert manager.get_active_thread_count() == 0


class TestThreadStatus:
    """Test thread status tracking and monitoring."""

    def test_get_thread_status(self):
        """Test getting status of a thread."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        event = threading.Event()
        event.set()
        thread = manager.start_thread(
            target=dummy_task, name="status_test", kwargs={"event": event}
        )
        thread.join(timeout=2.0)

        time.sleep(0.1)
        status = manager.get_thread_status("status_test")

        assert status is not None
        assert status["name"] == "status_test"
        assert status["alive"] is False

    def test_get_thread_status_nonexistent(self):
        """Test getting status of nonexistent thread."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        status = manager.get_thread_status("nonexistent")

        assert status is None

    def test_get_all_threads_status(self):
        """Test getting status of all threads."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        threads = []
        for i in range(3):
            event = threading.Event()
            event.set()
            thread = manager.start_thread(
                target=dummy_task, name=f"thread_{i}", kwargs={"event": event}
            )
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=2.0)

        time.sleep(0.1)
        all_status = manager.get_all_threads_status()

        assert len(all_status) == 3
        assert "thread_0" in all_status
        assert "thread_1" in all_status
        assert "thread_2" in all_status


def failing_task():
    """Task that raises an exception."""
    raise ValueError("Test exception")


def task_returning_success():
    """Task that returns a success dict."""
    return {"success": True, "data": "some data"}


def task_returning_failure():
    """Task that returns a failure dict."""
    return {"success": False, "error": "something went wrong"}


class TestThreadExceptionHandling:
    """Test exception handling in threads."""

    def test_thread_exception_capture(self):
        """Test that thread exceptions are captured."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        thread = manager.start_thread(target=failing_task, name="failing_thread")
        thread.join(timeout=2.0)
        time.sleep(0.1)

        status = manager.get_thread_status("failing_thread")

        assert status is not None
        assert status["status"] == "error"
        assert status["exception"] is not None
        assert "Test exception" in status["exception"]


class TestThreadCleanup:
    """Test thread cleanup operations."""

    def test_cleanup_dead_threads(self):
        """Test cleanup of dead threads."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        threads = []
        for i in range(3):
            event = threading.Event()
            event.set()
            thread = manager.start_thread(
                target=dummy_task, name=f"thread_{i}", kwargs={"event": event}
            )
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=2.0)

        time.sleep(0.1)
        removed_count = manager.cleanup_dead_threads()

        assert removed_count == 3
        assert len(manager.get_all_threads_status()) == 0


class TestThreadLimits:
    """Test thread limit enforcement."""

    def test_duplicate_thread_name(self):
        """Test handling of duplicate thread names."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        # First thread with event that doesn't complete immediately
        event1 = threading.Event()
        thread1 = manager.start_thread(
            target=dummy_task, name="duplicate", kwargs={"event": event1}
        )

        # Try to start another thread with same name (should fail)
        with pytest.raises(RuntimeError, match="already exists"):
            manager.start_thread(
                target=dummy_task, name="duplicate", kwargs={"event": threading.Event()}
            )

        # Complete the first thread
        event1.set()
        thread1.join(timeout=2.0)

        time.sleep(0.1)
        # Now we can use the name again
        event2 = threading.Event()
        event2.set()
        thread2 = manager.start_thread(
            target=dummy_task, name="duplicate", kwargs={"event": event2}
        )
        thread2.join(timeout=2.0)


def task_with_return_value(value):
    """Task that returns a value."""
    return value * 2


def task_with_dict_return():
    """Task that returns a dictionary."""
    return {"status": "success", "count": 42}


class TestThreadResultTracking:
    """Test result tracking features."""

    def test_get_thread_result_success(self):
        """Test getting result from successful thread."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        thread = manager.start_thread(target=task_with_return_value, name="result_test", args=(10,))
        thread.join(timeout=2.0)
        time.sleep(0.1)

        result = manager.get_thread_result("result_test")
        assert result == 20

    def test_get_thread_result_nonexistent(self):
        """Test getting result from nonexistent thread."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        result = manager.get_thread_result("nonexistent")
        assert result is None

    def test_get_thread_result_complex_return(self):
        """Test getting complex return value from thread."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        thread = manager.start_thread(target=task_with_dict_return, name="dict_test")
        thread.join(timeout=2.0)
        time.sleep(0.1)

        result = manager.get_thread_result("dict_test")
        assert result == {"status": "success", "count": 42}

    def test_get_all_results(self):
        """Test getting results from all threads."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        threads = []
        for i in range(3):
            thread = manager.start_thread(
                target=task_with_return_value, name=f"thread_{i}", args=(i,)
            )
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=2.0)

        time.sleep(0.1)
        results = manager.get_all_results()

        assert len(results) == 3
        assert results["thread_0"] == 0
        assert results["thread_1"] == 2
        assert results["thread_2"] == 4

    def test_get_results_summary_all_successful(self):
        """Test results summary with all successful threads."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        threads = []
        for i in range(3):
            event = threading.Event()
            event.set()
            thread = manager.start_thread(
                target=dummy_task, name=f"thread_{i}", kwargs={"event": event}
            )
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=2.0)

        time.sleep(0.1)
        summary = manager.get_results_summary()

        assert summary["successful"] == 3
        assert summary["failed"] == 0
        assert summary["running"] == 0
        assert summary["total"] == 3

    def test_get_results_summary_with_failures(self):
        """Test results summary with successful and failed threads."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        # Start successful thread
        event = threading.Event()
        event.set()
        thread1 = manager.start_thread(target=dummy_task, name="success", kwargs={"event": event})

        # Start failing thread
        thread2 = manager.start_thread(target=failing_task, name="failure")

        thread1.join(timeout=2.0)
        thread2.join(timeout=2.0)
        time.sleep(0.1)

        summary = manager.get_results_summary()

        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert summary["running"] == 0
        assert summary["total"] == 2

    def test_get_thread_status_includes_result(self):
        """Test that get_thread_status includes result field."""
        config = ThreadConfig(daemon_threads=True, max_threads=5, thread_timeout=2)
        manager = ThreadManager(config=config)

        thread = manager.start_thread(target=task_with_return_value, name="status_test", args=(5,))
        thread.join(timeout=2.0)
        time.sleep(0.1)

        status = manager.get_thread_status("status_test")

        assert status is not None
        assert "result" in status
        assert status["result"] == 10

    def test_get_all_threads_status_includes_results(self):
        """Test that get_all_threads_status includes result fields."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        threads = []
        for i in range(2):
            thread = manager.start_thread(
                target=task_with_return_value, name=f"thread_{i}", args=(i,)
            )
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=2.0)

        time.sleep(0.1)
        all_status = manager.get_all_threads_status()

        assert len(all_status) == 2
        assert "result" in all_status["thread_0"]
        assert all_status["thread_0"]["result"] == 0
        assert "result" in all_status["thread_1"]
        assert all_status["thread_1"]["result"] == 2


class TestThreadResultBasedCounting:
    """Test result-based success/failure counting in get_results_summary."""

    def test_summary_with_success_dict_results(self):
        """Test that threads returning {"success": True} are counted as successful."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        threads = []
        for i in range(3):
            thread = manager.start_thread(target=task_returning_success, name=f"success_thread_{i}")
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=2.0)

        time.sleep(0.1)
        summary = manager.get_results_summary()

        assert summary["successful"] == 3
        assert summary["failed"] == 0
        assert summary["running"] == 0
        assert summary["total"] == 3

    def test_summary_with_failure_dict_results(self):
        """Test that threads returning {"success": False} are counted as failed."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        threads = []
        for i in range(3):
            thread = manager.start_thread(target=task_returning_failure, name=f"failure_thread_{i}")
            threads.append(thread)

        for thread in threads:
            thread.join(timeout=2.0)

        time.sleep(0.1)
        summary = manager.get_results_summary()

        assert summary["successful"] == 0
        assert summary["failed"] == 3
        assert summary["running"] == 0
        assert summary["total"] == 3

    def test_summary_with_mixed_dict_results(self):
        """Test summary with mix of success and failure dict results."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        # 2 successful
        for i in range(2):
            manager.start_thread(target=task_returning_success, name=f"success_{i}")

        # 2 failed
        for i in range(2):
            manager.start_thread(target=task_returning_failure, name=f"failure_{i}")

        # 1 exception
        manager.start_thread(target=failing_task, name="exception")

        time.sleep(0.5)
        summary = manager.get_results_summary()

        assert summary["successful"] == 2
        assert summary["failed"] == 3  # 2 from dict results + 1 from exception
        assert summary["running"] == 0
        assert summary["total"] == 5

    def test_backward_compatibility_non_dict_results(self):
        """Test that non-dict return values are still counted as successful (backward compat)."""
        config = ThreadConfig(daemon_threads=True, max_threads=10, thread_timeout=2)
        manager = ThreadManager(config=config)

        # Task returning True (not a dict)
        event = threading.Event()
        event.set()
        thread1 = manager.start_thread(target=dummy_task, name="bool_task", kwargs={"event": event})

        # Task returning an integer (not a dict)
        thread2 = manager.start_thread(target=task_with_return_value, name="int_task", args=(5,))

        thread1.join(timeout=2.0)
        thread2.join(timeout=2.0)
        time.sleep(0.1)

        summary = manager.get_results_summary()

        # Both should be counted as successful (backward compatibility)
        assert summary["successful"] == 2
        assert summary["failed"] == 0
        assert summary["total"] == 2
