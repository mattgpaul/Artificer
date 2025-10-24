load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "influxdb",
    srcs = ["influxdb.py"],
    visibility = ["//visibility:public"],
    deps = [
        "//infrastructure:client",
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
