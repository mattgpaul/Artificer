load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "cli_utils",
    srcs = ["cli_utils.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/datasource/sec:tickers_lib",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pandas"),
    ],
)

py_library(
    name = "backtest_lib",
    srcs = [
        "core/data_loader.py",
        "core/execution.py",
        "core/results_generator.py",
        "core/signal_collector.py",
        "core/time_stepper.py",
        "engine.py",
        "ohlcv_cache.py",
        "processor/parallel.py",
        "processor/processor.py",
        "processor/sequential.py",
        "processor/worker.py",
        "results/hash.py",
        "results/results.py",
        "results/schema.py",
        "results/writer.py",
        "utils/progress.py",
        "utils/utils.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__subpackages__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        ":cli_utils",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/multiprocess:process_manager",
        "//infrastructure/redis",
        "//system/algo_trader/influx:market_data_influx",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/strategy:strategy_lib",
        "//system/algo_trader/strategy/filters:filters_lib",
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        requirement("pandas"),
        requirement("pyyaml"),
        requirement("tqdm"),
    ],
)

py_library(
    name = "main_lib",
    srcs = ["main.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__pkg__",
    ],
    deps = [
        ":backtest_lib",
        ":cli_utils",
        ":portfolio_main_lib",
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:strategy_lib",
        "//system/algo_trader/strategy/filters:filters_lib",
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        requirement("pandas"),
    ],
    # Note: main.py imports from subdirectories via backtest_lib
)

py_binary(
    name = "main",
    srcs = ["main.py"],
    data = ["ohlcv_cache_config.yaml"],
    main = "main.py",
    visibility = ["//visibility:public"],
    deps = [
        ":main_lib",
    ],
)

py_library(
    name = "portfolio_main_lib",
    srcs = ["portfolio_main.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__pkg__",
    ],
    deps = [
        ":backtest_lib",
        ":cli_utils",
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:market_data_influx",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/strategy/portfolio_manager:portfolio_manager_lib",
        requirement("pandas"),
    ],
)

py_binary(
    name = "portfolio_main",
    srcs = ["portfolio_main.py"],
    data = ["ohlcv_cache_config.yaml"],
    main = "portfolio_main.py",
    visibility = ["//visibility:public"],
    deps = [
        ":portfolio_main_lib",
    ],
)

# Test targets
pytest_test(
    name = "test_execution",
    size = "small",
    coverage_path = "system.algo_trader.backtest.core.execution",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/backtest/core:test_execution_lib",
)

pytest_test(
    name = "test_results",
    size = "small",
    coverage_path = "system.algo_trader.backtest.results.writer",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/backtest/results:test_results_lib",
)

pytest_test(
    name = "test_engine",
    size = "small",
    coverage_path = "system.algo_trader.backtest.engine",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/backtest:test_engine_lib",
)

pytest_test(
    name = "test_main",
    size = "medium",
    coverage_path = "system.algo_trader.backtest.main",
    tags = [
        "e2e",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/backtest:test_main_lib",
)

pytest_test(
    name = "test_processor",
    size = "small",
    coverage_path = "system.algo_trader.backtest.processor.processor",
    tags = [
        "exclusive",
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/backtest/processor:test_processor_lib",
)

pytest_test(
    name = "test_worker",
    size = "small",
    coverage_path = "system.algo_trader.backtest.processor.worker",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/backtest/processor:test_worker_lib",
)

pytest_test(
    name = "test_results_generator",
    size = "small",
    coverage_path = "system.algo_trader.backtest.core.results_generator",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/backtest/core:test_results_generator_lib",
)

pytest_test(
    name = "test_writer",
    size = "small",
    coverage_path = "system.algo_trader.backtest.results.writer",
    tags = [
        "integration",
        "unit",
    ],
    test_lib = "//tests/system/algo_trader/backtest/results:test_writer_lib",
)

pytest_test(
    name = "test_schema",
    size = "small",
    coverage_path = "system.algo_trader.backtest.results.schema",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/backtest/results:test_schema_lib",
)

pytest_test(
    name = "test_utils",
    size = "small",
    coverage_path = "system.algo_trader.backtest.utils.utils",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/backtest/utils:test_utils_lib",
)

pytest_test(
    name = "test_cli_utils",
    size = "small",
    coverage_path = "system.algo_trader.backtest.cli_utils",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/backtest:test_cli_utils_lib",
)
