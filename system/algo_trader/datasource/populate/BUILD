load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "populate_lib",
    srcs = [
        "argument_base.py",
        "fundamentals.py",
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
        "//system/algo_trader/datasource/populate:utils",
        "//system/algo_trader/datasource/sec:tickers_lib",
        "//system/algo_trader/influx:influx_services",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
        "//system/algo_trader/mysql:bad_ticker_client",
        "//system/algo_trader/mysql:fundamentals_client",
        requirement("pandas"),
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
