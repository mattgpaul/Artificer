load("@pip//:requirements.bzl", "requirement")  # @unused
load("//:pytest_test.bzl", "pytest_test")

# buildifier: disable=native-sh-binary
sh_binary(
    name = "exec",
    srcs = ["redis_cli.sh"],
    visibility = ["//visibility:public"],
)

py_library(
    name = "redis_services",
    srcs = [
        "account.py",
        "historical_market.py",
        "live_market.py",
        "queue_broker.py",
        "watchlist.py",
    ],
    visibility = [
        "//system:__pkg__",  # Allow system package access
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/datasource/populate:__pkg__",  # Allow populate test access
        "//tests/system/algo_trader/mysql:__pkg__",  # Allow mysql test access
        "//tests/system/algo_trader/redis:__pkg__",  # Allow test access
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/redis",
        "//system/algo_trader/utils:schema",
    ],
)

py_library(
    name = "live_market",
    srcs = ["live_market.py"],
    visibility = ["//visibility:public"],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/redis",
    ],
)

# Test for AccountBroker - OAuth2 Token Management
pytest_test(
    name = "test_account",
    size = "small",
    coverage_path = "system.algo_trader.redis",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/redis:test_account_lib",
)

# Test for HistoricalMarketBroker - Historical Data Management
pytest_test(
    name = "test_historical_market",
    size = "small",
    coverage_path = "system.algo_trader.redis",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/redis:test_historical_market_lib",
)

# Test for LiveMarketBroker - Live Quote Management
pytest_test(
    name = "test_live_market",
    size = "small",
    coverage_path = "system.algo_trader.redis",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/redis:test_live_market_lib",
)

# Test for WatchlistBroker - Watchlist Management
pytest_test(
    name = "test_watchlist",
    size = "small",
    coverage_path = "system.algo_trader.redis",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/redis:test_watchlist_lib",
)
