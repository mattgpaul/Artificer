load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/strategy:__pkg__",
        "//tests/system/algo_trader/strategy/strategies:__pkg__",
    ],
    deps = [
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_sma_crossover_lib",
    testonly = True,
    srcs = ["test_sma_crossover.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        ":conftest_lib",
        "//infrastructure/logging:logger",
        "//system/algo_trader/backtest:backtest_lib",
        "//system/algo_trader/strategy:strategies",
        "//tests/system/algo_trader/backtest:conftest_lib",
        "//tests/system/algo_trader/strategy:conftest_lib",
        requirement("numpy"),
        requirement("pandas"),
        requirement("pytest"),
    ],
)
