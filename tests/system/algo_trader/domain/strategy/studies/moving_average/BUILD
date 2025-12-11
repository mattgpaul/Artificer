load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "test_simple_moving_average_lib",
    testonly = True,
    srcs = ["test_simple_moving_average.py"],
    visibility = ["//system/algo_trader/strategy/studies/moving_average:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/studies:studies_lib",
        "//system/algo_trader/strategy/studies/moving_average:moving_average_lib",
        "//tests/system/algo_trader/strategy/studies:conftest_lib",
        requirement("numpy"),
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_exponential_moving_average_lib",
    testonly = True,
    srcs = ["test_exponential_moving_average.py"],
    visibility = ["//system/algo_trader/strategy/studies/moving_average:__pkg__"],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader/strategy/studies:studies_lib",
        "//system/algo_trader/strategy/studies/moving_average:moving_average_lib",
        "//tests/system/algo_trader/strategy/studies:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

pytest_test(
    name = "test_exponential_moving_average",
    size = "small",
    coverage_path = "system.algo_trader.strategy.studies.moving_average",
    tags = ["unit"],
    test_lib = ":test_exponential_moving_average_lib",
)
