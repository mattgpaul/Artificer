load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schwab_services",
    srcs = [
        "schwab_client.py",
        "market_handler.py",
        "account_handler.py",
        "timescale_enum.py",
    ],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
        requirement("requests"),
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
        "//tests:__subpackages__",  # Allow test access
    ],
)
