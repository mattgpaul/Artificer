load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

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

# Test for SchwabClient - OAuth2 and Token Management
pytest_test(
    name = "test_schwab_client",
    test_lib = "//tests/system/algo_trader/schwab:test_schwab_client_lib",
    size = "small",
    coverage_path = "system.algo_trader.schwab",
    tags = ["unit"],
)

# Test for MarketHandler - Market data operations
pytest_test(
    name = "test_market_handler",
    test_lib = "//tests/system/algo_trader/schwab:test_market_handler_lib",
    size = "small",
    coverage_path = "system.algo_trader.schwab",
    tags = ["unit"],
)

# Test for AccountHandler - Account API operations
pytest_test(
    name = "test_account_handler",
    test_lib = "//tests/system/algo_trader/schwab:test_account_handler_lib",
    size = "small",
    coverage_path = "system.algo_trader.schwab",
    tags = ["unit"],
)

# Test for Timescale Enums - Period and Frequency validation
pytest_test(
    name = "test_timescale_enum",
    test_lib = "//tests/system/algo_trader/schwab:test_timescale_enum_lib",
    size = "small",
    coverage_path = "system.algo_trader.schwab",
    tags = ["unit"],
)
