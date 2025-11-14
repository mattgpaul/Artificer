load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_process_manager_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_process_manager.py",
    ],
    visibility = ["//infrastructure/multiprocess:__pkg__"],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/multiprocess:process_manager",
    ],
)
