load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/strategy:__pkg__",
        "//tests/system/algo_trader/strategy:__subpackages__",
    ],
    deps = [
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_strategy_lib",
    testonly = True,
    srcs = ["test_strategy.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy:strategy_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_strategy_registry_lib",
    testonly = True,
    srcs = ["test_strategy_registry.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy:strategy_lib",
        requirement("pytest"),
    ],
)

pytest_test(
    name = "test_strategy",
    size = "small",
    coverage_path = "system.algo_trader.strategy",
    tags = ["unit"],
    test_lib = ":test_strategy_lib",
)

pytest_test(
    name = "test_strategy_registry",
    size = "small",
    coverage_path = "system.algo_trader.strategy",
    tags = ["unit"],
    test_lib = ":test_strategy_registry_lib",
)
