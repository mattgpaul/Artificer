# Contributing to Artificer

## Code Quality Standards

This project follows **Google Python Style Guide** and uses automated tooling to enforce standards.

### Quick Start

1. **Install Git hooks** (one-time setup):
   ```bash
   ./scripts/setup-hooks.sh
   ```

2. **Before committing**, the pre-commit hook will automatically:
   - Format Python files with `ruff`
   - Lint and auto-fix issues
   - Format BUILD files with `buildifier`

### Manual Commands

#### Format all code:
```bash
./scripts/format.sh
```

#### Check for issues:
```bash
./scripts/lint.sh
```

#### Individual commands:
```bash
# Format Python
bazel run //:ruff -- format .

# Lint Python
bazel run //:ruff -- check . --fix

# Format BUILD files
bazel run //:buildifier -- -r .
```

## Coding Standards

### Python

- **Docstrings**: Use Google style with Args/Returns sections
- **Type hints**: Required for all public APIs
- **Line length**: 100 characters maximum
- **Import order**: stdlib → third-party → local
- **Constants**: Extract magic values to named constants

Example:
```python
"""Module docstring with one-line summary.

Detailed description of the module.
"""

from datetime import datetime
from typing import Optional

from infrastructure.logging.logger import get_logger

# Module-level constants
_DEFAULT_TIMEOUT_SECONDS = 30


class MyClass:
    """Class docstring with one-line summary.

    Detailed description of what this class does.

    Attributes:
        logger: Configured logger instance.
        timeout: Request timeout in seconds.
    """

    def __init__(self, timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> None:
        """Initialize with optional timeout.

        Args:
            timeout: Timeout value in seconds.
        """
        self.logger = get_logger(self.__class__.__name__)
        self.timeout = timeout

    def fetch_data(self, url: str) -> dict[str, any]:
        """Fetch data from URL.

        Args:
            url: URL to fetch data from.

        Returns:
            Dictionary containing fetched data.

        Raises:
            ValueError: If URL is invalid.
            ConnectionError: If request fails.
        """
        # Implementation
```

### BUILD Files

- **Indentation**: 4 spaces
- **Target names**: Descriptive `{component}_{type}` pattern
- **Dependencies**: Sorted alphabetically
- **Visibility**: Explicit visibility declarations

Example:
```python
load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "market_handler_lib",
    srcs = ["market_handler.py"],
    visibility = ["//visibility:public"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
        requirement("requests"),
    ],
)
```

## Testing

Run all tests before committing:
```bash
bazel test //...
```

## Bypassing Hooks (Not Recommended)

Only in emergencies:
```bash
git commit --no-verify
```

## IDE Setup

### VS Code / Cursor

Install the Ruff extension:
```json
{
  "python.linting.ruffEnabled": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    }
  },
  "editor.rulers": [100]
}
```

## Resources

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Bazel Best Practices](https://bazel.build/basics/best-practices)
- Internal: `.cursor/rules/bazel-monorepo-python.mdc`
- Internal: `.cursor/rules/linting-and-formatting.mdc`

