load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_processor_lib",
    testonly = True,
    srcs = ["test_processor.py"],
    visibility = ["//system/algo_trader/datasource/populate:__pkg__"],
    deps = [
        "//system/algo_trader/datasource/populate:populate_lib",
        "//system/algo_trader/datasource/populate/ohlcv:ohlcv_lib",
        "//tests/system/algo_trader/datasource/populate:conftest_lib",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_handler_lib",
    testonly = True,
    srcs = ["test_handler.py"],
    visibility = ["//system/algo_trader/datasource/populate:__pkg__"],
    deps = [
        "//system/algo_trader/datasource/populate:populate_lib",
        "//system/algo_trader/datasource/populate/ohlcv:ohlcv_lib",
        "//tests/system/algo_trader/datasource/populate:conftest_lib",
        requirement("pytest"),
    ],
)

