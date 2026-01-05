load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "apps",
    srcs = [
        "backtest_app.py",
        "forward_app.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
    ],
)
