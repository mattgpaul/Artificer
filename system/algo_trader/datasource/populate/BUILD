load("@rules_python//python:defs.bzl", "py_binary", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "populate_lib",
    srcs = [
        "argument_base.py",
        "main.py",
        "ohlcv_args.py",
    ],
    visibility = [
        "//system/algo_trader/datasource:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/threads:thread_manager",
        "//system/algo_trader:config",
        "//system/algo_trader/datasource/sec:tickers_lib",
        "//system/algo_trader/influx:influx_services",
        "//system/algo_trader/schwab:schwab_services",
    ],
)

py_binary(
    name = "main",
    srcs = ["main.py"],
    main = "main.py",
    visibility = [
        "//system/algo_trader/datasource:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",
    ],
    deps = [":populate_lib"],
)

# Test targets
pytest_test(
    name = "test_argument_base",
    size = "small",
    coverage_path = "system.algo_trader.datasource.populate.argument_base",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/datasource/populate:test_argument_base_lib",
)

pytest_test(
    name = "test_ohlcv_args",
    size = "small",
    coverage_path = "system.algo_trader.datasource.populate.ohlcv_args",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/datasource/populate:test_ohlcv_args_lib",
)

pytest_test(
    name = "test_main",
    size = "medium",
    coverage_path = "system.algo_trader.datasource.populate.main",
    tags = ["integration"],
    test_lib = "//tests/system/algo_trader/datasource/populate:test_main_lib",
)
