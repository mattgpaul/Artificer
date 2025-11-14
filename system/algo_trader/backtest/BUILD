load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")

py_library(
    name = "backtest_lib",
    srcs = [
        "engine.py",
        "execution.py",
        "processor.py",
        "progress.py",
        "results.py",
        "strategy_wrapper.py",
        "utils.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/multiprocess:process_manager",
        "//system/algo_trader/influx:market_data_influx",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/strategy:strategies",
        "//system/algo_trader/strategy:cli_utils",
        requirement("pandas"),
        requirement("tqdm"),
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

