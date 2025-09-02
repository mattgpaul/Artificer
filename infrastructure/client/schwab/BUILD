load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schwab",
    srcs = [
        "schwab_client.py",
        "services/market_handler.py",
        "services/account_handler.py",
        "services/timescale_enum.py",
    ],
    deps = [
        "//infrastructure/client:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
        requirement("python-dotenv"),
    ],
    visibility = [
        "//infrastructure/client:__subpackages__",
        "//component/software/finance:__subpackages__",
        "//system:__subpackages__",
    ],
)

py_binary(
    name = "test_market_handler",
    srcs = ["services/market_handler.py"],
    deps = [":schwab"],
    main = "services/market_handler.py",
)

py_binary(
    name = "test_account_handler",
    srcs = ["services/account_handler.py"],
    deps = [":schwab"],
    main = "services/account_handler.py",
)

