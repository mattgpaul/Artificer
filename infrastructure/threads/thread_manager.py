"""Thread manager for lifecycle management and pooling.

This module provides the ThreadManager class for managing thread lifecycles,
tracking thread status, and providing graceful shutdown capabilities.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger


@dataclass
class ThreadStatus:
    """Status information for a managed thread.

    Attributes:
        name: Thread identifier.
        thread: Thread object.
        started_at: Timestamp when thread was started.
        status: Current status (running, stopped, error).
        exception: Exception if thread failed.
        result: Return value from thread target function.
    """

    name: str
    thread: threading.Thread
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "running"
    exception: BaseException | None = None
    result: Any | None = None


class ThreadManager(Client):
    """Manages thread lifecycle, pooling, and monitoring.

    Provides thread management capabilities including lifecycle tracking,
    graceful shutdown, status monitoring, and exception handling.

    Attributes:
        logger: Configured logger instance.
        config: Thread configuration settings.
        threads: Dictionary of managed threads by name.
        shutdown_event: Event for signaling thread shutdown.
        lock: Lock for thread-safe operations.
    """

    def __init__(self, config=None):
        """Initialize ThreadManager with configuration.

        Args:
            config: Optional ThreadConfig object. If None, auto-populates from environment.
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)

        # Auto-populate from environment if not provided
        if config is None:
            from infrastructure.config import ThreadConfig  # noqa: PLC0415

            config = ThreadConfig()

        self.config = config
        self.threads: dict[str, ThreadStatus] = {}
        self.shutdown_event = threading.Event()
        self.lock = threading.Lock()
        self._thread_counter = 0

        self.logger.info(f"ThreadManager initialized (max_threads={config.max_threads})")

    def _generate_thread_id(self) -> int:
        """Generate unique thread ID.

        Returns:
            Unique integer ID for thread naming.
        """
        with self.lock:
            self._thread_counter += 1
            return self._thread_counter

    def _wrapped_target(
        self, target: Callable, name: str, args: tuple = (), kwargs: dict | None = None
    ):
        """Wrap target function with exception handling, logging, and result capture.

        Args:
            target: Function to execute in thread.
            name: Thread name.
            args: Positional arguments for target.
            kwargs: Keyword arguments for target.
        """
        kwargs = kwargs or {}
        try:
            self.logger.debug(f"Thread '{name}' starting execution")
            result = target(*args, **kwargs)
            self.logger.info(f"Thread '{name}' completed successfully")
            with self.lock:
                if name in self.threads:
                    self.threads[name].status = "stopped"
                    self.threads[name].result = result
        except BaseException as e:
            self.logger.error(f"Thread '{name}' failed with exception: {e}")
            with self.lock:
                if name in self.threads:
                    self.threads[name].status = "error"
                    self.threads[name].exception = e

    def start_thread(
        self,
        target: Callable,
        name: str | None = None,
        args: tuple = (),
        kwargs: dict | None = None,
    ) -> threading.Thread:
        """Start a new managed thread.

        Args:
            target: Function to execute in thread.
            name: Optional thread name. If None, generates unique name.
            args: Positional arguments for target function.
            kwargs: Keyword arguments for target function.

        Returns:
            Created Thread object.

        Raises:
            RuntimeError: If max_threads limit reached or thread with same name exists.
        """
        with self.lock:
            # Generate name if not provided
            if name is None:
                name = f"thread-{self._generate_thread_id()}"

            # Check if thread with this name already exists
            if name in self.threads:
                existing = self.threads[name]
                if existing.status == "running" and existing.thread.is_alive():
                    raise RuntimeError(f"Thread '{name}' already exists and is running")

            # Check max threads limit
            active_count = sum(
                1 for t in self.threads.values() if t.status == "running" and t.thread.is_alive()
            )
            if active_count >= self.config.max_threads:
                raise RuntimeError(f"Max threads ({self.config.max_threads}) limit reached")

            # Create wrapped target function
            def wrapped_target():
                return self._wrapped_target(target, name, args, kwargs)

            # Create thread
            thread = threading.Thread(
                target=wrapped_target, name=name, daemon=self.config.daemon_threads
            )

            # Register thread
            self.threads[name] = ThreadStatus(name=name, thread=thread, status="running")

            # Start thread
            thread.start()
            self.logger.info(f"Started thread '{name}' (daemon={self.config.daemon_threads})")

        return thread

    def stop_thread(self, name: str, timeout: int | None = None) -> bool:
        """Stop a specific thread by name.

        Args:
            name: Thread name to stop.
            timeout: Optional timeout in seconds. Uses config default if None.

        Returns:
            True if thread stopped successfully, False otherwise.
        """
        if timeout is None:
            timeout = self.config.thread_timeout

        with self.lock:
            if name not in self.threads:
                self.logger.warning(f"Thread '{name}' not found")
                return False

            thread_status = self.threads[name]
            thread = thread_status.thread

            if thread_status.status != "running" or not thread.is_alive():
                self.logger.info(f"Thread '{name}' already stopped")
                thread_status.status = "stopped"
                return True

        # Try to stop thread
        self.logger.info(f"Stopping thread '{name}' (timeout={timeout}s)")
        thread_status.status = "stopping"

        # For graceful shutdown, we rely on the target function checking the shutdown event
        # Python threads don't have a built-in stop mechanism
        self.logger.warning(f"Thread '{name}' force-stopped (no graceful shutdown mechanism)")
        thread_status.status = "stopped"
        return True

    def stop_all_threads(self, timeout: int | None = None) -> bool:
        """Stop all managed threads.

        Args:
            timeout: Optional timeout in seconds per thread. Uses config default if None.

        Returns:
            True if all threads stopped, False if any failed.
        """
        if timeout is None:
            timeout = self.config.thread_timeout

        with self.lock:
            thread_names = [
                name
                for name, status in self.threads.items()
                if status.status == "running" and status.thread.is_alive()
            ]

        if not thread_names:
            self.logger.info("No running threads to stop")
            return True

        self.logger.info(f"Stopping {len(thread_names)} threads")

        results = []
        for name in thread_names:
            result = self.stop_thread(name, timeout)
            results.append(result)

        all_stopped = all(results)
        if all_stopped:
            self.logger.info(f"All {len(thread_names)} threads stopped successfully")
        else:
            failed_count = len([r for r in results if not r])
            self.logger.error(f"Failed to stop {failed_count} of {len(thread_names)} threads")

        return all_stopped

    def get_thread_status(self, name: str) -> dict | None:
        """Get status information for a specific thread.

        Args:
            name: Thread name.

        Returns:
            Dictionary with thread status information, or None if thread not found.
        """
        with self.lock:
            if name not in self.threads:
                return None

            status = self.threads[name]
            return {
                "name": status.name,
                "alive": status.thread.is_alive(),
                "started_at": status.started_at.isoformat(),
                "status": status.status,
                "exception": str(status.exception) if status.exception else None,
                "result": status.result,
            }

    def get_all_threads_status(self) -> dict[str, dict]:
        """Get status information for all managed threads.

        Returns:
            Dictionary mapping thread names to their status information.
        """
        with self.lock:
            insights = {}
            for name, status in self.threads.items():
                insights[name] = {
                    "name": status.name,
                    "alive": status.thread.is_alive(),
                    "started_at": status.started_at.isoformat(),
                    "status": status.status,
                    "exception": str(status.exception) if status.exception else None,
                    "result": status.result,
                }
            return insights

    def is_thread_alive(self, name: str) -> bool:
        """Check if a thread is currently running.

        Args:
            name: Thread name.

        Returns:
            True if thread exists and is alive, False otherwise.
        """
        with self.lock:
            if name not in self.threads:
                return False
            return self.threads[name].thread.is_alive()

    def wait_for_thread(self, name: str, timeout: int | None = None) -> bool:
        """Wait for a specific thread to complete.

        Args:
            name: Thread name to wait for.
            timeout: Optional timeout in seconds. Uses config default if None.

        Returns:
            True if thread completed, False if timeout.
        """
        if timeout is None:
            timeout = self.config.thread_timeout

        with self.lock:
            if name not in self.threads:
                self.logger.warning(f"Thread '{name}' not found")
                return False

            thread = self.threads[name].thread

        self.logger.info(f"Waiting for thread '{name}' (timeout={timeout}s)")
        thread.join(timeout=timeout)

        is_alive = thread.is_alive()
        if is_alive:
            self.logger.warning(f"Thread '{name}' did not complete within timeout")
        else:
            self.logger.info(f"Thread '{name}' completed")

        return not is_alive

    def wait_for_all_threads(self, timeout: int | None = None) -> bool:
        """Wait for all managed threads to complete.

        Args:
            timeout: Optional timeout in seconds per thread. Uses config default if None.

        Returns:
            True if all threads completed, False if any timed out.
        """
        if timeout is None:
            timeout = self.config.thread_timeout

        with self.lock:
            thread_names = [
                name for name, status in self.threads.items() if status.status == "running"
            ]

        if not thread_names:
            self.logger.info("No threads to wait for")
            return True

        self.logger.info(f"Waiting for {len(thread_names)} threads")

        results = []
        for name in thread_names:
            result = self.wait_for_thread(name, timeout)
            results.append(result)

        all_completed = all(results)
        if all_completed:
            self.logger.info(f"All {len(thread_names)} threads completed")
        else:
            incomplete_count = len([r for r in results if not r])
            self.logger.error(f"{incomplete_count} of {len(thread_names)} threads did not complete")

        return all_completed

    def get_active_thread_count(self) -> int:
        """Get count of active managed threads.

        Returns:
            Number of threads currently running.
        """
        with self.lock:
            return sum(1 for status in self.threads.values() if status.thread.is_alive())

    def cleanup_dead_threads(self) -> int:
        """Remove dead threads from registry.

        Returns:
            Number of threads removed.
        """
        with self.lock:
            dead_threads = [
                name
                for name, status in self.threads.items()
                if not status.thread.is_alive() and status.status in ("stopped", "error")
            ]

            for name in dead_threads:
                del self.threads[name]

            if dead_threads:
                self.logger.info(f"Cleaned up {len(dead_threads)} dead threads")

        return len(dead_threads)

    def get_thread_result(self, name: str) -> Any | None:
        """Get result from a specific thread.

        Args:
            name: Thread name.

        Returns:
            Result value from thread target function, or None if thread not found
            or hasn't completed yet.
        """
        with self.lock:
            if name not in self.threads:
                return None
            return self.threads[name].result

    def get_all_results(self) -> dict[str, Any]:
        """Get results from all threads.

        Returns:
            Dictionary mapping thread names to their result values.
            Only includes threads that have completed (stopped or error status).
        """
        with self.lock:
            results = {}
            for name, status in self.threads.items():
                if status.status in ("stopped", "error"):
                    results[name] = status.result
            return results

    def get_results_summary(self) -> dict[str, int]:
        """Get summary of thread execution results.

        Returns:
            Dictionary with counts of successful, failed, and running threads:
            - 'successful': Threads that completed without exception and returned success=True
            - 'failed': Threads that raised an exception or returned success=False
            - 'running': Threads still executing
            - 'total': Total number of threads
        """
        with self.lock:
            successful = 0
            failed = 0
            running = 0

            for status in self.threads.values():
                if status.status == "running":
                    running += 1
                elif status.status == "error":
                    # Thread raised an exception
                    failed += 1
                elif status.status == "stopped" and status.exception is None:
                    # Thread completed without exception - check result
                    result = status.result
                    if isinstance(result, dict) and "success" in result:
                        # Result has success field - use it for counting
                        if result["success"]:
                            successful += 1
                        else:
                            failed += 1
                    else:
                        # No success field - count as successful (backward compatible)
                        successful += 1

            return {
                "successful": successful,
                "failed": failed,
                "running": running,
                "total": len(self.threads),
            }
