load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

# Library for MarketBase tests
py_library(
    name = "test_base_lib",
    testonly = True,
    srcs = ["test_base.py"],
    visibility = ["//system/algo_trader/market_data:__pkg__"],
    deps = [
        "//system/algo_trader/market_data:market_data_lib",
        "//system/algo_trader/utils:schema",
    ],
)

# Library for LiveMarketService tests
py_library(
    name = "test_live_lib",
    testonly = True,
    srcs = ["test_live.py"],
    visibility = ["//system/algo_trader/market_data:__pkg__"],
    deps = [
        "//system/algo_trader/market_data:market_data_lib",
    ],
)

# Library for HistoricalMarketService tests
py_library(
    name = "test_historical_lib",
    testonly = True,
    srcs = ["test_historical.py"],
    visibility = ["//system/algo_trader/market_data:__pkg__"],
    deps = [
        "//system/algo_trader/market_data:market_data_lib",
    ],
)

# Test targets
pytest_test(
    name = "test_base",
    size = "small",
    coverage_path = "system.algo_trader.market_data",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/market_data:test_base_lib",
)

pytest_test(
    name = "test_live",
    size = "small",
    coverage_path = "system.algo_trader.market_data",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/market_data:test_live_lib",
)

pytest_test(
    name = "test_historical",
    size = "small",
    coverage_path = "system.algo_trader.market_data",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/market_data:test_historical_lib",
)
