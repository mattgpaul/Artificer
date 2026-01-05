load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "domain",
    srcs = [
        "equity.py",
        "engine.py",
        "events.py",
        "models.py",
        "portfolio.py",
        "strategies.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/ports",
    ],
)
