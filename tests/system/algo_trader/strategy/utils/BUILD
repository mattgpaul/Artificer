load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_cli_utils_lib",
    testonly = True,
    srcs = ["test_cli_utils.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/datasource/sec:tickers_lib",
        "//system/algo_trader/strategy:cli_utils",
        "//tests/system/algo_trader/strategy:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
