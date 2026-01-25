from abc import ABC, abstractmethod

from domain.models import JournalError, JournalInput, JournalOutput


class JournalPort(ABC):
    @abstractmethod
    def report_input(self, input: JournalInput) -> None: ...

    @abstractmethod
    def report_output(self, output: JournalOutput) -> None: ...

    @abstractmethod
    def report_error(self, error: JournalError) -> None: ...