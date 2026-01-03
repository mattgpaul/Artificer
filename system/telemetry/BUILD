# BUILD file for telemetry monitoring system
# This package contains Prometheus configs, Grafana provisioning, and Docker Compose setup

filegroup(
    name = "prometheus_config",
    srcs = glob([
        "prometheus/**/*.yml",
        "prometheus/**/*.yaml",
    ]),
    visibility = ["//tests/system/telemetry:__pkg__"],
)

filegroup(
    name = "grafana_provisioning",
    srcs = glob([
        "grafana/provisioning/**/*.yaml",
        "grafana/provisioning/**/*.json",
    ]),
    visibility = ["//tests/system/telemetry:__pkg__"],
)

filegroup(
    name = "docker_compose",
    srcs = ["ops/docker-compose.yaml"],
    visibility = ["//visibility:public"],
)

