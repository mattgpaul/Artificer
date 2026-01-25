load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

# Domain models and states
py_library(
    name = "domain_models",
    srcs = [
        "models.py",
        "states.py",
    ],
    # In the monorepo, sources live under `system/algo_trader/...` but we want to
    # import as `algo_trader.*` (matching deploy bundle layout). Depend on the
    # repo-root helper that adds `system/` to PYTHONPATH.
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader:__pkg__",
        "//tests/system/algo_trader/domain:__pkg__",
    ],
    deps = [requirement("pandas")],
)

# Port interfaces (defined in ports subpackage)
# Use alias for convenience
py_library(
    name = "domain_ports",
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader:__pkg__",
        "//tests/system/algo_trader/domain:__pkg__",
    ],
    deps = [
        "//system/algo_trader/domain/ports",
    ],
)

# Engine (main domain logic)
py_library(
    name = "domain",
    srcs = [
        "engine.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader:__pkg__",
        "//tests/system/algo_trader/domain:__pkg__",
    ],
    deps = [
        ":domain_models",
        ":domain_ports",
    ],
)

# Unit tests
pytest_test(
    name = "test_engine_unit",
    args = [
        "-m",
        "unit",
    ],
    coverage_path = "system.algo_trader.domain",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/domain:test_engine_unit_lib",
)

# Integration tests
pytest_test(
    name = "test_engine_integration",
    args = [
        "-m",
        "integration",
    ],
    coverage_path = "system.algo_trader.domain",
    tags = ["integration"],
    test_lib = "//tests/system/algo_trader/domain:test_engine_integration_lib",
)
