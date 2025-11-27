load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

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
        "//system/algo_trader/strategy:strategy_lib",
        "//tests/system/algo_trader/backtest:conftest_lib",
        "//tests/system/algo_trader/strategy:conftest_lib",
        requirement("numpy"),
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_ema_crossover_lib",
    testonly = True,
    srcs = ["test_ema_crossover.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy:strategy_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

pytest_test(
    name = "test_ema_crossover",
    size = "small",
    coverage_path = "system.algo_trader.strategy.strategies",
    tags = ["unit"],
    test_lib = ":test_ema_crossover_lib",
)
