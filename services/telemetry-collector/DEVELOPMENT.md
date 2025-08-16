# Telemetry Collector - Development Guide

This guide explains what you need to implement to build the industry-standard telemetry collector.

## 🎯 Implementation Checklist

### Phase 1: Core Data Models
Create `src/models.rs` with:

- [ ] `TelemetryMessage` struct with schema versioning
- [ ] `TelemetryData` struct with metadata 
- [ ] `TelemetryMetrics` enum for different metric types
- [ ] `CpuMetrics` struct with CPU-specific data
- [ ] Helper structs: `LoadAverages`, `CoreMetrics`, `CpuFrequencies`
- [ ] Unit tests for serialization/deserialization
- [ ] Schema compatibility tests

**Key Requirements:**
- Use `#[derive(Debug, Clone, Serialize, Deserialize)]` on all structs
- Include `schema_version` field in `TelemetryMessage`
- Use `Option<T>` for fields that might not be available on all systems
- Include comprehensive documentation

### Phase 2: Error Handling  
Create `src/errors.rs` with:

- [ ] `TelemetryError` enum using `thiserror`
- [ ] Error variants for: System, Collection, Publishing, Configuration
- [ ] Conversion implementations (`From` traits)
- [ ] Helper methods for creating common errors
- [ ] `TelemetryResult<T>` type alias

### Phase 3: Collector Traits
Create `src/collectors/traits.rs` with:

- [ ] `TelemetryCollector` trait (main interface)
- [ ] `CpuCollector` trait (CPU-specific operations) 
- [ ] Use `#[async_trait]` for async methods
- [ ] Include detailed documentation for each method
- [ ] Define expected behavior and error conditions

### Phase 4: Publisher Traits
Create `src/publishers/traits.rs` with:

- [ ] `TelemetryPublisher` trait (main interface)
- [ ] `RedisPublisher` trait (Redis-specific operations)
- [ ] Support for both single and batch publishing
- [ ] Health check methods
- [ ] Connection management abstractions

### Phase 5: CPU Collector Implementation
Create `src/collectors/cpu.rs` with:

- [ ] Struct implementing `CpuCollector` trait
- [ ] Use `sysinfo` crate for system metrics
- [ ] Handle systems without temperature sensors gracefully
- [ ] Per-core metrics collection
- [ ] Load average collection
- [ ] CPU frequency collection
- [ ] Comprehensive error handling
- [ ] Unit tests with mocking

### Phase 6: Redis Publisher Implementation  
Create `src/publishers/redis.rs` with:

- [ ] Struct implementing `RedisPublisher` trait
- [ ] Connection pool management
- [ ] Retry logic with exponential backoff
- [ ] JSON serialization of messages
- [ ] Queue operations (LPUSH for publishing)
- [ ] Health check implementation
- [ ] Unit tests with Redis mock

### Phase 7: Configuration Management
Create `src/config.rs` with:

- [ ] Configuration struct with all service settings
- [ ] Environment variable loading using `config` crate
- [ ] Validation of configuration values
- [ ] Default values for development
- [ ] Configuration for Redis connection, collection intervals, etc.
- [ ] Schema for environment variable documentation

### Phase 8: Service Assembly
Create `src/lib.rs` with:

- [ ] Module declarations and exports
- [ ] Version information functions
- [ ] Service factory functions
- [ ] Integration tests
- [ ] Documentation for external consumers

### Phase 9: Main Application
Create `src/main.rs` with:

- [ ] Application startup and configuration loading
- [ ] Graceful shutdown handling (SIGTERM)
- [ ] Service orchestration (collector + publisher loop)
- [ ] Structured logging setup
- [ ] Health check endpoint
- [ ] Error handling and recovery

## 🧪 Testing Strategy

### Unit Tests
For each module, create tests that:
- Test happy path scenarios
- Test error conditions
- Test edge cases (missing sensors, connection failures)
- Use mocking for external dependencies
- Verify schema compatibility

### Integration Tests
Create `tests/integration_test.rs` with:
- End-to-end data collection and publishing
- Redis integration tests
- Schema evolution tests
- Performance benchmarks

## 🔧 Development Workflow

### 1. Start with Models
Begin with `src/models.rs` - this defines your data contracts and is the foundation for everything else.

### 2. Add Error Handling  
Create robust error types in `src/errors.rs` - you'll use these throughout the system.

### 3. Define Interfaces
Create the traits in `collectors/traits.rs` and `publishers/traits.rs` - these define the abstractions.

### 4. Implement Core Logic
Build the CPU collector and Redis publisher - the actual business logic.

### 5. Wire Everything Together
Create the main application that orchestrates all components.

## 📋 Industry Standards Compliance

As you implement each component, ensure:
- ✅ **Dependency Injection**: Components receive dependencies via constructors
- ✅ **Error Propagation**: Use `Result<T, E>` and `?` operator consistently
- ✅ **Structured Logging**: Use `tracing` with appropriate levels
- ✅ **Configuration**: All config via environment variables
- ✅ **Testing**: Comprehensive unit and integration tests
- ✅ **Documentation**: Detailed docs for public APIs
- ✅ **Versioning**: Update schema/service versions when making changes

## 🚀 Build and Test Commands

```bash
# Generate dependencies and build
bazel build //services/telemetry-collector:telemetry-collector

# Run tests
bazel test //services/telemetry-collector:telemetry_collector_test

# Run the service (after implementation)
bazel run //services/telemetry-collector:telemetry-collector

# Check versions
./scripts/version-check.sh
```

## 📚 Key Learning Concepts

This implementation teaches:
- **Trait-based architecture** for clean abstractions
- **Async Rust** with tokio for high-performance I/O
- **Error handling** patterns in systems programming  
- **Schema evolution** for long-term maintainability
- **Configuration management** following 12-factor principles
- **Testing strategies** including mocking and integration tests
- **Build system integration** with Bazel

Start with the models and work your way through each phase. Each component builds on the previous ones!
