load("@rules_python//python:defs.bzl", "py_library")

# Test library for AccountBroker
py_library(
    name = "test_account_lib",
    testonly = True,
    srcs = ["test_account.py"],
    visibility = ["//system/algo_trader/redis:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/redis",
        "//system/algo_trader/redis:redis_services",
    ],
)

# Test library for HistoricalMarketBroker
py_library(
    name = "test_historical_market_lib",
    testonly = True,
    srcs = ["test_historical_market.py"],
    visibility = ["//system/algo_trader/redis:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/redis",
        "//system/algo_trader/redis:redis_services",
    ],
)

# Test library for LiveMarketBroker
py_library(
    name = "test_live_market_lib",
    testonly = True,
    srcs = ["test_live_market.py"],
    visibility = ["//system/algo_trader/redis:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/redis",
        "//system/algo_trader/redis:redis_services",
    ],
)

# Test library for WatchlistBroker
py_library(
    name = "test_watchlist_lib",
    testonly = True,
    srcs = ["test_watchlist.py"],
    visibility = ["//system/algo_trader/redis:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/redis",
        "//system/algo_trader/redis:redis_services",
    ],
)

# Test library for check_queues
py_library(
    name = "test_check_queues_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_check_queues.py",
    ],
    visibility = ["//system/algo_trader/redis:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
    ],
)
