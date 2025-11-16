load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_execution_lib",
    testonly = True,
    srcs = ["test_execution.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        "//tests/system/algo_trader/backtest:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_results_generator_lib",
    testonly = True,
    srcs = ["test_results_generator.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        "//tests/system/algo_trader/backtest:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
