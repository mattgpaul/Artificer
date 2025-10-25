load("@rules_python//python:defs.bzl", "py_library")

# Library for market data service CLI integration tests
py_library(
    name = "test_market_data_lib",
    testonly = True,
    srcs = ["test_market_data.py"],
    visibility = ["//system/algo_trader/service:__pkg__"],
    deps = [
        "//system/algo_trader/market_data:market_data_lib",
        "//system/algo_trader/service:market_data",
    ],
)
