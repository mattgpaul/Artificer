load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/backtest:__pkg__",
        "//tests/system/algo_trader/backtest:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_engine_lib",
    testonly = True,
    srcs = ["test_engine.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/backtest:backtest_lib",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_main_lib",
    testonly = True,
    srcs = ["test_main.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/backtest:backtest_lib",
        "//system/algo_trader/backtest:main_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
