load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "backtest_lib",
    srcs = [
        "core/data_loader.py",
        "core/execution.py",
        "core/results_generator.py",
        "core/signal_collector.py",
        "core/time_stepper.py",
        "engine.py",
        "processor/parallel.py",
        "processor/processor.py",
        "processor/sequential.py",
        "processor/worker.py",
        "results/hash.py",
        "results/results.py",
        "results/writer.py",
        "utils/progress.py",
        "utils/strategy_wrapper.py",
        "utils/utils.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/backtest:__subpackages__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/multiprocess:process_manager",
        "//system/algo_trader/influx:market_data_influx",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/strategy:cli_utils",
        "//system/algo_trader/strategy:strategies",
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
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:cli_utils",
        "//system/algo_trader/strategy:strategies",
        requirement("pandas"),
    ],
    # Note: main.py imports from subdirectories via backtest_lib
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
    name = "test_execution",
    size = "small",
    coverage_path = "system.algo_trader.backtest.core.execution",
    test_lib = "//tests/system/algo_trader/backtest/core:test_execution_lib",
)

pytest_test(
    name = "test_results",
    size = "small",
    coverage_path = "system.algo_trader.backtest.results.writer",
    test_lib = "//tests/system/algo_trader/backtest/results:test_results_lib",
)

pytest_test(
    name = "test_engine",
    size = "small",
    coverage_path = "system.algo_trader.backtest.engine",
    test_lib = "//tests/system/algo_trader/backtest:test_engine_lib",
)

pytest_test(
    name = "test_processor",
    size = "small",
    coverage_path = "system.algo_trader.backtest.processor.processor",
    tags = ["exclusive"],
    test_lib = "//tests/system/algo_trader/backtest/processor:test_processor_lib",
)
