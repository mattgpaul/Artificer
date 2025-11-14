load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_executor_lib",
    testonly = True,
    srcs = ["test_executor.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:cli_utils",
        "//system/algo_trader/strategy:executor",
        "//system/algo_trader/strategy:strategies",
        "//tests/system/algo_trader/strategy:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
