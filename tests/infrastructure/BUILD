load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_client_lib",
    testonly = True,
    srcs = ["test_client.py"],
    visibility = ["//infrastructure:__pkg__"],
    deps = [
        "//infrastructure:client",
    ],
)

py_library(
    name = "test_config_lib",
    testonly = True,
    srcs = ["test_config.py"],
    visibility = ["//infrastructure:__pkg__"],
    deps = [
        "//infrastructure:config",
    ],
)
