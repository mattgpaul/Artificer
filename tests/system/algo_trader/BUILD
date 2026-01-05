load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_sma_e2e_lib",
    testonly = True,
    srcs = [
        "conftest.py",
        "test_sma_e2e.py",
    ],
    visibility = [
        "//system/algo_trader:__pkg__",
    ],
    deps = [
        requirement("pytest"),
        "//system/algo_trader/adapters/paper:paper_adapters",
        "//system/algo_trader/apps",
        "//system/algo_trader/cli",
        "//system/algo_trader/domain",
    ],
)
