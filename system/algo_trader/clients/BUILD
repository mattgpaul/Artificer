load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "redis_client",
    srcs = ["redis_client.py"],
    deps = [
        "//infrastructure/clients:redis_client",
        "//infrastructure/logging:logger",
    ],
    visibility = ["//system/algo_trader:__subpackages__"],
)

py_library(
    name = "schwab_client",
    srcs = ["schwab_client.py"],
    deps = [
        ":redis_client",
        "//infrastructure/clients:schwab_client",
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//system/algo_trader:__subpackages__"],
)

py_library(
    name = "influxdb_client",
    srcs = ["influxdb_client.py"],
    deps = [
        "//infrastructure/clients:influxdb_client",
        "//infrastructure/logging:logger",
        requirement("influxdb3-python"),
    ],
    visibility = ["//system/algo_trader:__subpackages__"],
)

py_library(
    name = "grafana_client",
    srcs = ["grafana_client.py"],
    deps = [
        "//infrastructure/clients:grafana_client",
        "//infrastructure/logging:logger",
    ],
    visibility = ["//system/algo_trader:__subpackages__"],
)

# InfluxDB client as executable for container management
py_binary(
    name = "influxdb",
    srcs = ["influxdb_client.py"],
    main = "influxdb_client.py",
    deps = [
        ":influxdb_client",
    ],
    visibility = ["//visibility:public"],
)

# Grafana client as executable for container management
py_binary(
    name = "grafana",
    srcs = ["grafana_client.py"],
    main = "grafana_client.py",
    deps = [
        "//infrastructure/clients:grafana_client",
        "//infrastructure/logging:logger",
    ],
    data = [
        "//system/algo_trader/grafana:dashboard_json",
    ],
    visibility = ["//visibility:public"],
)

# Unit tests
pytest_test(
    name = "redis_client_test_unit",
    srcs = ["redis_client_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.clients.redis_client",
    deps = [
        ":redis_client",
    ],
)

pytest_test(
    name = "schwab_client_test_unit",
    srcs = ["schwab_client_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.clients.schwab_client",
    deps = [
        ":schwab_client",
        ":redis_client",
    ],
)

# Integration tests
pytest_test(
    name = "schwab_client_test_integration",
    srcs = ["schwab_client_test.py"],
    args = ["-m", "integration"],
    tags = ["integration"],
    coverage_path = "system.algo_trader.clients.schwab_client",
    deps = [
        ":schwab_client",
        ":redis_client",
    ],
)

# InfluxDB Client Tests
pytest_test(
    name = "influxdb_client_test_unit",
    srcs = ["influxdb_client_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.clients.influxdb_client",
    deps = [
        ":influxdb_client",
        requirement("requests"),
    ],
)

pytest_test(
    name = "influxdb_client_test_integration",
    srcs = ["influxdb_client_test.py"],
    args = ["-m", "integration"],
    tags = ["integration"],
    coverage_path = "system.algo_trader.clients.influxdb_client",
    deps = [
        ":influxdb_client",
        requirement("requests"),
    ],
)

# Grafana Client Tests
pytest_test(
    name = "grafana_client_test_unit",
    srcs = ["grafana_client_test.py"],
    args = ["-m", "unit"],
    tags = ["unit"],
    coverage_path = "system.algo_trader.clients.grafana_client",
    data = [
        "//system/algo_trader/grafana:dashboard_json",
    ],
    deps = [
        ":grafana_client",
    ],
)

pytest_test(
    name = "grafana_client_test_integration",
    srcs = ["grafana_client_test.py"],
    args = ["-m", "integration"],
    tags = ["integration"],
    coverage_path = "system.algo_trader.clients.grafana_client",
    deps = [
        ":grafana_client",
    ],
)

