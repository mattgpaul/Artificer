load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schwab_services",
    srcs = [
        "market_handler.py",
        "account_handler.py",
        "timescale_enum.py",
    ],
    deps = [
        "//infrastructure/clients:schwab_client",
        "//infrastructure/logging:logger",
        "//system/algo-trader:schema"
    ],
    visibility = [
        "//system/algo-trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
    ],
)

# py_binary(
#     name = "test_market_handler",
#     srcs = ["market_handler.py"],
#     deps = [":schwab_services"],
#     main = "market_handler.py",
# )
