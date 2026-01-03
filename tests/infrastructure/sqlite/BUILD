load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_sqlite_lib",
    testonly = True,
    srcs = ["test_sqlite.py"],
    visibility = ["//infrastructure/sqlite:__pkg__"],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/sqlite",
    ],
)
