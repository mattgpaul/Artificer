load("@rules_python//python:defs.bzl", "py_library")

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
