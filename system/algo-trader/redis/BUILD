load("@pip//:requirements.bzl", "requirement")

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
        "//infrastructure/clients:redis_client",
        "//system/algo-trader/utils:schema",
    ],
    visibility = [
        "//system/algo-trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
    ],
)