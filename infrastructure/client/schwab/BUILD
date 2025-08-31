load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schwab",
    srcs = [
        "schwab_client.py",
        "market_handler.py", 
        "account_handler.py",  # when you build it
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
    srcs = ["market_handler.py"],
    deps = [":schwab"],
    main = "market_handler.py",
)

py_binary(
    name = "test_account_handler",
    srcs = ["account_handler.py"],
    deps = [":schwab"],
    main = "account_handler.py",
)