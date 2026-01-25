from abc import ABC, abstractmethod
from typing import Optional

from domain.models import Event


class EventPort(ABC):
    @abstractmethod
    def wait_for_event(self, timeout_s: Optional[float]) -> Optional[Event]:
        ...