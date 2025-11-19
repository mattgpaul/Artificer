load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/backtest:__pkg__",
        "//tests/system/algo_trader/backtest/processor:__subpackages__",
    ],
    deps = [
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_processor_lib",
    testonly = True,
    srcs = ["test_processor.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        ":conftest_lib",
        "//infrastructure/multiprocess:process_manager",
        "//system/algo_trader/backtest:backtest_lib",
        "//tests/system/algo_trader/backtest:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_worker_lib",
    testonly = True,
    srcs = ["test_worker.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/backtest:backtest_lib",
        "//tests/system/algo_trader/backtest:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
