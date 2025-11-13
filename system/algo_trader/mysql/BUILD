load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("@rules_python//python:defs.bzl", "py_binary")
load("//:pytest_test.bzl", "pytest_test")

# buildifier: disable=native-sh-binary
sh_binary(
    name = "exec",
    srcs = ["mysql_cli.sh"],
    visibility = ["//visibility:public"],
)

# buildifier: disable=native-sh-binary
sh_binary(
    name = "daemon-exec",
    srcs = ["mysql_daemon_cli.sh"],
    visibility = ["//visibility:public"],
)

py_library(
    name = "bad_ticker_client",
    srcs = ["bad_ticker_client.py"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",  # Allow populate test access
        "//tests/system/algo_trader/mysql:__pkg__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/mysql",
    ],
)

py_library(
    name = "fundamentals_client",
    srcs = ["fundamentals_client.py"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/mysql:__pkg__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/mysql",
    ],
)

py_library(
    name = "mysql_daemon_lib",
    srcs = ["mysql_daemon.py"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/mysql:__pkg__",
    ],
    deps = [
        ":bad_ticker_client",
        ":fundamentals_client",
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
    ],
)

py_binary(
    name = "mysql-daemon",
    srcs = ["mysql_daemon.py"],
    main = "mysql_daemon.py",
    visibility = ["//visibility:public"],
    deps = [":mysql_daemon_lib"],
)

# Test for BadTickerClient - Bad Ticker Tracking
pytest_test(
    name = "test_bad_ticker_client",
    size = "small",
    coverage_path = "system.algo_trader.mysql",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/mysql:test_bad_ticker_client_lib",
)

# Test for FundamentalsClient - Fundamentals Data Storage
pytest_test(
    name = "test_fundamentals_client",
    size = "small",
    coverage_path = "system.algo_trader.mysql.fundamentals_client",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/mysql:test_fundamentals_client_lib",
)

# Test for MySQLDaemon - MySQL Daemon
pytest_test(
    name = "test_mysql_daemon",
    size = "small",
    coverage_path = "system.algo_trader.mysql.mysql_daemon",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/mysql:test_mysql_daemon_lib",
)

oci_image(
    name = "mysql_daemon_image_lib",
    base = "@python//:python",
)

oci_load(
    name = "mysql_daemon_image",
    image = ":mysql_daemon_image_lib",
    repo_tags = ["artificer-mysql-daemon:latest"],
)
