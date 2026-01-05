load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "paper_adapters",
    srcs = ["broker.py"],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
    ],
)
