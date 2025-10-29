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
