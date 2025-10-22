load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "redis",
    srcs = ["redis.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("redis"),
    ],
    visibility = ["//visibility:public"],
)
