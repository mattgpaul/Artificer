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
        "//system/trader:schema",
    ],
    visibility = [
        "//system/trader:__subpackages__",
    ],
)