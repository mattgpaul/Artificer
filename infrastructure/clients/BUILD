load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis_client",
    srcs = ["redis_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("redis"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "schwab_client",
    srcs = ["schwab_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "influx_client",
    srcs = ["influx_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
        requirement("pandas"),
        requirement("influxdb3-python"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "schwab_authenticate",
    srcs = ["schwab_client.py"],
    main = "schwab_client.py",
    deps = [
        ":schwab_client",
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "influx_authenticate",
    srcs = ["influx_client.py"],
    main = "influx_client.py",
    deps = [
        ":influx_client",
    ],
    visibility = ["//visibility:public"]
)

##### Unit tests #####
pytest_test(
    name = "influx_client_test_unit", 
    srcs = ["influx_client_test.py"],
    coverage_path = "infrastructure.clients.influx_client",
    deps = [
        ":influx_client",
        requirement("requests"),
    ],
    python_version = "PY3",
    tags = [
        "infrastructure", 
        "algo-trader",
        "unit",
    ],
    args = ["-k", "TestInfluxDBClientUnit"],
    size = "small",
    visibility = ["//visibility:public"],
)

##### Integration tests #####
pytest_test(
    name = "influx_client_test_integration", 
    srcs = ["influx_client_test.py"],
    coverage_path = "infrastructure.clients.influx_client",
    deps = [
        ":influx_client",
        requirement("requests"),
    ],
    python_version = "PY3",
    tags = [
        "infrastructure", 
        "algo-trader",
        "integration",
    ],
    args = ["-k", "TestInfluxDBClientIntegration"],
    size = "medium",
    visibility = ["//visibility:public"],
)
