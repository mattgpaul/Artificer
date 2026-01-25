from abc import ABC, abstractmethod

from system.algo_trader.domain.models import Account, Positions


class AccountPort(ABC):
    @abstractmethod
    def get_account(self) -> Account: ...

    @abstractmethod
    def get_positions(self) -> Positions: ...
