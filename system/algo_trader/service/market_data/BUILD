load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("//:pytest_test.bzl", "pytest_test")

py_binary(
    name = "main",
    srcs = ["main.py"],
    main = "main.py",
    visibility = [
        "//system/algo_trader/service:__pkg__",
        "//tests/system/algo_trader/service:__pkg__",
    ],
    deps = [":market_data_lib"],
)

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
        "//tests/system/algo_trader/service:__pkg__",
        "//tests/system/algo_trader/service/market_data:__pkg__",
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
    coverage_path = "system.algo_trader.service.market_data.base",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/service/market_data:test_base_lib",
)

pytest_test(
    name = "test_live",
    size = "small",
    coverage_path = "system.algo_trader.service.market_data.live",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/service/market_data:test_live_lib",
)

pytest_test(
    name = "test_historical",
    size = "small",
    coverage_path = "system.algo_trader.service.market_data.historical",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/service/market_data:test_historical_lib",
)

# Test target for market data service CLI
pytest_test(
    name = "test_market_data",
    size = "medium",
    coverage_path = "system.algo_trader.service.market_data",
    tags = ["integration"],
    test_lib = "//tests/system/algo_trader/service:test_market_data_lib",
)
