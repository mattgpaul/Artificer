# Algo Trader

An algorithmic trading system for US capital markets that collects company information, tests trading strategies against historical data, and makes trade decisions.

## Current Status

**Phase:** Phase 1 - Schwab API Authentication and Market Data  
**Version:** v0.1.0

## Phase 1: Schwab API Authentication and Market Data

Phase 1 establishes the foundation for interacting with the Schwab API, including authentication, token management, and historical market data retrieval.

### Components

#### System Components
- **`redis_client.py`**: Redis client for storing authentication tokens and ephemeral data
- **`schwab_handler.py`**: Handler for Schwab API interactions, authentication, and market data
- **`main.py`**: Entry point that demonstrates the Phase 1 flow

### Setup

1. **Configure Environment Variables**

   Edit `system/algo_trader/algo_trader.env` with your Schwab API credentials:
   ```bash
   export SCHWAB_API_KEY="your_api_key_here"
   export SCHWAB_SECRET="your_secret_here"
   ```

   Then source it:
   ```bash
   source system/algo_trader/algo_trader.env
   ```

2. **Ensure Redis is Running**
   
   The system requires a Redis instance for token storage:
   ```bash
   redis-server
   ```

### Usage

Run the Phase 1 demo:
```bash
bazel run //system/algo_trader:main
```

This will:
1. Check for existing authentication tokens in Redis
2. Prompt for OAuth2 authentication if no refresh token exists
3. Retrieve historical market data for a sample ticker (AAPL)
4. Display the price history in the console

### Testing

Run unit tests (fast, all mocked):
```bash
bazel test --config=unit //system/algo_trader/...
```

Run integration tests (requires Redis):
```bash
bazel test --config=integration //system/algo_trader/...
```

Run all tests:
```bash
bazel test //system/algo_trader/...
```

### Architecture

**Data Flow:**
1. `main.py` initializes `AlgoTraderRedisClient` and `SchwabHandler`
2. `SchwabHandler` checks Redis for valid access token
3. If no token exists, performs OAuth2 authentication flow
4. Tokens are stored in Redis (access token with TTL, refresh token persistent)
5. `SchwabHandler` uses valid token to request historical market data
6. Data is formatted and displayed to console

**Token Management:**
- Access tokens stored in Redis with 30-minute TTL (ephemeral)
- Refresh tokens stored in Redis without expiration
- Automatic token refresh when access token expires
- API credentials loaded from `algo_trader.env` environment variables
- Infrastructure client properly separated - does NOT manage storage

### Dependencies

**Infrastructure:**
- `//infrastructure/clients:redis_client` - Base Redis client
- `//infrastructure/clients:schwab_client` - Base Schwab API client
- `//infrastructure/logging:logger` - Logging infrastructure

**External:**
- `redis` - Redis Python client
- `requests` - HTTP client for API calls
- `python-dotenv` - Environment variable management

### Phase 1 Completion Criteria

- [x] OAuth2 authentication with Schwab API
- [x] Token storage in Redis
- [x] Automatic token refresh
- [x] Historical market data retrieval
- [x] Console output of market data
- [x] Unit tests with 95%+ coverage
- [x] Integration tests for Redis and API

## Next Phases

See `docs/algo_trader.mdc` for upcoming phases and roadmap.

