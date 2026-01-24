from abc import ABC, abstractmethod

from domain.models import Journal


class JournalPort(ABC):
    @abstractmethod
    def report_input(self, input: Journal) -> None: ...

    @abstractmethod
    def report_output(self, output: Journal) -> None: ...

    @abstractmethod
    def report_error(self, error: Journal) -> None: ...