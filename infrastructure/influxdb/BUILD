load("@pip//:requirements.bzl", "requirement")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "influxdb",
    srcs = ["influxdb.py"],
    visibility = ["//visibility:public"],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        requirement("requests"),
        requirement("pandas"),
        requirement("influxdb3-python"),
    ],
)

py_binary(
    name = "influxdb_authenticate",
    srcs = ["influxdb.py"],
    main = "influxdb.py",
    visibility = ["//visibility:public"],
    deps = [
        ":influxdb",
    ],
)

# Test target
pytest_test(
    name = "test_influxdb",
    coverage_path = "infrastructure.influxdb",
    tags = ["unit"],
    test_lib = "//tests/infrastructure/influxdb:test_influxdb_lib",
)

oci_image(
    name = "influxdb3_image_lib",
    base = "@influxdb3//:influxdb3",
)

oci_load(
    name = "influxdb3_image",
    image = ":influxdb3_image_lib",
    repo_tags = ["artificer-influxdb:latest"],
)

# Tarball for release distribution
genrule(
    name = "influxdb3_tarball",
    srcs = [],
    outs = ["artificer-influxdb.tar"],
    cmd = "$(location :influxdb3_image) && docker save artificer-influxdb:latest -o $@",
    tags = ["release"],
    tools = [":influxdb3_image"],
)
