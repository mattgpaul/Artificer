load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_execution_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_execution.py",
    ],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_results_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_results.py",
    ],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        "//system/algo_trader/redis:redis_services",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_engine_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_engine.py",
    ],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_processor_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_processor.py",
    ],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//infrastructure/multiprocess:process_manager",
        "//system/algo_trader/backtest:backtest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
