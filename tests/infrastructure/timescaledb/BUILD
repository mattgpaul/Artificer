load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_timescaledb_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_timescaledb.py",
    ],
    visibility = ["//infrastructure/timescaledb:__pkg__"],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/timescaledb",
    ],
)
