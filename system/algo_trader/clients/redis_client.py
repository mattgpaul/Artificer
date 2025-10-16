from infrastructure.clients.redis_client import BaseRedisClient


class AlgoTraderRedisClient(BaseRedisClient):
    """
    Redis client for the algo_trader system.
    
    Handles storage of authentication tokens and other ephemeral data
    needed for algorithmic trading operations.
    """
    
    def _get_namespace(self) -> str:
        """
        Define the Redis namespace for algo_trader system.
        
        Returns:
            Namespace string 'algo_trader'
        """
        return "algo_trader"
    
    def store_access_token(self, token: str, ttl: int = 1800) -> bool:
        """
        Store Schwab API access token with TTL.
        
        Arguments:
            token: Access token string
            ttl: Time to live in seconds (default 1800 = 30 minutes)
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.debug(f"Storing access token with TTL: {ttl}s")
        return self.set("schwab_access_token", token, ttl=ttl)
    
    def get_access_token(self) -> str:
        """
        Retrieve Schwab API access token.
        
        Returns:
            Access token string if exists, None otherwise
        """
        self.logger.debug("Retrieving access token")
        return self.get("schwab_access_token")
    
    def store_refresh_token(self, token: str) -> bool:
        """
        Store Schwab API refresh token (no expiration).
        
        Arguments:
            token: Refresh token string
            
        Returns:
            True if successful, False otherwise
        """
        self.logger.debug("Storing refresh token")
        return self.set("schwab_refresh_token", token)
    
    def get_refresh_token(self) -> str:
        """
        Retrieve Schwab API refresh token.
        
        Returns:
            Refresh token string if exists, None otherwise
        """
        self.logger.debug("Retrieving refresh token")
        return self.get("schwab_refresh_token")

