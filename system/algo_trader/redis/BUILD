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
        "//infrastructure/redis:redis",
        "//system/algo_trader/utils:schema",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
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