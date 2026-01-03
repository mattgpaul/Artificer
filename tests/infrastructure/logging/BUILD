load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_logger_lib",
    testonly = True,
    srcs = ["test_logger.py"],
    visibility = ["//infrastructure/logging:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
    ],
)
