load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis_services",
    srcs = [
        "account.py",
        "historical_market.py",
        "live_market.py",
        "watchlist.py",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/redis:redis",
        "//system/algo_trader/utils:schema",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
        "//tests/system/algo_trader/redis:__pkg__",  # Allow test access
    ],
)

py_library(
    name = "live_market",
    srcs = ["live_market.py"],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/redis:redis",
    ],
    visibility = ["//visibility:public"],
)

# Test for AccountBroker - OAuth2 Token Management
pytest_test(
    name = "test_account",
    test_lib = "//tests/system/algo_trader/redis:test_account_lib",
    coverage_path = "system.algo_trader.redis",
    size = "small",
    tags = ["unit"],
)

# Test for HistoricalMarketBroker - Historical Data Management
pytest_test(
    name = "test_historical_market",
    test_lib = "//tests/system/algo_trader/redis:test_historical_market_lib",
    coverage_path = "system.algo_trader.redis",
    size = "small",
    tags = ["unit"],
)

# Test for LiveMarketBroker - Live Quote Management
pytest_test(
    name = "test_live_market",
    test_lib = "//tests/system/algo_trader/redis:test_live_market_lib",
    coverage_path = "system.algo_trader.redis",
    size = "small",
    tags = ["unit"],
)

# Test for WatchlistBroker - Watchlist Management
pytest_test(
    name = "test_watchlist",
    test_lib = "//tests/system/algo_trader/redis:test_watchlist_lib",
    coverage_path = "system.algo_trader.redis",
    size = "small",
    tags = ["unit"],
)