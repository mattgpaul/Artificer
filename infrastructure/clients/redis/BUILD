load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "redis",
    srcs = [
        "redis_client.py",
    ],
    deps = [
        "//infrastructure/client:client",
        "//infrastructure/logging:logger",
    ],
    visibility = [
        "//infrastructure/client:__subpackages__",
    ],
)
