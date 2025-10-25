# Configuration Layer Foundation Plan

## Overview

Add configuration management infrastructure that enables future microservice deployment while maintaining 100% backward compatibility with the current standalone Bazel workflow. Config split between infrastructure (reusable) and algo_trader (system-specific).

## Architecture Goals

**Current State:**
- Services run via `bazel run //system/algo_trader/service:<service_name>`
- Configuration via environment variables in `algo_trader.env`
- Redis, InfluxDB at `localhost` (hardcoded defaults)

**After This Phase:**
- Same Bazel workflow works unchanged
- Config layer exists but is optional (opt-in)
- Infrastructure clients support config injection
- Foundation ready for future Docker/microservice deployment

## Key Design Principles

1. **100% Backward Compatible**: All existing code works without changes
2. **Opt-In Configuration**: Config layer only used when explicitly passed
3. **Environment Variables First**: Current workflow (env vars) remains default
4. **No Breaking Changes**: All constructor signatures remain compatible via optional parameters
5. **Type Safety**: Pydantic validation when config is used
6. **Proper Layering**: Infrastructure configs reusable, system configs composed
7. **Bazel-Native**: No `__init__.py`, explicit dependencies via BUILD files
8. **Pydantic Built-ins**: Use pydantic-settings for automatic env var parsing

## Dependency Graph

```
infrastructure/config.py (RedisConfig, InfluxDBConfig)
  ↓
infrastructure/redis/redis.py (accepts RedisConfig)
infrastructure/influxdb/influxdb.py (accepts InfluxDBConfig)
  ↓
system/algo_trader/config.py (AlgoTraderConfig composes infrastructure configs)
  ↓
system/algo_trader/redis/*.py (brokers accept RedisConfig)
system/algo_trader/influx/*.py (accepts InfluxDBConfig)
  ↓
system/algo_trader/service/*.py (services accept AlgoTraderConfig)
```

## What This Enables (Future)

After this phase, future microservice deployment only requires:
1. Create AlgoTraderConfig programmatically with Docker service names
2. Pass config to service constructors
3. No code changes needed!

