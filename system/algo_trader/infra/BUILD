load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "infra",
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/infra/redis:redis_services",
        "//system/algo_trader/infra/schwab:schwab_services",
    ],
)
