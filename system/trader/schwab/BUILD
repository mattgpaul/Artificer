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
        requirement("requests"),
    ],
    visibility = [
        "//system/trader:__subpackages__",
        "//visibility:public",
    ],
)

py_binary(
    name = "test_market_handler",
    srcs = ["market_handler.py"],
    deps = [":schwab_services"],
    main = "market_handler.py",
)
