load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "timescale_adapters",
    srcs = [
        "journal.py",
        "migrations.py",
        "store.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//infrastructure/postgres",
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
    ],
)

