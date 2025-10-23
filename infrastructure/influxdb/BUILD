load("@pip//:requirements.bzl", "requirement")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "influxdb",
    srcs = ["influxdb.py"],
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
    name = "influxdb_authenticate",
    srcs = ["influxdb.py"],
    main = "influxdb.py",
    deps = [
        ":influxdb",
    ],
    visibility = ["//visibility:public"]
)

# Test target
pytest_test(
    name = "test_influxdb",
    test_lib = "//tests/infrastructure/influxdb:test_influxdb_lib",
    coverage_path = "infrastructure.influxdb",
    tags = ["unit"],
)
