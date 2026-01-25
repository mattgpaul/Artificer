load("@rules_python//python:defs.bzl", "py_library")

# Unit test library
py_library(
    name = "test_engine_unit_lib",
    testonly = True,
    srcs = ["test_engine_unit.py"],
    visibility = ["//system/algo_trader/domain:__pkg__"],
    deps = [
        "//system/algo_trader/domain",
        "//system/algo_trader/domain:domain_models",
        "//tests/system/algo_trader:conftest_lib",
    ],
)

# Integration test library
py_library(
    name = "test_engine_integration_lib",
    testonly = True,
    srcs = ["test_engine_integration.py"],
    visibility = ["//system/algo_trader/domain:__pkg__"],
    deps = [
        "//system/algo_trader/domain",
        "//system/algo_trader/domain:domain_models",
        "//tests/system/algo_trader:conftest_lib",
    ],
)
