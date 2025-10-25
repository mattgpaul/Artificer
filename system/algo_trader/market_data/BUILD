load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "market_data_lib",
    srcs = [
        "base.py",
        "historical.py",
        "live.py",
    ],
    visibility = [
        "//system/algo_trader:__pkg__",
        "//system/algo_trader/service:__pkg__",
        "//tests/system/algo_trader/market_data:__pkg__",
        "//tests/system/algo_trader/service:__pkg__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader:config",
        "//system/algo_trader/influx:influx_services",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
        "//system/algo_trader/utils:schema",
        requirement("pandas"),
        requirement("pydantic"),
    ],
)

# Test targets for market data components
pytest_test(
    name = "test_base",
    size = "small",
    coverage_path = "system.algo_trader.market_data.base",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/market_data:test_base_lib",
)

pytest_test(
    name = "test_live",
    size = "small",
    coverage_path = "system.algo_trader.market_data.live",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/market_data:test_live_lib",
)

pytest_test(
    name = "test_historical",
    size = "small",
    coverage_path = "system.algo_trader.market_data.historical",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/market_data:test_historical_lib",
)
