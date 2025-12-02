from infrastructure.client import Client
from system.algo_trader.config import SchwabConfig
from infrastructure.logging.logger import get_logger

class SchwabBase(Client):
    def __init__(self, config=None):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        if config is None:
            config = SchwabConfig()
        self.api_key = config.api_key
        self.secret = config.secret
        self.app_name = config.app_name
        self.base_url = "https://api.schwabapi.com"

        if not all([self.api_key, self.secret, self.app_name]):
            raise ValueError(
                "Missing required Schwab environment variables. "
                "Please set SCHWAB_API_KEY, SCHWAB_SECRET, and SCHWAB_APP_NAME"
            )
