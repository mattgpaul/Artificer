load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "historical_influx_handler",
    srcs = ["historical_influx_handler.py"],
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
    name = "historical_influx_handler_test",
    srcs = ["historical_influx_handler_test.py"],
    deps = [
        ":historical_influx_handler",
    ],
    python_version = "PY3",
    tags = [
        "algo_trader", 
        "integration",
    ],
    args = ["-k", "TestHistoricalInfluxHandler"],
    size = "medium",
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
)