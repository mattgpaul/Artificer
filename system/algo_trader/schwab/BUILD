load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "schwab_services",
    srcs = [
        "account_handler.py",
        "market_handler.py",
        "schwab_client.py",
        "timescale_enum.py",
    ],
    visibility = [
        "//system:__pkg__",  # Allow system package access
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",  # Allow test access
    ],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        "//system/algo_trader/infra/redis:redis_services",
        "//system/algo_trader/schwab/auth",
        requirement("requests"),
    ],
)

# OAuth2 authentication binary
py_binary(
    name = "authenticate",
    srcs = ["authenticate.py"],
    main = "authenticate.py",
    visibility = ["//visibility:public"],
    deps = [":schwab_services"],
)

# Test for SchwabClient - OAuth2 and Token Management
pytest_test(
    name = "test_schwab_client",
    size = "small",
    coverage_path = "system.algo_trader.schwab",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/schwab:test_schwab_client_lib",
)

# Test for MarketHandler - Market data operations
pytest_test(
    name = "test_market_handler",
    size = "small",
    coverage_path = "system.algo_trader.schwab",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/schwab:test_market_handler_lib",
)

# Test for AccountHandler - Account API operations
pytest_test(
    name = "test_account_handler",
    size = "small",
    coverage_path = "system.algo_trader.schwab",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/schwab:test_account_handler_lib",
)

# Test for Timescale Enums - Period and Frequency validation
pytest_test(
    name = "test_timescale_enum",
    size = "small",
    coverage_path = "system.algo_trader.schwab",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/schwab:test_timescale_enum_lib",
)
