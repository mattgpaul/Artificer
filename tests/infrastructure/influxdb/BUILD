load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_influxdb_lib",
    testonly = True,
    srcs = ["test_influxdb.py"],
    visibility = ["//infrastructure/influxdb:__pkg__"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
    ],
)
