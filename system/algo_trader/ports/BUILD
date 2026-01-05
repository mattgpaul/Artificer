load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "ports",
    srcs = [
        "broker.py",
        "clock.py",
        "data_broker.py",
        "journal.py",
        "market_data.py",
        "override.py",
        "portfolio.py",
        "strategy.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
)
