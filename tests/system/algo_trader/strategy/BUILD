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
        "//system/algo_trader/strategy:strategies",
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
        "//system/algo_trader/strategy:strategies",
        requirement("numpy"),
        requirement("pandas"),
        requirement("pytest"),
    ],
)

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
        "//infrastructure/logging:logger",
        "//system/algo_trader/datasource/sec:tickers_lib",
        "//system/algo_trader/strategy:cli_utils",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_main_lib",
    testonly = True,
    srcs = ["test_main.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:cli_utils",
        "//system/algo_trader/strategy:executor",
        "//system/algo_trader/strategy:main_lib",
        "//system/algo_trader/strategy:strategies",
        requirement("pytest"),
    ],
)
