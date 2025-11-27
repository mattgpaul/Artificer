load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    deps = [
        "//system/algo_trader/strategy/filters:filters_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
    visibility = [
        "//system/algo_trader/strategy/filters:__pkg__",
        "//tests/system/algo_trader/strategy/filters:__subpackages__",
    ],
)

py_library(
    name = "test_registry_lib",
    testonly = True,
    srcs = ["test_registry.py"],
    deps = [
        "//system/algo_trader/strategy/filters:filters_lib",
        ":conftest_lib",
        requirement("pytest"),
    ],
    visibility = ["//system/algo_trader/strategy/filters:__pkg__"],
)

py_library(
    name = "test_config_loader_lib",
    testonly = True,
    srcs = ["test_config_loader.py"],
    deps = [
        "//system/algo_trader/strategy/filters:filters_lib",
        ":conftest_lib",
        requirement("pytest"),
        requirement("pyyaml"),
    ],
    visibility = ["//system/algo_trader/strategy/filters:__pkg__"],
)

py_library(
    name = "test_price_comparison_lib",
    testonly = True,
    srcs = ["test_price_comparison.py"],
    deps = [
        "//system/algo_trader/strategy/filters:filters_lib",
        ":conftest_lib",
        requirement("pytest"),
    ],
    visibility = ["//system/algo_trader/strategy/filters:__pkg__"],
)

py_library(
    name = "test_sma_comparison_lib",
    testonly = True,
    srcs = ["test_sma_comparison.py"],
    deps = [
        "//system/algo_trader/strategy/filters:filters_lib",
        ":conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
    visibility = ["//system/algo_trader/strategy/filters:__pkg__"],
)

