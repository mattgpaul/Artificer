load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "influx_services",
    srcs = [
        "market_data_influx.py",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//infrastructure/influxdb:influxdb",
        "//system/algo_trader/utils:schema",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
    ],
)

py_library(
    name = "market_data_influx",
    srcs = ["market_data_influx.py"],
    deps = [
        "//infrastructure/influxdb:influxdb",
        "//infrastructure/logging:logger",
        requirement("pandas"),
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/influx:__pkg__",
    ],
)

# Test target
pytest_test(
    name = "test_market_data_influx",
    test_lib = "//tests/system/algo_trader/influx:test_market_data_influx_lib",
    coverage_path = "system.algo_trader.influx",
    tags = ["unit"],
)
