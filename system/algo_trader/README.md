# Algo Trader

An algorithmic trading system for US capital markets that collects company information, tests trading strategies against historical data, and makes trade decisions.

## Current Status

**Phase:** Phase 4 - Grafana Visualization  
**Version:** v0.4.0

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

2. **Start Required Services**

   The system requires Redis, InfluxDB, and Grafana.

   **Start Redis:**
   ```bash
   redis-server
   ```

   **Start InfluxDB:**
   ```bash
   # InfluxDB should be running on localhost:8086
   # Configuration is in artificer.env
   ```

   **Start Grafana:**
   
   Option 1 - Using Bazel (recommended):
   ```bash
   bazel run //system/algo_trader/clients:grafana
   ```

   Option 2 - Using convenience script:
   ```bash
   ./scripts/grafana.sh start
   ```

   Option 3 - Using docker-compose directly:
   ```bash
   docker-compose up -d grafana
   ```

   **Grafana Commands (Bazel):**
   ```bash
   # Start (default)
   bazel run //system/algo_trader/clients:grafana
   
   # Stop
   bazel run //system/algo_trader/clients:grafana stop
   
   # Restart
   bazel run //system/algo_trader/clients:grafana restart
   
   # Status
   bazel run //system/algo_trader/clients:grafana status
   
   # Logs
   bazel run //system/algo_trader/clients:grafana logs
   ```

   **Access Grafana:**
   - URL: http://localhost:3000
   - Authentication: **DISABLED** (no login required for localhost)
   - Opens directly to dashboards

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

**Prerequisites:** 
- Unit tests: No services required (all mocked)
- Integration tests: Requires Redis, InfluxDB, and Grafana running

Run unit tests (fast, all mocked):
```bash
bazel test --config=unit //system/algo_trader/...
```

Run integration tests (requires services):
```bash
# Ensure services are running first
redis-server &
# InfluxDB should be running
bazel run //system/algo_trader/clients:grafana start

# Run integration tests
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
- `//infrastructure/clients:influxdb_client` - Base InfluxDB client
- `//infrastructure/clients:grafana_client` - Base Grafana client
- `//infrastructure/logging:logger` - Logging infrastructure

**External Services:**
- **Redis** (localhost:6379) - Token storage and ephemeral data
- **InfluxDB** (localhost:8086) - Time-series market data storage
- **Grafana** (localhost:3000) - Visualization dashboard (Docker)

**External Python Packages:**
- `redis` - Redis Python client
- `requests` - HTTP client for API calls
- `influxdb3-python` - InfluxDB 3.0 client
- `python-dotenv` - Environment variable management

### Phase 1 Completion Criteria

- [x] OAuth2 authentication with Schwab API
- [x] Token storage in Redis
- [x] Automatic token refresh
- [x] Historical market data retrieval
- [x] Console output of market data
- [x] Unit tests with 95%+ coverage
- [x] Integration tests for Redis and API

## Docker + Bazel Hybrid Approach

This project uses a **hybrid approach** for managing services:

- **Bazel**: Builds, tests, and runs the application code
- **Docker Compose**: Manages external service dependencies (Grafana)
- **Manual**: Redis and InfluxDB run directly on host (for now)

### Why This Approach?

1. **Separation of Concerns**: Bazel's hermetic builds conflict with Docker's non-hermetic nature
2. **Industry Standard**: Used at Google, Uber, and other companies that use both Bazel and Docker
3. **rules_docker Deprecated**: The old Bazel Docker rules don't work with modern Bazel (bzlmod)
4. **Flexibility**: Easy to add more services to docker-compose.yml

### Grafana in Docker (POC)

Grafana runs in Docker as a proof-of-concept demonstrating the hybrid Bazel + Docker approach:

**Architecture:**
- **Infrastructure Layer**: `BaseGrafanaClient` in `infrastructure/clients/grafana_client.py`
  - Provides reusable container lifecycle methods (`start_via_compose`, `stop_via_compose`, etc.)
  - Generic, works for any system that needs Grafana
- **System Client Layer**: `system/algo_trader/clients/grafana_client.py`
  - `AlgoTraderGrafanaClient` extends BaseGrafanaClient
  - Loads dashboard JSON files from `grafana/` directory
  - Configures InfluxDB datasource for market data
  - Includes integrated CLI interface
  - Entry point: `bazel run //system/algo_trader/clients:grafana`
- **Data Layer**: `system/algo_trader/grafana/`
  - Dashboard definitions as `.json` files
  - Loaded dynamically by the client at runtime
  - Easy to add/modify dashboards without code changes

**Configuration:**
- **Container**: Managed via `docker-compose.yml` at repository root
- **Dashboards**: JSON files in `system/algo_trader/grafana/` directory
- **Datasources**: InfluxDB connection configured for market data
- **Security**: Authentication disabled for localhost development
- **Network**: Standard Docker networking with host.docker.internal for InfluxDB access

**Why This Architecture?**
- Container management logic is reusable across systems (infrastructure)
- System-specific Python logic in clients layer
- Dashboard data separated as JSON files (configuration as data)
- Other systems can extend `BaseGrafanaClient` with their own dashboards
- Follows repository's component < infrastructure < system hierarchy

If this works well, Redis and InfluxDB may be migrated to Docker Compose in the future.

## Phase History

### Phase 4: Grafana Visualization (Current)
- [x] InfluxDB integration for time-series data
- [x] Market data storage (multiple timeframes)
- [x] Grafana dashboard setup
- [x] Docker Compose integration (Grafana POC)

### Phase 1: Schwab API Authentication and Market Data
- [x] OAuth2 authentication with Schwab API
- [x] Token storage in Redis
- [x] Automatic token refresh
- [x] Historical market data retrieval
- [x] Console output of market data
- [x] Unit tests with 95%+ coverage
- [x] Integration tests for Redis and API

## Next Phases

See `docs/algo_trader.mdc` for upcoming phases and roadmap.

