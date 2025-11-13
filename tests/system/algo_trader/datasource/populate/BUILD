"""Build file for populate datasource tests."""

load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_argument_base_lib",
    testonly = True,
    srcs = ["test_argument_base.py"],
    visibility = ["//system/algo_trader/datasource/populate:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/datasource/populate:populate_lib",
    ],
)

py_library(
    name = "test_ohlcv_args_lib",
    testonly = True,
    srcs = ["test_ohlcv_args.py"],
    visibility = ["//system/algo_trader/datasource/populate:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/datasource/populate:populate_lib",
        "//system/algo_trader/schwab:schwab_services",
    ],
)

py_library(
    name = "test_main_lib",
    testonly = True,
    srcs = ["test_main.py"],
    visibility = ["//system/algo_trader/datasource/populate:__pkg__"],
    deps = [
        "//system/algo_trader/datasource/populate:main",
        "//system/algo_trader/datasource/populate:populate_lib",
    ],
)

# Test library for market_cap utils
py_library(
    name = "test_market_cap_lib",
    testonly = True,
    srcs = [
        "utils/conftest.py",
        "utils/test_market_cap.py",
    ],
    visibility = ["//system/algo_trader/datasource/populate:__pkg__"],
    deps = [
        "//system/algo_trader/datasource/populate:utils",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

# Test library for fundamentals
py_library(
    name = "test_fundamentals_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_fundamentals.py",
    ],
    visibility = ["//system/algo_trader/datasource/populate:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/threads:thread_manager",
        "//system/algo_trader/datasource/populate:populate_lib",
        "//system/algo_trader/datasource/sec:tickers_lib",
        "//system/algo_trader/mysql:bad_ticker_client",
        "//system/algo_trader/redis:redis_services",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
