load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_mysql_lib",
    testonly = True,
    srcs = ["test_mysql.py"],
    visibility = ["//infrastructure/mysql:__pkg__"],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/mysql",
    ],
)
