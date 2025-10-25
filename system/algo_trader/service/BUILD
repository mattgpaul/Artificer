load("@pip//:requirements.bzl", "requirement")  # @unused
load("//:pytest_test.bzl", "pytest_test")

py_binary(
    name = "market_data",
    srcs = ["market_data.py"],
    main = "market_data.py",
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__pkg__",
        "//tests/system/algo_trader/service:__pkg__",
    ],
    deps = ["//system/algo_trader/market_data:market_data_lib"],
)

# Test target for market data service CLI
pytest_test(
    name = "test_market_data",
    size = "medium",
    coverage_path = "system.algo_trader.service",
    tags = ["integration"],
    test_lib = "//tests/system/algo_trader/service:test_market_data_lib",
)
