load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_client_lib",
    srcs = ["test_client.py"],
    deps = [
        "//infrastructure:client",
    ],
    testonly = True,
    visibility = ["//infrastructure:__pkg__"],
)
