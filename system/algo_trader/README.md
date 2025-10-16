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

#### First Run (OAuth2 Authentication Required)

On the **first run**, you will need to complete OAuth2 authentication:

1. The system will display a Schwab authorization URL
2. Visit the URL in your browser and authorize the application
3. After authorization, Schwab redirects to `https://127.0.0.1?code=...`
4. Copy the **full redirect URL** from your browser
5. Paste it when prompted: `Redirect URL:`
6. Tokens will be stored in Redis

**Note:** This interactive authentication is only required:
- On first run (no tokens in Redis)
- Once per month when the refresh token expires (~7 days for Schwab)

#### Subsequent Runs (Automatic)

After initial authentication, the system will:
1. Check Redis for existing access token
2. Use token if valid, or automatically refresh if expired
3. Retrieve historical market data for AAPL
4. Display formatted price history in the console

**Token Management:**
- **Access token**: Expires in ~30 minutes, automatically refreshed
- **Refresh token**: Lasts ~7 days, used to get new access tokens
- Both stored in Redis (access token with TTL, refresh token persistent)

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

