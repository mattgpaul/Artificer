load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_logger_lib",
    srcs = ["test_logger.py"],
    deps = [
        "//infrastructure/logging:logger",
    ],
    testonly = True,
    visibility = ["//infrastructure/logging:__pkg__"],
)

