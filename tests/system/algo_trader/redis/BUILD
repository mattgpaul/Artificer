load("@rules_python//python:defs.bzl", "py_library")

# Test library for AccountBroker
py_library(
    name = "test_account_lib",
    srcs = ["test_account.py"],
    deps = [
        "//system/algo_trader/redis:redis_services",
        "//infrastructure/redis:redis",
        "//infrastructure/logging:logger",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/redis:__pkg__"],
)

# Test library for HistoricalMarketBroker
py_library(
    name = "test_historical_market_lib",
    srcs = ["test_historical_market.py"],
    deps = [
        "//system/algo_trader/redis:redis_services",
        "//infrastructure/redis:redis",
        "//infrastructure/logging:logger",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/redis:__pkg__"],
)

# Test library for LiveMarketBroker
py_library(
    name = "test_live_market_lib",
    srcs = ["test_live_market.py"],
    deps = [
        "//system/algo_trader/redis:redis_services",
        "//infrastructure/redis:redis",
        "//infrastructure/logging:logger",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/redis:__pkg__"],
)

# Test library for WatchlistBroker
py_library(
    name = "test_watchlist_lib",
    srcs = ["test_watchlist.py"],
    deps = [
        "//system/algo_trader/redis:redis_services",
        "//infrastructure/redis:redis",
        "//infrastructure/logging:logger",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/redis:__pkg__"],
)

