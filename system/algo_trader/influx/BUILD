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
    name = "historical_influx_handler_test_unit",
    srcs = ["historical_influx_handler_test.py"],
    deps = [
        ":historical_influx_handler",
    ],
    python_version = "PY3",
    tags = [
        "algo_trader", 
        "unit",
    ],
    args = ["-k", "TestHistoricalInfluxHandlerUnit"],
    size = "small",
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
)

pytest_test(
    name = "historical_influx_handler_test_integration",
    srcs = ["historical_influx_handler_test.py"],
    deps = [
        ":historical_influx_handler",
    ],
    python_version = "PY3",
    tags = [
        "algo_trader", 
        "integration",
    ],
    args = ["-k", "TestHistoricalInfluxHandlerIntegration"],
    size = "medium",
    visibility = [
        "//system/algo_trader:__subpackages__",
    ],
)