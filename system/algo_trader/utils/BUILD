load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "schema",
    srcs = ["schema.py"],
    deps = [
        requirement("pydantic"),
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
        "//system:__pkg__",  # Available to system package (for project aggregation)
        "//tests/system/algo_trader/utils:__pkg__",  # Allow test access
    ],
)

# Test for Schema models - StockQuote and MarketHours
pytest_test(
    name = "test_schema",
    test_lib = "//tests/system/algo_trader/utils:test_schema_lib",
    coverage_path = "system.algo_trader.utils",
    size = "small",
    tags = ["unit"],
)
