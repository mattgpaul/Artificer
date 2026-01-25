"""Controller port interface.

Defines the interface for engine control and status publishing.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.states import ControllerCommand, EngineState


class ControllerPort(ABC):
    """Abstract port for engine control and status management."""

    @abstractmethod
    def wait_for_command(self, timeout_s: float | None) -> ControllerCommand | None:
        """Wait for a control command from the controller.

        Args:
            timeout_s: Optional timeout in seconds. None means wait indefinitely.

        Returns:
            ControllerCommand if received, None if timeout or no command.
        """
        ...

    @abstractmethod
    def publish_status(self, status: EngineState) -> None:
        """Publish engine status to the controller.

        Args:
            status: Current engine state to publish.
        """
        ...
