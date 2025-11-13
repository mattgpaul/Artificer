load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("@rules_python//python:defs.bzl", "py_binary")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "bad_ticker_client",
    srcs = ["bad_ticker_client.py"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",  # Allow populate test access
        "//tests/system/algo_trader/sqlite:__pkg__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/sqlite",
    ],
)

py_library(
    name = "fundamentals_client",
    srcs = ["fundamentals_client.py"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/sqlite:__pkg__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/sqlite",
    ],
)

py_library(
    name = "unified_sqlite_daemon_lib",
    srcs = ["unified_sqlite_daemon.py"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/sqlite:__pkg__",
    ],
    deps = [
        ":bad_ticker_client",
        ":fundamentals_client",
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
    ],
)

py_binary(
    name = "unified_sqlite_daemon",
    srcs = ["unified_sqlite_daemon.py"],
    main = "unified_sqlite_daemon.py",
    visibility = ["//visibility:public"],
    deps = [":unified_sqlite_daemon_lib"],
)

# Test for BadTickerClient - Bad Ticker Tracking
pytest_test(
    name = "test_bad_ticker_client",
    size = "small",
    coverage_path = "system.algo_trader.sqlite",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/sqlite:test_bad_ticker_client_lib",
)

# Test for FundamentalsClient - Fundamentals Data Storage
pytest_test(
    name = "test_fundamentals_client",
    size = "small",
    coverage_path = "system.algo_trader.sqlite.fundamentals_client",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/sqlite:test_fundamentals_client_lib",
)

oci_image(
    name = "sqlite_daemon_image_lib",
    base = "@python//:python",
)

oci_load(
    name = "sqlite_daemon_image",
    image = ":sqlite_daemon_image_lib",
    repo_tags = ["artificer-sqlite-daemon:latest"],
)
