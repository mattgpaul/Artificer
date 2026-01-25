load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "redis_services",
    srcs = ["account.py"],
    imports = ["../../.."],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//infrastructure/redis",
    ],
)
