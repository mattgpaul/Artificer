# Telemetry Collector Schema Migrations

This directory contains documentation for all schema changes and migration procedures.

## Schema Version History

### v1.0.0 (Schema Version 1)
- **Release Date**: Initial release
- **Changes**: 
  - Initial CPU telemetry format
  - Basic CPU metrics (usage, temperature, cores)
  - Load averages and frequency information
- **Breaking Changes**: None (initial version)
- **Migration**: None required

## Migration Procedures

### Schema Version Compatibility

The telemetry collector implements **backward-compatible schema evolution**:

1. **Consumers can read older schemas** - New collector versions can process old message formats
2. **Graceful degradation** - Unknown future schemas fall back to supported versions
3. **Version negotiation** - Services communicate their supported schema versions

### Rolling Back Versions

For each schema version change, we maintain:
- **Forward migration** - How to upgrade from previous version
- **Rollback procedure** - How to safely downgrade if needed
- **Data compatibility matrix** - Which versions can communicate

### Adding New Schema Versions

When adding a new schema version:

1. **Update `TelemetryMessage::CURRENT_SCHEMA_VERSION`**
2. **Add new enum variants with version suffix** (e.g., `cpu_v2`)
3. **Document migration in this directory**
4. **Update compatibility tests**
5. **Create rollback documentation**

## Future Schema Changes (Planned)

### v2.0.0 (Schema Version 2) - Planned
- Add memory metrics (`memory_v1` variant)
- Add disk I/O metrics (`disk_v1` variant)
- Enhanced CPU metrics with power consumption
- **Backward Compatibility**: v1 consumers can still read CPU data

### v3.0.0 (Schema Version 3) - Proposed
- Network interface metrics
- Container/process-level telemetry
- Geographic/datacenter metadata
- **Backward Compatibility**: v1 and v2 consumers supported
