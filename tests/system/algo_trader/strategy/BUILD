load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_base_lib",
    testonly = True,
    srcs = ["test_base.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:base",
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
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:base",
        "//system/algo_trader/strategy:sma_crossover",
        requirement("pandas"),
        requirement("numpy"),
        requirement("pytest"),
    ],
)
