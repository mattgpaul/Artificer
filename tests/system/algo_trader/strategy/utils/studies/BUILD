load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = ["//tests/system/algo_trader/strategy/utils/studies:__subpackages__"],
    deps = [
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_base_study_lib",
    testonly = True,
    srcs = ["test_base_study.py"],
    visibility = ["//system/algo_trader/strategy/studies:__pkg__"],
    deps = [
        ":conftest_lib",
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/studies:base_study",
        requirement("pandas"),
        requirement("pytest"),
    ],
)
