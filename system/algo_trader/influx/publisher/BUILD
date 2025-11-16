load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "publisher_modules",
    srcs = [
        "config.py",
        "queue_processor.py",
    ],
    visibility = [
        "//system/algo_trader/influx:__pkg__",
        "//tests/system/algo_trader/influx:__subpackages__",
    ],
    deps = [
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/influx:market_data_influx",
        "//system/algo_trader/redis:redis_services",
        requirement("pyyaml"),
    ],
)

py_library(
    name = "publisher_service",
    srcs = [
        "publisher.py",
    ],
    visibility = [
        "//system/algo_trader/influx:__pkg__",
        "//tests/system/algo_trader/influx:__subpackages__",
    ],
    deps = [
        ":publisher_modules",
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
        requirement("pyyaml"),
    ],
)

# Test targets
pytest_test(
    name = "test_queue_processor",
    size = "medium",
    coverage_path = "system.algo_trader.influx.publisher.queue_processor",
    tags = ["unit", "integration"],
    test_lib = "//tests/system/algo_trader/influx/publisher:test_queue_processor_lib",
)

pytest_test(
    name = "test_config",
    size = "small",
    coverage_path = "system.algo_trader.influx.publisher.config",
    tags = ["unit"],
    test_lib = "//tests/system/algo_trader/influx/publisher:test_config_lib",
)

pytest_test(
    name = "test_main",
    size = "medium",
    coverage_path = "system.algo_trader.influx.publisher.__main__",
    tags = ["unit", "e2e"],
    test_lib = "//tests/system/algo_trader/influx/publisher:test_main_lib",
)

pytest_test(
    name = "test_publisher",
    size = "medium",
    coverage_path = "system.algo_trader.influx.publisher.publisher",
    tags = ["unit", "integration"],
    test_lib = "//tests/system/algo_trader/influx/publisher:test_publisher_lib",
)
