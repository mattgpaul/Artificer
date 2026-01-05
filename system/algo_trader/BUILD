load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

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
        "//system/algo_trader/apps",
        "//system/algo_trader/cli",
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
        "//system/algo_trader/infra/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
    ],
)

pytest_test(
    name = "test_sma_e2e",
    size = "small",
    coverage_path = "system.algo_trader",
    tags = [
        "e2e",
        "integration",
    ],
    test_lib = "//tests/system/algo_trader:test_sma_e2e_lib",
)
