load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

# Conftest library
py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = ["//tests/system/algo_trader/service:__subpackages__"],
    deps = [
        requirement("pytest"),
    ],
)

# Library for market data service CLI integration tests
py_library(
    name = "test_market_data_lib",
    testonly = True,
    srcs = ["test_market_data.py"],
    visibility = [
        "//system/algo_trader/service:__pkg__",
        "//system/algo_trader/service/market_data:__pkg__",
    ],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/service/market_data:main",
        "//system/algo_trader/service/market_data:market_data_lib",
    ],
)
