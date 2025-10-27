load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

# Library for tickers tests
py_library(
    name = "test_tickers_lib",
    testonly = True,
    srcs = ["test_tickers.py"],
    visibility = ["//system/algo_trader/datasource/sec:__pkg__"],
    deps = [
        "//system/algo_trader/datasource/sec:tickers_lib",
        requirement("pytest"),
    ],
)
