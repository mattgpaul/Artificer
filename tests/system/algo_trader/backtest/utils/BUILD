load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_utils_lib",
    testonly = True,
    srcs = ["test_utils.py"],
    visibility = ["//system/algo_trader/backtest:__pkg__"],
    deps = [
        "//system/algo_trader/backtest:backtest_lib",
        "//tests/system/algo_trader/backtest:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
