load("@pip//:requirements.bzl", "requirement")

py_binary(
    name = "main",
    srcs = ["main.py"],
    deps = [
        "//system/algo_trader/clients:redis_client",
        "//system/algo_trader/clients:schwab_client",
        "//system/algo_trader/clients:influxdb_client",
        "//system/algo_trader/clients:grafana_client",
        "//system/algo_trader/datasources:sec",
        "//infrastructure/logging:logger",
    ],
    visibility = ["//visibility:public"],
)

# Shell script for Grafana management (deprecated - use docker-compose instead)
# Kept for backward compatibility during migration
sh_binary(
    name = "grafana_shell",
    srcs = ["run_grafana.sh"],
    data = ["//system/algo_trader/grafana:dashboard_json"],
    visibility = ["//visibility:public"],
)

