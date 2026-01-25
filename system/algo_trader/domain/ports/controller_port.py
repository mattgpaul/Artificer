from abc import ABC, abstractmethod
from typing import Optional

from algo_trader.domain.states import ControllerCommand, EngineState


class ControllerPort(ABC):
    @abstractmethod
    def wait_for_command(self, timeout_s: Optional[float]) -> Optional[ControllerCommand]:
        ...

    @abstractmethod
    def publish_status(self, status: EngineState) -> None:
        ...