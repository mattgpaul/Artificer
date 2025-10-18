load("@pip//:requirements.bzl", "requirement")

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
        requirement("python-dotenv"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "influxdb_client",
    srcs = ["influxdb_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("influxdb3-python"),
        requirement("pandas"),
        requirement("requests"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "grafana_client",
    srcs = ["grafana_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//visibility:public"],
)

# InfluxDB client as executable for container management
py_binary(
    name = "influxdb",
    srcs = ["influxdb_client.py"],
    main = "influxdb_client.py",
    deps = [
        ":influxdb_client",
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("influxdb3-python"),
        requirement("pandas"),
        requirement("requests"),
    ],
    visibility = ["//visibility:public"],
)

# Grafana Client Tests
load("//:pytest_test.bzl", "pytest_test")

pytest_test(
    name = "grafana_client_test_unit",
    srcs = ["grafana_client_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "infrastructure.clients.grafana_client",
    deps = [
        ":grafana_client",
    ],
)