<!-- 56a36946-ea2b-4b82-8bfe-d706feb2f404 02e80d50-d888-4c1d-bfd4-3802d69b6f72 -->
# Consolidated Market Data Service CLI

## Goal

Consolidate `LiveMarketService` and `HistoricalMarketService` into a single entry point with subcommand-based service selection, following the existing configuration layer architecture.

## Architecture

Replace individual service binaries with a unified CLI:

```bash
# Before
bazel run //system/algo_trader/service:live_market_service
bazel run //system/algo_trader/service:historical_market_service

# After
bazel run //system/algo_trader/service:market_data -- live [options]
bazel run //system/algo_trader/service:market_data -- historical [options]
bazel run //system/algo_trader/service:market_data -- live health
```

## Implementation Steps

### 1. Reorganize Directory Structure

Create new `/market_data` directory and move service files:

```
system/algo_trader/
├── service/
│   ├── BUILD                   (NEW: defines market_data binary)
│   └── market_data.py          (NEW: unified CLI entry point)
└── market_data/                (NEW: service implementations)
    ├── BUILD
    ├── base.py                 (MOVED from service/market_base.py, remove main())
    ├── live.py                 (MOVED from service/live_market_service.py, remove __main__)
    └── historical.py           (MOVED from service/historical_market_service.py, remove __main__)
```

**Naming Changes**:

- `market_data_service.py` → `market_data.py` (simpler, matches binary name)
- `market_base.py` → `base.py` (shorter, clearer in context of market_data/)
- `live_market_service.py` → `live.py` (concise, clear in market_data/ context)
- `historical_market_service.py` → `historical.py` (concise, clear in market_data/ context)
- Class names remain: `MarketBase`, `LiveMarketService`, `HistoricalMarketService` (public API)

### 2. Create Unified Entry Point

Create `system/algo_trader/service/market_data_service.py` with:

**Argument Structure**:

```python
#!/usr/bin/env python3
"""Unified market data service CLI with subcommand-based service selection."""

import argparse
import sys

from system.algo_trader.market_data.live_market_service import LiveMarketService
from system.algo_trader.market_data.historical_market_service import HistoricalMarketService


def main():
    """Main entry point for market data services."""
    parser = argparse.ArgumentParser(description="Market Data Service")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level"
    )
    
    subparsers = parser.add_subparsers(dest="service", required=True, help="Service to run")
    
    # Live market subcommand
    live_parser = subparsers.add_parser("live", help="Run live market data service")
    live_parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "health"],
        help="Command to execute"
    )
    live_parser.add_argument(
        "--sleep-interval",
        type=int,
        help="Override sleep interval in seconds"
    )
    
    # Historical market subcommand
    historical_parser = subparsers.add_parser("historical", help="Run historical market data service")
    historical_parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "health"],
        help="Command to execute"
    )
    
    args = parser.parse_args()
    
    try:
        # Select service class and configuration
        if args.service == "live":
            service = LiveMarketService(sleep_override=getattr(args, 'sleep_interval', None))
        elif args.service == "historical":
            service = HistoricalMarketService()
        
        # Execute command
        if args.command == "run":
            service.run()
            return 0
        elif args.command == "health":
            if service.health_check():
                service.logger.info("Health check passed")
                return 0
            else:
                service.logger.error("Health check failed")
                return 1
                
    except KeyboardInterrupt:
        print("Service interrupted by user")
        return 0
    except Exception as e:
        print(f"Service failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### 3. Update Service Files

**Remove `MarketBase.main()` method** entirely from `market_base.py` - no longer needed.

**Remove `if __name__ == "__main__"` blocks** from `live_market_service.py` and `historical_market_service.py` - services are now pure classes.

### 4. Update BUILD Files

Create `system/algo_trader/market_data/BUILD`:

```python
load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "market_data_lib",
    srcs = [
        "historical_market_service.py",
        "live_market_service.py",
        "market_base.py",
    ],
    visibility = [
        "//system/algo_trader/service:__pkg__",
        "//tests/system/algo_trader/market_data:__pkg__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader:config",
        "//system/algo_trader/influx:influx_services",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
        "//system/algo_trader/utils:schema",
        requirement("pandas"),
        requirement("pydantic"),
    ],
)
```

Update `system/algo_trader/service/BUILD`:

```python
load("@pip//:requirements.bzl", "requirement")

py_binary(
    name = "market_data",
    srcs = ["market_data_service.py"],
    main = "market_data_service.py",
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__pkg__",
    ],
    deps = ["//system/algo_trader/market_data:market_data_lib"],
)
```

### 5. Create Integration Tests

Create `tests/system/algo_trader/market_data/BUILD`:

```python
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "test_market_data_integration_lib",
    srcs = ["test_market_data_integration.py"],
    deps = [
        "//system/algo_trader/market_data:market_data_lib",
        "@pip//pytest",
        "@pip//pytest-mock",
    ],
)

pytest_test(
    name = "test_market_data_integration",
    size = "small",
    coverage_path = "system.algo_trader.market_data",
    tags = ["integration"],
    test_lib = ":test_market_data_integration_lib",
)
```

Create `tests/system/algo_trader/market_data/test_market_data_integration.py`:

```python
"""Integration tests for market data services with full workflow mocking."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from system.algo_trader.market_data.live_market_service import LiveMarketService
from system.algo_trader.market_data.historical_market_service import HistoricalMarketService


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch("infrastructure.redis.redis.Redis") as mock:
        yield mock.return_value


@pytest.fixture
def mock_influx():
    """Mock InfluxDB client for testing."""
    with patch("infrastructure.influxdb.influxdb.InfluxDBClient") as mock:
        yield mock.return_value


@pytest.fixture
def mock_schwab_api():
    """Mock Schwab API handler for testing."""
    with patch("system.algo_trader.schwab.market_handler.MarketHandler") as mock:
        mock_handler = mock.return_value
        mock_handler.get_quotes.return_value = {
            "AAPL": {"symbol": "AAPL", "lastPrice": 150.0},
            "GOOGL": {"symbol": "GOOGL", "lastPrice": 2800.0}
        }
        mock_handler.get_market_hours.return_value = {
            "start": datetime.now(timezone.utc).isoformat(),
            "end": datetime.now(timezone.utc).isoformat()
        }
        yield mock_handler


class TestLiveMarketServiceIntegration:
    """Integration tests for LiveMarketService full workflow."""
    
    def test_service_initialization(self, mock_redis, mock_schwab_api):
        """Test service initializes all clients correctly."""
        service = LiveMarketService(sleep_override=1)
        
        assert service is not None
        assert service.running is True
        assert service.sleep_override == 1
        assert service.api_handler is not None
        assert service.watchlist_broker is not None
    
    def test_execute_pipeline_full_workflow(self, mock_redis, mock_schwab_api):
        """Test complete pipeline execution with mocked dependencies."""
        service = LiveMarketService(sleep_override=1)
        
        # Mock watchlist
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL", "GOOGL"})
        service.market_broker.set_quotes = Mock(return_value=True)
        
        # Execute pipeline
        result = service._execute_pipeline()
        
        assert result is True
        service.watchlist_broker.get_watchlist.assert_called_once()
        service.api_handler.get_quotes.assert_called_once()
        service.market_broker.set_quotes.assert_called_once()


class TestHistoricalMarketServiceIntegration:
    """Integration tests for HistoricalMarketService full workflow."""
    
    def test_service_initialization(self, mock_redis, mock_influx, mock_schwab_api):
        """Test service initializes all clients correctly."""
        service = HistoricalMarketService()
        
        assert service is not None
        assert service.running is True
        assert service.api_handler is not None
        assert service.watchlist_broker is not None
        assert service.database_handler is not None
    
    def test_execute_pipeline_full_workflow(self, mock_redis, mock_influx, mock_schwab_api):
        """Test complete pipeline execution with mocked dependencies."""
        service = HistoricalMarketService()
        
        # Mock dependencies
        service.watchlist_broker.get_watchlist = Mock(return_value={"AAPL"})
        service.market_broker.get_market_hours = Mock(return_value={
            "start": datetime.now(timezone.utc).isoformat(),
            "end": datetime.now(timezone.utc).isoformat()
        })
        service.api_handler.get_price_history = Mock(return_value={
            "symbol": "AAPL",
            "candles": [{"open": 150.0, "close": 151.0}]
        })
        service.database_handler.write = Mock(return_value=True)
        
        # Execute pipeline
        service._execute_pipeline()
        
        service.watchlist_broker.get_watchlist.assert_called_once()
        service.api_handler.get_price_history.assert_called()
        service.database_handler.write.assert_called()
```

## Usage Examples

```bash
# Run live market service
bazel run //system/algo_trader/service:market_data -- live

# Run with sleep override
bazel run //system/algo_trader/service:market_data -- live --sleep-interval 10

# Run historical market service
bazel run //system/algo_trader/service:market_data -- historical

# Health checks
bazel run //system/algo_trader/service:market_data -- live health
bazel run //system/algo_trader/service:market_data -- historical health

# With custom log level
bazel run //system/algo_trader/service:market_data -- --log-level DEBUG live
```

## Configuration Handling

Per config-layer-plan and microservice-readiness docs:

1. **Default**: Environment variables via Pydantic BaseSettings

   - Services auto-populate config from `REDIS_*`, `INFLUXDB_*`, `SCHWAB_*` env vars
   - No explicit config passing needed

2. **Future Microservice Mode**: Config injection (already supported)

   - Services accept optional `config` parameter
   - No CLI changes needed for Docker deployment

3. **No Config Files**: Not needed - Pydantic handles env var parsing

## Testing

No test changes required:

- Services remain testable as classes with config injection
- Existing unit tests in `tests/system/algo_trader/service/` continue working
- CLI can be tested with subprocess calls if needed

## Files Modified

1. **NEW**: `system/algo_trader/service/market_data_service.py` - Unified CLI entry point
2. **MODIFIED**: `system/algo_trader/service/BUILD` - Add market_data binary, mark old ones deprecated
3. **MODIFIED**: `system/algo_trader/service/market_base.py` - Deprecate `main()` method
4. **MODIFIED**: `system/algo_trader/service/live_market_service.py` - Add deprecation warning to `__main__`
5. **MODIFIED**: `system/algo_trader/service/historical_market_service.py` - Add deprecation warning to `__main__`

## Backward Compatibility

- Individual service binaries remain functional with deprecation warnings
- All existing tests continue working
- Environment variable configuration unchanged
- Service classes unchanged (only entry point consolidated)

## Implementation Status

### ✅ COMPLETED TASKS

- [x] Create market_data.py with subcommand parsing (live/historical) and service dispatching
- [x] Add market_data binary target to BUILD file
- [x] Remove MarketBase.main() method entirely (no deprecation needed)
- [x] Remove __main__ blocks from individual service files (no deprecation needed)
- [x] Test all subcommands and verify functionality
- [x] Create comprehensive integration tests with mocking
- [x] Move service files to new market_data/ directory structure
- [x] Update all BUILD files for new structure
- [x] Fix all test dependencies and mocking issues

### 🔄 CHANGES FROM ORIGINAL PLAN

#### 1. **No Backward Compatibility Maintained**
- **Original Plan**: Keep individual service binaries with deprecation warnings
- **Actual Implementation**: Completely removed individual binaries, no backward compatibility
- **Reason**: User explicitly requested "do not keep backwards compatibility"

#### 2. **File Structure Changes**
- **Original Plan**: Keep files in `service/` directory with deprecation warnings
- **Actual Implementation**: Moved all service files to new `market_data/` directory
- **Files Moved**:
  - `service/market_base.py` → `market_data/base.py`
  - `service/live_market_service.py` → `market_data/live.py`
  - `service/historical_market_service.py` → `market_data/historical.py`

#### 3. **CLI Implementation Changes**
- **Original Plan**: `market_data_service.py` as filename
- **Actual Implementation**: `market_data.py` as filename (matches binary name)
- **Original Plan**: Complex argument structure with `nargs="?"` and `default="run"`
- **Actual Implementation**: Simpler structure with required command argument

#### 4. **Configuration Handling**
- **Original Plan**: Services auto-populate config from environment variables
- **Actual Implementation**: Services accept optional `config` parameter for dependency injection
- **Reason**: Better testability and follows microservice patterns

#### 5. **Testing Strategy**
- **Original Plan**: "No test changes required"
- **Actual Implementation**: Created comprehensive integration tests with full mocking
- **Added**: Complete test suite with Redis, InfluxDB, and Schwab API mocking
- **Added**: Tests for both service initialization and pipeline execution

#### 6. **BUILD File Dependencies**
- **Original Plan**: Generic dependency references like `//system/algo_trader/influx:influx_services`
- **Actual Implementation**: Specific dependency references like `//system/algo_trader/influx:influx_services`
- **Fixed**: Corrected all dependency paths to match actual BUILD file structure

#### 7. **Test Size and Tags**
- **Original Plan**: `size = "small"`
- **Actual Implementation**: `size = "medium"` (as requested by user)
- **Added**: Proper integration test tags and coverage paths

### 🐛 ISSUES RESOLVED DURING IMPLEMENTATION

1. **Bazel Dependency Resolution**
   - **Issue**: `@pip//pytest-mock` not found
   - **Solution**: Used `requirement("pytest-mock")` from pytest_test.bzl

2. **Redis Mocking**
   - **Issue**: `infrastructure.redis.redis.Redis` doesn't exist
   - **Solution**: Mock `redis.Redis` directly from the redis library

3. **InfluxDB Mocking**
   - **Issue**: `influxdb3.InfluxDBClient` not found
   - **Solution**: Mock `influxdb_client_3.InfluxDBClient3` (correct module)

4. **Environment Variable Dependencies**
   - **Issue**: Services trying to load real Schwab API credentials
   - **Solution**: Mock all internal client instantiations in tests

5. **Pydantic Schema Validation**
   - **Issue**: `MarketHours` schema missing required `date` field
   - **Solution**: Updated mock data to include all required fields

### 📁 FINAL FILE STRUCTURE

```
system/algo_trader/
├── service/
│   ├── BUILD                   (UPDATED: defines market_data binary)
│   └── market_data.py          (NEW: unified CLI entry point)
└── market_data/                (NEW: service implementations)
    ├── BUILD                   (NEW: market_data_lib)
    ├── base.py                 (MOVED: MarketBase class)
    ├── live.py                 (MOVED: LiveMarketService class)
    └── historical.py           (MOVED: HistoricalMarketService class)

tests/system/algo_trader/market_data/
├── BUILD                       (NEW: integration test target)
└── test_market_data_integration.py (NEW: comprehensive integration tests)
```

### 🎯 FINAL USAGE

```bash
# Run live market service
bazel run //system/algo_trader/service:market_data -- live run

# Run with sleep override
bazel run //system/algo_trader/service:market_data -- live run --sleep-interval 10

# Run historical market service
bazel run //system/algo_trader/service:market_data -- historical run

# Health checks
bazel run //system/algo_trader/service:market_data -- live health
bazel run //system/algo_trader/service:market_data -- historical health

# With custom log level
bazel run //system/algo_trader/service:market_data -- --log-level DEBUG live run
```

### ✅ VERIFICATION COMPLETED

- [x] All integration tests pass
- [x] CLI subcommands work correctly
- [x] Help messages display properly
- [x] Error handling works (no subcommand provided)
- [x] Service initialization works with mocked dependencies
- [x] Pipeline execution works with mocked dependencies
- [x] All BUILD files compile successfully
- [x] No backward compatibility maintained (as requested)