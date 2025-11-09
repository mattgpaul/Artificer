load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "tickers_lib",
    srcs = ["tickers.py"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/datasource/sec:__pkg__",
        "//tests/system/algo_trader/strategy:__pkg__",  # Allow strategy tests to access tickers
    ],
    deps = [
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
)

# Test for Tickers - SEC Ticker Data Retrieval
pytest_test(
    name = "test_tickers",
    size = "small",
    coverage_path = "system.algo_trader.datasource.sec",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/datasource/sec:test_tickers_lib",
)
