from infrastructure.schwab.schwab import SchwabClient
from infrastructure.logging.logger import get_logger

class AccountHandler(SchwabClient):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        
    # TODO: Implement account handler methods
    pass
