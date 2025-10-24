load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_redis_lib",
    testonly = True,
    srcs = ["test_redis.py"],
    visibility = ["//infrastructure/redis:__pkg__"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        "//infrastructure/redis",
    ],
)
