from infrastructure.client import Client
from system.algo_trader.config.config import SchwabConfig
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
        self.refresh_token = config.refresh_token
        self.base_url = "https://api.schwabapi.com"

        if not all([self.api_key, self.secret, self.app_name, self.refresh_token]):
            raise ValueError(
                "Missing required Schwab environment variables. "
                "Please set SCHWAB_API_KEY, SCHWAB_SECRET, SCHWAB_APP_NAME, and SCHWAB_REFRESH_TOKEN"
            )
