load("@pip//:requirements.bzl", "requirement")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("@rules_python//python:defs.bzl", "py_binary")
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

# InfluxDB Publisher binary
py_binary(
    name = "publisher",
    srcs = ["publisher.py"],
    data = ["publisher_config.yaml"],
    main = "publisher.py",
    visibility = ["//visibility:public"],
    deps = [
        ":market_data_influx",
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
        requirement("pyyaml"),
    ],
)

# OCI image for the publisher (base Python image)
# Note: The actual application code will be mounted as a volume in docker-compose
# This allows running the publisher via bazel inside the container
oci_image(
    name = "publisher_image_lib",
    base = "@python//:python",
)

oci_load(
    name = "publisher_image",
    image = ":publisher_image_lib",
    repo_tags = ["artificer-influx-publisher:latest"],
)
