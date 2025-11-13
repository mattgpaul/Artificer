load("@rules_python//python:defs.bzl", "py_library")

# Test library for BadTickerClient
py_library(
    name = "test_bad_ticker_client_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_bad_ticker_client.py",
    ],
    visibility = ["//system/algo_trader/mysql:__pkg__"],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/mysql",
        "//system/algo_trader/mysql:bad_ticker_client",
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
    visibility = ["//system/algo_trader/mysql:__pkg__"],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/mysql",
        "//system/algo_trader/mysql:fundamentals_client",
    ],
)

# Test library for MySQLDaemon
py_library(
    name = "test_mysql_daemon_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_mysql_daemon.py",
    ],
    visibility = ["//system/algo_trader/mysql:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/mysql:mysql_daemon_lib",
        "//system/algo_trader/redis:redis_services",
    ],
)
