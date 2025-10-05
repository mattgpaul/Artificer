load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "market_data_influx",
    srcs = ["market_data_influx.py"],
    deps = [
        "//infrastructure/clients:influx_client",
        "//infrastructure/logging:logger",
        requirement("pandas"),
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
)

pytest_test(
    name = "market_data_influx_test",
    srcs = ["market_data_influx_test.py"],
    deps = [
        ":market_data_influx",
    ],
    python_version = "PY3",
    tags = [
        "algo_trader", 
        "integration",
    ],
    args = ["-k", "TestMarketDataInflux"],
    size = "medium",
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
)