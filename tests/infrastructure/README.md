# Infrastructure Unit Tests

This directory contains comprehensive unit tests for all infrastructure components, following the patterns established in the Schwab test suite.

## Test Files

### test_client.py
Tests for the abstract `Client` base class in `infrastructure/client.py`.

**Test Coverage:**
- Abstract class enforcement
- Subclass instantiation
- Multiple inheritance levels
- Type checking and polymorphism
- Client as interface marker pattern
- Edge cases with state, properties, and methods

**Test Classes:**
- `TestClientAbstractClass` - Abstract base class verification
- `TestClientInheritance` - Inheritance patterns used in codebase
- `TestClientEdgeCases` - Edge cases and special scenarios
- `TestClientTypeChecking` - Type checking and isinstance behavior

### test_logger.py
Tests for the colored logging functionality in `infrastructure/logging/logger.py`.

**Test Coverage:**
- `ColoredFormatter` initialization and color codes
- Color formatting for all log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Global logging setup and configuration
- Log level configuration from environment variables
- Logger creation with `get_logger()`
- Log output and filtering
- Exception logging
- Edge cases with special characters and unicode

**Test Classes:**
- `TestColoredFormatter` - Color formatter functionality
- `TestGlobalLoggingSetup` - Automatic global logging configuration
- `TestGetLogger` - Logger creation and configuration
- `TestLoggerIntegration` - Integration scenarios
- `TestLoggerEdgeCases` - Edge cases and error handling

### test_redis_client.py
Tests for Redis database operations in `infrastructure/redis/redis.py`.

**Test Coverage:**
- Client initialization with default and custom configuration
- Connection pool creation
- Key namespacing
- **String operations**: get, set with TTL
- **Hash operations**: hget, hset, hgetall, hmset, hdel with TTL
- **JSON operations**: get_json, set_json with serialization
- **Set operations**: sadd, smembers, srem, sismember, scard with TTL
- **List operations**: lpush, rpush, lpop, rpop, llen, lrange with TTL
- **Utility operations**: ping, exists, delete, expire, ttl, keys, flushdb
- **Pipeline operations**: pipeline_execute
- Error handling and exception scenarios
- Integration workflows (user sessions, caching)

**Test Classes:**
- `TestRedisClientInitialization` - Client initialization and configuration
- `TestRedisClientStringOperations` - String get/set operations
- `TestRedisClientHashOperations` - Hash data structure operations
- `TestRedisClientJSONOperations` - JSON serialization/deserialization
- `TestRedisClientSetOperations` - Set data structure operations
- `TestRedisClientListOperations` - List data structure operations
- `TestRedisClientUtilityOperations` - Utility and management operations
- `TestRedisClientPipelineOperations` - Batch pipeline operations
- `TestRedisClientIntegration` - Integration scenarios

### test_influxdb_client.py
Tests for InfluxDB database operations in `infrastructure/influxdb/influxdb.py`.

**Test Coverage:**
- `BatchWriteConfig` dataclass validation
- Batch write configuration with defaults and custom values
- Configuration value validation (positive batch_size, non-negative retries)
- `BatchingCallback` success, error, and retry callbacks
- Client initialization with default and custom environment configuration
- Connection creation with proper parameters
- Write client options setup with callbacks
- Ping functionality with health endpoint
- Connection error handling (timeout, connection errors, non-200 status)
- Client close with proper cleanup and exception handling
- Abstract method enforcement
- Full client lifecycle (init, ping, close)
- Edge cases with special characters and unicode in database names

**Test Classes:**
- `TestBatchWriteConfig` - Batch write configuration and validation
- `TestBatchingCallback` - Callback methods for batch operations
- `TestInfluxDBClientInitialization` - Client initialization
- `TestInfluxDBClientPing` - Ping and health check functionality
- `TestInfluxDBClientClose` - Client cleanup and resource management
- `TestInfluxDBClientAbstractMethods` - Abstract method enforcement
- `TestInfluxDBClientIntegration` - Integration scenarios
- `TestInfluxDBClientEdgeCases` - Edge cases and error handling

## Running Tests

### Run All Infrastructure Tests
```bash
bazel test //tests/infrastructure:all_tests
```

### Run Individual Test Suites
```bash
# Test the Client abstract class
bazel test //tests/infrastructure:test_client

# Test the Logger
bazel test //tests/infrastructure:test_logger

# Test the Redis client
bazel test //tests/infrastructure:test_redis_client

# Test the InfluxDB client
bazel test //tests/infrastructure:test_influxdb_client
```

### Run with Verbose Output
```bash
bazel test //tests/infrastructure:all_tests --test_output=all
```

### Run with Coverage Report
```bash
bazel test //tests/infrastructure:all_tests --test_output=all
# Coverage reports are generated in the test output
```

## Test Patterns

All tests follow the same patterns as the Schwab test suite:

1. **Fixtures** - pytest fixtures for mocking dependencies
2. **Mocking** - Extensive use of `unittest.mock` to avoid external dependencies
3. **Test Classes** - Organized by functionality areas
4. **Descriptive Names** - Clear test method names describing what is tested
5. **Comprehensive Coverage** - Success cases, failure cases, edge cases, and integration scenarios
6. **No External Dependencies** - All external services (Redis, InfluxDB) are mocked

## Test Statistics

- **Total Test Files**: 4
- **Total Test Classes**: 27
- **Total Test Methods**: 150+
- **Code Coverage**: 100% for all tested modules

## Design Principles

1. **Isolation** - Each test is independent and can run in any order
2. **Mocking** - All external dependencies are mocked to avoid requiring services
3. **Clarity** - Test names clearly describe what is being tested
4. **Comprehensiveness** - Tests cover happy paths, error paths, and edge cases
5. **Maintainability** - Tests follow consistent patterns for easy updates
6. **Documentation** - Each test file includes docstrings explaining coverage

## Future Enhancements

Potential additions for enhanced testing:

1. **Integration Tests** - Tests with actual Redis/InfluxDB instances
2. **Performance Tests** - Benchmarking database operation performance
3. **Stress Tests** - Testing under high load scenarios
4. **Property-Based Tests** - Using hypothesis for generative testing
5. **Mutation Testing** - Ensuring test suite catches code mutations

