load("@pip//:requirements.bzl", "requirement")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "timescaledb",
    srcs = ["timescaledb.py"],
    visibility = [
        "//tests/infrastructure/timescaledb:__pkg__",
        "//visibility:public",
    ],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        requirement("psycopg2"),
    ],
)

oci_image(
    name = "timescaledb_image_lib",
    base = "@timescaledb//:timescaledb",
)

oci_load(
    name = "timescaledb_image",
    image = ":timescaledb_image_lib",
    repo_tags = ["artificer-timescaledb:latest"],
)

pytest_test(
    name = "test_timescaledb",
    coverage_path = "infrastructure.timescaledb",
    tags = ["unit"],
    test_lib = "//tests/infrastructure/timescaledb:test_timescaledb_lib",
)
