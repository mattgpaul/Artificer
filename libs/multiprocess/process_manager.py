"""Process manager for lifecycle management and pooling.

This module provides the ProcessManager class for managing process lifecycles,
tracking process status, and providing graceful shutdown capabilities.
"""

from __future__ import annotations

import multiprocessing
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from infrastructure.client import Client
from infrastructure.logging.logger import get_logger


@dataclass
class ProcessStatus:
    """Status information for a managed process.

    Attributes:
        name: Process identifier.
        process: Process object.
        started_at: Timestamp when process was started.
        status: Current status (running, stopped, error).
        exception: Exception if process failed.
        result: Return value from process target function.
    """

    name: str
    process: multiprocessing.Process
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "running"
    exception: BaseException | None = None
    result: Any | None = None


class ProcessManager(Client):
    """Manages process lifecycle, pooling, and monitoring.

    Provides process management capabilities including lifecycle tracking,
    graceful shutdown, status monitoring, and exception handling.

    Attributes:
        logger: Configured logger instance.
        config: Process configuration settings.
        processes: Dictionary of managed processes by name.
        pool: Process pool for parallel execution.
    """

    def __init__(self, config=None):
        """Initialize ProcessManager with configuration.

        Args:
            config: Optional ProcessConfig object. If None, auto-populates from environment.
        """
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)

        if config is None:
            from infrastructure.config import ProcessConfig  # noqa: PLC0415

            config = ProcessConfig()

        self.config = config
        self.processes: dict[str, ProcessStatus] = {}
        self.pool: multiprocessing.Pool | None = None
        self._process_counter = 0

        max_processes = config.max_processes or max(1, multiprocessing.cpu_count() - 2)
        self.logger.info(
            f"ProcessManager initialized "
            f"(max_processes={max_processes}, start_method={config.start_method})"
        )

    def _generate_process_id(self) -> int:
        """Generate unique process ID.

        Returns:
            Unique integer ID for process naming.
        """
        self._process_counter += 1
        return self._process_counter

    def _wrapped_target(
        self, target: Callable, name: str, args: tuple = (), kwargs: dict | None = None
    ):
        """Wrap target function with exception handling, logging, and result capture.

        Args:
            target: Function to execute in process.
            name: Process name.
            args: Positional arguments for target.
            kwargs: Keyword arguments for target.
        """
        kwargs = kwargs or {}
        try:
            self.logger.debug(f"Process '{name}' starting execution")
            result = target(*args, **kwargs)
            self.logger.info(f"Process '{name}' completed successfully")
            if name in self.processes:
                self.processes[name].status = "stopped"
                self.processes[name].result = result
        except BaseException as e:
            self.logger.error(f"Process '{name}' failed with exception: {e}")
            if name in self.processes:
                self.processes[name].status = "error"
                self.processes[name].exception = e

    def start_process(
        self,
        target: Callable,
        name: str | None = None,
        args: tuple = (),
        kwargs: dict | None = None,
    ) -> multiprocessing.Process:
        """Start a new managed process.

        Args:
            target: Function to execute in process.
            name: Optional process name. If None, generates unique name.
            args: Positional arguments for target function.
            kwargs: Keyword arguments for target function.

        Returns:
            Created Process object.

        Raises:
            RuntimeError: If max_processes limit reached or process with same name exists.
        """
        if name is None:
            name = f"process-{self._generate_process_id()}"

        if name in self.processes:
            existing = self.processes[name]
            if existing.status == "running" and existing.process.is_alive():
                raise RuntimeError(f"Process '{name}' already exists and is running")

        max_processes = self.config.max_processes or max(1, multiprocessing.cpu_count() - 2)
        active_count = sum(
            1 for p in self.processes.values() if p.status == "running" and p.process.is_alive()
        )
        if active_count >= max_processes:
            raise RuntimeError(f"Max processes ({max_processes}) limit reached")

        def wrapped_target():
            return self._wrapped_target(target, name, args, kwargs)

        ctx = multiprocessing.get_context(self.config.start_method)
        process = ctx.Process(target=wrapped_target, name=name)

        self.processes[name] = ProcessStatus(name=name, process=process, status="running")

        process.start()
        self.logger.info(f"Started process '{name}' (PID={process.pid})")

        return process

    def stop_process(self, name: str, timeout: int | None = None) -> bool:
        """Stop a specific process by name.

        Args:
            name: Process name to stop.
            timeout: Optional timeout in seconds. Uses config default if None.

        Returns:
            True if process stopped successfully, False otherwise.
        """
        if timeout is None:
            timeout = self.config.process_timeout

        if name not in self.processes:
            self.logger.warning(f"Process '{name}' not found")
            return False

        process_status = self.processes[name]
        process = process_status.process

        if process_status.status != "running" or not process.is_alive():
            self.logger.info(f"Process '{name}' already stopped")
            process_status.status = "stopped"
            return True

        self.logger.info(f"Stopping process '{name}' (timeout={timeout}s)")
        process_status.status = "stopping"

        process.terminate()
        process.join(timeout=timeout)

        if process.is_alive():
            self.logger.warning(f"Process '{name}' did not terminate, forcing kill")
            process.kill()
            process.join()
            process_status.status = "stopped"
            return False
        else:
            process_status.status = "stopped"
            self.logger.info(f"Process '{name}' stopped successfully")
            return True

    def stop_all_processes(self, timeout: int | None = None) -> bool:
        """Stop all managed processes.

        Args:
            timeout: Optional timeout in seconds per process. Uses config default if None.

        Returns:
            True if all processes stopped, False if any failed.
        """
        if timeout is None:
            timeout = self.config.process_timeout

        process_names = [
            name
            for name, status in self.processes.items()
            if status.status == "running" and status.process.is_alive()
        ]

        if not process_names:
            self.logger.info("No running processes to stop")
            return True

        self.logger.info(f"Stopping {len(process_names)} processes")

        results = []
        for name in process_names:
            result = self.stop_process(name, timeout)
            results.append(result)

        all_stopped = all(results)
        if all_stopped:
            self.logger.info(f"All {len(process_names)} processes stopped successfully")
        else:
            failed_count = len([r for r in results if not r])
            self.logger.error(f"Failed to stop {failed_count} of {len(process_names)} processes")

        return all_stopped

    def get_process_status(self, name: str) -> dict | None:
        """Get status information for a specific process.

        Args:
            name: Process name.

        Returns:
            Dictionary with process status information, or None if process not found.
        """
        if name not in self.processes:
            return None

        status = self.processes[name]
        return {
            "name": status.name,
            "alive": status.process.is_alive(),
            "pid": status.process.pid if status.process.is_alive() else None,
            "started_at": status.started_at.isoformat(),
            "status": status.status,
            "exception": str(status.exception) if status.exception else None,
            "result": status.result,
        }

    def get_all_processes_status(self) -> dict[str, dict]:
        """Get status information for all managed processes.

        Returns:
            Dictionary mapping process names to their status information.
        """
        insights = {}
        for name, status in self.processes.items():
            insights[name] = {
                "name": status.name,
                "alive": status.process.is_alive(),
                "pid": status.process.pid if status.process.is_alive() else None,
                "started_at": status.started_at.isoformat(),
                "status": status.status,
                "exception": str(status.exception) if status.exception else None,
                "result": status.result,
            }
        return insights

    def is_process_alive(self, name: str) -> bool:
        """Check if a process is currently running.

        Args:
            name: Process name.

        Returns:
            True if process exists and is alive, False otherwise.
        """
        if name not in self.processes:
            return False
        return self.processes[name].process.is_alive()

    def wait_for_process(self, name: str, timeout: int | None = None) -> bool:
        """Wait for a specific process to complete.

        Args:
            name: Process name to wait for.
            timeout: Optional timeout in seconds. Uses config default if None.

        Returns:
            True if process completed, False if timeout.
        """
        if timeout is None:
            timeout = self.config.process_timeout

        if name not in self.processes:
            self.logger.warning(f"Process '{name}' not found")
            return False

        process = self.processes[name].process

        self.logger.info(f"Waiting for process '{name}' (timeout={timeout}s)")
        process.join(timeout=timeout)

        is_alive = process.is_alive()
        if is_alive:
            self.logger.warning(f"Process '{name}' did not complete within timeout")
        else:
            self.logger.info(f"Process '{name}' completed")

        return not is_alive

    def wait_for_all_processes(self, timeout: int | None = None) -> bool:
        """Wait for all managed processes to complete.

        Args:
            timeout: Optional timeout in seconds per process. Uses config default if None.

        Returns:
            True if all processes completed, False if any timed out.
        """
        if timeout is None:
            timeout = self.config.process_timeout

        process_names = [
            name for name, status in self.processes.items() if status.status == "running"
        ]

        if not process_names:
            self.logger.info("No processes to wait for")
            return True

        self.logger.info(f"Waiting for {len(process_names)} processes")

        results = []
        for name in process_names:
            result = self.wait_for_process(name, timeout)
            results.append(result)

        all_completed = all(results)
        if all_completed:
            self.logger.info(f"All {len(process_names)} processes completed")
        else:
            incomplete_count = len([r for r in results if not r])
            self.logger.error(
                f"{incomplete_count} of {len(process_names)} processes did not complete"
            )

        return all_completed

    def get_active_process_count(self) -> int:
        """Get count of active managed processes.

        Returns:
            Number of processes currently running.
        """
        return sum(1 for status in self.processes.values() if status.process.is_alive())

    def cleanup_dead_processes(self) -> int:
        """Remove dead processes from registry.

        Returns:
            Number of processes removed.
        """
        dead_processes = [
            name
            for name, status in self.processes.items()
            if not status.process.is_alive() and status.status in ("stopped", "error")
        ]

        for name in dead_processes:
            del self.processes[name]

        if dead_processes:
            self.logger.info(f"Cleaned up {len(dead_processes)} dead processes")

        return len(dead_processes)

    def get_process_result(self, name: str) -> Any | None:
        """Get result from a specific process.

        Args:
            name: Process name.

        Returns:
            Result value from process target function, or None if process not found
            or hasn't completed yet.
        """
        if name not in self.processes:
            return None
        return self.processes[name].result

    def get_all_results(self) -> dict[str, Any]:
        """Get results from all processes.

        Returns:
            Dictionary mapping process names to their result values.
            Only includes processes that have completed (stopped or error status).
        """
        results = {}
        for name, status in self.processes.items():
            if status.status in ("stopped", "error"):
                results[name] = status.result
        return results

    def get_results_summary(self) -> dict[str, int]:
        """Get summary of process execution results.

        Returns:
            Dictionary with counts of successful, failed, and running processes:
            - 'successful': Processes that completed without exception
            - 'failed': Processes that raised an exception
            - 'running': Processes still executing
            - 'total': Total number of processes
        """
        successful = sum(
            1
            for status in self.processes.values()
            if status.status == "stopped" and status.exception is None
        )
        failed = sum(1 for status in self.processes.values() if status.status == "error")
        running = sum(1 for status in self.processes.values() if status.status == "running")

        return {
            "successful": successful,
            "failed": failed,
            "running": running,
            "total": len(self.processes),
        }

    def map(self, func: Callable, iterable, chunksize: int | None = None) -> list:
        """Execute function across iterable using process pool.

        Args:
            func: Function to execute.
            iterable: Iterable of arguments for function.
            chunksize: Optional chunk size for batching work.

        Returns:
            List of results from function execution.
        """
        max_processes = self.config.max_processes or max(1, multiprocessing.cpu_count() - 2)

        if self.pool is None:
            ctx = multiprocessing.get_context(self.config.start_method)
            self.pool = ctx.Pool(processes=max_processes)

        try:
            return self.pool.map(func, iterable, chunksize=chunksize)
        except Exception as e:
            self.logger.error(f"Error in process pool map: {e}")
            raise

    def close_pool(self):
        """Close the process pool and wait for completion."""
        if self.pool is not None:
            self.logger.info("Closing process pool")
            self.pool.close()
            self.pool.join()
            self.pool = None

    def terminate_pool(self):
        """Terminate the process pool immediately."""
        if self.pool is not None:
            self.logger.warning("Terminating process pool")
            self.pool.terminate()
            self.pool.join()
            self.pool = None
