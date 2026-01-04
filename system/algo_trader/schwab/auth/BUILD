load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "auth",
    srcs = [
        "oauth2.py",
        "token_manager.py",
    ],
    visibility = [
        "//system/algo_trader/schwab:__pkg__",
        "//tests/system/algo_trader/schwab:__pkg__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/infra/redis:redis_services",
        requirement("requests"),
    ],
)
