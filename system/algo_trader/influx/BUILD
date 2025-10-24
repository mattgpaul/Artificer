load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "influx_services",
    srcs = [
        "market_data_influx.py",
    ],
    visibility = [
        "//system:__pkg__",  # Allow system package access
        "//system/algo_trader:__subpackages__",
    ],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/utils:schema",
    ],
)

py_library(
    name = "market_data_influx",
    srcs = ["market_data_influx.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/influx:__pkg__",
    ],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        requirement("pandas"),
    ],
)

# Test target
pytest_test(
    name = "test_market_data_influx",
    coverage_path = "system.algo_trader.influx",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/influx:test_market_data_influx_lib",
)
