load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "schema",
    srcs = ["schema.py"],
    visibility = [
        "//system:__pkg__",  # Available to system package (for project aggregation)
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
        "//tests/system/algo_trader/utils:__pkg__",  # Allow test access
    ],
    deps = [
        requirement("pydantic"),
    ],
)

# Test for Schema models - StockQuote and MarketHours
pytest_test(
    name = "test_schema",
    size = "small",
    coverage_path = "system.algo_trader.utils",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/utils:test_schema_lib",
)
