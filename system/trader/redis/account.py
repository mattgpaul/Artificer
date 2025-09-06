from infrastructure.logging.logger import get_logger
from infrastructure.clients.redis_client import BaseRedisClient

class AccountBroker(BaseRedisClient):
    def __init__(self):
        super().__init__()
        self.logger = get_logger(self.__class__.__name__)
        self.namespace = self._get_namespace()

    def _get_namespace(self) -> str:
        return "account"

    def set_refresh_token(self, token) -> bool:
        ttl = 90 * 24 * 60 * 60  # 90 days in seconds
        success = self.set(key="refresh-token", value=token, ttl=ttl)
        return success

    def get_refresh_token(self) -> str:
        token = self.get("refresh-token")
        return token

    def set_access_token(self, token, ttl: int = 30) -> bool:
        success = self.set(self, key="access-token", value=token, ttl=ttl*60)
        return success
        
    def get_access_token(self) -> str:
        token = self.get("access-token")
        return token

