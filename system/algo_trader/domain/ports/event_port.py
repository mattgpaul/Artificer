from abc import ABC, abstractmethod
from typing import Optional

from system.algo_trader.domain.models import Event


class EventPort(ABC):
    @abstractmethod
    def wait_for_event(self, timeout_s: Optional[float]) -> Optional[Event]:
        ...