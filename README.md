# Artificer
Monorepo for my robotics lab

## Linting and Formatting Tools

Bazel targets for linting and formatting code in the Artificer monorepo.

Based on the approach from [bazel-ruff](https://github.com/philipuvarov/bazel-ruff) by [Phil Uvarov](https://philuvarov.io/bazel-can-be-ruff/).

### Quick Start

All tools (Ruff and Buildifier) are downloaded automatically by Bazel from GitHub releases. No manual installation needed!

### Available Commands

#### Python Formatting and Linting

```bash
# Format Python files
bazel run //:ruff -- format .

# Lint Python files
bazel run //:ruff -- check .

# Lint and auto-fix
bazel run //:ruff -- check --fix .
```

#### Python Type Checking

For type checking, install mypy separately (not managed by Bazel):

```bash
pip install mypy
mypy infrastructure system tests
```

#### Bazel Formatting and Linting

```bash
# Format Bazel files
bazel run //:buildifier -- -r .

# Lint Bazel files  
bazel run //:buildifier -- -lint=warn -mode=check -r .

# Format and fix lint issues
bazel run //:buildifier -- -lint=fix -r .
```

### Configuration Files

- `ruff.toml` - Ruff configuration (formatter and linter for Python)
- `mypy.ini` - mypy configuration (type checker for Python)

See `.cursor/rules/linting-and-formatting.mdc` for detailed documentation on standards and conventions.

### Pre-Commit Workflow

Before committing code:

1. Format Python: `bazel run //:ruff -- format .`
2. Lint Python: `bazel run //:ruff -- check --fix .`
3. Format Bazel: `bazel run //:buildifier -- -r .`
4. Test: `bazel test //...`
