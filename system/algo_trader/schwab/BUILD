load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schwab_services",
    srcs = [
        "market_handler.py",
        "account_handler.py",
        "timescale_enum.py",
    ],
    deps = [
        "//infrastructure/schwab:schwab",
        "//infrastructure/logging:logger",
        "//system/algo_trader/utils:schema"
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
    ],
)
