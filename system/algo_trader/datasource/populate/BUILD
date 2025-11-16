load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "argument_base",
    srcs = ["argument_base.py"],
    visibility = [
        "//system/algo_trader/datasource:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",
    ],
    deps = [
        "//infrastructure/logging:logger",
    ],
)

py_library(
    name = "populate_lib",
    srcs = [
        "argument_base.py",
        "main.py",
    ],
    visibility = [
        "//system/algo_trader/datasource:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__subpackages__",
    ],
    deps = [
        ":argument_base",
        ":utils",
        "//infrastructure/logging:logger",
        "//system/algo_trader/datasource/populate/fundamentals:fundamentals_lib",
        "//system/algo_trader/datasource/populate/ohlcv:ohlcv_lib",
        "//system/algo_trader/datasource/sec:tickers_lib",
    ],
)

py_library(
    name = "utils",
    srcs = ["utils/market_cap.py"],
    visibility = [
        "//system/algo_trader/datasource:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:market_data_influx",
        requirement("pandas"),
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
    coverage_path = "system.algo_trader.datasource.populate.ohlcv",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/datasource/populate:test_ohlcv_args_lib",
)

pytest_test(
    name = "test_ohlcv_processor",
    size = "medium",
    coverage_path = "system.algo_trader.datasource.populate.ohlcv.processor",
    tags = ["unit", "integration"],
    test_lib = "//tests/system/algo_trader/datasource/populate/ohlcv:test_processor_lib",
)

pytest_test(
    name = "test_ohlcv_handler",
    size = "medium",
    coverage_path = "system.algo_trader.datasource.populate.ohlcv.handler",
    tags = ["unit", "e2e"],
    test_lib = "//tests/system/algo_trader/datasource/populate/ohlcv:test_handler_lib",
)

pytest_test(
    name = "test_main",
    size = "medium",
    coverage_path = "system.algo_trader.datasource.populate.main",
    tags = ["integration"],
    test_lib = "//tests/system/algo_trader/datasource/populate:test_main_lib",
)

pytest_test(
    name = "test_market_cap",
    size = "small",
    coverage_path = "system.algo_trader.datasource.populate.utils.market_cap",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/datasource/populate:test_market_cap_lib",
)

pytest_test(
    name = "test_fundamentals",
    size = "medium",
    coverage_path = "system.algo_trader.datasource.populate.fundamentals",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/datasource/populate:test_fundamentals_lib",
)

pytest_test(
    name = "test_fundamentals_handler",
    size = "medium",
    coverage_path = "system.algo_trader.datasource.populate.fundamentals.handler",
    tags = ["unit", "e2e"],
    test_lib = "//tests/system/algo_trader/datasource/populate/fundamentals:test_handler_lib",
)
