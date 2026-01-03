load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

# Conftest library
py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = ["//tests/system/algo_trader/strategy/utils:__subpackages__"],
    deps = [
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_cli_utils_lib",
    testonly = True,
    srcs = ["test_cli_utils.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        ":conftest_lib",
        "//infrastructure/logging:logger",
        "//system/algo_trader/backtest:cli_utils",
        "//system/algo_trader/datasource/sec:tickers_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
