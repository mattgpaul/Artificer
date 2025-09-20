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

pytest_test(
    name = "influx_client_test", 
    srcs = ["influx_client_test.py"],
    coverage_path = "infrastructure.clients.influx_client",
    deps = [
        ":influx_client",
        requirement("requests"),
    ],
    env = {
        "INFLUXDB3_AUTH_TOKEN": "test_token",
        "INFLUXDB3_HTTP_BIND_ADDR": "http://test-url:test-port",
    },
    python_version = "PY3",
    tags = [
        "infrastructure", 
        "algo-trader",
    ],
    visibility = ["//visibility:public"],
)
