load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "schwab_adapters",
    srcs = ["market_data.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
        "//system/algo_trader/schwab:schwab_services",
    ],
)
