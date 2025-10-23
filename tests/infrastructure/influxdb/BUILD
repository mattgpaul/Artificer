load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_influxdb_lib",
    srcs = ["test_influxdb.py"],
    deps = [
        "//infrastructure/influxdb:influxdb",
        "//infrastructure:client",
        "//infrastructure/logging:logger",
    ],
    testonly = True,
    visibility = ["//infrastructure/influxdb:__pkg__"],
)

