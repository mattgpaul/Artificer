load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

# Shared fixtures library for e2e tests
py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader:__pkg__",
        "//tests/system/algo_trader:__subpackages__",
    ],
    deps = [
        requirement("pytest"),
        "//system/algo_trader/domain",
        "//system/algo_trader/domain:domain_models",
        "//system/algo_trader/domain:domain_ports",
    ],
)

# E2E test library
py_library(
    name = "test_engine_e2e_lib",
    testonly = True,
    srcs = ["test_engine_e2e.py"],
    visibility = [
        "//system/algo_trader:__pkg__",
    ],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/domain",
        "//system/algo_trader/domain:domain_models",
    ],
)
