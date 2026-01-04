load("@rules_python//python:defs.bzl", "py_library")

# Project aggregation target - collects all algo_trader components (clean slate)
py_library(
    name = "library",
    tags = [
        "algo_trader",
        "system",
    ],
    visibility = [
        "//system:__pkg__",  # Available to system package
    ],
    deps = [
        "//system/algo_trader/infra/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
    ],
)

# CI system-scoped test runner may execute `bazel test //system/algo_trader:all`.
# Provide an aggregate test target at the system package root so tests are found.
test_suite(
    name = "tests",
    tests = [
        "//system/algo_trader/schwab:test_account_handler",
        "//system/algo_trader/schwab:test_market_handler",
        "//system/algo_trader/schwab:test_schwab_client",
        "//system/algo_trader/schwab:test_timescale_enum",
    ],
)
