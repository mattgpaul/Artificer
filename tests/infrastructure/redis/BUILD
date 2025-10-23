load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_redis_lib",
    srcs = ["test_redis.py"],
    deps = [
        "//infrastructure/redis:redis",
        "//infrastructure:client",
        "//infrastructure/logging:logger",
    ],
    testonly = True,
    visibility = ["//infrastructure/redis:__pkg__"],
)

