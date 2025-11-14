load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")

py_library(
    name = "backtest_lib",
    srcs = [
        "engine.py",
        "execution.py",
        "results.py",
        "strategy_wrapper.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:market_data_influx",
        "//system/algo_trader/strategy:strategies",
        "//system/algo_trader/strategy:cli_utils",
        requirement("pandas"),
    ],
)

py_library(
    name = "main_lib",
    srcs = ["main.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
    deps = [
        ":backtest_lib",
        "//system/algo_trader/strategy:strategies",
        "//system/algo_trader/strategy:cli_utils",
        "//infrastructure/logging:logger",
        requirement("pandas"),
    ],
)

py_binary(
    name = "main",
    srcs = ["main.py"],
    main = "main.py",
    visibility = ["//visibility:public"],
    deps = [
        ":main_lib",
    ],
)

