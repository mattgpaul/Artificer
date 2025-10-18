# Artificer

## Overview
This is a monorepo for my lab. It is designed to be a one stop shop for all of my projects, whether that be software, hardware, or both.

## Philosophy
I wanted a single repository for keeping all of my projects, whether large or small. Too often I simply create a new repo for a thing I want to do, and leave all of my old code from previous projects behind. Not anymore. This repo will serve as a central location for all of my future projects, with proper architecture to handle better versioning and reuse of code throughout its lifetime. 

Its designed to challenge the norms. Too often in the industry am I forced to go along with the design or implementation laid down by the company or software architect. This repo serves as a monument to their sins. To challenge the traditional trenches that I am forced to walk, and see if "we can do better". Some paradigms will survive, but I want to see which ones dont.

Finally, its designed to be shared. I want my friends, family, and complete strangers to benefit from what I create, if I am able to create it well. Which means the repo, and systems within it, need to be well versioned and "plug-and-play".

## Core Components and Tools
### Bazel
Build system for the entire repository
- Handles all builds, tests, and runs
- Manages package visibility and dependencies
- Every project must have a BUILD file

### Python
Primary language for backend and glue code
- Default choice for new projects unless performance critical
- Acts as the integration layer between tools and systems
- Use for: APIs, data processing, system orchestration

### C++
Performance-critical implementation language
- Use when maximum speed is required
- Primary language for: hardware components, real-time systems, infrastructure
- Must justify C++ over Python (avoid premature optimization)

### Redis
In-memory data broker for cross-system communication
- Handles cached data and real-time state sharing
- Use for: data flowing between different systems/components
- Use for: session state, rate limiting, pub/sub messaging
- Keep data ephemeral - Redis is not persistent storage

### InfluxDB
Time-series database for temporal data
- Use when data is naturally organized by TIME
- Primary use cases: telemetry, metrics, sensor readings, market data
- Optimized for: high-frequency writes, time-based queries
- Data should have a timestamp as its primary organizational axis

### MySQL
Relational database for contextual/structured data
- Use when relationships between entities matter more than time
- Primary use cases: user accounts, configurations, reference data
- Optimized for: complex queries, joins, transactions
- Use when data integrity and ACID properties are required

### Docker (Grafana Only - POC)
Container orchestration for external services
- **Current Status**: Proof of concept with Grafana only
- **Hybrid Approach**: Bazel builds code, Docker runs services
- **Why**: Bazel's hermetic builds conflict with Docker's non-hermetic nature
- **Management**: Via Bazel or convenience scripts
- **Future**: May expand to Redis, InfluxDB, MySQL if POC successful

#### Docker + Bazel Integration Philosophy
The industry-standard approach is **separation of concerns**:
- **Bazel**: Handles building, testing, and running application code
- **Docker Compose**: Manages external service dependencies (databases, visualization tools)
- **Why Not rules_docker**: Deprecated and forces non-hermetic operations into Bazel's build graph

This pattern is used at Google, Uber, and other major tech companies that use both tools.

#### Architecture Layers
Container management follows the repository's component/infrastructure/system hierarchy:

1. **Infrastructure Layer** (`infrastructure/clients/grafana_client.py`):
   - `BaseGrafanaClient` provides reusable container lifecycle methods
   - Methods: `start_via_compose()`, `stop_via_compose()`, `restart_via_compose()`, etc.
   - Reusable across all systems that need Grafana

2. **System Layer** (`system/algo_trader/clients/grafana_client.py`):
   - `AlgoTraderGrafanaClient` extends BaseGrafanaClient
   - Loads dashboards from JSON files in `system/algo_trader/grafana/*.json`
   - Provides InfluxDB datasource configuration
   - Includes integrated CLI interface (no separate wrapper needed)
   - Entry point: `bazel run //system/algo_trader/clients:grafana`

3. **Data Layer** (`system/algo_trader/grafana/`):
   - Dashboard definitions as `.json` files
   - Loaded dynamically by the client at runtime
   - Easy to add/modify dashboards without changing code

This ensures container management logic lives in infrastructure (reusable), system-specific Python logic in clients, and dashboard data as JSON files.

#### Current Docker Services
- **Grafana**: Visualization dashboard (port 3000)
  - Start: `bazel run //system/algo_trader/clients:grafana`
  - Stop: `bazel run //system/algo_trader/clients:grafana stop`
  - Status: `bazel run //system/algo_trader/clients:grafana status`
  - Logs: `bazel run //system/algo_trader/clients:grafana logs`
  - Alternative: `./scripts/grafana.sh {start|stop|status|logs}`
  - Dashboards: JSON files in `system/algo_trader/grafana/`
  - Authentication: Disabled for localhost (no login required)
  - Configuration: `docker-compose.yml` at repository root

#### Services Still on Host
- **Redis**: Run manually with `redis-server`
- **InfluxDB**: Run manually (configured via `artificer.env`)
- These may be migrated to Docker Compose in future iterations

## Project Structure
### Components
Classified as hardware or software that "depends on nothing but itself"
- Stored under `/component`
- Cannot depend on anything else in the repo (`/infrastructure` or `/system`)
- Can depend on external libraries, but should limit external dependencies where possible
- Can be hardware or software related
- A hardware example would be pin registers of a microcontroller
- A software example would be a python pydantic schema

### Infrastructure
Classified as modular functionality that might be useful across multiple systems
- Stored under `/infrastructure`
- Can be dependent on `/component`, but cannot be dependent on `/system`
- Should contain base functionality for implementation in a system
- For instance a base class for redis or influxdb that handles general boilerplate to utilize those tools, that can then be inherited or "packaged" for use in `/system`
- More concrete examples would be API clients or a logger

### System
Classified as the various projects created within the repo
- Stored under `/system`
- Can be dependent on `/infrastructure` and `/component`
- Cannot depend on other systems within `/system`
- Each system represents a **distinct domain** or end-user application
- Systems should be vastly different from each other (e.g., algorithmic trader vs home automation)
- If two systems need shared logic, extract it to `/infrastructure`
- Should be able to build and package for distribution to other users
- Examples: `/system/algo_trader`, `/system/pi_robot`, `/system/weather_station`

## Development Guidelines
- Build first, then test
- Minimal dependencies - avoid bloat
- Code should be plug-and-play with clear interfaces
- Regular commits during development
- Documentation should be clear and concise
- All code requires docstrings, and should follow a common format and linting pattern
- Each `/system` must have a README.md associated with it

## Code Evolution
This repository is a learning environment. Existing code may not represent best practices.

When implementing new features:
- Use industry-standard best practices
- Don't blindly copy existing patterns
- Improve upon existing code rather than replicate it
- Point out opportunities to refactor existing code
- Reference existing code for structure (BUILD files, Bazel setup) but not necessarily for implementation patterns
- When uncertain, ask "should I match the existing pattern or use best practices?"

## Environment Configuration

Environment variables follow a **strict separation of concerns** between infrastructure and implementation:

### Philosophy: Infrastructure as a Generic Store

Infrastructure code should never contain hardcoded values or implementation-specific defaults. Think of infrastructure as a grocery store: **the store provides celery, but doesn't dictate whether it's for soup, salad, or a snack** - that decision belongs to the implementation (the system).

**Key Principles:**
1. **Infrastructure is generic**: No hardcoded hosts, ports, credentials, or business logic
2. **Systems provide configuration**: All values passed explicitly to infrastructure
3. **Secrets never in code**: All sensitive data in environment variables
4. **Fallback pattern**: System-specific env vars → Infrastructure defaults → Safe defaults

### Environment Variable Architecture

Variables are managed at two levels with a **fallback hierarchy**:

#### Root Configuration (`artificer.env`)
- **Location**: `/artificer.env` at repository root
- **Purpose**: Safe defaults for infrastructure components
- **Contains**: 
  - Default hostnames and ports (e.g., `localhost`, `3000`, `8181`)
  - Shared infrastructure tokens (Redis, InfluxDB, MySQL)
  - Container names and configuration
- **Security**: Contains secrets but NEVER committed to git (in `.gitignore`)
- **Example**:
```bash
# Grafana (safe defaults)
export GRAFANA_HOST=localhost
export GRAFANA_PORT=3000
export GRAFANA_ADMIN_USER=admin
export GRAFANA_ADMIN_PASSWORD=admin
export GRAFANA_CONTAINER_NAME=algo-trader-grafana

# InfluxDB (safe defaults)
export INFLUXDB3_HOST=localhost
export INFLUXDB3_PORT=8181
export INFLUXDB3_CONTAINER_NAME=algo-trader-influxdb
```

#### System-Specific Configuration (`system/<project>/<project>.env`)
- **Location**: `/system/<project>/<project>.env` (e.g., `/system/algo_trader/algo_trader.env`)
- **Purpose**: System-specific configuration and overrides
- **Contains**:
  - System-specific endpoints (e.g., `ALGO_TRADER_GRAFANA_HOST`)
  - Database names specific to the system
  - Docker network hostnames for container-to-container communication
- **Naming Convention**: Prefixed with uppercase system name (e.g., `ALGO_TRADER_*`)
- **Example**:
```bash
# Algo Trader InfluxDB Configuration
export ALGO_TRADER_INFLUXDB_DATABASE=algo-trader-database
export ALGO_TRADER_INFLUXDB_HOST=localhost:8181
export ALGO_TRADER_INFLUXDB_DOCKER_HOST=influxdb:8181  # Container network
```

### Loading Order and Fallback Pattern

```bash
# Terminal setup for working on a specific system
source artificer.env                          # Load infrastructure defaults
source system/algo_trader/algo_trader.env     # Load system-specific (can override)
bazel run //system/algo_trader:main
```

**Code implements fallback in system layer:**
```python
# System-specific variable first, then infrastructure default, then safe default
host = os.getenv("ALGO_TRADER_GRAFANA_HOST", 
                 os.getenv("GRAFANA_HOST", "localhost"))
```

### Infrastructure vs System Responsibilities

#### Infrastructure Layer (`/infrastructure/clients/`)
**Responsibilities:**
- Provide generic, reusable functionality
- Accept ALL configuration via constructor parameters
- NO hardcoded defaults (all passed by caller)
- NO business logic or implementation decisions
- Container lifecycle management (start, stop, status)

**What Infrastructure Should NOT Do:**
- ❌ Read environment variables directly (except in CLI utilities)
- ❌ Hardcode hostnames, ports, or credentials
- ❌ Make implementation-specific decisions (database names, URLs)
- ❌ Know about specific systems using it

**Example:**
```python
class BaseGrafanaClient:
    def __init__(self, host: str, port: int, admin_user: str, 
                 admin_password: str, container_name: str):
        # All configuration provided by caller - no defaults!
        self.host = f"http://{host}:{port}"
        self.admin_user = admin_user
        self.admin_password = admin_password
```

#### System Layer (`/system/<project>/clients/`)
**Responsibilities:**
- Read environment variables with proper fallback
- Decide which database, ports, hostnames to use
- Pass all configuration to infrastructure base classes
- Implement business logic specific to the system

**What System MUST Do:**
- ✅ Read env vars with fallback: system-specific → infrastructure → defaults
- ✅ Provide ALL parameters to infrastructure constructors
- ✅ Handle system-specific datasource configurations
- ✅ Make implementation decisions (what database, what queries, etc.)

**Example:**
```python
class AlgoTraderGrafanaClient(BaseGrafanaClient):
    def __init__(self):
        # System reads env vars and decides configuration
        grafana_host = os.getenv("ALGO_TRADER_GRAFANA_HOST", 
                                os.getenv("GRAFANA_HOST", "localhost"))
        grafana_port = int(os.getenv("GRAFANA_PORT", "3000"))
        
        # Pass everything to infrastructure
        super().__init__(
            host=grafana_host,
            port=grafana_port,
            admin_user=os.getenv("GRAFANA_ADMIN_USER", "admin"),
            admin_password=os.getenv("GRAFANA_ADMIN_PASSWORD", "admin"),
            container_name=os.getenv("GRAFANA_CONTAINER_NAME", "grafana")
        )
```

### Docker Compose Integration

`docker-compose.yml` uses environment variable substitution with safe defaults:

```yaml
services:
  influxdb:
    container_name: ${INFLUXDB3_CONTAINER_NAME:-algo-trader-influxdb}
    ports:
      - "${INFLUXDB3_PORT:-8181}:${INFLUXDB3_PORT:-8181}"
```

**Pattern**: `${VARIABLE:-default}` reads from environment, falls back to default.

**Usage**: Environment variables must be exported before running docker-compose:
```bash
source artificer.env
docker-compose up -d
# or via Bazel (which handles env loading):
bazel run //infrastructure/clients:influxdb start
```

### Security Best Practices

1. **Never commit secrets**: All `.env` files in `.gitignore`
2. **Never hardcode credentials**: Always use environment variables
3. **Use safe defaults for development**: `admin/admin` acceptable in artificer.env for localhost
4. **Production**: Override with secure values in environment
5. **Template files**: Provide `.env.template` to show required variables (without secrets)

### Rationale

- **Separation of concerns**: Infrastructure doesn't make implementation decisions
- **Reusability**: Same infrastructure code works for any system
- **Security**: Secrets isolated in env files, never in code
- **Flexibility**: Systems can override any value via environment
- **Portability**: Each system self-contained with its own configuration
- **Clarity**: Clear which layer is responsible for what decisions

## Test Guidelines
- New modules should have tests
- Use mocking where appropriate
- Tests should live alongside code with `*_test*` suffix (Python: `*_test.py`, C++: `*_test.cpp`)
- Bazel manages test execution and coverage reporting
- Tests should be broken up into 3 categories: unit, integration, and end-to-end

### Language-Specific Testing Tools

#### Python Tests
- Use the custom `pytest_test` macro from `/pytest_test.bzl` in BUILD files
- Mark tests with pytest decorators: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- Coverage is tracked via pytest-cov and can be viewed in `htmlcov/` directory after tests run
- Use `pytest.mock` for mocking

#### C++ Tests
- Use Bazel's native `cc_test` rule in BUILD files
- Use Google Test (gtest) framework for assertions and test structure
- Tag tests in BUILD file: `tags = ["unit"]`, `tags = ["integration"]`, etc.
- Mocking via Google Mock (gmock) when needed
- Example BUILD file:
```python
cc_test(
    name = "processor_test",
    srcs = ["processor_test.cpp"],
    deps = [
        ":processor",
        "@com_google_googletest//:gtest_main",
    ],
    tags = ["unit"],
)
```
- Run with: `bazel test --config=unit //component/hardware/...`

### Running Tests by Category (Works for All Languages)
The `--config` flags in `.bazelrc` work universally for Python and C++ tests:
- **Unit tests:** `bazel test --config=unit //...` - Runs all tests tagged `unit`, uses fake env vars
- **Integration tests:** `bazel test --config=integration //...` - Runs all tests tagged `integration`, uses real env vars
- **E2E tests:** `bazel test --config=e2e //...` - Runs all tests tagged `e2e`, uses real env vars
- **All tests:** `bazel test //...` - Runs all tests regardless of tags

The key is:
- **Python:** Uses `args = ["-m", "marker"]` in `pytest_test` + pytest decorators
- **C++:** Uses `tags = ["marker"]` in `cc_test` rules
- **Both:** Filtered by `--test_tag_filters` in `.bazelrc` configs

### Unit Tests
- Logic, structure, and flow checks
- Should be very fast
- Should be run each time 
- Requirements dependencies should be run each time as well
- Mocking should be used exclusively, including environment variables
- Mark test functions with `@pytest.mark.unit` decorator
- Run with: `bazel test --config=unit //path/to:test_target`
- BUILD file example:
```python
pytest_test(
    name = "test_unit",
    srcs = ["module_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],  # Allows filtering with --config=unit
    coverage_path = "path.to.module",
    deps = [":module"],
)
```

### Integration Tests
- Functionality and key checks
- Should be medium speed
- Specific token and environment variables should be used (loaded from shell environment)
- Real API calls and database interactions should be made when called out in specific implementation directions. Default should be to use mocking unless otherwise specified
- Should test the immediate file, and anything it depends on, but should not exceed that scope
- Examples would be testing if an influxdb client is actually writing to a database, and the data query comes back as expected
- Mark test functions with `@pytest.mark.integration` decorator
- Run with: `bazel test //path/to:test_target` (loads real env vars from `artificer.env`)
- BUILD file example:
```python
pytest_test(
    name = "test_integration",
    srcs = ["module_test.py"],
    args = ["-m", "integration"],
    tags = ["integration"],  # Allows filtering with --config=integration
    coverage_path = "path.to.module",
    deps = [":module"],
)
```

### End to End Tests
- Only applicable at the `/system` level
- Test an entire system
- Should be slow
- Should verify common use cases of the entire system, plus a few edge cases
- Examples would be a computer system that exposes hardware telemetry using a FastAPI, and a few clients that ingest that data into an influxdb database using a Redis data broker, where that telemetry is finally displayed in Grafana.
- Similar to integration tests, mocking should be the default, but actual products should be used where applicable. System level implementation will delegate what should/should not be mocked
- Mark test functions with `@pytest.mark.e2e` decorator (add to pytest.ini markers if needed)
- Run with: `bazel test //system/project:test_e2e`
- BUILD file example:
```python
pytest_test(
    name = "test_e2e",
    srcs = ["system_test.py"],
    args = ["-m", "e2e"],
    tags = ["e2e"],  # Allows filtering with --config=e2e
    coverage_path = "system.project",
    deps = [
        # All system dependencies
    ],
)
```

## Git Workflow and Versions
**Status:** Aspirational - will be implemented after 1-2 projects are complete. This represents the target workflow as the repo scales. Simpler workflows are acceptable initially.

git and github will be used for code configuration and management
- Commit code changes often, with commit messages that follow industry standard guidelines
- git versioning should also apply the industry standard of 3 decimal versions `<breaking-release>.<non-breaking release>.<hotfix>
- git tags should be used for versioning
- Infrastructure versions should be able to change frequently without breaking dependencies in `/system`
- Component version should also be able to change frequently without breaking dependencies in `/infrastructure` or `/system`
- Versioning **must** be robust enough that backward compatibility, or "going back in time" for a `/system` is easy and straightforward
- **Versioning Strategy:** Independent versioning - each component, infrastructure module, and system maintains its own version (e.g., `component/processor/v1.2.3`, `infrastructure/logging/v2.0.1`, `system/algo_trader/v0.5.0`). This will be revisited once the full 4-tier git workflow is implemented.
- Each project under `/system` will get its own development branch that is protected, and the branch will have the same name as the project.
- main and develop will also be protected branches

### Git Branches
Branches made in git will consist of the following
- main
- develop
- `/system` branch or `/infrastructure` branch or `/component` branch
- feature branch of the system/infrastructure/component branch being worked on

#### Main
- Primary branch, and what most (or all) end users will see
- Merges `develop` on a nightly chron-job
- All `end2end` tests must pass with 80% code coverage, otherwise main will not merge develop into it
- A new version will be created on a successful merge
- cannot be edited directly

#### Develop
- Base branch for developers
- should be the `base` branch for all new projects or additions to infrastructure or component
- Cannot be edited directly
- All `integration` tests for a particular feature branch must pass with 90% code coverage in order to merge
- A new version will be created on a successful merge

#### Project Branch
- Base branch for development of a new system, infrastructure, or component
- Cannot be edited directly
- All `unit` tests for a project feature branch must pass, with 95% code coverage in order to merge
- A new version will be created on a successful merge

#### Project Feature Branch
- Feature branch for development
- should follow the naming convention `<system or infrastructure or component>/<name of project (should match project branch name)>/<feature name>`

## Inter-System Communication
- Redis: Real-time data sharing between systems
- InfluxDB: Time-series telemetry and metrics
- MySQL: Persistent contextual/relational data
- Systems should be loosely coupled via these data layers

## What Belongs Here
- Personal projects (software, hardware, or hybrid)
- Reusable infrastructure components
- Experimental/learning projects

## What Does NOT Belong Here
- Third-party code (use dependencies instead)
- Proprietary work from employers

## Scripts Directory
The `/scripts` directory is for development tooling and necessary workarounds
- Use **very** sparingly
- Should be committed, but excluded from normal builds
- Typical use cases: git hooks, CI/CD helpers, build workarounds
- If you're creating a script, first consider if it belongs in `/infrastructure` instead
- Scripts are usually an indicator of a necessary workaround, not core functionality

## Code Style Standards
- Python: docstrings required (Google style preferred)
- C++: docstrings required (Doxygen style)
- Linting: (TBD - will be standardized once patterns emerge)
- Output: Maximum 1-2 status prints per operation

## Bazel Patterns
- Every directory needs a BUILD file (even if empty for visibility)
- Visibility: public only for systems, otherwise specify explicitly
- Custom rules: pytest_test (in /pytest_test.bzl)
- **No `__init__.py` files needed**: Bazel's `py_library` rules handle Python package structure through BUILD files
  - PYTHONPATH is set up automatically based on BUILD declarations
  - Imports work via `from infrastructure.module import Class` without `__init__.py`
  - Versioning is handled through git tags (e.g., `system/algo_trader/v0.1.0`)