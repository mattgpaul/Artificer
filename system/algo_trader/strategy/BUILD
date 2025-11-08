load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "base",
    srcs = ["base.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
        "//tests/system/algo_trader/strategy:__pkg__",  # Allow test access
    ],
    deps = [
        "//infrastructure:client",
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//infrastructure/threads:thread_manager",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pandas"),
        requirement("numpy"),
    ],
)

py_library(
    name = "sma_crossover",
    srcs = ["sma_crossover.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
        "//tests/system/algo_trader/strategy:__pkg__",  # Allow test access
    ],
    deps = [
        ":base",
        "//infrastructure/influxdb",
        requirement("pandas"),
    ],
)

py_library(
    name = "cli_utils",
    srcs = ["cli_utils.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__pkg__",
    ],
    deps = [
        "//system/algo_trader/datasource/sec:tickers_lib",
    ],
)

py_binary(
    name = "main",
    srcs = ["main.py"],
    main = "main.py",
    visibility = ["//visibility:public"],
    deps = [
        ":cli_utils",
        ":sma_crossover",
        "//infrastructure/logging:logger",
    ],
)

# Test targets
pytest_test(
    name = "test_base",
    size = "small",
    coverage_path = "system.algo_trader.strategy.base",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy:test_base_lib",
)

pytest_test(
    name = "test_sma_crossover",
    size = "small",
    coverage_path = "system.algo_trader.strategy.sma_crossover",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy:test_sma_crossover_lib",
)
