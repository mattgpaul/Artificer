load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "test_prometheus_config_lib",
    testonly = True,
    srcs = ["test_prometheus_config.py"],
    visibility = ["//system/telemetry:__pkg__"],
    deps = [
        requirement("pyyaml"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_grafana_assets_lib",
    testonly = True,
    srcs = ["test_grafana_assets.py"],
    visibility = ["//system/telemetry:__pkg__"],
    deps = [
        requirement("pyyaml"),
        requirement("pytest"),
    ],
)

pytest_test(
    name = "test_prometheus_config",
    coverage_path = "system.telemetry",
    tags = ["unit"],
    test_lib = ":test_prometheus_config_lib",
)

pytest_test(
    name = "test_grafana_assets",
    coverage_path = "system.telemetry",
    tags = ["unit"],
    test_lib = ":test_grafana_assets_lib",
)
