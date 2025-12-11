load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "test_simple_moving_average_lib",
    testonly = True,
    srcs = ["test_simple_moving_average.py"],
    visibility = ["//system/algo_trader/strategy/studies/moving_average:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/studies:base_study",
        "//system/algo_trader/strategy/studies/moving_average:simple_moving_average",
        "//tests/system/algo_trader/strategy/utils/studies:conftest_lib",
        requirement("numpy"),
        requirement("pandas"),
        requirement("pytest"),
    ],
)
