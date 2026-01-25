"""Event port interface.

Defines the interface for event-driven engine control.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.models import Event


class EventPort(ABC):
    """Abstract port for event-driven control flow."""

    @abstractmethod
    def wait_for_event(self, timeout_s: float | None) -> Event | None:
        """Wait for an event from the event source.

        Args:
            timeout_s: Optional timeout in seconds. None means wait indefinitely.

        Returns:
            Event if received, None if timeout or no event.
        """
        ...
