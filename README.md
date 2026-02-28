# Artificer
Monorepo for my robotics lab

## Project Structure

### Infrastructure
Reusable infrastructure modules (`/infrastructure`)
- Can depend on external libraries
- Should contain base functionality for implementation in a system
- Examples: API clients, loggers, database wrappers

### System
End-user applications and projects (`/system`)
- Can depend on `/infrastructure`
- Each system represents a distinct domain or end-user application
- Examples: `/system/algo_trader`

### Tests
Test suites organized by component (`/tests`)

## Contributing

See [docs/artificer.md](docs/artificer.md) for detailed project philosophy and guidelines.
