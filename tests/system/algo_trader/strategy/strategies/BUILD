load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_sma_crossover_lib",
    testonly = True,
    srcs = ["test_sma_crossover.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:strategies",
        "//tests/system/algo_trader/strategy:conftest_lib",
        requirement("numpy"),
        requirement("pandas"),
        requirement("pytest"),
    ],
)
