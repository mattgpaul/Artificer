load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "adapters",
    srcs = [],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/adapters/paper:paper_adapters",
        "//system/algo_trader/adapters/redis:redis_adapters",
        "//system/algo_trader/adapters/schwab:schwab_adapters",
        "//system/algo_trader/adapters/timescale:timescale_adapters",
    ],
)
