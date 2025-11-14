load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

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
    name = "test_base_lib",
    testonly = True,
    srcs = ["test_base.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        ":conftest_lib",
        "//infrastructure/influxdb",
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:strategies",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_main_lib",
    testonly = True,
    srcs = ["test_main.py"],
    visibility = ["//system/algo_trader/strategy:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy:cli_utils",
        "//system/algo_trader/strategy:executor",
        "//system/algo_trader/strategy:main_lib",
        "//system/algo_trader/strategy:strategies",
        requirement("pytest"),
    ],
)
