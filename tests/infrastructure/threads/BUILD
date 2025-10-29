load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_thread_manager_lib",
    testonly = True,
    srcs = ["test_thread_manager.py"],
    visibility = ["//infrastructure/threads:__pkg__"],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/threads:thread_manager",
    ],
)
