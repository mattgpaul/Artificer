load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/strategy/filters:__pkg__",
        "//tests/system/algo_trader/strategy/filters:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/strategy/filters:filters_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_registry_lib",
    testonly = True,
    srcs = ["test_registry.py"],
    visibility = ["//system/algo_trader/strategy/filters:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy/filters:filters_lib",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_config_loader_lib",
    testonly = True,
    srcs = ["test_config_loader.py"],
    visibility = ["//system/algo_trader/strategy/filters:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy/filters:filters_lib",
        requirement("pytest"),
        requirement("pyyaml"),
    ],
)

py_library(
    name = "test_price_comparison_lib",
    testonly = True,
    srcs = ["test_price_comparison.py"],
    visibility = ["//system/algo_trader/strategy/filters:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy/filters:filters_lib",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_sma_comparison_lib",
    testonly = True,
    srcs = ["test_sma_comparison.py"],
    visibility = ["//system/algo_trader/strategy/filters:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/strategy/filters:filters_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
