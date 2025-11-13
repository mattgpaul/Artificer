load("@rules_python//python:defs.bzl", "py_library")

# Test library for BadTickerClient
py_library(
    name = "test_bad_ticker_client_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_bad_ticker_client.py",
    ],
    visibility = ["//system/algo_trader/sqlite:__pkg__"],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/sqlite",
        "//system/algo_trader/sqlite:bad_ticker_client",
    ],
)

# Test library for BadTickerDaemon
py_library(
    name = "test_bad_ticker_daemon_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_bad_ticker_daemon.py",
    ],
    visibility = ["//system/algo_trader/sqlite:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/sqlite:bad_ticker_client",
        "//system/algo_trader/sqlite:bad_ticker_daemon_lib",
    ],
)

# Test library for FundamentalsClient
py_library(
    name = "test_fundamentals_client_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_fundamentals_client.py",
    ],
    visibility = ["//system/algo_trader/sqlite:__pkg__"],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/sqlite",
        "//system/algo_trader/sqlite:fundamentals_client",
    ],
)

# Test library for FundamentalsDaemon
py_library(
    name = "test_fundamentals_daemon_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_fundamentals_daemon.py",
    ],
    visibility = ["//system/algo_trader/sqlite:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/sqlite:fundamentals_client",
        "//system/algo_trader/sqlite:fundamentals_daemon_lib",
    ],
)
