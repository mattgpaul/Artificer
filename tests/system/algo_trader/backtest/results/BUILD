load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_results_lib",
    testonly = True,
    srcs = ["test_results.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        "//system/algo_trader/redis:redis_services",
        "//tests/system/algo_trader/backtest:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_writer_lib",
    testonly = True,
    srcs = ["test_writer.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        "//system/algo_trader/redis:redis_services",
        "//tests/system/algo_trader/backtest:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
