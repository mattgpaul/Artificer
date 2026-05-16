"""Journal port interface.

Defines the interface for trading journal logging and error reporting.
"""

from abc import ABC, abstractmethod

from system.algo_trader.domain.models import JournalError, JournalInput, JournalOutput


class JournalPort(ABC):
    """Abstract port for trading journal and error logging."""

    @abstractmethod
    def report_input(self, input: JournalInput) -> None:
        """Log journal input data.

        Args:
            input: Journal input containing market and account data.
        """
        ...

    @abstractmethod
    def report_output(self, output: JournalOutput) -> None:
        """Log journal output data.

        Args:
            output: Journal output containing signals and orders.
        """
        ...

    @abstractmethod
    def report_error(self, error: JournalError) -> None:
        """Log engine errors.

        Args:
            error: Journal error containing error details and engine state.
        """
        ...
