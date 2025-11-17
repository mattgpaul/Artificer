load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "strategies",
    srcs = [
        "base.py",
        "core/data_access.py",
        "core/sequential.py",
        "core/signal_writer.py",
        "core/threaded.py",
        "journal/calculator.py",
        "journal/efficiency.py",
        "journal/journal.py",
        "journal/trade_matching.py",
        "strategies/sma_crossover.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",  # Available to algo_trader subpackages
        "//tests/system/algo_trader/strategy:__subpackages__",  # Allow test access
    ],
    deps = [
        "//infrastructure:client",
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//infrastructure/threads:thread_manager",
        "//system/algo_trader/influx:market_data_influx",
        "//system/algo_trader/strategy/utils/studies/moving_average:simple_moving_average",
        requirement("numpy"),
        requirement("pandas"),
    ],
)

py_library(
    name = "cli_utils",
    srcs = ["utils/cli_utils.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/datasource/sec:tickers_lib",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pandas"),
    ],
)

py_library(
    name = "executor",
    srcs = ["core/executor.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        ":cli_utils",
        ":strategies",
        "//infrastructure/logging:logger",
    ],
)

py_library(
    name = "main_lib",
    srcs = ["main.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/strategy:__pkg__",
    ],
    deps = [
        ":cli_utils",
        ":executor",
        ":strategies",
        "//infrastructure/logging:logger",
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

# Test targets
pytest_test(
    name = "test_base",
    size = "small",
    coverage_path = "system.algo_trader.strategy.base",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy:test_base_lib",
)

pytest_test(
    name = "test_journal",
    size = "small",
    coverage_path = "system.algo_trader.strategy.journal.journal",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/strategy/journal:test_journal_lib",
)

pytest_test(
    name = "test_trade_matching",
    size = "small",
    coverage_path = "system.algo_trader.strategy.journal.trade_matching",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/strategy/journal:test_trade_matching_lib",
)

pytest_test(
    name = "test_sma_crossover",
    size = "small",
    coverage_path = "system.algo_trader.strategy.strategies.sma_crossover",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/strategies:test_sma_crossover_lib",
)

pytest_test(
    name = "test_executor",
    size = "small",
    coverage_path = "system.algo_trader.strategy.core.executor",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/core:test_executor_lib",
)

pytest_test(
    name = "test_cli_utils",
    size = "small",
    coverage_path = "system.algo_trader.strategy.utils.cli_utils",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy/utils:test_cli_utils_lib",
)

pytest_test(
    name = "test_main",
    size = "small",
    coverage_path = "system.algo_trader.strategy.main",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/strategy:test_main_lib",
)
